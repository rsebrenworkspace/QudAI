using System;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using HarmonyLib;
using XRL;
using XRL.Core;
using XRL.World;
using XRL.World.Parts;
using XRL.UI;
using XRL.World.Skills;
using XRL.World.Parts.Mutation;
using XRL.World.Parts.Skill;
using XRL.Messages;
using XRL.World.Capabilities;

using GameObject = XRL.World.GameObject;
using Physics = XRL.World.Parts.Physics;
using Event = XRL.World.Event;

namespace QudAIBrain
{
    [HarmonyPatch(typeof(XRLCore), "PlayerTurn")]
    public static class AIPlayerTurnPatch
    {
        private const string ExchangeDir = @"C:\Users\rsebr\AppData\LocalLow\Freehold Games\CavesOfQud\QudAI";
        public static string FlagFile => Path.Combine(ExchangeDir, "active.flag");
        private static string StateFile => Path.Combine(ExchangeDir, "state.json");
        private static string ActionFile => Path.Combine(ExchangeDir, "action.json");

        private static bool lastMoveFailed = false;
        private static string lastFailedDir = "";
        private static bool isZoneFullyExplored = false;
        private static string lastZoneId = "";
        private static readonly List<Tuple<int, int>> autoexplorePosHistory = new List<Tuple<int, int>>();
        private static MethodInfo cachedFireMethod = null;

        private static readonly Regex QudColorRegex = new Regex(@"(&[a-zA-Z0-9]|\^[a-zA-Z0-9]|\{\{|\}\})", RegexOptions.Compiled);
        private static readonly Regex PipePrefixRegex = new Regex(@"(\b|^)[a-zA-Z]\|", RegexOptions.Compiled);

        private static readonly (string Dir, int DX, int DY)[] Offsets = new (string, int, int)[]
        {
            ("NW", -1, -1), ("N", 0, -1), ("NE", 1, -1),
            ("W",  -1,  0),                ("E",  1,  0),
            ("SW", -1,  1), ("S", 0,  1), ("SE", 1,  1),

            ("NW2", -2, -2), ("NNW", -1, -2), ("NN", 0, -2), ("NNE", 1, -2), ("NE2", 2, -2),
            ("WNW", -2, -1),                                                  ("ENE", 2, -1),
            ("WW",  -2,  0),                                                  ("EE",  2,  0),
            ("WSW", -2,  1),                                                  ("ESE", 2,  1),
            ("SW2", -2,  2), ("SSW", -1,  2), ("SS", 0,  2), ("SSE", 1,  2), ("SE2", 2,  2)
        };

        public static string PreferredDirection = "";
        public static Cell PreferredTargetCell = null;
        public static GameObject PreferredTargetObj = null;

        public static string GetBestAdjacentEnemyDirection(GameObject player)
        {
            if (player == null || player.CurrentCell == null) return "";

            try
            {
                GameObject target = player.Target ?? Sidebar.CurrentTarget;
                if (target != null && target.CurrentCell != null)
                {
                    string tDir = player.CurrentCell.GetDirectionFromCell(target.CurrentCell);
                    if (!string.IsNullOrEmpty(tDir) && tDir.Length <= 2)
                    {
                        return tDir;
                    }
                }
            }
            catch { }

            try
            {
                for (int i = 0; i < 8; i++)
                {
                    string dir = Offsets[i].Dir;
                    Cell c = player.CurrentCell.GetCellFromDirection(dir, false);
                    if (c != null && c.Objects != null)
                    {
                        if (c.Objects.Any(o => o != null && CheckIsEnemy(o, player)))
                        {
                            return dir;
                        }
                    }
                }
            }
            catch { }

            return "";
        }

        public static string GetBestEnemyDirection(GameObject player)
        {
            string adjDir = GetBestAdjacentEnemyDirection(player);
            if (!string.IsNullOrEmpty(adjDir)) return adjDir;

            if (player == null || player.CurrentCell == null) return "";

            try
            {
                Zone zone = player.CurrentCell.ParentZone;
                if (zone != null)
                {
                    Cell pCell = player.CurrentCell;
                    var closestEnemy = GetSafeZoneObjects(zone)
                        .Where(o => o != null && !o.IsPlayer() && CheckIsEnemy(o, player) && o.CurrentCell != null)
                        .OrderBy(o => Math.Max(Math.Abs(o.CurrentCell.X - pCell.X), Math.Abs(o.CurrentCell.Y - pCell.Y)))
                        .FirstOrDefault();

                    if (closestEnemy != null && closestEnemy.CurrentCell != null)
                    {
                        string cDir = pCell.GetDirectionFromCell(closestEnemy.CurrentCell);
                        if (!string.IsNullOrEmpty(cDir) && cDir.Length <= 2)
                        {
                            return cDir;
                        }
                    }
                }
            }
            catch { }

            return "";
        }

        public static List<GameObject> GetSafeZoneObjects(Zone zone)
        {
            var list = new List<GameObject>();
            if (zone == null) return list;
            try
            {
                for (int x = 0; x < 80; x++)
                {
                    for (int y = 0; y < 25; y++)
                    {
                        Cell c = zone.GetCell(x, y);
                        if (c?.Objects != null)
                        {
                            foreach (var obj in c.Objects)
                            {
                                if (obj != null) list.Add(obj);
                            }
                        }
                    }
                }
            }
            catch { }
            return list;
        }

        public static bool IsCompanion(GameObject obj, GameObject player)
        {
            if (obj == null || player == null || obj == player || obj.IsPlayer() || !obj.IsAlive) return false;
            try
            {
                // 1. Direct effect checks (Proselytize, Beguile, Rebuke, Love)
                if (obj.HasEffect("Proselytized") || obj.HasEffect("Beguiled") || obj.HasEffect("Rebuked") || obj.HasEffect("Lovesick") || obj.HasEffect("LoveTonic"))
                    return true;

                // 2. Direct AI part checks on creature
                if (obj.HasPart("AllyProselytize") || obj.HasPart("AllyBeguile") || obj.HasPart("AllyRebuke") || obj.HasPart("AllyPet") || obj.HasPart("AllyClone"))
                    return true;

                // 3. Brain leader checks
                var brain = obj.Brain ?? obj.GetPart<Brain>();
                if (brain != null)
                {
                    if (brain.PartyLeader == player) return true;
                    if (brain.PartyLeader != null && (brain.PartyLeader.IsPlayer() || brain.PartyLeader.ID == player.ID)) return true;
                }

                // 4. Engine leader and alliance methods
                if (obj.IsLedBy(player)) return true;

                try
                {
                    var comps = player.GetCompanions();
                    if (comps != null && comps.Contains(obj)) return true;
                }
                catch { }
            }
            catch { }
            return false;
        }

        public static bool CanBeProselytized(GameObject obj, GameObject player)
        {
            if (obj == null || player == null || obj == player || obj.IsPlayer() || !obj.IsAlive) return false;
            if (IsCompanion(obj, player)) return false;
            if (obj.Brain == null && !obj.HasPart("Brain")) return false;
            if (obj.HasPart("Corpse") || obj.HasPart("Plant") || obj.HasPart("Fungus") || obj.HasPart("Robot")) return false;
            string bp = obj.Blueprint ?? "";
            string name = obj.DisplayName ?? "";
            if (bp.IndexOf("Glowpad", StringComparison.OrdinalIgnoreCase) >= 0 ||
                bp.IndexOf("Watervine", StringComparison.OrdinalIgnoreCase) >= 0 ||
                bp.IndexOf("Brinestalk", StringComparison.OrdinalIgnoreCase) >= 0 ||
                bp.IndexOf("Brimestalk", StringComparison.OrdinalIgnoreCase) >= 0 ||
                bp.IndexOf("Starapple", StringComparison.OrdinalIgnoreCase) >= 0 ||
                name.IndexOf("Glowpad", StringComparison.OrdinalIgnoreCase) >= 0 ||
                name.IndexOf("Watervine", StringComparison.OrdinalIgnoreCase) >= 0 ||
                name.IndexOf("Brinestalk", StringComparison.OrdinalIgnoreCase) >= 0 ||
                name.IndexOf("Brimestalk", StringComparison.OrdinalIgnoreCase) >= 0 ||
                name.IndexOf("Starapple", StringComparison.OrdinalIgnoreCase) >= 0)
            {
                return false;
            }
            return true;
        }

        public static bool CanSafelyLoot(GameObject item, GameObject player)
        {
            if (item == null || player == null || item == player || item.IsPlayer()) return false;
            if (!item.IsAlive && item.HasPart("Combat")) return false;
            if (item.HasPart("Brain")) return false;
            if (item.HasPart("Door") || item.HasPart("StairsUp") || item.HasPart("StairsDown")) return false;

            // 1. NEVER steal owned objects!
            if (item.IsOwned()) return false;
            if (!string.IsNullOrEmpty(item.Owner)) return false;
            if (item.HasProperty("Owned") || item.HasProperty("OwnedBy")) return false;

            // 2. NEVER loot in peaceful settlements (Joppa, Six Day Stilt, Grit Gate, Kyakukya, etc.)!
            var zone = player.CurrentCell != null ? player.CurrentCell.ParentZone : null;
            if (zone != null)
            {
                string zName = (zone.DisplayName ?? "").ToLower();
                string zId = (zone.ZoneID ?? "").ToLower();
                if (zName.Contains("joppa") || zName.Contains("stilt") || zName.Contains("grit gate") ||
                    zName.Contains("kyakukya") || zName.Contains("yd freehold") || zName.Contains("bey lah") ||
                    zName.Contains("omonporch") || zId.Contains("joppaworld"))
                {
                    return false;
                }
            }

            // 3. NEVER pick up furniture, structural items, fixtures, or containers!
            string bp = (item.Blueprint ?? "").ToLower();
            string name = (item.DisplayName ?? "").ToLower();
            string combined = bp + " " + name;

            string[] furnitureKeywords = new string[] {
                "bed", "bedroll", "chair", "table", "cushion", "bench", "desk", "sconce", "fan",
                "contraption", "chest", "dresser", "basket", "crate", "barrel", "vase", "urn",
                "shelf", "bookshelf", "statue", "idol", "altar", "fountain", "tombstone", "sign",
                "post", "fence", "tree", "bush", "plant", "fungus", "wall", "door", "torchpost",
                "canteen", "waterskin"
            };
            for (int i = 0; i < furnitureKeywords.Length; i++)
            {
                if (combined.Contains(furnitureKeywords[i])) return false;
            }

            if (item.HasPart("Furniture") || item.HasPart("Bed") || item.HasPart("Chair") ||
                item.HasPart("Table") || item.HasPart("Chest") || item.HasPart("Container") ||
                item.HasTag("Furniture") || item.HasTag("Structure") || item.HasTag("Fixture") ||
                item.HasTag("Immobile") || item.HasProperty("Immobile"))
            {
                return false;
            }

            // 4. Must have Physics, be non-solid and takeable
            var phys = item.GetPart<Physics>();
            if (phys == null || phys.Solid) return false;
            if (!phys.Takeable) return false;

            // 5. Weight limit: don't loot heavy bulk (> 15 lbs) or if encumbered
            try
            {
                int weight = phys.Weight;
                if (weight > 15) return false;
                int curWeight = player.GetCarriedWeight();
                int maxWeight = player.GetMaxCarriedWeight();
                if (curWeight + weight > maxWeight - 10) return false;
            }
            catch { }

            // 6. Must be actual desired item type
            bool isLootableType = item.HasPart("Armor") ||
                                  item.HasPart("MeleeWeapon") ||
                                  item.HasPart("MissileWeapon") ||
                                  item.HasPart("Shield") ||
                                  item.HasPart("Commerce") ||
                                  item.HasPart("Key") ||
                                  item.HasPart("TinkerItem") ||
                                  item.HasPart("ModArtifact") ||
                                  item.HasTag("Artifact") ||
                                  item.HasPart("Corpse");

            return isLootableType;
        }

        public static bool CheckIsEnemy(GameObject obj, GameObject player)
        {
            if (obj == null || player == null || obj == player || obj.IsPlayer()) return false;
            if (!obj.IsAlive) return false;
            if (obj.Blueprint != null && obj.Blueprint.EndsWith("Corpse")) return false;

            try
            {
                // 0. ABSOLUTE COMPANION CHECK: If this entity is a companion or led by the player, it is NEVER an enemy!
                if (IsCompanion(obj, player)) return false;

                // 1. Explicit exclude tags
                if (obj.HasTag("ExcludeFromHostiles")) return false;

                var brain = obj.Brain ?? obj.GetPart<Brain>();

                // 2. Conversational NPCs / Merchants / Townsfolk: Never treat peaceful citizens as enemies!
                bool hasConversation = obj.HasPart("ConversationScript") || obj.HasPart("Converser");
                if (hasConversation && !obj.IsHostileTowards(player) && !(brain != null && brain.IsHostileTowards(player)))
                {
                    return false;
                }

                // 3. Engine native hostility: does obj consider player hostile, or player consider obj hostile?
                if (obj.IsHostileTowards(player) || player.IsHostileTowards(obj)) return true;

                // 4. Brain feeling checks
                if (brain != null)
                {
                    if (brain.IsHostileTowards(player)) return true;
                    if (brain.GetFeelingLevel(player) == 0) return true; // FeelingLevel.Hostile
                    if (brain.GetFeeling(player) < 0) return true;
                }

                // 5. Active combat target ONLY if confirmed hostile
                if ((obj.Target == player || (brain != null && brain.Target == player)) && (obj.IsHostileTowards(player) || (brain != null && brain.IsHostileTowards(player))))
                {
                    return true;
                }

                // 6. Explicit user preference: Character hunts wild Glowpads (lilypads) in marshes
                if (obj.Blueprint != null && obj.Blueprint.IndexOf("Glowpad", StringComparison.OrdinalIgnoreCase) >= 0)
                {
                    return true;
                }
            }
            catch (Exception ex)
            {
                UnityEngine.Debug.LogError("[QudAI CheckIsEnemy Error] " + ex.ToString());
            }

            return false;
        }

