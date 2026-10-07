import os
import time
import json
import re
import random
import threading
import requests
from collections import deque, defaultdict
import chronicler
import twitch_bot
import build_templates
import mutation_policy
import ability_registry
import danger_ledger

# Paths
# QUDAI_EXCHANGE_DIR overrides the folder (tests point it at a temp dir so they can never touch the real game files).
EXCHANGE_DIR = os.environ.get("QUDAI_EXCHANGE_DIR") or r"C:\Users\rsebr\AppData\LocalLow\Freehold Games\CavesOfQud\QudAI"
STATE_FILE = os.path.join(EXCHANGE_DIR, "state.json")
ACTION_FILE = os.path.join(EXCHANGE_DIR, "action.json")
FLAG_FILE = os.path.join(EXCHANGE_DIR, "active.flag")
DEATH_FILE = os.path.join(EXCHANGE_DIR, "death.json")

# LM Studio Config
# QUDAI_LM_URL points the brain at another endpoint (tests use a dead port so they never call the live LLM).
LM_STUDIO_URL = os.environ.get("QUDAI_LM_URL") or "http://localhost:1234/v1/chat/completions"
LM_STUDIO_MODELS_URL = "http://localhost:1234/v1/models"
LM_STUDIO_MODELS_V0_URL = LM_STUDIO_MODELS_URL.replace("/v1/models", "/api/v0/models")   # LM Studio's own listing: includes each model's load state
# Model lab (HANDOFF issue 65): QUDAI_LM_MODEL forces a model id (LM Studio loads it on demand if just-in-time loading is on);
# QUDAI_LLM_TIMEOUT is the seconds the combat call may take (a slower, stronger model needs more than the default).
LM_MODEL_OVERRIDE = os.environ.get("QUDAI_LM_MODEL") or None
LM_STUDIO_TIMEOUT = float(os.environ.get("QUDAI_LLM_TIMEOUT") or 6.0)

# Pacing and Thresholds
EXPLORE_STEP_DELAY = 0.25  # Seconds per exploration turn (250ms makes movement comfortable to watch)
COMBAT_STEP_DELAY = 0.20   # Seconds per combat action
REST_HP_THRESHOLD = 0.75   # Only rest when HP drops below 75% of max HP

if not os.path.exists(EXCHANGE_DIR):
    os.makedirs(EXCHANGE_DIR)



def remove_stale_flag():
    """Starts every `python brain.py` in MANUAL mode by removing a leftover active.flag.

    This must run only when the brain is LAUNCHED (in main()), never at import time: it used to run on `import brain`,
    so running the test suite (or any tool that imports brain) deleted the flag of a live run, the game stopped
    exporting state, and the brain still believed it was engaged (HANDOFF issue 49)."""
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
recent_positions = deque(maxlen=24)
stuck_autoexplore_zones = set()
blocked_coords = set()
UNREACHABLE_SECTORS = set()  # set of (zone_id, (tx, ty)) for unreachable frontiers/sectors
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
    "syphonvim", "syphon vim", "forcewall", "force wall", "proselytize", "beguile",
    "flaming ray", "freezing ray", "flameray", "flame ray", "commandflamingray",
    "commandfreezingray", "commandlase", "commandstunningforce"
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
    "turret", "robot", "chest", "door", "wall", "corpse", "slime", "ooze",
    "fish", "glowfish", "piranha", "eel"
}


CHARMED_COMPANION_COORDS = set()

# Food foraging (HANDOFF issue 34: "make him earn his dinner"). No free meals; he walks to corpses/plants and butchers/harvests.
FOOD_BLACKLIST = {}            # (zone_id, tx, ty) -> FOOD_TURN value when the entry expires
FOOD_PURSUIT = {"key": None, "turns": 0}
FOOD_TURN = 0
FOOD_PURSUIT_MAX_TURNS = 40    # give up on one target after this many pursuit turns
FOOD_BLACKLIST_TURNS = 300
FOOD_RESTOCK_THRESHOLD = 3     # forage when hungry or carrying fewer than this many food items
BUTCHER_STREAK = 0             # consecutive BUTCHER actions; a silent failure must not repeat forever
BUTCHER_TURN = 0               # Phase A sustenance calls (a clock for the cool-down below)
BUTCHER_SUPPRESS_UNTIL = 0     # after 3 BUTCHERs in a row, stop trying for BUTCHER_COOLDOWN_TURNS
BUTCHER_COOLDOWN_TURNS = 30

KNOWN_STAIRS_DOWN = {}   # zone_id -> {"tx": tx, "ty": ty, "z": z, "name": name, "req_level": int}
KNOWN_STAIRS_UP = {}     # zone_id -> {"tx": tx, "ty": ty, "z": z, "name": name}
RETREAT_TARGET_LEVEL = None  # Level to attain before re-delving after an emergency retreat


def min_level_for_depth(next_z):
    """
    Calculates minimum recommended level to delve into a depth stratum.
    z <= 10: Surface (requires Level 1)
    z == 11: Stratum 1 (requires Level 3)
    z >= 12: Stratum 2+ (requires Level 3 + (z - 11) * 2)
    """
    if next_z <= 10:
        return 1
    if next_z == 11:
        return 3
    return 3 + (next_z - 11) * 2


def is_swim_move(move_name, surroundings):
    """Returns True if the specified move steps into a swimming-depth liquid tile."""
    if not move_name or not move_name.startswith("MOVE_") or not surroundings:
        return False
    d = move_name[5:]
    t = surroundings.get(d, "").lower()
    return "[swim" in t or "deep water" in t or "deep pool" in t or "deep liquid" in t


def get_best_move_towards(cur_pos, target_pos, valid_moves, surroundings=None):
    """
    Selects the valid move that gets closest to target_pos (tx, ty).
    Uses Chebyshev distance primary, Euclidean distance secondary, breaking ties with least-visited coordinates
    and preferring dry land over swimming liquid when distances and visits are equal.
    """
    if not valid_moves:
        return None
    px, py = cur_pos
    tx, ty = target_pos

    def score_move(m):
        dx, dy = CARDINAL_OFFSETS[m[5:]]
        nx, ny = px + dx, py + dy
        cheb_dist = max(abs(nx - tx), abs(ny - ty))
        euc_dist_sq = (nx - tx) ** 2 + (ny - ty) ** 2
        visits = visit_counts.get((nx, ny), 0)
        swim_penalty = 1 if is_swim_move(m, surroundings) else 0
        return (cheb_dist, euc_dist_sq, visits, swim_penalty)

    sorted_moves = sorted(valid_moves, key=score_move)
    return sorted_moves[0]


RECENT_ZONES = deque(maxlen=10)
LAST_ZONE_ENTRY = None  # {"from_zone": str, "to_zone": str, "entry_pos": (x,y), "reverse_dir": str}
ZONE_HOPPING_DETECTED = False
ZONE_CYCLE_LENGTH = 0  # Length of detected cycle (2, 3, 4...)
CURRENT_TRACKED_ZONE = None
ZONE_STEP_COUNT = 0
EXPLORED_ZONE_SET = set()  # Zones the ENGINE reported fully explored (C# `zone_fully_explored`). Never "stuck", never a guess (AGENTS R2).
ENGINE_EXPLORED_LAST = {}  # zone_id -> last `zone_fully_explored` the engine reported while we were in that zone


def engine_confirms_explored(game_state):
    """True only when the ENGINE says the zone is done and no large unexplored region is still reachable by other means.

    The engine's flag means "native autoexplore has nothing left". On the surface, more than 35 unrevealed cells with
    autoexplore still working usually means regions across water (handled by macro-sector navigation), so that is not
    "explored". Never derived from Python-side guesses such as stuck/oscillation/navigation failures (AGENTS R2)."""
    unexp = game_state.get("unexplored_cells")
    if unexp == 0:
        return True
    if (game_state.get("frontier_checked") and not game_state.get("frontier_targets")
            and game_state.get("reachable_edges")):
        return True   # the engine pathfinder finds nothing left to explore (and exits are reachable, so he is not merely sealed in)
    if not game_state.get("zone_fully_explored", False):
        return False
    if game_state.get("z", 10) > 10:
        return True
    return not (unexp is not None and unexp > 35 and not game_state.get("autoexplore_stuck", False))


def update_zone_records(game_state):
    """
    Tracks zone transition history and detects rapid border ping-pong oscillations.
    Determines entry border and reverse transition direction to prevent immediate bounce-back.
    Detects 2-cycle (A->B->A), 3-cycle (A->B->C->A), and 4-cycle oscillations.
    """
    global CURRENT_TRACKED_ZONE, current_zone_id, ZONE_STEP_COUNT, ZONE_HOPPING_DETECTED, LAST_ZONE_ENTRY, ZONE_CYCLE_LENGTH
    global CURRENT_ZONE_CHOSEN_EXIT, CURRENT_ZONE_CHOSEN_EXIT_ZONE
    zone_id = game_state.get("zone_id", "")
    px = game_state.get("x", 0)
    py = game_state.get("y", 0)
    cur_pos = (px, py)

    if not zone_id:
        return

    if CURRENT_TRACKED_ZONE is not None and zone_id != CURRENT_TRACKED_ZONE:
        # Remember the zone we are LEAVING as explored only if the engine said so while we were in it
        # (game_state now describes the NEW zone, so its flag says nothing about the old one).
        leaving_zone = CURRENT_TRACKED_ZONE
        if ENGINE_EXPLORED_LAST.get(leaving_zone, False):
            EXPLORED_ZONE_SET.add(leaving_zone)
        # A fresh visit gets a fresh autoexplore attempt: stale "stuck" marks must not carry over.
        stuck_autoexplore_zones.discard(zone_id)
        CURRENT_ZONE_CHOSEN_EXIT = None
        CURRENT_ZONE_CHOSEN_EXIT_ZONE = None

        RECENT_ZONES.append(zone_id)
        # Determine entry border and reverse direction
        rev_dir = None
        if px <= 1:
            rev_dir = "W"
        elif px >= 78:
            rev_dir = "E"
        elif py <= 1:
            rev_dir = "N"
        elif py >= 23:
            rev_dir = "S"

        LAST_ZONE_ENTRY = {
            "from_zone": CURRENT_TRACKED_ZONE,
            "to_zone": zone_id,
            "entry_pos": cur_pos,
            "reverse_dir": rev_dir
        }

        # Check for N-cycle oscillation (2, 3, 4-zone cycles)
        # A 2-cycle is A->B->A: zones[-1]==zones[-3]
        # A 3-cycle is A->B->C->A: zones[-1]==zones[-4]
        # A 4-cycle is A->B->C->D->A: zones[-1]==zones[-5]
        detected_cycle = 0
        zones_list = list(RECENT_ZONES)
        for cycle_len in [2, 3, 4]:
            check_idx = -(cycle_len + 1)
            if len(zones_list) >= cycle_len + 1 and zones_list[-1] == zones_list[check_idx]:
                # Verify the full cycle pattern repeats
                pattern = zones_list[-(cycle_len):]
                prior_pattern = zones_list[-(cycle_len * 2):-cycle_len] if len(zones_list) >= cycle_len * 2 else None
                if prior_pattern is None or pattern == prior_pattern:
                    detected_cycle = cycle_len
                    break

        if detected_cycle > 0:
            ZONE_HOPPING_DETECTED = True
            ZONE_CYCLE_LENGTH = detected_cycle
            cycle_zones = list(RECENT_ZONES)[-detected_cycle:]
            print(f"[ZONE HOPPING BREAKER] {detected_cycle}-zone cycle detected: {' -> '.join(cycle_zones)}! Enforcing inward zone navigation.")
        else:
            ZONE_HOPPING_DETECTED = False
            ZONE_CYCLE_LENGTH = 0

        visit_counts.clear()
        blocked_coords.clear()
        recent_positions.clear()
        ZONE_STEP_COUNT = 0
        CURRENT_ZONE_CHOSEN_EXIT = None
        CURRENT_ZONE_CHOSEN_EXIT_ZONE = None
    elif CURRENT_TRACKED_ZONE is None and zone_id:
        RECENT_ZONES.append(zone_id)
        ZONE_STEP_COUNT = 0

    CURRENT_TRACKED_ZONE = zone_id
    current_zone_id = zone_id
    ZONE_STEP_COUNT += 1


FRONTIER_COMMIT = {"zone": None, "target": None}
# Failure feedback for frontier targets (HANDOFF issue 46): the engine pathfinder can list a target as reachable while the
# actual step keeps failing (a stuck or locked door, an obstacle it does not model). Never stay committed to such a target.
FRONTIER_FAILS = {}             # (zone_id, x, y) -> failed approach count
FRONTIER_PURSUIT = {"key": None, "turns": 0}
FRONTIER_BAD = {}               # zone_id -> [(x, y)] centres of written-off targets (their neighbours are skipped too)
FRONTIER_FAIL_LIMIT = 3         # failed NAVIGATE_TO_CELL steps toward one target
FRONTIER_PURSUIT_MAX = 60       # turns on one target without arriving
FRONTIER_FAIL_RADIUS = 2        # neighbours within this Chebyshev distance share the blockage


def _frontier_write_off(zone_id, xy, why):
    UNREACHABLE_SECTORS.add((zone_id, xy))
    FRONTIER_BAD.setdefault(zone_id, []).append(xy)
    FRONTIER_COMMIT.update({"zone": None, "target": None})
    FRONTIER_PURSUIT.update({"key": None, "turns": 0})
    print(f"[FRONTIER] Writing off target {xy} in {zone_id}: {why}.")


def is_frontier_walk(action, reason):
    """True for a committed engine-reachable frontier walk (exempt from the oscillation breaker)."""
    return str(action).startswith("NAVIGATE_TO_CELL:") and str(reason).startswith("Frontier:")


def pick_frontier_target(game_state, cur_pos, zone_id, last_act=None):
    """Chooses an engine-reachable frontier target from C#'s `frontier_targets` (explored walkable cells that touch
    unexplored cells and that AutoAct.TryFindPathStep can route to, never ones the player already stood on).

    Commits to one target until it disappears from the list, is reached, or is blacklisted, so he stops flip-flopping.
    Returns ((x, y), reason) or (None, None). Only meaningful when `frontier_checked` is true."""
    # Learn from the last step: a failed approach counts against the committed target.
    if FRONTIER_COMMIT["zone"] == zone_id and FRONTIER_COMMIT["target"] is not None and last_act:
        ck = FRONTIER_COMMIT["target"]
        if last_act == f"NAVIGATE_TO_CELL:{ck[0]},{ck[1]}" and game_state.get("last_move_failed"):
            fk = (zone_id, ck[0], ck[1])
            FRONTIER_FAILS[fk] = FRONTIER_FAILS.get(fk, 0) + 1
            if FRONTIER_FAILS[fk] >= FRONTIER_FAIL_LIMIT:
                _frontier_write_off(zone_id, ck, f"{FRONTIER_FAIL_LIMIT} failed approaches although the engine lists it as reachable")
    bad_centres = FRONTIER_BAD.get(zone_id, [])
    targets = []
    for tg in game_state.get("frontier_targets", []) or []:
        x, y = tg.get("x"), tg.get("y")
        if x is None or y is None or (x, y) == tuple(cur_pos) or (zone_id, (x, y)) in UNREACHABLE_SECTORS:
            continue
        if any(max(abs(x - bx), abs(y - by)) <= FRONTIER_FAIL_RADIUS for bx, by in bad_centres):
            continue
        targets.append(tg)
    if not targets:
        FRONTIER_COMMIT.update({"zone": None, "target": None})
        return None, None
    chosen = None
    if FRONTIER_COMMIT["zone"] == zone_id and FRONTIER_COMMIT["target"] is not None:
        chosen = next((tg for tg in targets if (tg["x"], tg["y"]) == FRONTIER_COMMIT["target"]), None)
    if chosen is None:
        chosen = min(targets, key=lambda tg: (tg.get("dist", 999), tg.get("q", "")))
        FRONTIER_COMMIT.update({"zone": zone_id, "target": (chosen["x"], chosen["y"])})
    ckey = (zone_id, chosen["x"], chosen["y"])
    if FRONTIER_PURSUIT["key"] == ckey:
        FRONTIER_PURSUIT["turns"] += 1
    else:
        FRONTIER_PURSUIT.update({"key": ckey, "turns": 1})
    if FRONTIER_PURSUIT["turns"] > FRONTIER_PURSUIT_MAX:
        _frontier_write_off(zone_id, (chosen["x"], chosen["y"]), f"{FRONTIER_PURSUIT_MAX} turns without arriving")
        return pick_frontier_target(game_state, cur_pos, zone_id, None)
    return (chosen["x"], chosen["y"]), (
        f"Frontier: engine-reachable unexplored area in the {chosen.get('q', '?')} quadrant at ({chosen['x']}, {chosen['y']}), "
        f"{chosen.get('dist', '?')} tiles away"
    )


# Water/sector traversal progress (HANDOFF issue 53): the greedy step toward a far "unexplored sector" can sit in a local minimum
# (a bank or wall between the player and the target) and flip N/S forever. A sector target is a committed intent: if the distance
# to it sets no new minimum for SECTOR_STALL_LIMIT turns, it is written off like any other unreachable target.
SECTOR_STALL_LIMIT = 14
SECTOR_PROGRESS = {"key": None, "best": None, "stall": 0}
STAIRS_GIVEUP = set()       # (zone_id, stairs xy) the greedy fallback could not approach: delving to them is skipped
SECTOR_GIVEUP = set()       # zone ids where even the nearest-unexplored-cell chase stalled: stop the water traversal there


def sector_target_ok(zone_id, target, cur_pos, kind="centroid"):
    """Records this turn's distance to the committed sector target. False (and blacklisted) once progress has stalled."""
    key = (zone_id, tuple(target)) if kind in ("centroid", "stairs") else (zone_id, kind)   # the nearest cell moves every step
    dist = max(abs(target[0] - cur_pos[0]), abs(target[1] - cur_pos[1]))
    if SECTOR_PROGRESS["key"] != key:
        SECTOR_PROGRESS.update({"key": key, "best": dist, "stall": 0})
        return True
    if dist < SECTOR_PROGRESS["best"]:
        SECTOR_PROGRESS.update({"best": dist, "stall": 0})
        return True
    SECTOR_PROGRESS["stall"] += 1
    if SECTOR_PROGRESS["stall"] >= SECTOR_STALL_LIMIT:
        UNREACHABLE_SECTORS.add((zone_id, tuple(target)))
        if kind == "stairs":
            STAIRS_GIVEUP.add((zone_id, tuple(target)))
        elif kind != "centroid":
            SECTOR_GIVEUP.add(zone_id)
        SECTOR_PROGRESS.update({"key": None, "best": None, "stall": 0})
        print(f"[SECTOR] No progress toward {tuple(target)} in {SECTOR_STALL_LIMIT} turns (closest {dist}). Writing it off.")
        return False
    return True


# Lase and food (HANDOFF issue 34 part C, design decision 2026-10-04: "make him earn his dinner"). Fire and Light damage turn a corpse into
# a burnt, non-butcherable one [verified in code, ENGINE_INTERNALS 12.1b]. When he can butcher and needs food, and the fight is safe, the
# corpse-burning abilities are taken off the table for this decision so melee and the clean abilities (Stunning Force, Sunder Mind) are used.
# C# exports `corpse_chance` per creature (the engine's own number); a creature with 0 or no number is never protected.
CORPSE_BURNER_FAMILY = "corpse_burners"
LASE_POLICY_STATE = {"withheld": False}


def withhold_corpse_burners(game_state, hostiles, hp_ratio):
    """(True, reason) when Lase-like abilities should be withheld this turn."""
    if not game_state.get("can_butcher"):
        return False, ""
    needs_food = game_state.get("is_hungry") or game_state.get("is_famished") or game_state.get("food_count", 0) < FOOD_RESTOCK_THRESHOLD
    if not needs_food:
        return False, ""
    if hp_ratio < 0.5 or len(hostiles) >= 3:
        return False, ""
    if any(e.get("difficulty") in ("Tough", "Very Tough", "Impossible") for e in hostiles):
        return False, ""
    nearest = min(hostiles, key=lambda e: e.get("dist", 999), default=None)
    if not nearest or not (nearest.get("corpse_chance") or 0) > 0:
        return False, ""
    return True, f"{nearest.get('name', 'the target')} may leave a corpse ({nearest.get('corpse_chance')}%) and he needs food"


def filter_corpse_burners(game_state, abilities, hostiles, hp_ratio):
    """The ability list without the corpse-burning abilities when the policy withholds them (logged on change only)."""
    withhold, why = withhold_corpse_burners(game_state, hostiles, hp_ratio)
    if withhold != LASE_POLICY_STATE["withheld"]:
        LASE_POLICY_STATE["withheld"] = withhold
        print(f"[FOOD POLICY] {'Withholding Lase/fire abilities: ' + why if withhold else 'Lase and fire abilities available again.'}")
    if not withhold:
        return abilities
    return [a for a in abilities if not ability_registry.in_family(a, CORPSE_BURNER_FAMILY)]


# Retreat across the arrival border (HANDOFF issue 61). Gen 16 (level 5) stepped into a new zone, stood on its border for 12 turns Lasing a group of
# jells the engine rates Impossible, and died; one step back would have returned him to the cleared zone. When an Impossible hostile is in view
# and he is still within BORDER_RETREAT_RADIUS of the border he just came through, he goes back, and the exit that leads into that zone is
# written off (FAILED_ZONE_EXITS) so the exit chooser does not walk him straight back in. Stairs, when known, are used first (is_overwhelmed).
BORDER_RETREAT_RADIUS = 6
OPPOSITE_DIR = {"N": "S", "S": "N", "E": "W", "W": "E"}


