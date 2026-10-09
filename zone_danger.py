"""Where have we met something we cannot beat, and which way out of this zone leads away from it (BACKLOG B10 step 1, HANDOFF issue 85).

Pure functions and one small ledger; brain.py feeds it and asks it. Nothing here touches the game.
A zone is "flagged" when a mobile hostile there was out of our class (the engine called it Very Tough or Impossible, or our threat score
called it deadly, or several lesser ones together would be). A flag lapses when we have grown: see Flag.clears_at.
Steering only changes WHICH exit the brain picks. It never overrides the engine's reachable edges, the failed-exit list or the stairs.
"""
import re

DIRECTIONS = ("N", "S", "E", "W")
LEVEL_MARGIN = 3              # a flag lapses when our level reaches the creature's level minus this ...
MIN_GROWTH = 2                # ... or when we have gained this many levels since the flag (so a flag for a level-1 pack lapses too)
RETREAT_PRESSURE = 0.5        # back-tracking is considered only when the danger is this close (a flag in this zone or the next one)
AVOID_RADIUS = 8              # frontier targets this close (Chebyshev, in cells) to where the creature was last seen are skipped
AVOID_MAX_AGE = 80            # ... for this many turns after it was last seen (a mobile creature moves on)
# A swarm flag (BACKLOG B10 / HANDOFF issue 97) must never become a permanent block (human, 2026-10-09). It lapses on ANY of: two more levels, two more armor value or two more average
# weapon damage than when it was raised (a gear upgrade), or SWARM_BACKSTOP_TURNS turns. While it holds it only closes the ENTRY to that zone, and only while another way on exists.
SWARM_LEVELS = 2
SWARM_AV_GAIN = 2
SWARM_DAMAGE_GAIN = 2.0
SWARM_BACKSTOP_TURNS = 800
SWARM_RETREAT_MAX = 3         # after this many retreats from one zone he stops retreating from it (no endless in-and-out)


def world_cell(zone_id):
    """(X, Y, depth) on one grid of zones: parasang * 3 + sub-zone, so neighbouring zones differ by 1 even across a parasang border.
    None for an id that is not 'World.wx.wy.sx.sy.z'."""
    parts = str(zone_id or "").split(".")
    if len(parts) < 6:
        return None
    try:
        wx, wy, sx, sy, z = (int(p) for p in parts[1:6])
    except ValueError:
        return None
    return wx * 3 + sx, wy * 3 + sy, z


def zone_distance(a, b):
    """Manhattan distance in zones between two zone ids on the same depth; None when either is unreadable or the depths differ."""
    ca, cb = world_cell(a), world_cell(b)
    if ca is None or cb is None or ca[2] != cb[2]:
        return None
    return abs(ca[0] - cb[0]) + abs(ca[1] - cb[1])


class Flag:
    def __init__(self, zone_id, creature, creature_level, our_level):
        self.zone_id = zone_id
        self.creature = creature
        self.creature_level = int(creature_level or 0)
        self.seen_at_level = int(our_level or 1)
        self.where = None               # (x, y) of the creature the last time it was in view in this zone
        self.where_turn = None
        self.swarm = False              # a pack of individually weak creatures that together would kill him quickly
        self.power = None               # {"av", "melee", "turn"} when a swarm flag was raised
        self.retreats = 0

    @property
    def clears_at(self):
        """Our level at which the zone is acceptable again. Both rules must be met, so the flag lasts until we have grown AND are near the creature's class,
        except that a creature of our own class (a level-1 pack) lapses on growth alone."""
        return max(self.seen_at_level + MIN_GROWTH, min(self.creature_level - LEVEL_MARGIN, self.seen_at_level + 6))

    def active(self, our_level, now=None):
        """now = {"av", "melee", "turn"}: what he is and has at this moment (Ledger.observe). A swarm flag lapses on a level gain, a gear upgrade or time; without `now` only the level counts."""
        if self.swarm:
            if int(our_level or 1) >= self.seen_at_level + SWARM_LEVELS:
                return False
            p, n = self.power or {}, now or {}
            if p and n:
                if (n.get("av") or 0) >= (p.get("av") or 0) + SWARM_AV_GAIN or (n.get("melee") or 0) >= (p.get("melee") or 0) + SWARM_DAMAGE_GAIN:
                    return False
                if n.get("turn") is not None and p.get("turn") is not None and n["turn"] - p["turn"] >= SWARM_BACKSTOP_TURNS:
                    return False
            return True
        return int(our_level or 1) < self.clears_at

    def lapse_text(self):
        """What would end this flag, for the log."""
        if not self.swarm:
            return f"our level {self.clears_at}"
        p = self.power or {}
        return (f"level {self.seen_at_level + SWARM_LEVELS}, or armor {(p.get('av') or 0) + SWARM_AV_GAIN}, or average weapon damage {(p.get('melee') or 0) + SWARM_DAMAGE_GAIN:g}, "
                f"or turn {(p.get('turn') or 0) + SWARM_BACKSTOP_TURNS}")


