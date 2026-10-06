"""Mutation choice policy (HANDOFF issue 50).

Caves of Qud offers three random mutations when a mutant buys a new one (Rapid Advancement at levels 4-5, or 4 MP). The C# mod
answers that picker synchronously, so it cannot ask Python at that moment. Instead Python publishes a ranking file
(`mutation_ranking.txt` in the exchange folder) for the detected build; C# reads it and picks the best-ranked option.

This module is POLICY (what we want), not an engine rule (AGENTS R3): the data below can be changed freely. Engine facts used:
the list of mutation names comes from `StreamingAssets/Base/Mutations.xml` (59 normal mutations, 20 defects, 3 morphotypes) and
the picker's option text looks like "Burrowing Claws - You bear spade-like claws..." or "Heightened Quickness (1)"
[verified in game, 2026-10-06 Player.log; names verified from the XML].
"""
import os
import re

# Tiers, best first. The order inside a tier is the order of preference.
TIER_SURVIVAL = [          # stay alive and mobile: the most useful for an unattended agent
    "Heightened Quickness", "Regeneration", "Force Bubble", "Force Wall", "Phasing", "Carapace",
    "Two-hearted", "Time Dilation", "Teleportation", "Adrenal Control",
]
TIER_CONTROL = [           # safe ranged damage and control, good with pets (Thrallmaster)
    "Sunder Mind", "Freezing Ray", "Cryokinesis", "Disintegration", "Domination", "Beguiling", "Stunning Force",
    "Light Manipulation", "Precognition", "Syphon Vim", "Mental Mirror", "Confusion", "Teleport Other", "Clairvoyance",
    "Spacetime Vortex", "Ego Projection", "Mass Mind", "Telepathy", "Temporal Fugue",
]
TIER_TRAVERSAL = [         # get through procedural terrain: trees, walls, water, dead ends (human decision, 2026-10-06).
    # The engine has pathing flags PathAsBurrower and PathAsIfFlying, a "burrowed" state and a Flying effect that is "not
    # affected by terrain" [verified in code strings]. Phasing and Teleportation also help, but sit in TIER_SURVIVAL as escapes.
    "Burrowing Claws", "Wings",
]
TIER_PHYSICAL = [          # melee and body mutations
    "Double-muscled", "Multiple Arms", "Multiple Legs", "Triple-jointed", "Two-headed", "Horns",
    "Stinger (Paralyzing Venom)", "Stinger (Confusing Venom)", "Thick Fur", "Quills", "Spinnerets",
    "Beak", "Electromagnetic Pulse",
]
TIER_SITUATIONAL = [       # passive or niche
    "Night Vision", "Heightened Hearing", "Photosynthetic Skin", "Sense Psychic", "Psychometry", "Burgeoning",
    "Metamorphosis", "Slime Glands", "Stinger (Poisoning Venom)",
]
TIER_HAZARDOUS = [         # start fires or gas clouds around an agent that walks through forests and cooks near trees
    "Flaming Ray", "Pyrokinesis", "Kindle", "Corrosive Gas Generation", "Sleep Gas Generation", "Electrical Generation",
]
DEFECTS = [                # should never be offered by the picker; ranked last just in case
    "Albino", "Amphibious", "Brittle Bones", "Nerve Poppy", "Carnivorous", "Cold-Blooded", "Electromagnetic Impulse",
    "Hooks for Feet", "Irritable Genome", "Myopic", "Spontaneous Combustion", "Tonic Allergy",
    "Amnesia", "Blinking Tic", "Dystechnia", "Evil Twin", "Narcolepsy", "Psionic Migraines", "Quantum Jitters",
    "Socially Repugnant",
]

UNIVERSAL_MUTATION_RANKING = (TIER_SURVIVAL + TIER_CONTROL + TIER_TRAVERSAL + TIER_PHYSICAL + TIER_SITUATIONAL + TIER_HAZARDOUS + DEFECTS)


def normalize_mutation_name(name):
    """Lower case letters and digits only: 'Double-muscled', 'DoubleMuscled' and 'double muscled' all compare equal."""
    return re.sub(r"[^a-z0-9]", "", str(name or "").lower())


def option_head(option):
    """The mutation name inside a picker option: text before ' - ', without a trailing '(N)' level suffix."""
    s = re.sub(r"\{\{[^|}]*\|", "", str(option or ""))       # Qud colour markup {{G|...
    s = s.replace("}}", "")
    i = s.find(" - ")
    if i >= 0:
        s = s[:i]
    s = re.sub(r"\s*\(\d+\)\s*$", "", s)
    return s.strip()


def build_mutation_ranking(template):
    """The template's own mutation priorities first (class names are fine), then the universal ranking."""
    ranking, seen = [], set()
    for name in list((template or {}).get("mutation_priorities", [])) + UNIVERSAL_MUTATION_RANKING:
        n = normalize_mutation_name(name)
        if n and n not in seen:
            seen.add(n)
            ranking.append(name)
    return ranking


def choose_option(options, ranking, preferred="", builtin=None):
    """Python copy of the C# picker rule (AIPickOptionPatch), for tests. Returns (index, reason).

    1. the mutation requested by the brain command, 2. the best-ranked option in `ranking`, 3. the built-in list,
    4. the default (the first option)."""
    norm = [normalize_mutation_name(option_head(o)) for o in options]
    want = normalize_mutation_name(preferred)
    if want:
        for i, n in enumerate(norm):
            if n and n == want:
                return i, "requested by the brain"
    rank_norm = [normalize_mutation_name(r) for r in (ranking or [])]
    best = None
    for i, n in enumerate(norm):
        if n and n in rank_norm:
            r = rank_norm.index(n)
            if best is None or r < best[0]:
                best = (r, i)
    if best is not None:
        return best[1], f"build ranking #{best[0] + 1}"
    for name in (builtin or []):
        n = normalize_mutation_name(name)
        for i, o in enumerate(norm):
            if o and o == n:
                return i, "built-in list"
    return 0, "default"


_PUBLISHED = {"name": None, "path": None}


def publish_mutation_ranking(template, path):
    """Writes the ranking for the detected build to `path` (mutation_ranking.txt) when the build changes. Never raises."""
    try:
        name = (template or {}).get("name", "")
        if _PUBLISHED["name"] == name and _PUBLISHED["path"] == path and os.path.exists(path):
            return False
        lines = [f"# mutation ranking for build: {name}", "# best first; written by brain.py (mutation_policy.py); read by the mod's mutation picker"]
        lines += build_mutation_ranking(template)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        os.replace(tmp, path)
        _PUBLISHED.update({"name": name, "path": path})
        return True
    except Exception:
        return False
