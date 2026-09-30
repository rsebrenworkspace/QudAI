import os
import time
import json
import re
import threading
import requests
from collections import deque, defaultdict
import chronicler
import twitch_bot
import build_templates

# Paths
EXCHANGE_DIR = r"C:\Users\rsebr\AppData\LocalLow\Freehold Games\CavesOfQud\QudAI"
STATE_FILE = os.path.join(EXCHANGE_DIR, "state.json")
ACTION_FILE = os.path.join(EXCHANGE_DIR, "action.json")
FLAG_FILE = os.path.join(EXCHANGE_DIR, "active.flag")
DEATH_FILE = os.path.join(EXCHANGE_DIR, "death.json")

# LM Studio Config
LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
LM_STUDIO_MODELS_URL = "http://localhost:1234/v1/models"

# Pacing and Thresholds
EXPLORE_STEP_DELAY = 0.25  # Seconds per exploration turn (250ms makes movement comfortable to watch)
COMBAT_STEP_DELAY = 0.20   # Seconds per combat action
REST_HP_THRESHOLD = 0.75   # Only rest when HP drops below 75% of max HP

if not os.path.exists(EXCHANGE_DIR):
    os.makedirs(EXCHANGE_DIR)

if os.path.exists(FLAG_FILE):
    try:
        os.remove(FLAG_FILE)
    except OSError:
        pass

CARDINAL_OFFSETS = {
    "NW": (-1, -1), "N":  (0, -1), "NE": (1, -1),
    "W":  (-1, 0),                 "E":  (1, 0),
    "SW": (-1, 1),  "S":  (0, 1),  "SE": (1, 1),
}

OPPOSITE_DIR = {
    "N": "S", "S": "N", "E": "W", "W": "E",
    "NE": "SW", "SW": "NE", "NW": "SE", "SE": "NW"
}

ENVIRONMENTAL_TERRAIN = [
    "watervine", "tree", "trunk", "bush", "shrub", "reed", "grass",
    "door", "stairs", "wall", "rock", "boulder", "chest", "fence", "chasm"
]

ai_active = False
move_history = deque(maxlen=8)
recent_actions = deque(maxlen=40)
recent_positions = deque(maxlen=10)
stuck_autoexplore_zones = set()
blocked_coords = set()
visit_counts = defaultdict(int)

NON_COMBAT_KEYWORDS = {
    "camp", "harvest", "butcher", "cook", "tinker", "disassemble",
    "look", "chat", "talk", "sleep", "wait", "ritual", "worship", "pray",
    "clairvoyance", "ambientlight", "ambient light", "berate"
}

DIRECTIONAL_ABILITIES = {
    "freezingray", "flamingray", "spitpoison", "teleportother", "teleport other",
    "teleport", "charge", "meleecharge", "lunge", "slam", "juke", "jump",
    "lase", "stunningforce", "stunning force", "cryokinesis", "pyrokinesis",
    "syphonvim", "syphon vim", "forcewall", "force wall", "proselytize", "beguile"
}

MELEE_TARGETED_ABILITIES = {
    "dismember", "swipe", "cleave", "decapitate", "hookanddrag"
}

PROSELYTIZE_EXCLUSIONS = {
    "plant", "watervine", "glowpad", "tree", "bush", "vine", "fungus", "fungi",
    "stalk", "brimestalk", "brinestalk", "starapple", "apple", "fern", "root", "dreadroot",
    "lichen", "moss", "shroom", "mushroom", "flower", "leaf", "leaves", "wood", "log",
    "boulder", "rock", "stone", "chasm", "fence", "grass", "reed", "shrub", "algae",
    "coral", "strangler", "spore", "seed",
    "turret", "robot", "chest", "door", "wall", "corpse", "slime", "ooze"
}


CHARMED_COMPANION_NAMES = set()
CHARMED_COMPANION_COORDS = set()


def is_companion_name(ename, comp_names):
    """Checks if an entity name strictly matches a known companion name or full creature species."""
    if not ename or not comp_names:
        return False
    elower = ename.strip().lower()
    for cn in comp_names:
        if not cn:
            continue
        cn_lower = cn.strip().lower()
        if elower == cn_lower:
            return True
        if elower.endswith(" " + cn_lower) or cn_lower.endswith(" " + elower):
            return True
    return False


def register_companion(name=None, coord=None):
    """Registers an allied companion into memory for 0-latency friendly fire immunity."""
    if name:
        clean = name.strip().lower()
        clean = re.sub(r'\{\{[^}]*\}\}', '', clean).strip()
        # Strictly reject non-creatures, liquids, terrain, and plants
        if any(bad in clean for bad in ["pool of", "puddle of", "dram", "drams", "ground", "wall", "watervine", "glowpad", "brinestalk", "rules"]):
            return
        if clean:
            CHARMED_COMPANION_NAMES.add(clean)
    if coord and coord[0] is not None and coord[1] is not None:
        CHARMED_COMPANION_COORDS.add((coord[0], coord[1]))


def is_peaceful_npc(name, blueprint=None):
    """
    Identifies conversational NPCs, quest givers, wardens, merchants, and peaceful citizens
    who must never be treated as combat enemies, attacked, or harassed with offensive abilities.
    """
    if not name:
        return False
    nl = name.lower()
    bp = (blueprint or "").lower()
    combined = f"{nl} {bp}"

    # Explicit hostile factions/monsters that might contain words like priest, guard, or convert
    hostile_overrides = [
        "snapjaw", "raider", "cannibal", "goatfolk", "cultist", "putus", "templar",
        "issachari", "chaun", "glowpad", "glowfish"
    ]
    if any(h in combined for h in hostile_overrides):
        return False

    peaceful_keywords = [
        "farmer", "warden", "elder", "convert", "zealot", "merchant", "trader",
        "dromad", "pariah", "villager", "citizen", "settler", "irudad", "yrame", "mehmet",
        "argyve", "tam", "obsessionist", "priest", "preacher", "hindren", "kesehind",
        "barathrumite", "barathrum", "q-girl", "jacob", "esther", "sheba", "tinkerer",
        "apothecary", "water merchant", "mayor", "councillor", "cantor", "scribe",
        "archivist", "librarian", "domestic pig"
    ]
    return any(pk in combined for pk in peaceful_keywords)


def is_proselytizable(entity, companions=None):
    """Checks if an entity is a biological living creature with a mind capable of being proselytized."""
    if not entity or not isinstance(entity, dict):
        return False
    if entity.get("is_companion", False):
        return False
    if entity.get("can_proselytize") is False:
        return False
    ename = entity.get("name", "").lower()
    bp = entity.get("blueprint", "").lower()
    if is_peaceful_npc(ename, bp):
        return False
    combined = f"{ename} {bp}"
    if any(ex in combined for ex in PROSELYTIZE_EXCLUSIONS):
        return False
    if is_companion_name(ename, CHARMED_COMPANION_NAMES):
        return False
    etx, ety = entity.get("tx"), entity.get("ty")
    if (etx, ety) in CHARMED_COMPANION_COORDS:
        return False
    if companions:
        comp_coords = {(c.get("tx"), c.get("ty")) for c in companions if c.get("tx") is not None and c.get("ty") is not None}
        if (etx, ety) in comp_coords:
            return False
        comp_names = {c.get("name", "").lower() for c in companions if c.get("name")}
        if is_companion_name(ename, comp_names):
            return False
    return True


def is_pure_caster_or_ranged(template):
    """Returns True if the build template is a pure caster or dedicated ranged specialist."""
    if not template:
        return False
    cid = template.get("id", "")
    arch = template.get("archetype", "").lower()
    pref_range = template.get("preferred_range", 4)
    if cid in ("esper_ited_away", "esper_mindflayer", "uncle_iroh", "gas_giant", "bullet_specter", "gunkin"):
        return True
    if any(k in arch for k in ["sorcerer", "caster", "pistoleer", "leadstorm", "gunslinger"]):
        return True
    return pref_range >= 5


current_zone_id = None
zone_step_count = 0
last_action = None
last_hp = None
consecutive_kites = 0
active_model_id = None
twitch_manager = None

action_repeat_count = 0
last_executed_action = None
last_executed_pos = None


def detect_lm_studio_model():
    global active_model_id
    try:
        res = requests.get(LM_STUDIO_MODELS_URL, timeout=3)
        if res.status_code == 200:
            data = res.json().get("data", [])
            if data:
                active_model_id = data[0]["id"]
                print(f"[LM Studio Connected] Active model: {active_model_id}")
                return active_model_id
    except Exception as e:
        print(f"[LM Studio Warning] Could not reach LM Studio on port 1234: {e}")
    return None


def input_listener():
    global ai_active
    while True:
        input()
        ai_active = not ai_active
        if ai_active:
            try:
                with open(FLAG_FILE, "w", encoding="utf-8") as f:
                    f.write("active")
            except OSError:
                pass
            print("\n>>> [AI ENGAGED] Autonomous Driver Active. Press Enter to pause. <<<\n")
        else:
            if os.path.exists(FLAG_FILE):
                try:
                    os.remove(FLAG_FILE)
                except OSError:
                    pass
            print("\n>>> [AI PAUSED] Manual control restored. Press Enter to resume. <<<\n")


def get_step_direction(from_pos, to_pos):
    fx, fy = from_pos
    tx, ty = to_pos
    dx = tx - fx
    dy = ty - fy

    step_x = 1 if dx > 0 else (-1 if dx < 0 else 0)
    step_y = 1 if dy > 0 else (-1 if dy < 0 else 0)

    for dir_name, (ox, oy) in CARDINAL_OFFSETS.items():
        if ox == step_x and oy == step_y:
            return dir_name
    return "N"


def get_valid_moves(surroundings, cur_pos, last_failed_action, is_in_combat=False):
    valid = []
    companion_moves = []
    px, py = cur_pos

    for dir_key, (dx, dy) in CARDINAL_OFFSETS.items():
        move_name = f"MOVE_{dir_key}"
        text = surroundings.get(dir_key, "").lower()
        target_pos = (px + dx, py + dy)

        if target_pos in blocked_coords or move_name == last_failed_action:
            continue
        has_bridge = "bridge" in text
        if any(w in text for w in ["wall", "rock", "chasm", "[blocked"]):
            continue
        if not has_bridge and any(w in text for w in ["deep pool", "deep water", "deep liquid"]):
            continue
        # During active combat, avoid blindly fleeing off the map into unknown zones
        if is_in_combat and ("[zone_exit" in text or "exit" in text):
            continue

        # If a friendly companion occupies this adjacent cell, avoid bumping into them
        if target_pos in CHARMED_COMPANION_COORDS or "[companion" in text:
            companion_moves.append(move_name)
            continue

        valid.append(move_name)

    # If all open tiles are blocked, allow swapping with companion if available
    if not valid and companion_moves:
        return companion_moves

    # Emergency: if all moves are zone exits and we have no other escape, allow zone exit
    if is_in_combat and not valid:
        for dir_key, (dx, dy) in CARDINAL_OFFSETS.items():
            move_name = f"MOVE_{dir_key}"
            text = surroundings.get(dir_key, "").lower()
            target_pos = (px + dx, py + dy)
            if target_pos in blocked_coords or move_name == last_failed_action:
                continue
            has_bridge = "bridge" in text
            if any(w in text for w in ["wall", "rock", "chasm", "[blocked"]):
                continue
            if not has_bridge and any(w in text for w in ["deep pool", "deep water", "deep liquid"]):
                continue
            valid.append(move_name)

    return valid


OFFSETS_5X5 = [
    [('NW2', -2, -2), ('NNW', -1, -2), ('NN', 0, -2), ('NNE', 1, -2), ('NE2', 2, -2)],
    [('WNW', -2, -1), ('NW', -1, -1),  ('N', 0, -1),  ('NE', 1, -1),  ('ENE', 2, -1)],
    [('WW', -2, 0),   ('W', -1, 0),    ('CENTER', 0, 0), ('E', 1, 0),  ('EE', 2, 0)],
    [('WSW', -2, 1),  ('SW', -1, 1),   ('S', 0, 1),   ('SE', 1, 1),   ('ESE', 2, 1)],
    [('SW2', -2, 2),  ('SSW', -1, 2),  ('SS', 0, 2),  ('SSE', 1, 2),  ('SE2', 2, 2)]
]