def border_retreat_decision(game_state, zone_id, cur_pos, enemies):
    """A retreat decision through the border he arrived by, or None."""
    entry = LAST_ZONE_ENTRY
    if not entry or entry.get("to_zone") != zone_id or not entry.get("reverse_dir"):
        return None
    danger = [e for e in enemies
              if e.get("difficulty") == "Impossible" and e.get("has_los") is not False and e.get("dist", 999) <= 10
              and not is_ignorable_stationary_enemy(e)]
    if not danger:
        return None
    ex, ey = entry.get("entry_pos", (None, None))
    if ex is None or max(abs(cur_pos[0] - ex), abs(cur_pos[1] - ey)) > BORDER_RETREAT_RADIUS:
        return None
    rev = entry["reverse_dir"]
    px, py = cur_pos
    on_border = (rev == "W" and px == 0) or (rev == "E" and px == 79) or (rev == "N" and py == 0) or (rev == "S" and py == 24)
    from_zone = entry.get("from_zone")
    if from_zone:
        FAILED_ZONE_EXITS.add((from_zone, OPPOSITE_DIR.get(rev, rev)))
    names = ", ".join(sorted({e.get("name", "?") for e in danger})[:3])
    why = f"Danger retreat: {names} (Impossible) in view {min(e.get('dist', 99) for e in danger)} tiles away; going back through the {rev} border I arrived by"
    if on_border:
        return {"action": f"MOVE_{rev}", "reason": why, "flee_ok": True}
    return {"action": f"NAVIGATE_ZONE_EXIT:{rev}", "reason": why, "flee_ok": True}


# Reacting to being on fire (HANDOFF issue 32). Engine facts [verified in code, ENGINE_INTERNALS 12.1g]: `Burning` deals damage every turn
# and removes itself once the creature is no longer aflame; contact with liquid cools it (`LiquidVolume.ProcessExposure` /
# `GetLiquidCooling`). So: step into deep water if it is adjacent; otherwise move away from burning cells; otherwise let it burn out.
# Bounded (R6): after FIRE_REACTION_MAX consecutive reaction turns the normal logic takes over, so this can never become a loop.
FIRE_REACTION = {"turns": 0}
FIRE_REACTION_MAX = 10


def fire_reaction(game_state, surroundings, valid_moves):
    """Decision when the character is on fire, or None."""
    if not game_state.get("is_on_fire"):
        FIRE_REACTION["turns"] = 0
        return None
    if game_state.get("is_swimming") or FIRE_REACTION["turns"] >= FIRE_REACTION_MAX:
        return None
    swim = [m for m in valid_moves if is_swim_move(m, surroundings)]
    if swim:
        FIRE_REACTION["turns"] += 1
        return {"action": swim[0], "reason": f"ON FIRE: stepping into the water {swim[0][5:]} to put it out"}
    hazards = [CARDINAL_OFFSETS[d] for d in CARDINAL_OFFSETS if "[hazard: fire" in surroundings.get(d, "").lower()]
    if not hazards:
        return None
    best = None
    for m in valid_moves:
        mx, my = CARDINAL_OFFSETS[m[5:]]
        score = sum((mx - hx) ** 2 + (my - hy) ** 2 for hx, hy in hazards)
        if best is None or score > best[0]:
            best = (score, m)
    if best is None:
        return None
    FIRE_REACTION["turns"] += 1
    return {"action": best[1], "reason": f"ON FIRE: moving {best[1][5:]} away from the flames ({len(hazards)} burning cells adjacent)"}


# Autolevel circuit breaker (HANDOFF issue 56). Two AUTOLEVEL decisions in a row that leave the points unchanged stop autolevel so a purchase
# the game refuses cannot freeze the loop. It used to stay off until the points changed, and points only change on a level-up: a character
# sat on 134 unspent SP for a whole session. Now it retries after AUTOLEVEL_RETRY_TURNS.
AUTOLEVEL_RETRY_TURNS = 100


class AutolevelBreaker:
    def __init__(self):
        self.failed = 0
        self.last_points = None
        self.tripped_at = None

    def suppressed(self, points):
        if self.failed >= 2 and points == self.last_points:
            if self.tripped_at is not None and TURN_CLOCK - self.tripped_at >= AUTOLEVEL_RETRY_TURNS:
                self.failed = 0
                self.tripped_at = None
                return False
            return True
        return False

    def note_autolevel(self, points):
        """Called when the decision is an AUTOLEVEL action. True when the breaker trips on this attempt."""
        if points == self.last_points:
            self.failed += 1
        else:
            self.last_points = points
            self.failed = 1
        if self.failed >= 2:
            self.tripped_at = TURN_CLOCK
            return True
        return False

    def note_other(self, points):
        if points != self.last_points:
            self.failed = 0
            self.last_points = points
            self.tripped_at = None


# Burrowing Claws policy (HANDOFF issue 54, BACKLOG B7 promoted by the human 2026-10-06). The toggle (`CommandToggleBurrowingClaws`) is the
# "Digging" mode: with it on, the engine pathfinder (PathAsBurrower) and bumping walls dig through them [verified in code strings; the
# mechanism of the bump is inferred from 94 stationary NAVIGATE turns]. That is good in procedural dungeons and forbidden in a settlement (R7).
# So: off in towns, on everywhere else. A gap between toggles stops flicker when a peaceful NPC walks in and out of view.
CLAWS_COMMAND = "CommandToggleBurrowingClaws"
CLAWS_TOGGLE_GAP = 25
CLAWS_LAST_TOGGLE = {"turn": -10_000}


def claws_toggle_action(abilities, is_town):
    """USE_ABILITY decision that puts the claws toggle in the wanted state (off in towns, on elsewhere), or None."""
    ab = next((a for a in abilities or [] if str(a.get("command", "")).lower() == CLAWS_COMMAND.lower()), None)
    if not ab or not ab.get("usable", True) or ab.get("cooldown", 0) > 0:
        return None
    want_on = not is_town
    if bool(ab.get("active", False)) == want_on:
        return None
    if TURN_CLOCK - CLAWS_LAST_TOGGLE["turn"] < CLAWS_TOGGLE_GAP:
        return None
    CLAWS_LAST_TOGGLE["turn"] = TURN_CLOCK
    why = "settlements are off limits (R7): no digging through walls here" if is_town else "outside a settlement the claws dig through trees and walls on the engine's route"
    return {"action": f"USE_ABILITY:{CLAWS_COMMAND}", "reason": f"Burrowing Claws {'ON' if want_on else 'OFF'}: {why}"}


def find_zone_unexplored_frontier(game_state, cur_pos, visit_counts):
    """
    Finds a macro-level unexplored frontier in the current zone when local autoexplore stalls
    (e.g. when a zone is split by a river or lake).
    Prioritizes in-engine fog-of-war grid telemetry (unexplored_centroid) when available.
    Falls back to radar of visible_entities to find clusters of unvisited objects across water.
    Returns (target_pos, reason) or (None, None).
    """
    px, py = cur_pos

    # 1. In-engine fog-of-war grid telemetry (centroid or nearest unrevealed tiles)
    unexp_cells = game_state.get("unexplored_cells", None)
    if unexp_cells is not None and unexp_cells > 0:
        cx = game_state.get("unexplored_centroid_x", -1)
        cy = game_state.get("unexplored_centroid_y", -1)
        nx = game_state.get("nearest_unexplored_x", -1)
        ny = game_state.get("nearest_unexplored_y", -1)

        if 0 <= cx < 80 and 0 <= cy < 25 and (cx != px or cy != py):
            return (cx, cy), f"Water Traversal: Navigating across water toward unexplored sector at ({cx}, {cy}) ({unexp_cells} unrevealed cells)"
        if 0 <= nx < 80 and 0 <= ny < 25 and (nx != px or ny != py):
            return (nx, ny), f"Water Traversal: Navigating toward nearest unexplored cell at ({nx}, {ny}) ({unexp_cells} unrevealed cells)"

    entities = game_state.get("visible_entities", [])
    if not entities:
        return None, None

    # Check visible entities in unvisited sectors (e.g. across water/river)
    unvisited_entities = []
    for e in entities:
        tx = e.get("tx")
        ty = e.get("ty")
        if tx is not None and ty is not None:
            if visit_counts.get((tx, ty), 0) == 0:
                unvisited_entities.append((tx, ty))

    if unvisited_entities:
        distant_unvisited = [p for p in unvisited_entities if (p[0] != px or p[1] != py)]
        if distant_unvisited:
            # Sort by Chebyshev distance first, then Euclidean distance
            distant_unvisited.sort(key=lambda p: (max(abs(p[0] - px), abs(p[1] - py)), (p[0] - px)**2 + (p[1] - py)**2))
            target = distant_unvisited[0]
            return target, f"Water Traversal: Navigating across water toward unvisited frontier at {target}"

    return None, None


def _compute_adjacent_zone_id(zone_id, direction):
    """
    Compute the zone ID of the adjacent zone in the given cardinal direction.
    Zone IDs are formatted as: JoppaWorld.WX.WY.SX.SY.Z
    where WX/WY are world coordinates, SX/SY are sub-grid (0-2), Z is depth.
    Returns the adjacent zone ID string, or None if at world edge.
    """
    parts = zone_id.split(".")
    if len(parts) < 6:
        return None
    try:
        prefix = parts[0]
        wx, wy = int(parts[1]), int(parts[2])
        sx, sy = int(parts[3]), int(parts[4])
        z = parts[5]
    except (ValueError, IndexError):
        return None

    if direction == "N":
        sy -= 1
        if sy < 0:
            sy = 2
            wy -= 1
    elif direction == "S":
        sy += 1
        if sy > 2:
            sy = 0
            wy += 1
    elif direction == "E":
        sx += 1
        if sx > 2:
            sx = 0
            wx += 1
    elif direction == "W":
        sx -= 1
        if sx < 0:
            sx = 2
            wx -= 1
    else:
        return None

    if wx < 0 or wy < 0:
        return None
    return f"{prefix}.{wx}.{wy}.{sx}.{sy}.{z}"


# Direction -> (border_x, border_y_formula) for exit targets
_EXIT_TARGETS = {
    "N": lambda px, py: ((px, 1), "North zone exit"),
    "S": lambda px, py: ((px, 23), "South zone exit"),
    "E": lambda px, py: ((78, py), "East zone exit"),
    "W": lambda px, py: ((1, py), "West zone exit"),
}

# Reverse direction map
_OPPOSITE_DIR = {"N": "S", "S": "N", "E": "W", "W": "E"}


CURRENT_ZONE_CHOSEN_EXIT = None
CURRENT_ZONE_CHOSEN_EXIT_ZONE = None
FAILED_ZONE_EXITS = set()  # set of (zone_id, exit_dir)


def check_exit_direction_failure(game_state, cur_pos, chosen_exit):
    """
    Checks if the chosen exit direction in the current zone has failed due to:
    1. Direct movement failure (last_move_failed in that direction).
    2. Reachable edges telemetry confirming the exit is unreachable.
    3. Solid rock dead-end when reachable edges telemetry is absent.
    Returns True if the exit direction should be blacklisted as unreachable.
    """
    if not chosen_exit or not game_state:
        return False

    # 1. Did the engine report a movement failure in that direction?
    if game_state.get("last_move_failed", False):
        last_failed = (game_state.get("last_failed_dir", "") or "").upper()
        if last_failed.startswith("MOVE_"):
            last_failed = last_failed[5:]
        if last_failed in ("N", "S", "E", "W", "NE", "NW", "SE", "SW") and last_failed == chosen_exit:
            return True

    px, py = cur_pos
    is_on_border = (
        (chosen_exit == "W" and px == 0)
        or (chosen_exit == "E" and px == 79)
        or (chosen_exit == "N" and py == 0)
        or (chosen_exit == "S" and py == 24)
    )

    # 2. If the engine provided verified reachable edges telemetry, trust it!
    reachable_val = game_state.get("reachable_edges", None)
    if reachable_val is not None:
        if chosen_exit not in reachable_val and not is_on_border:
            return True
        if chosen_exit in reachable_val:
            return False

    # 3. Fallback for states without reachable_edges telemetry (e.g. synthetic test scenarios):
    surroundings = game_state.get("surroundings", {})
    if chosen_exit == "E":
        if (px >= 70 and all("[BLOCKED:" in surroundings.get(d, "") for d in ["E", "NE", "SE"])) or \
           all("[BLOCKED:" in surroundings.get(d, "") for d in ["E", "ENE", "EE", "ESE"]):
            return True
    elif chosen_exit == "W":
        if (px <= 10 and all("[BLOCKED:" in surroundings.get(d, "") for d in ["W", "NW", "SW"])) or \
           all("[BLOCKED:" in surroundings.get(d, "") for d in ["W", "WNW", "WW", "WSW"]):
            return True
    elif chosen_exit == "N":
        if (py <= 5 and all("[BLOCKED:" in surroundings.get(d, "") for d in ["N", "NW", "NE"])) or \
           all("[BLOCKED:" in surroundings.get(d, "") for d in ["N", "NNW", "NN", "NNE"]):
            return True
    elif chosen_exit == "S":
        if (py >= 20 and all("[BLOCKED:" in surroundings.get(d, "") for d in ["S", "SW", "SE"])) or \
           all("[BLOCKED:" in surroundings.get(d, "") for d in ["S", "SSW", "SS", "SSE"]):
            return True

    return False


EXIT_LOG_PATH = os.path.join(chronicler.MEMORY_DIR, "exit_choices.jsonl")

# Exit thrash circuit breaker (HANDOFF issue 42): repeated exit failures in one zone mean "stop hunting exits and explore".
TURN_CLOCK = 0                 # incremented once per query_decision call
EXIT_FAILURES = {}             # zone_id -> failures since the last suppression
EXIT_SUPPRESS_UNTIL = {}       # zone_id -> TURN_CLOCK value until which exit selection is switched off
EXIT_FAILURE_LIMIT = 4
EXIT_SUPPRESS_TURNS = 60


DECISION_TRACE_PATH = os.path.join(chronicler.MEMORY_DIR, "decision_trace.jsonl")
DECISION_TRACE_MAX_BYTES = 3_000_000


def log_decision_trace(record):
    """One JSON line per turn (action, reason, position and the flags behind the decision) so loops can be diagnosed from
    the file instead of pasted console output. Keeps one rotated backup (.1). Never raises."""
    try:
        if os.path.exists(DECISION_TRACE_PATH) and os.path.getsize(DECISION_TRACE_PATH) > DECISION_TRACE_MAX_BYTES:
            os.replace(DECISION_TRACE_PATH, DECISION_TRACE_PATH + ".1")
        with open(DECISION_TRACE_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + chr(10))
    except Exception:
        pass


def note_exit_failure(zone, direction):
    """Blacklists an exit direction for a zone and counts it. After EXIT_FAILURE_LIMIT failures, exit selection is
    suppressed for EXIT_SUPPRESS_TURNS turns so exploration (e.g. across water) can take over."""
    global CURRENT_ZONE_CHOSEN_EXIT, CURRENT_ZONE_CHOSEN_EXIT_ZONE
    FAILED_ZONE_EXITS.add((zone, direction))
    EXIT_FAILURES[zone] = EXIT_FAILURES.get(zone, 0) + 1
    if EXIT_FAILURES[zone] >= EXIT_FAILURE_LIMIT:
        EXIT_SUPPRESS_UNTIL[zone] = TURN_CLOCK + EXIT_SUPPRESS_TURNS
        EXIT_FAILURES[zone] = 0
        if CURRENT_ZONE_CHOSEN_EXIT_ZONE == zone:
            CURRENT_ZONE_CHOSEN_EXIT = None
            CURRENT_ZONE_CHOSEN_EXIT_ZONE = None
        print(f"[EXIT THRASH BREAKER] {EXIT_FAILURE_LIMIT} exit failures in {zone}: exploring instead of hunting exits for {EXIT_SUPPRESS_TURNS} turns.")


def log_exit_choice(record):
    """Appends one structured line per zone-exit decision (inputs and result) so exit bias can be diagnosed from data
    instead of guessed (HANDOFF issue 38). Never raises."""
    try:
        record = dict(record, ts=round(time.time(), 1))
        with open(EXIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + chr(10))
    except Exception:
        pass


def get_zone_exit_target(cur_pos, game_state=None):
    """
    Returns (target_coord, exit_tag, exit_dir) of the zone border exit to transition to the next zone.
    Chooses exits organically (random selection among novel / non-backtracking directions)
    to keep runs unpredictable, emergent, and diverse, while caching the decision for the duration
    of the zone so the character navigates steadily toward that chosen border without jittering.
    Prioritizes verified reachable edges from game_state telemetry when available.
    Automatically invalidates and blacklists exits that dead-end into solid rock or fail.
    """
    global CURRENT_ZONE_CHOSEN_EXIT, CURRENT_ZONE_CHOSEN_EXIT_ZONE, FAILED_ZONE_EXITS
    px, py = cur_pos
    cur_zone = (game_state.get("zone_id") if game_state else None) or current_zone_id or ""

    if EXIT_SUPPRESS_UNTIL.get(cur_zone, 0) > TURN_CLOCK:
        CURRENT_ZONE_CHOSEN_EXIT = None
        CURRENT_ZONE_CHOSEN_EXIT_ZONE = None
        return (px, py), "Exits suppressed after repeated failures", None

    # Check if current chosen exit has dead-ended or failed
    if CURRENT_ZONE_CHOSEN_EXIT and CURRENT_ZONE_CHOSEN_EXIT_ZONE == cur_zone:
        if game_state and check_exit_direction_failure(game_state, cur_pos, CURRENT_ZONE_CHOSEN_EXIT):
            print(f"[ZONE EXIT FAILED]: Exit {CURRENT_ZONE_CHOSEN_EXIT} in zone {cur_zone} is blocked by impassable dead-end terrain at {cur_pos}. Blacklisting and re-routing.")
            note_exit_failure(cur_zone, CURRENT_ZONE_CHOSEN_EXIT)
            CURRENT_ZONE_CHOSEN_EXIT = None
            CURRENT_ZONE_CHOSEN_EXIT_ZONE = None

    reachable_val = game_state.get("reachable_edges", None) if game_state else None
    reachable_set = set(reachable_val) if reachable_val is not None and reachable_val != "" else None
    reachable_telemetry_present = (reachable_val is not None)

    # If an exit was already chosen for this zone, check if it's still valid/reachable
    if CURRENT_ZONE_CHOSEN_EXIT and CURRENT_ZONE_CHOSEN_EXIT_ZONE == cur_zone:
        if reachable_telemetry_present and (reachable_set is None or CURRENT_ZONE_CHOSEN_EXIT not in reachable_set):
            print(f"[ZONE EXIT INVALIDATED]: Previously chosen exit {CURRENT_ZONE_CHOSEN_EXIT} in zone {cur_zone} is not in reachable edges '{reachable_val}'. Blacklisting.")
            note_exit_failure(cur_zone, CURRENT_ZONE_CHOSEN_EXIT)
            CURRENT_ZONE_CHOSEN_EXIT = None
            CURRENT_ZONE_CHOSEN_EXIT_ZONE = None
        elif (cur_zone, CURRENT_ZONE_CHOSEN_EXIT) not in FAILED_ZONE_EXITS:
            pos, tag = _EXIT_TARGETS[CURRENT_ZONE_CHOSEN_EXIT](px, py)
            return pos, tag, CURRENT_ZONE_CHOSEN_EXIT

    rev_dir = LAST_ZONE_ENTRY.get("reverse_dir") if LAST_ZONE_ENTRY else None

    # The engine reports NO reachable edges (e.g. a companion is sealing a one-tile corridor). That is transient: do not
    # pick anything and above all do not run the "all failed" reset below, which wiped every blacklisted exit and let
    # the same two failing exits be re-picked forever (HANDOFF issue 42).
    if reachable_telemetry_present and not reachable_set:
        return (px, py), "No Reachable Exit", None

    # Determine candidate directions: prioritize reachable edges if telemetry provides them,
    # and strictly exclude directions known to have failed/dead-ended in this zone
    if reachable_telemetry_present:
        all_dirs = [d for d in ["N", "S", "E", "W"] if reachable_set and d in reachable_set]
    else:
        all_dirs = ["N", "S", "E", "W"]

    if game_state:
        for d in list(all_dirs):
            if check_exit_direction_failure(game_state, cur_pos, d):
                FAILED_ZONE_EXITS.add((cur_zone, d))
    candidates = [d for d in all_dirs if d != rev_dir and (cur_zone, d) not in FAILED_ZONE_EXITS]
    if not candidates:
        candidates = [d for d in all_dirs if (cur_zone, d) not in FAILED_ZONE_EXITS]
    if not candidates and reachable_telemetry_present:
        # If all candidates failed, reset failed exits ONLY within reachable_set
        FAILED_ZONE_EXITS = {f for f in FAILED_ZONE_EXITS if f[0] != cur_zone or (reachable_set and f[1] not in reachable_set)}
        candidates = [d for d in all_dirs if d != rev_dir] or all_dirs
    elif not candidates:
        # If all candidates somehow failed, reset failed exits for this zone as a fallback
        FAILED_ZONE_EXITS = {f for f in FAILED_ZONE_EXITS if f[0] != cur_zone}
        candidates = [d for d in all_dirs if d != rev_dir] or all_dirs or ["N", "S", "E", "W"]

    if not candidates:
        return (px, py), "No Reachable Exit", None

    # In subterranean strata (z > 10), prioritize directions suggested by unexplored boundaries / corridors
    cur_z = game_state.get("z", 10) if game_state else 10
    prioritized = []
    if cur_z > 10 and game_state:
        ny = game_state.get("nearest_unexplored_y", -1)
        nx = game_state.get("nearest_unexplored_x", -1)
        if ny >= 0 and ny < py and "N" in candidates:
            prioritized.append("N")
        if ny >= 0 and ny > py and "S" in candidates:
            prioritized.append("S")
        if nx >= 0 and nx > px and "E" in candidates:
            prioritized.append("E")
        if nx >= 0 and nx < px and "W" in candidates:
            prioritized.append("W")
        if prioritized:
            candidates = prioritized + [c for c in candidates if c not in prioritized]

    # Check for novel (unvisited) adjacent zones
    cycle_zones = set(list(RECENT_ZONES)[-max(ZONE_CYCLE_LENGTH, 2):]) if ZONE_HOPPING_DETECTED else set()
    avoid_zones = cycle_zones | EXPLORED_ZONE_SET

    novel_candidates = []
    for d in candidates:
        adj_zone = _compute_adjacent_zone_id(cur_zone, d)
        if adj_zone and adj_zone not in avoid_zones:
            novel_candidates.append(d)

    _log_base = {
        "zone": cur_zone, "pos": [px, py], "reachable": reachable_val, "rev": rev_dir,
        "failed_here": sorted(d for (zz, d) in FAILED_ZONE_EXITS if zz == cur_zone),
        "explored_neighbors": sorted(d for d in ["N", "S", "E", "W"] if _compute_adjacent_zone_id(cur_zone, d) in EXPLORED_ZONE_SET),
        "cycle_neighbors": sorted(d for d in ["N", "S", "E", "W"] if _compute_adjacent_zone_id(cur_zone, d) in cycle_zones),
        "candidates": list(candidates), "novel": list(novel_candidates),
    }

    # Prefer novel unvisited zones if available to foster organic world exploration
    if novel_candidates:
        prioritized_novel = [d for d in prioritized if d in novel_candidates]
        chosen_dir = prioritized_novel[0] if prioritized_novel else random.choice(novel_candidates)
        pos, tag = _EXIT_TARGETS[chosen_dir](px, py)
        CURRENT_ZONE_CHOSEN_EXIT = chosen_dir
        CURRENT_ZONE_CHOSEN_EXIT_ZONE = cur_zone
        label = f"{tag} (novel)"
        log_exit_choice(dict(_log_base, chosen=chosen_dir, mode="novel", hopping=bool(ZONE_HOPPING_DETECTED)))
        if ZONE_HOPPING_DETECTED:
            print(f"[ZONE HOPPING BREAKER] Organically picked novel exit {chosen_dir} ({label}) avoiding cycle: {avoid_zones}")
        else:
            print(f"[ORGANIC EXPLORATION] Selected organic novel exit {chosen_dir} ({label}) for zone {cur_zone}")
        return pos, label, chosen_dir

    # If no strictly novel zones are detected, pick among candidates
    prioritized_candidates = [d for d in prioritized if d in candidates]
    chosen_dir = prioritized_candidates[0] if prioritized_candidates else random.choice(candidates)
    pos, tag = _EXIT_TARGETS[chosen_dir](px, py)
    CURRENT_ZONE_CHOSEN_EXIT = chosen_dir
    CURRENT_ZONE_CHOSEN_EXIT_ZONE = cur_zone
    log_exit_choice(dict(_log_base, chosen=chosen_dir, mode="any", hopping=bool(ZONE_HOPPING_DETECTED)))
    print(f"[ORGANIC EXPLORATION] Selected organic exit {chosen_dir} ({tag}) for zone {cur_zone}")
    return pos, tag, chosen_dir