class Ledger:
    def __init__(self):
        self.flags = {}
        self.now = None

    def observe(self, av, melee, turn):
        """What he has right now (armor value, average main-hand damage, the brain's turn clock): swarm flags lapse on a gear upgrade or on time."""
        self.now = {"av": av or 0, "melee": melee or 0, "turn": turn}

    def record_swarm(self, zone_id, names, count, our_level, av, melee, turn):
        """Flag a zone for a swarm. Keeps the retreat count of an existing flag for the same zone. Returns the flag (None for an unreadable zone id)."""
        if world_cell(zone_id) is None:
            return None
        old = self.flags.get(zone_id)
        f = Flag(zone_id, f"swarm of {count}: {names}", our_level, our_level)
        f.swarm = True
        f.power = {"av": av or 0, "melee": melee or 0, "turn": turn if turn is not None else 0}
        f.retreats = old.retreats if (old is not None and old.swarm) else 0
        self.flags[zone_id] = f
        return f

    def entry_blocked(self, zone_id, our_level):
        """True while a swarm flag on this very zone holds (it closes the way IN, nothing else)."""
        f = self.flags.get(zone_id)
        return bool(f is not None and f.swarm and f.active(our_level, self.now))

    def record(self, zone_id, creature, creature_level, our_level):
        """Remember the worst creature met in a zone. Returns True when this is a new flag or a worse one (the caller prints it)."""
        if world_cell(zone_id) is None:
            return False
        old = self.flags.get(zone_id)
        if old is not None and old.swarm and old.active(our_level, self.now):
            return False                                  # a swarm flag is not replaced by a lesser flag for the same zone
        if old is not None and old.creature_level >= int(creature_level or 0) and old.active(our_level, self.now):
            return False
        self.flags[zone_id] = Flag(zone_id, creature, creature_level, our_level)
        return True

    def seen(self, zone_id, x, y, turn):
        """Remember where the flagged creature was last in view. Ignored for a zone without an active flag."""
        f = self.flags.get(zone_id)
        if f is not None and x is not None and y is not None:
            f.where, f.where_turn = (int(x), int(y)), turn

    def avoid_points(self, zone_id, our_level, turn):
        """Cells in this zone to keep away from: where an active flag's creature was last seen, if that was recent."""
        f = self.flags.get(zone_id)
        if f is None or f.where is None or not f.active(our_level, self.now):
            return []
        if f.where_turn is not None and turn is not None and turn - f.where_turn > AVOID_MAX_AGE:
            return []
        return [f.where]

    def active_flags(self, our_level):
        return [f for f in self.flags.values() if f.active(our_level, self.now)]

    def pressure(self, zone_id, our_level):
        """How close a zone is to the flagged ones: each active flag on the same depth adds 1 / (1 + distance). 0 when nothing is flagged."""
        total = 0.0
        for f in self.active_flags(our_level):
            d = zone_distance(zone_id, f.zone_id)
            if d is not None:
                total += 1.0 / (1.0 + d)
        return total


def adjacent_zone(zone_id, direction):
    """The neighbouring zone id (same convention as brain._compute_adjacent_zone_id, kept here so this module stands alone)."""
    c = world_cell(zone_id)
    if c is None or direction not in DIRECTIONS:
        return None
    parts = str(zone_id).split(".")
    X, Y, z = c
    X += {"E": 1, "W": -1}.get(direction, 0)
    Y += {"S": 1, "N": -1}.get(direction, 0)
    if X < 0 or Y < 0:
        return None
    return f"{parts[0]}.{X // 3}.{Y // 3}.{X % 3}.{Y % 3}.{z}"


def steer(ledger, cur_zone, our_level, candidates, novel, rev_dir):
    """Decide among exits. -> (directions to choose from, mode, note) or (None, None, None) when there is nothing to say (no active flag: the caller's own random choice stands).
    mode 'away' narrows the choice to the exits with the least pressure; mode 'retreat' names the way we came because every way on leads closer to the danger."""
    if not ledger.active_flags(our_level):
        return None, None, None
    pool = list(novel) if novel else list(candidates)
    if not pool:
        return None, None, None
    here = ledger.pressure(cur_zone, our_level)
    scored = {d: ledger.pressure(adjacent_zone(cur_zone, d), our_level) for d in pool}
    best = min(scored.values())
    # every way on is no better than standing here, the danger is close, and the way back is better: go back
    if rev_dir and here >= RETREAT_PRESSURE and best >= here:
        back = ledger.pressure(adjacent_zone(cur_zone, rev_dir), our_level)
        if back < here:
            return [rev_dir], "retreat", f"danger pressure {here:.2f} here, {best:.2f} ahead, {back:.2f} behind"
    keep = [d for d in pool if scored[d] <= best + 1e-9]
    if len(keep) == len(pool):
        return None, None, None             # all equal: no information, the random choice stands
    return keep, "away", "pressure " + ", ".join(f"{d}={scored[d]:.2f}" for d in sorted(scored))