def render_5x5_grid(surroundings):
    def get_sym(text, is_center):
        if is_center:
            return '@'
        t = text.lower()
        if '[companion' in t:
            return 'C'
        if '[enemy' in t:
            return 'E'
        if '[npc' in t:
            return 'N'
        if '[hazard' in t or any(h in t for h in ['acid', 'lava', 'magma', 'convalessence']):
            return '!'
        if '[blocked' in t or 'wall' in t or 'rock' in t or 'fence' in t or 'boulder' in t or 'deep pool' in t or 'deep water' in t or 'deep liquid' in t:
            return '#'
        if 'door' in t:
            return '+'
        if '[item' in t:
            return '$'
        if 'exit' in t:
            return '|'
        if 'water' in t or 'pool' in t or 'puddle' in t:
            return '~'
        return '.'

    rows = []
    for r in OFFSETS_5X5:
        chars = [get_sym(surroundings.get(k, ''), (dx == 0 and dy == 0)) for (k, dx, dy) in r]
        rows.append('  ' + ' '.join(chars))
    return '\n'.join(rows)


def get_adjacent_threats(surroundings, companions=None):
    adj = {}
    comp_names = set(CHARMED_COMPANION_NAMES)
    if companions:
        for c in companions:
            cname = c.get("name", "").strip().lower()
            if cname:
                comp_names.add(cname)

    for d in ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]:
        text = surroundings.get(d, "")
        if "[COMPANION:" in text or "[companion" in text.lower():
            continue
        if "[NPC:" in text or "[npc:" in text.lower():
            continue
        if "[ENEMY:" in text:
            m = re.search(r"\[ENEMY:\s*([^\]]+)\]", text)
            ename = m.group(1).strip() if m else "Enemy"
            if is_companion_name(ename, comp_names):
                continue
            if is_peaceful_npc(ename):
                continue
            adj[d] = ename
    return adj


def filter_hostile_enemies(entities, companions=None):
    """
    Strictly filters a list of entities to only include true hostiles.
    Companions, pets, followers, and peaceful NPCs/citizens are permanently excluded.
    """
    if not entities:
        return []
    comp_coords = set(CHARMED_COMPANION_COORDS)
    comp_names = set(CHARMED_COMPANION_NAMES)
    if companions:
        for c in companions:
            cx, cy = c.get("tx"), c.get("ty")
            if cx is not None and cy is not None:
                comp_coords.add((cx, cy))
            cname = c.get("name", "").strip().lower()
            if cname:
                comp_names.add(cname)

    result = []
    for e in entities:
        if not e.get("is_enemy", False):
            continue
        if e.get("is_companion", False):
            continue
        if (e.get("tx"), e.get("ty")) in comp_coords:
            continue
        ename = e.get("name", "")
        bp = e.get("blueprint", "")
        if is_companion_name(ename, comp_names):
            continue
        if is_peaceful_npc(ename, bp):
            continue
        result.append(e)
    return result


def is_ability_ready(ab):
    """Checks if an ability is enabled, usable, off cooldown, and has available charges (not '0 charges')."""
    if not ab or not ab.get("usable", True) or ab.get("cooldown", 0) > 0 or ab.get("active", False):
        return False
    name = ab.get("name", "").lower()
    # Check for depleted charges like 'Lase (0 charges)'
    if "0 charge" in name or "(0 charges)" in name:
        return False
    return True


def find_ready_ability(abilities, keywords):
    """Finds an enabled, usable ability off cooldown matching any keyword in name or command."""
    for ab in abilities:
        if is_ability_ready(ab):
            name = ab.get("name", "").lower()
            cmd = ab.get("command", "").lower()
            if any(k in name or k in cmd for k in keywords):
                return ab
    return None


def bresenham_line(x0, y0, x1, y1):
    """
    Standard Bresenham line algorithm generating all integer grid coordinates
    from (x0, y0) to (x1, y1) inclusive.
    """
    points = []
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy

    cx, cy = x0, y0
    while True:
        points.append((cx, cy))
        if cx == x1 and cy == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            cx += sx
        if e2 < dx:
            err += dx
            cy += sy
    return points


def is_line_of_fire_clear(from_pos, to_pos, companions=None, blocked_set=None):
    """
    Checks if a direct ray from from_pos to to_pos is unblocked.
    Returns (is_clear: bool, reason: str).
    - If target coordinate is itself a companion, returns (False, f"Target coordinate ({x1}, {y1}) IS friendly companion {comp_name}!").
    - If any companion's tile lies strictly between from_pos and to_pos,
      returns (False, f"Blocked by companion {comp_name} at {pt}").
    - If any known solid wall/obstacle lies strictly between from_pos and to_pos,
      returns (False, f"Blocked by obstacle at {pt}").
    """
    x0, y0 = from_pos
    x1, y1 = to_pos
    if x0 == x1 and y0 == y1:
        return True, "Adjacent/Self"

    comp_map = {}
    if companions:
        for c in companions:
            cx, cy = c.get("tx", -1), c.get("ty", -1)
            if cx >= 0 and cy >= 0:
                comp_map[(cx, cy)] = c.get("name", "Companion")
    for pt in CHARMED_COMPANION_COORDS:
        if pt not in comp_map:
            comp_map[pt] = "Allied Pet"

    # Guardrail: Never aim direct rays or missile attacks directly at friendly companions!
    if (x1, y1) in comp_map:
        return False, f"Target coordinate ({x1}, {y1}) IS friendly companion {comp_map[(x1, y1)]}!"

    line = bresenham_line(x0, y0, x1, y1)
    # Check intermediate points (exclude origin and target)
    intermediate = line[1:-1]

    for pt in intermediate:
        if pt in comp_map:
            return False, f"Line of fire obstructed by friendly companion {comp_map[pt]} at {pt}!"
        if blocked_set and pt in blocked_set:
            return False, f"Line of fire obstructed by obstacle at {pt}"

    return True, "Clear"


def is_ignorable_stationary_enemy(e):
    """
    Determines if an enemy is a distant stationary trivial entity (e.g. glowpads, harmless fungi,
    distant roots/plants) that should not lock the AI into combat mode or interrupt autoexplore.
    """
    name = e.get("name", "").lower()
    dist = e.get("dist", 999)
    diff = e.get("difficulty", "")
    is_stat = e.get("is_stationary", False) or any(k in name for k in [
        "glowpad", "plant", "fungus", "lichen", "brimestalk", "root", "vine", "seaweed", "lily", "pad"
    ])

    # If adjacent (dist <= 1), never ignore
    if dist <= 1:
        return False

    # Never ignore turrets or mechanical defense emplacements!
    if any(t in name for t in ["turret", "gun", "cannon", "rocket", "mortar", "idol", "statue"]):
        return False

    # Never ignore tough, very tough, or impossible hostiles!
    if diff in ("Tough", "Very Tough", "Impossible"):
        return False

    # If stationary and trivial/easy/average, ignore for combat lock at distance > 3
    if is_stat and dist > 3 and diff in ("Trivial", "Easy", "Average", ""):
        return True

    # Aquatic creatures swimming in isolated pools (glowfish, etc.) cannot traverse dry land.
    # At distance > 3, ignore them so the AI doesn't break exploration to charge across town into ponds!
    if "swimming" in name and dist > 3 and diff in ("Trivial", "Easy", "Average", ""):
        return True

    return False