        public static bool Prefix()
        {
            try
            {
                UnityEngine.Application.runInBackground = true;

                if (!File.Exists(FlagFile) || !UnityEngine.Application.isPlaying)
                {
                    try { Popup.Suppress = false; } catch { }
                    return true;
                }

                // AI is active: suppress all blocking popups and ensure engine doesn't wait on UI thread
                try { Popup.Suppress = true; } catch { }
                try { GameManager.runPlayerTurnOnUIThread = false; } catch { }

                GameObject player = The.Player;
                if (player == null || player.CurrentCell == null) return true;

                if (!player.IsAlive || player.hitpoints <= 0)
                {
                    ExportDeath(player);
                    return true;
                }

                EnsureLightSource(player);
                ExportState(player);
                string action = ReadAction();

                if (!UnityEngine.Application.isPlaying) return true;

                ExecuteCommand(player, action);

                try
                {
                    if (The.Core != null) The.Core.RenderBase();
                }
                catch { }

                return false;
            }
            catch (Exception ex)
            {
                UnityEngine.Debug.LogError("[QudAI Prefix Error] " + ex.ToString());
                return true;
            }
        }

        private static void EnsureLightSource(GameObject player)
        {
            if (player == null || player.CurrentCell == null || player.CurrentCell.ParentZone == null) return;

            var body = player.GetPart<Body>();
            if (body == null) return;

            try
            {
                bool hasLit = false;
                GameObject unburnt = null;

                foreach (var part in body.GetParts())
                {
                    if (part.Equipped != null)
                    {
                        var eq = part.Equipped;
                        var ls = eq.GetPart<LightSource>();
                        if (ls != null && ls.Lit) { hasLit = true; break; }

                        string name = (eq.DisplayName ?? "").ToLower();
                        if (name.Contains("torch") && (name.Contains("unburnt") || name.Contains("unlit") || ls == null || !ls.Lit))
                        {
                            unburnt = eq;
                        }
                    }
                }

                if (!hasLit)
                {
                    if (unburnt != null)
                    {
                        try { unburnt.GetPart<TorchProperties>()?.Light(); } catch { }
                        try { var ls = unburnt.GetPart<LightSource>(); if (ls != null) ls.Lit = true; } catch { }
                        unburnt.FireEvent(Event.New("CommandActivate", "User", player));
                        unburnt.FireEvent(Event.New("LightTorch", "User", player));
                    }
                    else
                    {
                        var inv = player.GetPart<Inventory>();
                        if (inv != null && inv.Objects != null)
                        {
                            var invTorch = inv.Objects.FirstOrDefault(o => (o.DisplayName ?? "").ToLower().Contains("torch"));
                            if (invTorch != null)
                            {
                                player.FireEvent(Event.New("CommandEquipObject", "Object", invTorch));
                                try { invTorch.GetPart<TorchProperties>()?.Light(); } catch { }
                                try { var ls = invTorch.GetPart<LightSource>(); if (ls != null) ls.Lit = true; } catch { }
                                invTorch.FireEvent(Event.New("CommandActivate", "User", player));
                                invTorch.FireEvent(Event.New("LightTorch", "User", player));
                            }
                        }
                    }
                }
            }
            catch { }
        }

