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
        public static string ExchangeFile(string name) { return Path.Combine(ExchangeDir, name); }
        private static string StateFile => Path.Combine(ExchangeDir, "state.json");
        private static string ActionFile => Path.Combine(ExchangeDir, "action.json");

        private static bool lastMoveFailed = false;
        private static string lastFailedDir = "";
        private static bool isZoneFullyExplored = false;
        private static bool isAutoexploreStuck = false;
        private static int lastUnexploredCellCount = 0;
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
        public static string PreferredMutation = "";

        public static HashSet<string> RegisteredCompanionIds = new HashSet<string>();

        public static List<Cell> GetLineBetween(Cell from, Cell to)
        {
            List<Cell> line = new List<Cell>();
            if (from == null || to == null || from.ParentZone == null) return line;
            int x0 = from.X;
            int y0 = from.Y;
            int x1 = to.X;
            int y1 = to.Y;

            int dx = Math.Abs(x1 - x0);
            int dy = Math.Abs(y1 - y0);
            int sx = x0 < x1 ? 1 : -1;
            int sy = y0 < y1 ? 1 : -1;
            int err = dx - dy;

            int currX = x0;
            int currY = y0;

            while (true)
            {
                if (currX != x0 || currY != y0)
                {
                    Cell cell = from.ParentZone.GetCell(currX, currY);
                    if (cell != null) line.Add(cell);
                }
                if (currX == x1 && currY == y1) break;
                int e2 = 2 * err;
                if (e2 > -dy)
                {
                    err -= dy;
                    currX += sx;
                }
                if (e2 < dx)
                {
                    err += dx;
                    currY += sy;
                }
            }
            return line;
        }

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

        // ---- Reachable frontier (HANDOFF issue 43/44; AGENTS R2: the engine owns "what can I still explore?") ----
        // `unexplored_cells`, `nearest_unexplored_*` and `unexplored_centroid_*` count EVERY cell never marked explored,
        // including solid rock that can never be revealed, so Python chased the centroid of rock. A frontier is an explored,
        // walkable "access" cell that touches an unexplored cell. We export, per quadrant, the nearest access cells the ENGINE
        // pathfinder (AutoAct.TryFindPathStep) can actually route to, skipping cells the player has already stood on.
        // ---- Burrow progress (HANDOFF issue 45): the result of the last ATTACK_WALL swing, so Python can tell a tree that is
        // losing hit points from one that never will (no hit points, or damage that does nothing).
        private static int burrowSeq = 0;
        private static string lastBurrowJson = "null";

        private static string LastBurrowJson() { return "\"last_burrow\": " + lastBurrowJson + ","; }

        // ---- Ability use log (HANDOFF issue 52): what the last USE_ABILITY did to the ability's cooldown, so "it works" is
        // measured instead of assumed. Python (note_ability_use) turns it into memory/ability_stats.json.
        private static int abilityUseSeq = 0;
        private static string lastAbilityUseJson = "null";

        private static string LastAbilityUseJson() { return "\"last_ability_use\": " + lastAbilityUseJson + ","; }

        // Reads the live state of the player's ability with this engine command. found=false when the player has no such ability.
        private static void ReadAbilityState(GameObject player, string cmd, out bool found, out bool enabled, out bool usable, out int cooldown, out string label)
        {
            found = false; enabled = false; usable = false; cooldown = 0; label = "";
            try
            {
                var abilities = player.GetPart<ActivatedAbilities>();
                if (abilities == null || abilities.AbilityByGuid == null) return;
                foreach (var kvp in abilities.AbilityByGuid)
                {
                    var ab = kvp.Value;
                    if (ab == null || !string.Equals(ab.Command ?? "", cmd, StringComparison.OrdinalIgnoreCase)) continue;
                    found = true;
                    enabled = ab.Enabled;
                    usable = ab.IsUsable;
                    cooldown = ab.CooldownRounds > 0 ? ab.CooldownRounds : ab.Cooldown;
                    label = StripQudFormatting(ab.DisplayName ?? "") + (ab.ToggleState ? "|on" : "|off");   // "Lase (5 charges)" changes for charge abilities, the toggle state for toggles; neither moves the cooldown
                    return;
                }
            }
            catch { }
        }

        private static void RecordAbilityUse(string cmd, string dir, bool found, int cdBefore, int cdAfter, string labelBefore, string labelAfter, bool refused, string reason)
        {
            abilityUseSeq++;
            lastAbilityUseJson = "{\"seq\": " + abilityUseSeq + ", \"command\": \"" + EscapeJson(cmd) + "\", \"dir\": \"" + EscapeJson(dir ?? "") +
                "\", \"known\": " + (found ? "true" : "false") + ", \"cd_before\": " + cdBefore + ", \"cd_after\": " + cdAfter +
                ", \"fired\": " + ((!refused && (cdAfter > cdBefore || labelAfter != labelBefore)) ? "true" : "false") + ", \"refused\": " + (refused ? "true" : "false") +
                ", \"reason\": \"" + EscapeJson(reason ?? "") + "\"}";
        }

        // ---- Obstacles on an engine-planned path (HANDOFF issue 47) ----
        // The engine pathfinder routes THROUGH trees and plant walls (it expects the walker to hack through), but a step into an
        // occluding cell used to be refused here, so such a path always failed. If the blocker is a solid, ownerless, non-creature
        // object with hit points, attack it, and report the swing in last_burrow exactly like ATTACK_WALL does.
        private static bool TryBreakPathObstacle(GameObject player, Cell cell, string dir)
        {
            try
            {
                if (player == null || cell == null || cell.Objects == null) return false;
                if (IsSettlementZone(player.CurrentCell?.ParentZone)) return false;
                GameObject target = null;
                foreach (GameObject o in cell.Objects)
                {
                    if (o == null || o.IsPlayer() || o.Brain != null || o.HasPart("Brain") || o.HasPart("Door")) continue;
                    if (IsCompanion(o, player)) continue;
                    if (o.IsOwned() || !string.IsNullOrEmpty(o.Owner) || o.HasProperty("Owned") || o.HasProperty("OwnedBy")) continue;
                    var phys = o.GetPart<Physics>();
                    if (phys == null || !phys.Solid || !o.HasStat("Hitpoints")) continue;
                    target = o;
                    break;
                }
                if (target == null) return false;

                int energyBefore = player.Energy?.Value ?? 0;
                int hpBefore = 0, maxHp = 0;
                try { hpBefore = target.hitpoints; maxHp = target.baseHitpoints; } catch { }
                UnityEngine.Debug.Log($"[QudAI PATH_OBSTACLE] Breaking {target.DisplayNameOnly} ({dir}) at ({cell.X}, {cell.Y}) on the engine path");
                try { player.PerformMeleeAttack(target); }
                catch (Exception ex) { UnityEngine.Debug.LogError("[QudAI PATH_OBSTACLE Error] " + ex.ToString()); }

                int hpAfter = hpBefore;
                bool destroyed = false;
                try { hpAfter = target.hitpoints; } catch { }
                try { destroyed = hpAfter <= 0 || (cell.Objects != null && !cell.Objects.Contains(target)); } catch { }
                burrowSeq++;
                lastBurrowJson = "{\"seq\": " + burrowSeq + ", \"dir\": \"" + dir.ToUpper() + "\", \"name\": \"" + EscapeJson(StripQudFormatting(target.DisplayNameOnly ?? "")) +
                    "\", \"x\": " + cell.X + ", \"y\": " + cell.Y + ", \"has_hp\": true, \"hp_before\": " + hpBefore + ", \"hp_after\": " + hpAfter +
                    ", \"max_hp\": " + maxHp + ", \"destroyed\": " + (destroyed ? "true" : "false") + "}";
                UnityEngine.Debug.Log($"[QudAI PATH_OBSTACLE] {target.DisplayNameOnly}: HP {hpBefore} -> {hpAfter}/{maxHp}{(destroyed ? " (destroyed)" : "")}");

                if (player.Energy != null && player.Energy.Value >= energyBefore) player.UseEnergy(1000, "Attack");
                return true;
            }
            catch { return false; }
        }

        private const int FrontierPerQuadrant = 3;
        private const int FrontierPathChecksPerQuadrant = 6;
        private static readonly HashSet<string> frontierVisited = new HashSet<string>();

        private static string BuildFrontierJson(GameObject player, Cell currentCell, bool compute)
        {
            var entries = new List<string>();
            int frontierCells = 0;
            bool checkedFlag = false;
            try
            {
                Zone zone = currentCell?.ParentZone;
                if (zone != null && player != null)
                {
                    string zid = zone.ZoneID ?? "";
                    frontierVisited.Add(zid + ":" + currentCell.X + "," + currentCell.Y);
                    if (compute && !zone.IsWorldMap())
                    {
                        checkedFlag = true;
                        int px = currentCell.X, py = currentCell.Y;
                        var access = new Dictionary<int, Tuple<Cell, Cell>>();
                        for (int x = 0; x < zone.Width; x++)
                        {
                            for (int y = 0; y < zone.Height; y++)
                            {
                                Cell u = zone.GetCell(x, y);
                                if (u == null || u.Explored) continue;
                                for (int dx = -1; dx <= 1; dx++)
                                {
                                    for (int dy = -1; dy <= 1; dy++)
                                    {
                                        if (dx == 0 && dy == 0) continue;
                                        Cell a = zone.GetCell(x + dx, y + dy);
                                        if (a == null || !a.Explored || !a.IsPassable(player, false)) continue;
                                        if (frontierVisited.Contains(zid + ":" + a.X + "," + a.Y)) continue;
                                        int key = a.Y * 100 + a.X;
                                        if (!access.ContainsKey(key)) access[key] = Tuple.Create(a, u);
                                    }
                                }
                            }
                        }
                        frontierCells = access.Count;
                        var ordered = access.Values
                            .OrderBy(tp => Math.Max(Math.Abs(tp.Item1.X - px), Math.Abs(tp.Item1.Y - py)))
                            .ToList();
                        var perQuad = new Dictionary<string, int>();
                        var checksQuad = new Dictionary<string, int>();
                        foreach (var tp in ordered)
                        {
                            Cell a = tp.Item1;
                            string quad = (a.Y < zone.Height / 2 ? "N" : "S") + (a.X < zone.Width / 2 ? "W" : "E");
                            int have; perQuad.TryGetValue(quad, out have);
                            int tried; checksQuad.TryGetValue(quad, out tried);
                            if (have >= FrontierPerQuadrant || tried >= FrontierPathChecksPerQuadrant) continue;
                            checksQuad[quad] = tried + 1;
                            string step = null;
                            bool ok = false;
                            try { ok = AutoAct.TryFindPathStep(a, out step) && !string.IsNullOrEmpty(step) && step != "."; } catch { }
                            if (!ok) continue;
                            perQuad[quad] = have + 1;
                            int fdist = Math.Max(Math.Abs(a.X - px), Math.Abs(a.Y - py));
                            entries.Add("{\"q\": \"" + quad + "\", \"x\": " + a.X + ", \"y\": " + a.Y + ", \"ux\": " + tp.Item2.X + ", \"uy\": " + tp.Item2.Y + ", \"dist\": " + fdist + "}");
                        }
                    }
                }
            }
            catch { }
            return "\"frontier_checked\": " + (checkedFlag ? "true" : "false") + ", \"frontier_cells\": " + frontierCells + ", \"frontier_targets\": [" + string.Join(",", entries) + "],";
        }

        // ---- Food (HANDOFF issue 34): only real butcherable corpse ITEMS count. Living creatures carry a `Corpse` part
        // (it makes their corpse on death), so testing for `Corpse` flagged every adjacent animal and pet as a corpse.
        // A charred corpse (killed by Fire/Light, e.g. Lase) has no Butcherable part and is correctly excluded.
        private const int FoodSourceRadius = 15;

        public static bool IsButcherableCorpse(GameObject o)
        {
            if (o == null || o.IsPlayer() || o.Brain != null || o.HasPart("Brain")) return false;
            try { return o.HasPart("Butcherable"); }
            catch { return false; }
        }

        // ---- Fire safety (engine data only; see docs/DECISIONS.md "campfire next to dogthorn trees" and HANDOFF issue 30) ----
        private const int CampSafetyRadius = 2;

        public static bool IsObjectAflame(GameObject obj, GameObject player)
        {
            if (obj == null || obj == player) return false;
            try { return obj.IsAflame() || obj.HasEffect("Burning") || obj.HasPart("Campfire"); }
            catch { return false; }
        }

        // A creature that cannot move at all (engine `GameObject.IsMobile()`), e.g. the wall-dwelling jilted lover (`Brain Mobile="false"`,
        // `LivesOnWalls="true"`, 5 HP, kills only at radius 1). Such a creature rendered as a red wall segment and locked the brain into
        // combat mode at distance 3 (HANDOFF issue 57). Engine truth instead of a name list (R2/R3).
        public static bool IsImmobile(GameObject o)
        {
            try { return o != null && o.Brain != null && !o.IsMobile(); }
            catch { return false; }
        }

        // ---- Quest log export (HANDOFF issue 76, BACKLOG B2 stage 1): READ ONLY ----
        // The player's quests live in `The.Game.Quests` (name to Quest) and the finished ones in `The.Game.FinishedQuests`. Everything is read by reflection (field or
        // property, public or not) so a renamed member can only blank the export, never stop the mod from compiling or the game from loading.
        private const int MaxQuestsExport = 40;
        private const int MaxQuestStepsExport = 12;
        private const int MaxFinishedQuestsExport = 80;

        private static object QuestMember(object o, string name)
        {
            if (o == null) return null;
            try
            {
                BindingFlags bf = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static;
                Type t = o.GetType();
                FieldInfo f = t.GetField(name, bf);
                if (f != null) return f.GetValue(o);
                PropertyInfo p = t.GetProperty(name, bf);
                if (p != null && p.GetIndexParameters().Length == 0) return p.GetValue(o, null);
            }
            catch { }
            return null;
        }

        private static string QuestText(object o, string name, int max)
        {
            string s = "";
            try { s = StripQudFormatting(Convert.ToString(QuestMember(o, name)) ?? ""); } catch { }
            if (s.Length > max) s = s.Substring(0, max);
            return EscapeJson(s);
        }

        private static int QuestInt(object o, string name)
        {
            try { return Convert.ToInt32(QuestMember(o, name)); } catch { return 0; }
        }

        private static bool QuestBool(object o, string name)
        {
            try { return Convert.ToBoolean(QuestMember(o, name)); } catch { return false; }
        }

        private static int QuestStepFlag(object step, string flagName)
        {
            try
            {
                FieldInfo f = step.GetType().GetField(flagName, BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static | BindingFlags.Instance);
                return f != null ? Convert.ToInt32(f.GetValue(null)) : 0;
            }
            catch { return 0; }
        }

        // The items of a quest collection, by plain enumeration. IDictionary.Values and .Keys are NOT used: the game's own dictionary threw
        // NotSupportedException ("Specified method is not supported") from them (seen in game 2026-10-07). A KeyValuePair is unwrapped by QuestUnwrap/QuestKey.
        private static System.Collections.IEnumerable QuestElements(object coll)
        {
            if (coll == null || coll is string) return null;
            return coll as System.Collections.IEnumerable;
        }

        private static object QuestKey(object item)
        {
            try
            {
                if (item != null && item.GetType().Name.StartsWith("KeyValuePair")) return QuestMember(item, "Key");
            }
            catch { }
            return item;
        }

        private static string QuestCount(object coll)
        {
            try
            {
                object c = QuestMember(coll, "Count");
                return c == null ? "?" : Convert.ToString(c);
            }
            catch { return "?"; }
        }

        private static object QuestUnwrap(object item)
        {
            try
            {
                if (item != null && item.GetType().Name.StartsWith("KeyValuePair")) return QuestMember(item, "Value");
            }
            catch { }
            return item;
        }

        private static string lastQuestDiag = "";

        // One line in Player.log whenever what the export found changes (never every turn), so an empty `quests` can be explained from the log.
        private static void QuestDiag(string line)
        {
            try
            {
                if (line == lastQuestDiag) return;
                lastQuestDiag = line;
                UnityEngine.Debug.Log("[QudAI Quests] " + line);
            }
            catch { }
        }

        private static string BuildQuestsJson(out string finishedJson)
        {
            finishedJson = "[]";
            try
            {
                object game = The.Game;
                if (game == null) { QuestDiag("The.Game is null"); return "[]"; }
                var sb = new StringBuilder("[");
                int n = 0;
                object questsObj = QuestMember(game, "Quests");
                var questSeq = QuestElements(questsObj);
                QuestDiag("game=" + game.GetType().Name + " Quests=" + (questsObj == null ? "null" : questsObj.GetType().Name) + " sequence=" + (questSeq != null)
                    + " FinishedQuests=" + (QuestMember(game, "FinishedQuests") == null ? "null" : QuestMember(game, "FinishedQuests").GetType().Name)
                    + " count=" + QuestCount(questsObj));
                if (questSeq != null)
                {
                    foreach (object item in questSeq)
                    {
                        object q = QuestUnwrap(item);
                        if (q == null || n >= MaxQuestsExport) continue;
                        if (n > 0) sb.Append(",");
                        n++;
                        sb.Append("{\"id\": \"" + QuestText(q, "ID", 80) + "\", \"name\": \"" + QuestText(q, "Name", 120) + "\", \"level\": " + QuestInt(q, "Level")
                            + ", \"finished\": " + (QuestBool(q, "Finished") ? "true" : "false")
                            + ", \"giver\": \"" + QuestText(q, "QuestGiverName", 80) + "\", \"giver_place\": \"" + QuestText(q, "QuestGiverLocationName", 120)
                            + "\", \"giver_zone\": \"" + QuestText(q, "QuestGiverLocationZoneID", 80) + "\", \"steps\": [");
                        var stepSeq = QuestElements(QuestMember(q, "StepsByID"));
                        int k = 0;
                        if (stepSeq != null)
                        {
                            int finishedFlag = 0, failedFlag = 0, optionalFlag = 0, hiddenFlag = 0;
                            foreach (object stItem in stepSeq)
                            {
                                object st = QuestUnwrap(stItem);
                                if (st == null || k >= MaxQuestStepsExport) continue;
                                if (k == 0)
                                {
                                    finishedFlag = QuestStepFlag(st, "FLAG_FINISHED"); failedFlag = QuestStepFlag(st, "FLAG_FAILED");
                                    optionalFlag = QuestStepFlag(st, "FLAG_OPTIONAL"); hiddenFlag = QuestStepFlag(st, "FLAG_HIDDEN");
                                }
                                if (k > 0) sb.Append(",");
                                k++;
                                int flags = QuestInt(st, "Flags");
                                sb.Append("{\"name\": \"" + QuestText(st, "Name", 120) + "\", \"text\": \"" + QuestText(st, "Text", 240) + "\", \"xp\": " + QuestInt(st, "XP")
                                    + ", \"finished\": " + (finishedFlag != 0 && (flags & finishedFlag) != 0 ? "true" : "false")
                                    + ", \"failed\": " + (failedFlag != 0 && (flags & failedFlag) != 0 ? "true" : "false")
                                    + ", \"optional\": " + (optionalFlag != 0 && (flags & optionalFlag) != 0 ? "true" : "false")
                                    + ", \"hidden\": " + (hiddenFlag != 0 && (flags & hiddenFlag) != 0 ? "true" : "false") + "}");
                            }
                        }
                        sb.Append("]}");
                    }
                }
                sb.Append("]");
                var fin = new StringBuilder("[");
                int m = 0;
                object finishedObj = QuestMember(game, "FinishedQuests");
                System.Collections.IEnumerable finSeq = QuestElements(finishedObj);
                if (finSeq != null)
                {
                    foreach (object finItem in finSeq)
                    {
                        object key = QuestKey(finItem);
                        if (key == null || m >= MaxFinishedQuestsExport) continue;
                        if (m > 0) fin.Append(",");
                        m++;
                        fin.Append("\"" + EscapeJson(StripQudFormatting(Convert.ToString(key) ?? "")) + "\"");
                    }
                }
                fin.Append("]");
                finishedJson = fin.ToString();
                return sb.ToString();
            }
            catch (Exception e)
            {
                QuestDiag("export failed: " + e.GetType().Name + ": " + e.Message);
                return "[]";
            }
        }

        // ---- Steering around immobile hostiles (HANDOFF issue 69) ----
        // A rooted hostile such as the wall-dwelling jilted lover (5 HP, grabs at radius 1) cannot follow, but the engine's autoexplore and path steps walk straight past
        // it and into its reach. The engine's own `AvoidMovingNearby` part (a Weight that GetNavigationWeightEvent and GetAdjacentNavigationWeightEvent add to the
        // object's cell and every cell next to it; walls use the sibling AvoidMovingOnto at 40) makes the pathfinder prefer a detour while still allowing the route when
        // there is no other. Each immobile hostile gets the part once, and the cached navigation costs around it are flushed.
        private const int AvoidWeight = 40;
        private const int AvoidMaxNewPerTurn = 24;
        private static readonly HashSet<string> avoidDecidedIds = new HashSet<string>();
        private static int avoidTaggedTotal = 0;

        private static void TagImmobileHostilesForAvoidance(GameObject player, Zone zone)
        {
            try
            {
                if (player == null || zone == null || zone.IsWorldMap()) return;
                int added = 0;
                foreach (GameObject o in GetSafeZoneObjects(zone))
                {
                    if (o == null || o == player || o.CurrentCell == null) continue;
                    string id = o.ID;
                    if (string.IsNullOrEmpty(id) || avoidDecidedIds.Contains(id)) continue;
                    if (!IsImmobile(o)) continue;
                    if (IsCompanion(o, player) || !CheckIsEnemy(o, player)) continue;
                    avoidDecidedIds.Add(id);                       // one decision per object
                    if (o.HasPart("AvoidMovingNearby")) continue;
                    o.AddPart(new AvoidMovingNearby { Weight = AvoidWeight });
                    added++;
                    try
                    {
                        o.CurrentCell.FlushNavigationCache();
                        var adj = o.CurrentCell.GetLocalAdjacentCells();
                        if (adj != null) foreach (Cell a in adj) if (a != null) a.FlushNavigationCache();
                    }
                    catch { }
                    if (added >= AvoidMaxNewPerTurn) break;
                }
                if (added > 0)
                {
                    avoidTaggedTotal += added;
                    UnityEngine.Debug.Log("[QudAI Avoid] tagged " + added + " immobile hostile(s) for path avoidance (total " + avoidTaggedTotal + ")");
                }
            }
            catch { }
        }

        // ---- Inventory (HANDOFF issue 66, stage 2) ----
        // Export: every carried or worn item (natural weapons excluded) with its object id, so Python can score it (item_scoring.py) and name it in a command.
        // Commands: DROP_ITEMS:<id>,<id> (whole items, never equipped, never in a settlement or with hostiles near) and EQUIP_ITEM:<id> (the engine's own AutoEquip).
        // A drop mirrors what the engine's drop does (Inventory CommandDropObject: take it out of the pack, put it on the cell, mark DroppedByPlayer so autoget
        // never picks it up again) without its quantity popup, which the mod could not answer. Every step is verified and undone if it fails.
        private const int MaxInventoryExport = 90;
        private const int MaxDropsPerCommand = 5;
        private static int invActionSeq = 0;
        private static string lastInvActionJson = "null";

        private static string LastInvActionJson() { return "\"last_inventory_action\": " + lastInvActionJson + ","; }

        private static string BuildInventoryJson(GameObject player)
        {
            var entries = new List<string>();
            try
            {
                var items = new List<GameObject>();
                try { items.AddRange(player.GetInventory()); } catch { }
                try
                {
                    foreach (GameObject worn in player.GetEquippedObjects())
                        if (worn != null && !items.Contains(worn)) items.Add(worn);
                }
                catch { }
                foreach (GameObject it in items)
                {
                    if (it == null) continue;
                    try { if (it.HasPart("NaturalEquipment")) continue; } catch { }
                    string bp = it.Blueprint ?? "";
                    bool eq = false; try { eq = it.Equipped != null; } catch { }
                    int n = 1; try { n = it.Count; } catch { }
                    int w = 0; try { w = it.Weight; } catch { }
                    bool ident = true; try { ident = it.Understood(); } catch { }
                    entries.Add("{\"id\": \"" + EscapeJson(it.ID ?? "") + "\", \"blueprint\": \"" + EscapeJson(bp) + "\", \"name\": \"" +
                                EscapeJson(StripQudFormatting(it.DisplayNameOnly ?? bp)) + "\", \"count\": " + n + ", \"weight\": " + w +
                                ", \"equipped\": " + (eq ? "true" : "false") + ", \"identified\": " + (ident ? "true" : "false") + "}");
                    if (entries.Count >= MaxInventoryExport) break;
                }
            }
            catch { }
            return "[" + string.Join(",", entries) + "]";
        }

        private static void RecordInventoryAction(string kind, List<string> okNames, List<string> failed, GameObject player)
        {
            invActionSeq++;
            string zone = ""; int x = -1, y = -1;
            try { zone = player.CurrentCell.ParentZone.ZoneID ?? ""; x = player.CurrentCell.X; y = player.CurrentCell.Y; } catch { }
            lastInvActionJson = "{\"seq\": " + invActionSeq + ", \"kind\": \"" + kind + "\", \"ok\": [" + string.Join(",", okNames.Select(s => "\"" + EscapeJson(s) + "\"")) +
                                "], \"failed\": [" + string.Join(",", failed.Select(s => "\"" + EscapeJson(s) + "\"")) + "], \"zone\": \"" + EscapeJson(zone) + "\", \"x\": " + x + ", \"y\": " + y + "}";
            UnityEngine.Debug.Log("[QudAI Inventory] " + kind + " ok=" + okNames.Count + " failed=" + failed.Count);
        }

        private static GameObject FindInventoryItem(GameObject player, string id)
        {
            try
            {
                foreach (GameObject o in player.GetInventory())
                    if (o != null && o.ID == id) return o;
            }
            catch { }
            return null;
        }

        private static void ExecuteDropItems(GameObject player, string idList)
        {
            var ok = new List<string>(); var failed = new List<string>();
            try
            {
                Cell cell = player.CurrentCell;
                Zone zone = cell != null ? cell.ParentZone : null;
                bool refuse = cell == null || zone == null || zone.IsWorldMap() || IsSettlementZone(zone);
                try { if (player.AreHostilesNearby()) refuse = true; } catch { }
                var ids = (idList ?? "").Split(new char[] { ',' }, StringSplitOptions.RemoveEmptyEntries).Take(MaxDropsPerCommand).ToList();
                foreach (string raw in ids)
                {
                    string id = raw.Trim();
                    GameObject item = FindInventoryItem(player, id);
                    if (refuse) { failed.Add(id + ":refused here"); continue; }
                    if (item == null) { failed.Add(id + ":not in pack"); continue; }
                    bool worn = false; try { worn = item.Equipped != null; } catch { }
                    if (worn) { failed.Add(id + ":equipped"); continue; }
                    string name = StripQudFormatting(item.DisplayNameOnly ?? item.Blueprint ?? "");
                    try
                    {
                        item.RemoveFromContext(null);
                        cell.AddObject(item, NoStack: true);
                        try { item.SetIntProperty("DroppedByPlayer", 1); } catch { }
                        if (FindInventoryItem(player, id) == null) ok.Add(id + "|" + name);
                        else failed.Add(id + ":still in pack");
                    }
                    catch (Exception ex)
                    {
                        failed.Add(id + ":" + ex.GetType().Name);
                        try { if (item.CurrentCell == null && FindInventoryItem(player, id) == null) player.TakeObject(item); } catch { }   // never lose an item to a failed drop
                    }
                }
            }
            catch (Exception ex) { failed.Add("error:" + ex.GetType().Name); }
            RecordInventoryAction("drop", ok, failed, player);
        }

        private static void ExecuteEquipItem(GameObject player, string id)
        {
            var ok = new List<string>(); var failed = new List<string>();
            try
            {
                GameObject item = FindInventoryItem(player, (id ?? "").Trim());
                if (item == null) failed.Add(id + ":not in pack");
                else
                {
                    string name = StripQudFormatting(item.DisplayNameOnly ?? item.Blueprint ?? "");
                    bool done = false;
                    try { done = player.AutoEquip(item, true, false, true); } catch { }
                    bool worn = false; try { worn = item.Equipped != null; } catch { }
                    if (done || worn) ok.Add(id + "|" + name); else failed.Add(id + ":AutoEquip refused");
                }
            }
            catch (Exception ex) { failed.Add("error:" + ex.GetType().Name); }
            RecordInventoryAction("equip", ok, failed, player);
        }

        // ---- Ground equipment (HANDOFF issue 96, BACKLOG B16, human promotion 2026-10-09) ----
        // The loot step only takes what the engine's autoget policy accepts, which skips weapons and armor, so the gear that killed snapjaws drop stayed on the ground while a level 5
        // character still wore AV 1 and swung a 1d2 staff (Gen 27). Export: `ground_items`, unowned takeable armor, weapons and shields within GroundItemRadius, never one the player
        // dropped (DroppedByPlayer) or the loot step gave up on (AutoexploreSuppressed), never in a settlement. Command: TAKE_ITEM:<id> takes one from the player's cell or an adjacent one
        // and nothing else: Python decides whether it is an upgrade (the same scorer as the inventory) and the existing EQUIP_ITEM wears it.
        private const int GroundItemRadius = 10;
        private const int MaxGroundItems = 12;

        public static bool IsGroundEquipment(GameObject o, GameObject player)
        {
            try
            {
                if (o == null || o == player || o.IsPlayer() || o.CurrentCell == null) return false;
                if (o.HasPart("Brain") || o.HasPart("Mimic") || o.HasPart("Combat") || o.HasPart("NaturalEquipment")) return false;
                if (!(o.HasPart("Armor") || o.HasPart("MeleeWeapon") || o.HasPart("Shield") || o.HasPart("MissileWeapon"))) return false;
                if (o.IsOwned() || !string.IsNullOrEmpty(o.Owner)) return false;
                if (o.HasProperty("Owned") || o.HasProperty("OwnedBy")) return false;
                if (o.GetIntProperty("AutoexploreSuppressed", 0) > 0 || o.GetIntProperty("DroppedByPlayer", 0) > 0) return false;
                var phys = o.GetPart<Physics>();
                if (phys == null || !phys.Takeable) return false;
                string bp = o.Blueprint ?? "";
                if (bp.EndsWith("Corpse") || o.HasPart("Door") || o.HasPart("StairsUp") || o.HasPart("StairsDown")) return false;
                return true;
            }
            catch { return false; }
        }

        private static string BuildGroundItemsJson(GameObject player, Zone zone, Cell here, bool swimming)
        {
            var entries = new List<Tuple<int, string>>();
            try
            {
                if (zone == null || here == null || swimming || zone.IsWorldMap() || IsSettlementZone(zone)) return "[]";
                foreach (GameObject o in GetSafeZoneObjects(zone))
                {
                    if (o == null || o.CurrentCell == null) continue;
                    int d = Math.Max(Math.Abs(o.CurrentCell.X - here.X), Math.Abs(o.CurrentCell.Y - here.Y));
                    if (d > GroundItemRadius) continue;
                    if (!IsGroundEquipment(o, player)) continue;
                    if (!LootWeightOk(o, player)) continue;
                    string bp = o.Blueprint ?? "";
                    int w = 0; try { var ph = o.GetPart<Physics>(); w = ph != null ? ph.Weight : 0; } catch { }
                    bool ident = true; try { ident = o.Understood(); } catch { }
                    entries.Add(Tuple.Create(d, "{\"id\": \"" + EscapeJson(o.ID ?? "") + "\", \"blueprint\": \"" + EscapeJson(bp) + "\", \"name\": \"" +
                        EscapeJson(StripQudFormatting(o.DisplayNameOnly ?? bp)) + "\", \"dist\": " + d + ", \"tx\": " + o.CurrentCell.X + ", \"ty\": " + o.CurrentCell.Y +
                        ", \"weight\": " + w + ", \"identified\": " + (ident ? "true" : "false") + "}"));
                }
            }
            catch { }
            return "[" + string.Join(",", entries.OrderBy(e => e.Item1).Take(MaxGroundItems).Select(e => e.Item2)) + "]";
        }

        private static void ExecuteTakeItem(GameObject player, string id)
        {
            var ok = new List<string>(); var failed = new List<string>();
            try
            {
                id = (id ?? "").Trim();
                Cell cell = player.CurrentCell;
                Zone zone = cell != null ? cell.ParentZone : null;
                bool refuse = cell == null || zone == null || zone.IsWorldMap() || IsSettlementZone(zone);
                try { if (player.AreHostilesNearby()) refuse = true; } catch { }
                if (refuse) failed.Add(id + ":refused here");
                else
                {
                    GameObject item = null;
                    var cells = new List<Cell> { cell };
                    var adj = cell.GetLocalAdjacentCells();
                    if (adj != null) cells.AddRange(adj);
                    foreach (Cell c in cells)
                    {
                        if (c == null || c.Objects == null) continue;
                        item = c.Objects.FirstOrDefault(o => o != null && o.ID == id);
                        if (item != null) break;
                    }
                    if (item == null) failed.Add(id + ":not within reach");
                    else if (!IsGroundEquipment(item, player)) failed.Add(id + ":not takeable equipment");
                    else if (!LootWeightOk(item, player)) failed.Add(id + ":too heavy");
                    else
                    {
                        string name = StripQudFormatting(item.DisplayNameOnly ?? item.Blueprint ?? "");
                        bool taken = false;
                        try { taken = player.TakeObject(item); } catch { }
                        if (taken) ok.Add(id + "|" + name);
                        else
                        {
                            try { item.SetIntProperty("AutoexploreSuppressed", 1); } catch { }
                            failed.Add(id + ":TakeObject refused");
                        }
                    }
                }
            }
            catch (Exception ex) { failed.Add("error:" + ex.GetType().Name); }
            RecordInventoryAction("take", ok, failed, player);
        }

        // ---- Loot (HANDOFF issue 59, BACKLOG B6, human decision 2026-10-06: "take everything unowned") ----
        // Engine facts (ENGINE_INTERNALS 14.9): the game's own autoexplore treats unowned, unopened containers as goals
        // (GameObject.ShouldAutoexploreAsChest) and ground items through CanAutoget/ShouldAutoget. Opening a chest with the "Open"
        // event raises a modal trade screen (Container.AttemptOpen) that the mod cannot answer, so containers are emptied directly from
        // their Inventory part instead. Never in settlements, never anything owned (AGENTS R7).
        private const int LootRadius = 14;
        private const int LootMaxActionsPerZone = 80;
        private static int lootSeq = 0;
        private static string lastLootJson = "null";
        private static string lootZoneId = "";
        private static int lootActionsInZone = 0;

        private static string LastLootJson() { return "\"last_loot\": " + lastLootJson + ","; }

        private static bool LootWeightOk(GameObject o, GameObject player)
        {
            try
            {
                var phys = o.GetPart<Physics>();
                int w = phys != null ? phys.Weight : 0;
                if (w > 25) return false;
                return player.GetCarriedWeight() + w <= player.GetMaxCarriedWeight() - 10;
            }
            catch { return true; }
        }

        // "item" (a ground item the engine would autoget), "chest" (an unowned container that still holds something) or null.
        public static string LootKind(GameObject o, GameObject player)
        {
            try
            {
                if (o == null || o == player || o.IsPlayer() || o.CurrentCell == null) return null;
                if (o.HasPart("Brain") || o.HasPart("Mimic") || o.HasPart("Combat")) return null;
                if (o.IsOwned() || !string.IsNullOrEmpty(o.Owner)) return null;
                if (o.HasProperty("Owned") || o.HasProperty("OwnedBy")) return null;
                if (o.GetIntProperty("AutoexploreSuppressed", 0) > 0) return null;
                if (o.ShouldAutoexploreAsChest())
                {
                    var inv = o.GetPart<Inventory>();
                    var contents = inv != null ? inv.GetObjectsDirect() : null;
                    return (contents != null && contents.Count > 0) ? "chest" : null;
                }
                string bp = o.Blueprint ?? "";
                if (bp.EndsWith("Corpse") || IsButcherableCorpse(o)) return null;
                if (o.HasPart("Door") || o.HasPart("StairsUp") || o.HasPart("StairsDown")) return null;
                if (!o.CanAutoget(true) || !o.ShouldAutoget()) return null;
                if (!LootWeightOk(o, player)) return null;
                return "item";
            }
            catch { return null; }
        }

        private static void RecordLoot(string kind, string name, int count, int left)
        {
            lootSeq++;
            lastLootJson = "{\"seq\": " + lootSeq + ", \"kind\": \"" + kind + "\", \"name\": \"" + EscapeJson(name) + "\", \"count\": " + count + ", \"left\": " + left + "}";
            UnityEngine.Debug.Log("[QudAI Loot] " + kind + " '" + name + "': took " + count + ", left " + left);
        }

        // Takes one unowned item, or empties one unowned chest, on the player's cell or an adjacent one. True when a turn's worth of work was done.
        public static bool TryLootNearby(GameObject player)
        {
            try
            {
                Cell cell = player != null ? player.CurrentCell : null;
                Zone zone = cell != null ? cell.ParentZone : null;
                if (cell == null || zone == null || zone.IsWorldMap() || IsSettlementZone(zone)) return false;
                try { if (player.AreHostilesNearby()) return false; } catch { }
                string zid = zone.ZoneID ?? "";
                if (zid != lootZoneId) { lootZoneId = zid; lootActionsInZone = 0; }
                if (lootActionsInZone >= LootMaxActionsPerZone) return false;

                var cells = new List<Cell> { cell };
                var adj = cell.GetLocalAdjacentCells();
                if (adj != null) cells.AddRange(adj);
                foreach (Cell c in cells)
                {
                    if (c == null || c.Objects == null) continue;
                    foreach (GameObject o in c.Objects.ToList())
                    {
                        string kind = LootKind(o, player);
                        if (kind == null) continue;
                        string name = StripQudFormatting(o.DisplayNameOnly ?? o.Blueprint ?? "");
                        lootActionsInZone++;
                        if (kind == "item")
                        {
                            bool ok = false;
                            try { ok = player.TakeObject(o); } catch { }
                            if (!ok)
                            {
                                try { o.SetIntProperty("AutoexploreSuppressed", 1); } catch { }
                                continue;
                            }
                            try { player.FireEvent(Event.New("CommandAutoEquip")); } catch { }
                            RecordLoot("item", name, 1, 0);
                            return true;
                        }
                        int taken = 0, left = 0;
                        var contents = o.GetPart<Inventory>().GetObjectsDirect().ToList();
                        foreach (GameObject it in contents)
                        {
                            bool ok = false;
                            if (LootWeightOk(it, player)) { try { ok = player.TakeObject(it); } catch { } }
                            if (ok) taken++; else left++;
                        }
                        try { o.SetIntProperty("Autoexplored", 1); } catch { }
                        try { o.SetIntProperty("AutoexploreSuppressed", 1); } catch { }
                        if (taken > 0) { try { player.FireEvent(Event.New("CommandAutoEquip")); } catch { } }
                        RecordLoot("chest", name, taken, left);
                        return true;
                    }
                }
            }
            catch { }
            return false;
        }

        // Chance (percent) that a dead creature leaves a corpse at all (Corpse.CorpseChance); 0 when it has no Corpse part.
        // Fire and Light damage replace it by a burnt, non-butcherable one (ENGINE_INTERNALS 12.1b). Read by reflection so the
        // mod does not depend on the field's declared type. Python only learns whether food is at stake, not any engine rule.
        public static int CorpseChanceOf(GameObject o)
        {
            try
            {
                var part = o != null ? o.GetPart("Corpse") : null;
                if (part == null) return 0;
                var f = part.GetType().GetField("CorpseChance");
                return f == null ? 0 : Convert.ToInt32(f.GetValue(part));
            }
            catch { return 0; }
        }

        public static bool IsOnFire(GameObject player)
        {
            if (player == null) return false;
            try { return player.IsAflame() || player.HasEffect("Burning"); }
            catch { return false; }
        }

        // Plants burn (Physics.Category "Plants": trees, grass, vines). Creatures are never counted as terrain.
        private static bool IsFlammableTerrainObject(GameObject obj)
        {
            if (obj == null || obj.IsPlayer() || obj.Brain != null || obj.HasPart("Brain")) return false;
            try
            {
                var phys = obj.GetPart<Physics>();
                return phys != null && string.Equals(phys.Category, "Plants", StringComparison.OrdinalIgnoreCase);
            }
            catch { return false; }
        }

        // A campfire ignites flammable neighbors. Unsafe if anything within CampSafetyRadius is a plant or already burning.
        public static bool IsCampSpotSafe(GameObject player)
        {
            try
            {
                Cell center = player?.CurrentCell;
                Zone zone = center?.ParentZone;
                if (zone == null) return true;
                for (int dx = -CampSafetyRadius; dx <= CampSafetyRadius; dx++)
                {
                    for (int dy = -CampSafetyRadius; dy <= CampSafetyRadius; dy++)
                    {
                        Cell c = zone.GetCell(center.X + dx, center.Y + dy);
                        if (c?.Objects == null) continue;
                        foreach (GameObject o in c.Objects)
                        {
                            if (o == null) continue;
                            if (IsObjectAflame(o, player) || IsFlammableTerrainObject(o)) return false;
                        }
                    }
                }
            }
            catch { }
            return true;
        }

        // GameObject.IsAlive is ORGANIC life: (IsCreature or LivePlant or LiveFungus or LiveAnimal) and IsOrganic (decoded from the engine, ENGINE_INTERNALS 14.22). A turret, a robot
        // or a golem is "not alive" although it acts and can be shot. Where the question is "is it still there and can it be hit", ask for hit points instead.
        private static bool IsStanding(GameObject o)
        {
            try { return o != null && o.hitpoints > 0; }
            catch { return false; }
        }

        // A peaceful person who restocks and trades, gives reputation or offers quests: never a recruit. `ConversationScript` cannot tell them from an animal: 814 of the 845
        // creatures in the game data carry one (a default per species), but only about 120 have GivesRep or GenericInventoryRestocker (data/creatures.json flags gives_rep,
        // restocks), and quest givers carry the properties found in the engine's quest code.
        private static bool IsServiceNpc(GameObject obj)
        {
            try
            {
                return obj.HasPart("GivesRep") || obj.HasPart("GenericInventoryRestocker") || obj.HasProperty("GivesDynamicQuest") || obj.HasProperty("NamedVillager") || obj.HasProperty("ParticipantVillager");
            }
            catch { return false; }
        }

        // Diagnostic for "the engine finds no step to this cell" (HANDOFF issue 92: known stairs down at (73, 13) could not be routed to although a route exists).
        // One line per target in Player.log: `[QudAI PathDiag]` with the target cell, its eight neighbours and the player's cell and neighbours. Legend per cell:
        // x,y:  E explored / u unexplored,  P passable (Cell.IsPassable for the player) / x not,  S solid,  w wading-depth liquid,  W swimming-depth liquid,
        // ! dangerous open liquid,  #n the engine's navigation weight for the player (GetNavigationWeightFor). Never acts, never throws, at most 40 lines per game session.
        private static readonly HashSet<string> pathDiagSeen = new HashSet<string>();
        private static readonly string[] pathDiagDirs = new string[] { "N", "NE", "E", "SE", "S", "SW", "W", "NW" };

        private static string PathDiagCell(Cell c, GameObject player)
        {
            if (c == null) return "none";
            StringBuilder sb = new StringBuilder();
            try { sb.Append(c.X).Append(',').Append(c.Y).Append(':'); } catch { }
            try { sb.Append(c.IsExplored() ? "E" : "u"); } catch { sb.Append("?"); }
            try { sb.Append(c.IsPassable(player, false) ? "P" : "x"); } catch { sb.Append("?"); }
            try { if (c.IsSolid()) sb.Append("S"); } catch { }
            try { if (c.HasWadingDepthLiquid()) sb.Append("w"); } catch { }
            try { if (c.HasSwimmingDepthLiquid()) sb.Append("W"); } catch { }
            try { if (c.GetDangerousOpenLiquidVolume() != null) sb.Append("!"); } catch { }
            try { sb.Append("#").Append(c.GetNavigationWeightFor(player, false, false, false, false, false)); } catch { }
            return sb.ToString();
        }

        private static void LogPathDiag(GameObject player, Cell target)
        {
            try
            {
                if (target == null || player == null) return;
                string zid = target.ParentZone != null ? target.ParentZone.ZoneID : "?";
                string key = zid + "|" + target.X + "," + target.Y;
                if (pathDiagSeen.Count >= 40 || !pathDiagSeen.Add(key)) return;
                StringBuilder sb = new StringBuilder();
                sb.Append("[QudAI PathDiag] no engine step to ").Append(target.X).Append(',').Append(target.Y).Append(" in ").Append(zid);
                sb.Append(" | target ").Append(PathDiagCell(target, player)).Append(" | around target");
                foreach (string d in pathDiagDirs)
                {
                    Cell n = null;
                    try { n = target.GetCellFromDirection(d, false); } catch { }
                    sb.Append(" [").Append(d).Append(' ').Append(PathDiagCell(n, player)).Append(']');
                }
                Cell pc = player.CurrentCell;
                sb.Append(" | player ").Append(PathDiagCell(pc, player)).Append(" | around player");
                foreach (string d in pathDiagDirs)
                {
                    Cell n = null;
                    try { if (pc != null) n = pc.GetCellFromDirection(d, false); } catch { }
                    sb.Append(" [").Append(d).Append(' ').Append(PathDiagCell(n, player)).Append(']');
                }
                UnityEngine.Debug.Log(sb.ToString());
            }
            catch { }
        }

        public static bool IsCompanion(GameObject obj, GameObject player)
        {
            if (obj == null || player == null || obj == player || obj.IsPlayer() || !IsStanding(obj)) return false;
            try
            {
                // 0. Registered companion ID cache. IDs are only added after a real engine check below. Never cache by display
                //    name: one recruited "baboon" would make every baboon a companion.
                if (!string.IsNullOrEmpty(obj.ID) && RegisteredCompanionIds.Contains(obj.ID))
                    return true;

                // 1. Direct effect checks (Proselytize, Beguile, Rebuke, Love)
                if (obj.HasEffect("Proselytized") || obj.HasEffect("Beguiled") || obj.HasEffect("Rebuked") || obj.HasEffect("Lovesick") || obj.HasEffect("LoveTonic"))
                {
                    if (!string.IsNullOrEmpty(obj.ID)) RegisteredCompanionIds.Add(obj.ID);
                    return true;
                }

                // 2. Direct AI part checks on creature
                if (obj.HasPart("AllyProselytize") || obj.HasPart("AllyBeguile") || obj.HasPart("AllyRebuke") || obj.HasPart("AllyPet") || obj.HasPart("AllyClone"))
                {
                    if (!string.IsNullOrEmpty(obj.ID)) RegisteredCompanionIds.Add(obj.ID);
                    return true;
                }

                // 3. Brain leader checks
                var brain = obj.Brain ?? obj.GetPart<Brain>();
                if (brain != null)
                {
                    if (brain.PartyLeader == player)
                    {
                        if (!string.IsNullOrEmpty(obj.ID)) RegisteredCompanionIds.Add(obj.ID);
                        return true;
                    }
                    if (brain.PartyLeader != null && (brain.PartyLeader.IsPlayer() || brain.PartyLeader.ID == player.ID))
                    {
                        if (!string.IsNullOrEmpty(obj.ID)) RegisteredCompanionIds.Add(obj.ID);
                        return true;
                    }
                }

                // 4. Engine leader and alliance methods
                if (obj.IsLedBy(player))
                {
                    if (!string.IsNullOrEmpty(obj.ID)) RegisteredCompanionIds.Add(obj.ID);
                    return true;
                }

                try
                {
                    var comps = player.GetCompanions();
                    if (comps != null && comps.Contains(obj))
                    {
                        if (!string.IsNullOrEmpty(obj.ID)) RegisteredCompanionIds.Add(obj.ID);
                        return true;
                    }
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
            if (obj.HasPart("Plant") || obj.HasPart("Fungus") || obj.HasPart("Robot")) return false;
            try { if (IsServiceNpc(obj) && !obj.IsHostileTowards(player)) return false; } catch { }       // shopkeepers, quest givers and reputation NPCs stay where they are (HANDOFF issue 79)
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

        private static readonly HashSet<string> turretDiagSeen = new HashSet<string>();

        // A turret by the engine's own tag, by the tag's value, or by blueprint name (the tinker robot that PLACES turrets is not one). The first real run of the turret doctrine
        // (HANDOFF issue 77, Gen 24) showed `HasTag("Turret")` alone was not enough: the turret stayed is_enemy false, so the Lase had "target none". One log line per blueprint
        // says what each test answered, so the cause can be read from Player.log.
        private static bool IsTurretObject(GameObject obj)
        {
            try
            {
                string bp = obj.Blueprint ?? "";
                bool byTag = false, byValue = false;
                try { byTag = obj.HasTag("Turret"); } catch { }
                try { byValue = obj.GetTag("Turret", null) != null; } catch { }
                bool byName = bp.IndexOf("Turret", StringComparison.OrdinalIgnoreCase) >= 0 && bp.IndexOf("Tinker", StringComparison.OrdinalIgnoreCase) < 0;
                if (bp.IndexOf("Turret", StringComparison.OrdinalIgnoreCase) >= 0 && turretDiagSeen.Add(bp))
                {
                    bool alive = false; int thp = -1;
                    try { alive = obj.IsAlive; } catch { }
                    try { thp = obj.hitpoints; } catch { }
                    UnityEngine.Debug.Log("[QudAI Turret] " + bp + ": HasTag=" + byTag + " GetTag=" + byValue + " byName=" + byName + " IsAlive=" + alive + " hitpoints=" + thp);
                }
                return byTag || byValue || byName;
            }
            catch { return false; }
        }

        public static bool CheckIsEnemy(GameObject obj, GameObject player)
        {
            if (obj == null || player == null || obj == player || obj.IsPlayer()) return false;

            // A turret is decided FIRST, before the IsAlive and corpse checks: the second game run of the turret doctrine (Gen 25) still listed it is_enemy false and logged no
            // [QudAI Turret] line, so the test was never reached; an inanimate turret may well fail the IsAlive check above. It is an enemy while it has hit points and is not
            // the player's own (a placed turret has a party leader: IsCompanion).
            if (IsTurretObject(obj))
            {
                int turretHp = 1;
                try { turretHp = obj.hitpoints; } catch { }
                if (turretHp > 0 && !IsCompanion(obj, player)) return true;
            }

            if (!IsStanding(obj)) return false;          // hit points left, NOT IsAlive: that is organic life, and a hostile robot, golem or turret is "not alive" (HANDOFF issue 77)
            if (obj.Blueprint != null && obj.Blueprint.EndsWith("Corpse")) return false;

            try
            {
                // 0. ABSOLUTE COMPANION CHECK: If this entity is a companion or led by the player, it is NEVER an enemy!
                if (IsCompanion(obj, player)) return false;

                // 0b. Turrets (blueprint tag "Turret": security, rifle and tinker turrets) fire at the player although their Brain says Hostile="false", so the engine tests
                // below can answer "not an enemy" while one kills him (HANDOFF issue 77: a musket turret listed with is_enemy false killed a level 3 character), and the
                // ability targeting, which looks for the nearest enemy, would then find nothing to shoot. A turret the player placed is a companion and returned above.
                if (IsTurretObject(obj)) return true;

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

        private static bool patchCheckDone = false;

        // Asks Harmony which of this assembly's [HarmonyPatch] classes actually have a prefix/postfix applied.
        // Expected set = reflection over the assembly (single source of truth). Never throws, runs once.
        // If PlayerTurn itself failed to patch, Prefix never runs and the "PlayerTurn patch ACTIVE" line is absent.
        private static void RunPatchSelfCheck()
        {
            if (patchCheckDone) return;
            patchCheckDone = true;
            try
            {
                UnityEngine.Debug.Log("[QudAI] PlayerTurn patch ACTIVE");
                var patchedMethods = Harmony.GetAllPatchedMethods()?.ToList() ?? new List<MethodBase>();
                int applied = 0, expected = 0;
                foreach (Type t in typeof(AIPlayerTurnPatch).Assembly.GetTypes())
                {
                    var attr = t.GetCustomAttributes(typeof(HarmonyPatch), false).Cast<HarmonyPatch>().FirstOrDefault();
                    if (attr == null || attr.info == null) continue;
                    expected++;
                    string label = $"{attr.info.declaringType?.Name}.{attr.info.methodName}";
                    bool found = false;
                    foreach (MethodBase m in patchedMethods)
                    {
                        var info = Harmony.GetPatchInfo(m);
                        if (info == null) continue;
                        var all = info.Prefixes.Concat(info.Postfixes).Concat(info.Transpilers).Concat(info.Finalizers);
                        if (all.Any(p => p.PatchMethod != null && p.PatchMethod.DeclaringType == t)) { found = true; break; }
                    }
                    if (found) { applied++; UnityEngine.Debug.Log($"[QudAI] Patched: {label}"); }
                    else UnityEngine.Debug.Log($"[QudAI] PATCH MISSING: {label}");
                }
                UnityEngine.Debug.Log($"[QudAI] Patch check: {applied}/{expected} applied");
            }
            catch (Exception ex)
            {
                UnityEngine.Debug.Log($"[QudAI] Patch check failed: {ex.Message}");
            }
        }

        // Low-health warning ("Your health has dropped below 40%!" press-space popup, XRLCore.PlayerTurn and
        // TerrainTravel, gated by the static int XRL.Core.Globals.HPWarningThreshold, filled from the game option
        // OptionDisplayHPWarning, default "40%"). It blocks automation, so the threshold is zeroed while the AI is
        // engaged and the player's own value is restored when it is paused (HANDOFF issue 40).
        private static int hpWarningOriginal = -1;

        private static void SetHpWarningSuppressed(bool suppress)
        {
            try
            {
                if (suppress)
                {
                    if (XRL.Core.Globals.HPWarningThreshold != 0)
                    {
                        if (hpWarningOriginal < 0) hpWarningOriginal = XRL.Core.Globals.HPWarningThreshold;
                        XRL.Core.Globals.HPWarningThreshold = 0;
                    }
                }
                else if (hpWarningOriginal >= 0)
                {
                    XRL.Core.Globals.HPWarningThreshold = hpWarningOriginal;
                    hpWarningOriginal = -1;
                }
            }
            catch { }
        }

        public static bool Prefix()
        {
            try
            {
                RunPatchSelfCheck();
                UnityEngine.Application.runInBackground = true;

                if (!File.Exists(FlagFile) || !UnityEngine.Application.isPlaying)
                {
                    try { Popup.Suppress = false; } catch { }
                    SetHpWarningSuppressed(false);
                    return true;
                }

                // AI is active: suppress all blocking popups and ensure engine doesn't wait on UI thread
                try { Popup.Suppress = true; } catch { }
                SetHpWarningSuppressed(true);
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

                // R4: every command costs a turn. If a command returned without spending energy,
                // spend one here so the game does not re-export an identical state forever.
                int energyBefore = player.Energy?.Value ?? 0;
                ExecuteCommand(player, action);

                // ACTIVATE_SPRINT is intentionally free when the sprint starts (it only spends energy on failure).
                bool exempt = string.Equals(action?.Trim(), "ACTIVATE_SPRINT", StringComparison.OrdinalIgnoreCase);
                if (!exempt && player.Energy != null && player.Energy.Value >= energyBefore)
                {
                    UnityEngine.Debug.LogWarning($"[QudAI EnergyGuard] '{action}' spent no energy; passing a turn.");
                    player.UseEnergy(1000, "Pass");
                }

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
                    isAutoexploreStuck = false;
                    lastUnexploredCellCount = 0;
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
                                if (IsButcherableCorpse(o))
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
                    canMakeCamp = !isSwimming && (hasCampAbility || player.HasSkill("Survival_Camp") || player.HasSkill("CookingAndGathering")) && !hostilesNearby && !(currentCell?.ParentZone?.IsWorldMap() ?? false) && IsCampSpotSafe(player);
                }
                catch { }

                bool canCook = !isSwimming && campfireNearby && (player.HasSkill("CookingAndGathering") || foodCount > 0);
                var foodSourceEntries = new List<string>();
                try
                {
                    Zone fsZone = currentCell?.ParentZone;
                    if (fsZone != null && !isSwimming)
                    {
                        var fsFound = new List<Tuple<int, string>>();
                        foreach (GameObject fsObj in GetSafeZoneObjects(fsZone))
                        {
                            if (fsObj == null || fsObj.IsPlayer() || fsObj.CurrentCell == null) continue;
                            string fsKind = IsButcherableCorpse(fsObj) ? "corpse" : (fsObj.HasPart("Harvestable") ? "plant" : null);
                            if (fsKind == null) continue;
                            int fsDist = Math.Max(Math.Abs(fsObj.CurrentCell.X - currentCell.X), Math.Abs(fsObj.CurrentCell.Y - currentCell.Y));
                            if (fsDist > FoodSourceRadius) continue;
                            string fsName = EscapeJson(StripQudFormatting(fsObj.DisplayNameOnly ?? fsObj.Blueprint ?? ""));
                            string fsEntry = "{\"kind\": \"" + fsKind + "\", \"name\": \"" + fsName + "\", \"tx\": " + fsObj.CurrentCell.X + ", \"ty\": " + fsObj.CurrentCell.Y + ", \"dist\": " + fsDist + "}";
                            fsFound.Add(Tuple.Create((fsKind == "corpse" ? 0 : 1000) + fsDist, fsEntry));
                        }
                        foreach (var fsItem in fsFound.OrderBy(fsKey => fsKey.Item1).Take(8)) foodSourceEntries.Add(fsItem.Item2);
                    }
                }
                catch { }
                var lootSourceEntries = new List<string>();
                try
                {
                    Zone lsZone = currentCell?.ParentZone;
                    if (lsZone != null && !isSwimming && !lsZone.IsWorldMap() && !IsSettlementZone(lsZone))
                    {
                        var lsFound = new List<Tuple<int, string>>();
                        foreach (GameObject lsObj in GetSafeZoneObjects(lsZone))
                        {
                            if (lsObj == null || lsObj.CurrentCell == null) continue;
                            int lsDist = Math.Max(Math.Abs(lsObj.CurrentCell.X - currentCell.X), Math.Abs(lsObj.CurrentCell.Y - currentCell.Y));
                            if (lsDist > LootRadius) continue;
                            string lsKind = LootKind(lsObj, player);
                            if (lsKind == null) continue;
                            string lsName = EscapeJson(StripQudFormatting(lsObj.DisplayNameOnly ?? lsObj.Blueprint ?? ""));
                            lsFound.Add(Tuple.Create(lsDist, "{\"kind\": \"" + lsKind + "\", \"name\": \"" + lsName + "\", \"tx\": " + lsObj.CurrentCell.X + ", \"ty\": " + lsObj.CurrentCell.Y + ", \"dist\": " + lsDist + "}"));
                        }
                        foreach (var lsItem in lsFound.OrderBy(lsKey => lsKey.Item1).Take(8)) lootSourceEntries.Add(lsItem.Item2);
                    }
                }
                catch { }
                TagImmobileHostilesForAvoidance(player, currentCell?.ParentZone);
                string finishedQuestsJson;
                string questsJson = BuildQuestsJson(out finishedQuestsJson);
                string inventoryJson = BuildInventoryJson(player);
                string groundItemsJson = BuildGroundItemsJson(player, currentCell?.ParentZone, currentCell, isSwimming);
                int carryNow = 0, carryMax = 0;
                try { carryNow = player.GetCarriedWeight(); carryMax = player.GetMaxCarriedWeight(); } catch { }
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

                // What the combat score (creature_threat.py) needs from us: armour and dodge as the engine computes them now, and what our main hand does.
                // Penetration: MeleeWeapon.GetNormalPenetration is the attacker's strength modifier and weapon bonus, the number the engine itself passes to the penetration roll.
                int statAV = player.Stat("AV", 0);
                int statDV = player.Stat("DV", 0);
                string meleeDamage = "";
                int meleePen = 0, meleeHit = 0;
                string meleeName = "";
                try
                {
                    GameObject mainHand = player.GetPrimaryWeapon();
                    var mw = mainHand != null ? mainHand.GetPart<MeleeWeapon>() : null;
                    if (mw != null)
                    {
                        meleeName = mainHand.DisplayNameOnlyStripped ?? "";
                        meleeDamage = mw.BaseDamage ?? "";
                        meleeHit = mw.HitBonus;
                        meleePen = mw.GetNormalPenetration(player);
                    }
                }
                catch (Exception ex) { UnityEngine.Debug.Log("[QudAI Combat] main weapon read failed: " + ex.Message); }

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
                sb.Append($"\"av\": {statAV}, \"dv\": {statDV},");
                sb.Append($"\"melee\": {{\"weapon\": \"{EscapeJson(meleeName)}\", \"damage\": \"{EscapeJson(meleeDamage)}\", \"penetration\": {meleePen}, \"hit_bonus\": {meleeHit}}},");
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
                sb.Append($"\"food_sources\": [{string.Join(",", foodSourceEntries)}],");
                sb.Append($"\"loot_sources\": [{string.Join(",", lootSourceEntries)}],");
                sb.Append($"\"ground_items\": {groundItemsJson},");
                sb.Append($"\"inventory\": {inventoryJson},");
                sb.Append($"\"carry_weight\": {carryNow}, \"max_carry_weight\": {carryMax},");
                sb.Append($"\"avoid_tagged\": {avoidTaggedTotal},");
                sb.Append($"\"quests\": {questsJson}, \"finished_quests\": {finishedQuestsJson},");
                sb.Append($"\"harvestable_nearby\": {harvestableNearby},");
                sb.Append($"\"campfire_nearby\": {(campfireNearby ? "true" : "false")},");
                sb.Append($"\"can_make_camp\": {(canMakeCamp ? "true" : "false")},");
                sb.Append($"\"can_cook\": {(canCook ? "true" : "false")},");
                sb.Append($"\"can_butcher\": {(canButcher ? "true" : "false")},");
                sb.Append($"\"can_harvest\": {(canHarvest ? "true" : "false")},");
                sb.Append($"\"is_swimming\": {(isSwimming ? "true" : "false")},");
                sb.Append($"\"is_on_fire\": {(IsOnFire(player) ? "true" : "false")},");
                sb.Append($"\"effects\": [{string.Join(",", effectStrs)}],");
                sb.Append($"\"abilities\": [{string.Join(",", abilityStrs)}],");
                sb.Append($"\"has_missile_weapon\": {(hasMissileWeapon ? "true" : "false")},");
                sb.Append($"\"missile_ammo\": {missileCurrentAmmo},");
                sb.Append($"\"missile_max_ammo\": {missileMaxAmmo},");
                sb.Append($"\"inventory_ammo\": {inventoryAmmo},");
                sb.Append($"\"zone_id\": \"{EscapeJson(zoneId)}\",");
                sb.Append($"\"zone_name\": \"{EscapeJson(zoneName)}\",");
                sb.Append($"\"zone_fully_explored\": {(isZoneFullyExplored ? "true" : "false")},");
                sb.Append($"\"autoexplore_stuck\": {(isAutoexploreStuck ? "true" : "false")},");
                bool isSettlement = IsSettlementZone(currentCell?.ParentZone);
                sb.Append($"\"is_settlement\": {(isSettlement ? "true" : "false")},");
                int zoneTier = 1;
                try { zoneTier = currentCell?.ParentZone?.Tier ?? 1; } catch { }
                sb.Append($"\"zone_tier\": {zoneTier},");

                int unexploredCellCount = 0;
                int sumUnexpX = 0;
                int sumUnexpY = 0;
                int nearestUnexpX = -1;
                int nearestUnexpY = -1;
                int minUnexpDist = int.MaxValue;
                try
                {
                    var parentZone = currentCell?.ParentZone;
                    if (parentZone != null && !parentZone.IsWorldMap())
                    {
                        int curPx = player?.CurrentCell?.X ?? -1;
                        int curPy = player?.CurrentCell?.Y ?? -1;
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
                                    if (curPx >= 0 && curPy >= 0)
                                    {
                                        int dist = Math.Max(Math.Abs(x - curPx), Math.Abs(y - curPy));
                                        if (dist < minUnexpDist)
                                        {
                                            minUnexpDist = dist;
                                            nearestUnexpX = x;
                                            nearestUnexpY = y;
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                catch { }

                lastUnexploredCellCount = unexploredCellCount;
                sb.Append($"\"unexplored_cells\": {unexploredCellCount},");
                sb.Append($"\"unexplored_centroid_x\": {(unexploredCellCount > 0 ? sumUnexpX / unexploredCellCount : -1)},");
                sb.Append($"\"unexplored_centroid_y\": {(unexploredCellCount > 0 ? sumUnexpY / unexploredCellCount : -1)},");
                sb.Append($"\"nearest_unexplored_x\": {nearestUnexpX},");
                sb.Append($"\"nearest_unexplored_y\": {nearestUnexpY},");
                sb.Append($"\"nearest_unexplored_dist\": {(minUnexpDist != int.MaxValue ? minUnexpDist : -1)},");
                sb.Append(BuildFrontierJson(player, currentCell, isAutoexploreStuck || isZoneFullyExplored));
                sb.Append(LastBurrowJson());
                sb.Append(LastAbilityUseJson());
                sb.Append(LastLootJson());
                sb.Append(LastInvActionJson());

                string reachableEdges = "";
                try
                {
                    if (currentCell?.ParentZone != null && !currentCell.ParentZone.IsWorldMap())
                    {
                        char[] testEdges = new char[] { 'N', 'S', 'E', 'W' };
                        foreach (char edge in testEdges)
                        {
                            string edgeStep = null;
                            if (AutoAct.TryFindEdgeStep(edge, out edgeStep) && !string.IsNullOrEmpty(edgeStep) && edgeStep != ".")
                            {
                                reachableEdges += edge.ToString();
                            }
                        }
                    }
                }
                catch { }
                sb.Append($"\"reachable_edges\": \"{reachableEdges}\",");

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
                            if (c != null && !c.IsPlayer() && IsStanding(c))
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
                                    if (zObj != null && !zObj.IsPlayer() && IsStanding(zObj) && IsCompanion(zObj, player))
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
                        if (IsDownPassage(o)) standingOnStairsDown = true;
                        if (IsUpPassage(o)) standingOnStairsUp = true;
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

                                    if (IsDownPassage(obj))
                                    {
                                        stairsDownEntries.Add($"{{\"name\": \"{EscapeJson(name)}\", \"blueprint\": \"{EscapeJson(bp)}\", \"dist\": {dist}, \"dir\": \"{dir}\", \"tx\": {x}, \"ty\": {y}}}");
                                    }
                                    if (IsUpPassage(obj))
                                    {
                                        stairsUpEntries.Add($"{{\"name\": \"{EscapeJson(name)}\", \"blueprint\": \"{EscapeJson(bp)}\", \"dist\": {dist}, \"dir\": \"{dir}\", \"tx\": {x}, \"ty\": {y}}}");
                                    }

                                    bool isCompanion = IsCompanion(obj, player);
                                    bool isEnemy = !isCompanion && CheckIsEnemy(obj, player);
                                    bool canProselytize = CanBeProselytized(obj, player);
                                    bool hasLOS = false;
                                    try { hasLOS = player.HasLOSTo(obj); } catch { }

                                    int objLevel = 1;
                                    try { objLevel = obj.Stat("Level", 1); } catch { }
                                    int objHp = 0, objMaxHp = 0;
                                    try { objHp = obj.hitpoints; objMaxHp = obj.baseHitpoints; } catch { }
                                    int levelDiff = objLevel - playerLevel;
                                    string diffStr = levelDiff <= -5 ? "Trivial" : levelDiff <= -2 ? "Easy" : levelDiff <= 2 ? "Average" : levelDiff <= 5 ? "Tough" : levelDiff <= 9 ? "Very Tough" : "Impossible";
                                    bool isStationary = IsImmobile(obj) || obj.HasPart("Plant") || obj.HasPart("Fungus") || obj.HasTag("Immobile") || obj.HasProperty("Immobile") || bp.IndexOf("Glowpad", StringComparison.OrdinalIgnoreCase) >= 0;

                                    entityEntries.Add($"{{\"name\": \"{EscapeJson(name)}\", \"blueprint\": \"{EscapeJson(bp)}\", \"dist\": {dist}, \"dir\": \"{dir}\", \"tx\": {x}, \"ty\": {y}, \"is_enemy\": {(isEnemy ? "true" : "false")}, \"is_companion\": {(isCompanion ? "true" : "false")}, \"can_proselytize\": {(canProselytize ? "true" : "false")}, \"has_los\": {(hasLOS ? "true" : "false")}, \"level\": {objLevel}, \"difficulty\": \"{diffStr}\", \"is_stationary\": {(isStationary ? "true" : "false")}, \"hp\": {objHp}, \"max_hp\": {objMaxHp}, \"corpse_chance\": {CorpseChanceOf(obj)}}}");
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
                                    bool isStationary = IsImmobile(currentTarget) || currentTarget.HasPart("Plant") || currentTarget.HasPart("Fungus") || currentTarget.HasTag("Immobile") || currentTarget.HasProperty("Immobile") || bp.IndexOf("Glowpad", StringComparison.OrdinalIgnoreCase) >= 0;
                                    entityEntries.Insert(0, $"{{\"name\": \"{EscapeJson(name)}\", \"blueprint\": \"{EscapeJson(bp)}\", \"dist\": {dist}, \"dir\": \"{dir}\", \"tx\": {tx}, \"ty\": {ty}, \"is_enemy\": true, \"level\": {objLevel}, \"difficulty\": \"{diffStr}\", \"is_stationary\": {(isStationary ? "true" : "false")}, \"corpse_chance\": {CorpseChanceOf(currentTarget)}}}");
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

        private static bool IsDownPassage(GameObject obj)
        {
            if (obj == null || obj.IsPlayer()) return false;
            if (obj.IsAlive || obj.HasPart("Combat") || obj.HasPart("Brain") || obj.HasPart("Plant") || obj.HasPart("Fungus") || obj.HasPart("Creature")) return false;

            string bp = (obj.Blueprint ?? "").ToLower();
            string name = StripQudFormatting(obj.DisplayName ?? "").ToLower();
            if (bp.Contains("vine") || bp.Contains("spit") || name.Contains("vine") || name.Contains("spit")) return false;

            if (obj.HasPart("StairsDown") || obj.HasPart("Hole") || obj.HasPart("OpenShaft") || obj.HasPart("Pit")) return true;

            bool isPit = bp == "pit" || bp.StartsWith("pit_") || bp.EndsWith("_pit") || bp.Contains("_pit_") ||
                         name == "pit" || name.StartsWith("pit ") || name.EndsWith(" pit") || name.Contains(" pit ");

            if (bp.Contains("stairsdown") || bp.Contains("hole") || bp.Contains("shaft") || bp.Contains("chasm") || isPit) return true;
            if (name.Contains("stairs down") || name.Contains("hole") || name.Contains("shaft") || name.Contains("ladder down") || name.Contains("chasm") || isPit) return true;
            return false;
        }

        private static bool IsUpPassage(GameObject obj)
        {
            if (obj == null || obj.IsPlayer()) return false;
            if (obj.IsAlive || obj.HasPart("Combat") || obj.HasPart("Brain") || obj.HasPart("Plant") || obj.HasPart("Fungus") || obj.HasPart("Creature")) return false;

            string bp = (obj.Blueprint ?? "").ToLower();
            string name = StripQudFormatting(obj.DisplayName ?? "").ToLower();
            if (bp.Contains("vine") || bp.Contains("spit") || name.Contains("vine") || name.Contains("spit")) return false;

            if (obj.HasPart("StairsUp")) return true;
            if (bp.Contains("stairsup") || name.Contains("stairs up") || name.Contains("ladder up")) return true;
            return false;
        }

        public static bool IsSettlementZone(Zone zone)
        {
            if (zone == null) return false;
            string zName = (zone.DisplayName ?? "").ToLower();
            if (zName.Contains("joppa") || zName.Contains("stilt") || zName.Contains("grit gate") ||
                zName.Contains("kyakukya") || zName.Contains("yd freehold") || zName.Contains("bey lah") ||
                zName.Contains("omonporch") || zName.Contains("ezra") || zName.Contains("village") ||
                zName.Contains("settlement") || zName.Contains("town") || zName.Contains("commune") ||
                zName.Contains("enclave") || zName.Contains("pariah") || zName.Contains("haven") ||
                zName.Contains("bazaar") || zName.Contains("kith and kin"))
            {
                return true;
            }
            try
            {
                if (zone.HasZoneProperty("Settlement") || zone.HasZoneProperty("Town") || zone.HasZoneProperty("Village") ||
                    zone.HasZoneProperty("Peaceful") || !string.IsNullOrEmpty(zone.GetZoneProperty("Settlement")))
                {
                    return true;
                }
            }
            catch { }
            return false;
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

                if (IsDownPassage(obj))
                {
                    names.Insert(0, $"[STAIRS_DOWN: {cleanName}]");
                    continue;
                }
                if (IsUpPassage(obj))
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
                if (IsObjectAflame(obj, player))
                {
                    names.Insert(0, "[HAZARD: fire]");
                    continue;
                }
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
                                .Where(o => {
                                    try { return player.HasLOSTo(o); } catch { return true; }
                                })
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
                        var missileRay = GetLineBetween(current, targetCell);
                        if (missileRay.Any(c => c.Objects != null && c.Objects.Any(o => o != null && IsCompanion(o, player))))
                        {
                            UnityEngine.Debug.LogWarning("[QudAI FIRE_MISSILE] Refusing to fire missile because a friendly companion is standing in the line of fire!");
                            return;
                        }
                        bool cellHasLOS = true;
                        try { cellHasLOS = player.HasLOSTo(targetCell); } catch { }
                        if (!cellHasLOS)
                        {
                            UnityEngine.Debug.LogWarning($"[QudAI FIRE_MISSILE] Aborting missile fire on cell {targetCell.X},{targetCell.Y} because line of sight is occluded by walls!");
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

            if (act.StartsWith("ATTACK_WALL:") || act.StartsWith("FORCE_ATTACK:") || act.StartsWith("ATTACK_CELL:"))
            {
                lastMoveFailed = false;
                lastFailedDir = "";
                string dir = act.Split(':')[1].Trim().ToUpper();

                // NEVER attack walls, huts, or structures in peaceful towns/settlements!
                if (IsSettlementZone(player?.CurrentCell?.ParentZone))
                {
                    UnityEngine.Debug.Log($"[QudAI ATTACK_WALL] Suppressed wall/hut attack in peaceful settlement '{player?.CurrentCell?.ParentZone?.DisplayName}'");
                    lastMoveFailed = true;
                    lastFailedDir = dir;
                    if (player.Energy != null) player.UseEnergy(1000, "Pass");
                    return;
                }

                Cell targetCell = null;
                if (player != null && player.CurrentCell != null)
                {
                    targetCell = player.CurrentCell.GetCellFromDirection(dir, false);
                }

                if (targetCell != null && targetCell.Objects != null)
                {
                    GameObject targetWall = null;
                    for (int i = 0; i < targetCell.Objects.Count; i++)
                    {
                        GameObject o = targetCell.Objects[i];
                        if (o != null && !o.IsPlayer() && !IsCompanion(o, player))
                        {
                            // Never attack owned objects or structures
                            if (o.IsOwned() || !string.IsNullOrEmpty(o.Owner) || o.HasProperty("Owned") || o.HasProperty("OwnedBy"))
                                continue;

                            if (o.HasPart("Wall") || o.HasPart("Plant") || o.HasPart("Combat") || o.HasPart("Physics"))
                            {
                                targetWall = o;
                                break;
                            }
                        }
                    }

                    if (targetWall != null)
                    {
                        int energyBefore = player.Energy?.Value ?? 0;
                        UnityEngine.Debug.Log($"[QudAI ATTACK_WALL] Burrowing through wall/obstacle {targetWall.DisplayNameOnly} ({dir}) at ({targetCell.X}, {targetCell.Y})");
                        bool burrowHasHp = false;
                        int burrowHpBefore = 0, burrowMaxHp = 0;
                        try { burrowHasHp = targetWall.HasStat("Hitpoints"); burrowHpBefore = targetWall.hitpoints; burrowMaxHp = targetWall.baseHitpoints; } catch { }
                        try
                        {
                            player.PerformMeleeAttack(targetWall);
                        }
                        catch (Exception ex)
                        {
                            UnityEngine.Debug.LogError("[QudAI ATTACK_WALL Error] " + ex.ToString());
                        }
                        try
                        {
                            int burrowHpAfter = burrowHpBefore;
                            bool burrowDestroyed = false;
                            try { burrowHpAfter = targetWall.hitpoints; } catch { }
                            try { burrowDestroyed = (burrowHasHp && burrowHpAfter <= 0) || (targetCell.Objects != null && !targetCell.Objects.Contains(targetWall)); } catch { }
                            burrowSeq++;
                            lastBurrowJson = "{\"seq\": " + burrowSeq + ", \"dir\": \"" + dir + "\", \"name\": \"" + EscapeJson(StripQudFormatting(targetWall.DisplayNameOnly ?? "")) +
                                "\", \"x\": " + targetCell.X + ", \"y\": " + targetCell.Y + ", \"has_hp\": " + (burrowHasHp ? "true" : "false") +
                                ", \"hp_before\": " + burrowHpBefore + ", \"hp_after\": " + burrowHpAfter + ", \"max_hp\": " + burrowMaxHp +
                                ", \"destroyed\": " + (burrowDestroyed ? "true" : "false") + "}";
                            UnityEngine.Debug.Log($"[QudAI ATTACK_WALL] {targetWall.DisplayNameOnly}: HP {burrowHpBefore} -> {burrowHpAfter}/{burrowMaxHp}{(burrowDestroyed ? " (destroyed)" : "")}");
                        }
                        catch { }

                        if (player.Energy != null && player.Energy.Value >= energyBefore)
                        {
                            player.UseEnergy(1000, "Attack");
                        }
                        return;
                    }
                }

                // If no wall found in target cell, report failure and pass
                lastMoveFailed = true;
                lastFailedDir = dir;
                if (player.Energy != null) player.UseEnergy(1000, "Pass");
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
                        var stairs = player.CurrentCell?.Objects?.FirstOrDefault(o => o != null && IsDownPassage(o));
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
                        var stairs = player.CurrentCell?.Objects?.FirstOrDefault(o => o != null && IsUpPassage(o));
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

            if (act.StartsWith("DROP_ITEMS:"))
            {
                lastMoveFailed = false;
                lastFailedDir = "";
                ExecuteDropItems(player, action.Substring(11));
                player.UseEnergy(1000, "Inventory");
                return;
            }

            if (act.StartsWith("EQUIP_ITEM:"))
            {
                lastMoveFailed = false;
                lastFailedDir = "";
                ExecuteEquipItem(player, action.Substring(11));
                player.UseEnergy(1000, "Inventory");
                return;
            }

            if (act.StartsWith("TAKE_ITEM:"))
            {
                lastMoveFailed = false;
                lastFailedDir = "";
                ExecuteTakeItem(player, action.Substring(10));
                player.UseEnergy(1000, "Inventory");
                return;
            }

            if (act == "LOOT")
            {
                lastMoveFailed = false;
                lastFailedDir = "";
                TryLootNearby(player);
                player.UseEnergy(1000, "Loot");
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
                    if (!IsCampSpotSafe(player))
                    {
                        UnityEngine.Debug.Log("[QudAI MAKE_CAMP] Refused: flammable plants or fire within " + CampSafetyRadius + " cells");
                        MessageQueue.AddPlayerMessage("{{R|It is too dangerous to light a campfire among flammable plants.}}");
                        if (player.Energy != null) player.UseEnergy(1000, "MakeCamp");
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

                        // 1. Consume 1 ingredient or food item from player inventory. No ingredient = no meal (HANDOFF issue 34).
                        bool ate = false;
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
                                ate = true;
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

                        if (!ate)
                        {
                            UnityEngine.Debug.Log("[QudAI COOK_MEAL] No ingredient to cook; hunger unchanged");
                            MessageQueue.AddPlayerMessage("{{R|You have nothing to cook.}}");
                            if (player.Energy != null) player.UseEnergy(1000, "Cook");
                            return;
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
                                corpseObj = c.Objects.FirstOrDefault(o => IsButcherableCorpse(o));
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
                // REST / PASS used to run a hard-coded autolevel here (rifle/acrobatics/endurance skills, Toughness or Agility for
                // attributes, the first available mutation) that ignored the build template: it bought Acrobatics and put a point
                // into Agility for an Esper that wanted Tactics and Ego. Python spends points explicitly with AUTOLEVEL_STAT /
                // AUTOLEVEL_SKILL / AUTOLEVEL_*MUTATION according to the template (HANDOFF issue 50).
                player.UseEnergy(1000, "Pass");
                return;
            }

            if (act.StartsWith("USE_ABILITY:"))
            {
                lastMoveFailed = false;
                lastFailedDir = "";
                string cmd = action.Substring(12).Trim();

                PreferredDirection = "";
                Cell explicitCell = null;
                if (cmd.Contains(":"))
                {
                    string[] parts = cmd.Split(':');
                    cmd = parts[0].Trim();
                    if (parts.Length > 1)
                    {
                        // "USE_ABILITY:CommandLase:W@25,12": the direction, then the exact cell the brain read from the exported entity (see below).
                        string dirPart = parts[1].Trim();
                        int at = dirPart.IndexOf('@');
                        if (at >= 0)
                        {
                            string[] xy = dirPart.Substring(at + 1).Split(',');
                            int ex, ey;
                            if (xy.Length == 2 && int.TryParse(xy[0].Trim(), out ex) && int.TryParse(xy[1].Trim(), out ey))
                            {
                                try { explicitCell = player.CurrentCell?.ParentZone?.GetCell(ex, ey); } catch { }
                            }
                            dirPart = dirPart.Substring(0, at);
                        }
                        PreferredDirection = dirPart.Trim().ToUpper();
                    }
                }

                if (string.IsNullOrEmpty(PreferredDirection))
                {
                    PreferredDirection = GetBestEnemyDirection(player);
                }

                // Resolve ability command alias/display name against player's ActivatedAbilities
                try
                {
                    var playerAbilities = player.GetPart<ActivatedAbilities>();
                    if (playerAbilities != null && playerAbilities.AbilityByGuid != null)
                    {
                        foreach (var kvp in playerAbilities.AbilityByGuid)
                        {
                            var ab = kvp.Value;
                            if (ab == null) continue;
                            string cleanName = StripQudFormatting(ab.DisplayName ?? "");
                            string abCmd = ab.Command ?? "";
                            if (string.Equals(abCmd, cmd, StringComparison.OrdinalIgnoreCase) ||
                                string.Equals(cleanName, cmd, StringComparison.OrdinalIgnoreCase) ||
                                string.Equals(cleanName.Replace(" ", ""), cmd.Replace(" ", ""), StringComparison.OrdinalIgnoreCase) ||
                                string.Equals(abCmd, "Command" + cmd.Replace(" ", ""), StringComparison.OrdinalIgnoreCase) ||
                                string.Equals("Command" + cleanName.Replace(" ", ""), cmd, StringComparison.OrdinalIgnoreCase))
                            {
                                cmd = abCmd;
                                break;
                            }
                        }
                    }
                }
                catch { }

                if (cmd.IndexOf("butcher", StringComparison.OrdinalIgnoreCase) >= 0)
                {
                    ExecuteCommand(player, "BUTCHER");
                    return;
                }
                if (cmd.IndexOf("harvest", StringComparison.OrdinalIgnoreCase) >= 0)
                {
                    ExecuteCommand(player, "HARVEST");
                    return;
                }

                // Usability pre-check (HANDOFF issue 52): do not fire into a cooldown or a disabled ability and call it a use.
                // The turn is still spent (R4: a command that spends no energy re-exports the same state and loops).
                bool abFound, abEnabled, abUsable; int cdBefore; string labelBefore;
                ReadAbilityState(player, cmd, out abFound, out abEnabled, out abUsable, out cdBefore, out labelBefore);
                if (abFound && (!abEnabled || !abUsable || cdBefore > 0))
                {
                    string why = !abEnabled ? "disabled" : (!abUsable ? "not usable" : "on cooldown (" + cdBefore + ")");
                    UnityEngine.Debug.LogWarning($"[QudAI USE_ABILITY] Refused {cmd}: {why}");
                    RecordAbilityUse(cmd, PreferredDirection, true, cdBefore, cdBefore, labelBefore, labelBefore, true, why);
                    PreferredDirection = "";
                    player.UseEnergy(1000, "Ability");
                    return;
                }

                bool isProselytize = cmd.IndexOf("proselytize", StringComparison.OrdinalIgnoreCase) >= 0 || cmd.IndexOf("beguile", StringComparison.OrdinalIgnoreCase) >= 0;
                bool isTouchOrDirect = isProselytize || cmd.IndexOf("teleportother", StringComparison.OrdinalIgnoreCase) >= 0;
                bool isDirectRay = cmd.IndexOf("lase", StringComparison.OrdinalIgnoreCase) >= 0 ||
                                   cmd.IndexOf("stunningforce", StringComparison.OrdinalIgnoreCase) >= 0 ||
                                   cmd.IndexOf("ray", StringComparison.OrdinalIgnoreCase) >= 0 ||
                                   cmd.IndexOf("spit", StringComparison.OrdinalIgnoreCase) >= 0;

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
                            .Where(o => !isDirectRay || (player.HasLOSTo(o) && !GetLineBetween(pCell, o.CurrentCell).Any(c => c.Objects != null && c.Objects.Any(comp => IsCompanion(comp, player)))))
                            .Where(o => pCell.GetDirectionFromCell(o.CurrentCell).Equals(PreferredDirection, StringComparison.OrdinalIgnoreCase))
                            .OrderBy(o => Math.Max(Math.Abs(o.CurrentCell.X - pCell.X), Math.Abs(o.CurrentCell.Y - pCell.Y)))
                            .FirstOrDefault();
                    }

                    if (targetObj == null)
                    {
                        targetObj = safeZoneObjs
                            .Where(o => o != null && !o.IsPlayer() && (isProselytize ? CanBeProselytized(o, player) : (!IsCompanion(o, player) && CheckIsEnemy(o, player))) && o.CurrentCell != null)
                            .Where(o => !isDirectRay || (player.HasLOSTo(o) && !GetLineBetween(pCell, o.CurrentCell).Any(c => c.Objects != null && c.Objects.Any(comp => IsCompanion(comp, player)))))
                            .OrderBy(o => Math.Max(Math.Abs(o.CurrentCell.X - pCell.X), Math.Abs(o.CurrentCell.Y - pCell.Y)))
                            .FirstOrDefault();
                    }
                    targetCell = targetObj?.CurrentCell;
                }

                // An explicit cell from the brain wins over the direction search, and does not depend on CheckIsEnemy: a musket turret exported is_enemy false and the Lase went to the
                // empty cell next to the player four times (HANDOFF issue 77, Gen 25: "on target none"). The line-of-sight and companion safety checks below still apply.
                if (explicitCell != null)
                {
                    targetCell = explicitCell;
                    targetObj = explicitCell.Objects == null ? null : explicitCell.Objects.FirstOrDefault(o => o != null && !o.IsPlayer() && !IsCompanion(o, player) && o.HasStat("Hitpoints"));
                }

                if (targetCell == null && !string.IsNullOrEmpty(PreferredDirection) && player.CurrentCell != null)
                {
                    targetCell = player.CurrentCell.GetCellFromDirection(PreferredDirection, false);
                }

                if (isDirectRay && targetCell != null && player.CurrentCell != null)
                {
                    bool cellHasLOS = false;
                    try { cellHasLOS = player.HasLOSTo(targetCell); } catch { }
                    if (!cellHasLOS)
                    {
                        UnityEngine.Debug.LogWarning($"[QudAI USE_ABILITY] Aborting direct ray {cmd} on cell {targetCell.X},{targetCell.Y} because line of sight is occluded by walls!");
                        targetCell = null;
                        targetObj = null;
                    }
                    else
                    {
                        var rayCells = GetLineBetween(player.CurrentCell, targetCell);
                        if (rayCells.Any(c => c.Objects != null && c.Objects.Any(o => o != null && IsCompanion(o, player))))
                        {
                            UnityEngine.Debug.LogWarning($"[QudAI USE_ABILITY] Aborting direct ray {cmd} because a friendly companion is standing in the line of fire!");
                            targetCell = null;
                            targetObj = null;
                        }
                    }
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

                if (targetObj != null && !isProselytize)
                {
                    player.Target = targetObj;
                    try { Sidebar.CurrentTarget = targetObj; } catch { }
                }
                else if (isProselytize)
                {
                    player.Target = null;
                    try { Sidebar.CurrentTarget = null; } catch { }
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

                if (isProselytize)
                {
                    player.Target = null;
                    try { Sidebar.CurrentTarget = null; } catch { }
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

                {
                    bool f2, e2, u2; int cdAfter; string labelAfter;
                    ReadAbilityState(player, cmd, out f2, out e2, out u2, out cdAfter, out labelAfter);
                    RecordAbilityUse(cmd, PreferredDirection, abFound, cdBefore, cdAfter, labelBefore, labelAfter, false, "");
                }

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

            if (act.StartsWith("NAVIGATE_TO_CELL:"))
            {
                string coordStr = act.Substring(17).Trim();
                string[] parts = coordStr.Split(',');
                if (parts.Length == 2 && int.TryParse(parts[0], out int tx) && int.TryParse(parts[1], out int ty))
                {
                    Cell targetCell = null;
                    try { targetCell = player.CurrentCell?.ParentZone?.GetCell(tx, ty); } catch { }
                    if (targetCell != null)
                    {
                        string step = null;
                        try
                        {
                            AutoAct.TryFindPathStep(targetCell, out step);
                        }
                        catch { }

                        if (string.IsNullOrEmpty(step) || step == ".")
                        {
                            LogPathDiag(player, targetCell);      // once per target: why does the engine find no step? (HANDOFF issue 92)
                            // Check open adjacent cells that reduce distance to targetCell
                            try
                            {
                                Cell pCell = player.CurrentCell;
                                if (pCell != null)
                                {
                                    int curDist = Math.Abs(pCell.X - tx) + Math.Abs(pCell.Y - ty);
                                    int bestDist = curDist;
                                    string bestDir = null;
                                    string[] candidateDirs = new string[] { "N", "S", "E", "W", "NE", "NW", "SE", "SW" };
                                    foreach (var cd in candidateDirs)
                                    {
                                        Cell nc = pCell.GetCellFromDirection(cd, false);
                                        if (nc != null && !nc.IsOccluding() && !nc.HasWall())
                                        {
                                            int nd = Math.Abs(nc.X - tx) + Math.Abs(nc.Y - ty);
                                            if (nd < bestDist)
                                            {
                                                bestDist = nd;
                                                bestDir = cd;
                                            }
                                        }
                                    }
                                    if (!string.IsNullOrEmpty(bestDir))
                                    {
                                        step = bestDir;
                                    }
                                }
                            }
                            catch { }
                        }

                        if (!string.IsNullOrEmpty(step) && step != ".")
                        {
                            Cell targetNext = player.CurrentCell?.GetCellFromDirection(step, false);
                            if (targetNext != null && (targetNext.IsOccluding() || targetNext.HasWall()))
                            {
                                if (TryBreakPathObstacle(player, targetNext, step))
                                {
                                    lastMoveFailed = false;
                                    lastFailedDir = "";
                                    return;
                                }
                                lastMoveFailed = true;
                                lastFailedDir = step.ToUpper();
                                if (player.Energy != null) player.UseEnergy(1000, "Pass");
                                return;
                            }

                            int energyBefore = player.Energy?.Value ?? 0;
                            int pxBefore = player.CurrentCell?.X ?? -1;
                            int pyBefore = player.CurrentCell?.Y ?? -1;

                            bool moved = player.Move(step);
                            bool cellChanged = (player.CurrentCell != null && (player.CurrentCell.X != pxBefore || player.CurrentCell.Y != pyBefore));

                            if (!moved || !cellChanged)
                            {
                                if (TryBreakPathObstacle(player, player.CurrentCell?.GetCellFromDirection(step, false), step))
                                {
                                    lastMoveFailed = false;
                                    lastFailedDir = "";
                                    return;
                                }
                                lastMoveFailed = true;
                                lastFailedDir = step.ToUpper();
                                TryOpenDoorInDirection(player, step);
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
                            return;
                        }
                        else
                        {
                            lastMoveFailed = true;
                            lastFailedDir = "PATH_BLOCKED";
                            if (player.Energy != null) player.UseEnergy(1000, "Pass");
                            return;
                        }
                    }
                }
            }

            if (act.StartsWith("NAVIGATE_ZONE_EXIT:"))
            {
                string dirStr = act.Substring(19).Trim().ToUpper();
                char edgeChar = !string.IsNullOrEmpty(dirStr) ? dirStr[0] : 'E';
                string step = null;

                int curX = player.CurrentCell?.X ?? -1;
                int curY = player.CurrentCell?.Y ?? -1;
                bool isOnTargetEdge = (edgeChar == 'W' && curX == 0)
                                   || (edgeChar == 'E' && curX == 79)
                                   || (edgeChar == 'N' && curY == 0)
                                   || (edgeChar == 'S' && curY == 24);

                if (isOnTargetEdge)
                {
                    // Stepping directly off the zone border transitions to the adjacent zone!
                    string exitDir = edgeChar.ToString();
                    int energyBefore = player.Energy?.Value ?? 0;
                    int pxBefore = curX;
                    int pyBefore = curY;
                    string zoneBefore = player.CurrentCell?.ParentZone?.ZoneID;

                    bool moved = player.Move(exitDir);
                    bool zoneOrCellChanged = (player.CurrentCell != null && (
                        player.CurrentCell.ParentZone?.ZoneID != zoneBefore ||
                        player.CurrentCell.X != pxBefore ||
                        player.CurrentCell.Y != pyBefore
                    ));

                    if (moved || zoneOrCellChanged)
                    {
                        lastMoveFailed = false;
                        lastFailedDir = "";
                        autoexplorePosHistory.Clear();
                    }
                    else
                    {
                        lastMoveFailed = true;
                        lastFailedDir = exitDir;
                        TryOpenDoorInDirection(player, exitDir);
                    }
                    if (player.Energy != null && player.Energy.Value >= energyBefore)
                    {
                        player.UseEnergy(1000, "Movement");
                    }
                    return;
                }

                try
                {
                    AutoAct.TryFindEdgeStep(edgeChar, out step);
                }
                catch { }

                // Fallback: Check open border cells on requested edge if TryFindEdgeStep didn't find a direct step
                if (string.IsNullOrEmpty(step) || step == ".")
                {
                    try
                    {
                        Zone z = player.CurrentCell?.ParentZone;
                        if (z != null && player.CurrentCell != null)
                        {
                            List<Cell> borderCells = new List<Cell>();
                            if (edgeChar == 'N') { for (int x = 0; x < z.Width; x++) borderCells.Add(z.GetCell(x, 0)); }
                            else if (edgeChar == 'S') { for (int x = 0; x < z.Width; x++) borderCells.Add(z.GetCell(x, z.Height - 1)); }
                            else if (edgeChar == 'E') { for (int y = 0; y < z.Height; y++) borderCells.Add(z.GetCell(z.Width - 1, y)); }
                            else if (edgeChar == 'W') { for (int y = 0; y < z.Height; y++) borderCells.Add(z.GetCell(0, y)); }

                            Cell bestBorder = null;
                            int bestD = int.MaxValue;
                            foreach (var bc in borderCells)
                            {
                                if (bc != null && !bc.IsOccluding() && !bc.HasWall())
                                {
                                    int d = Math.Abs(bc.X - player.CurrentCell.X) + Math.Abs(bc.Y - player.CurrentCell.Y);
                                    if (d < bestD)
                                    {
                                        string testStep = null;
                                        if (AutoAct.TryFindPathStep(bc, out testStep) && !string.IsNullOrEmpty(testStep) && testStep != ".")
                                        {
                                            bestD = d;
                                            bestBorder = bc;
                                            step = testStep;
                                        }
                                    }
                                }
                            }
                        }
                    }
                    catch { }
                }

                // If no complex path step found, check if player is directly adjacent to the target edge border
                if (string.IsNullOrEmpty(step) || step == ".")
                {
                    Cell c = player.CurrentCell?.GetCellFromDirection(edgeChar.ToString(), false);
                    if (c != null && !c.IsOccluding() && !c.HasWall())
                    {
                        bool isBorderCell = (edgeChar == 'W' && c.X == 0)
                                         || (edgeChar == 'E' && c.X == (c.ParentZone?.Width - 1 ?? 79))
                                         || (edgeChar == 'N' && c.Y == 0)
                                         || (edgeChar == 'S' && c.Y == (c.ParentZone?.Height - 1 ?? 24));
                        if (isBorderCell)
                        {
                            step = edgeChar.ToString();
                        }
                    }
                }

                if (!string.IsNullOrEmpty(step) && step != ".")
                {
                    int energyBefore = player.Energy?.Value ?? 0;
                    int pxBefore = player.CurrentCell?.X ?? -1;
                    int pyBefore = player.CurrentCell?.Y ?? -1;
                    string zoneBefore = player.CurrentCell?.ParentZone?.ZoneID;

                    bool moved = player.Move(step);
                    bool zoneOrCellChanged = (player.CurrentCell != null && (
                        player.CurrentCell.ParentZone?.ZoneID != zoneBefore ||
                        player.CurrentCell.X != pxBefore ||
                        player.CurrentCell.Y != pyBefore
                    ));

                    if (!moved || !zoneOrCellChanged)
                    {
                        lastMoveFailed = true;
                        lastFailedDir = step.ToUpper();
                        TryOpenDoorInDirection(player, step);
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
                    return;
                }
                else
                {
                    lastMoveFailed = true;
                    lastFailedDir = edgeChar.ToString();
                    if (player.Energy != null) player.UseEnergy(1000, "Pass");
                    return;
                }
            }

            string direction = null;
            if (act.StartsWith("MOVE_")) direction = act.Substring(5);

            if (!string.IsNullOrEmpty(direction))
            {
                int energyBefore = player.Energy?.Value ?? 0;
                int pxBefore = player.CurrentCell?.X ?? -1;
                int pyBefore = player.CurrentCell?.Y ?? -1;
                string zoneBefore = player.CurrentCell?.ParentZone?.ZoneID;

                bool moved = player.Move(direction);
                bool cellChanged = (player.CurrentCell != null && (
                    player.CurrentCell.ParentZone?.ZoneID != zoneBefore ||
                    player.CurrentCell.X != pxBefore ||
                    player.CurrentCell.Y != pyBefore
                ));

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
                        cellChanged = (player.CurrentCell != null && (
                            player.CurrentCell.ParentZone?.ZoneID != zoneBefore ||
                            player.CurrentCell.X != pxBefore ||
                            player.CurrentCell.Y != pyBefore
                        ));
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

            // 1b. Engine-style loot step (issue 59): take unowned items and empty unowned chests next to him before walking on.
            if (TryLootNearby(player))
            {
                lastMoveFailed = false;
                lastFailedDir = "";
                if (player.Energy != null) player.UseEnergy(1000, "Loot");
                return;
            }

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
                // Persistent cycling: yield to Python brain navigation without falsely claiming the zone is explored
                isZoneFullyExplored = false;
                isAutoexploreStuck = true;
                autoexplorePosHistory.Clear();
                lastMoveFailed = false;
                lastFailedDir = "";
                UnityEngine.Debug.LogWarning($"[QudAI Autoexplore Oscillation] Cycling detected at ({curX}, {curY}) (visits: {repeatVisits}, unique: {uniquePositions}/{autoexplorePosHistory.Count}). Yielding to brain navigation.");
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

            if (string.IsNullOrEmpty(step) || step == ".")
            {
                // Fallback for narrow corridors / dungeons: search for nearest reachable unexplored cell via pathfinder
                try
                {
                    Cell pCell = player.CurrentCell;
                    if (pCell?.ParentZone != null)
                    {
                        Zone z = pCell.ParentZone;
                        Cell nearestUnexplored = null;
                        int bestDist = int.MaxValue;
                        for (int x = 0; x < z.Width; x++)
                        {
                            for (int y = 0; y < z.Height; y++)
                            {
                                Cell c = z.GetCell(x, y);
                                if (c != null && !c.Explored && !c.IsOccluding() && !c.HasWall())
                                {
                                    int d = Math.Abs(x - pCell.X) + Math.Abs(y - pCell.Y);
                                    if (d < bestDist)
                                    {
                                        bestDist = d;
                                        nearestUnexplored = c;
                                    }
                                }
                            }
                        }
                        if (nearestUnexplored != null)
                        {
                            AutoAct.TryFindPathStep(nearestUnexplored, out step);
                        }
                    }
                }
                catch { }
            }

            if (!string.IsNullOrEmpty(step) && step != ".")
            {
                Cell targetNext = player.CurrentCell?.GetCellFromDirection(step, false);
                if (targetNext != null && (targetNext.IsOccluding() || targetNext.HasWall()))
                {
                    lastMoveFailed = true;
                    lastFailedDir = step.ToUpper();
                    isAutoexploreStuck = true;
                    if (player.Energy != null) player.UseEnergy(1000, "Pass");
                    return;
                }

                isZoneFullyExplored = false;
                isAutoexploreStuck = false;
                int energyBefore = player.Energy != null ? player.Energy.Value : 0;
                bool moved = player.Move(step);
                if (!moved)
                {
                    lastMoveFailed = true;
                    lastFailedDir = step.ToUpper();
                    isAutoexploreStuck = true;
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

            // 4. If neither native autoexplore nor pathfinder can find an unexplored step, mark zone as explored so AI advances to stairs or exits!
            isZoneFullyExplored = true;
            isAutoexploreStuck = false;
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

                if (command.StartsWith("AUTOLEVEL_BUY_MUTATION", StringComparison.OrdinalIgnoreCase))
                {
                    string targetMut = "";
                    if (command.Contains(":"))
                    {
                        targetMut = command.Substring(command.IndexOf(':') + 1).Trim();
                    }
                    BuyNewMutation(player, targetMut);
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
                    if (!AllocateMutation(player, null))
                    {
                        if (mp >= 4)
                        {
                            if (!BuyNewMutation(player, null)) break;
                        }
                        else
                        {
                            break;
                        }
                    }
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
                if (apStat.BaseValue > 0) apStat.BaseValue -= 1;

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

        private static bool BuyNewMutation(GameObject player, string preferredMutation = null)
        {
            try
            {
                if (player == null) return false;
                int mp = player.Stat("MP", 0);
                if (mp < 4) return false;

                AIPlayerTurnPatch.PreferredMutation = preferredMutation ?? "";
                try
                {
                    bool bought = Qud.API.MutationsAPI.BuyRandomMutation(player, 4, false, null);
                    if (bought)
                    {
                        string msg = "{G|[AI Level Up] Unlocked new mutation ability for 4 MP!}";
                        MessageQueue.AddPlayerMessage(msg);
                        UnityEngine.Debug.Log("[QudAI LevelUp] " + msg);
                        return true;
                    }
                }
                finally
                {
                    AIPlayerTurnPatch.PreferredMutation = "";
                }
            }
            catch (Exception ex)
            {
                UnityEngine.Debug.LogError("[QudAI BuyNewMutation Exception] " + ex.ToString());
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
                        if (spStat != null)
                        {
                            spStat.Penalty += sEntry.Cost;
                            if (spStat.BaseValue >= sEntry.Cost) spStat.BaseValue -= sEntry.Cost;
                        }
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
                                if (spStat != null)
                                {
                                    spStat.Penalty += (s.Cost + pEntry.Cost);
                                    if (spStat.BaseValue >= (s.Cost + pEntry.Cost)) spStat.BaseValue -= (s.Cost + pEntry.Cost);
                                }
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
                            if (spStat != null)
                            {
                                spStat.Penalty += pEntry.Cost;
                                if (spStat.BaseValue >= pEntry.Cost) spStat.BaseValue -= pEntry.Cost;
                            }
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
                    AIPlayerTurnPatch.RegisteredCompanionIds.Clear();
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
                            .Where(o => { try { return player.HasLOSTo(o); } catch { return true; } })
                            .Where(o => !AIPlayerTurnPatch.GetLineBetween(pCell, o.CurrentCell).Any(c => c.Objects != null && c.Objects.Any(comp => AIPlayerTurnPatch.IsCompanion(comp, player))))
                            .Where(o => pCell.GetDirectionFromCell(o.CurrentCell).Equals(AIPlayerTurnPatch.PreferredDirection, StringComparison.OrdinalIgnoreCase))
                            .OrderBy(o => Math.Max(Math.Abs(o.CurrentCell.X - pCell.X), Math.Abs(o.CurrentCell.Y - pCell.Y)))
                            .FirstOrDefault();
                    }
                    if (target == null)
                    {
                        target = safeZoneObjs
                            .Where(o => o != null && !o.IsPlayer() && AIPlayerTurnPatch.CheckIsEnemy(o, player) && o.CurrentCell != null)
                            .Where(o => { try { return player.HasLOSTo(o); } catch { return true; } })
                            .Where(o => !AIPlayerTurnPatch.GetLineBetween(pCell, o.CurrentCell).Any(c => c.Objects != null && c.Objects.Any(comp => AIPlayerTurnPatch.IsCompanion(comp, player))))
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
                        bool dirHasLOS = true;
                        try { dirHasLOS = player.HasLOSTo(dirCell); } catch { }
                        if (dirHasLOS && !AIPlayerTurnPatch.GetLineBetween(player.CurrentCell, dirCell).Any(c => c.Objects != null && c.Objects.Any(comp => AIPlayerTurnPatch.IsCompanion(comp, player))))
                        {
                            __result = dirCell;
                            UnityEngine.Debug.Log($"[QudAI AIPickTargetPatch] Auto-selected direction cell: {__result.X},{__result.Y}");
                            return false;
                        }
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
                            .Where(o => !AIPlayerTurnPatch.GetLineBetween(pCell, o.CurrentCell).Any(c => c.Objects != null && c.Objects.Any(comp => AIPlayerTurnPatch.IsCompanion(comp, player))))
                            .Where(o => pCell.GetDirectionFromCell(o.CurrentCell).Equals(AIPlayerTurnPatch.PreferredDirection, StringComparison.OrdinalIgnoreCase))
                            .OrderBy(o => Math.Max(Math.Abs(o.CurrentCell.X - pCell.X), Math.Abs(o.CurrentCell.Y - pCell.Y)))
                            .FirstOrDefault();
                    }
                    if (target == null)
                    {
                        target = safeZoneObjs
                            .Where(o => o != null && !o.IsPlayer() && AIPlayerTurnPatch.CheckIsEnemy(o, player) && o.CurrentCell != null)
                            .Where(o => !AIPlayerTurnPatch.GetLineBetween(pCell, o.CurrentCell).Any(c => c.Objects != null && c.Objects.Any(comp => AIPlayerTurnPatch.IsCompanion(comp, player))))
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

    [HarmonyPatch(typeof(XRL.UI.Popup), "ShowYesNo")]
    public static class AIPopupShowYesNoPatch
    {
        public static bool Prefix(string Message, Action<DialogResult> callback, ref DialogResult __result)
        {
            if (File.Exists(AIPlayerTurnPatch.FlagFile))
            {
                __result = DialogResult.Yes;
                try { callback?.Invoke(DialogResult.Yes); } catch { }
                UnityEngine.Debug.Log($"[QudAI AIPopupShowYesNoPatch] Auto-confirmed YES for: {Message}");
                return false;
            }
            return true;
        }
    }

    [HarmonyPatch(typeof(XRL.UI.Popup), "ShowYesNoCancel")]
    public static class AIPopupShowYesNoCancelPatch
    {
        public static bool Prefix(string Message, ref DialogResult __result)
        {
            if (File.Exists(AIPlayerTurnPatch.FlagFile))
            {
                __result = DialogResult.Yes;
                UnityEngine.Debug.Log($"[QudAI AIPopupShowYesNoCancelPatch] Auto-confirmed YES for: {Message}");
                return false;
            }
            return true;
        }
    }

    [HarmonyPatch(typeof(XRL.UI.Popup), "PickOption")]
    public static class AIPickOptionPatch
    {
        private static readonly string[] MutationPriorities = new string[]
        {
            "Light Manipulation", "Freezing Ray", "Flaming Ray", "Force Bubble", "Force Wall",
            "Phasing", "Teleportation", "Precognition", "Clairvoyance", "Double-muscled",
            "Triple-jointed", "Two-headed", "Multiple Arms", "Multiple Legs", "Regeneration",
            "Adrenal Control", "Corrosive Gas", "Electrical Generation", "Quills", "Burrowing Claws",
            "Wings", "Heightened Hearing", "Heightened Smell", "Night Vision", "Spiny", "Carapace",
            "LightManipulation", "FreezingRay", "FlamingRay", "ForceBubble", "ForceWall",
            "DoubleMuscled", "TripleJointed", "TwoHeaded", "MultipleArms", "MultipleLegs",
            "AdrenalControl", "CorrosiveGasGeneration", "ElectricalGeneration", "BurrowingClaws",
            "HeightenedHearing", "HeightenedSmell", "NightVision"
        };

        // ---- Mutation naming and the published ranking (HANDOFF issue 50) ----
        private static List<string> cachedRanking = null;
        private static DateTime rankingStamp = DateTime.MinValue;

        public static string NormalizeMutationName(string s)
        {
            if (string.IsNullOrEmpty(s)) return "";
            var sb = new StringBuilder();
            foreach (char ch in s) if (char.IsLetterOrDigit(ch)) sb.Append(char.ToLowerInvariant(ch));
            return sb.ToString();
        }

        public static string OptionHead(string option)
        {
            string s = option ?? "";
            try { s = ConsoleLib.Console.ColorUtility.StripFormatting(s); } catch { }
            int i = s.IndexOf(" - ", StringComparison.Ordinal);
            if (i >= 0) s = s.Substring(0, i);
            s = Regex.Replace(s, @"\s*\(\d+\)\s*$", "");
            return s.Trim();
        }

        // mutation_ranking.txt: one mutation name per line (class or display name), best first; '#' lines are comments.
        private static List<string> LoadRanking()
        {
            try
            {
                string path = AIPlayerTurnPatch.ExchangeFile("mutation_ranking.txt");
                if (!File.Exists(path)) return cachedRanking;
                DateTime stamp = File.GetLastWriteTimeUtc(path);
                if (stamp != rankingStamp)
                {
                    var list = new List<string>();
                    foreach (string line in File.ReadAllLines(path, Encoding.UTF8))
                    {
                        string tl = line.Trim();
                        if (tl.Length == 0 || tl.StartsWith("#")) continue;
                        list.Add(NormalizeMutationName(tl));
                    }
                    cachedRanking = list;
                    rankingStamp = stamp;
                }
            }
            catch { }
            return cachedRanking;
        }

        public static bool Prefix(
            string Title,
            string Intro,
            IReadOnlyList<string> Options,
            int DefaultSelected,
            Action<int> OnResult,
            ref int __result)
        {
            if (File.Exists(AIPlayerTurnPatch.FlagFile))
            {
                if (Options == null || Options.Count == 0)
                {
                    __result = -1;
                    return false;
                }

                int chosenIndex = -1;
                string chosenReason = "default";

                // Option text looks like "Burrowing Claws - You bear spade-like claws..." or "Heightened Quickness (1)". Compare by
                // normalized head (letters and digits, lower case) so class names (LightManipulation), display names (Light
                // Manipulation) and "Double-muscled" / "DoubleMuscled" all match. The old substring match never matched class names.
                var heads = new List<string>();
                for (int i = 0; i < Options.Count; i++) heads.Add(OptionHead(Options[i]));
                var norm = heads.Select(h => NormalizeMutationName(h)).ToList();

                // 1. A specific mutation requested by the brain command (AUTOLEVEL_BUY_MUTATION:<name>)
                if (!string.IsNullOrEmpty(AIPlayerTurnPatch.PreferredMutation))
                {
                    string want = NormalizeMutationName(AIPlayerTurnPatch.PreferredMutation);
                    for (int i = 0; i < norm.Count; i++)
                    {
                        if (norm[i].Length > 0 && norm[i] == want) { chosenIndex = i; chosenReason = "requested by the brain"; break; }
                    }
                }

                // 2. Mutation picker: the ranking Python publishes for the detected build (mutation_ranking.txt), then the built-in list
                bool isMutationPicker = (Intro != null && (Intro.IndexOf("mutation", StringComparison.OrdinalIgnoreCase) >= 0 || Intro.IndexOf("advance", StringComparison.OrdinalIgnoreCase) >= 0))
                                         || (Title != null && (Title.IndexOf("mutation", StringComparison.OrdinalIgnoreCase) >= 0 || Title.IndexOf("advance", StringComparison.OrdinalIgnoreCase) >= 0));

                if (chosenIndex < 0 && Options.Count > 1 && isMutationPicker)
                {
                    var ranking = LoadRanking();
                    int bestRank = int.MaxValue;
                    if (ranking != null)
                    {
                        for (int i = 0; i < norm.Count; i++)
                        {
                            int r = norm[i].Length > 0 ? ranking.IndexOf(norm[i]) : -1;
                            if (r >= 0 && r < bestRank) { bestRank = r; chosenIndex = i; }
                        }
                        if (chosenIndex >= 0) chosenReason = "build ranking #" + (bestRank + 1);
                    }
                    if (chosenIndex < 0)
                    {
                        foreach (string p in MutationPriorities)
                        {
                            string np = NormalizeMutationName(p);
                            for (int i = 0; i < norm.Count; i++)
                            {
                                if (norm[i].Length > 0 && norm[i] == np) { chosenIndex = i; chosenReason = "built-in list"; break; }
                            }
                            if (chosenIndex >= 0) break;
                        }
                    }
                }

                // 3. Fallback: default selected or 0
                if (chosenIndex < 0)
                {
                    chosenIndex = (DefaultSelected >= 0 && DefaultSelected < Options.Count) ? DefaultSelected : 0;
                }

                __result = chosenIndex;
                try { OnResult?.Invoke(chosenIndex); } catch { }

                string chosenText = (chosenIndex >= 0 && chosenIndex < Options.Count) ? Options[chosenIndex] : "";
                try { chosenText = ConsoleLib.Console.ColorUtility.StripFormatting(chosenText); } catch { }
                if (chosenText.Length > 60) chosenText = chosenText.Substring(0, 60) + "...";

                string logMsg = $"{{G|[AI Autonomous Choice] Picked option {chosenIndex}: '{chosenText}'}}";
                MessageQueue.AddPlayerMessage(logMsg);
                UnityEngine.Debug.Log($"[QudAI AIPickOptionPatch] Intro: '{Intro}', Picked [{chosenIndex}]: {chosenText}");
                UnityEngine.Debug.Log("[QudAI MutationChoice] options: " + string.Join(" | ", heads.Select((h, k) => "[" + k + "] " + h)) + " -> chose [" + chosenIndex + "] (" + chosenReason + ")");
                return false;
            }
            return true;
        }
    }
}