def query_llm_decision(game_state, enemies, valid_moves, abilities, template=None, took_damage=False):
    """Invokes LM Studio for high-level tactical combat decisions tailored to the character class."""
    global active_model_id
    if not active_model_id:
        active_model_id = detect_lm_studio_model()
    if not active_model_id:
        return None

    if template is None:
        template = build_templates.detect_build(game_state)

    companions = game_state.get("companions", [])
    enemies = filter_hostile_enemies(enemies, companions)

    px = game_state.get("x", 0)
    py = game_state.get("y", 0)
    hp = game_state.get("hp", 0)
    max_hp = game_state.get("max_hp", 1)
    ammo = game_state.get("missile_ammo", 0)
    max_ammo = game_state.get("missile_max_ammo", 0)
    inv_ammo = game_state.get("inventory_ammo", 0)
    has_mw = game_state.get("has_missile_weapon", False)
    effects = game_state.get("effects", [])
    surroundings = game_state.get("surroundings", {})
    is_sprinting = game_state.get("is_sprinting", False) or any(e in ef.lower() for ef in effects for e in ["running", "sprint"])
    sprint_ab = next((ab for ab in abilities if "sprint" in ab.get("name", "").lower() or "sprint" in ab.get("command", "").lower()), None)
    can_sprint = (not is_sprinting) and (sprint_ab is not None) and sprint_ab.get("usable", True) and sprint_ab.get("cooldown", 0) <= 0
    is_caster_or_ranged = is_pure_caster_or_ranged(template)
    is_bleeding = any("bleed" in str(ef).lower() for ef in effects)

    adj_threats = get_adjacent_threats(surroundings, companions=companions)
    grid_ascii = render_5x5_grid(surroundings)

    # Format threat list (including directly adjacent threats from 5x5 scan)
    threat_lines = []
    for d, ename in adj_threats.items():
        threat_lines.append(f"- [MELEE THREAT] {ename} directly {d} (Distance 1!)")
    for e in enemies[:4]:
        name = e.get("name", "Unknown")
        dist = e.get("dist", 0)
        direction = e.get("dir", "?")
        tx = e.get("tx", 0)
        ty = e.get("ty", 0)
        diff = e.get("difficulty", "Average")
        lvl = e.get("level", 1)
        stat_tag = " [Stationary]" if e.get("is_stationary") else ""
        if dist > 1:
            threat_lines.append(f"- [{diff.upper()}{stat_tag}] {name} (Lvl {lvl}) at ({tx}, {ty}), dist: {dist} ({direction})")

    if threat_lines:
        threat_str = "\n".join(threat_lines)
    elif took_damage:
        threat_str = "[!] UNSEEN HOSTILE ATTACKER (Active threat firing from beyond sight or concealed!)"
    else:
        threat_str = "None in direct sight"

    # Format ready combat abilities
    ready_abilities = []
    for ab in abilities:
        if is_ability_ready(ab):
            name = ab.get("name", "")
            cmd = ab.get("command", "")
            combined = f"{name} {cmd}".lower()
            if any(nc in combined for nc in NON_COMBAT_KEYWORDS):
                continue
            if "sprint" in combined:
                if can_sprint:
                    ready_abilities.append("- Sprint: Ready (Action: ACTIVATE_SPRINT)")
            elif name and cmd:
                ready_abilities.append(f"- {name}: Ready (Action: USE_ABILITY:{cmd})")
        elif "0 charge" in ab.get("name", "").lower():
            ready_abilities.append(f"- {ab.get('name')}: Empty charges (Recharging...)")
    if is_sprinting:
        ready_abilities.append("- Sprinting: ACTIVE (+Double Move Speed!)")
    ability_str = "\n".join(ready_abilities) if ready_abilities else "None off cooldown"

    # Assemble possible valid actions
    open_moves = [vm for vm in valid_moves if vm[5:] not in adj_threats]
    action_choices = []

    if is_sprinting:
        # SPRINT ACTIVE: Use double move speed to escape/kite into open ground!
        if adj_threats and open_moves:
            for vm in open_moves:
                vdir = vm[5:]
                action_choices.append(f"{vm} (Sprint Retreat {vdir} into open ground)")
        else:
            if has_mw and ammo > 0 and enemies and not adj_threats:
                closest = enemies[0]
                action_choices.append(f"FIRE_MISSILE@{closest.get('tx')},{closest.get('ty')} (Ranged Snipe {closest.get('name')} at dist {closest.get('dist')})")
            for vm in open_moves:
                vdir = vm[5:]
                action_choices.append(f"{vm} (Sprint Maneuver {vdir})")
            for d, ename in adj_threats.items():
                if not is_caster_or_ranged:
                    action_choices.append(f"MOVE_{d} (Melee Attack {ename})")
                else:
                    action_choices.append(f"MOVE_{d} (Sprint Disengage past {ename})")
    else:
        closest = enemies[0] if enemies else None
        c_dist = closest.get("dist", 999) if closest else 999
        c_name = closest.get("name", "Enemy") if closest else "Enemy"
        c_tx = closest.get("tx", px) if closest else px
        c_ty = closest.get("ty", py) if closest else py
        s_dir = get_step_direction((px, py), (c_tx, c_ty)) if closest else ""

        # 0. PET RECRUITMENT: Proselytize / Beguile adjacent beasts or humanoids (HIGHEST PRIORITY IF NO PET!)
        companions = game_state.get("companions", [])
        has_companion = game_state.get("has_companion", False) or bool(companions)
        if not has_companion:
            for ab in abilities:
                if is_ability_ready(ab) and ab.get("command"):
                    name = ab.get("name", "")
                    cmd = ab.get("command", "")
                    combined = f"{name} {cmd}".lower()
                    if "proselytize" in combined or "beguile" in combined:
                        for ent in game_state.get("visible_entities", []):
                            if ent.get("dist") == 1 and is_proselytizable(ent, companions=companions):
                                edir = ent.get("dir", "")
                                ename = ent.get("name", "Creature")
                                if edir:
                                    action_choices.append(f"USE_ABILITY:{cmd}:{edir} (RECRUIT PET: Proselytize adjacent {ename} {edir} to become your permanent combat companion & frontline tank!)")

        # Check line-of-fire from player to primary target
        c_lof_clear, c_lof_reason = is_line_of_fire_clear((px, py), (c_tx, c_ty), companions=companions, blocked_set=blocked_coords)

        # 1. RANGED ATTACKS: Missile Fire & Ranged Mental/Beam Abilities (HIGHEST PRIORITY)
        # A. Missile Fire (Requires clear line of fire past companions)
        if has_mw and ammo > 0 and enemies and c_lof_clear:
            if not adj_threats:
                action_choices.append(f"FIRE_MISSILE@{c_tx},{c_ty} (Ranged Snipe {c_name} at dist {c_dist} - SAFE RANGED ATTACK)")
            elif len(adj_threats) == 1 and not open_moves:
                action_choices.append(f"FIRE_MISSILE@{c_tx},{c_ty} (Point-blank blast at {c_name})")

        # B. Ranged Mental & Beam Abilities (Stunning Force CC opener, Sunder Mind execution, Lase sustained DPS, etc.)
        for ab in abilities:
            if is_ability_ready(ab) and ab.get("command"):
                name = ab.get("name", "")
                cmd = ab.get("command", "")
                combined = f"{name} {cmd}".lower()
                if any(nc in combined for nc in NON_COMBAT_KEYWORDS) or "sprint" in combined:
                    continue

                if any(ray in combined for ray in ["freezingray", "flamingray", "spitpoison", "cryokinesis", "pyrokinesis", "lase", "stunningforce", "stunning force", "syphonvim", "syphon vim", "sundermind", "sunder mind", "chainfire", "disarmingshot"]):
                    if closest and c_dist <= 25 and s_dir:
                        is_beam = any(b in combined for b in ["lase", "ray", "spit", "stunning"])
                        if is_beam and not c_lof_clear:
                            # Do not offer beam attack if friendly companion is in the ray path!
                            continue
                        if "stunning" in combined:
                            action_choices.append(f"USE_ABILITY:{cmd}:{s_dir} (Cast Stunning Force concussive blast - OPENER CC: Stun & knock back {c_name} {s_dir})")
                        elif "sunder" in combined:
                            action_choices.append(f"USE_ABILITY:{cmd}:{s_dir} (Channel Sunder Mind against {c_name} {s_dir} - HEAVY MENTAL EXECUTION [Safe over pets])")
                        elif "lase" in combined:
                            action_choices.append(f"USE_ABILITY:{cmd}:{s_dir} (Focus Light Manipulation laser beam at {c_name} {s_dir} - SUSTAINED BEAM DPS)")
                        elif "chainfire" in combined:
                            action_choices.append(f"USE_ABILITY:{cmd} (Unleash Chain Fire lead storm - HIGH BURST VOLLEY)")
                        elif "disarmingshot" in combined:
                            action_choices.append(f"USE_ABILITY:{cmd}:{s_dir} (Disarming Shot at {c_name} {s_dir} - WEAPON DENIAL)")
                        elif "freezingray" in combined or "freezing ray" in combined:
                            action_choices.append(f"USE_ABILITY:{cmd}:{s_dir} (Cast Freezing Ray at {c_name} {s_dir} - FREEZE CC)")
                        else:
                            action_choices.append(f"USE_ABILITY:{cmd}:{s_dir} (Cast {name} at {c_name} {s_dir})")

        # 2. MELEE ATTACKS & MELEE-TARGETED ABILITIES
        # A. Bump Melee strikes on adjacent enemies
        if not is_caster_or_ranged:
            for d, ename in adj_threats.items():
                action_choices.append(f"MOVE_{d} (Melee Attack {ename})")
        else:
            # Pure casters and ranged specialists must NEVER voluntarily melee bump-attack enemies with frail weapons
            has_defensive_ability = any(
                is_ability_ready(ab) and any(db in (f"{ab.get('name')} {ab.get('command')}").lower() for db in ["force bubble", "force wall", "teleport other", "intimidate", "phasing", "teleportation"])
                for ab in abilities
            )
            if not open_moves and not can_sprint and not has_defensive_ability:
                for d, ename in adj_threats.items():
                    action_choices.append(f"MOVE_{d} (DESPERATE LAST RESORT: Cornered melee strike on {ename} with wooden staff)")

        # B. Melee targeted abilities (Dismember, Cleave, Shield Slam, Swipe) & Gap-closers
        for ab in abilities:
            if is_ability_ready(ab) and ab.get("command"):
                name = ab.get("name", "")
                cmd = ab.get("command", "")
                combined = f"{name} {cmd}".lower()
                if any(nc in combined for nc in NON_COMBAT_KEYWORDS) or "sprint" in combined:
                    continue

                if any(mta in combined for mta in ["dismember", "cleave", "shieldslam", "slam", "swipe", "decapitate"]):
                    if adj_threats:
                        for d, ename in adj_threats.items():
                            action_choices.append(f"USE_ABILITY:{cmd}:{d} (Execute {name} on {ename} {d} - MELEE BURST & BLEED)")
                elif any(cg in combined for cg in ["charge", "meleecharge", "chargingstrike", "lunge"]):
                    if closest and 2 <= c_dist <= 4 and not adj_threats and s_dir:
                        action_choices.append(f"USE_ABILITY:{cmd}:{s_dir} (Charge at {c_name} {s_dir} - GAP-CLOSER OPENER: Close gap & daze)")
                elif any(touch in combined for touch in ["teleportother", "teleport other"]):
                    if adj_threats:
                        for td, tename in adj_threats.items():
                            action_choices.append(f"USE_ABILITY:{cmd}:{td} (EMERGENCY BANISH: Cast Teleport Other to banish adjacent {tename} {td} across map)")
                    elif closest and c_dist <= 1 and s_dir:
                        action_choices.append(f"USE_ABILITY:{cmd}:{s_dir} (EMERGENCY BANISH: Cast Teleport Other on adjacent threat {s_dir} across map)")
                elif "disarm" in combined:
                    if adj_threats:
                        for d, ename in adj_threats.items():
                            action_choices.append(f"USE_ABILITY:{cmd}:{d} (Disarm {ename} {d})")

        # 3. DEFENSIVE & BUFF ABILITIES (Force Bubble, Phasing, Intimidate)
        for ab in abilities:
            if is_ability_ready(ab) and ab.get("command"):
                name = ab.get("name", "")
                cmd = ab.get("command", "")
                combined = f"{name} {cmd}".lower()
                if any(nc in combined for nc in NON_COMBAT_KEYWORDS) or "sprint" in combined:
                    continue
                # Skip if already handled in categories 1 or 2
                if any(k in combined for k in [
                    "freezingray", "flamingray", "spitpoison", "cryokinesis", "pyrokinesis",
                    "lase", "stunningforce", "stunning force", "syphonvim", "syphon vim", "sundermind", "sunder mind",
                    "chainfire", "disarmingshot",
                    "dismember", "cleave", "shieldslam", "slam", "swipe", "decapitate",
                    "charge", "meleecharge", "chargingstrike", "lunge",
                    "teleportother", "teleport other", "disarm",
                    "proselytize", "beguile"
                ]):
                    continue
                if "intimidate" in combined:
                    if adj_threats or (closest and c_dist <= 2):
                        action_choices.append(f"USE_ABILITY:{cmd} (EMERGENCY FEAR: Terrify close threats with Intimidate)")
                else:
                    action_choices.append(f"USE_ABILITY:{cmd} (Activate {name} - DEFENSIVE BARRIER)")

        # 4. RELOADING: Strictly forbidden in melee range
        if has_mw and ammo < max_ammo and inv_ammo > 0 and not adj_threats:
            action_choices.append("RELOAD")

        # 5. SPRINT ESCAPES: Only when adjacent to melee threats
        if can_sprint and adj_threats and open_moves:
            for vm in open_moves:
                vdir = vm[5:]
                action_choices.append(f"SPRINT_{vdir} (Sprint & Escape {vdir} into open ground)")
        elif can_sprint and adj_threats:
            action_choices.append("ACTIVATE_SPRINT")

        # 6. TACTICAL REPOSITIONING & MANEUVERS
        for vm in open_moves:
            vdir = vm[5:]
            if adj_threats:
                action_choices.append(f"{vm} (Retreat/Step {vdir} into open ground)")
            elif not (has_mw and ammo > 0 and enemies):
                action_choices.append(f"{vm} (Maneuver {vdir})")
            else:
                action_choices.append(f"{vm} (Reposition {vdir})")

        # 7. STANDOFF & COOLDOWN RECHARGE (Casters / Ranged)
        if is_caster_or_ranged and enemies and not adj_threats:
            action_choices.append("WAIT (Hold safe standoff distance & recharge Light Manipulation laser charges / mental cooldowns)")

        if is_caster_or_ranged and closest and c_dist <= 3 and open_moves:
            for vm in open_moves:
                vdir = vm[5:]
                dx, dy = CARDINAL_OFFSETS.get(vdir, (0, 0))
                new_dist = max(abs((px + dx) - c_tx), abs((py + dy) - c_ty))
                if new_dist > c_dist:
                    action_choices.append(f"{vm} (Kite backpedal {vdir} away from {c_name} to maintain safe standoff)")

    ancestral_lore = chronicler.format_ancestral_memory_for_prompt()
    class_name = template.get("name", "Nomad Wanderer")
    archetype = template.get("archetype", "General Combatant")
    strengths = template.get("strengths", [])
    doctrine = template.get("combat_doctrine", {})
    doctrine_name = doctrine.get("doctrine_name", "Combat Doctrine")
    open_action = doctrine.get("open_combat_action", "Engage hostile targets")
    close_policy = doctrine.get("close_contact_policy", "Manage distance")
    pref_range = template.get("preferred_range", 4)
    strengths_str = "\n".join(f"   - {s}" for s in strengths)
    rot_list = doctrine.get("ability_rotation", [])
    rot_str = "\n".join(f"   {r}" for r in rot_list) if rot_list else "   - Use class abilities when in range."

    if is_caster_or_ranged:
        rule2 = (
            "2. CASTER / RANGED ATTACK & KITING PRIORITY: Fire ranged powers (Lase, Sunder Mind, Stunning Force, Elemental Rays, Guns) "
            "whenever available. When abilities or laser charges are cooling down, MAINTAIN SAFE DISTANCE (kiting backpedal or WAIT) "
            "to let charges recharge and mental cooldowns reset. NEVER voluntarily charge into melee to strike with a frail staff! "
            "If an enemy breaches adjacent melee range, prioritize EMERGENCY DEFENSE (Teleport Other banish, Force Bubble barrier, Intimidate fear) "
            "or Sprinting/Retreating into open ground!"
        )
    else:
        rule2 = (
            "2. ATTACK PRIORITY: If an offensive action (Missile Snipe, Charge, Dismember, Cleave, or Melee Attack) is listed in VALID ACTIONS, "
            "YOU MUST ATTACK. Never waste a turn walking away when you can already strike or charge the enemy!"
        )

    system_prompt = (
        f"You are an expert tactical AI controlling a {class_name} ({archetype}) in Caves of Qud.\n"
        f"{ancestral_lore}\n\n"
        f"CLASS TACTICAL DOCTRINE ({doctrine_name.upper()} - Preferred Range: {pref_range} tiles):\n"
        f"1. PRIMARY COMBAT GOAL: {open_action}.\n"
        f"{rule2}\n"
        f"3. ABILITY ROTATION & COMBO DOCTRINE:\n{rot_str}\n"
        f"4. CLOSE CONTACT POLICY: {close_policy}.\n"
        f"5. CLASS STRENGTHS TO EXPLOIT:\n{strengths_str}\n"
        "6. DO NOT ZONE DURING COMBAT: Stay in the current tactical arena. Never run off the map into unknown zones while fighting.\n"
        "7. TARGET PRIORITY: Prioritize the highest-threat pursuer, elite, or legendary creature.\n"
        "Choose exactly ONE optimal action from the provided VALID ACTIONS list.\n"
        "Respond ONLY with valid JSON in this exact structure:\n"
        "{\n"
        '  "action": "<ACTION_STRING>",\n'
        '  "thought": "<Short tactical reason, max 20 words>"\n'
        "}"
    )

    damage_alert = ""
    if took_damage:
        damage_alert += "- COMBAT ALERT: [!HIT!] YOU TOOK DAMAGE LAST TURN! You are actively taking damage in combat!\n"
    if is_bleeding:
        damage_alert += "- CRITICAL BLEEDING ALERT: [!BLEEDING!] You are bleeding heavily! Every step or bump-attack inflicts bleed damage. Prioritize emergency defense (Teleport Other to banish adjacent enemies, Force Bubble barrier) or retreat to safe ground!\n"
    if has_mw:
        if ammo > 0:
            ammo_display = f"Loaded {ammo}/{max_ammo} (Spare inventory slugs: {inv_ammo})"
        elif inv_ammo > 0:
            ammo_display = f"Empty 0/{max_ammo} (Can reload! Spare slugs: {inv_ammo})"
        else:
            ammo_display = f"EMPTY 0/{max_ammo} [OUT OF AMMO! No slugs left in inventory. Must fight in melee or disengage!]"
    else:
        ammo_display = "None"

    if has_companion:
        comp_summary = ", ".join(f"{c.get('name')} (HP {c.get('hp')}/{c.get('max_hp')}, dist {c.get('dist')} {c.get('dir')})" for c in companions)
        pet_display = f"ACTIVE: {comp_summary} [Frontline Tank - DO NOT SHOOT YOUR PET!]"
    else:
        pet_display = "None [Use Proselytize on adjacent beasts/humanoids to recruit a combat tank!]"

    user_prompt = f"""STATUS:
- Location: {game_state.get('zone_name', 'Unknown')}
- HP: {hp}/{max_hp}
{damage_alert}- Active Combat Pet: {pet_display}
- Water: {game_state.get('water_drams', 0)} drams
- Active Effects: {', '.join(effects) if effects else 'None'}
- Missile Weapon: {ammo_display}
- Sprint Status: {'ACTIVE' if is_sprinting else 'Off'}

SURROUNDINGS (5x5 GRID - Legend: @=You, C=Companion/Pet, E=Enemy, N=Neutral/Friend, !=Hazard, #=Wall, +=Door, $=Item, ~=Shallow Water [safe ground], .=Clear):
{grid_ascii}
- Note: Shallow water/pools (~) are normal walkable marsh ground and NOT dangerous hazards.

VISIBLE HOSTILE ENEMIES:
{threat_str}

AVAILABLE ABILITIES:
{ability_str}

VALID ACTIONS:
{chr(10).join(f"- {a}" for a in action_choices)}"""

    payload = {
        "model": active_model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 128
    }

    try:
        t0 = time.time()
        res = requests.post(LM_STUDIO_URL, json=payload, timeout=6.0)
        if res.status_code == 200:
            content = res.json()["choices"][0]["message"]["content"]
            # Clean possible markdown fence
            clean = re.sub(r"^```json\s*", "", content.strip(), flags=re.IGNORECASE)
            clean = re.sub(r"^```\s*", "", clean)
            clean = re.sub(r"\s*```$", "", clean).strip()
            data = json.loads(clean)
            raw_action = data.get("action", "").strip()
            thought = data.get("thought", "").strip()

            # Sanitize action (e.g. "MOVE_N (Melee Attack snapjaw)" -> "MOVE_N")
            action = raw_action.split()[0] if raw_action else ""

            # If the LLM returned a directional ability without a direction (e.g. "USE_ABILITY:CommandLase"),
            # auto-append the closest enemy's direction so the game engine gets the exact vector!
            if action.startswith("USE_ABILITY:") and enemies:
                ab_cmd = action.split(":")[1].strip()
                if ":" not in action[12:]:
                    closest = enemies[0]
                    closest_dir = closest.get("dir")
                    if not closest_dir:
                        closest_dir = get_step_direction((px, py), (closest.get("tx", px), closest.get("ty", py)))
                    if any(d in ab_cmd.lower() for d in DIRECTIONAL_ABILITIES) or ab_cmd.lower() in DIRECTIONAL_ABILITIES:
                        action = f"USE_ABILITY:{ab_cmd}:{closest_dir}"

            # LOF Safety Guardrail: Prevent friendly fire on companions if LLM generated a beam/missile attack
            companions = game_state.get("companions", [])
            if companions and enemies:
                is_beam_or_missile = action.startswith("FIRE_MISSILE") or any(b in action.lower() for b in ["lase", "flaming", "freezing", "spit"])
                if is_beam_or_missile:
                    closest = enemies[0]
                    ctx = closest.get("tx", px)
                    cty = closest.get("ty", py)
                    clear, reason = is_line_of_fire_clear((px, py), (ctx, cty), companions=companions, blocked_set=blocked_coords)
                    if not clear:
                        ab_sunder = find_ready_ability(abilities, ["sunder mind", "sundermind", "sunder"])
                        s_dir = get_step_direction((px, py), (ctx, cty))
                        if ab_sunder and ab_sunder.get("command") and s_dir:
                            action = f"USE_ABILITY:{ab_sunder['command']}:{s_dir}"
                            thought = f"[LOF Safety Override] {reason}. Redirected to Sunder Mind."
                        elif open_moves:
                            action = open_moves[0]
                            thought = f"[LOF Safety Override] {reason}. Repositioning {open_moves[0][5:]}."

            if action:
                dt = time.time() - t0
                return {"action": action, "thought": f"[LLM in {dt:.2f}s] {thought}"}
    except Exception as e:
        print(f"[LLM Error / Timeout] {e}")

    return None