        private static void ExportState(GameObject player)
        {
            try
            {
                if (!Directory.Exists(ExchangeDir)) Directory.CreateDirectory(ExchangeDir);

                int hp = player.hitpoints;
                int maxHp = player.baseHitpoints;
                Cell currentCell = player.CurrentCell;
                int px = currentCell?.X ?? -1;
                int py = currentCell?.Y ?? -1;
                int pz = currentCell?.ParentZone?.Z ?? 10;
                string zoneId = currentCell?.ParentZone?.ZoneID ?? "Unknown";
                string zoneName = StripQudFormatting(currentCell?.ParentZone?.DisplayName ?? "Unknown");
                if (zoneId != lastZoneId)
                {
                    lastZoneId = zoneId;
                    isZoneFullyExplored = false;
                    autoexplorePosHistory.Clear();
                }

                bool hasMissileWeapon = false;
                int missileCurrentAmmo = 0;
                int missileMaxAmmo = 0;
                int inventoryAmmo = 0;

                var bodyParts = player.GetPart<Body>()?.GetParts();
                if (bodyParts != null)
                {
                    foreach (var part in bodyParts)
                    {
                        if (part.Type == "Missile Weapon" && part.Equipped != null)
                        {
                            hasMissileWeapon = true;
                            var mw = part.Equipped;
                            if (mw.HasPart("MagazineAmmoLoader"))
                            {
                                var loader = mw.GetPart<MagazineAmmoLoader>();
                                if (loader != null)
                                {
                                    missileCurrentAmmo = loader.Ammo != null ? loader.Ammo.Count : 0;
                                    missileMaxAmmo = loader.MaxAmmo > 0 ? loader.MaxAmmo : 6;

                                    try
                                    {
                                        var invObjects = player.GetInventory();
                                        if (invObjects == null)
                                        {
                                            var inv = player.GetPart<Inventory>();
                                            if (inv != null) invObjects = inv.GetObjects();
                                        }
                                        if (invObjects != null)
                                        {
                                            foreach (var obj in invObjects)
                                            {
                                                if (obj != null && loader.IsValidAmmo(obj))
                                                {
                                                    inventoryAmmo += obj.Count;
                                                }
                                            }
                                        }
                                    }
                                    catch { }
                                }
                            }
                            break;
                        }
                    }
                }

                bool hostilesNearby = false;
                bool hostilesAdjacent = false;
                try
                {
                    hostilesNearby = player.AreHostilesNearby();
                    hostilesAdjacent = player.AreHostilesAdjacent();
                }
                catch { }

                int waterDrams = 0;
                try
                {
                    waterDrams = player.GetFreeDrams();
                }
                catch { }

                string hungerStatus = "Satisfied";
                bool isHungry = false;
                bool isFamished = false;
                try
                {
                    var stomach = player.GetPart<Stomach>();
                    if (stomach != null)
                    {
                        isFamished = stomach.IsFamished() || player.HasEffect("Famished") || player.HasEffect("Starving");
                        isHungry = isFamished || stomach.HungerLevel > 0 || player.HasEffect("Hungry");
                        hungerStatus = isFamished ? "Famished" : isHungry ? "Hungry" : "Satisfied";
                    }
                    else
                    {
                        if (player.HasEffect("Famished") || player.HasEffect("Starving"))
                        {
                            isFamished = true;
                            hungerStatus = "Famished";
                        }
                        else if (player.HasEffect("Hungry"))
                        {
                            isHungry = true;
                            hungerStatus = "Hungry";
                        }
                    }
                }
                catch { }

                int foodCount = 0;
                List<string> foodItemNames = new List<string>();
                try
                {
                    var invObjects = player.GetInventory();
                    if (invObjects == null)
                    {
                        var inv = player.GetPart<Inventory>();
                        if (inv != null) invObjects = inv.GetObjects();
                    }
                    if (invObjects != null)
                    {
                        foreach (var obj in invObjects)
                        {
                            if (obj != null && (obj.HasPart("Food") || obj.HasPart("PreparedCookingIngredient")))
                            {
                                foodCount += obj.Count;
                                string fName = StripQudFormatting(!string.IsNullOrEmpty(obj.DisplayName) ? obj.DisplayName : obj.Blueprint);
                                if (!string.IsNullOrEmpty(fName))
                                {
                                    foodItemNames.Add($"\"{EscapeJson(fName)}\"");
                                }
                            }
                        }
                    }
                }
                catch { }

                int corpsesNearby = 0;
                int harvestableNearby = 0;
                bool campfireNearby = false;
                try
                {
                    if (currentCell != null)
                    {
                        var checkCells = currentCell.GetLocalAdjacentCells();
                        if (checkCells == null) checkCells = new List<Cell>();
                        checkCells.Add(currentCell);

                        foreach (Cell c in checkCells)
                        {
                            if (c?.Objects == null) continue;
                            foreach (var o in c.Objects)
                            {
                                if (o == null || o.IsPlayer()) continue;
                                if (o.HasPart("Campfire") || (o.Blueprint ?? "").IndexOf("Campfire", StringComparison.OrdinalIgnoreCase) >= 0)
                                {
                                    campfireNearby = true;
                                }
                                if (o.HasPart("Corpse") || o.HasPart("Butcherable"))
                                {
                                    corpsesNearby++;
                                }
                                if (o.HasPart("Harvestable"))
                                {
                                    harvestableNearby++;
                                }
                            }
                        }
                    }
                }
                catch { }

                bool isSwimming = false;
                try
                {
                    isSwimming = player.HasEffect<XRL.World.Effects.Swimming>() || player.HasEffect("Swimming") || (currentCell != null && currentCell.HasSwimmingDepthLiquid());
                }
                catch { }

                bool canMakeCamp = false;
                try
                {
                    bool hasCampAbility = false;
                    var abilities = player.GetPart<ActivatedAbilities>();
                    if (abilities?.AbilityByGuid != null)
                    {
                        hasCampAbility = abilities.AbilityByGuid.Values.Any(a => a != null && a.Command == "CommandSurvivalCamp");
                    }
                    canMakeCamp = !isSwimming && (hasCampAbility || player.HasSkill("Survival_Camp") || player.HasSkill("CookingAndGathering")) && !hostilesNearby && !(currentCell?.ParentZone?.IsWorldMap() ?? false);
                }
                catch { }

                bool canCook = !isSwimming && campfireNearby && (player.HasSkill("CookingAndGathering") || foodCount > 0);
                bool canButcher = !isSwimming && player.HasSkill("CookingAndGathering_Butchery") && corpsesNearby > 0;
                bool canHarvest = !isSwimming && player.HasSkill("CookingAndGathering_Harvestry") && harvestableNearby > 0;

                List<string> effectStrs = new List<string>();
                try
                {
                    if (player.Effects != null)
                    {
                        foreach (var fx in player.Effects)
                        {
                            if (fx != null)
                            {
                                string desc = StripQudFormatting(fx.GetDescription());
                                if (!string.IsNullOrEmpty(desc))
                                {
                                    effectStrs.Add($"\"{EscapeJson(desc)}\"");
                                }
                            }
                        }
                    }
                }
                catch { }

                bool isSprinting = false;
                try { isSprinting = player.HasEffect("Running") || player.HasEffect("Sprinting"); } catch { }

                List<string> abilityStrs = new List<string>();
                try
                {
                    var abilities = player.GetPart<ActivatedAbilities>();
                    if (abilities != null && abilities.AbilityByGuid != null)
                    {
                        foreach (var kvp in abilities.AbilityByGuid)
                        {
                            var ab = kvp.Value;
                            if (ab != null && ab.Enabled)
                            {
                                int cd = ab.CooldownRounds > 0 ? ab.CooldownRounds : ab.Cooldown;
                                bool usable = ab.IsUsable;
                                string name = StripQudFormatting(ab.DisplayName);
                                string cmd = ab.Command ?? "";
                                bool active = ab.ToggleState || (name.ToLower().Contains("sprint") && isSprinting);
                                abilityStrs.Add($"{{\"name\": \"{EscapeJson(name)}\", \"command\": \"{EscapeJson(cmd)}\", \"cooldown\": {cd}, \"usable\": {(usable ? "true" : "false")}, \"active\": {(active ? "true" : "false")}}}");
                            }
                        }
                    }
                }
                catch { }

                int playerLevel = player.Stat("Level", 1);
                int playerXP = player.Stat("XP", 0);
                int apPoints = player.Stat("AP", 0);
                int spPoints = player.Stat("SP", 0);
                int mpPoints = player.Stat("MP", 0);

                int statStr = player.Stat("Strength", 10);
                int statAgi = player.Stat("Agility", 10);
                int statTou = player.Stat("Toughness", 10);
                int statInt = player.Stat("Intelligence", 10);
                int statWil = player.Stat("Willpower", 10);
                int statEgo = player.Stat("Ego", 10);

                HashSet<string> learnedSkills = new HashSet<string>();
                List<string> learnableSkillEntries = new List<string>();
                try
                {
                    var allSkills = SkillFactory.GetSkills();
                    if (allSkills != null)
                    {
                        foreach (var s in allSkills)
                        {
                            if (s == null) continue;
                            if (player.HasSkill(s.Class))
                            {
                                learnedSkills.Add($"\"{EscapeJson(s.Class)}\"");
                                if (!string.IsNullOrEmpty(s.Name)) learnedSkills.Add($"\"{EscapeJson(s.Name)}\"");
                            }
                            else
                            {
                                if (!s.Initiatory && s.Cost <= spPoints && s.MeetsRequirements(player, false))
                                {
                                    learnableSkillEntries.Add($"{{\"class\": \"{EscapeJson(s.Class)}\", \"name\": \"{EscapeJson(s.Name)}\", \"cost\": {s.Cost}, \"is_parent\": true, \"parent\": \"\"}}");
                                }
                            }

                            if (s.PowerList != null)
                            {
                                foreach (var p in s.PowerList)
                                {
                                    if (p == null) continue;
                                    if (player.HasSkill(p.Class))
                                    {
                                        learnedSkills.Add($"\"{EscapeJson(p.Class)}\"");
                                        if (!string.IsNullOrEmpty(p.Name)) learnedSkills.Add($"\"{EscapeJson(p.Name)}\"");
                                    }
                                    else
                                    {
                                        if (player.HasSkill(s.Class) && p.Cost <= spPoints && p.MeetsRequirements(player, false))
                                        {
                                            learnableSkillEntries.Add($"{{\"class\": \"{EscapeJson(p.Class)}\", \"name\": \"{EscapeJson(p.Name)}\", \"cost\": {p.Cost}, \"is_parent\": false, \"parent\": \"{EscapeJson(s.Class)}\"}}");
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                catch { }

                List<string> mutationEntries = new List<string>();
                try
                {
                    var mPart = player.GetPart<Mutations>();
                    if (mPart != null && mPart.ActiveMutationList != null)
                    {
                        foreach (var m in mPart.ActiveMutationList)
                        {
                            if (m != null)
                            {
                                string mName = m.GetDisplayName(false);
                                int mLevel = m.Level;
                                int mCap = m.GetMutationCap();
                                bool canLvl = m.CanLevel() && (mLevel < mCap);
                                mutationEntries.Add($"{{\"name\": \"{EscapeJson(mName)}\", \"class\": \"{EscapeJson(m.Name)}\", \"level\": {mLevel}, \"cap\": {mCap}, \"can_level\": {(canLvl ? "true" : "false")}}}");
                            }
                        }
                    }
                }
                catch { }

                StringBuilder sb = new StringBuilder(16384);
                sb.Append("{");
                sb.Append($"\"hp\": {hp},");
                sb.Append($"\"max_hp\": {maxHp},");
                sb.Append($"\"level\": {playerLevel},");
                sb.Append($"\"xp\": {playerXP},");
                sb.Append($"\"ap\": {apPoints},");
                sb.Append($"\"sp\": {spPoints},");
                sb.Append($"\"mp\": {mpPoints},");
                sb.Append($"\"attributes\": {{\"Strength\": {statStr}, \"Agility\": {statAgi}, \"Toughness\": {statTou}, \"Intelligence\": {statInt}, \"Willpower\": {statWil}, \"Ego\": {statEgo}}},");
                sb.Append($"\"skills\": [{string.Join(",", learnedSkills)}],");
                sb.Append($"\"learnable_skills\": [{string.Join(",", learnableSkillEntries)}],");
                sb.Append($"\"mutations\": [{string.Join(",", mutationEntries)}],");
                sb.Append($"\"x\": {px},");
                sb.Append($"\"y\": {py},");
                sb.Append($"\"z\": {pz},");
                sb.Append($"\"is_sprinting\": {(isSprinting ? "true" : "false")},");
                sb.Append($"\"hostiles_nearby\": {(hostilesNearby ? "true" : "false")},");
                sb.Append($"\"hostiles_adjacent\": {(hostilesAdjacent ? "true" : "false")},");
                sb.Append($"\"water_drams\": {waterDrams},");
                sb.Append($"\"hunger_level\": \"{hungerStatus}\",");
                sb.Append($"\"is_hungry\": {(isHungry ? "true" : "false")},");
                sb.Append($"\"is_famished\": {(isFamished ? "true" : "false")},");
                sb.Append($"\"has_food\": {(foodCount > 0 ? "true" : "false")},");
                sb.Append($"\"food_count\": {foodCount},");
                sb.Append($"\"food_items\": [{string.Join(",", foodItemNames)}],");
                sb.Append($"\"corpses_nearby\": {corpsesNearby},");
                sb.Append($"\"harvestable_nearby\": {harvestableNearby},");
                sb.Append($"\"campfire_nearby\": {(campfireNearby ? "true" : "false")},");
                sb.Append($"\"can_make_camp\": {(canMakeCamp ? "true" : "false")},");
                sb.Append($"\"can_cook\": {(canCook ? "true" : "false")},");
                sb.Append($"\"can_butcher\": {(canButcher ? "true" : "false")},");
                sb.Append($"\"can_harvest\": {(canHarvest ? "true" : "false")},");
                sb.Append($"\"is_swimming\": {(isSwimming ? "true" : "false")},");
                sb.Append($"\"effects\": [{string.Join(",", effectStrs)}],");
                sb.Append($"\"abilities\": [{string.Join(",", abilityStrs)}],");
                sb.Append($"\"has_missile_weapon\": {(hasMissileWeapon ? "true" : "false")},");
                sb.Append($"\"missile_ammo\": {missileCurrentAmmo},");
                sb.Append($"\"missile_max_ammo\": {missileMaxAmmo},");
                sb.Append($"\"inventory_ammo\": {inventoryAmmo},");
                sb.Append($"\"zone_id\": \"{EscapeJson(zoneId)}\",");
                sb.Append($"\"zone_name\": \"{EscapeJson(zoneName)}\",");
                sb.Append($"\"zone_fully_explored\": {(isZoneFullyExplored ? "true" : "false")},");
                int zoneTier = 1;
                try { zoneTier = currentCell?.ParentZone?.Tier ?? 1; } catch { }
                sb.Append($"\"zone_tier\": {zoneTier},");

                int unexploredCellCount = 0;
                int sumUnexpX = 0;
                int sumUnexpY = 0;
                try
                {
                    var parentZone = currentCell?.ParentZone;
                    if (parentZone != null && !parentZone.IsWorldMap())
                    {
                        for (int x = 0; x < parentZone.Width; x++)
                        {
                            for (int y = 0; y < parentZone.Height; y++)
                            {
                                Cell c = parentZone.GetCell(x, y);
                                if (c != null && !c.Explored)
                                {
                                    unexploredCellCount++;
                                    sumUnexpX += x;
                                    sumUnexpY += y;
                                }
                            }
                        }
                    }
                }
                catch { }

                sb.Append($"\"unexplored_cells\": {unexploredCellCount},");
                sb.Append($"\"unexplored_centroid_x\": {(unexploredCellCount > 0 ? sumUnexpX / unexploredCellCount : -1)},");
                sb.Append($"\"unexplored_centroid_y\": {(unexploredCellCount > 0 ? sumUnexpY / unexploredCellCount : -1)},");
                string genotype = "";
                string subtype = "";
                try { genotype = player.GetGenotype() ?? ""; } catch { }
                try { subtype = player.GetSubtype() ?? ""; } catch { }

                sb.Append($"\"genotype\": \"{EscapeJson(genotype)}\",");
                sb.Append($"\"subtype\": \"{EscapeJson(subtype)}\",");
                sb.Append($"\"calling\": \"{EscapeJson(subtype)}\",");
                sb.Append($"\"last_move_failed\": {(lastMoveFailed ? "true" : "false")},");
                sb.Append($"\"last_failed_dir\": \"{lastFailedDir}\",");
                sb.Append($"\"equipped_summary\": \"{EscapeJson(GetEquippedSummary(player))}\",");

                List<string> companionStrs = new List<string>();
                HashSet<GameObject> foundCompanions = new HashSet<GameObject>();

                try
                {
                    var comps = player.GetCompanions();
                    if (comps != null)
                    {
                        foreach (var c in comps)
                        {
                            if (c != null && !c.IsPlayer() && c.IsAlive)
                            {
                                foundCompanions.Add(c);
                            }
                        }
                    }
                }
                catch { }

                if (currentCell?.ParentZone != null)
                {
                    try
                    {
                        Zone zone = currentCell.ParentZone;
                        for (int zx = 0; zx < 80; zx++)
                        {
                            for (int zy = 0; zy < 25; zy++)
                            {
                                Cell zc = zone.GetCell(zx, zy);
                                if (zc?.Objects == null) continue;
                                foreach (var zObj in zc.Objects)
                                {
                                    if (zObj != null && !zObj.IsPlayer() && zObj.IsAlive && IsCompanion(zObj, player))
                                    {
                                        foundCompanions.Add(zObj);
                                    }
                                }
                            }
                        }
                    }
                    catch { }
                }

                foreach (var obj in foundCompanions)
                {
                    try
                    {
                        string cName = StripQudFormatting(!string.IsNullOrEmpty(obj.DisplayName) ? obj.DisplayName : obj.Blueprint);
                        int cHp = obj.hitpoints;
                        int cMaxHp = obj.baseHitpoints;
                        Cell cCell = obj.CurrentCell;
                        int cx = cCell?.X ?? -1;
                        int cy = cCell?.Y ?? -1;
                        int cDist = (cx >= 0 && cy >= 0) ? Math.Max(Math.Abs(cx - px), Math.Abs(cy - py)) : 999;
                        string cDir = (cx >= 0 && cy >= 0) ? GetApproximateDirection(px, py, cx, cy) : "";
                        companionStrs.Add($"{{\"name\": \"{EscapeJson(cName)}\", \"hp\": {cHp}, \"max_hp\": {cMaxHp}, \"dist\": {cDist}, \"dir\": \"{cDir}\", \"tx\": {cx}, \"ty\": {cy}}}");
                    }
                    catch { }
                }

                sb.Append($"\"has_companion\": {(companionStrs.Count > 0 ? "true" : "false")},");
                sb.Append($"\"companions\": [{string.Join(",", companionStrs)}],");

                // Expanded spatial scan & active target capture
                sb.Append("\"visible_entities\": [");
                List<string> entityEntries = new List<string>();
                List<string> stairsDownEntries = new List<string>();
                List<string> stairsUpEntries = new List<string>();
                bool standingOnStairsDown = false;
                bool standingOnStairsUp = false;

                if (currentCell != null && currentCell.Objects != null)
                {
                    foreach (var o in currentCell.Objects)
                    {
                        if (o == null || o.IsPlayer()) continue;
                        if (o.HasPart("StairsDown")) standingOnStairsDown = true;
                        if (o.HasPart("StairsUp")) standingOnStairsUp = true;
                    }
                }

                if (currentCell?.ParentZone != null)
                {
                    Zone zone = currentCell.ParentZone;
                    int minX = Math.Max(0, px - 25);
                    int maxX = Math.Min(79, px + 25);
                    int minY = Math.Max(0, py - 20);
                    int maxY = Math.Min(24, py + 20);

                    for (int x = minX; x <= maxX; x++)
                    {
                        for (int y = minY; y <= maxY; y++)
                        {
                            if (x == px && y == py) continue;
                            Cell c = zone.GetCell(x, y);
                            if (c != null && c.Objects != null)
                            {
                                foreach (GameObject obj in c.Objects)
                                {
                                    if (obj == null || obj.IsPlayer()) continue;

                                    string name = StripQudFormatting(!string.IsNullOrEmpty(obj.DisplayName) ? obj.DisplayName : obj.Blueprint);
                                    if (string.IsNullOrEmpty(name) || name.IndexOf("widget", StringComparison.OrdinalIgnoreCase) >= 0) continue;
                                    string bp = obj.Blueprint ?? "";

                                    int dist = Math.Max(Math.Abs(x - px), Math.Abs(y - py));
                                    string dir = GetApproximateDirection(px, py, x, y);

                                    if (obj.HasPart("StairsDown"))
                                    {
                                        stairsDownEntries.Add($"{{\"name\": \"{EscapeJson(name)}\", \"blueprint\": \"{EscapeJson(bp)}\", \"dist\": {dist}, \"dir\": \"{dir}\", \"tx\": {x}, \"ty\": {y}}}");
                                    }
                                    if (obj.HasPart("StairsUp"))
                                    {
                                        stairsUpEntries.Add($"{{\"name\": \"{EscapeJson(name)}\", \"blueprint\": \"{EscapeJson(bp)}\", \"dist\": {dist}, \"dir\": \"{dir}\", \"tx\": {x}, \"ty\": {y}}}");
                                    }

                                    bool isCompanion = IsCompanion(obj, player);
                                    bool isEnemy = !isCompanion && CheckIsEnemy(obj, player);
                                    bool canProselytize = CanBeProselytized(obj, player);

                                    int objLevel = 1;
                                    try { objLevel = obj.Stat("Level", 1); } catch { }
                                    int levelDiff = objLevel - playerLevel;
                                    string diffStr = levelDiff <= -5 ? "Trivial" : levelDiff <= -2 ? "Easy" : levelDiff <= 2 ? "Average" : levelDiff <= 5 ? "Tough" : levelDiff <= 9 ? "Very Tough" : "Impossible";
                                    bool isStationary = obj.HasPart("Plant") || obj.HasPart("Fungus") || obj.HasTag("Immobile") || obj.HasProperty("Immobile") || bp.IndexOf("Glowpad", StringComparison.OrdinalIgnoreCase) >= 0;

                                    entityEntries.Add($"{{\"name\": \"{EscapeJson(name)}\", \"blueprint\": \"{EscapeJson(bp)}\", \"dist\": {dist}, \"dir\": \"{dir}\", \"tx\": {x}, \"ty\": {y}, \"is_enemy\": {(isEnemy ? "true" : "false")}, \"is_companion\": {(isCompanion ? "true" : "false")}, \"can_proselytize\": {(canProselytize ? "true" : "false")}, \"level\": {objLevel}, \"difficulty\": \"{diffStr}\", \"is_stationary\": {(isStationary ? "true" : "false")}}}");
                                }
                            }
                        }
                    }

                    // Active combat target from engine or sidebar
                    try
                    {
                        GameObject currentTarget = Sidebar.CurrentTarget ?? player.Target;
                        if (currentTarget != null && currentTarget != player && !currentTarget.HasPart("Corpse"))
                        {
                            bool isCtCompanion = IsCompanion(currentTarget, player);
                            if (isCtCompanion)
                            {
                                if (player.Target == currentTarget) player.Target = null;
                                if (Sidebar.CurrentTarget == currentTarget) Sidebar.CurrentTarget = null;
                            }
                            else if (CheckIsEnemy(currentTarget, player))
                            {
                                Cell tc = currentTarget.CurrentCell;
                                int tx = tc?.X ?? -1;
                                int ty = tc?.Y ?? -1;
                                if (tx >= 0 && ty >= 0)
                                {
                                    string name = StripQudFormatting(!string.IsNullOrEmpty(currentTarget.DisplayName) ? currentTarget.DisplayName : currentTarget.Blueprint);
                                    int dist = Math.Max(Math.Abs(tx - px), Math.Abs(ty - py));
                                    string dir = GetApproximateDirection(px, py, tx, ty);
                                    string bp = currentTarget.Blueprint ?? "";
                                    int objLevel = 1;
                                    try { objLevel = currentTarget.Stat("Level", 1); } catch { }
                                    int levelDiff = objLevel - playerLevel;
                                    string diffStr = levelDiff <= -5 ? "Trivial" : levelDiff <= -2 ? "Easy" : levelDiff <= 2 ? "Average" : levelDiff <= 5 ? "Tough" : levelDiff <= 9 ? "Very Tough" : "Impossible";
                                    bool isStationary = currentTarget.HasPart("Plant") || currentTarget.HasPart("Fungus") || currentTarget.HasTag("Immobile") || currentTarget.HasProperty("Immobile") || bp.IndexOf("Glowpad", StringComparison.OrdinalIgnoreCase) >= 0;
                                    entityEntries.Insert(0, $"{{\"name\": \"{EscapeJson(name)}\", \"blueprint\": \"{EscapeJson(bp)}\", \"dist\": {dist}, \"dir\": \"{dir}\", \"tx\": {tx}, \"ty\": {ty}, \"is_enemy\": true, \"level\": {objLevel}, \"difficulty\": \"{diffStr}\", \"is_stationary\": {(isStationary ? "true" : "false")}}}");
                                }
                            }
                        }
                    }
                    catch { }
                }
                sb.Append(string.Join(",", entityEntries));
                sb.Append("],");
                sb.Append($"\"standing_on_stairs_down\": {(standingOnStairsDown ? "true" : "false")},");
                sb.Append($"\"standing_on_stairs_up\": {(standingOnStairsUp ? "true" : "false")},");
                sb.Append($"\"stairs_down\": [{string.Join(",", stairsDownEntries)}],");
                sb.Append($"\"stairs_up\": [{string.Join(",", stairsUpEntries)}],");

                // 5x5 Surroundings Grid
                sb.Append("\"surroundings\": {");
                for (int i = 0; i < Offsets.Length; i++)
                {
                    var offset = Offsets[i];
                    string summary = "Blocked";

                    if (currentCell?.ParentZone != null)
                    {
                        int targetX = currentCell.X + offset.DX;
                        int targetY = currentCell.Y + offset.DY;

                        if (targetX < 0 || targetX >= 80 || targetY < 0 || targetY >= 25)
                        {
                            summary = $"[ZONE_EXIT: {offset.Dir}]";
                        }
                        else
                        {
                            Cell neighbor = currentCell.ParentZone.GetCell(targetX, targetY);
                            if (neighbor != null) summary = GetCellSummary(neighbor, player);
                        }
                    }

                    sb.Append($"\"{offset.Dir}\": \"{EscapeJson(summary)}\"");
                    if (i < Offsets.Length - 1) sb.Append(",");
                }
                sb.Append("}}");

                string tempFile = StateFile + ".tmp";
                File.WriteAllText(tempFile, sb.ToString(), Encoding.UTF8);
                if (File.Exists(StateFile)) File.Delete(StateFile);
                File.Move(tempFile, StateFile);
            }
            catch (Exception ex)
            {
                UnityEngine.Debug.LogError("[QudAI ExportState Error] " + ex.ToString());
            }
        }

        private static string GetEquippedSummary(GameObject player)
        {
            var body = player?.GetPart<Body>();
            if (body == null) return "None";

            List<string> gear = new List<string>();
            try
            {
                foreach (var part in body.GetParts())
                {
                    if (part?.Equipped != null)
                    {
                        gear.Add($"{part.Type}: {StripQudFormatting(part.Equipped.DisplayName)}");
                    }
                }
            }
            catch { }

            return gear.Count > 0 ? string.Join("; ", gear) : "Nothing Equipped";
        }

        private static string GetApproximateDirection(int fromX, int fromY, int toX, int toY)
        {
            int dx = toX - fromX;
            int dy = toY - fromY;
            if (dx == 0 && dy < 0) return "N";
            if (dx == 0 && dy > 0) return "S";
            if (dx > 0 && dy == 0) return "E";
            if (dx < 0 && dy == 0) return "W";
            if (dx > 0 && dy < 0) return "NE";
            if (dx < 0 && dy < 0) return "NW";
            if (dx > 0 && dy > 0) return "SE";
            return "SW";
        }

        private static string GetCellSummary(Cell cell, GameObject player)
        {
            if (cell?.Objects == null) return "Empty ground";

            List<string> names = new List<string>();
            foreach (GameObject obj in cell.Objects)
            {
                if (obj == null || obj.IsPlayer()) continue;

                string rawName = !string.IsNullOrEmpty(obj.DisplayName) ? obj.DisplayName : obj.Blueprint;
                string cleanName = StripQudFormatting(rawName);
                if (string.IsNullOrEmpty(cleanName) || cleanName.IndexOf("widget", StringComparison.OrdinalIgnoreCase) >= 0) continue;

                if (IsCompanion(obj, player))
                {
                    names.Insert(0, $"[COMPANION: {cleanName}]");
                    continue;
                }

                if (CheckIsEnemy(obj, player))
                {
                    names.Insert(0, $"[ENEMY: {cleanName}]");
                    continue;
                }

                if (obj.HasPart("StairsDown"))
                {
                    names.Insert(0, $"[STAIRS_DOWN: {cleanName}]");
                    continue;
                }
                if (obj.HasPart("StairsUp"))
                {
                    names.Insert(0, $"[STAIRS_UP: {cleanName}]");
                    continue;
                }
                if (obj.HasPart("Door"))
                {
                    var door = obj.GetPart<Door>();
#pragma warning disable CS0618
                    names.Insert(0, $"{(door != null && door.bOpen ? "Open Door" : "Closed Door")} ({cleanName})");
#pragma warning restore CS0618
                    continue;
                }

                string lower = cleanName.ToLower();
                if (lower.Contains("acid") || lower.Contains("lava") || lower.Contains("magma") || lower.Contains("convalessence"))
                {
                    names.Insert(0, $"[HAZARD: {cleanName}]");
                    continue;
                }

                if (lower.Contains("corpse") || lower.Contains("severed"))
                {
                    names.Add($"[ITEM: {cleanName}]");
                    continue;
                }

                if (obj.HasPart("Combat") || obj.Brain != null || obj.HasPart("Brain"))
                {
                    names.Insert(0, $"[NPC: {cleanName}]");
                    continue;
                }

                var phys = obj.GetPart<Physics>();
                if ((phys != null && phys.Solid) || obj.HasPart("Chair") || obj.HasPart("Bed") || obj.HasPart("Table") || lower.Contains("cushion") || lower.Contains("chair") || lower.Contains("bedroll") || lower.Contains("table"))
                {
                    names.Insert(0, $"[BLOCKED: {cleanName}]");
                    continue;
                }

                names.Add(cleanName);
            }

            try
            {
                bool hasBridge = cell.Objects != null && cell.Objects.Any(o => o != null && (o.DisplayName ?? "").ToLower().Contains("bridge"));
                if (!hasBridge && cell.GetDangerousOpenLiquidVolume() != null)
                {
                    var dangerousLiq = cell.GetDangerousOpenLiquidVolume();
                    string liqName = dangerousLiq != null ? StripQudFormatting(dangerousLiq.DisplayName ?? "dangerous liquid") : "dangerous liquid";
                    names.Insert(0, $"[HAZARD: {liqName}]");
                }
                else if (!cell.IsPassable(player, false))
                {
                    names.Insert(0, "[BLOCKED: impassable terrain]");
                }
                else if (!hasBridge && cell.HasSwimmingDepthLiquid())
                {
                    var swimLiq = cell.GetSwimmingDepthLiquid();
                    string liqName = swimLiq != null ? StripQudFormatting(swimLiq.DisplayName ?? "deep water") : "deep water";
                    names.Insert(0, $"[SWIM: {liqName}]");
                }
            }
            catch { }

            return names.Count > 0 ? string.Join(", ", names) : "Empty ground";
        }

        public static string StripQudFormatting(string input)
        {
            if (string.IsNullOrEmpty(input)) return string.Empty;
            string clean = QudColorRegex.Replace(input, "");
            clean = PipePrefixRegex.Replace(clean, "");
            return clean.Trim();
        }

        private static string ReadAction()
        {
            int elapsed = 0;
            while (elapsed < 6000)
            {
                if (!UnityEngine.Application.isPlaying) return "WAIT";

                if (File.Exists(ActionFile))
                {
                    System.Threading.Thread.Sleep(15);
                    try
                    {
                        string content = File.ReadAllText(ActionFile);
                        File.Delete(ActionFile);

                        if (content.Contains("\"action\":"))
                        {
                            int start = content.IndexOf("\"action\":") + 9;
                            int quoteStart = content.IndexOf("\"", start) + 1;
                            int quoteEnd = content.IndexOf("\"", quoteStart);
                            return content.Substring(quoteStart, quoteEnd - quoteStart);
                        }
                    }
                    catch (IOException) { }
                }

                System.Threading.Thread.Sleep(30);
                elapsed += 30;
            }

            return "WAIT";
        }

        private static void ExecuteCommand(GameObject player, string action)
        {
            try
            {
                string actionLog = Path.Combine(ExchangeDir, "last_action_executed.txt");
                File.WriteAllText(actionLog, $"{DateTime.UtcNow:O}: {action}", Encoding.UTF8);
            }
            catch { }

            if (string.IsNullOrEmpty(action) || action.ToUpper() == "WAIT")
            {
                lastMoveFailed = false;
                lastFailedDir = "";
                player.UseEnergy(1000, "Pass");
                return;
            }

            string act = action.ToUpper().Trim();

            if (act == "AUTOEXPLORE")
            {
                ExecuteAutoexplore(player);
                return;
            }

            if (act == "RELOAD")
            {
                ExecuteReload(player);
                return;
            }

            if (act.StartsWith("FIRE_MISSILE"))
            {
                lastMoveFailed = false;
                lastFailedDir = "";
                try
                {
                    int tx = -1;
                    int ty = -1;
                    if (act.Contains("@"))
                    {
                        string[] parts = act.Split('@')[1].Split(',');
                        if (parts.Length == 2)
                        {
                            int.TryParse(parts[0], out tx);
                            int.TryParse(parts[1], out ty);
                        }
                    }

                    Cell targetCell = null;
                    Cell current = player.CurrentCell;
                    Zone zone = current?.ParentZone;

                    if (zone != null)
                    {
                        if (tx >= 0 && ty >= 0 && tx < 80 && ty < 25)
                        {
                            targetCell = zone.GetCell(tx, ty);
                        }

                        if (targetCell == null)
                        {
                            var enemy = GetSafeZoneObjects(zone)
                                .Where(o => o != null && !o.IsPlayer() && CheckIsEnemy(o, player) && o.CurrentCell != null)
                                .OrderBy(o => Math.Max(Math.Abs(o.CurrentCell.X - current.X), Math.Abs(o.CurrentCell.Y - current.Y)))
                                .FirstOrDefault();
                            targetCell = enemy?.CurrentCell;
                        }
                    }

                    if (targetCell != null)
                    {
                        if (targetCell.Objects != null && targetCell.Objects.Any(o => o != null && IsCompanion(o, player)))
                        {
                            UnityEngine.Debug.LogWarning("[QudAI FIRE_MISSILE] Refusing to fire missile at friendly companion's cell!");
                            return;
                        }
                        ExecuteMissileFire(player, targetCell);
                    }
                }
                catch (Exception ex)
                {
                    UnityEngine.Debug.LogError("[QudAI FIRE_MISSILE Exception] " + ex.ToString());
                }

                if (player.Energy != null && player.Energy.Value >= 1000)
                {
                    player.UseEnergy(1000, "Missile");
                }
                return;
            }

            if (act == "USE_STAIRS_DOWN")
            {
                lastMoveFailed = false;
                lastFailedDir = "";
                int energyBefore = player.Energy?.Value ?? 0;
                bool moved = player.Move("D");
                if (!moved)
                {
                    try
                    {
                        var stairs = player.CurrentCell?.Objects?.FirstOrDefault(o => o != null && o.HasPart("StairsDown"));
                        if (stairs != null)
                        {
                            stairs.FireEvent(Event.New("CommandMoveDown", "User", player));
                        }
                    }
                    catch { }
                }
                if (player.Energy != null && player.Energy.Value >= energyBefore)
                {
                    player.UseEnergy(1000, "Movement");
                }
                return;
            }

            if (act == "USE_STAIRS_UP")
            {
                lastMoveFailed = false;
                lastFailedDir = "";
                int energyBefore = player.Energy?.Value ?? 0;
                bool moved = player.Move("U");
                if (!moved)
                {
                    try
                    {
                        var stairs = player.CurrentCell?.Objects?.FirstOrDefault(o => o != null && o.HasPart("StairsUp"));
                        if (stairs != null)
                        {
                            stairs.FireEvent(Event.New("CommandMoveUp", "User", player));
                        }
                    }
                    catch { }
                }
                if (player.Energy != null && player.Energy.Value >= energyBefore)
                {
                    player.UseEnergy(1000, "Movement");
                }
                return;
            }

            if (act == "GET_ITEM")
            {
                lastMoveFailed = false;
                lastFailedDir = "";
                Cell cell = player.CurrentCell;
                if (cell?.Objects != null)
                {
                    var item = cell.Objects.FirstOrDefault(o => o != null && CanSafelyLoot(o, player));
                    if (item != null)
                    {
                        player.TakeObject(item);
                        try { player.FireEvent(Event.New("CommandAutoEquip")); } catch { }
                    }
                }
                player.UseEnergy(1000, "Pickup");
                return;
            }

            if (act == "EAT")
            {
                lastMoveFailed = false;
                lastFailedDir = "";
                try
                {
                    var invObjects = player.GetInventory();
                    if (invObjects == null)
                    {
                        var inv = player.GetPart<Inventory>();
                        if (inv != null) invObjects = inv.GetObjects();
                    }
                    if (invObjects != null)
                    {
                        var foodObj = invObjects.FirstOrDefault(o => o != null && (o.HasPart("Food") || o.HasPart("PreparedCookingIngredient")));
                        if (foodObj != null)
                        {
                            UnityEngine.Debug.Log($"[QudAI EAT] Consuming food item '{foodObj.DisplayNameOnly}'");
                            try { foodObj.FireEvent(Event.New("Eat", "Eater", player)); } catch { }
                            try { foodObj.FireEvent(Event.New("Eating", "Eater", player)); } catch { }
                            try { player.GetPart<Stomach>()?.ClearHunger(); } catch { }
                            if (player.Energy != null) player.UseEnergy(1000, "Eat");
                            return;
                        }
                    }
                }
                catch (Exception ex)
                {
                    UnityEngine.Debug.LogError("[QudAI EAT Error] " + ex.ToString());
                }
                if (player.Energy != null) player.UseEnergy(1000, "Pass");
                return;
            }

            if (act == "MAKE_CAMP")
            {
                lastMoveFailed = false;
                lastFailedDir = "";
                try
                {
                    if (player.CurrentCell != null && (player.CurrentCell.HasSwimmingDepthLiquid() || player.HasEffect("Swimming") || player.HasEffect<XRL.World.Effects.Swimming>()))
                    {
                        MessageQueue.AddPlayerMessage("{{R|You cannot make camp while swimming in deep water.}}");
                        return;
                    }
                    UnityEngine.Debug.Log("[QudAI MAKE_CAMP] Deploying campfire programmatically");
                    bool hasCampfireNearby = false;
                    if (player.CurrentCell != null)
                    {
                        var cells = player.CurrentCell.GetLocalAdjacentCells();
                        if (cells == null) cells = new List<Cell>();
                        cells.Add(player.CurrentCell);
                        foreach (Cell c in cells)
                        {
                            if (c?.Objects != null && c.Objects.Any(o => o != null && (o.HasPart("Campfire") || (o.Blueprint ?? "").IndexOf("Campfire", StringComparison.OrdinalIgnoreCase) >= 0)))
                            {
                                hasCampfireNearby = true;
                                break;
                            }
                        }
                    }

                    if (!hasCampfireNearby && player.CurrentCell != null)
                    {
                        Cell targetCell = player.CurrentCell;
                        var adj = player.CurrentCell.GetLocalAdjacentCells();
                        if (adj != null)
                        {
                            var emptyCell = adj.FirstOrDefault(c => c != null && c.IsEmpty());
                            if (emptyCell != null) targetCell = emptyCell;
                        }

                        var campfire = targetCell.AddObject("Campfire");
                        if (campfire != null)
                        {
                            try { campfire.SetIntProperty("PlayerCampfire", 1); } catch { }
                            try { campfire.SetStringProperty("PointOfInterestKey", "PlayerCampfire"); } catch { }
                            MessageQueue.AddPlayerMessage("{{G|You deploy a campfire.}}");
                        }
                    }
                }
                catch (Exception ex)
                {
                    UnityEngine.Debug.LogError("[QudAI MAKE_CAMP Error] " + ex.ToString());
                }
                if (player.Energy != null) player.UseEnergy(1000, "MakeCamp");
                return;
            }

            if (act == "COOK_MEAL")
            {
                lastMoveFailed = false;
                lastFailedDir = "";
                try
                {
                    if (player.CurrentCell != null && (player.CurrentCell.HasSwimmingDepthLiquid() || player.HasEffect("Swimming") || player.HasEffect<XRL.World.Effects.Swimming>()))
                    {
                        MessageQueue.AddPlayerMessage("{{R|You cannot cook while swimming in deep water.}}");
                        return;
                    }
                    GameObject campfireObj = null;
                    if (player.CurrentCell != null)
                    {
                        var cells = player.CurrentCell.GetLocalAdjacentCells();
                        if (cells == null) cells = new List<Cell>();
                        cells.Add(player.CurrentCell);
                        foreach (Cell c in cells)
                        {
                            if (c?.Objects != null)
                            {
                                campfireObj = c.Objects.FirstOrDefault(o => o != null && (o.HasPart("Campfire") || (o.Blueprint ?? "").IndexOf("Campfire", StringComparison.OrdinalIgnoreCase) >= 0));
                                if (campfireObj != null) break;
                            }
                        }
                    }

                    if (campfireObj != null)
                    {
                        UnityEngine.Debug.Log($"[QudAI COOK_MEAL] Cooking at campfire '{campfireObj.DisplayNameOnly}' programmatically");

                        // 1. Consume 1 ingredient or food item from player inventory if available
                        var invObjects = player.GetInventory();
                        if (invObjects == null)
                        {
                            var inv = player.GetPart<Inventory>();
                            if (inv != null) invObjects = inv.GetObjects();
                        }
                        if (invObjects != null)
                        {
                            var ingredient = invObjects.FirstOrDefault(o => o != null && (o.HasPart("PreparedCookingIngredient") || o.HasPart("Food")));
                            if (ingredient != null)
                            {
                                try
                                {
                                    if (ingredient.Count > 1)
                                    {
                                        ingredient.Count--;
                                    }
                                    else
                                    {
                                        ingredient.Destroy();
                                    }
                                }
                                catch { }
                            }
                        }

                        // 2. Clear hunger and reset stomach cooking counter
                        var stomach = player.GetPart<Stomach>();
                        if (stomach != null)
                        {
                            try { stomach.ClearHunger(); } catch { }
                            try { stomach.ResetCookingCounter(); } catch { }
                        }

                        // 3. Fire silent engine events without calling campPart.Cook() (which opens interactive UI modal)
                        var campPart = campfireObj.GetPart<Campfire>();
                        if (campPart != null)
                        {
                            try { campPart.AfterCooked(); } catch { }
                        }
                        else
                        {
                            try { campfireObj.FireEvent(Event.New("CookedAt", "Actor", player, "Object", campfireObj)); } catch { }
                        }

                        MessageQueue.AddPlayerMessage("{{G|You whip up a simple meal at the campfire and satisfy your hunger.}}");
                    }
                }
                catch (Exception ex)
                {
                    UnityEngine.Debug.LogError("[QudAI COOK_MEAL Error] " + ex.ToString());
                }
                if (player.Energy != null) player.UseEnergy(1000, "Cook");
                return;
            }

            if (act == "BUTCHER")
            {
                lastMoveFailed = false;
                lastFailedDir = "";
                try
                {
                    GameObject corpseObj = null;
                    if (player.CurrentCell != null)
                    {
                        var cells = player.CurrentCell.GetLocalAdjacentCells();
                        if (cells == null) cells = new List<Cell>();
                        cells.Add(player.CurrentCell);
                        foreach (Cell c in cells)
                        {
                            if (c?.Objects != null)
                            {
                                corpseObj = c.Objects.FirstOrDefault(o => o != null && !o.IsPlayer() && (o.HasPart("Corpse") || o.HasPart("Butcherable")));
                                if (corpseObj != null) break;
                            }
                        }
                    }

                    if (corpseObj != null)
                    {
                        UnityEngine.Debug.Log($"[QudAI BUTCHER] Butchering '{corpseObj.DisplayNameOnly}'");
                        var bPart = corpseObj.GetPart<Butcherable>();
                        if (bPart != null)
                        {
                            try { bPart.AttemptButcher(player); } catch { }
                        }
                        else
                        {
                            try { corpseObj.FireEvent(Event.New("Butcher", "Actor", player)); } catch { }
                        }
                    }
                }
                catch (Exception ex)
                {
                    UnityEngine.Debug.LogError("[QudAI BUTCHER Error] " + ex.ToString());
                }
                if (player.Energy != null) player.UseEnergy(1000, "Butcher");
                return;
            }

            if (act == "HARVEST")
            {
                lastMoveFailed = false;
                lastFailedDir = "";
                try
                {
                    GameObject plantObj = null;
                    if (player.CurrentCell != null)
                    {
                        var cells = player.CurrentCell.GetLocalAdjacentCells();
                        if (cells == null) cells = new List<Cell>();
                        cells.Add(player.CurrentCell);
                        foreach (Cell c in cells)
                        {
                            if (c?.Objects != null)
                            {
                                plantObj = c.Objects.FirstOrDefault(o => o != null && !o.IsPlayer() && o.HasPart("Harvestable"));
                                if (plantObj != null) break;
                            }
                        }
                    }

                    if (plantObj != null)
                    {
                        UnityEngine.Debug.Log($"[QudAI HARVEST] Harvesting '{plantObj.DisplayNameOnly}'");
                        var hPart = plantObj.GetPart<Harvestable>();
                        if (hPart != null)
                        {
                            try { hPart.AttemptHarvest(player); } catch { }
                        }
                        else
                        {
                            try { plantObj.FireEvent(Event.New("Harvest", "Actor", player)); } catch { }
                        }
                    }
                }
                catch (Exception ex)
                {
                    UnityEngine.Debug.LogError("[QudAI HARVEST Error] " + ex.ToString());
                }
                if (player.Energy != null) player.UseEnergy(1000, "Harvest");
                return;
            }

            if (act.StartsWith("AUTOLEVEL"))
            {
                lastMoveFailed = false;
                lastFailedDir = "";
                ExecuteAutolevel(player, action);
                player.UseEnergy(1000, "Pass");
                return;
            }

            if (act == "REST" || act == "PASS")
            {
                lastMoveFailed = false;
                lastFailedDir = "";
                try
                {
                    if (player.Stat("AP", 0) > 0 || player.Stat("SP", 0) >= 50 || player.Stat("MP", 0) > 0)
                    {
                        ExecuteAutolevel(player, "AUTOLEVEL");
                    }
                }
                catch { }
                player.UseEnergy(1000, "Pass");
                return;
            }

            if (act.StartsWith("USE_ABILITY:"))
            {
                lastMoveFailed = false;
                lastFailedDir = "";
                string cmd = action.Substring(12).Trim();

                PreferredDirection = "";
                if (cmd.Contains(":"))
                {
                    string[] parts = cmd.Split(':');
                    cmd = parts[0].Trim();
                    if (parts.Length > 1) PreferredDirection = parts[1].Trim().ToUpper();
                }

                if (string.IsNullOrEmpty(PreferredDirection))
                {
                    PreferredDirection = GetBestEnemyDirection(player);
                }

                bool isProselytize = cmd.IndexOf("proselytize", StringComparison.OrdinalIgnoreCase) >= 0 || cmd.IndexOf("beguile", StringComparison.OrdinalIgnoreCase) >= 0;
                bool isTouchOrDirect = isProselytize || cmd.IndexOf("teleportother", StringComparison.OrdinalIgnoreCase) >= 0;

                GameObject targetObj = player.Target ?? Sidebar.CurrentTarget;
                if (!isProselytize && targetObj != null && IsCompanion(targetObj, player))
                {
                    targetObj = null;
                }
                Cell targetCell = targetObj?.CurrentCell;

                if (!string.IsNullOrEmpty(PreferredDirection) && player.CurrentCell != null && targetCell != null)
                {
                    string existingDir = player.CurrentCell.GetDirectionFromCell(targetCell);
                    if (!string.Equals(existingDir, PreferredDirection, StringComparison.OrdinalIgnoreCase))
                    {
                        targetObj = null;
                        targetCell = null;
                    }
                }

                if (isTouchOrDirect)
                {
                    if (!string.IsNullOrEmpty(PreferredDirection) && player.CurrentCell != null)
                    {
                        Cell adjCell = player.CurrentCell.GetCellFromDirection(PreferredDirection, false);
                        if (adjCell != null && adjCell.Objects != null)
                        {
                            var cand = adjCell.Objects.FirstOrDefault(o => o != null && !o.IsPlayer() && (isProselytize ? CanBeProselytized(o, player) : (!IsCompanion(o, player) && CheckIsEnemy(o, player))));
                            if (cand == null && !isProselytize)
                            {
                                cand = adjCell.Objects.FirstOrDefault(o => o != null && !o.IsPlayer() && !IsCompanion(o, player));
                            }
                            if (cand != null)
                            {
                                targetObj = cand;
                                targetCell = adjCell;
                            }
                        }
                    }
                }

                if (targetObj == null && player.CurrentCell?.ParentZone != null)
                {
                    Cell pCell = player.CurrentCell;
                    var safeZoneObjs = GetSafeZoneObjects(pCell.ParentZone);
                    if (!string.IsNullOrEmpty(PreferredDirection))
                    {
                        targetObj = safeZoneObjs
                            .Where(o => o != null && !o.IsPlayer() && (isProselytize ? CanBeProselytized(o, player) : (!IsCompanion(o, player) && CheckIsEnemy(o, player))) && o.CurrentCell != null)
                            .Where(o => pCell.GetDirectionFromCell(o.CurrentCell).Equals(PreferredDirection, StringComparison.OrdinalIgnoreCase))
                            .OrderBy(o => Math.Max(Math.Abs(o.CurrentCell.X - pCell.X), Math.Abs(o.CurrentCell.Y - pCell.Y)))
                            .FirstOrDefault();
                    }

                    if (targetObj == null)
                    {
                        targetObj = safeZoneObjs
                            .Where(o => o != null && !o.IsPlayer() && (isProselytize ? CanBeProselytized(o, player) : (!IsCompanion(o, player) && CheckIsEnemy(o, player))) && o.CurrentCell != null)
                            .OrderBy(o => Math.Max(Math.Abs(o.CurrentCell.X - pCell.X), Math.Abs(o.CurrentCell.Y - pCell.Y)))
                            .FirstOrDefault();
                    }
                    targetCell = targetObj?.CurrentCell;
                }

                if (targetCell == null && !string.IsNullOrEmpty(PreferredDirection) && player.CurrentCell != null)
                {
                    targetCell = player.CurrentCell.GetCellFromDirection(PreferredDirection, false);
                }

                if (!isProselytize)
                {
                    if (targetObj != null && IsCompanion(targetObj, player))
                    {
                        targetObj = null;
                    }
                    if (targetCell != null && targetCell.Objects != null && targetCell.Objects.Any(o => o != null && IsCompanion(o, player)))
                    {
                        UnityEngine.Debug.LogWarning($"[QudAI USE_ABILITY] Aborting offensive targeting on cell {targetCell.X},{targetCell.Y} because it contains a friendly companion!");
                        targetCell = null;
                        targetObj = null;
                    }
                }

                if (targetObj != null)
                {
                    player.Target = targetObj;
                    try { Sidebar.CurrentTarget = targetObj; } catch { }
                }

                PreferredTargetCell = targetCell;
                PreferredTargetObj = targetObj;

                UnityEngine.Debug.Log($"[QudAI USE_ABILITY] Executing {cmd} towards '{PreferredDirection}' at cell {(targetCell != null ? $"{targetCell.X},{targetCell.Y}" : "null")} on target {(targetObj?.DisplayNameOnly ?? "none")}");

                int energyBefore = player.Energy?.Value ?? 0;
                try
                {
                    CommandEvent.Send(player, cmd, targetObj, targetCell, 0, false, false, null);
                }
                catch (Exception ex)
                {
                    UnityEngine.Debug.LogError("[QudAI CommandEvent Error] " + ex.ToString());
                }

                try
                {
                    player.FireEvent(Event.New(cmd, "User", player));
                }
                catch { }

                try
                {
                    Sidebar.UpdateState();
                    Sidebar.Update();
                }
                catch { }

                PreferredDirection = "";
                PreferredTargetCell = null;
                PreferredTargetObj = null;

                if (player.Energy != null && player.Energy.Value >= energyBefore)
                {
                    player.UseEnergy(1000, "Ability");
                }
                return;
            }

            if (act == "ACTIVATE_SPRINT")
            {
                lastMoveFailed = false;
                lastFailedDir = "";
                try
                {
                    if (!player.HasEffect("Running") && !player.HasEffect("Sprinting"))
                    {
                        var abilities = player.GetPart<ActivatedAbilities>();
                        if (abilities != null && abilities.AbilityByGuid != null)
                        {
                            foreach (var kvp in abilities.AbilityByGuid)
                            {
                                var ab = kvp.Value;
                                if (ab != null && ab.Enabled && ((ab.DisplayName ?? "").ToLower().Contains("sprint") || (ab.Command ?? "").ToLower().Contains("sprint")))
                                {
                                    if (ab.IsUsable && ab.CooldownRounds <= 0 && ab.Cooldown <= 0)
                                    {
                                        player.FireEvent(Event.New(ab.Command, "User", player));
                                        break;
                                    }
                                }
                            }
                        }
                    }
                }
                catch (Exception ex)
                {
                    UnityEngine.Debug.LogError("[QudAI SPRINT Error] " + ex.ToString());
                }

                if (!player.HasEffect("Running") && !player.HasEffect("Sprinting"))
                {
                    if (player.Energy != null && player.Energy.Value >= 1000)
                    {
                        player.UseEnergy(1000, "SprintFail");
                    }
                }
                return;
            }

            if (act.StartsWith("SPRINT_"))
            {
                string dir = act.Substring(7).Trim();
                lastMoveFailed = false;
                lastFailedDir = "";
                try
                {
                    if (!player.HasEffect("Running") && !player.HasEffect("Sprinting"))
                    {
                        var abilities = player.GetPart<ActivatedAbilities>();
                        if (abilities != null && abilities.AbilityByGuid != null)
                        {
                            foreach (var kvp in abilities.AbilityByGuid)
                            {
                                var ab = kvp.Value;
                                if (ab != null && ab.Enabled && ((ab.DisplayName ?? "").ToLower().Contains("sprint") || (ab.Command ?? "").ToLower().Contains("sprint")))
                                {
                                    if (ab.IsUsable && ab.CooldownRounds <= 0 && ab.Cooldown <= 0)
                                    {
                                        player.FireEvent(Event.New(ab.Command, "User", player));
                                        break;
                                    }
                                }
                            }
                        }
                    }
                }
                catch (Exception ex)
                {
                    UnityEngine.Debug.LogError("[QudAI SPRINT Error] " + ex.ToString());
                }

                int energyBefore = player.Energy?.Value ?? 0;
                bool moved = player.Move(dir);
                if (!moved)
                {
                    lastMoveFailed = true;
                    lastFailedDir = dir.ToUpper();
                    TryOpenDoorInDirection(player, dir);
                }
                else
                {
                    lastMoveFailed = false;
                    lastFailedDir = "";
                }
                if (player.Energy != null && player.Energy.Value >= energyBefore)
                {
                    player.UseEnergy(1000, "Movement");
                }
                return;
            }

            string direction = null;
            if (act.StartsWith("MOVE_")) direction = act.Substring(5);

            if (!string.IsNullOrEmpty(direction))
            {
                int energyBefore = player.Energy?.Value ?? 0;
                int pxBefore = player.CurrentCell?.X ?? -1;
                int pyBefore = player.CurrentCell?.Y ?? -1;

                bool moved = player.Move(direction);
                bool cellChanged = (player.CurrentCell != null && (player.CurrentCell.X != pxBefore || player.CurrentCell.Y != pyBefore));

                if (!moved || !cellChanged)
                {
                    // If simple move bumped a wall or obstacle, ask Qud's native pathfinder for an edge step!
                    char edgeChar = direction.ToUpper()[0];
                    string pathStep = null;
                    try
                    {
                        AutoAct.TryFindEdgeStep(edgeChar, out pathStep);
                    }
                    catch { }

                    if (!string.IsNullOrEmpty(pathStep) && pathStep != "." && pathStep != direction)
                    {
                        moved = player.Move(pathStep);
                        cellChanged = (player.CurrentCell != null && (player.CurrentCell.X != pxBefore || player.CurrentCell.Y != pyBefore));
                    }
                }

                if (!moved || !cellChanged)
                {
                    lastMoveFailed = true;
                    lastFailedDir = direction.ToUpper();
                    TryOpenDoorInDirection(player, direction);
                }
                else
                {
                    lastMoveFailed = false;
                    lastFailedDir = "";
                    autoexplorePosHistory.Clear();
                }
                if (player.Energy != null && player.Energy.Value >= energyBefore)
                {
                    player.UseEnergy(1000, "Movement");
                }
            }
            else
            {
                lastMoveFailed = false;
                lastFailedDir = "";
                player.UseEnergy(1000, "Pass");
            }
        }

        private static void ExecuteAutoexplore(GameObject player)
        {
            if (player == null || player.CurrentCell == null)
            {
                lastMoveFailed = false;
                lastFailedDir = "";
                if (player?.Energy != null) player.UseEnergy(1000, "Pass");
                return;
            }

            Zone zone = player.CurrentCell.ParentZone;
            if (zone == null || zone.IsWorldMap())
            {
                lastMoveFailed = false;
                lastFailedDir = "";
                if (player.Energy != null) player.UseEnergy(1000, "Pass");
                return;
            }

            // 1. Pick up takeable item on current tile ONLY if safe to loot (never steal in settlements or take furniture)
            try
            {
                Cell curCell = player.CurrentCell;
                if (curCell != null && curCell.Objects != null)
                {
                    var groundItem = curCell.Objects.FirstOrDefault(o => o != null && CanSafelyLoot(o, player));
                    if (groundItem != null)
                    {
                        player.TakeObject(groundItem);
                        try { player.FireEvent(Event.New("CommandAutoEquip")); } catch { }
                        if (player.Energy != null) player.UseEnergy(1000, "Pickup");
                        lastMoveFailed = false;
                        lastFailedDir = "";
                        return;
                    }
                }
            }
            catch { }

            // 2. Oscillation & cycling detection: track recent coordinates
            int curX = player.CurrentCell.X;
            int curY = player.CurrentCell.Y;
            autoexplorePosHistory.Add(Tuple.Create(curX, curY));
            if (autoexplorePosHistory.Count > 24)
            {
                autoexplorePosHistory.RemoveAt(0);
            }

            int repeatVisits = autoexplorePosHistory.Count(p => p.Item1 == curX && p.Item2 == curY);
            int uniquePositions = autoexplorePosHistory.Select(p => p.Item1 * 1000 + p.Item2).Distinct().Count();
            bool isCycling = (repeatVisits >= 3) || (autoexplorePosHistory.Count >= 10 && uniquePositions <= 5) || (autoexplorePosHistory.Count >= 16 && uniquePositions <= autoexplorePosHistory.Count / 2);

            if (repeatVisits >= 2)
            {
                // We are cycling between coordinates! Suppress adjacent non-combat POIs (signs, tables, bookshelves, chests)
                try
                {
                    var adjCells = player.CurrentCell.GetLocalAdjacentCells();
                    if (adjCells != null)
                    {
                        foreach (Cell adj in adjCells)
                        {
                            if (adj?.Objects == null) continue;
                            foreach (var obj in adj.Objects)
                            {
                                if (obj == null || obj.IsPlayer() || obj.HasPart("Combat") || obj.HasPart("Brain")) continue;
                                if (!CanSafelyLoot(obj, player))
                                {
                                    try { obj.SetIntProperty("AutoexploreSuppressed", 1); } catch { }
                                    try { obj.SetIntProperty("AutoexploreSuppression", 1); } catch { }
                                    try { obj.SetIntProperty("Autoexplored", 1); } catch { }
                                    UnityEngine.Debug.Log($"[QudAI Autoexplore Oscillation] Suppressed adjacent POI '{obj.DisplayNameOnly}' at {adj.X},{adj.Y}");
                                }
                            }
                        }
                    }
                }
                catch { }
            }

            if (isCycling)
            {
                // Persistent cycling: mark zone fully explored and yield to Python brain navigation
                isZoneFullyExplored = true;
                autoexplorePosHistory.Clear();
                lastMoveFailed = false;
                lastFailedDir = "";
                UnityEngine.Debug.LogWarning($"[QudAI Autoexplore Oscillation] Zone marked fully explored due to cycling at ({curX}, {curY}) (visits: {repeatVisits}, unique: {uniquePositions}/{autoexplorePosHistory.Count}). Yielding to brain navigation.");
                if (player.Energy != null) player.UseEnergy(1000, "Pass");
                return;
            }

            // 3. Query native Autoexplore step
            string step = null;
            bool blackout = false;

            try
            {
                FasterDMapAutoexplore.FindAutoexploreStep(out step, out blackout);
            }
            catch { }

            if (string.IsNullOrEmpty(step) || step == ".")
            {
                try
                {
                    AutoAct.FindAutoexploreStep(false, out step, out blackout);
                }
                catch { }
            }

            if (!string.IsNullOrEmpty(step) && step != ".")
            {
                isZoneFullyExplored = false;
                int energyBefore = player.Energy != null ? player.Energy.Value : 0;
                bool moved = player.Move(step);
                if (!moved)
                {
                    lastMoveFailed = true;
                    lastFailedDir = step.ToUpper();
                    TryOpenDoorInDirection(player, step);

                    // If autoexplore told us to move into an impassable object (e.g. table, sign, wall), suppress that object so it won't target it again!
                    try
                    {
                        Cell targetCell = player.CurrentCell.GetCellFromDirection(step, false);
                        if (targetCell?.Objects != null)
                        {
                            foreach (var obj in targetCell.Objects)
                            {
                                if (obj != null && !obj.IsPlayer() && !obj.HasPart("Combat") && !CanSafelyLoot(obj, player))
                                {
                                    try { obj.SetIntProperty("AutoexploreSuppressed", 1); } catch { }
                                    try { obj.SetIntProperty("AutoexploreSuppression", 1); } catch { }
                                    try { obj.SetIntProperty("Autoexplored", 1); } catch { }
                                    UnityEngine.Debug.Log($"[QudAI Autoexplore Blocked] Suppressed blocking object '{obj.DisplayNameOnly}' in direction {step}");
                                }
                            }
                        }
                    }
                    catch { }
                }
                else
                {
                    lastMoveFailed = false;
                    lastFailedDir = "";
                }

                if (player.Energy != null && player.Energy.Value >= energyBefore)
                {
                    player.UseEnergy(1000, "Movement");
                }
                return;
            }

            // 4. Mark zone fully explored when no autoexplore targets remain
            isZoneFullyExplored = true;
            autoexplorePosHistory.Clear();
            lastMoveFailed = false;
            lastFailedDir = "";
            if (player.Energy != null) player.UseEnergy(1000, "Pass");
        }

        private static void ExecuteAutolevel(GameObject player, string command)
        {
            if (player == null || string.IsNullOrEmpty(command)) return;

            try
            {
                // 1. Specific targeted allocations (case-insensitive command parsing)
                if (command.StartsWith("AUTOLEVEL_STAT:", StringComparison.OrdinalIgnoreCase))
                {
                    string targetStat = command.Substring(15).Trim();
                    AllocateStat(player, targetStat);
                    return;
                }

                if (command.StartsWith("AUTOLEVEL_SKILL:", StringComparison.OrdinalIgnoreCase))
                {
                    string targetSkill = command.Substring(16).Trim();
                    AllocateSkill(player, targetSkill);
                    return;
                }

                if (command.StartsWith("AUTOLEVEL_MUTATION:", StringComparison.OrdinalIgnoreCase))
                {
                    string targetMut = command.Substring(19).Trim();
                    AllocateMutation(player, targetMut);
                    return;
                }

                // 2. Full Autolevel Doctrine
                // A. Spend AP (Attributes)
                int ap = player.Stat("AP", 0);
                while (ap > 0)
                {
                    int tou = player.Stat("Toughness", 10);
                    int agi = player.Stat("Agility", 10);
                    string targetAttr = (tou < agi + 2) ? "Toughness" : "Agility";
                    if (!AllocateStat(player, targetAttr)) break;
                    int newAp = player.Stat("AP", 0);
                    if (newAp >= ap) break;
                    ap = newAp;
                }

                // B. Spend MP (Mutations)
                int mp = player.Stat("MP", 0);
                while (mp > 0)
                {
                    if (!AllocateMutation(player, null)) break;
                    int newMp = player.Stat("MP", 0);
                    if (newMp >= mp) break;
                    mp = newMp;
                }

                // C. Spend SP (Skills)
                int sp = player.Stat("SP", 0);
                if (sp >= 50)
                {
                    string[] prioritySkills = new string[]
                    {
                        "Rifles",
                        "Rifle_SteadyHands",
                        "Rifle_DrawABead",
                        "Rifle_FlatteningFire",
                        "Rifle_SuppressiveFire",
                        "Rifle_SureFire",
                        "Acrobatics",
                        "Acrobatics_Dodge",
                        "Acrobatics_SwiftReflexes",
                        "Acrobatics_Jump",
                        "Endurance",
                        "Endurance_Swimming",
                        "Endurance_Longstrider",
                        "Endurance_Weathered",
                        "Endurance_ShakeItOff",
                        "CookingAndGathering_Harvestry",
                        "CookingAndGathering_Butchery"
                    };

                    foreach (string skillClass in prioritySkills)
                    {
                        if (AllocateSkill(player, skillClass))
                        {
                            sp = player.Stat("SP", 0);
                            if (sp < 50) break;
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                UnityEngine.Debug.LogError("[QudAI ExecuteAutolevel Exception] " + ex.ToString());
            }
        }

        private static bool AllocateStat(GameObject player, string statName)
        {
            try
            {
                if (player == null || string.IsNullOrEmpty(statName)) return false;

                var apStat = player.GetStat("AP");
                if (apStat == null || apStat.Value <= 0) return false;

                string[] validStats = new string[] { "Strength", "Agility", "Toughness", "Intelligence", "Willpower", "Ego" };
                string canonicalStat = validStats.FirstOrDefault(s => string.Equals(s, statName.Trim(), StringComparison.OrdinalIgnoreCase)) ?? statName.Trim();

                var targetStat = player.GetStat(canonicalStat);
                if (targetStat == null)
                {
                    foreach (var s in validStats)
                    {
                        if (s.IndexOf(statName.Trim(), StringComparison.OrdinalIgnoreCase) >= 0)
                        {
                            targetStat = player.GetStat(s);
                            if (targetStat != null)
                            {
                                canonicalStat = s;
                                break;
                            }
                        }
                    }
                }

                if (targetStat == null || targetStat.BaseValue >= 100) return false;

                targetStat.BaseValue += 1;
                apStat.Penalty += 1;

                string msg = $"{{G|[AI Level Up] Allocated 1 AP to {canonicalStat} (Now: {targetStat.Value})}}";
                MessageQueue.AddPlayerMessage(msg);
                UnityEngine.Debug.Log("[QudAI LevelUp] " + msg);
                return true;
            }
            catch (Exception ex)
            {
                UnityEngine.Debug.LogError("[QudAI AllocateStat Exception] " + ex.ToString());
                return false;
            }
        }

        private static bool AllocateMutation(GameObject player, string mutationName)
        {
            try
            {
                int mp = player.Stat("MP", 0);
                if (mp <= 0) return false;

                var muts = player.GetPart<Mutations>();
                if (muts == null) return false;

                BaseMutation targetMutation = null;
                if (!string.IsNullOrEmpty(mutationName))
                {
                    string target = mutationName.Trim();
                    targetMutation = muts.GetMutation(target);
                    if (targetMutation == null && muts.MutationList != null)
                    {
                        targetMutation = muts.MutationList.FirstOrDefault(m => m != null && (
                            string.Equals(m.Name, target, StringComparison.OrdinalIgnoreCase) ||
                            string.Equals(m.GetDisplayName(), target, StringComparison.OrdinalIgnoreCase)
                        ));
                    }
                    if (targetMutation == null && muts.ActiveMutationList != null)
                    {
                        targetMutation = muts.ActiveMutationList.FirstOrDefault(m => m != null && (
                            string.Equals(m.Name, target, StringComparison.OrdinalIgnoreCase) ||
                            string.Equals(m.GetDisplayName(), target, StringComparison.OrdinalIgnoreCase)
                        ));
                    }
                }
                else
                {
                    targetMutation = muts.GetMutation("FreezingRay")
                        ?? muts.ActiveMutationList.FirstOrDefault(m => m != null && m.CanLevel() && m.Level < m.GetMutationCap());
                }

                if (targetMutation != null && targetMutation.CanLevel() && targetMutation.Level < targetMutation.GetMutationCap())
                {
                    muts.LevelMutation(targetMutation, targetMutation.BaseLevel + 1);
                    player.UseMP(1, "default");
                    string msg = $"{{G|[AI Level Up] Leveled Mutation: {targetMutation.GetDisplayName(false)} to Rank {targetMutation.Level}}}";
                    MessageQueue.AddPlayerMessage(msg);
                    UnityEngine.Debug.Log("[QudAI LevelUp] " + msg);
                    return true;
                }
            }
            catch (Exception ex)
            {
                UnityEngine.Debug.LogError("[QudAI AllocateMutation Exception] " + ex.ToString());
            }
            return false;
        }

        private static bool AllocateSkill(GameObject player, string skillClass)
        {
            try
            {
                if (player == null || string.IsNullOrEmpty(skillClass)) return false;

                int sp = player.Stat("SP", 0);
                if (sp < 0) return false;

                var skills = player.GetPart<Skills>();
                if (skills == null) return false;

                var allSkills = SkillFactory.GetSkills();
                if (allSkills == null) return false;

                string target = skillClass.Trim();

                // Check skill entry
                SkillEntry sEntry = allSkills.FirstOrDefault(s => s != null && (
                    string.Equals(s.Class, target, StringComparison.OrdinalIgnoreCase) ||
                    string.Equals(s.Name, target, StringComparison.OrdinalIgnoreCase)
                ));
                if (sEntry != null)
                {
                    if (player.HasSkill(sEntry.Class)) return false;
                    if (!sEntry.Initiatory && sEntry.Cost <= sp && sEntry.MeetsRequirements(player, false))
                    {
                        skills.AddSkill(sEntry.Class);
                        var spStat = player.GetStat("SP");
                        if (spStat != null) spStat.Penalty += sEntry.Cost;
                        string msg = $"{{G|[AI Level Up] Learned Skill: {sEntry.Name} for {sEntry.Cost} SP}}";
                        MessageQueue.AddPlayerMessage(msg);
                        UnityEngine.Debug.Log("[QudAI LevelUp] " + msg);
                        return true;
                    }
                    return false;
                }

                // Check power entry
                foreach (var s in allSkills)
                {
                    if (s == null || s.PowerList == null) continue;
                    PowerEntry pEntry = s.PowerList.FirstOrDefault(p => p != null && (
                        string.Equals(p.Class, target, StringComparison.OrdinalIgnoreCase) ||
                        string.Equals(p.Name, target, StringComparison.OrdinalIgnoreCase)
                    ));
                    if (pEntry != null)
                    {
                        if (player.HasSkill(pEntry.Class)) return false;
                        if (!player.HasSkill(s.Class))
                        {
                            // If player doesn't have parent skill, attempt to buy parent + power together if affordable!
                            if (!s.Initiatory && (s.Cost + pEntry.Cost) <= sp && s.MeetsRequirements(player, false) && pEntry.MeetsRequirements(player, false))
                            {
                                skills.AddSkill(s.Class);
                                skills.AddSkill(pEntry.Class);
                                var spStat = player.GetStat("SP");
                                if (spStat != null) spStat.Penalty += (s.Cost + pEntry.Cost);
                                string msg = $"{{G|[AI Level Up] Learned Parent Skill {s.Name} ({s.Cost} SP) and Power {pEntry.Name} ({pEntry.Cost} SP)}}";
                                MessageQueue.AddPlayerMessage(msg);
                                UnityEngine.Debug.Log("[QudAI LevelUp] " + msg);
                                return true;
                            }
                            return false;
                        }

                        if (pEntry.Cost <= sp && pEntry.MeetsRequirements(player, false))
                        {
                            skills.AddSkill(pEntry.Class);
                            var spStat = player.GetStat("SP");
                            if (spStat != null) spStat.Penalty += pEntry.Cost;
                            string msg = $"{{G|[AI Level Up] Learned Power: {pEntry.Name} for {pEntry.Cost} SP}}";
                            MessageQueue.AddPlayerMessage(msg);
                            UnityEngine.Debug.Log("[QudAI LevelUp] " + msg);
                            return true;
                        }
                        return false;
                    }
                }
            }
            catch (Exception ex)
            {
                UnityEngine.Debug.LogError("[QudAI AllocateSkill Exception] " + ex.ToString());
            }
            return false;
        }

        private static void ExecuteReload(GameObject player)
        {
            lastMoveFailed = false;
            lastFailedDir = "";

            bool reloaded = false;
            try
            {
                var body = player.GetPart<Body>();
                if (body != null)
                {
                    var invObjects = player.GetInventory();
                    if (invObjects == null)
                    {
                        var inv = player.GetPart<Inventory>();
                        if (inv != null) invObjects = inv.GetObjects();
                    }

                    if (invObjects != null)
                    {
                        foreach (var part in body.GetParts())
                        {
                            if (part.Type == "Missile Weapon" && part.Equipped != null)
                            {
                                var weapon = part.Equipped;
                                var loader = weapon.GetPart<MagazineAmmoLoader>();
                                if (loader != null)
                                {
                                    int currentAmmo = loader.Ammo != null ? loader.Ammo.Count : 0;
                                    int maxAmmo = loader.MaxAmmo > 0 ? loader.MaxAmmo : 6;

                                    if (currentAmmo < maxAmmo)
                                    {
                                        GameObject slugStack = invObjects
                                            .Where(o => o != null && loader.IsValidAmmo(o))
                                            .OrderByDescending(o => o.Count)
                                            .FirstOrDefault();

                                        if (slugStack != null)
                                        {
                                            if (loader.Ammo != null && loader.Ammo.Count > 0)
                                            {
                                                try { loader.Unload(player); } catch { }
                                            }
                                            loader.Load(player, slugStack, false);
                                            reloaded = true;
                                            UnityEngine.Debug.Log($"[QudAI] Successfully loaded {weapon.DisplayNameOnly} with {slugStack.DisplayNameOnly} ({slugStack.Count} left in stack).");
                                            break;
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                UnityEngine.Debug.LogError("[QudAI ExecuteReload Error] " + ex.ToString());
            }

            if (reloaded)
            {
                player.UseEnergy(1000, "Reload");
            }
            else
            {
                player.UseEnergy(1000, "Pass");
            }
        }

        private static void ExecuteMissileFire(GameObject player, Cell targetCell)
        {
            if (player == null || targetCell == null) return;

            // Only fire if the missile weapon is equipped and has ammo loaded
            try
            {
                var body = player.GetPart<Body>();
                if (body != null)
                {
                    bool hasLoadedAmmo = false;
                    foreach (var part in body.GetParts())
                    {
                        if (part.Type == "Missile Weapon" && part.Equipped != null)
                        {
                            var mw = part.Equipped;
                            var loader = mw.GetPart<MagazineAmmoLoader>();
                            if (loader != null && loader.Ammo != null && loader.Ammo.Count > 0)
                            {
                                hasLoadedAmmo = true;
                                break;
                            }
                        }
                    }

                    if (!hasLoadedAmmo)
                    {
                        UnityEngine.Debug.Log("[QudAI] Missile weapon empty during fire command; redirecting to ExecuteReload.");
                        ExecuteReload(player);
                        return;
                    }
                }
            }
            catch { }

            GameObject targetObj = null;
            if (targetCell.Objects != null)
            {
                targetObj = targetCell.Objects.FirstOrDefault(o => o != null && !o.IsPlayer() && CheckIsEnemy(o, player));
            }

            try
            {
                var brain = player.Brain ?? player.GetPart<Brain>();
                if (brain != null && targetObj != null)
                {
                    brain.Target = targetObj;
                }
            }
            catch { }

            try
            {
                if (cachedFireMethod == null)
                {
                    cachedFireMethod = typeof(Combat).GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static | BindingFlags.Instance)
                        .FirstOrDefault(m => m.Name == "FireMissileWeapon");
                }

                if (cachedFireMethod != null)
                {
                    var parameters = cachedFireMethod.GetParameters();
                    object[] args = new object[parameters.Length];

                    for (int i = 0; i < parameters.Length; i++)
                    {
                        var p = parameters[i];
                        string pName = p.Name.ToLower();
                        Type pType = p.ParameterType;

                        if (pName == "attacker")
                        {
                            args[i] = player;
                        }
                        else if (pName == "aimedat")
                        {
                            args[i] = targetObj;
                        }
                        else if (pName == "targetcell")
                        {
                            args[i] = targetCell;
                        }
                        else if (pName == "sweepwidth")
                        {
                            args[i] = 0; // Overrides Qud's default 90-degree fan spray
                        }
                        else if (pName == "sweepshots")
                        {
                            args[i] = 0;
                        }
                        else if (pName == "rapid")
                        {
                            args[i] = 0;
                        }
                        else if (pName == "skill")
                        {
                            args[i] = "Rifle";
                        }
                        else if (p.HasDefaultValue)
                        {
                            args[i] = p.DefaultValue;
                        }
                        else if (pType.IsValueType)
                        {
                            args[i] = Activator.CreateInstance(pType);
                        }
                        else
                        {
                            args[i] = null;
                        }
                    }

                    object instance = cachedFireMethod.IsStatic ? null : player.GetPart<Combat>();
                    cachedFireMethod.Invoke(instance, args);
                }
            }
            catch (Exception ex)
            {
                UnityEngine.Debug.LogError("[QudAI ExecuteMissileFire Invocation Error] " + ex.ToString());
            }
        }

        private static void TryOpenDoorInDirection(GameObject player, string direction)
        {
            try
            {
                Cell current = player.CurrentCell;
                if (current?.ParentZone == null) return;
                foreach (var offset in Offsets)
                {
                    if (offset.Dir.Equals(direction, StringComparison.OrdinalIgnoreCase))
                    {
                        Cell target = current.ParentZone.GetCell(current.X + offset.DX, current.Y + offset.DY);
                        var door = target?.Objects?.FirstOrDefault(o => o.HasPart("Door"));
                        if (door != null) door.FireEvent(Event.New("Open", "Opener", player));
                        break;
                    }
                }
            }
            catch { }
        }

        public static void ExportDeath(GameObject player, string customReason = null, string customCategory = null)
        {
            try
            {
                if (!Directory.Exists(ExchangeDir)) Directory.CreateDirectory(ExchangeDir);
                string deathFile = Path.Combine(ExchangeDir, "death.json");
                if (File.Exists(deathFile)) return;

                string name = StripQudFormatting(player?.DisplayName ?? "Unknown Nomad");
                int level = 1;
                try { if (player != null && player.HasStat("Level")) level = player.Stat("Level"); } catch { }
                long turns = The.Game != null ? The.Game.Turns : 0;
                string zone = StripQudFormatting(player?.CurrentCell?.ParentZone?.DisplayName ?? "Unknown Sands");
                string reason = !string.IsNullOrEmpty(customReason) ? StripQudFormatting(customReason) : StripQudFormatting(The.Game?.DeathReason ?? "Slain in the salt wastes");
                string category = !string.IsNullOrEmpty(customCategory) ? StripQudFormatting(customCategory) : StripQudFormatting(The.Game?.DeathCategory ?? "Combat");

                string json = $"{{\"player_name\": \"{EscapeJson(name)}\", \"level\": {level}, \"turns\": {turns}, \"zone\": \"{EscapeJson(zone)}\", \"death_reason\": \"{EscapeJson(reason)}\", \"death_category\": \"{EscapeJson(category)}\", \"timestamp\": \"{DateTime.UtcNow:O}\"}}";
                File.WriteAllText(deathFile, json, Encoding.UTF8);
                UnityEngine.Debug.Log($"[QudAI ExportDeath] Player death exported: {name} fell in {zone} ({reason})");
            }
            catch (Exception ex)
            {
                UnityEngine.Debug.LogError("[QudAI ExportDeath Error] " + ex.ToString());
            }
        }

        private static string EscapeJson(string s)
        {
            if (string.IsNullOrEmpty(s)) return "";
            StringBuilder sb = new StringBuilder(s.Length);
            foreach (char c in s)
            {
                if (c == '\\') sb.Append("\\\\");
                else if (c == '\"') sb.Append("\\\"");
                else if (c == '\r') { }
                else if (c == '\n' || c == '\t') sb.Append(" ");
                else if (c >= 32) sb.Append(c);
            }
            return sb.ToString();
        }
    }

    [HarmonyPatch(typeof(XRL.World.GameObject), "Die")]
    public static class AIDiePatch
    {
        public static void Prefix(GameObject __instance, GameObject Killer, string KillerText, string Reason, string ThirdPersonReason, string DeathCategory)
        {
            try
            {
                if (__instance != null && __instance.IsPlayer())
                {
                    string killerName = Killer != null ? AIPlayerTurnPatch.StripQudFormatting(Killer.DisplayName) : (!string.IsNullOrEmpty(KillerText) ? KillerText : "the dangers of Qud");
                    string deathReason = !string.IsNullOrEmpty(ThirdPersonReason) ? ThirdPersonReason : (!string.IsNullOrEmpty(Reason) ? Reason : $"killed by {killerName}");
                    string category = !string.IsNullOrEmpty(DeathCategory) ? DeathCategory : "Combat";

                    AIPlayerTurnPatch.ExportDeath(__instance, deathReason, category);
                }
            }
            catch (Exception ex)
            {
                UnityEngine.Debug.LogError("[QudAI AIDiePatch Error] " + ex.ToString());
            }
        }
    }

    [HarmonyPatch(typeof(XRL.UI.PickDirection), "ShowPicker")]
    public static class AIPickDirectionPatch
    {
        public static bool Prefix(ref string __result)
        {
            if (File.Exists(AIPlayerTurnPatch.FlagFile))
            {
                string dir = AIPlayerTurnPatch.PreferredDirection;
                if (string.IsNullOrEmpty(dir) && AIPlayerTurnPatch.PreferredTargetCell != null && The.Player?.CurrentCell != null)
                {
                    try { dir = The.Player.CurrentCell.GetDirectionFromCell(AIPlayerTurnPatch.PreferredTargetCell); } catch { }
                }
                if (string.IsNullOrEmpty(dir))
                {
                    dir = AIPlayerTurnPatch.GetBestEnemyDirection(The.Player);
                }
                __result = !string.IsNullOrEmpty(dir) ? dir : null;
                UnityEngine.Debug.Log($"[QudAI AIPickDirectionPatch] Auto-selected direction: '{__result}'");
                return false;
            }
            return true;
        }
    }

    [HarmonyPatch(typeof(XRL.UI.PickItem), "ShowPickerInternal")]
    public static class AIPickItemPatch
    {
        public static bool Prefix(IList<GameObject> Items, ref GameObject __result)
        {
            if (File.Exists(AIPlayerTurnPatch.FlagFile))
            {
                GameObject player = The.Player;
                GameObject safeItem = null;
                if (Items != null)
                {
                    for (int i = 0; i < Items.Count; i++)
                    {
                        if (Items[i] != null && AIPlayerTurnPatch.CanSafelyLoot(Items[i], player))
                        {
                            safeItem = Items[i];
                            break;
                        }
                    }
                }
                __result = safeItem;
                UnityEngine.Debug.Log($"[QudAI AIPickItemPatch] Auto-selected item: '{__result?.DisplayNameOnly ?? "None (Unsafe/Owned)"}'");
                return false;
            }
            return true;
        }
    }

    [HarmonyPatch(typeof(XRL.UI.Popup), "PickGameObject")]
    public static class AIPickGameObjectPatch
    {
        public static bool Prefix(List<GameObject> Objects, ref GameObject __result)
        {
            if (File.Exists(AIPlayerTurnPatch.FlagFile))
            {
                if (Objects != null && Objects.Count > 0)
                {
                    if (AIPlayerTurnPatch.PreferredTargetObj != null && Objects.Contains(AIPlayerTurnPatch.PreferredTargetObj))
                    {
                        __result = AIPlayerTurnPatch.PreferredTargetObj;
                    }
                    else
                    {
                        GameObject enemy = null;
                        foreach (var obj in Objects)
                        {
                            if (obj != null && !obj.IsPlayer() && AIPlayerTurnPatch.CheckIsEnemy(obj, The.Player))
                            {
                                enemy = obj;
                                break;
                            }
                        }
                        if (enemy != null)
                        {
                            __result = enemy;
                        }
                        else
                        {
                            GameObject nonPlayer = null;
                            foreach (var obj in Objects)
                            {
                                if (obj != null && !obj.IsPlayer() && obj.IsAlive)
                                {
                                    if (!AIPlayerTurnPatch.IsCompanion(obj, The.Player) && !obj.HasPart("Plant") && !obj.HasPart("Fungus") && !obj.HasPart("Robot"))
                                    {
                                        string bp = obj.Blueprint ?? "";
                                        if (bp.IndexOf("Glowpad", StringComparison.OrdinalIgnoreCase) < 0 &&
                                            bp.IndexOf("Watervine", StringComparison.OrdinalIgnoreCase) < 0 &&
                                            bp.IndexOf("Brinestalk", StringComparison.OrdinalIgnoreCase) < 0)
                                        {
                                            nonPlayer = obj;
                                            break;
                                        }
                                    }
                                }
                            }
                            __result = nonPlayer ?? Objects.Find(o => !o.IsPlayer() && !AIPlayerTurnPatch.IsCompanion(o, The.Player) && !(o.Blueprint ?? "").Contains("Glowpad")) ?? Objects[0];
                        }
                    }
                }
                else
                {
                    __result = null;
                }
                UnityEngine.Debug.Log($"[QudAI AIPickGameObjectPatch] Auto-selected GameObject: '{__result?.DisplayNameOnly}'");
                return false;
            }
            return true;
        }
    }

    [HarmonyPatch(typeof(XRL.UI.PickTarget), "ShowPicker")]
    public static class AIPickTargetPatch
    {
        public static bool Prefix(ref Cell __result)
        {
            if (File.Exists(AIPlayerTurnPatch.FlagFile))
            {
                if (AIPlayerTurnPatch.PreferredTargetCell != null)
                {
                    __result = AIPlayerTurnPatch.PreferredTargetCell;
                    UnityEngine.Debug.Log($"[QudAI AIPickTargetPatch] Auto-selected preferred target cell: {__result.X},{__result.Y}");
                    return false;
                }

                GameObject player = The.Player;
                GameObject target = player?.Target ?? Sidebar.CurrentTarget;
                if (target != null && AIPlayerTurnPatch.IsCompanion(target, player))
                {
                    target = null;
                }

                if (target == null && player?.CurrentCell?.ParentZone != null)
                {
                    Cell pCell = player.CurrentCell;
                    var safeZoneObjs = AIPlayerTurnPatch.GetSafeZoneObjects(pCell.ParentZone);
                    if (!string.IsNullOrEmpty(AIPlayerTurnPatch.PreferredDirection))
                    {
                        target = safeZoneObjs
                            .Where(o => o != null && !o.IsPlayer() && AIPlayerTurnPatch.CheckIsEnemy(o, player) && o.CurrentCell != null)
                            .Where(o => pCell.GetDirectionFromCell(o.CurrentCell).Equals(AIPlayerTurnPatch.PreferredDirection, StringComparison.OrdinalIgnoreCase))
                            .OrderBy(o => Math.Max(Math.Abs(o.CurrentCell.X - pCell.X), Math.Abs(o.CurrentCell.Y - pCell.Y)))
                            .FirstOrDefault();
                    }
                    if (target == null)
                    {
                        target = safeZoneObjs
                            .Where(o => o != null && !o.IsPlayer() && AIPlayerTurnPatch.CheckIsEnemy(o, player) && o.CurrentCell != null)
                            .OrderBy(o => Math.Max(Math.Abs(o.CurrentCell.X - pCell.X), Math.Abs(o.CurrentCell.Y - pCell.Y)))
                            .FirstOrDefault();
                    }
                }

                if (target != null && target.CurrentCell != null)
                {
                    __result = target.CurrentCell;
                    UnityEngine.Debug.Log($"[QudAI AIPickTargetPatch] Auto-selected target cell: {__result.X},{__result.Y}");
                    return false;
                }

                if (!string.IsNullOrEmpty(AIPlayerTurnPatch.PreferredDirection) && player?.CurrentCell != null)
                {
                    Cell dirCell = player.CurrentCell.GetCellFromDirection(AIPlayerTurnPatch.PreferredDirection, false);
                    if (dirCell != null)
                    {
                        __result = dirCell;
                        UnityEngine.Debug.Log($"[QudAI AIPickTargetPatch] Auto-selected direction cell: {__result.X},{__result.Y}");
                        return false;
                    }
                }

                __result = null;
                return false;
            }
            return true;
        }
    }

    [HarmonyPatch(typeof(XRL.UI.PickTarget), "ShowFieldPicker")]
    public static class AIPickFieldTargetPatch
    {
        public static bool Prefix(ref List<Cell> __result)
        {
            if (File.Exists(AIPlayerTurnPatch.FlagFile))
            {
                if (AIPlayerTurnPatch.PreferredTargetCell != null)
                {
                    __result = new List<Cell> { AIPlayerTurnPatch.PreferredTargetCell };
                    UnityEngine.Debug.Log($"[QudAI AIPickFieldTargetPatch] Auto-selected preferred field target cell: {AIPlayerTurnPatch.PreferredTargetCell.X},{AIPlayerTurnPatch.PreferredTargetCell.Y}");
                    return false;
                }

                GameObject player = The.Player;
                GameObject target = player?.Target ?? Sidebar.CurrentTarget;
                if (target != null && AIPlayerTurnPatch.IsCompanion(target, player))
                {
                    target = null;
                }

                if (target == null && player?.CurrentCell?.ParentZone != null)
                {
                    Cell pCell = player.CurrentCell;
                    var safeZoneObjs = AIPlayerTurnPatch.GetSafeZoneObjects(pCell.ParentZone);
                    if (!string.IsNullOrEmpty(AIPlayerTurnPatch.PreferredDirection))
                    {
                        target = safeZoneObjs
                            .Where(o => o != null && !o.IsPlayer() && AIPlayerTurnPatch.CheckIsEnemy(o, player) && o.CurrentCell != null)
                            .Where(o => pCell.GetDirectionFromCell(o.CurrentCell).Equals(AIPlayerTurnPatch.PreferredDirection, StringComparison.OrdinalIgnoreCase))
                            .OrderBy(o => Math.Max(Math.Abs(o.CurrentCell.X - pCell.X), Math.Abs(o.CurrentCell.Y - pCell.Y)))
                            .FirstOrDefault();
                    }
                    if (target == null)
                    {
                        target = safeZoneObjs
                            .Where(o => o != null && !o.IsPlayer() && AIPlayerTurnPatch.CheckIsEnemy(o, player) && o.CurrentCell != null)
                            .OrderBy(o => Math.Max(Math.Abs(o.CurrentCell.X - pCell.X), Math.Abs(o.CurrentCell.Y - pCell.Y)))
                            .FirstOrDefault();
                    }
                }

                if (target != null && target.CurrentCell != null)
                {
                    __result = new List<Cell> { target.CurrentCell };
                    return false;
                }

                if (!string.IsNullOrEmpty(AIPlayerTurnPatch.PreferredDirection) && player?.CurrentCell != null)
                {
                    Cell dirCell = player.CurrentCell.GetCellFromDirection(AIPlayerTurnPatch.PreferredDirection, false);
                    if (dirCell != null)
                    {
                        __result = new List<Cell> { dirCell };
                        return false;
                    }
                }

                __result = new List<Cell>();
                return false;
            }
            return true;
        }
    }
}