def is_valid_stair_down(name: str, bp: str = "") -> bool:
    """Validates that a detected down passage is genuine terrain/architecture, not a plant, creature, or vine."""
    name_l = (name or "").lower()
    bp_l = (bp or "").lower()
    combined = f"{name_l} {bp_l}"
    invalid_keywords = [
        "vine", "spit", "plant", "creature", "fungus", "corpse", "seed",
        "tree", "bush", "flower", "spider", "beetle", "worm", "fly", "centipede"
    ]
    if any(k in combined for k in invalid_keywords):
        return False
    if "pit" in combined:
        words = set(re.findall(r"\w+", combined))
        if "pit" not in words and not any(w.startswith("pit") or w.endswith("pit") for w in words):
            return False
    return True


def get_stair_priority(name: str, bp: str = "") -> int:
    """Returns priority for down passages: 2 for staircases/ladders, 1 for pits/holes/shafts/chasms."""
    combined = f"{(name or '').lower()} {(bp or '').lower()}"
    if "stair" in combined or "ladder" in combined:
        return 2
    return 1


def update_stair_records(game_state):
    """
    Ingests stairs_down and stairs_up telemetry from state.json,
    maintaining persistent spatial memory of discovered staircases across zones.
    Filters out plants/vines/creatures and prioritizes true staircases over pits/holes.
    """
    zone_id = game_state.get("zone_id", "")
    cur_z = game_state.get("z", 10)
    cur_lvl = game_state.get("level", 1)

    # 1. Ingest stairs down from dedicated telemetry
    raw_sd = game_state.get("stairs_down", [])
    valid_sd = []
    for sd in raw_sd:
        sname = sd.get("name", "stairs down")
        sbp = sd.get("blueprint", "")
        if is_valid_stair_down(sname, sbp):
            valid_sd.append(sd)

    # Sort so higher priority (stairs down > pit/hole) is processed last
    valid_sd.sort(key=lambda s: get_stair_priority(s.get("name", ""), s.get("blueprint", "")))

    for sd in valid_sd:
        stx, sty = sd.get("tx"), sd.get("ty")
        if stx is not None and sty is not None and zone_id:
            sname = sd.get("name", "stairs down")
            sbp = sd.get("blueprint", "")
            req_lvl = min_level_for_depth(cur_z + 1)
            prio = get_stair_priority(sname, sbp)
            prev = KNOWN_STAIRS_DOWN.get(zone_id)
            prev_prio = prev.get("priority", 0) if prev else 0

            # Don't downgrade from a staircase (priority 2) to a pit (priority 1)
            if prev and prev_prio > prio:
                continue

            if not prev or prev.get("tx") != stx or prev.get("ty") != sty:
                print(f"[STAIRCASE NOTED]: Discovered {sname} at ({stx}, {sty}) in {zone_id}. Delving requires Level {req_lvl} (Current: {cur_lvl}).")
            KNOWN_STAIRS_DOWN[zone_id] = {
                "tx": stx, "ty": sty, "z": cur_z, "name": sname, "req_level": req_lvl, "priority": prio
            }

    # Fallback to visible_entities for stairs down
    for ent in game_state.get("visible_entities", []):
        ename = ent.get("name", "").lower()
        ebp = ent.get("blueprint", "").lower()
        if ("stair" in ename or "stair" in ebp or "hole" in ename or "shaft" in ename or "ladder" in ename) and "down" in ename:
            if not is_valid_stair_down(ename, ebp):
                continue
            stx, sty = ent.get("tx"), ent.get("ty")
            if stx is not None and sty is not None and zone_id:
                prio = get_stair_priority(ename, ebp)
                prev = KNOWN_STAIRS_DOWN.get(zone_id)
                prev_prio = prev.get("priority", 0) if prev else 0
                if prev and prev_prio > prio:
                    continue
                req_lvl = min_level_for_depth(cur_z + 1)
                if not prev or prev.get("tx") != stx or prev.get("ty") != sty:
                    print(f"[STAIRCASE NOTED]: Discovered {ent.get('name')} at ({stx}, {sty}) in {zone_id}. Delving requires Level {req_lvl} (Current: {cur_lvl}).")
                KNOWN_STAIRS_DOWN[zone_id] = {
                    "tx": stx, "ty": sty, "z": cur_z, "name": ent.get("name", "stairs down"), "req_level": req_lvl, "priority": prio
                }

    # 2. Ingest stairs up from dedicated telemetry
    raw_su = game_state.get("stairs_up", [])
    for su in raw_su:
        stx, sty = su.get("tx"), su.get("ty")
        if stx is not None and sty is not None and zone_id:
            sname = su.get("name", "stairs up")
            sbp = su.get("blueprint", "")
            if is_valid_stair_down(sname, sbp):
                KNOWN_STAIRS_UP[zone_id] = {
                    "tx": stx, "ty": sty, "z": cur_z, "name": sname
                }

    # Fallback to visible_entities for stairs up
    for ent in game_state.get("visible_entities", []):
        ename = ent.get("name", "").lower()
        ebp = ent.get("blueprint", "").lower()
        if ("stair" in ename or "stair" in ebp or "hole" in ename or "shaft" in ename or "ladder" in ename) and "up" in ename:
            if not is_valid_stair_down(ename, ebp):
                continue
            stx, sty = ent.get("tx"), ent.get("ty")
            if stx is not None and sty is not None and zone_id and zone_id not in KNOWN_STAIRS_UP:
                KNOWN_STAIRS_UP[zone_id] = {
                    "tx": stx, "ty": sty, "z": cur_z, "name": ent.get("name", "stairs up")
                }


DESTRUCTIBLE_OBSTACLE_KEYWORDS = [
    "plant matter", "plantwall", "plant wall", "mudroot", "tangled mudroot",
    "wood", "fence", "web", "fungus", "tree", "brush", "bramble", "vine", "wall"
]


def find_burrow_direction(surroundings, cur_pos, target_pos=None, is_town=False, exclude=None):
    """
    Finds the best adjacent destructible obstacle (e.g. plant matter, tangled mudroot)
    to attack/burrow through when the agent is trapped in an enclosed pocket.
    Prioritizes directions that advance toward target_pos (e.g. unexplored centroid).
    NEVER burrows in towns or settlements!
    """
    if is_town:
        return None, None

    candidates = []
    px, py = cur_pos
    tx, ty = target_pos if target_pos else (px, py)

    for d in ["N", "S", "E", "W", "NE", "NW", "SE", "SW"]:
        if exclude and d in exclude:
            continue
        info = surroundings.get(d, "").lower()
        if "[blocked:" in info or "impassable" in info or "wall" in info:
            if any(k in info for k in DESTRUCTIBLE_OBSTACLE_KEYWORDS):
                dx, dy = CARDINAL_OFFSETS[d]
                nx, ny = px + dx, py + dy
                dist_to_target = (nx - tx) ** 2 + (ny - ty) ** 2
                # Prioritize softer materials (plant matter, mudroot, web) over solid rock
                is_soft = any(k in info for k in ["plant", "mudroot", "web", "vine", "wood", "fungus", "brush"])
                score = (0 if is_soft else 1, dist_to_target)
                candidates.append((score, d, info))

    if candidates:
        candidates.sort(key=lambda x: x[0])
        best_score, best_d, best_info = candidates[0]
        clean_tag = next((k for k in DESTRUCTIBLE_OBSTACLE_KEYWORDS if k in best_info), "wall")
        return best_d, clean_tag
    return None, None


def register_companion(coord=None):
    """Remembers an allied companion's cell. Never by name: one recruited baboon must not make every baboon an ally
    (AGENTS.md R2/R3: the engine owns companion status, exported as `is_companion` / `companions`)."""
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
    # Short keywords must be whole words: "tam" (a Joppa NPC) is a substring of "GiantAmoeba", "Metamorphic Polygel" and "Stamped Data
    # Disk", and made the brain treat a giant amoeba as a peaceful citizen and the whole marsh as a town (HANDOFF issue 60).
    words = set(re.findall(r"[a-z]+|\d+", nl)) | {w.lower() for w in re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+", blueprint or "")}
    for pk in peaceful_keywords:
        if len(pk) <= 4:
            if pk in words:
                return True
        elif pk in combined:
            return True
    return False


SETTLEMENT_KEYWORDS = [
    "joppa", "stilt", "grit gate", "kyakukya", "yd freehold", "bey lah",
    "omonporch", "ezra", "settlement", "village", "town", "commune",
    "enclave", "haven", "bazaar", "kith and kin", "pariah"
]


def is_town_zone(game_state):
    """
    Checks whether the agent is currently in a peaceful town or settlement
    where attacking structures, huts, or walls is strictly forbidden.
    """
    if not game_state:
        return False
    if game_state.get("is_settlement", False):
        return True
    zone_name = (game_state.get("zone_name") or "").lower()
    if any(k in zone_name for k in SETTLEMENT_KEYWORDS):
        return True
    # If any visible entity is a peaceful townsfolk, treat as town
    for e in game_state.get("visible_entities", []):
        if is_peaceful_npc(e.get("name"), e.get("blueprint")):
            return True
    return False


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
    if entity.get("is_swimming") or "[swimming]" in ename:
        return False
    combined = f"{ename} {bp}"
    if any(ex in combined for ex in PROSELYTIZE_EXCLUSIONS):
        return False
    etx, ety = entity.get("tx"), entity.get("ty")
    comp_coords = set(CHARMED_COMPANION_COORDS)
    for c in (companions or []):
        if c.get("tx") is not None and c.get("ty") is not None:
            comp_coords.add((c.get("tx"), c.get("ty")))
    if (etx, ety) in comp_coords:
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


def pick_model_id(v0_models, v1_models, override=None):
    """The model to talk to: the override; else a LOADED chat model from LM Studio's own listing; else the first non-embedding model of
    the OpenAI-style listing. (It used to be "the first entry of /v1/models", which lists every downloaded model, embeddings included.)"""
    if override:
        return override
    for m in v0_models or []:
        if m.get("state") == "loaded" and m.get("type") in ("llm", "vlm"):
            return m.get("id")
    for m in v1_models or []:
        mid = str(m.get("id", ""))
        if mid and "embed" not in mid.lower():
            return mid
    return None


def detect_lm_studio_model():
    global active_model_id
    v0, v1 = [], []
    try:
        res = requests.get(LM_STUDIO_MODELS_V0_URL, timeout=3)
        if res.status_code == 200:
            v0 = res.json().get("data", [])
    except Exception:
        pass
    try:
        res = requests.get(LM_STUDIO_MODELS_URL, timeout=3)
        if res.status_code == 200:
            v1 = res.json().get("data", [])
    except Exception as e:
        print(f"[LM Studio Warning] Could not reach LM Studio on port 1234: {e}")
    chosen = pick_model_id(v0, v1, LM_MODEL_OVERRIDE)
    if chosen:
        active_model_id = chosen
        why = "forced by QUDAI_LM_MODEL" if LM_MODEL_OVERRIDE else "loaded in LM Studio"
        print(f"[LM Studio Connected] Active model: {active_model_id} ({why}); combat call timeout {LM_STUDIO_TIMEOUT:.0f}s")
        return active_model_id
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
        is_stair_passage = "[stairs_down" in text or "[stairs_up" in text
        if not is_stair_passage and any(w in text for w in ["wall", "rock", "chasm", "[blocked", "[hazard", "acid", "lava", "magma", "cushion", "chair", "table", "bed", "bedroll", "statue", "tombstone"]):
            continue
        # During active combat, avoid blindly fleeing off the map into unknown zones
        if is_in_combat and ("[zone_exit" in text or "exit" in text):
            continue

        # If a friendly companion occupies this adjacent cell, avoid bumping into them
        if target_pos in CHARMED_COMPANION_COORDS or "[companion" in text:
            companion_moves.append(move_name)
            continue

        # Neutral/Friendly NPCs occupy their tile out of combat; do not bump into them
        if not is_in_combat and "[npc:" in text:
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
            is_stair_passage = "[stairs_down" in text or "[stairs_up" in text
            if not is_stair_passage and any(w in text for w in ["wall", "rock", "chasm", "[blocked", "[hazard", "acid", "lava", "magma", "cushion", "chair", "table", "bed", "bedroll", "statue", "tombstone"]):
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
        if '[blocked' in t or 'wall' in t or 'rock' in t or 'fence' in t or 'boulder' in t:
            return '#'
        if 'door' in t:
            return '+'
        if '[item' in t:
            return '$'
        if 'exit' in t:
            return '|'
        if '[swim' in t or 'water' in t or 'pool' in t or 'puddle' in t or 'deep liquid' in t:
            return '~'
        return '.'

    rows = []
    for r in OFFSETS_5X5:
        chars = [get_sym(surroundings.get(k, ''), (dx == 0 and dy == 0)) for (k, dx, dy) in r]
        rows.append('  ' + ' '.join(chars))
    return '\n'.join(rows)


def get_adjacent_threats(surroundings, companions=None, cur_pos=None):
    adj = {}
    # Companions are excluded by the engine's [COMPANION:] cell tag, never by name (same-species hostiles exist).
    for d in ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]:
        text = surroundings.get(d, "")
        if "[COMPANION:" in text or "[companion" in text.lower():
            continue
        if "[NPC:" in text or "[npc:" in text.lower():
            continue
        if "[ENEMY:" in text:
            m = re.search(r"\[ENEMY:\s*([^\]]+)\]", text)
            ename = m.group(1).strip() if m else "Enemy"
            if is_peaceful_npc(ename):
                continue
            adj[d] = ename
    if cur_pos:
        adj = drop_companion_cells(adj, cur_pos, companions)
    return adj


# Ability use evidence (HANDOFF issue 52): C# reports each USE_ABILITY in `last_ability_use` (cooldown before/after, refusal).
# Counted per engine command in memory/ability_stats.json, kept across characters, so "this ability works" is measured.
ABILITY_STATS_PATH = os.path.join(chronicler.MEMORY_DIR, "ability_stats.json")
ABILITY_LAST_SEQ = {"seq": 0}


def note_ability_use(game_state):
    """Counts the engine's report of the last ability use: attempts, fired (cooldown rose), refused (C# pre-check). Never raises."""
    try:
        lu = game_state.get("last_ability_use")
        if not lu or lu.get("seq", 0) <= ABILITY_LAST_SEQ["seq"]:
            return
        ABILITY_LAST_SEQ["seq"] = lu.get("seq", 0)
        cmd = lu.get("command", "")
        if not cmd:
            return
        try:
            with open(ABILITY_STATS_PATH, "r", encoding="utf-8") as f:
                stats = json.load(f)
        except (OSError, ValueError):
            stats = {}
        rec = stats.setdefault(cmd, {"attempts": 0, "fired": 0, "refused": 0, "unknown": 0})
        rec["attempts"] += 1
        if lu.get("refused"):
            rec["refused"] += 1
            rec["last_refusal"] = lu.get("reason", "")
        elif lu.get("fired"):
            rec["fired"] += 1
        if not lu.get("known", True):
            rec["unknown"] += 1
        rec["last_seen"] = time.strftime("%Y-%m-%d %H:%M:%S")
        tmp = ABILITY_STATS_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=1, sort_keys=True)
        os.replace(tmp, ABILITY_STATS_PATH)
        if lu.get("refused"):
            print(f"[ABILITY] {cmd} refused by the game: {lu.get('reason')}")
        elif not lu.get("fired"):
            print(f"[ABILITY] {cmd} used but its cooldown did not change (cd {lu.get('cd_before')} -> {lu.get('cd_after')}); it may not have fired.")
    except Exception:
        pass


# Burrow progress (HANDOFF issue 45): C# reports each ATTACK_WALL swing in `last_burrow` (target HP before/after, destroyed).
BURROW_STALL_LIMIT = 3          # swings that did no damage before the target is written off
BURROW_BLOCK_TURNS = 400
BURROW_BLOCKED = {}             # (zone_id, x, y) -> TURN_CLOCK value until which this obstacle is not burrowed
BURROW_PROGRESS = {}            # (zone_id, x, y) -> {"stalled": int}
BURROW_LAST_SEQ = {"seq": 0}


def note_burrow_progress(game_state):
    """Reads the engine's report of the last burrow swing. Keep swinging while the target loses hit points; write it off
    when it has no hit points, or three swings in a row did no damage; forget it when it is destroyed."""
    lb = game_state.get("last_burrow")
    if not lb or lb.get("seq", 0) <= BURROW_LAST_SEQ["seq"]:
        return
    BURROW_LAST_SEQ["seq"] = lb.get("seq", 0)
    key = (game_state.get("zone_id"), lb.get("x"), lb.get("y"))
    name = lb.get("name", "obstacle")
    if lb.get("destroyed"):
        BURROW_PROGRESS.pop(key, None)
        BURROW_BLOCKED.pop(key, None)
        print(f"[BURROW] {name} destroyed.")
        return
    if not lb.get("has_hp"):
        BURROW_BLOCKED[key] = TURN_CLOCK + BURROW_BLOCK_TURNS
        print(f"[BURROW] {name} has no hit points: it cannot be broken. Writing it off.")
        _written_off_obstacle_blocks_frontier(game_state)
        return
    prog = BURROW_PROGRESS.setdefault(key, {"stalled": 0})
    if lb.get("hp_after", 0) >= lb.get("hp_before", 0):
        prog["stalled"] += 1
        if prog["stalled"] >= BURROW_STALL_LIMIT:
            BURROW_BLOCKED[key] = TURN_CLOCK + BURROW_BLOCK_TURNS
            print(f"[BURROW] {name} took no damage in {BURROW_STALL_LIMIT} swings (HP {lb.get('hp_after')}/{lb.get('max_hp')}). Writing it off.")
            _written_off_obstacle_blocks_frontier(game_state)
    else:
        prog["stalled"] = 0
        print(f"[BURROW] {name}: HP {lb.get('hp_after')}/{lb.get('max_hp')}.")


def _written_off_obstacle_blocks_frontier(game_state):
    """The path to the committed frontier target runs through an obstacle that cannot be broken: write the target off too
    (otherwise the engine keeps listing it as reachable and the walk starts the same swings again)."""
    zone_id = game_state.get("zone_id")
    if FRONTIER_COMMIT["zone"] == zone_id and FRONTIER_COMMIT["target"] is not None:
        _frontier_write_off(zone_id, FRONTIER_COMMIT["target"], "its path runs through an obstacle that cannot be broken")


def blocked_burrow_dirs(zone_id, cur_pos):
    """Directions whose adjacent cell holds an obstacle already written off as unbreakable."""
    out = set()
    for d, (dx, dy) in CARDINAL_OFFSETS.items():
        exp = BURROW_BLOCKED.get((zone_id, cur_pos[0] + dx, cur_pos[1] + dy))
        if exp is not None and exp > TURN_CLOCK:
            out.add(d)
    return out


def guard_blocked_burrow(action, reason, surroundings, cur_pos, zone_id, is_town=False):
    """Replaces a burrow (ATTACK_WALL) aimed at an obstacle written off as unbreakable: another breakable obstacle if one
    exists, otherwise a free move, otherwise a passed turn. Returns (action, reason)."""
    if not action.startswith("ATTACK_WALL"):
        return action, reason
    parts = action.split(":")
    if len(parts) < 2:
        return action, reason
    bad = blocked_burrow_dirs(zone_id, cur_pos)
    if parts[1].strip().upper() not in bad:
        return action, reason
    alt, info = find_burrow_direction(surroundings, cur_pos, None, is_town=is_town, exclude=bad)
    if alt:
        return f"ATTACK_WALL:{alt}", f"[Burrow] {parts[1]} is unbreakable; trying {info} ({alt}) instead."
    moves = [m for m in get_valid_moves(surroundings, cur_pos, None, is_in_combat=False)
             if "[companion" not in surroundings.get(m[5:], "").lower()]
    if moves:
        moves.sort(key=lambda m: visit_counts[(cur_pos[0] + CARDINAL_OFFSETS[m[5:]][0], cur_pos[1] + CARDINAL_OFFSETS[m[5:]][1])])
        return moves[0], f"[Burrow] {parts[1]} is unbreakable and nothing else is breakable; taking the least-visited free move."
    return "PASS", f"[Burrow] {parts[1]} is unbreakable and nothing else is breakable; passing the turn."