def fallback_melee(game_state, enemies, adj_threats, open_moves, valid_moves, abilities, template, cur_pos, px, py, hp, max_hp, can_sp, has_missile, ammo, max_ammo, inv_ammo):
    """Melee Bruiser & Tank Tactical Fallback (Axe Berserker / Praetorian)."""
    companions = game_state.get("companions", [])
    enemies = filter_hostile_enemies(enemies, companions)
    if companions and adj_threats:
        comp_names = {c.get("name", "").lower() for c in companions if c.get("name")}
        adj_threats = {
            d: ename for d, ename in adj_threats.items()
            if not any(cn in ename.lower() for cn in comp_names if len(cn) > 2)
        }

    closest_enemy = enemies[0] if enemies else None
    closest_dist = closest_enemy.get("dist", 999) if closest_enemy else 999
    c_name = closest_enemy.get("name", "Enemy") if closest_enemy else ""
    c_tx = closest_enemy.get("tx", px) if closest_enemy else px
    c_ty = closest_enemy.get("ty", py) if closest_enemy else py

    # 1. Critical Encirclement: Melee warriors hold ground; only retreat if HP < 35% AND surrounded by 3+ hostiles
    if hp / max(1, max_hp) < 0.35 and len(adj_threats) >= 3 and open_moves:
        best_retreat = open_moves[0]
        r_dir = best_retreat[5:]
        if can_sp:
            return {"action": f"SPRINT_{r_dir}", "reason": f"[{template['name']} Fallback] Critical HP ({hp}/{max_hp})! Sprinting {r_dir} from 3+ hostiles"}
        return {"action": best_retreat, "reason": f"[{template['name']} Fallback] Critical HP ({hp}/{max_hp})! Disengaging {r_dir}"}

    # 2. Adjacent Combat: Prioritize heavy melee abilities (Dismember, Cleave, Shield Slam, Charging Strike)
    if adj_threats:
        target_dir = list(adj_threats.keys())[0]
        target_name = adj_threats[target_dir]

        ab_strike = find_ready_ability(abilities, ["dismember", "cleave", "shieldslam", "slam", "swipe", "decapitate", "bludgeon", "backhand", "flurry"])
        if ab_strike and ab_strike.get("command"):
            cmd = ab_strike["command"]
            name = ab_strike.get("name", "Strike")
            return {"action": f"USE_ABILITY:{cmd}:{target_dir}", "reason": f"[{template['name']} Fallback] Executing {name} on adjacent {target_name} ({target_dir})"}

        # Basic melee bump-attack
        return {"action": f"MOVE_{target_dir}", "reason": f"[{template['name']} Fallback] Relentless melee strike on {target_name} ({target_dir})"}

    # 3. Gap Closer: If enemy at distance 2-4, use Charge!
    if closest_enemy and 2 <= closest_dist <= 4:
        ab_charge = find_ready_ability(abilities, ["charge", "meleecharge", "chargingstrike", "lunge"])
        s_dir = get_step_direction(cur_pos, (c_tx, c_ty))
        if ab_charge and ab_charge.get("command"):
            cmd = ab_charge["command"]
            return {"action": f"USE_ABILITY:{cmd}:{s_dir}", "reason": f"[{template['name']} Fallback] Charging {c_name} ({s_dir}) to close gap and daze target"}

        # Charge not ready -> Advance directly into melee
        step_move = f"MOVE_{s_dir}"
        if step_move in valid_moves:
            return {"action": step_move, "reason": f"[{template['name']} Fallback] Advancing into melee contact on {c_name} ({s_dir})"}

    # 4. Long-range approach or suppressive missile fire
    if closest_enemy and closest_dist <= 10:
        if closest_dist >= 6 and has_missile and ammo > 0:
            companions = game_state.get("companions", [])
            is_clear, _ = is_line_of_fire_clear((px, py), (c_tx, c_ty), companions=companions, blocked_set=blocked_coords)
            if is_clear:
                return {"action": f"FIRE_MISSILE@{c_tx},{c_ty}", "reason": f"[{template['name']} Fallback] Suppressive fire at {c_name} while closing distance"}
        s_dir = get_step_direction(cur_pos, (c_tx, c_ty))
        step_move = f"MOVE_{s_dir}"
        if step_move in valid_moves:
            return {"action": step_move, "reason": f"[{template['name']} Fallback] Pursuing {c_name} ({s_dir})"}

    if valid_moves:
        ranked = sorted(valid_moves, key=lambda m: visit_counts[(cur_pos[0] + CARDINAL_OFFSETS[m[5:]][0], cur_pos[1] + CARDINAL_OFFSETS[m[5:]][1])])
        return {"action": ranked[0], "reason": f"[{template['name']} Fallback] Maneuvering into position"}

    return {"action": "WAIT", "reason": f"[{template['name']} Fallback] Holding ground"}


def fallback_esper(game_state, enemies, adj_threats, open_moves, valid_moves, abilities, template, cur_pos, px, py, hp, max_hp, can_sp, has_missile, ammo, max_ammo, inv_ammo):
    """Pure Mental Sorcerer Tactical Fallback (Esper Mindflayer)."""
    companions = game_state.get("companions", [])
    has_companion = game_state.get("has_companion", False) or bool(companions) or bool(CHARMED_COMPANION_NAMES)
    enemies = filter_hostile_enemies(enemies, companions)
    if (companions or CHARMED_COMPANION_NAMES) and adj_threats:
        comp_names = {c.get("name", "").lower() for c in companions if c.get("name")} | CHARMED_COMPANION_NAMES
        adj_threats = {
            d: ename for d, ename in adj_threats.items()
            if not any(cn in ename.lower() for cn in comp_names if len(cn) > 2)
        }

    closest_enemy = enemies[0] if enemies else None
    closest_dist = closest_enemy.get("dist", 999) if closest_enemy else 999
    c_name = closest_enemy.get("name", "Enemy") if closest_enemy else ""
    c_tx = closest_enemy.get("tx", px) if closest_enemy else px
    c_ty = closest_enemy.get("ty", py) if closest_enemy else py
    s_dir = get_step_direction(cur_pos, (c_tx, c_ty)) if closest_enemy else ""
    is_stationary = any(st in c_name.lower() for st in ["glowpad", "plant", "turret", "fungus", "vine", "tree"])

    # 0. Pet Recruitment: If without an active companion, proselytize adjacent beasts or humanoids into combat thralls
    if not has_companion:
        ab_proselytize = find_ready_ability(abilities, ["proselytize", "beguile"])
        if ab_proselytize and ab_proselytize.get("command"):
            for ent in game_state.get("visible_entities", []):
                if ent.get("dist") == 1 and is_proselytizable(ent, companions=companions) and ent.get("dir"):
                    p_dir = ent["dir"]
                    p_name = ent.get("name", "Creature")
                    return {"action": f"USE_ABILITY:{ab_proselytize['command']}:{p_dir}", "reason": f"[{template['name']} Fallback] Proselytizing adjacent {p_name} ({p_dir}) into combat pet & frontline tank"}

    # 1. Close-Contact Emergency: Defensive Mental Shielding, Banishment & Evasion
    if adj_threats or closest_dist <= 2:
        ab_bubble = find_ready_ability(abilities, ["force bubble", "forcebubble", "bubble", "force wall", "forcewall"])
        if ab_bubble and ab_bubble.get("command"):
            return {"action": f"USE_ABILITY:{ab_bubble['command']}", "reason": f"[{template['name']} Fallback] Popping Force Bubble impenetrable barrier against close hostiles"}

        ab_banish = find_ready_ability(abilities, ["teleport other", "teleportother"])
        if ab_banish and ab_banish.get("command"):
            if adj_threats:
                t_dir = list(adj_threats.keys())[0]
                t_name = adj_threats[t_dir]
                return {"action": f"USE_ABILITY:{ab_banish['command']}:{t_dir}", "reason": f"[{template['name']} Fallback] Banishing adjacent hostile {t_name} with Teleport Other ({t_dir})"}
            elif closest_dist == 1 and s_dir:
                return {"action": f"USE_ABILITY:{ab_banish['command']}:{s_dir}", "reason": f"[{template['name']} Fallback] Banishing close hostile {c_name} with Teleport Other ({s_dir})"}

        ab_intimidate = find_ready_ability(abilities, ["intimidate"])
        if ab_intimidate and ab_intimidate.get("command"):
            return {"action": f"USE_ABILITY:{ab_intimidate['command']}", "reason": f"[{template['name']} Fallback] Terrifying close hostile with Intimidate"}

        ab_teleport = find_ready_ability(abilities, ["teleportation", "phasing"])
        if ab_teleport and ab_teleport.get("command"):
            return {"action": f"USE_ABILITY:{ab_teleport['command']}", "reason": f"[{template['name']} Fallback] Teleporting away from close hostiles"}

        if adj_threats and open_moves:
            r_dir = open_moves[0][5:]
            if can_sp:
                return {"action": f"SPRINT_{r_dir}", "reason": f"[{template['name']} Fallback] Sprint kiting away from fragile melee engagement"}
            return {"action": open_moves[0], "reason": f"[{template['name']} Fallback] Backpedaling away from melee threat"}

        # If enemy is at dist 2 (not adjacent yet) and we have open moves, kite away!
        if closest_dist <= 2 and open_moves:
            kites = [m for m in open_moves if max(abs(px + CARDINAL_OFFSETS[m[5:]][0] - c_tx), abs(py + CARDINAL_OFFSETS[m[5:]][1] - c_ty)) > closest_dist]
            if kites:
                return {"action": kites[0], "reason": f"[{template['name']} Fallback] Backpedaling to maintain safe distance ({closest_dist} -> {kites[0][5:]})"}

    # 2. Long-Range Psychic Assault (Distance >= 1)
    if closest_enemy and closest_dist >= 1:
        # Check line-of-fire from player to primary target
        c_lof_clear, c_lof_reason = is_line_of_fire_clear((px, py), (c_tx, c_ty), companions=companions, blocked_set=blocked_coords)

        # A. Sunder Mind (Uncapped psychic annihilation - DIRECT MENTAL, 100% SAFE OVER PETS & WALLS!)
        ab_sunder = find_ready_ability(abilities, ["sunder mind", "sundermind", "sunder"])
        if ab_sunder and ab_sunder.get("command") and s_dir:
            return {"action": f"USE_ABILITY:{ab_sunder['command']}:{s_dir}", "reason": f"[{template['name']} Fallback] Channeling Sunder Mind against {c_name} (dist: {closest_dist})"}

        # B. Opener CC: Stunning Force on approaching mobile enemies (dist 3-8, requires clear LOF)
        ab_stun = find_ready_ability(abilities, ["stunning force", "stunningforce"])
        if ab_stun and ab_stun.get("command") and 3 <= closest_dist <= 8 and not is_stationary and s_dir and c_lof_clear:
            return {"action": f"USE_ABILITY:{ab_stun['command']}:{s_dir}", "reason": f"[{template['name']} Fallback] Blasting approaching {c_name} with Stunning Force CC opener ({s_dir})"}

        # C. Lase (Light Manipulation focused laser beam - requires clear LOF past companions)
        ab_lase = find_ready_ability(abilities, ["lase", "light manipulation"])
        if ab_lase and ab_lase.get("command") and s_dir and c_lof_clear:
            return {"action": f"USE_ABILITY:{ab_lase['command']}:{s_dir}", "reason": f"[{template['name']} Fallback] Firing Lase light beam at {c_name} ({s_dir}, dist: {closest_dist})"}

        # D. Cryokinesis / Pyrokinesis / Ray / Elemental / Gas attacks (requires clear LOF)
        ab_elemental = find_ready_ability(abilities, ["cryokinesis", "pyrokinesis", "flaming ray", "freezing ray", "spit poison", "electrical generation", "corrosive gas", "sleep gas"])
        if ab_elemental and ab_elemental.get("command") and s_dir and c_lof_clear:
            return {"action": f"USE_ABILITY:{ab_elemental['command']}:{s_dir}", "reason": f"[{template['name']} Fallback] Manifesting {ab_elemental.get('name')} at {c_name} ({s_dir})"}

        # E. Stunning Force (Secondary / Stationary / Close Finisher - dist <= 8, requires clear LOF)
        if ab_stun and ab_stun.get("command") and closest_dist <= 8 and s_dir and c_lof_clear:
            return {"action": f"USE_ABILITY:{ab_stun['command']}:{s_dir}", "reason": f"[{template['name']} Fallback] Blasting {c_name} with Stunning Force ({s_dir})"}

        # F. Syphon Vim (Life drain if within 4 tiles)
        ab_syphon = find_ready_ability(abilities, ["syphon vim", "syphonvim"])
        if ab_syphon and ab_syphon.get("command") and closest_dist <= 4 and s_dir:
            return {"action": f"USE_ABILITY:{ab_syphon['command']}:{s_dir}", "reason": f"[{template['name']} Fallback] Draining life force from {c_name} ({s_dir})"}

        # G. Equipped missile weapon fire (requires clear LOF)
        if has_missile and ammo > 0 and not adj_threats and c_lof_clear:
            return {"action": f"FIRE_MISSILE@{c_tx},{c_ty}", "reason": f"[{template['name']} Fallback] Firing ranged weapon at {c_name} while mental cooldowns reset"}

        # H. Friendly-fire evasion: If primary target line of fire is blocked by pet, redirect to unblocked target!
        if not c_lof_clear:
            for alt in enemies[1:]:
                alt_tx = alt.get("tx", px)
                alt_ty = alt.get("ty", py)
                alt_clear, _ = is_line_of_fire_clear((px, py), (alt_tx, alt_ty), companions=companions, blocked_set=blocked_coords)
                if alt_clear:
                    alt_dir = get_step_direction(cur_pos, (alt_tx, alt_ty))
                    if ab_lase and ab_lase.get("command") and alt_dir:
                        return {"action": f"USE_ABILITY:{ab_lase['command']}:{alt_dir}", "reason": f"[{template['name']} Fallback] Friendly-fire protection: redirecting Lase to unblocked {alt.get('name')} ({alt_dir})"}
                    if has_missile and ammo > 0:
                        return {"action": f"FIRE_MISSILE@{alt_tx},{alt_ty}", "reason": f"[{template['name']} Fallback] Friendly-fire protection: redirecting missile to unblocked {alt.get('name')}"}

            # If all targets blocked, reposition sideways to get an open firing line!
            if open_moves:
                return {"action": open_moves[0], "reason": f"[{template['name']} Fallback] Repositioning {open_moves[0][5:]} to clear line of fire past companion"}

        # I. Standoff Kiting: if enemy is closer than preferred distance (dist < 4) and open_moves exist, step back
        if closest_dist < 4 and open_moves:
            kites = [m for m in open_moves if max(abs(px + CARDINAL_OFFSETS[m[5:]][0] - c_tx), abs(py + CARDINAL_OFFSETS[m[5:]][1] - c_ty)) > closest_dist]
            if kites:
                return {"action": kites[0], "reason": f"[{template['name']} Fallback] Preserving safe standoff distance (dist {closest_dist} -> {kites[0][5:]})"}

        # J. Standoff & Recharge: When all ranged powers / laser charges are cooling down and distance is 2-8 tiles:
        # HOLD GROUND and WAIT! Let ambient light recharge Lase charges and mental cooldowns tick down!
        if closest_dist <= 8:
            return {"action": "WAIT", "reason": f"[{template['name']} Fallback] Holding safe standoff distance ({closest_dist} tiles) & recharging laser charges/mental cooldowns to finish {c_name}"}

        # K. If enemy is distant (dist > 8), close the gap to bring into psychic range
        if closest_dist > 8:
            step_move = f"MOVE_{s_dir}"
            if step_move in valid_moves:
                return {"action": step_move, "reason": f"[{template['name']} Fallback] Advancing to psychic engagement range on {c_name} ({s_dir})"}

        # Otherwise, hold ground and recharge mental energy/cooldowns
        return {"action": "WAIT", "reason": f"[{template['name']} Fallback] Recharging mental focus for next psychic strike on {c_name} (dist: {closest_dist})"}

    # 3. Last Resort Melee (Only when completely cornered with 0 open moves, 0 sprint, and 0 defensive abilities)
    if adj_threats:
        d, ename = list(adj_threats.items())[0]
        return {"action": f"MOVE_{d}", "reason": f"[{template['name']} Fallback] Cornered last resort: emergency defense on {ename} ({d})"}

    if valid_moves:
        ranked = sorted(valid_moves, key=lambda m: visit_counts[(cur_pos[0] + CARDINAL_OFFSETS[m[5:]][0], cur_pos[1] + CARDINAL_OFFSETS[m[5:]][1])])
        return {"action": ranked[0], "reason": f"[{template['name']} Fallback] Repositioning"}

    return {"action": "WAIT", "reason": f"[{template['name']} Fallback] Meditating / Passing turn"}