COMPANION_BLOCK = {"pos": None, "tries": 0}   # where a companion has been blocking the only exit, and how many tries


def guard_companion_blocked_burrow(action, reason, surroundings, cur_pos):
    """Returns (action, reason). Replaces a burrow (ATTACK_WALL) with swap/wait when the only exit is a companion.

    In a one-tile dead-end corridor a recruited pet can stand in the only way out. The engine pathfinder treats it as a
    wall, autoexplore reports "stuck", and the loop breakers then chew on solid rock forever (HANDOFF issue 41). Burrowing
    cannot help there, so try to swap with the companion (MOVE into it), and every third try wait a turn so it can move.
    """
    if not action.startswith("ATTACK_WALL"):
        return action, reason
    comp_dirs = [d for d in ["N", "S", "E", "W", "NE", "NW", "SE", "SW"] if "[companion" in surroundings.get(d, "").lower()]
    if not comp_dirs:
        return action, reason
    open_noncomp = [m for m in get_valid_moves(surroundings, cur_pos, None, is_in_combat=False)
                    if "[companion" not in surroundings.get(m[5:], "").lower()]
    if open_noncomp:
        return action, reason
    st = COMPANION_BLOCK
    if st["pos"] != cur_pos:
        st["pos"], st["tries"] = cur_pos, 0
    st["tries"] += 1
    if st["tries"] % 3 == 0:
        return "WAIT", f"[Companion Block] Only exit {comp_dirs[0]} is occupied by a companion; waiting a turn for it to move instead of burrowing."
    return f"MOVE_{comp_dirs[0]}", f"[Companion Block] Only exit {comp_dirs[0]} is occupied by a companion; trying to swap places instead of burrowing."


def drop_companion_cells(adj_threats, cur_pos, companions):
    """Removes adjacent 'threats' standing on a known companion cell. Matches by coordinates only, never by name."""
    if not adj_threats:
        return adj_threats
    comp_coords = set(CHARMED_COMPANION_COORDS)
    for c in (companions or []):
        if c.get("tx") is not None and c.get("ty") is not None:
            comp_coords.add((c.get("tx"), c.get("ty")))
    return {
        d: ename for d, ename in adj_threats.items()
        if (cur_pos[0] + CARDINAL_OFFSETS[d][0], cur_pos[1] + CARDINAL_OFFSETS[d][1]) not in comp_coords
    }


def filter_hostile_enemies(entities, companions=None):
    """
    Strictly filters a list of entities to only include true hostiles.
    Companions, pets, followers, and peaceful NPCs/citizens are permanently excluded.
    """
    if not entities:
        return []
    comp_coords = set(CHARMED_COMPANION_COORDS)
    if companions:
        for c in companions:
            cx, cy = c.get("tx"), c.get("ty")
            if cx is not None and cy is not None:
                comp_coords.add((cx, cy))

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
        if is_peaceful_npc(ename, bp):
            continue
        result.append(e)
    return result


def choose_food_source(game_state, zone_id, learned_skills, last_act):
    """Picks the nearest butcherable corpse / harvestable plant (exported by C# as `food_sources`) that the character
    has the skill for, and returns a committed NAVIGATE_TO_CELL decision, or None.

    Targets that the engine pathfinder cannot reach (`last_failed_dir == PATH_BLOCKED`) or that take too long are
    blacklisted. Adjacent sources (dist <= 1) are left to the BUTCHER/HARVEST step."""
    global FOOD_TURN
    FOOD_TURN += 1
    for k in [k for k, exp in FOOD_BLACKLIST.items() if exp <= FOOD_TURN]:
        del FOOD_BLACKLIST[k]
    cur_key = FOOD_PURSUIT["key"]
    if (cur_key and game_state.get("last_move_failed") and game_state.get("last_failed_dir") == "PATH_BLOCKED"
            and last_act and last_act.startswith("NAVIGATE_TO_CELL:")):
        FOOD_BLACKLIST[cur_key] = FOOD_TURN + FOOD_BLACKLIST_TURNS
        FOOD_PURSUIT.update({"key": None, "turns": 0})
    allowed = set()
    if "CookingAndGathering_Butchery" in learned_skills:
        allowed.add("corpse")
    if "CookingAndGathering_Harvestry" in learned_skills:
        allowed.add("plant")
    best = None
    for s in game_state.get("food_sources", []) or []:
        if s.get("kind") not in allowed or s.get("dist", 0) < 2:
            continue
        key = (zone_id, s.get("tx"), s.get("ty"))
        if key in FOOD_BLACKLIST:
            continue
        rank = (0 if s.get("kind") == "corpse" else 1, s.get("dist", 999))
        if best is None or rank < best[0]:
            best = (rank, key, s)
    if best is None:
        FOOD_PURSUIT.update({"key": None, "turns": 0})
        return None
    _, key, s = best
    if FOOD_PURSUIT["key"] == key:
        FOOD_PURSUIT["turns"] += 1
    else:
        FOOD_PURSUIT.update({"key": key, "turns": 1})
    if FOOD_PURSUIT["turns"] > FOOD_PURSUIT_MAX_TURNS:
        FOOD_BLACKLIST[key] = FOOD_TURN + FOOD_BLACKLIST_TURNS
        FOOD_PURSUIT.update({"key": None, "turns": 0})
        return None
    verb = "butcher" if s.get("kind") == "corpse" else "harvest"
    return {"action": f"NAVIGATE_TO_CELL:{s.get('tx')},{s.get('ty')}",
            "reason": f"Foraging: walking to {s.get('name', 'food')} ({s.get('dist')} tiles) to {verb} it for food"}


# Loot (HANDOFF issue 59, BACKLOG B6, human decision 2026-10-06: take everything unowned). C# exports `loot_sources` (unowned ground items the
# engine would autoget, and unowned chests that still hold something; never in settlements) and does the taking (`LOOT`, and a loot step
# inside AUTOEXPLORE). Python only walks to the nearest one, with the same guards as foraging.
LOOT_BLACKLIST = {}            # (zone_id, tx, ty) -> LOOT_TURN value when the entry expires
LOOT_PURSUIT = {"key": None, "turns": 0}
LOOT_TURN = 0
LOOT_PURSUIT_MAX_TURNS = 40
LOOT_BLACKLIST_TURNS = 300
LOOT_STREAK_MAX = 4            # consecutive LOOT actions at one spot before the spot is written off
LOOT_STREAK = {"key": None, "count": 0}
LOOT_LAST_SEQ = {"seq": 0}


def choose_loot_action(game_state, zone_id, last_act, is_town):
    """`LOOT` when a loot source is on or next to him, a committed NAVIGATE_TO_CELL when one is in view, else None."""
    global LOOT_TURN
    LOOT_TURN += 1
    for k in [k for k, exp in LOOT_BLACKLIST.items() if exp <= LOOT_TURN]:
        del LOOT_BLACKLIST[k]
    sources = game_state.get("loot_sources") or []
    if is_town or game_state.get("is_swimming") or not sources:
        LOOT_PURSUIT.update({"key": None, "turns": 0})
        LOOT_STREAK.update({"key": None, "count": 0})
        return None
    cur_key = LOOT_PURSUIT["key"]
    if (cur_key and game_state.get("last_move_failed") and game_state.get("last_failed_dir") == "PATH_BLOCKED"
            and last_act and last_act.startswith("NAVIGATE_TO_CELL:")):
        LOOT_BLACKLIST[cur_key] = LOOT_TURN + LOOT_BLACKLIST_TURNS
        LOOT_PURSUIT.update({"key": None, "turns": 0})
    best = None
    for s in sources:
        key = (zone_id, s.get("tx"), s.get("ty"))
        if key in LOOT_BLACKLIST:
            continue
        rank = (s.get("dist", 999), 0 if s.get("kind") == "chest" else 1)
        if best is None or rank < best[0]:
            best = (rank, key, s)
    if best is None:
        LOOT_PURSUIT.update({"key": None, "turns": 0})
        return None
    _, key, s = best
    what = f"{s.get('kind', 'item')} '{s.get('name', '?')}'"
    if s.get("dist", 99) <= 1:
        if last_act == "LOOT" and LOOT_STREAK["key"] == key:
            LOOT_STREAK["count"] += 1
        else:
            LOOT_STREAK.update({"key": key, "count": 1})
        if LOOT_STREAK["count"] > LOOT_STREAK_MAX:
            LOOT_BLACKLIST[key] = LOOT_TURN + LOOT_BLACKLIST_TURNS
            LOOT_STREAK.update({"key": None, "count": 0})
            return None
        return {"action": "LOOT", "reason": f"Loot: taking from {what} right here"}
    if LOOT_PURSUIT["key"] == key:
        LOOT_PURSUIT["turns"] += 1
    else:
        LOOT_PURSUIT.update({"key": key, "turns": 1})
    if LOOT_PURSUIT["turns"] > LOOT_PURSUIT_MAX_TURNS:
        LOOT_BLACKLIST[key] = LOOT_TURN + LOOT_BLACKLIST_TURNS
        LOOT_PURSUIT.update({"key": None, "turns": 0})
        return None
    return {"action": f"NAVIGATE_TO_CELL:{s.get('tx')},{s.get('ty')}",
            "reason": f"Loot: walking to {what} ({s.get('dist')} tiles)"}


def note_loot(game_state):
    """Prints the engine's report of the last loot action once. Never raises."""
    try:
        ll = game_state.get("last_loot")
        if not ll or ll.get("seq", 0) <= LOOT_LAST_SEQ["seq"]:
            return
        LOOT_LAST_SEQ["seq"] = ll.get("seq", 0)
        left = f", left {ll.get('left')}" if ll.get("left") else ""
        print(f"[LOOT] {ll.get('kind')} '{ll.get('name')}': took {ll.get('count')}{left}")
    except Exception:
        pass


def is_ability_ready(ab):
    """Checks if an ability is enabled, usable, off cooldown, and has available charges (not '0 charges')."""
    if not ab or not ab.get("usable", True) or ab.get("cooldown", 0) > 0 or ab.get("active", False):
        return False
    name = ab.get("name", "").lower()
    # Check for depleted charges like 'Lase (0 charges)'
    if "0 charge" in name or "(0 charges)" in name:
        return False
    return True


def find_ready_ability(abilities, *families):
    """First enabled, usable, off-cooldown ability whose engine command is in one of the families (ability_registry).

    Exact command match; an ability in no wired family is never returned (HANDOFF issue 52)."""
    for ab in abilities:
        if is_ability_ready(ab) and ability_registry.in_family(ab, *families):
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


def is_line_of_fire_clear(from_pos, to_pos, companions=None, blocked_set=None, target_entity=None, surroundings=None):
    """
    Checks if a direct ray from from_pos to to_pos is unblocked.
    Returns (is_clear: bool, reason: str).
    - If target entity has has_los explicitly False, returns (False, "Target is occluded by walls (no line of sight)").
    - If target coordinate is itself a companion, returns (False, f"Target coordinate ({x1}, {y1}) IS friendly companion {comp_name}!").
    - If any companion's tile lies strictly between from_pos and to_pos,
      returns (False, f"Blocked by companion {comp_name} at {pt}").
    - If any known solid wall/obstacle lies strictly between from_pos and to_pos,
      returns (False, f"Blocked by obstacle at {pt}").
    - If surroundings 5x5 contains a solid wall/impassable obstacle intersecting the line,
      returns (False, f"Line of fire obstructed by solid wall at {pt}").
    """
    if target_entity is not None and target_entity.get("has_los") is False:
        return False, f"Target {target_entity.get('name', 'enemy')} is occluded by walls (no line of sight)"

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

    DELTA_TO_SURROUNDINGS = {
        (-1, -1): "NW", (0, -1): "N", (1, -1): "NE",
        (-1,  0): "W",                (1,  0): "E",
        (-1,  1): "SW", (0,  1): "S", (1,  1): "SE",
        (-2, -2): "NW2", (-1, -2): "NNW", (0, -2): "NN", (1, -2): "NNE", (2, -2): "NE2",
        (-2, -1): "WNW",                                                   (2, -1): "ENE",
        (-2,  0): "WW",                                                    (2,  0): "EE",
        (-2,  1): "WSW",                                                   (2,  1): "ESE",
        (-2,  2): "SW2", (-1,  2): "SSW", (0,  2): "SS", (1,  2): "SSE", (2,  2): "SE2",
    }

    for pt in intermediate:
        if pt in comp_map:
            return False, f"Line of fire obstructed by friendly companion {comp_map[pt]} at {pt}!"
        if blocked_set and pt in blocked_set:
            return False, f"Line of fire obstructed by obstacle at {pt}"
        if surroundings:
            d_pt = (pt[0] - x0, pt[1] - y0)
            if d_pt in DELTA_TO_SURROUNDINGS:
                k = DELTA_TO_SURROUNDINGS[d_pt]
                val = surroundings.get(k, "")
                if "[BLOCKED:" in val and not any(ok in val.lower() for ok in ["door", "openable", "companion", "pet"]):
                    return False, f"Line of fire obstructed by solid wall at {pt} ({k})"

    return True, "Clear"