def fallback_gunslinger(game_state, enemies, adj_threats, open_moves, valid_moves, abilities, template, cur_pos, px, py, hp, max_hp, can_sp, has_missile, ammo, max_ammo, inv_ammo):
    """Rapid-Fire Pistol Gunslinger Tactical Fallback (Akimbo Gunslinger)."""
    companions = game_state.get("companions", [])
    enemies = filter_hostile_enemies(enemies, companions)
    if (companions or CHARMED_COMPANION_NAMES) and adj_threats:
        comp_names = {c.get("name", "").lower() for c in companions if c.get("name")} | CHARMED_COMPANION_NAMES
        adj_threats = {
            d: ename for d, ename in adj_threats.items()
            if not any(cn in ename.lower() for cn in comp_names if len(cn) > 2)
        }

    closest_enemy = enemies[0] if enemies else None
    closest_dist = closest_enemy.get("dist", 999) if closest_enemy else 999
    c_name = closest_enemy.get("name", "Enemy") if closest_enemy else ""
    c_tx = closest_enemy.get("tx", px) if closest_enemy else px
    c_ty = closest_enemy.get("ty", py) if closest_enemy else py

    # 1. Encirclement Break (2+ threats)
    if len(adj_threats) >= 2 and open_moves:
        best_retreat = open_moves[0]
        r_dir = best_retreat[5:]
        if can_sp:
            return {"action": f"SPRINT_{r_dir}", "reason": f"[{template['name']} Fallback] Sprinting {r_dir} to escape {len(adj_threats)} melee threats"}
        return {"action": best_retreat, "reason": f"[{template['name']} Fallback] Stepping {r_dir} to break encirclement"}

    # 2. Adjacent Combat: Disarming Shot or Step-and-Shoot
    if adj_threats:
        target_dir = list(adj_threats.keys())[0]
        target_name = adj_threats[target_dir]

        ab_disarm = find_ready_ability(abilities, ["disarm", "disarmingshot"])
        if ab_disarm and ab_disarm.get("command"):
            return {"action": f"USE_ABILITY:{ab_disarm['command']}:{target_dir}", "reason": f"[{template['name']} Fallback] Disarming shot on adjacent {target_name} ({target_dir})"}

        if open_moves and ammo > 0:
            return {"action": open_moves[0], "reason": f"[{template['name']} Fallback] Stepping {open_moves[0][5:]} to point pistols at {target_name}"}

        if has_missile and ammo > 0:
            return {"action": f"FIRE_MISSILE@{px + CARDINAL_OFFSETS[target_dir][0]},{py + CARDINAL_OFFSETS[target_dir][1]}", "reason": f"[{template['name']} Fallback] Point-blank pistol blast at {target_name}"}
        return {"action": f"MOVE_{target_dir}", "reason": f"[{template['name']} Fallback] Striking {target_name} in melee"}

    # 3. Chain Fire / Rapid Pistol Volley (Distance 2 to 8)
    if closest_enemy and 2 <= closest_dist <= 8:
        ab_chain = find_ready_ability(abilities, ["chain fire", "chainfire"])
        if ab_chain and ab_chain.get("command") and ammo >= 3:
            return {"action": f"USE_ABILITY:{ab_chain['command']}", "reason": f"[{template['name']} Fallback] Unleashing Chain Fire pistol volley at {c_name} (dist: {closest_dist})"}

        if has_missile and ammo > 0:
            companions = game_state.get("companions", [])
            is_clear, _ = is_line_of_fire_clear((px, py), (c_tx, c_ty), companions=companions, blocked_set=blocked_coords)
            if is_clear:
                return {"action": f"FIRE_MISSILE@{c_tx},{c_ty}", "reason": f"[{template['name']} Fallback] Firing dual pistols at {c_name} (dist: {closest_dist})"}
            else:
                for alt in enemies[1:]:
                    alt_tx = alt.get("tx", px)
                    alt_ty = alt.get("ty", py)
                    alt_clear, _ = is_line_of_fire_clear((px, py), (alt_tx, alt_ty), companions=companions, blocked_set=blocked_coords)
                    if alt_clear:
                        return {"action": f"FIRE_MISSILE@{alt_tx},{alt_ty}", "reason": f"[{template['name']} Fallback] Redirecting pistols to unblocked {alt.get('name')} to protect companion"}
                if open_moves:
                    return {"action": open_moves[0], "reason": f"[{template['name']} Fallback] Repositioning {open_moves[0][5:]} for clear firing line past companion"}

        if has_missile and ammo <= 0 and inv_ammo > 0 and closest_dist >= 2:
            return {"action": "RELOAD", "reason": f"[{template['name']} Fallback] Fast pistol reload (empty 0/{max_ammo})"}

    # 4. Advance or reposition
    if closest_enemy and closest_dist > 8:
        s_dir = get_step_direction(cur_pos, (c_tx, c_ty))
        step_move = f"MOVE_{s_dir}"
        if step_move in valid_moves:
            return {"action": step_move, "reason": f"[{template['name']} Fallback] Closing to pistol range on {c_name} ({s_dir})"}

    if valid_moves:
        ranked = sorted(valid_moves, key=lambda m: visit_counts[(cur_pos[0] + CARDINAL_OFFSETS[m[5:]][0], cur_pos[1] + CARDINAL_OFFSETS[m[5:]][1])])
        return {"action": ranked[0], "reason": f"[{template['name']} Fallback] Maneuver"}

    return {"action": "WAIT", "reason": f"[{template['name']} Fallback] Readying weapons"}


def fallback_nomad(game_state, enemies, adj_threats, open_moves, valid_moves, abilities, template, cur_pos, px, py, hp, max_hp, can_sp, has_missile, ammo, max_ammo, inv_ammo, is_sprinting):
    """Ranged Sniper & Kite Specialist Fallback (Rifle Nomad)."""
    companions = game_state.get("companions", [])
    enemies = filter_hostile_enemies(enemies, companions)
    if (companions or CHARMED_COMPANION_NAMES) and adj_threats:
        comp_names = {c.get("name", "").lower() for c in companions if c.get("name")} | CHARMED_COMPANION_NAMES
        adj_threats = {
            d: ename for d, ename in adj_threats.items()
            if not any(cn in ename.lower() for cn in comp_names if len(cn) > 2)
        }

    closest_enemy = enemies[0] if enemies else None
    closest_dist = closest_enemy.get("dist", 999) if closest_enemy else 999
    c_name = closest_enemy.get("name", "Enemy") if closest_enemy else ""
    c_tx = closest_enemy.get("tx", px) if closest_enemy else px
    c_ty = closest_enemy.get("ty", py) if closest_enemy else py

    # 1. Encirclement Break: If surrounded by 2+ adjacent hostiles and open retreat tiles exist
    if len(adj_threats) >= 2 and open_moves:
        best_retreat = open_moves[0]
        r_dir = best_retreat[5:]
        if can_sp:
            return {"action": f"SPRINT_{r_dir}", "reason": f"[{template['name']} Fallback] Sprinting {r_dir} to escape {len(adj_threats)} melee threats"}
        return {"action": best_retreat, "reason": f"[{template['name']} Fallback] Stepping {r_dir} to break melee encirclement ({len(adj_threats)} threats)"}

    # 2. Active Sprint Evasion: If sprinting and in melee contact, step into open ground
    if is_sprinting and adj_threats and open_moves:
        return {"action": open_moves[0], "reason": f"[{template['name']} Fallback] Sprint kiting {open_moves[0][5:]}"}

    # 3. Crowd Control: Freezing Ray on incoming pursuers (distance 2-5)
    if closest_enemy and 2 <= closest_dist <= 5:
        ab_freeze = find_ready_ability(abilities, ["freezing ray", "freezingray", "freeze"])
        if ab_freeze and ab_freeze.get("command"):
            s_dir = get_step_direction(cur_pos, (c_tx, c_ty))
            companions = game_state.get("companions", [])
            is_clear, _ = is_line_of_fire_clear((px, py), (c_tx, c_ty), companions=companions, blocked_set=blocked_coords)
            if is_clear:
                return {"action": f"USE_ABILITY:{ab_freeze['command']}:{s_dir}", "reason": f"[{template['name']} Fallback] Freezing {c_name} in solid ice with Freezing Ray ({s_dir})"}

    # 4. RANGED SNIPE: Disengaged at safe distance (dist >= 2) with loaded rifle -> SHOOT! (Requires clear LOF)
    if closest_enemy and closest_dist >= 2 and has_missile and ammo > 0 and not adj_threats:
        companions = game_state.get("companions", [])
        is_clear, _ = is_line_of_fire_clear((px, py), (c_tx, c_ty), companions=companions, blocked_set=blocked_coords)
        if is_clear:
            return {"action": f"FIRE_MISSILE@{c_tx},{c_ty}", "reason": f"[{template['name']} Fallback] Firing rifle at {c_name} (dist: {closest_dist})"}
        else:
            for alt in enemies[1:]:
                alt_tx = alt.get("tx", px)
                alt_ty = alt.get("ty", py)
                alt_clear, _ = is_line_of_fire_clear((px, py), (alt_tx, alt_ty), companions=companions, blocked_set=blocked_coords)
                if alt_clear:
                    return {"action": f"FIRE_MISSILE@{alt_tx},{alt_ty}", "reason": f"[{template['name']} Fallback] Redirecting rifle to unblocked {alt.get('name')} to protect companion"}
            if open_moves:
                return {"action": open_moves[0], "reason": f"[{template['name']} Fallback] Repositioning {open_moves[0][5:]} for clear firing line past companion"}

    # 5. Combat reload: ONLY if no enemies are in melee contact!
    if has_missile and max_ammo > 0 and ammo <= 0 and inv_ammo > 0 and not adj_threats and closest_dist >= 2:
        return {"action": "RELOAD", "reason": f"[{template['name']} Fallback] Combat reload: magazine dry ({ammo}/{max_ammo}, Inv: {inv_ammo})"}

    # 6. Disengage & Kite: When threat is close (dist <= 2) and out of ammo or need distance
    if closest_enemy and closest_dist <= 2 and not adj_threats and ammo <= 0:
        safe_moves = []
        for vm in valid_moves:
            vdir = vm[5:]
            vdx, vdy = CARDINAL_OFFSETS[vdir]
            npos = (px + vdx, py + vdy)
            new_dist = max(abs(npos[0] - c_tx), abs(npos[1] - c_ty))
            if new_dist > closest_dist:
                safe_moves.append(vm)

        if safe_moves:
            if can_sp:
                return {"action": f"SPRINT_{safe_moves[0][5:]}", "reason": f"[{template['name']} Fallback] Sprint kiting {safe_moves[0][5:]} to reload"}
            return {"action": safe_moves[0], "reason": f"[{template['name']} Fallback] Kiting threat {safe_moves[0]} to reload"}

        if has_missile and ammo > 0:
            return {"action": f"FIRE_MISSILE@{c_tx},{c_ty}", "reason": f"[{template['name']} Fallback] Cornered: point-blank blast at ({c_tx},{c_ty})"}

    # 7. Adjacent Melee Engagement (1 threat)
    if adj_threats:
        d, ename = list(adj_threats.items())[0]
        return {"action": f"MOVE_{d}", "reason": f"[{template['name']} Fallback] Striking adjacent threat {ename} ({d})"}

    # 8. Advance to melee if no ammo available
    if closest_enemy and closest_dist <= 10:
        s_dir = get_step_direction(cur_pos, (c_tx, c_ty))
        step_move = f"MOVE_{s_dir}"
        if step_move in valid_moves:
            return {"action": step_move, "reason": f"[{template['name']} Fallback] Closing in on {c_name} ({s_dir})"}

    if valid_moves:
        ranked = sorted(valid_moves, key=lambda m: visit_counts[(cur_pos[0] + CARDINAL_OFFSETS[m[5:]][0], cur_pos[1] + CARDINAL_OFFSETS[m[5:]][1])])
        return {"action": ranked[0], "reason": f"[{template['name']} Fallback] Maneuver"}

    return {"action": "WAIT", "reason": f"[{template['name']} Fallback] Wait"}


def query_decision(game_state, took_damage, enemies, suppress_autolevel=False):
    global last_action, consecutive_kites

    template = build_templates.detect_build(game_state)

    surroundings = game_state.get("surroundings", {})
    has_missile = game_state.get("has_missile_weapon", False)
    ammo = game_state.get("missile_ammo", 0)
    max_ammo = game_state.get("missile_max_ammo", 0)
    inv_ammo = game_state.get("inventory_ammo", 0)
    hp = game_state.get("hp", 0)
    max_hp = game_state.get("max_hp", 1)
    px = game_state.get("x", 0)
    py = game_state.get("y", 0)
    cur_pos = (px, py)
    abilities = game_state.get("abilities", [])
    companions = game_state.get("companions", [])

    enemies = filter_hostile_enemies(enemies, companions)
    adj_threats = get_adjacent_threats(surroundings, companions=companions)
    close_threats = [e for e in enemies if not is_ignorable_stationary_enemy(e) and e.get("dist", 999) <= 20]
    engine_hostiles = (game_state.get("hostiles_adjacent", False) and bool(adj_threats)) or (game_state.get("hostiles_nearby", False) and bool(close_threats))
    is_in_combat = took_damage or bool(adj_threats) or bool(close_threats) or engine_hostiles

    last_failed = None
    if game_state.get("last_move_failed"):
        f_dir = game_state.get("last_failed_dir", "")
        if f_dir:
            last_failed = f"MOVE_{f_dir}"
            fdx, fdy = CARDINAL_OFFSETS.get(f_dir, (0, 0))
            blocked_coords.add((px + fdx, py + fdy))

    valid_moves = get_valid_moves(surroundings, cur_pos, last_failed, is_in_combat=is_in_combat)

    # ==========================================================
    # PHASE A: DETERMINISTIC SAFE MODE (Zero Latency / 0ms tokens)
    # ==========================================================
    if not is_in_combat:
        consecutive_kites = 0

        # 1. Autolevel unspent character points according to class doctrine
        ap = game_state.get("ap", 0)
        sp = game_state.get("sp", 0)
        mp = game_state.get("mp", 0)
        if not suppress_autolevel and (ap > 0 or sp >= 50 or mp > 0) and not took_damage:
            if twitch_manager:
                top_stat = twitch_manager.get_top_stat()
                if ap > 0 and top_stat:
                    stat_name, count = top_stat
                    twitch_manager.reset_stat_votes()
                    return {"action": f"AUTOLEVEL_STAT:{stat_name}", "reason": f"Twitch Chat Vote winner: {stat_name} ({count} votes)"}
                top_skill = twitch_manager.get_top_skill()
                if sp >= 50 and top_skill:
                    skill_class, count = top_skill
                    twitch_manager.reset_skill_votes()
                    return {"action": f"AUTOLEVEL_SKILL:{skill_class}", "reason": f"Twitch Chat Vote winner: {skill_class} ({count} votes)"}

            # Class template allocation priorities
            if ap > 0:
                attrs = game_state.get("attributes", {})
                rec_stat, reason = build_templates.get_stat_allocation_recommendation(template, attrs)
                return {"action": f"AUTOLEVEL_STAT:{rec_stat}", "reason": f"Class Progression ({template['name']}): {reason}"}

            if sp >= 50:
                learned = set(game_state.get("skills", []))
                for cand in template.get("skill_progression", []):
                    if cand not in learned:
                        return {"action": f"AUTOLEVEL_SKILL:{cand}", "reason": f"Class Progression ({template['name']}): Unlocking priority skill {cand}"}

            if mp > 0:
                muts = game_state.get("mutations", [])
                for p_mut in template.get("mutation_priorities", []):
                    m_obj = next((m for m in muts if m.get("class", "").lower() == p_mut.lower() and m.get("can_level", False)), None)
                    if m_obj:
                        return {"action": f"AUTOLEVEL_MUTATION:{m_obj.get('class')}", "reason": f"Class Progression ({template['name']}): Leveling {m_obj.get('name')}"}

            return {"action": "AUTOLEVEL", "reason": f"Safe autoleveling: allocating unspent points (AP:{ap}, SP:{sp}, MP:{mp})"}

        # 2. Rest until healed if safe and damaged below threshold (default 75%)
        hp_ratio = hp / max(1, max_hp)
        if hp_ratio < REST_HP_THRESHOLD and not took_damage:
            pct = int(hp_ratio * 100)
            return {"action": "REST", "reason": f"Safe resting: HP at {pct}% (< {int(REST_HP_THRESHOLD*100)}%)"}

        # 3. Top-off ammo while area is secure (only if we have spare ammo in inventory!)
        if has_missile and max_ammo > 0 and ammo < max_ammo and inv_ammo > 0:
            return {"action": "RELOAD", "reason": f"Safe top-off: reloading rifle ({ammo}/{max_ammo}, Inv: {inv_ammo})"}

        # 4. Autonomous area exploration via Caves of Qud native Autoexplore
        is_stuck_explore = (current_zone_id is not None and current_zone_id in stuck_autoexplore_zones)
        if not game_state.get("zone_fully_explored", False) and not is_stuck_explore:
            return {"action": "AUTOEXPLORE", "reason": "Safe exploration: advancing via native Qud autoexplore pathfinder"}

        # 5. Zone is fully explored -> Search for stairs down, zone transitions, or frontier moves
        center_tile = surroundings.get("CENTER", "").lower()
        if "stair" in center_tile and "down" in center_tile:
            return {"action": "USE_STAIRS_DOWN", "reason": "Zone fully explored: descending stairs down to next stratum"}

        for ent in game_state.get("visible_entities", []):
            ename = ent.get("name", "").lower()
            ebp = ent.get("blueprint", "").lower()
            if ("stair" in ename or "stair" in ebp) and "down" in ename:
                s_dir = ent.get("dir", "")
                if s_dir and f"MOVE_{s_dir}" in valid_moves:
                    return {"action": f"MOVE_{s_dir}", "reason": f"Zone fully explored: navigating towards stairs down ({s_dir})"}

        exit_moves = [m for m in valid_moves if "[zone_exit" in surroundings.get(m[5:], "").lower() or "exit" in surroundings.get(m[5:], "").lower()]
        if exit_moves:
            return {"action": exit_moves[0], "reason": f"Zone fully explored: transitioning to adjacent zone via {exit_moves[0]}"}

        if valid_moves:
            ranked = sorted(valid_moves, key=lambda m: visit_counts[(cur_pos[0] + CARDINAL_OFFSETS[m[5:]][0], cur_pos[1] + CARDINAL_OFFSETS[m[5:]][1])])
            return {"action": ranked[0], "reason": f"Zone fully explored: scouting zone frontier {ranked[0]}"}

        return {"action": "WAIT", "reason": "Zone fully explored: no open moves"}

    # ==========================================================
    # PHASE B: TACTICAL COMBAT (The Conversation Model)
    # ==========================================================
    # Query LM Studio for high-level tactical decisions tailored to class archetype
    llm_decision = query_llm_decision(game_state, enemies, valid_moves, abilities, template=template, took_damage=took_damage)
    if llm_decision:
        return {"action": llm_decision["action"], "reason": llm_decision["thought"]}

    # ==========================================================
    # PHASE C: DETERMINISTIC TACTICAL FALLBACK MATRIX (Class-Specific)
    # ==========================================================
    open_moves = [vm for vm in valid_moves if vm[5:] not in adj_threats]
    effects = game_state.get("effects", [])
    is_sprinting = game_state.get("is_sprinting", False) or any(e in ef.lower() for ef in effects for e in ["running", "sprint"])
    sprint_ab = next((ab for ab in abilities if "sprint" in ab.get("name", "").lower() or "sprint" in ab.get("command", "").lower()), None)
    can_sp = (not is_sprinting) and (sprint_ab is not None) and sprint_ab.get("usable", True) and sprint_ab.get("cooldown", 0) <= 0

    cid = template.get("id", "praetorian_generalist")
    if cid in ("auspicious_beginnings", "limb_off", "axe_berserker", "classic_punchkin"):
        return fallback_melee(
            game_state, enemies, adj_threats, open_moves, valid_moves, abilities,
            template, cur_pos, px, py, hp, max_hp, can_sp, has_missile, ammo, max_ammo, inv_ammo
        )
    elif cid in ("esper_ited_away", "esper_mindflayer", "uncle_iroh", "gas_giant"):
        return fallback_esper(
            game_state, enemies, adj_threats, open_moves, valid_moves, abilities,
            template, cur_pos, px, py, hp, max_hp, can_sp, has_missile, ammo, max_ammo, inv_ammo
        )
    elif cid in ("gunkin", "bullet_specter", "akimbo_gunslinger"):
        return fallback_gunslinger(
            game_state, enemies, adj_threats, open_moves, valid_moves, abilities,
            template, cur_pos, px, py, hp, max_hp, can_sp, has_missile, ammo, max_ammo, inv_ammo
        )
    else:
        return fallback_nomad(
            game_state, enemies, adj_threats, open_moves, valid_moves, abilities,
            template, cur_pos, px, py, hp, max_hp, can_sp, has_missile, ammo, max_ammo, inv_ammo, is_sprinting
        )