def is_ignorable_stationary_enemy(e):
    """
    Determines if an enemy is a distant stationary trivial entity (e.g. glowpads, harmless fungi,
    distant roots/plants) that should not lock the AI into combat mode or interrupt autoexplore.
    """
    name = e.get("name", "").lower()
    dist = e.get("dist", 999)
    diff = e.get("difficulty", "")
    # "pad" must be a whole word: it is a substring of "spade" (Cherubic Spade, Metachrome Spade are hostile constructs, HANDOFF issue 60).
    name_words = set(re.findall(r"[a-z]+", name))
    is_stat = e.get("is_stationary", False) or any(k in name for k in [
        "glowpad", "plant", "fungus", "lichen", "brimestalk", "root", "vine", "seaweed", "lily"
    ]) or "pad" in name_words

    # If adjacent (dist <= 1), never ignore
    if dist <= 1:
        return False

    # Never ignore turrets or mechanical defense emplacements!
    if any(t in name for t in ["turret", "gun", "cannon", "rocket", "mortar", "idol", "statue"]):
        return False

    # Never ignore tough, very tough, or impossible hostiles!
    if diff in ("Tough", "Very Tough", "Impossible"):
        return False

    # A stationary creature (the engine says it cannot move, or it is a plant) only reaches adjacent cells, so beyond one tile it is not
    # a threat. The old limit of 3 let a wall-dwelling jilted lover at distance 3 lock the brain into combat for 100+ turns (HANDOFF issue 57).
    # Turrets and anything Tough or worse were already excluded above; damage taken still forces combat in the caller.
    if is_stat and dist > 1 and diff in ("Trivial", "Easy", "Average", ""):
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

    pos = game_state.get("pos")
    if pos and len(pos) >= 2:
        px, py = pos[0], pos[1]
    else:
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

    adj_threats = get_adjacent_threats(surroundings, companions=companions, cur_pos=(game_state.get("x", 0), game_state.get("y", 0)))
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
            if "sprint" not in combined and not ability_registry.is_wired(ab):
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
        raw_ents = game_state.get("visible_entities", [])
        has_companion = (
            game_state.get("has_companion", False)
            or bool(companions)
            or any(e.get("is_companion") for e in raw_ents)
        )
        if not has_companion:
            for ab in abilities:
                if is_ability_ready(ab) and ab.get("command"):
                    name = ab.get("name", "")
                    cmd = ab.get("command", "")
                    combined = f"{name} {cmd}".lower()
                    if "proselytize" in combined or "beguile" in combined:
                        for ent in raw_ents:
                            if ent.get("dist") == 1 and is_proselytizable(ent, companions=companions):
                                edir = ent.get("dir") or get_step_direction((px, py), (ent.get("tx", px), ent.get("ty", py)))
                                ename = ent.get("name", "Creature")
                                if edir:
                                    action_choices.append(f"USE_ABILITY:{cmd}:{edir} (RECRUIT PET: Proselytize adjacent {ename} {edir} to become your permanent combat companion & frontline tank!)")
                        # Only offer approach to recruit if healthy, facing a single manageable enemy at distance 2, not taking damage
                        is_safe_to_approach = (
                            not adj_threats
                            and not took_damage
                            and not is_bleeding
                            and (hp / max(1, max_hp) >= 0.70)
                            and len(enemies) <= 1
                        )
                        if is_safe_to_approach:
                            for ent in sorted([e for e in raw_ents if e.get("dist") == 2], key=lambda x: x.get("dist", 99)):
                                if is_proselytizable(ent, companions=companions):
                                    diff = ent.get("difficulty", "Average")
                                    if diff not in ("Tough", "Very Tough", "Impossible"):
                                        s_step = get_step_direction((px, py), (ent.get("tx", px), ent.get("ty", py)))
                                        if s_step and f"MOVE_{s_step}" in open_moves:
                                            ename = ent.get("name", "Creature")
                                            action_choices.append(f"MOVE_{s_step} (RECRUIT PET: Approach {ename} {s_step} to get adjacent and Proselytize into frontline combat tank!)")

        # Check line-of-fire from player to primary target
        c_lof_clear, c_lof_reason = is_line_of_fire_clear((px, py), (c_tx, c_ty), companions=companions, blocked_set=blocked_coords, target_entity=closest, surroundings=surroundings)

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
                if any(nc in combined for nc in NON_COMBAT_KEYWORDS) or "sprint" in combined or not ability_registry.is_wired(ab):
                    continue

                if any(ray in combined for ray in ["freezingray", "flamingray", "spitpoison", "cryokinesis", "pyrokinesis", "lase", "stunningforce", "stunning force", "syphonvim", "syphon vim", "sundermind", "sunder mind", "chainfire", "disarmingshot"]):
                    max_ab_range = 10
                    if "syphon" in combined:
                        max_ab_range = 4
                    elif "stunning" in combined:
                        max_ab_range = 8
                    elif "sunder" in combined:
                        max_ab_range = 12
                    elif "lase" in combined:
                        max_ab_range = 10
                    elif "chainfire" in combined or "disarmingshot" in combined:
                        max_ab_range = 8

                    if closest and c_dist <= max_ab_range and s_dir:
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
                        elif "flamingray" in combined or "flaming ray" in combined or "flame ray" in combined:
                            action_choices.append(f"USE_ABILITY:{cmd}:{s_dir} (Cast Flaming Ray thermal beam at {c_name} {s_dir} - HIGH THERMAL BURST)")
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
                if any(nc in combined for nc in NON_COMBAT_KEYWORDS) or "sprint" in combined or not ability_registry.is_wired(ab):
                    continue

                if any(mta in combined for mta in ["dismember", "cleave", "shieldslam", "slam", "swipe", "decapitate"]):
                    if adj_threats:
                        for d, ename in adj_threats.items():
                            action_choices.append(f"USE_ABILITY:{cmd}:{d} (Execute {name} on {ename} {d} - MELEE BURST & BLEED)")
                elif any(ray in combined for ray in ["flamingray", "flaming ray", "flame ray", "freezingray", "freezing ray"]):
                    if adj_threats:
                        for d, ename in adj_threats.items():
                            action_choices.append(f"USE_ABILITY:{cmd}:{d} (Point-blank {name} burst on {ename} {d} - HEAVY BURST)")
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
                if any(nc in combined for nc in NON_COMBAT_KEYWORDS) or "sprint" in combined or not ability_registry.is_wired(ab):
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
            elif closest:
                dx, dy = CARDINAL_OFFSETS.get(vdir, (0, 0))
                new_dist = max(abs((px + dx) - c_tx), abs((py + dy) - c_ty))
                if new_dist < c_dist:
                    if not c_lof_clear:
                        action_choices.append(f"{vm} (Tactical Maneuver {vdir} around corner to establish clear Line of Sight on {c_name})")
                    else:
                        action_choices.append(f"{vm} (Advance {vdir} towards {c_name} [dist {c_dist} -> {new_dist}])")
                elif new_dist > c_dist:
                    action_choices.append(f"{vm} (Backpedal/Reposition {vdir} away from {c_name} [dist {c_dist} -> {new_dist}])")
                else:
                    action_choices.append(f"{vm} (Flank {vdir} around {c_name})")
            elif not (has_mw and ammo > 0 and enemies):
                action_choices.append(f"{vm} (Maneuver {vdir})")
            else:
                action_choices.append(f"{vm} (Reposition {vdir})")

        # 7. STANDOFF & COOLDOWN RECHARGE (Casters / Ranged)
        has_ready_offensive = any(
            is_ability_ready(ab) and any(k in (f"{ab.get('name')} {ab.get('command')}").lower() for k in ["lase", "sunder", "ray", "stunning", "cryo", "pyro", "syphon"])
            for ab in abilities
        )
        if is_caster_or_ranged and enemies and not adj_threats:
            if not has_ready_offensive or (c_lof_clear and c_dist >= 4):
                action_choices.append("WAIT (Hold safe standoff distance & recharge Light Manipulation laser charges / mental cooldowns)")

        if is_caster_or_ranged and closest and c_dist <= 3 and open_moves:
            # Only kite backpedal if offensive abilities are depleted or low HP (< 50%)
            hp_ratio_val = hp / max(1, max_hp)
            if not has_ready_offensive or hp_ratio_val < 0.50:
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
            "whenever available. If Line of Sight is obstructed by a corner or corridor bend, MANEUVER around the corner to gain clear Line of Sight so you can blast the enemy with ranged powers or approach to Proselytize. "
            "Maneuvering to establish Line of Sight or approaching to recruit a pet is NOT charging into melee; it is required tactical positioning! "
            "Only when offensive abilities or laser charges are cooling down should you MAINTAIN SAFE DISTANCE (kiting backpedal or WAIT). "
            "NEVER voluntarily strike enemies with a frail wooden staff in melee! "
            "If an enemy breaches adjacent melee range, prioritize EMERGENCY DEFENSE (Teleport Other banish, Force Bubble barrier, Intimidate fear) "
            "or Sprinting/Retreating into open ground!"
        )
    else:
        rule2 = (
            "2. ATTACK PRIORITY: If an offensive action (Missile Snipe, Charge, Dismember, Cleave, or Melee Attack) is listed in VALID ACTIONS, "
            "YOU MUST ATTACK. Never waste a turn walking away when you can already strike or charge the enemy!"
        )

    pet_rule = (
        "0. PET RECRUITMENT OPPORTUNITY: If you have no active companion/pet and Proselytize is ready, you may Proselytize an adjacent beast or approach a lone manageable foe at distance 2 to recruit a frontline tank. "
        "HOWEVER, in dangerous combat (multiple enemies, taking damage, or facing tough foes), ELIMINATE THREATS WITH RANGED POWERS (Lase, Sunder Mind, Flaming Ray, Guns) FIRST. Never charge into danger to recruit!\n"
        if not has_companion else ""
    )

    system_prompt = (
        f"You are an expert tactical AI controlling a {class_name} ({archetype}) in Caves of Qud.\n"
        f"{ancestral_lore}\n\n"
        f"CLASS TACTICAL DOCTRINE ({doctrine_name.upper()} - Preferred Range: {pref_range} tiles):\n"
        f"{pet_rule}"
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
        res = requests.post(LM_STUDIO_URL, json=payload, timeout=LM_STUDIO_TIMEOUT)
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

            # LOF Safety Guardrail: Prevent friendly fire on companions and wall impacts if LLM generated a beam/missile attack
            companions = game_state.get("companions", [])
            if enemies:
                is_beam_or_missile = action.startswith("FIRE_MISSILE") or any(b in action.lower() for b in ["lase", "flaming", "freezing", "spit"])
                if is_beam_or_missile:
                    closest = enemies[0]
                    ctx = closest.get("tx", px)
                    cty = closest.get("ty", py)
                    clear, reason = is_line_of_fire_clear((px, py), (ctx, cty), companions=companions, blocked_set=blocked_coords, target_entity=closest, surroundings=surroundings)
                    if not clear:
                        ab_sunder = find_ready_ability(abilities, "sunder_mind")
                        s_dir = get_step_direction((px, py), (ctx, cty))
                        if ab_sunder and ab_sunder.get("command") and s_dir:
                            action = f"USE_ABILITY:{ab_sunder['command']}:{s_dir}"
                            thought = f"[LOF Safety Override] {reason}. Redirected to Sunder Mind."
                        else:
                            best_step = get_best_move_towards((px, py), (ctx, cty), valid_moves, surroundings)
                            if best_step:
                                action = best_step
                                thought = f"[LOF Safety Override] {reason}. Maneuvering {best_step[5:]} to establish line of sight."
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
    surroundings = game_state.get("surroundings", {})
    companions = game_state.get("companions", [])
    enemies = filter_hostile_enemies(enemies, companions)
    adj_threats = drop_companion_cells(adj_threats, cur_pos, companions)

    closest_enemy = enemies[0] if enemies else None
    closest_dist = closest_enemy.get("dist", 999) if closest_enemy else 999
    c_name = closest_enemy.get("name", "Enemy") if closest_enemy else ""
    c_tx = closest_enemy.get("tx", px) if closest_enemy else px
    c_ty = closest_enemy.get("ty", py) if closest_enemy else py

    raw_entities = game_state.get("visible_entities", [])
    has_companion = game_state.get("has_companion", False) or bool(companions) or any(e.get("is_companion") for e in raw_entities)
    # 0. Pet Recruitment: If without an active companion, proselytize adjacent beasts or humanoids
    if not has_companion:
        ab_proselytize = find_ready_ability(abilities, "proselytize")
        if ab_proselytize and ab_proselytize.get("command"):
            for ent in raw_entities:
                if ent.get("dist") == 1 and is_proselytizable(ent, companions=companions):
                    p_dir = ent.get("dir") or get_step_direction(cur_pos, (ent.get("tx", px), ent.get("ty", py)))
                    if p_dir:
                        p_name = ent.get("name", "Creature")
                        return {"action": f"USE_ABILITY:{ab_proselytize['command']}:{p_dir}", "reason": f"[{template['name']} Fallback] Proselytizing adjacent {p_name} ({p_dir}) into combat pet & frontline tank"}

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

        ab_strike = find_ready_ability(abilities, "melee_strike")
        if ab_strike and ab_strike.get("command"):
            cmd = ab_strike["command"]
            name = ab_strike.get("name", "Strike")
            return {"action": f"USE_ABILITY:{cmd}:{target_dir}", "reason": f"[{template['name']} Fallback] Executing {name} on adjacent {target_name} ({target_dir})"}

        # Point-blank elemental burst (Flaming Ray / Freezing Ray)
        ab_burst = find_ready_ability(abilities, "flaming_ray", "freezing_ray")
        if ab_burst and ab_burst.get("command"):
            return {"action": f"USE_ABILITY:{ab_burst['command']}:{target_dir}", "reason": f"[{template['name']} Fallback] Point-blank {ab_burst.get('name', 'Ray')} burst on {target_name} ({target_dir})"}

        # Basic melee bump-attack
        return {"action": f"MOVE_{target_dir}", "reason": f"[{template['name']} Fallback] Relentless melee strike on {target_name} ({target_dir})"}

    # 3. Gap Closer & Ray Fire: If enemy at distance 2-6, use Charge or fire Ray!
    if closest_enemy and 2 <= closest_dist <= 6:
        ab_charge = find_ready_ability(abilities, "melee_charge")
        s_dir = get_step_direction(cur_pos, (c_tx, c_ty))
        if closest_dist <= 4 and ab_charge and ab_charge.get("command"):
            cmd = ab_charge["command"]
            return {"action": f"USE_ABILITY:{cmd}:{s_dir}", "reason": f"[{template['name']} Fallback] Charging {c_name} ({s_dir}) to close gap and daze target"}

        # Secondary action bar ray fire (Freezing Ray / Flaming Ray) while closing distance
        ab_ray = find_ready_ability(abilities, "flaming_ray", "freezing_ray")
        if ab_ray and ab_ray.get("command") and s_dir:
            surroundings = game_state.get("surroundings", {})
            is_clear, _ = is_line_of_fire_clear((px, py), (c_tx, c_ty), companions=companions, blocked_set=blocked_coords, target_entity=closest_enemy, surroundings=surroundings)
            if is_clear:
                return {"action": f"USE_ABILITY:{ab_ray['command']}:{s_dir}", "reason": f"[{template['name']} Fallback] Blasting approaching {c_name} with {ab_ray.get('name', 'Ray')} ({s_dir})"}

        # Advance directly into melee
        step_move = f"MOVE_{s_dir}"
        if step_move in valid_moves:
            return {"action": step_move, "reason": f"[{template['name']} Fallback] Advancing into melee contact on {c_name} ({s_dir})"}

    # 4. Long-range approach or suppressive missile fire
    if closest_enemy:
        if closest_dist >= 6 and has_missile and ammo > 0:
            surroundings = game_state.get("surroundings", {})
            is_clear, _ = is_line_of_fire_clear((px, py), (c_tx, c_ty), companions=companions, blocked_set=blocked_coords, target_entity=closest_enemy, surroundings=surroundings)
            if is_clear:
                return {"action": f"FIRE_MISSILE@{c_tx},{c_ty}", "reason": f"[{template['name']} Fallback] Suppressive fire at {c_name} while closing distance"}
        s_dir = get_step_direction(cur_pos, (c_tx, c_ty))
        step_move = f"MOVE_{s_dir}"
        if step_move in valid_moves:
            return {"action": step_move, "reason": f"[{template['name']} Fallback] Pursuing {c_name} ({s_dir})"}
        elif valid_moves:
            best_adv = get_best_move_towards(cur_pos, (c_tx, c_ty), valid_moves, surroundings)
            if best_adv:
                return {"action": best_adv, "reason": f"[{template['name']} Fallback] Pursuing {c_name} ({best_adv[5:]})"}

    if valid_moves:
        ranked = sorted(valid_moves, key=lambda m: visit_counts[(cur_pos[0] + CARDINAL_OFFSETS[m[5:]][0], cur_pos[1] + CARDINAL_OFFSETS[m[5:]][1])])
        return {"action": ranked[0], "reason": f"[{template['name']} Fallback] Maneuvering into position"}

    return {"action": "WAIT", "reason": f"[{template['name']} Fallback] Holding ground"}


def fallback_esper(game_state, enemies, adj_threats, open_moves, valid_moves, abilities, template, cur_pos, px, py, hp, max_hp, can_sp, has_missile, ammo, max_ammo, inv_ammo):
    """Pure Mental Sorcerer Tactical Fallback (Esper Mindflayer)."""
    surroundings = game_state.get("surroundings", {})
    companions = game_state.get("companions", [])
    raw_entities = game_state.get("visible_entities", [])
    has_companion = game_state.get("has_companion", False) or bool(companions) or any(e.get("is_companion") for e in raw_entities)
    enemies = filter_hostile_enemies(enemies, companions)
    adj_threats = drop_companion_cells(adj_threats, cur_pos, companions)

    closest_enemy = enemies[0] if enemies else None
    closest_dist = closest_enemy.get("dist", 999) if closest_enemy else 999
    c_name = closest_enemy.get("name", "Enemy") if closest_enemy else ""
    c_tx = closest_enemy.get("tx", px) if closest_enemy else px
    c_ty = closest_enemy.get("ty", py) if closest_enemy else py
    s_dir = get_step_direction(cur_pos, (c_tx, c_ty)) if closest_enemy else ""
    is_stationary = any(st in c_name.lower() for st in ["glowpad", "plant", "turret", "fungus", "vine", "tree"])

    # 0. Pet Recruitment: If without an active companion, proselytize adjacent beasts or humanoids into combat thralls
    if not has_companion:
        ab_proselytize = find_ready_ability(abilities, "proselytize")
        if ab_proselytize and ab_proselytize.get("command"):
            # A. Adjacent candidate recruitment (dist == 1)
            for ent in raw_entities:
                if ent.get("dist") == 1 and is_proselytizable(ent, companions=companions):
                    p_dir = ent.get("dir") or get_step_direction(cur_pos, (ent.get("tx", px), ent.get("ty", py)))
                    if p_dir:
                        p_name = ent.get("name", "Creature")
                        return {"action": f"USE_ABILITY:{ab_proselytize['command']}:{p_dir}", "reason": f"[{template['name']} Fallback] Proselytizing adjacent {p_name} ({p_dir}) into combat pet & frontline tank"}

            # B. Candidate recruitment approach (dist == 2 ONLY): ONLY when healthy, facing a single manageable target, and not taking damage!
            is_safe_to_approach = (
                not adj_threats
                and not game_state.get("took_damage", False)
                and (hp / max(1, max_hp) >= 0.70)
                and len(enemies) <= 1
            )
            if is_safe_to_approach:
                for ent in sorted([e for e in raw_entities if e.get("dist") == 2], key=lambda x: x.get("dist", 99)):
                    if is_proselytizable(ent, companions=companions):
                        diff = ent.get("difficulty", "Average")
                        if diff not in ("Tough", "Very Tough", "Impossible"):
                            s_step = get_step_direction(cur_pos, (ent.get("tx", px), ent.get("ty", py)))
                            if s_step and f"MOVE_{s_step}" in open_moves:
                                p_name = ent.get("name", "Creature")
                                return {"action": f"MOVE_{s_step}", "reason": f"[{template['name']} Fallback] Approaching {p_name} ({s_step}) to recruit into combat pet & frontline tank"}

    # 1. Close-Contact Emergency: Defensive Mental Shielding, Banishment & Evasion
    if adj_threats:
        ab_bubble = find_ready_ability(abilities, "force_shield")
        if ab_bubble and ab_bubble.get("command"):
            return {"action": f"USE_ABILITY:{ab_bubble['command']}", "reason": f"[{template['name']} Fallback] Popping Force Bubble impenetrable barrier against close hostiles"}

        ab_banish = find_ready_ability(abilities, "teleport_other")
        if ab_banish and ab_banish.get("command"):
            t_dir = list(adj_threats.keys())[0]
            t_name = adj_threats[t_dir]
            return {"action": f"USE_ABILITY:{ab_banish['command']}:{t_dir}", "reason": f"[{template['name']} Fallback] Banishing adjacent hostile {t_name} with Teleport Other ({t_dir})"}

        ab_intimidate = find_ready_ability(abilities, "intimidate")
        if ab_intimidate and ab_intimidate.get("command"):
            return {"action": f"USE_ABILITY:{ab_intimidate['command']}", "reason": f"[{template['name']} Fallback] Terrifying close hostile with Intimidate"}

        ab_teleport = find_ready_ability(abilities, "phase_escape")
        if ab_teleport and ab_teleport.get("command"):
            return {"action": f"USE_ABILITY:{ab_teleport['command']}", "reason": f"[{template['name']} Fallback] Teleporting away from close hostiles"}

        if open_moves:
            r_dir = open_moves[0][5:]
            if can_sp:
                return {"action": f"SPRINT_{r_dir}", "reason": f"[{template['name']} Fallback] Sprint kiting away from fragile melee engagement"}
            return {"action": open_moves[0], "reason": f"[{template['name']} Fallback] Backpedaling away from melee threat"}

    # 2. Long-Range Psychic Assault (Distance >= 1)
    if closest_enemy and closest_dist >= 1:
        surroundings = game_state.get("surroundings", {})
        c_has_los = closest_enemy.get("has_los", True) is not False
        # Check line-of-fire from player to primary target (checking companions, bumps, and 5x5 wall terrain)
        c_lof_clear, c_lof_reason = is_line_of_fire_clear((px, py), (c_tx, c_ty), companions=companions, blocked_set=blocked_coords, target_entity=closest_enemy, surroundings=surroundings)

        # A. Sunder Mind (Uncapped psychic annihilation - max range 12, DIRECT MENTAL, 100% SAFE OVER PETS & WALLS!)
        ab_sunder = find_ready_ability(abilities, "sunder_mind")
        if ab_sunder and ab_sunder.get("command") and closest_dist <= 12 and s_dir:
            return {"action": f"USE_ABILITY:{ab_sunder['command']}:{s_dir}", "reason": f"[{template['name']} Fallback] Channeling Sunder Mind against {c_name} (dist: {closest_dist})"}

        # B. Opener CC: Stunning Force on approaching mobile enemies (dist 3-8, requires clear LOF and LOS)
        ab_stun = find_ready_ability(abilities, "stunning_force")
        if ab_stun and ab_stun.get("command") and 3 <= closest_dist <= 8 and not is_stationary and s_dir and c_lof_clear and c_has_los:
            return {"action": f"USE_ABILITY:{ab_stun['command']}:{s_dir}", "reason": f"[{template['name']} Fallback] Blasting approaching {c_name} with Stunning Force CC opener ({s_dir})"}

        # C. Lase (Light Manipulation focused laser beam - max range 10, requires clear LOF and LOS past companions and walls)
        ab_lase = find_ready_ability(abilities, "lase")
        if ab_lase and ab_lase.get("command") and closest_dist <= 10 and s_dir and c_lof_clear and c_has_los:
            return {"action": f"USE_ABILITY:{ab_lase['command']}:{s_dir}", "reason": f"[{template['name']} Fallback] Firing Lase light beam at {c_name} ({s_dir}, dist: {closest_dist})"}

        # D. Cryokinesis / Pyrokinesis / Ray / Elemental / Gas attacks (max range 10, requires clear LOF and LOS)
        ab_elemental = find_ready_ability(abilities, "elemental_ray")
        if ab_elemental and ab_elemental.get("command") and closest_dist <= 10 and s_dir and c_lof_clear and c_has_los:
            return {"action": f"USE_ABILITY:{ab_elemental['command']}:{s_dir}", "reason": f"[{template['name']} Fallback] Manifesting {ab_elemental.get('name')} at {c_name} ({s_dir})"}

        # E. Stunning Force (Secondary / Stationary / Close Finisher - dist <= 8, requires clear LOF and LOS)
        if ab_stun and ab_stun.get("command") and closest_dist <= 8 and s_dir and c_lof_clear and c_has_los:
            return {"action": f"USE_ABILITY:{ab_stun['command']}:{s_dir}", "reason": f"[{template['name']} Fallback] Blasting {c_name} with Stunning Force ({s_dir})"}

        # F. Syphon Vim (Life drain if within 4 tiles, requires clear LOS)
        ab_syphon = find_ready_ability(abilities, "syphon_vim")
        if ab_syphon and ab_syphon.get("command") and closest_dist <= 4 and s_dir and c_has_los:
            return {"action": f"USE_ABILITY:{ab_syphon['command']}:{s_dir}", "reason": f"[{template['name']} Fallback] Draining life force from {c_name} ({s_dir})"}

        # G. Equipped missile weapon fire (requires clear LOF and LOS)
        if has_missile and ammo > 0 and not adj_threats and c_lof_clear and c_has_los:
            return {"action": f"FIRE_MISSILE@{c_tx},{c_ty}", "reason": f"[{template['name']} Fallback] Firing ranged weapon at {c_name} while mental cooldowns reset"}

        # H. Friendly-fire / wall occlusion evasion: If primary target line of fire is blocked, redirect to unblocked target!
        if not c_lof_clear or not c_has_los:
            for alt in enemies[1:]:
                alt_tx = alt.get("tx", px)
                alt_ty = alt.get("ty", py)
                alt_has_los = alt.get("has_los", True) is not False
                alt_clear, _ = is_line_of_fire_clear((px, py), (alt_tx, alt_ty), companions=companions, blocked_set=blocked_coords, target_entity=alt, surroundings=surroundings)
                if alt_clear and alt_has_los:
                    alt_dir = get_step_direction(cur_pos, (alt_tx, alt_ty))
                    if ab_lase and ab_lase.get("command") and alt_dir:
                        return {"action": f"USE_ABILITY:{ab_lase['command']}:{alt_dir}", "reason": f"[{template['name']} Fallback] Obstacle protection: redirecting Lase to unblocked {alt.get('name')} ({alt_dir})"}
                    if has_missile and ammo > 0:
                        return {"action": f"FIRE_MISSILE@{alt_tx},{alt_ty}", "reason": f"[{template['name']} Fallback] Obstacle protection: redirecting missile to unblocked {alt.get('name')}"}

            # If primary target is occluded by a wall or corner, maneuver along corridor to establish line of sight instead of waiting or fleeing!
            best_step = get_best_move_towards(cur_pos, (c_tx, c_ty), valid_moves, surroundings)
            if best_step:
                return {"action": best_step, "reason": f"[{template['name']} Fallback] Maneuvering {best_step[5:]} around corridor/wall to establish line of sight on {c_name}"}

            # If all targets blocked, reposition sideways to get an open firing line!
            if open_moves:
                return {"action": open_moves[0], "reason": f"[{template['name']} Fallback] Repositioning {open_moves[0][5:]} to clear line of fire past companion"}

        # I. Standoff Kiting: if enemy is closer than preferred distance (dist < 4) and open_moves exist, step back
        if closest_dist < 4 and open_moves:
            kites = [m for m in open_moves if max(abs(px + CARDINAL_OFFSETS[m[5:]][0] - c_tx), abs(py + CARDINAL_OFFSETS[m[5:]][1] - c_ty)) > closest_dist]
            if kites:
                return {"action": kites[0], "reason": f"[{template['name']} Fallback] Preserving safe standoff distance (dist {closest_dist} -> {kites[0][5:]})"}

        # J. Standoff & Recharge: When all ranged powers / laser charges are cooling down and distance is 2-8 tiles with clear LOS:
        # HOLD GROUND and WAIT! Let ambient light recharge Lase charges and mental cooldowns tick down!
        if closest_dist <= 8 and c_has_los:
            return {"action": "WAIT", "reason": f"[{template['name']} Fallback] Holding safe standoff distance ({closest_dist} tiles) & recharging laser charges/mental cooldowns to finish {c_name}"}

        # K. If enemy is distant (dist > 8) or occluded, close the gap to bring into psychic range
        if closest_dist > 8 or not c_has_los:
            step_move = f"MOVE_{s_dir}"
            if step_move in valid_moves:
                return {"action": step_move, "reason": f"[{template['name']} Fallback] Advancing to psychic engagement range on {c_name} ({s_dir})"}
            elif valid_moves:
                best_adv = get_best_move_towards(cur_pos, (c_tx, c_ty), valid_moves, surroundings)
                if best_adv:
                    return {"action": best_adv, "reason": f"[{template['name']} Fallback] Navigating towards {c_name} ({best_adv[5:]})"}
            elif valid_moves:
                best_adv = get_best_move_towards(cur_pos, (c_tx, c_ty), valid_moves, surroundings)
                if best_adv:
                    return {"action": best_adv, "reason": f"[{template['name']} Fallback] Navigating {best_adv[5:]} towards {c_name} (dist: {closest_dist})"}

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
    surroundings = game_state.get("surroundings", {})
    companions = game_state.get("companions", [])
    enemies = filter_hostile_enemies(enemies, companions)
    adj_threats = drop_companion_cells(adj_threats, cur_pos, companions)

    closest_enemy = enemies[0] if enemies else None
    closest_dist = closest_enemy.get("dist", 999) if closest_enemy else 999
    c_name = closest_enemy.get("name", "Enemy") if closest_enemy else ""
    c_tx = closest_enemy.get("tx", px) if closest_enemy else px
    c_ty = closest_enemy.get("ty", py) if closest_enemy else py

    raw_entities = game_state.get("visible_entities", [])
    has_companion = game_state.get("has_companion", False) or bool(companions) or any(e.get("is_companion") for e in raw_entities)
    # 0. Pet Recruitment: If without an active companion, proselytize adjacent beasts or humanoids
    if not has_companion:
        ab_proselytize = find_ready_ability(abilities, "proselytize")
        if ab_proselytize and ab_proselytize.get("command"):
            for ent in raw_entities:
                if ent.get("dist") == 1 and is_proselytizable(ent, companions=companions):
                    p_dir = ent.get("dir") or get_step_direction(cur_pos, (ent.get("tx", px), ent.get("ty", py)))
                    if p_dir:
                        p_name = ent.get("name", "Creature")
                        return {"action": f"USE_ABILITY:{ab_proselytize['command']}:{p_dir}", "reason": f"[{template['name']} Fallback] Proselytizing adjacent {p_name} ({p_dir}) into combat pet & frontline tank"}

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

        ab_disarm = find_ready_ability(abilities, "disarming_shot")
        if ab_disarm and ab_disarm.get("command"):
            return {"action": f"USE_ABILITY:{ab_disarm['command']}:{target_dir}", "reason": f"[{template['name']} Fallback] Disarming shot on adjacent {target_name} ({target_dir})"}

        if open_moves and ammo > 0:
            return {"action": open_moves[0], "reason": f"[{template['name']} Fallback] Stepping {open_moves[0][5:]} to point pistols at {target_name}"}

        if has_missile and ammo > 0:
            return {"action": f"FIRE_MISSILE@{px + CARDINAL_OFFSETS[target_dir][0]},{py + CARDINAL_OFFSETS[target_dir][1]}", "reason": f"[{template['name']} Fallback] Point-blank pistol blast at {target_name}"}

        ab_burst = find_ready_ability(abilities, "flaming_ray", "freezing_ray")
        if ab_burst and ab_burst.get("command"):
            return {"action": f"USE_ABILITY:{ab_burst['command']}:{target_dir}", "reason": f"[{template['name']} Fallback] Point-blank {ab_burst.get('name', 'Ray')} burst on {target_name} ({target_dir})"}

        return {"action": f"MOVE_{target_dir}", "reason": f"[{template['name']} Fallback] Striking {target_name} in melee"}

    # 3. Chain Fire / Rapid Pistol Volley / Ray Beams (Distance 2 to 8)
    if closest_enemy and 2 <= closest_dist <= 8:
        ab_chain = find_ready_ability(abilities, "chain_fire")
        if ab_chain and ab_chain.get("command") and ammo >= 3:
            return {"action": f"USE_ABILITY:{ab_chain['command']}", "reason": f"[{template['name']} Fallback] Unleashing Chain Fire pistol volley at {c_name} (dist: {closest_dist})"}

        # Secondary action bar ray attack (Freezing Ray / Flaming Ray)
        ab_ray = find_ready_ability(abilities, "flaming_ray", "freezing_ray")
        if ab_ray and ab_ray.get("command") and (ammo <= 0 or closest_dist <= 5):
            s_dir = get_step_direction(cur_pos, (c_tx, c_ty))
            surroundings = game_state.get("surroundings", {})
            is_clear, _ = is_line_of_fire_clear((px, py), (c_tx, c_ty), companions=companions, blocked_set=blocked_coords, target_entity=closest_enemy, surroundings=surroundings)
            if is_clear and s_dir:
                return {"action": f"USE_ABILITY:{ab_ray['command']}:{s_dir}", "reason": f"[{template['name']} Fallback] Blasting {c_name} with {ab_ray.get('name', 'Ray')} ({s_dir})"}

        if has_missile and ammo > 0:
            companions = game_state.get("companions", [])
            surroundings = game_state.get("surroundings", {})
            is_clear, _ = is_line_of_fire_clear((px, py), (c_tx, c_ty), companions=companions, blocked_set=blocked_coords, target_entity=closest_enemy, surroundings=surroundings)
            if is_clear:
                return {"action": f"FIRE_MISSILE@{c_tx},{c_ty}", "reason": f"[{template['name']} Fallback] Firing dual pistols at {c_name} (dist: {closest_dist})"}
            else:
                for alt in enemies[1:]:
                    alt_tx = alt.get("tx", px)
                    alt_ty = alt.get("ty", py)
                    alt_clear, _ = is_line_of_fire_clear((px, py), (alt_tx, alt_ty), companions=companions, blocked_set=blocked_coords, target_entity=alt, surroundings=surroundings)
                    if alt_clear:
                        return {"action": f"FIRE_MISSILE@{alt_tx},{alt_ty}", "reason": f"[{template['name']} Fallback] Redirecting pistols to unblocked {alt.get('name')} to protect companion/clear LOS"}
                if open_moves:
                    return {"action": open_moves[0], "reason": f"[{template['name']} Fallback] Repositioning {open_moves[0][5:]} for clear firing line past obstacle"}

        if has_missile and ammo <= 0 and inv_ammo > 0 and closest_dist >= 2:
            return {"action": "RELOAD", "reason": f"[{template['name']} Fallback] Fast pistol reload (empty 0/{max_ammo})"}

    # 4. Advance or reposition
    if closest_enemy and closest_dist > 8:
        s_dir = get_step_direction(cur_pos, (c_tx, c_ty))
        step_move = f"MOVE_{s_dir}"
        if step_move in valid_moves:
            return {"action": step_move, "reason": f"[{template['name']} Fallback] Closing to pistol range on {c_name} ({s_dir})"}
        elif valid_moves:
            best_adv = get_best_move_towards(cur_pos, (c_tx, c_ty), valid_moves, surroundings)
            if best_adv:
                return {"action": best_adv, "reason": f"[{template['name']} Fallback] Navigating {best_adv[5:]} towards {c_name} (dist: {closest_dist})"}

    if valid_moves:
        ranked = sorted(valid_moves, key=lambda m: visit_counts[(cur_pos[0] + CARDINAL_OFFSETS[m[5:]][0], cur_pos[1] + CARDINAL_OFFSETS[m[5:]][1])])
        return {"action": ranked[0], "reason": f"[{template['name']} Fallback] Maneuver"}

    return {"action": "WAIT", "reason": f"[{template['name']} Fallback] Readying weapons"}


def fallback_nomad(game_state, enemies, adj_threats, open_moves, valid_moves, abilities, template, cur_pos, px, py, hp, max_hp, can_sp, has_missile, ammo, max_ammo, inv_ammo, is_sprinting):
    """Ranged Sniper & Kite Specialist Fallback (Rifle Nomad)."""
    surroundings = game_state.get("surroundings", {})
    companions = game_state.get("companions", [])
    enemies = filter_hostile_enemies(enemies, companions)
    adj_threats = drop_companion_cells(adj_threats, cur_pos, companions)

    closest_enemy = enemies[0] if enemies else None
    closest_dist = closest_enemy.get("dist", 999) if closest_enemy else 999
    c_name = closest_enemy.get("name", "Enemy") if closest_enemy else ""
    c_tx = closest_enemy.get("tx", px) if closest_enemy else px
    c_ty = closest_enemy.get("ty", py) if closest_enemy else py

    raw_entities = game_state.get("visible_entities", [])
    has_companion = game_state.get("has_companion", False) or bool(companions) or any(e.get("is_companion") for e in raw_entities)
    # 0. Pet Recruitment: If without an active companion, proselytize adjacent beasts or humanoids
    if not has_companion:
        ab_proselytize = find_ready_ability(abilities, "proselytize")
        if ab_proselytize and ab_proselytize.get("command"):
            for ent in raw_entities:
                if ent.get("dist") == 1 and is_proselytizable(ent, companions=companions):
                    p_dir = ent.get("dir") or get_step_direction(cur_pos, (ent.get("tx", px), ent.get("ty", py)))
                    if p_dir:
                        p_name = ent.get("name", "Creature")
                        return {"action": f"USE_ABILITY:{ab_proselytize['command']}:{p_dir}", "reason": f"[{template['name']} Fallback] Proselytizing adjacent {p_name} ({p_dir}) into combat pet & frontline tank"}

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

    # 3. Crowd Control & Thermal Ray Sniping: Freezing Ray or Flaming Ray on incoming pursuers (distance 2-6)
    if closest_enemy and 2 <= closest_dist <= 6:
        ab_freeze = find_ready_ability(abilities, "freezing_ray")
        ab_flame = find_ready_ability(abilities, "flaming_ray")
        ray_ab = ab_freeze or ab_flame
        if ray_ab and ray_ab.get("command"):
            s_dir = get_step_direction(cur_pos, (c_tx, c_ty))
            companions = game_state.get("companions", [])
            surroundings = game_state.get("surroundings", {})
            is_clear, _ = is_line_of_fire_clear((px, py), (c_tx, c_ty), companions=companions, blocked_set=blocked_coords, target_entity=closest_enemy, surroundings=surroundings)
            if is_clear and s_dir:
                ab_name = ray_ab.get("name", "Ray")
                action_verb = "Freezing" if ray_ab == ab_freeze else "Incinerating"
                return {"action": f"USE_ABILITY:{ray_ab['command']}:{s_dir}", "reason": f"[{template['name']} Fallback] {action_verb} {c_name} with {ab_name} ({s_dir})"}

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
        # Point-blank burst (Flaming Ray / Freezing Ray)
        ab_burst = find_ready_ability(abilities, "flaming_ray", "freezing_ray")
        if ab_burst and ab_burst.get("command"):
            return {"action": f"USE_ABILITY:{ab_burst['command']}:{d}", "reason": f"[{template['name']} Fallback] Point-blank {ab_burst.get('name', 'Ray')} burst on {ename} ({d})"}
        return {"action": f"MOVE_{d}", "reason": f"[{template['name']} Fallback] Striking adjacent threat {ename} ({d})"}

    # 8. Advance to melee / target if no ammo available
    if closest_enemy:
        s_dir = get_step_direction(cur_pos, (c_tx, c_ty))
        step_move = f"MOVE_{s_dir}"
        if step_move in valid_moves:
            return {"action": step_move, "reason": f"[{template['name']} Fallback] Closing in on {c_name} ({s_dir})"}
        elif valid_moves:
            best_adv = get_best_move_towards(cur_pos, (c_tx, c_ty), valid_moves, surroundings)
            if best_adv:
                return {"action": best_adv, "reason": f"[{template['name']} Fallback] Closing in on {c_name} ({best_adv[5:]})"}

    if valid_moves:
        ranked = sorted(valid_moves, key=lambda m: visit_counts[(cur_pos[0] + CARDINAL_OFFSETS[m[5:]][0], cur_pos[1] + CARDINAL_OFFSETS[m[5:]][1])])
        return {"action": ranked[0], "reason": f"[{template['name']} Fallback] Maneuver"}

    return {"action": "WAIT", "reason": f"[{template['name']} Fallback] Wait"}


def get_close_threats(enemies, game_state):
    """Enemies near enough to force combat mode.

    A non-adjacent enemy the engine reports as having no line of sight (`has_los` is False, e.g. behind a wall or across
    water) is not a threat yet: chasing line of sight to it kept the agent oscillating in a lake (2026-10-04, HANDOFF
    issue 28). Adjacent enemies, damage taken (`took_damage` is handled by the caller) and enemies that regain line of
    sight still force combat."""
    hostiles_nearby = game_state.get("hostiles_nearby", False)
    return [
        e for e in enemies
        if not is_ignorable_stationary_enemy(e)
        and not (e.get("has_los") is False and e.get("dist", 999) >= 2)
        and (e.get("dist", 999) <= 6 or (e.get("dist", 999) <= 10 and hostiles_nearby))
    ]


# Stand and fight (HANDOFF issue 58, human decision 2026-10-06, option A). Running from an adjacent same-speed melee attacker costs HP and gains
# nothing: Gen 14 "emergency retreated" for 15 turns from a snapjaw (HP 28 to 10) without ever striking back. When the adjacent hostiles are all
# below Tough and no stairs are close, a flee action is replaced by an attack: Stunning Force, then Lase and the other ready offensive abilities,
# then a melee bump. Tough or worse, or stairs within STAND_STAIRS_RADIUS, keep the old freedom to run.
STAND_STAIRS_RADIUS = 4
STAND_CONTEXT = {"adj_threats": {}, "enemies": [], "abilities": []}
STAND_FIGHT_FAMILIES = ("stunning_force", "sunder_mind", "lase", "elemental_ray", "syphon_vim", "melee_strike")
STAND_FLEE_PREFIXES = ("SPRINT_", "NAVIGATE_", "USE_STAIRS")


def must_stand_and_fight(game_state, adj_threats, enemies):
    """(True, [adjacent enemy dicts]) when fleeing is forbidden this turn."""
    if not adj_threats:
        return False, []
    adj_enemies = [e for e in enemies if e.get("dist") == 1 and e.get("dir") in adj_threats]
    if not adj_enemies or any(e.get("difficulty") in ("Tough", "Very Tough", "Impossible") for e in adj_enemies):
        return False, []
    if game_state.get("standing_on_stairs_up") or game_state.get("standing_on_stairs_down"):
        return False, []
    px, py = game_state.get("x", 0), game_state.get("y", 0)
    stairs = list(game_state.get("stairs_up", []) or []) + list(game_state.get("stairs_down", []) or [])
    for rec in list(KNOWN_STAIRS_UP.values()) + list(KNOWN_STAIRS_DOWN.values()):
        stairs.append(rec)
    for s in stairs:
        if "tx" in s and "ty" in s and max(abs(s["tx"] - px), abs(s["ty"] - py)) <= STAND_STAIRS_RADIUS:
            return False, []
    return True, adj_enemies


def enforce_stand_and_fight(decision, game_state, adj_threats, enemies, abilities):
    """Replaces a flee decision by an attack when `must_stand_and_fight`. Other decisions pass through unchanged."""
    action = (decision or {}).get("action", "")
    if (decision or {}).get("flee_ok"):
        return decision
    stand, adj_enemies = must_stand_and_fight(game_state, adj_threats, enemies)
    if not stand:
        return decision
    adj_dirs = {e.get("dir") for e in adj_enemies}
    flee = (action.startswith(STAND_FLEE_PREFIXES) or action == "ACTIVATE_SPRINT"
            or (action.startswith("MOVE_") and action[5:] not in adj_dirs))
    if not flee:
        return decision
    target = adj_enemies[0]
    d = target.get("dir")
    ab = find_ready_ability(abilities, *STAND_FIGHT_FAMILIES)
    if ab and ab.get("command"):
        new = {"action": f"USE_ABILITY:{ab['command']}:{d}", "reason": f"Stand and fight: {ab.get('name', 'ability')} on adjacent {target.get('name', 'enemy')} ({d}) instead of fleeing ({target.get('difficulty', '?')} threat, no stairs close)"}
    else:
        new = {"action": f"MOVE_{d}", "reason": f"Stand and fight: melee on adjacent {target.get('name', 'enemy')} ({d}) instead of fleeing ({target.get('difficulty', '?')} threat, no stairs close)"}
    print(f"[STAND AND FIGHT] {action} -> {new['action']} ({decision.get('reason', '')[:60]})")
    return new


def query_decision(game_state, took_damage, enemies, suppress_autolevel=False):
    """The decision for this turn: `_query_decision` plus the stand-and-fight rule."""
    STAND_CONTEXT.update({"adj_threats": {}, "enemies": [], "abilities": []})
    decision = _query_decision(game_state, took_damage, enemies, suppress_autolevel)
    return enforce_stand_and_fight(decision, game_state, STAND_CONTEXT["adj_threats"], STAND_CONTEXT["enemies"], STAND_CONTEXT["abilities"])


def _query_decision(game_state, took_damage, enemies, suppress_autolevel=False):
    global last_action, consecutive_kites, RETREAT_TARGET_LEVEL, CURRENT_ZONE_CHOSEN_EXIT, CURRENT_ZONE_CHOSEN_EXIT_ZONE, FAILED_ZONE_EXITS, TURN_CLOCK
    TURN_CLOCK += 1

    update_zone_records(game_state)
    update_stair_records(game_state)

    # Self-heal: a successful autoexplore step with the engine not reporting "stuck" proves this zone is still explorable.
    _zid_now = game_state.get("zone_id", "")
    if _zid_now:
        ENGINE_EXPLORED_LAST[_zid_now] = engine_confirms_explored(game_state)
        if ENGINE_EXPLORED_LAST[_zid_now]:
            EXPLORED_ZONE_SET.add(_zid_now)   # only the engine's own report is remembered across transitions
        if (last_action == "AUTOEXPLORE" and not game_state.get("last_move_failed", False)
                and not game_state.get("autoexplore_stuck", False)):
            stuck_autoexplore_zones.discard(_zid_now)
            if not game_state.get("zone_fully_explored", False) and (game_state.get("unexplored_cells", 0) or 0) > 35:
                EXPLORED_ZONE_SET.discard(_zid_now)

    if game_state.get("autoexplore_stuck", False) or (last_action == "AUTOEXPLORE" and game_state.get("last_move_failed", False)):
        zid = game_state.get("zone_id", "")
        if zid:
            stuck_autoexplore_zones.add(zid)
        if CURRENT_TRACKED_ZONE:
            stuck_autoexplore_zones.add(CURRENT_TRACKED_ZONE)

    template = build_templates.detect_build(game_state)
    # Publish this build's mutation ranking for the mod's picker (rewritten only when the detected build changes).
    mutation_policy.publish_mutation_ranking(template, os.path.join(EXCHANGE_DIR, "mutation_ranking.txt"))

    surroundings = game_state.get("surroundings", {})
    has_missile = game_state.get("has_missile_weapon", False)
    ammo = game_state.get("missile_ammo", 0)
    max_ammo = game_state.get("missile_max_ammo", 0)
    inv_ammo = game_state.get("inventory_ammo", 0)
    hp = game_state.get("hp", 0)
    max_hp = game_state.get("max_hp", 1)
    hp_ratio = hp / max(1, max_hp)
    px = game_state.get("x", 0)
    py = game_state.get("y", 0)
    cur_pos = (px, py)
    zone_id = game_state.get("zone_id", "")
    cur_z = game_state.get("z", 10)
    cur_lvl = game_state.get("level", 1)
    abilities = game_state.get("abilities", [])
    companions = game_state.get("companions", [])
    is_town = is_town_zone(game_state)

    enemies = filter_hostile_enemies(enemies, companions)
    # Experience across characters (danger_ledger.py, HANDOFF issue 64): a creature that has hit hard relative to this character's HP is rated higher.
    enemies = danger_ledger.apply(enemies, game_state.get("max_hp"))
    adj_threats = get_adjacent_threats(surroundings, companions=companions, cur_pos=(game_state.get("x", 0), game_state.get("y", 0)))
    close_threats = get_close_threats(enemies, game_state)
    abilities = filter_corpse_burners(game_state, abilities, enemies, hp_ratio)
    STAND_CONTEXT.update({"adj_threats": dict(adj_threats), "enemies": enemies, "abilities": abilities})
    engine_hostiles = (game_state.get("hostiles_adjacent", False) and bool(adj_threats)) or (game_state.get("hostiles_nearby", False) and bool(close_threats))
    is_in_combat = took_damage or bool(adj_threats) or bool(close_threats) or engine_hostiles

    last_failed = None
    if game_state.get("last_move_failed"):
        f_dir = game_state.get("last_failed_dir", "")
        if f_dir == "PATH_BLOCKED":
            if last_action and last_action.startswith("NAVIGATE_TO_CELL:"):
                try:
                    coords = last_action.split(":")[1].split(",")
                    blocked_target = (int(coords[0]), int(coords[1]))
                    UNREACHABLE_SECTORS.add((zone_id, blocked_target))
                    print(f"[PATHFINDER BLOCKED]: Target {blocked_target} in zone {zone_id} is unreachable. Blacklisting.")
                except Exception:
                    pass
        elif f_dir:
            last_failed = f"MOVE_{f_dir}"
            fdx, fdy = CARDINAL_OFFSETS.get(f_dir, (0, 0))
            if (fdx, fdy) != (0, 0):
                blocked_coords.add((px + fdx, py + fdy))

    valid_moves = get_valid_moves(surroundings, cur_pos, last_failed, is_in_combat=is_in_combat)

    # Detect whether character is standing directly on stairs
    standing_on_sd = game_state.get("standing_on_stairs_down", False)
    standing_on_su = game_state.get("standing_on_stairs_up", False)
    center_tile = surroundings.get("CENTER", "").lower()
    if not standing_on_sd and ("stairs_down" in center_tile or "[stairs_down" in center_tile or ("stair" in center_tile and "down" in center_tile)):
        standing_on_sd = True
    if not standing_on_su and ("stairs_up" in center_tile or "[stairs_up" in center_tile or ("stair" in center_tile and "up" in center_tile)):
        standing_on_su = True

    fire_decision = fire_reaction(game_state, surroundings, valid_moves)
    if fire_decision:
        return fire_decision

    # ==========================================================
    # EMERGENCY TACTICAL RETREAT TO STAIRS UP (Underground Defense)
    # ==========================================================
    # Trigger when overwhelmed underground (z > 10): critical HP (< 35%), heavy damage (< 45%), or impossible hostiles
    is_overwhelmed = (cur_z > 10) and (
        (hp_ratio < 0.35) or
        (took_damage and hp_ratio < 0.45) or
        any(e.get("difficulty") == "Impossible" for e in enemies)
    )

    if is_overwhelmed:
        if standing_on_su:
            RETREAT_TARGET_LEVEL = cur_lvl + 1
            return {"action": "USE_STAIRS_UP", "reason": f"Tactical Retreat: Ascending stairs up to stratum {cur_z - 1} to escape lethal danger! (HP {hp}/{max_hp}, Target Level: {RETREAT_TARGET_LEVEL})"}

        su_info = KNOWN_STAIRS_UP.get(zone_id)
        if su_info:
            su_pos = (su_info["tx"], su_info["ty"])
            # Engine pathfinder first; the greedy step is only a guarded fallback (R6). A wall between him and the stairs made the greedy
            # retreat flip E/W for 20 turns while a snapjaw hunter killed him (HANDOFF issue 58).
            if cur_pos != su_pos and (zone_id, su_pos) not in STAIRS_GIVEUP:
                flee = f"Tactical Retreat: Fleeing towards stairs up at {su_pos} (HP {hp}/{max_hp}, Stratum {cur_z})"
                if (zone_id, su_pos) not in UNREACHABLE_SECTORS:
                    return {"action": f"NAVIGATE_TO_CELL:{su_pos[0]},{su_pos[1]}", "reason": flee}
                best_m = get_best_move_towards(cur_pos, su_pos, valid_moves)
                if best_m and sector_target_ok(zone_id, su_pos, cur_pos, "stairs"):
                    return {"action": best_m, "reason": flee + " [no engine route; stepping greedily]"}

    border_decision = border_retreat_decision(game_state, zone_id, cur_pos, enemies)
    if border_decision:
        print(f"[DANGER RETREAT] {border_decision['reason']}")
        return border_decision

    # Priority Attribute Allocation: If character leveled up and has unspent AP, spend immediately before battle
    g_ap = game_state.get("ap", 0)
    if g_ap > 0 and not adj_threats and not took_damage and not suppress_autolevel:
        attrs = game_state.get("attributes", {})
        rec_stat, reason = build_templates.get_stat_allocation_recommendation(template, attrs)
        return {"action": f"AUTOLEVEL_STAT:{rec_stat}", "reason": f"Class Progression ({template['name']}): {reason}"}

    # ==========================================================
    # PHASE A: DETERMINISTIC SAFE MODE (Zero Latency / 0ms tokens)
    # ==========================================================
    if not is_in_combat:
        consecutive_kites = 0

        # Check if retreat goal is accomplished
        if RETREAT_TARGET_LEVEL is not None and cur_lvl >= RETREAT_TARGET_LEVEL:
            print(f"[TACTICAL COMEBACK]: Attained target Level {cur_lvl} after retreat! Ready to re-delve deeper.")
            RETREAT_TARGET_LEVEL = None

        claws_decision = claws_toggle_action(abilities, is_town)
        if claws_decision:
            return claws_decision

        # 1. Autolevel unspent character points according to class doctrine
        ap = game_state.get("ap", 0)
        sp = game_state.get("sp", 0)
        mp = game_state.get("mp", 0)

        muts = game_state.get("mutations", [])
        can_level_any_mut = any(m.get("can_level", False) and m.get("level", 0) < m.get("cap", 99) for m in muts)
        can_buy_mutation = mp >= 4
        can_spend_mp = (mp > 0 and can_level_any_mut) or can_buy_mutation
        has_points_to_spend = (ap > 0) or (sp >= 50) or can_spend_mp

        # Check for eligible skills or free (0-cost) powers
        best_skill, skill_reason, is_saving_sp = build_templates.get_best_skill_to_learn(game_state, template)
        can_learn_skill = (best_skill is not None)

        if not suppress_autolevel and (has_points_to_spend or can_learn_skill) and not took_damage:
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
                top_mut = getattr(twitch_manager, "get_top_mutation", lambda: None)()
                if can_spend_mp and top_mut:
                    mut_name, count = top_mut
                    twitch_manager.reset_mutation_votes()
                    if mp >= 4 and (not can_level_any_mut or not any(m.get("class", "").lower() == mut_name.lower() for m in muts)):
                        return {"action": f"AUTOLEVEL_BUY_MUTATION:{mut_name}", "reason": f"Twitch Chat Vote winner: {mut_name} ({count} votes) - unlocking new ability"}
                    else:
                        return {"action": f"AUTOLEVEL_MUTATION:{mut_name}", "reason": f"Twitch Chat Vote winner: {mut_name} ({count} votes) - leveling mutation"}

            # Class template allocation priorities
            if ap > 0:
                attrs = game_state.get("attributes", {})
                rec_stat, reason = build_templates.get_stat_allocation_recommendation(template, attrs)
                return {"action": f"AUTOLEVEL_STAT:{rec_stat}", "reason": f"Class Progression ({template['name']}): {reason}"}

            if can_learn_skill:
                return {"action": f"AUTOLEVEL_SKILL:{best_skill}", "reason": skill_reason}
            elif is_saving_sp:
                # Character is purposefully saving SP for the next priority milestone in the tree
                pass

            if can_spend_mp:
                rec_action, rec_reason = build_templates.get_mutation_allocation_recommendation(template, muts, mp)
                if rec_action:
                    return {"action": rec_action, "reason": rec_reason}

            if ap > 0 or can_spend_mp:
                return {"action": "AUTOLEVEL", "reason": f"Safe autoleveling: allocating unspent points (AP:{ap}, SP:{sp}, MP:{mp})"}

        # 2. Survival & Sustenance Routine: Butchering, Cooking, Camping & Relieving Hunger
        hunger = game_state.get("hunger_level", "Satisfied")
        effects = game_state.get("effects", [])
        is_swimming = game_state.get("is_swimming", False) or any("swimming" in ef.lower() for ef in effects)
        is_famished = game_state.get("is_famished", False) or hunger == "Famished" or any("famished" in ef.lower() or "starving" in ef.lower() for ef in effects)
        is_hungry = game_state.get("is_hungry", False) or is_famished or hunger == "Hungry" or any("hungry" in ef.lower() for ef in effects)
        has_food = game_state.get("has_food", False) or game_state.get("food_count", 0) > 0
        food_count = game_state.get("food_count", 0)
        campfire_nearby = game_state.get("campfire_nearby", False)
        corpses_nearby = game_state.get("corpses_nearby", 0)
        harvestable_nearby = game_state.get("harvestable_nearby", 0)
        learned_skills = set(game_state.get("skills", []))
        can_make_camp = not is_swimming and (game_state.get("can_make_camp", False) or ("Survival_Camp" in learned_skills))
        can_cook = not is_swimming and (game_state.get("can_cook", False) or (campfire_nearby and (food_count > 0 or "CookingAndGathering" in learned_skills)))
        can_butcher = not is_swimming and (game_state.get("can_butcher", False) or ("CookingAndGathering_Butchery" in learned_skills and corpses_nearby > 0))
        can_harvest = not is_swimming and (game_state.get("can_harvest", False) or ("CookingAndGathering_Harvestry" in learned_skills and harvestable_nearby > 0))

        # 2A. Field harvesting & butchery: opportunistically butcher animal corpses and harvest plants when safe
        global BUTCHER_STREAK, BUTCHER_TURN, BUTCHER_SUPPRESS_UNTIL
        BUTCHER_TURN += 1
        BUTCHER_STREAK = BUTCHER_STREAK + 1 if last_action == "BUTCHER" else 0
        if BUTCHER_STREAK >= 3:
            BUTCHER_SUPPRESS_UNTIL = BUTCHER_TURN + BUTCHER_COOLDOWN_TURNS
        if can_butcher and BUTCHER_TURN >= BUTCHER_SUPPRESS_UNTIL:
            return {"action": "BUTCHER", "reason": "Survival: Butchering animal corpse for meat & cooking ingredients"}
        if can_harvest:
            return {"action": "HARVEST", "reason": "Survival: Harvesting wild plant for fresh cooking ingredients"}

        # 2B. Relief of hunger (Famished or Hungry)
        # No free meals: camping/cooking no longer relieves hunger (COOK_MEAL needs an ingredient and gives nothing EAT
        # does not). Hunger is relieved by eating real food; otherwise he forages (2C).
        if is_famished or is_hungry:
            if has_food:
                return {"action": "EAT", "reason": f"Survival ({hunger}): Eating food from inventory to relieve hunger"}

        # 2C. Earn dinner: walk to a butcherable corpse / harvestable plant when hungry or low on food
        if (is_hungry or food_count < FOOD_RESTOCK_THRESHOLD) and not is_swimming:
            forage = choose_food_source(game_state, zone_id, learned_skills, last_action)
            if forage:
                return forage

        # 3. Rest until healed if safe and damaged below threshold (default 75%)
        if hp_ratio < REST_HP_THRESHOLD and not took_damage and not is_swimming:
            pct = int(hp_ratio * 100)
            return {"action": "REST", "reason": f"Safe resting: HP at {pct}% (< {int(REST_HP_THRESHOLD*100)}%)"}

        # 3B. Loot: unowned ground items and chests (issue 59). Phase A only, so never with a hostile around.
        loot_decision = choose_loot_action(game_state, zone_id, last_action, is_town)
        if loot_decision:
            return loot_decision

        # 4. Top-off ammo while area is secure (only if we have spare ammo in inventory!)
        if has_missile and max_ammo > 0 and ammo < max_ammo and inv_ammo > 0:
            return {"action": "RELOAD", "reason": f"Safe top-off: reloading rifle ({ammo}/{max_ammo}, Inv: {inv_ammo})"}

        # 4B. Companion Recruitment (Exploration Phase)
        # If without an active pet, recruit adjacent or nearby beasts/humanoids into combat tanks
        raw_entities = game_state.get("visible_entities", [])
        has_companion = game_state.get("has_companion", False) or bool(companions) or any(e.get("is_companion") for e in raw_entities)
        if not has_companion:
            ab_proselytize = find_ready_ability(abilities, "proselytize")
            if ab_proselytize and ab_proselytize.get("command"):
                # Adjacent candidate recruitment (dist == 1)
                for ent in raw_entities:
                    if ent.get("dist") == 1 and is_proselytizable(ent, companions=companions):
                        p_dir = ent.get("dir") or get_step_direction(cur_pos, (ent.get("tx", px), ent.get("ty", py)))
                        if p_dir:
                            p_name = ent.get("name", "Creature")
                            return {
                                "action": f"USE_ABILITY:{ab_proselytize['command']}:{p_dir}",
                                "reason": f"Companion Recruitment: Proselytizing adjacent {p_name} ({p_dir}) into combat pet & frontline tank"
                            }
                # Nearby candidate approach (dist == 2 ONLY): strictly 1 step away on dry land
                for ent in raw_entities:
                    if ent.get("dist") == 2 and is_proselytizable(ent, companions=companions):
                        s_step = get_step_direction(cur_pos, (ent.get("tx", px), ent.get("ty", py)))
                        if s_step and f"MOVE_{s_step}" in valid_moves and not is_swim_move(f"MOVE_{s_step}", surroundings):
                            p_name = ent.get("name", "Creature")
                            return {
                                "action": f"MOVE_{s_step}",
                                "reason": f"Companion Recruitment: Approaching nearby {p_name} ({s_step}) to recruit as frontline pet"
                            }

        # 5. Stratum Progression & Staircase Delving (The Tough Choice)
        req_depth_lvl = min_level_for_depth(cur_z + 1)
        hp_ratio = hp / max(1, max_hp)
        is_healthy = (hp_ratio >= 0.70)
        is_subterranean = (cur_z > 10)
        # The retreat goal is a LEVEL goal: no further descent until the level warrants it, whatever his HP is. It used to
        # require hp_ratio < 0.85, so a retreat at full health (e.g. from an "Impossible" legendary creature) was forgotten
        # at once and he re-descended: an endless stairs ping-pong (HANDOFF issue 48).
        is_retreating = (RETREAT_TARGET_LEVEL is not None and cur_lvl < RETREAT_TARGET_LEVEL)

        is_stuck_explore = (bool(zone_id and zone_id in stuck_autoexplore_zones) or (current_zone_id is not None and current_zone_id in stuck_autoexplore_zones))
        is_zone_cleared = game_state.get("zone_fully_explored", False) or is_stuck_explore or (game_state.get("unexplored_cells", 999) == 0)

        # In dungeons (cur_z > 10), healthy adventurers make the tough choice to keep diving deeper,
        # even if below the recommended level!
        # On the surface (cur_z <= 10), explore first to reach Level 3 before entering the dungeon depths.
        can_delve = (not is_retreating) and is_healthy and (
            is_subterranean or (cur_lvl >= req_depth_lvl)
        )

        if standing_on_sd:
            if can_delve:
                if cur_lvl >= req_depth_lvl:
                    return {"action": "USE_STAIRS_DOWN", "reason": f"Stratum Progression: Descending stairs down to stratum {cur_z + 1} (Level {cur_lvl} >= Req {req_depth_lvl})"}
                else:
                    return {"action": "USE_STAIRS_DOWN", "reason": f"Dungeon Delving: Daring descent into stratum {cur_z + 1} (Level {cur_lvl} < Rec {req_depth_lvl}, HP {hp}/{max_hp})"}
            elif not is_healthy and not is_in_combat and is_subterranean:
                return {"action": "REST", "reason": f"Delve Preparation: Resting on stairs down to recover HP ({hp}/{max_hp}) before descending to stratum {cur_z + 1}"}
            else:
                print(f"[STAIRCASE GATED]: Standing on stairs down to stratum {cur_z + 1}, but Level {cur_lvl} < Req {req_depth_lvl} (or recovering from retreat). Exploring to gain levels first.")

        # If we know stairs down and are ready to delve, check if we should navigate to them
        has_visible_threats = bool(enemies) or any(
            not is_peaceful_npc(e.get("name"), e.get("blueprint")) and not is_ignorable_stationary_enemy(e)
            for e in game_state.get("visible_entities", [])
        )
        if can_delve and (is_zone_cleared or (is_subterranean and is_healthy and not has_visible_threats)) and (zone_id in KNOWN_STAIRS_DOWN):
            sd_info = KNOWN_STAIRS_DOWN[zone_id]
            sd_pos = (sd_info["tx"], sd_info["ty"])
            # In dungeons, if zone is cleared (or subterranean with no visible threats), route to stairs down
            if is_zone_cleared or (is_subterranean and cur_pos != sd_pos and max(abs(px - sd_pos[0]), abs(py - sd_pos[1])) <= 6):
                # The engine pathfinder, not a greedy step: a wall between him and the stairs made the greedy step flip back and
                # forth for 40+ turns (HANDOFF issue 55, R6). A PATH_BLOCKED report puts the stairs in UNREACHABLE_SECTORS and
                # delving is skipped until another route opens up.
                if cur_pos != sd_pos and (zone_id, sd_pos) not in STAIRS_GIVEUP:
                    delve_type = "Dungeon Delving" if is_subterranean else "Dungeon Entry"
                    rec_str = f"Level {cur_lvl} >= Req {req_depth_lvl}" if cur_lvl >= req_depth_lvl else f"Level {cur_lvl} < Rec {req_depth_lvl}"
                    if (zone_id, sd_pos) not in UNREACHABLE_SECTORS:
                        return {"action": f"NAVIGATE_TO_CELL:{sd_pos[0]},{sd_pos[1]}", "reason": f"{delve_type}: Navigating to stairs down at {sd_pos} to delve stratum {cur_z + 1} ({rec_str})"}
                    # The engine pathfinder reported no route (it may not swim). Greedy steps only as a guarded fallback.
                    best_m = get_best_move_towards(cur_pos, sd_pos, valid_moves)
                    if best_m and sector_target_ok(zone_id, sd_pos, cur_pos, "stairs"):
                        return {"action": best_m, "reason": f"{delve_type}: no engine route to the stairs at {sd_pos}; stepping {best_m[5:]} toward them ({rec_str})"}

        # 6. Inward Border Navigation & Zone Hopping Prevention
        rev_dir = LAST_ZONE_ENTRY.get("reverse_dir") if LAST_ZONE_ENTRY else None
        rev_exit = f"MOVE_{rev_dir}" if rev_dir else None
        is_on_border = (px in (0, 79) or py in (0, 24))

        # Arrival grace only. It must NOT also apply while ZONE_HOPPING_DETECTED stays true for the whole stay: crossing a
        # border means standing on the border cell first, so that made every exit impossible (the "dance on the zone
        # line", HANDOFF issue 39). The hopping flag steers exit CHOICE (get_zone_exit_target), not movement here.
        if is_on_border and ZONE_STEP_COUNT <= 4:
            target_interior = (40, 12)
            inward_moves = []
            for vm in valid_moves:
                vdir = vm[5:]
                dx, dy = CARDINAL_OFFSETS.get(vdir, (0, 0))
                nx, ny = px + dx, py + dy
                if 1 <= nx <= 78 and 1 <= ny <= 23:
                    if vm != rev_exit:
                        inward_moves.append(vm)

            if inward_moves:
                best_inward = get_best_move_towards(cur_pos, target_interior, inward_moves)
                if best_inward:
                    tag = "Zone Hopping Breaker" if ZONE_HOPPING_DETECTED else "Border Navigation"
                    return {"action": best_inward, "reason": f"{tag}: Stepping inward {best_inward} toward zone interior to establish stable foothold"}

        # 7. Autonomous area exploration via Caves of Qud native Autoexplore
        unexp_cells = game_state.get("unexplored_cells", None)
        is_subterranean = (cur_z > 10)
        # In subterranean strata (z > 10), solid rock walls permanently occlude hundreds of cells (500-1500 cells).
        # When native autoexplore and pathfinding confirm no reachable unexplored cells remain,
        # the engine sets zone_fully_explored: True.
        # In towns/settlements (is_town), buildings/huts permanently conceal hundreds of cells.
        # When autoexplore finishes or stalls, the town is fully explored and character must exit.
        # On the surface (z <= 10), trust native autoexplore completion or stuck resolution.
        if zone_id and zone_id in EXPLORED_ZONE_SET:
            zone_fully_explored = True
        elif is_subterranean:
            zone_fully_explored = game_state.get("zone_fully_explored", False) or (unexp_cells == 0)
        else:
            if not is_stuck_explore and unexp_cells is not None and unexp_cells > 35 and not (zone_id and zone_id in EXPLORED_ZONE_SET):
                zone_fully_explored = False
            else:
                zone_fully_explored = game_state.get("zone_fully_explored", False) or (unexp_cells == 0)
        zone_label = "Zone fully explored"

        # Determine if there is an unexplored sector (across water/obstacles)
        is_exiting_zone = bool(CURRENT_ZONE_CHOSEN_EXIT and CURRENT_ZONE_CHOSEN_EXIT_ZONE == zone_id)
        has_unexplored_sector = (not is_town) and (not zone_fully_explored) and (not is_exiting_zone) and (unexp_cells is not None and unexp_cells > 0)
        sector_target = None
        sector_reason = ""
        sector_is_frontier = False
        frontier_checked = bool(game_state.get("frontier_checked"))
        if has_unexplored_sector and frontier_checked:
            sector_target, sector_reason = pick_frontier_target(game_state, cur_pos, zone_id, last_action)
            sector_is_frontier = sector_target is not None
            if sector_target is None and game_state.get("reachable_edges"):
                # The engine pathfinder finds no reachable unexplored area: what is left is rock. Leave, and say so.
                zone_fully_explored = True
                zone_label = "No reachable unexplored area"
                has_unexplored_sector = False
        elif has_unexplored_sector:
            cx = game_state.get("unexplored_centroid_x", -1)
            cy = game_state.get("unexplored_centroid_y", -1)
            nx = game_state.get("nearest_unexplored_x", -1)
            ny = game_state.get("nearest_unexplored_y", -1)
            if 0 <= cx < 80 and 0 <= cy < 25 and (cx != px or cy != py) and (zone_id, (cx, cy)) not in UNREACHABLE_SECTORS and sector_target_ok(zone_id, (cx, cy), cur_pos):
                sector_target = (cx, cy)
                sector_reason = f"Water Traversal: Navigating across water toward unexplored sector at {sector_target} ({unexp_cells} unrevealed cells)"
            elif 0 <= nx < 80 and 0 <= ny < 25 and (nx != px or ny != py) and (zone_id, (nx, ny)) not in UNREACHABLE_SECTORS and zone_id not in SECTOR_GIVEUP and sector_target_ok(zone_id, (nx, ny), cur_pos, "nearest"):
                sector_target = (nx, ny)
                sector_reason = f"Water Traversal: Navigating toward nearest unexplored cell at {sector_target} ({unexp_cells} unrevealed cells)"
        elif unexp_cells is None and not is_town and not zone_fully_explored and not is_exiting_zone:
            # Fallback for synthetic dry-run tests without full zone grid telemetry
            cand_target, cand_reason = find_zone_unexplored_frontier(game_state, cur_pos, visit_counts)
            if cand_target and (zone_id, cand_target) not in UNREACHABLE_SECTORS:
                sector_target, sector_reason = cand_target, cand_reason

        best_sector_m = None
        if sector_target and valid_moves and not sector_is_frontier:
            best_sector_m = get_best_move_towards(cur_pos, sector_target, valid_moves, surroundings)

        is_swimming_now = game_state.get("is_swimming", False) or any("swim" in ef.lower() for ef in game_state.get("effects", []))

        # Check if native autoexplore can run:
        can_use_native_autoexplore = (not is_swimming_now) and (not is_stuck_explore) and (not zone_fully_explored) and (unexp_cells is None or unexp_cells > 0)
        if can_use_native_autoexplore:
            return {"action": "AUTOEXPLORE", "reason": "Safe exploration: advancing via native Qud autoexplore pathfinder"}

        # 8. Unexplored Sector across Water / Obstacles (Macro-sector navigation)
        if (not is_town) and (not zone_fully_explored) and sector_target and not is_exiting_zone:
            # Check if trapped in an enclosed pocket (visited multiple times with all moves leading to visited tiles)
            all_moves_visited = (not valid_moves) or all(visit_counts.get((cur_pos[0] + CARDINAL_OFFSETS[m[5:]][0], cur_pos[1] + CARDINAL_OFFSETS[m[5:]][1]), 0) >= 1 for m in valid_moves)
            # In towns/settlements, NEVER attack walls or whack huts!
            if not is_town and not sector_is_frontier and (is_stuck_explore or visit_counts[cur_pos] >= 2) and all_moves_visited:
                burrow_d, burrow_info = find_burrow_direction(surroundings, cur_pos, sector_target, is_town=is_town)
                if burrow_d:
                    return {
                        "action": f"ATTACK_WALL:{burrow_d}",
                        "reason": f"Autonomous Burrowing: Attacking {burrow_info} ({burrow_d}) to breach enclosed pocket toward sector {sector_target}"
                    }

            # If stuck in an enclosed pocket with no burrow and all moves already visited, don't force moves toward unreachable sector!
            is_stuck_in_visited_pocket = (is_stuck_explore or visit_counts[cur_pos] >= 2) and all_moves_visited and not sector_is_frontier
            if not is_stuck_in_visited_pocket:
                if best_sector_m:
                    return {"action": best_sector_m, "reason": sector_reason}
                return {"action": f"NAVIGATE_TO_CELL:{sector_target[0]},{sector_target[1]}", "reason": sector_reason}

        # 9. Local unexplored frontier: If any adjacent move leads to a completely unvisited tile (0 visits)
        # ONLY if the zone is not fully cleared (e.g. recovering from room loop in Joppa)
        if not zone_fully_explored and not is_exiting_zone:
            unvisited_local = [
                m for m in valid_moves
                if visit_counts.get((cur_pos[0] + CARDINAL_OFFSETS[m[5:]][0], cur_pos[1] + CARDINAL_OFFSETS[m[5:]][1]), 0) == 0
            ]
            if unvisited_local:
                unvisited_local.sort(key=lambda m: (1 if is_swim_move(m, surroundings) else 0))
                return {"action": unvisited_local[0], "reason": f"Scouting zone frontier {unvisited_local[0]}"}

        # If autoexplore is stuck and there is no reachable local frontier, give up on this zone for now and leave.
        # This is a local, one-turn decision: it is NOT recorded as "explored" (the engine did not say so) and the
        # reason text says what really happened.
        if (is_stuck_explore or is_town) and not zone_fully_explored and not is_exiting_zone:
            zone_fully_explored = True
            zone_label = "Town explored" if is_town else "Autoexplore stuck, leaving zone"

        # 10. Transition to adjacent zone via exit border (if standing directly on exit or adjacent to chosen border)
        exit_moves = [m for m in valid_moves if "[zone_exit" in surroundings.get(m[5:], "").lower() or "exit" in surroundings.get(m[5:], "").lower()]

        # Validate or select zone exit target
        exit_target_pos, exit_tag, exit_dir = get_zone_exit_target(cur_pos, game_state)

        # If a zone exit direction was chosen, commit to stepping onto or across the border
        if CURRENT_ZONE_CHOSEN_EXIT and CURRENT_ZONE_CHOSEN_EXIT_ZONE == zone_id:
            chosen_m = f"MOVE_{CURRENT_ZONE_CHOSEN_EXIT}"
            # Standing directly on border edge (px=0 for W, px=79 for E, py=0 for N, py=24 for S)
            is_on_chosen_border = (
                (CURRENT_ZONE_CHOSEN_EXIT == "W" and px == 0)
                or (CURRENT_ZONE_CHOSEN_EXIT == "E" and px == 79)
                or (CURRENT_ZONE_CHOSEN_EXIT == "N" and py == 0)
                or (CURRENT_ZONE_CHOSEN_EXIT == "S" and py == 24)
            )
            if is_on_chosen_border and (chosen_m in valid_moves or chosen_m in exit_moves):
                return {"action": chosen_m, "reason": f"Border Transition: Stepping across {CURRENT_ZONE_CHOSEN_EXIT} border into adjacent zone"}

            # Adjacent to border edge (px=1 for W, px=78 for E, py=1 for N, py=23 for S)
            is_adj_to_border = (
                (CURRENT_ZONE_CHOSEN_EXIT == "W" and px == 1)
                or (CURRENT_ZONE_CHOSEN_EXIT == "E" and px == 78)
                or (CURRENT_ZONE_CHOSEN_EXIT == "N" and py == 1)
                or (CURRENT_ZONE_CHOSEN_EXIT == "S" and py == 23)
            )
            if is_adj_to_border and chosen_m in valid_moves:
                return {"action": chosen_m, "reason": f"Border Transition: Advancing {chosen_m} onto zone exit border"}

            # If not yet on or adjacent to border, navigate toward the chosen exit border via native engine pathfinder!
            return {"action": f"NAVIGATE_ZONE_EXIT:{CURRENT_ZONE_CHOSEN_EXIT}", "reason": f"{zone_label}: navigating via engine pathfinder toward {exit_tag}"}

        if exit_moves:
            forward_exits = [m for m in exit_moves if m != rev_exit]

            # Prioritize chosen exit if present in forward_exits
            if CURRENT_ZONE_CHOSEN_EXIT and f"MOVE_{CURRENT_ZONE_CHOSEN_EXIT}" in forward_exits:
                return {"action": f"MOVE_{CURRENT_ZONE_CHOSEN_EXIT}", "reason": f"{zone_label}: transitioning to adjacent zone via chosen exit MOVE_{CURRENT_ZONE_CHOSEN_EXIT}"}

            # When zone hopping is detected, filter exits that lead back into cycle/explored zones
            if ZONE_HOPPING_DETECTED and zone_id and forward_exits:
                cycle_zones = set(list(RECENT_ZONES)[-max(ZONE_CYCLE_LENGTH, 2):])
                avoid_zones = cycle_zones | EXPLORED_ZONE_SET
                novel_exits = []
                for m in forward_exits:
                    m_dir = m[5:]  # e.g. "N", "SE" etc.
                    # Only check cardinal directions for zone transitions
                    if m_dir in ("N", "S", "E", "W"):
                        adj_zone = _compute_adjacent_zone_id(zone_id, m_dir)
                        if adj_zone and adj_zone not in avoid_zones:
                            novel_exits.append(m)
                    else:
                        novel_exits.append(m)  # Diagonal exits are rare; allow them
                if novel_exits:
                    return {"action": novel_exits[0], "reason": f"{zone_label}: transitioning to novel zone via {novel_exits[0]} (avoiding {len(avoid_zones)} cycle/explored zones)"}
                # All exits lead to cycle zones — fall through to step 11 which uses smart exit target

            elif forward_exits:
                return {"action": forward_exits[0], "reason": f"{zone_label}: transitioning to adjacent zone via {forward_exits[0]}"}
            elif not ZONE_HOPPING_DETECTED and (ZONE_STEP_COUNT > 6):
                return {"action": exit_moves[0], "reason": f"{zone_label}: backtracking to prior zone via {exit_moves[0]}"}
            else:
                print(f"[Zone Hopping Breaker] Suppressed immediate backtrack {exit_moves[0]} to avoid border ping-pong loop.")

        # 11. Navigate directly to forward zone exit border if zone is fully explored
        if zone_fully_explored or is_stuck_explore or (unexp_cells == 0):
            if not game_state.get("zone_fully_explored", False) and unexp_cells != 0:
                zone_label = "Town explored" if is_town else "Autoexplore stuck, leaving zone"
            exit_target_pos, exit_tag, exit_dir = get_zone_exit_target(cur_pos, game_state)
            if exit_dir and valid_moves:
                return {"action": f"NAVIGATE_ZONE_EXIT:{exit_dir}", "reason": f"{zone_label}: navigating via engine pathfinder toward {exit_tag}"}

        # 12. Least-visited fallback
        if valid_moves:
            ranked = sorted(valid_moves, key=lambda m: (
                visit_counts[(cur_pos[0] + CARDINAL_OFFSETS[m[5:]][0], cur_pos[1] + CARDINAL_OFFSETS[m[5:]][1])],
                1 if is_swim_move(m, surroundings) else 0
            ))
            return {"action": ranked[0], "reason": f"{zone_label}: scouting zone frontier {ranked[0]}"}

        return {"action": "WAIT", "reason": f"{zone_label}: no open moves"}

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
    global CURRENT_ZONE_CHOSEN_EXIT, CURRENT_ZONE_CHOSEN_EXIT_ZONE, FAILED_ZONE_EXITS

    remove_stale_flag()
    twitch_manager = twitch_bot.start_twitch_in_background()

    autolevel_breaker = AutolevelBreaker()

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
                CHARMED_COMPANION_COORDS.clear()
                if death_data:
                    last_state_for_pm = None
                    try:
                        with open(os.path.join(EXCHANGE_DIR, "last_state.json"), "r", encoding="utf-8-sig") as lsf:
                            last_state_for_pm = json.load(lsf, strict=False)
                    except Exception:
                        pass
                    danger_ledger.record_death(last_state_for_pm, death_data.get("death_reason"))
                    chronicler.process_death_event(death_data, list(recent_actions), active_model_id, last_state=last_state_for_pm, trace_path=DECISION_TRACE_PATH)
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
                px = game_state.get("x", 0)
                py = game_state.get("y", 0)
                cur_pos = (px, py)
                zone_id = game_state.get("zone_id")
                if current_zone_id is not None and zone_id != current_zone_id:
                    consecutive_kites = 0

                update_zone_records(game_state)
                note_burrow_progress(game_state)
                note_ability_use(game_state)
                note_loot(game_state)
                current_zone_id = zone_id
                zone_step_count = ZONE_STEP_COUNT

                hp = game_state.get("hp", 0)
                max_hp = game_state.get("max_hp", 1)
                took_damage = (last_hp is not None and hp < last_hp)
                danger_ledger.record_turn_damage(game_state, last_hp)
                last_hp = hp

                visit_counts[cur_pos] += 1
                recent_positions.append(cur_pos)
                pos_frequency = recent_positions.count(cur_pos)
                unique_positions = len(set(recent_positions))

                companions = list(game_state.get("companions", []))
                raw_entities = game_state.get("visible_entities", [])

                current_comp_coords = set()

                # 1. Update from raw_entities: trust only the engine-exported `is_companion` flag (never match by name)
                for e in raw_entities:
                    if e.get("is_companion", False):
                        e["is_companion"] = True
                        e["is_enemy"] = False
                        ex, ey = e.get("tx"), e.get("ty")
                        if ex is not None and ey is not None:
                            current_comp_coords.add((ex, ey))

                # 2. Ingest from engine companions list
                for c in companions:
                    cx, cy = c.get("tx"), c.get("ty")
                    if cx is not None and cy is not None:
                        current_comp_coords.add((cx, cy))

                # 3. Maintain persistent companion memory
                if current_comp_coords:
                    CHARMED_COMPANION_COORDS.clear()
                    CHARMED_COMPANION_COORDS.update(current_comp_coords)

                # Synthesize companion display if engine companions array is momentarily empty but we have an active companion
                if not companions and current_comp_coords:
                    for e in raw_entities:
                        if e.get("is_companion"):
                            companions.append({
                                "name": e.get("name"),
                                "hp": e.get("hp", 10),
                                "max_hp": e.get("max_hp", 10),
                                "tx": e.get("tx"),
                                "ty": e.get("ty")
                            })

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
                adj_threats = get_adjacent_threats(surroundings, companions=companions, cur_pos=(game_state.get("x", 0), game_state.get("y", 0)))
                close_threats = get_close_threats(enemies, game_state)
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

                cur_points = (game_state.get("ap", 0), game_state.get("sp", 0), game_state.get("mp", 0), len(game_state.get("skills", [])))
                suppress_auto = autolevel_breaker.suppressed(cur_points)

                decision = query_decision(game_state, took_damage, enemies, suppress_autolevel=suppress_auto)
                action = decision.get("action", "WAIT")
                reason = decision.get("reason", "None given")

                if action.startswith("AUTOLEVEL"):
                    if autolevel_breaker.note_autolevel(cur_points):
                        print(f"[AUTOLEVEL CIRCUIT BREAKER] Unspent points {cur_points} (AP, SP, MP, skills) failed to allocate ({action}). Suppressing autolevel for {AUTOLEVEL_RETRY_TURNS} turns.")
                        decision = query_decision(game_state, took_damage, enemies, suppress_autolevel=True)
                        action = decision.get("action", "WAIT")
                        reason = decision.get("reason", "None given")
                else:
                    autolevel_breaker.note_other(cur_points)

                # No instant companion registration here: a Proselytize/Beguile attempt can fail, and the next
                # state.json reports the real result (`is_companion`, `companions`). AGENTS.md R2.

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
                # (Ignore if player is using abilities, firing missiles, or actively attacking enemies in melee!)
                is_attacking = action.startswith("MOVE_") and (action[5:] in adj_threats)
                is_combat_action = action.startswith("USE_ABILITY") or action.startswith("FIRE_MISSILE") or is_attacking
                is_stationary_repeat = (action == last_executed_action and cur_pos == last_executed_pos and not is_combat_action)
                # A committed engine-reachable frontier walk is exempt from the oscillation breaker: its own failure and
                # pursuit limits (FRONTIER_FAIL_LIMIT / FRONTIER_PURSUIT_MAX) write a bad target off. Without this exemption
                # the breaker overrode the walk with "move away from the cycle centroid" and he ping-ponged forever
                # (HANDOFF issue 47).
                is_frontier_nav = is_frontier_walk(action, reason)
                is_oscillating = not is_in_combat and not is_combat_action and not is_frontier_nav and (
                    (pos_frequency >= 3) or
                    (len(recent_positions) >= 10 and unique_positions <= 5)
                )

                if is_stationary_repeat:
                    action_repeat_count += 1
                    # Mark the failed coordinate as blocked so the AI avoids it
                    if action.startswith("MOVE_") and len(action) > 5:
                        mv_dir = action[5:]
                        if mv_dir in CARDINAL_OFFSETS:
                            mdx, mdy = CARDINAL_OFFSETS[mv_dir]
                            blocked_coords.add((px + mdx, py + mdy))
                            print(f"[Loop Breaker] Move {action} failed to advance at {cur_pos}. Marked ({px + mdx}, {py + mdy}) as blocked.")

                    if action_repeat_count >= 2:
                        open_m = [vm for vm in get_valid_moves(surroundings, cur_pos, None, is_in_combat=is_in_combat)
                                  if vm[5:] not in adj_threats and vm != action]
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
                            valid_m = [vm for vm in get_valid_moves(surroundings, cur_pos, None, is_in_combat=is_in_combat) if vm != action]
                            if valid_m:
                                action = valid_m[0]
                                reason = f"[Loop Breaker] Action repeated {action_repeat_count}x at {cur_pos}. Forcing reposition {action}."
                            else:
                                is_town = is_town_zone(game_state)
                                if not is_town:
                                    burrow_t = (game_state.get("unexplored_centroid_x", px), game_state.get("unexplored_centroid_y", py))
                                    b_d, b_info = find_burrow_direction(surroundings, cur_pos, burrow_t, is_town=is_town)
                                    if b_d:
                                        action = f"ATTACK_WALL:{b_d}"
                                        reason = f"[Loop Breaker] Action repeated {action_repeat_count}x and trapped at {cur_pos}. Burrowing through {b_info} ({b_d})."
                                    else:
                                        action = "PASS"
                                        reason = f"[Loop Breaker] Action repeated {action_repeat_count}x at {cur_pos}. Passing turn."
                                else:
                                    action = "PASS"
                                    reason = f"[Loop Breaker] Action repeated {action_repeat_count}x in town at {cur_pos}. Passing turn."
                        action_repeat_count = 0
                elif is_oscillating and not is_in_combat:
                    is_stuck_explore = (bool(current_zone_id and current_zone_id in stuck_autoexplore_zones))
                    cur_z = game_state.get("z", 10)
                    if action == "AUTOEXPLORE":
                        unexp_c = game_state.get("unexplored_cells", 0) or 0
                        if current_zone_id:
                            stuck_autoexplore_zones.add(current_zone_id)
                        is_stuck_explore = True
                        print(f"[Loop Breaker] Autoexplore oscillation detected at {cur_pos} (freq: {pos_frequency}, unique: {unique_positions}/{len(recent_positions)}). Forcing frontier breakout.")

                    valid_m = get_valid_moves(surroundings, cur_pos, None, is_in_combat=is_in_combat)
                    open_escapes = [m for m in valid_m
                                    if (cur_pos[0] + CARDINAL_OFFSETS[m[5:]][0], cur_pos[1] + CARDINAL_OFFSETS[m[5:]][1]) not in recent_positions]

                    frontier_target, frontier_reason = find_zone_unexplored_frontier(game_state, cur_pos, visit_counts)

                    # If oscillation occurs while trying to exit or after choosing an exit, only blacklist if away from border
                    is_near_border = (px <= 1 or px >= 78 or py <= 1 or py >= 23)
                    if CURRENT_ZONE_CHOSEN_EXIT:
                        if not is_near_border and (pos_frequency >= 3 or is_oscillating or game_state.get("last_move_failed", False)):
                            print(f"[ZONE EXIT RECOVERY] Loop breaker detected oscillation while navigating to exit {CURRENT_ZONE_CHOSEN_EXIT} in zone {current_zone_id}. Blacklisting.")
                            note_exit_failure(current_zone_id, CURRENT_ZONE_CHOSEN_EXIT)
                            CURRENT_ZONE_CHOSEN_EXIT = None
                            CURRENT_ZONE_CHOSEN_EXIT_ZONE = None

                    exit_target_pos, exit_tag, exit_dir = get_zone_exit_target(cur_pos, game_state)

                    is_town = is_town_zone(game_state)
                    burrow_target = (game_state.get("unexplored_centroid_x", px), game_state.get("unexplored_centroid_y", py))
                    burrow_d, burrow_info = find_burrow_direction(surroundings, cur_pos, burrow_target, is_town=is_town)
                    unexp_c = game_state.get("unexplored_cells", 0) or 0

                    # If standing on or right next to border, commit to stepping across rather than turning around
                    chosen_border_m = f"MOVE_{exit_dir}" if exit_dir else None
                    is_on_border = (
                        (exit_dir == "W" and px == 0) or (exit_dir == "E" and px == 79)
                        or (exit_dir == "N" and py == 0) or (exit_dir == "S" and py == 24)
                    )
                    is_adj_border = (
                        (exit_dir == "W" and px == 1) or (exit_dir == "E" and px == 78)
                        or (exit_dir == "N" and py == 1) or (exit_dir == "S" and py == 23)
                    )

                    nav_cell_failed = (
                        last_executed_action.startswith("NAVIGATE_TO_CELL")
                        and (cur_pos == last_executed_pos or game_state.get("last_move_failed", False))
                    )
                    if nav_cell_failed and last_executed_action.startswith("NAVIGATE_TO_CELL:"):
                        try:
                            coords = last_executed_action.split(":")[1].split(",")
                            unreach_t = (int(coords[0]), int(coords[1]))
                            UNREACHABLE_SECTORS.add((current_zone_id, unreach_t))
                        except Exception:
                            pass

                    # Check if an adjacent cell has a friendly companion we can swap places with to break bottlenecks
                    companion_escapes = []
                    for cd in ["N", "S", "E", "W", "NE", "NW", "SE", "SW"]:
                        if "[companion" in surroundings.get(cd, "").lower() or (px + CARDINAL_OFFSETS[cd][0], py + CARDINAL_OFFSETS[cd][1]) in CHARMED_COMPANION_COORDS:
                            companion_escapes.append(f"MOVE_{cd}")

                    if not is_town and unexp_c > 35 and (not open_escapes or unique_positions <= 6) and burrow_d:
                        action = f"ATTACK_WALL:{burrow_d}"
                        reason = f"[Loop Breaker] Trapped in enclosed pocket with {unexp_c} unrevealed cells. Burrowing through {burrow_info} ({burrow_d}) to breach open corridor."
                    elif is_on_border and chosen_border_m and (chosen_border_m in valid_m or "[zone_exit" in surroundings.get(exit_dir or "", "").lower()):
                        action = chosen_border_m
                        reason = f"[Loop Breaker] Standing directly on exit border: committing to {chosen_border_m} to cross into adjacent zone."
                    elif is_adj_border and chosen_border_m and (chosen_border_m in valid_m):
                        action = chosen_border_m
                        reason = f"[Loop Breaker] Adjacent to exit border: stepping {chosen_border_m} onto border edge."
                    elif not is_town and not is_stuck_explore and frontier_target and unexp_c > 35 and cur_z <= 10 and not nav_cell_failed and (current_zone_id, frontier_target) not in UNREACHABLE_SECTORS:
                        action = f"NAVIGATE_TO_CELL:{frontier_target[0]},{frontier_target[1]}"
                        reason = f"[Loop Breaker] Oscillation detected at {cur_pos}. Routing via native pathfinder to unexplored frontier at {frontier_target} ({unexp_c} unrevealed cells)."
                    elif (is_town or is_stuck_explore or game_state.get("zone_fully_explored", False) or (unexp_c == 0)) and exit_dir:
                        action = f"NAVIGATE_ZONE_EXIT:{exit_dir}"
                        reason = f"[Loop Breaker] Oscillation detected at {cur_pos}. Escaping cycle towards forward exit {exit_tag} via native engine pathfinder."
                        CURRENT_ZONE_CHOSEN_EXIT = exit_dir
                        CURRENT_ZONE_CHOSEN_EXIT_ZONE = current_zone_id
                    elif open_escapes:
                        open_escapes.sort(key=lambda m: (
                            visit_counts[(cur_pos[0] + CARDINAL_OFFSETS[m[5:]][0], cur_pos[1] + CARDINAL_OFFSETS[m[5:]][1])],
                            1 if is_swim_move(m, surroundings) else 0
                        ))
                        action = open_escapes[0]
                        reason = f"[Loop Breaker] Oscillation detected at {cur_pos} (freq: {pos_frequency}, unique: {unique_positions}). Escaping cycle towards unvisited frontier {action}."
                    elif companion_escapes and not valid_m:
                        action = companion_escapes[0]
                        reason = f"[Loop Breaker] Corridor blocked by companion: swapping places via {action} to break bottleneck."
                    else:
                        if valid_m:
                            # Maximize distance from the cycle centroid to escape shoreline/subgraph loops
                            recent_set = set(recent_positions)
                            avg_rx = sum(p[0] for p in recent_set) / max(1, len(recent_set))
                            avg_ry = sum(p[1] for p in recent_set) / max(1, len(recent_set))
                            def dist_away_from_cycle(m):
                                dx, dy = CARDINAL_OFFSETS[m[5:]]
                                nx, ny = cur_pos[0] + dx, cur_pos[1] + dy
                                euc_dist = (nx - avg_rx)**2 + (ny - avg_ry)**2
                                return (-euc_dist, visit_counts[(nx, ny)], 1 if is_swim_move(m, surroundings) else 0)
                            valid_m.sort(key=dist_away_from_cycle)
                            action = valid_m[0]
                            reason = f"[Loop Breaker] Oscillation trapped in cycle. Forcing move {action} away from cycle centroid."
                        else:
                            action = "PASS"
                            reason = f"[Loop Breaker] Oscillation trapped at {cur_pos}. Passing turn."
                    action_repeat_count = 0
                else:
                    action_repeat_count = 0

                action, reason = guard_blocked_burrow(action, reason, surroundings, cur_pos, current_zone_id, is_town_zone(game_state))
                action, reason = guard_companion_blocked_burrow(action, reason, surroundings, cur_pos)

                last_executed_action = action
                last_executed_pos = cur_pos
                last_action = action
                if action.startswith("MOVE_"):
                    move_history.append(action)
                recent_actions.append({"action": action, "reason": reason, "pos": cur_pos, "hp": hp})
                log_decision_trace({
                    "t": TURN_CLOCK, "ts": round(time.time(), 1), "zone": game_state.get("zone_id"), "pos": list(cur_pos),
                    "z": game_state.get("z"), "hp": hp, "action": action, "reason": str(reason)[:160],
                    "combat": bool(is_in_combat), "stuck": game_state.get("autoexplore_stuck"),
                    "engine_explored": game_state.get("zone_fully_explored"), "unexp": game_state.get("unexplored_cells"),
                    "nearest": [game_state.get("nearest_unexplored_x"), game_state.get("nearest_unexplored_y")],
                    "reach": game_state.get("reachable_edges"), "chosen_exit": CURRENT_ZONE_CHOSEN_EXIT,
                    "suppressed": EXIT_SUPPRESS_UNTIL.get(game_state.get("zone_id"), 0) > TURN_CLOCK,
                    "move_failed": game_state.get("last_move_failed"), "model": active_model_id,
                })

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