def main():
    global current_zone_id, zone_step_count, last_action, last_hp, consecutive_kites
    global action_repeat_count, last_executed_action, last_executed_pos, twitch_manager

    twitch_manager = twitch_bot.start_twitch_in_background()

    autolevel_failed_attempts = 0
    last_autolevel_points = None

    print("==================================================")
    print(" Caves of Qud Autonomous Agent (Hierarchical)")
    print(" Connecting to LM Studio on port 1234...")
    detect_lm_studio_model()
    print(" Status: MANUAL MODE")
    print(" Press ENTER in this console to TOGGLE AI control")
    print("==================================================\n")

    t = threading.Thread(target=input_listener, daemon=True)
    t.start()

    while True:
        if os.path.exists(DEATH_FILE):
            time.sleep(0.05)
            try:
                with open(DEATH_FILE, "r", encoding="utf-8-sig") as f:
                    death_data = json.load(f, strict=False)
                try:
                    os.remove(DEATH_FILE)
                except OSError:
                    pass
                if death_data:
                    chronicler.process_death_event(death_data, list(recent_actions), active_model_id)
            except Exception as ex:
                print(f"[Death Processing Error] {ex}")

        if os.path.exists(STATE_FILE):
            time.sleep(0.015)
            game_state = None
            try:
                with open(STATE_FILE, "r", encoding="utf-8-sig") as f:
                    game_state = json.load(f, strict=False)
                try:
                    with open(os.path.join(EXCHANGE_DIR, "last_state.json"), "w", encoding="utf-8") as lf:
                        json.dump(game_state, lf, indent=2)
                except Exception:
                    pass
                try:
                    os.remove(STATE_FILE)
                except OSError:
                    pass
            except Exception:
                continue

            if not game_state:
                continue

            try:
                zone_id = game_state.get("zone_id")
                if current_zone_id is not None and zone_id != current_zone_id:
                    visit_counts.clear()
                    blocked_coords.clear()
                    recent_positions.clear()
                    zone_step_count = 0
                    consecutive_kites = 0

                current_zone_id = zone_id
                zone_step_count += 1

                hp = game_state.get("hp", 0)
                max_hp = game_state.get("max_hp", 1)
                took_damage = (last_hp is not None and hp < last_hp)
                last_hp = hp

                px = game_state.get("x", 0)
                py = game_state.get("y", 0)
                cur_pos = (px, py)
                visit_counts[cur_pos] += 1
                recent_positions.append(cur_pos)
                pos_frequency = recent_positions.count(cur_pos)

                companions = game_state.get("companions", [])
                current_comp_coords = set()
                for c in companions:
                    cx, cy = c.get("tx"), c.get("ty")
                    if cx is not None and cy is not None:
                        current_comp_coords.add((cx, cy))
                    register_companion(c.get("name"), (cx, cy))

                raw_entities = game_state.get("visible_entities", [])
                for e in raw_entities:
                    if e.get("is_companion", False):
                        ex, ey = e.get("tx"), e.get("ty")
                        if ex is not None and ey is not None:
                            current_comp_coords.add((ex, ey))
                            register_companion(e.get("name"), (ex, ey))
                    elif is_companion_name(e.get("name"), CHARMED_COMPANION_NAMES):
                        ex, ey = e.get("tx"), e.get("ty")
                        if ex is not None and ey is not None:
                            current_comp_coords.add((ex, ey))

                CHARMED_COMPANION_COORDS.clear()
                CHARMED_COMPANION_COORDS.update(current_comp_coords)

                if companions:
                    c_display = [f"{c.get('name')} (HP {c.get('hp')}/{c.get('max_hp')})" for c in companions]
                    print(f"[ALLIED PET]: {', '.join(c_display)}")

                enemies = filter_hostile_enemies(raw_entities, companions)

                # Prioritize active threats ahead of distant stationary trivial entities, then difficulty, then distance
                diff_weights = {"Impossible": 0, "Very Tough": 1, "Tough": 2, "Average": 3, "Easy": 4, "Trivial": 5, "": 4}
                enemies.sort(key=lambda x: (
                    1 if is_ignorable_stationary_enemy(x) else 0,
                    diff_weights.get(x.get("difficulty", ""), 4),
                    x.get("dist", 999)
                ))

                has_mw = game_state.get("has_missile_weapon", False)
                cur_ammo = game_state.get("missile_ammo", 0)
                max_ammo = game_state.get("missile_max_ammo", 0)
                inv_ammo = game_state.get("inventory_ammo", 0)
                ammo_str = f"Ammo: {cur_ammo}/{max_ammo} (Inv: {inv_ammo})" if has_mw else "Rifle: Unequipped"

                surroundings = game_state.get("surroundings", {})
                grid_display = render_5x5_grid(surroundings)
                adj_threats = get_adjacent_threats(surroundings, companions=companions)
                close_threats = [e for e in enemies if not is_ignorable_stationary_enemy(e) and e.get("dist", 999) <= 20]
                engine_hostiles = (game_state.get("hostiles_adjacent", False) and bool(adj_threats)) or (game_state.get("hostiles_nearby", False) and bool(close_threats))
                is_in_combat = took_damage or bool(adj_threats) or bool(close_threats) or engine_hostiles
                mode_str = "[COMBAT]" if is_in_combat else "[EXPLORE]"
                active_template = build_templates.detect_build(game_state)
                class_label = active_template.get("name", "Nomad Wanderer")

                if adj_threats:
                    adj_str = ", ".join([f"{ename} ({d})" for d, ename in adj_threats.items()])
                    print(f"[MELEE ENGAGEMENT ({class_label})]: {adj_str}")
                elif enemies:
                    enemy_summary = ", ".join([f"{e['name']} [{e.get('difficulty','?').upper()}] ({e['dist']}t {e['dir']})" for e in enemies[:3]])
                    print(f"(!) {mode_str} [{class_label}] THREATS: [{enemy_summary}] | {ammo_str}")

                print(f"SURROUNDINGS (5x5):\n{grid_display}\n")

                cur_points = (game_state.get("ap", 0), game_state.get("sp", 0), game_state.get("mp", 0))
                suppress_auto = (autolevel_failed_attempts >= 2 and cur_points == last_autolevel_points)

                decision = query_decision(game_state, took_damage, enemies, suppress_autolevel=suppress_auto)
                action = decision.get("action", "WAIT")
                reason = decision.get("reason", "None given")

                if action.startswith("AUTOLEVEL"):
                    if cur_points == last_autolevel_points:
                        autolevel_failed_attempts += 1
                    else:
                        last_autolevel_points = cur_points
                        autolevel_failed_attempts = 1

                    if autolevel_failed_attempts >= 2:
                        print(f"[AUTOLEVEL CIRCUIT BREAKER] Unspent points {cur_points} failed to allocate after {autolevel_failed_attempts} attempts. Suppressing autolevel to prevent loop freeze.")
                        decision = query_decision(game_state, took_damage, enemies, suppress_autolevel=True)
                        action = decision.get("action", "WAIT")
                        reason = decision.get("reason", "None given")
                else:
                    if cur_points != last_autolevel_points:
                        autolevel_failed_attempts = 0
                        last_autolevel_points = cur_points

                # If Proselytize or Beguile action chosen, immediately register target companion!
                if "proselytize" in action.lower() or "beguile" in action.lower():
                    parts = action.split(":")
                    if len(parts) >= 3 and parts[2] in CARDINAL_OFFSETS:
                        p_dir = parts[2]
                        dx, dy = CARDINAL_OFFSETS[p_dir]
                        tgt_coord = (px + dx, py + dy)
                        tgt_name = None
                        for e in raw_entities:
                            if (e.get("tx"), e.get("ty")) == tgt_coord:
                                if is_proselytizable(e):
                                    tgt_name = e.get("name")
                                break
                        if tgt_name:
                            register_companion(tgt_name, tgt_coord)
                            print(f"[PET RECRUITED]: Instantly registered {tgt_name} at {tgt_coord} as allied companion!")

                # Enforce: Never execute ACTIVATE_SPRINT twice in a row
                if action == "ACTIVATE_SPRINT" and last_executed_action == "ACTIVATE_SPRINT":
                    valid_m = get_valid_moves(surroundings, cur_pos, None, is_in_combat=is_in_combat)
                    if valid_m:
                        action = valid_m[0]
                        reason = f"[Sprint Cooldown] Sprint fired last turn. Repositioning {action}."
                    elif has_mw and cur_ammo > 0 and enemies:
                        closest = enemies[0]
                        action = f"FIRE_MISSILE@{closest.get('tx')},{closest.get('ty')}"
                        reason = f"[Sprint Cooldown] Sprint fired last turn. Firing missile."
                    else:
                        action = "PASS"
                        reason = "[Sprint Cooldown] Passing turn."

                # Loop Breaker: Detect and break repeated non-progressing actions or coordinate oscillation
                # (Ignore if player is actively bump-attacking an adjacent enemy in melee!)
                is_attacking = action.startswith("MOVE_") and (action[5:] in adj_threats)
                is_stationary_repeat = (action == last_executed_action and cur_pos == last_executed_pos and not is_attacking)
                is_oscillating = (pos_frequency >= 3 and not is_attacking)

                if is_stationary_repeat:
                    action_repeat_count += 1
                    if action_repeat_count >= 2:
                        open_m = [vm for vm in get_valid_moves(surroundings, cur_pos, None, is_in_combat=is_in_combat) if vm[5:] not in adj_threats]
                        if len(adj_threats) >= 2 and open_m:
                            action = open_m[0]
                            reason = f"[Loop Breaker] Surrounded by {len(adj_threats)} threats! Breaking encirclement via {open_m[0]}."
                        elif adj_threats:
                            atk_dir = list(adj_threats.keys())[0]
                            action = f"MOVE_{atk_dir}"
                            reason = f"[Loop Breaker] Counter-attacking adjacent threat {adj_threats[atk_dir]} ({atk_dir}) in melee."
                        elif has_mw and cur_ammo > 0 and enemies:
                            closest = enemies[0]
                            action = f"FIRE_MISSILE@{closest.get('tx')},{closest.get('ty')}"
                            reason = f"[Loop Breaker] Action repeated {action_repeat_count}x at {cur_pos}. Forcing missile shot."
                        else:
                            valid_m = get_valid_moves(surroundings, cur_pos, None, is_in_combat=is_in_combat)
                            if valid_m:
                                action = valid_m[0]
                                reason = f"[Loop Breaker] Action repeated {action_repeat_count}x at {cur_pos}. Forcing reposition {action}."
                            else:
                                action = "PASS"
                                reason = f"[Loop Breaker] Action repeated {action_repeat_count}x at {cur_pos}. Passing turn."
                        action_repeat_count = 0
                elif is_oscillating:
                    if action == "AUTOEXPLORE":
                        if current_zone_id:
                            stuck_autoexplore_zones.add(current_zone_id)
                        print(f"[Loop Breaker] Autoexplore oscillation detected at {cur_pos} ({pos_frequency}x in last 10). Marking zone autoexplore exhausted; forcing frontier breakout.")

                    open_escapes = [m for m in get_valid_moves(surroundings, cur_pos, None, is_in_combat=is_in_combat)
                                    if (cur_pos[0] + CARDINAL_OFFSETS[m[5:]][0], cur_pos[1] + CARDINAL_OFFSETS[m[5:]][1]) not in recent_positions]
                    if open_escapes:
                        open_escapes.sort(key=lambda m: visit_counts[(cur_pos[0] + CARDINAL_OFFSETS[m[5:]][0], cur_pos[1] + CARDINAL_OFFSETS[m[5:]][1])])
                        action = open_escapes[0]
                        reason = f"[Loop Breaker] Oscillation detected at {cur_pos} ({pos_frequency}x in 10). Escaping cycle towards unvisited frontier {action}."
                    else:
                        valid_m = get_valid_moves(surroundings, cur_pos, None, is_in_combat=is_in_combat)
                        if valid_m:
                            valid_m.sort(key=lambda m: visit_counts[(cur_pos[0] + CARDINAL_OFFSETS[m[5:]][0], cur_pos[1] + CARDINAL_OFFSETS[m[5:]][1])])
                            action = valid_m[0]
                            reason = f"[Loop Breaker] Oscillation detected at {cur_pos} ({pos_frequency}x in 10). Forcing least-visited move {action}."
                        else:
                            action = "PASS"
                            reason = f"[Loop Breaker] Oscillation trapped at {cur_pos}. Passing turn."
                    recent_positions.clear()
                    action_repeat_count = 0
                else:
                    action_repeat_count = 0

                last_executed_action = action
                last_executed_pos = cur_pos
                last_action = action
                if action.startswith("MOVE_"):
                    move_history.append(action)
                recent_actions.append({"action": action, "reason": reason, "pos": cur_pos, "hp": hp})

                dmg_flag = " [!HIT!]" if took_damage else ""
                lvl = game_state.get("level", 1)
                g_ap = game_state.get("ap", 0)
                g_sp = game_state.get("sp", 0)
                g_mp = game_state.get("mp", 0)
                prog_str = f" | Lvl {lvl} [AP:{g_ap} SP:{g_sp} MP:{g_mp}]" if (g_ap > 0 or g_sp > 0 or g_mp > 0) else f" | Lvl {lvl}"
                print(f"[{zone_step_count}] {mode_str} [{active_template.get('id', 'nomad')}] Pos: ({px}, {py}){dmg_flag} | HP: {hp}/{max_hp}{prog_str} | Action: {action} -> {reason}\n")

                with open(ACTION_FILE, "w", encoding="utf-8") as f:
                    json.dump({"action": action, "reason": reason}, f)

                # Configurable pacing delays to make actions easy to follow on screen
                if not is_in_combat:
                    time.sleep(EXPLORE_STEP_DELAY)
                else:
                    time.sleep(COMBAT_STEP_DELAY)

            except Exception as e:
                print(f"[Loop Error] {e}")

        time.sleep(0.02)


if __name__ == "__main__":
    main()