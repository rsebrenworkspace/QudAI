"""Reference data about every ability in the game, and the family table the brain uses (HANDOFF issue 52).

data/abilities.json        generated from the game's own data by tools/build_ability_registry.py
data/ability_families.json curated: which exact engine commands belong to which family, and whether the brain uses them
memory/ability_stats.json  evidence gathered while playing, kept across characters (written by brain.py)

Matching is by exact engine command (case-insensitive), never by substring on a display name.
"""
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY_PATH = os.path.join(_HERE, "data", "abilities.json")
FAMILIES_PATH = os.path.join(_HERE, "data", "ability_families.json")


def _load(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


REGISTRY = _load(REGISTRY_PATH).get("abilities", {})
_FAMILIES = _load(FAMILIES_PATH).get("families", {})
_REG_LOWER = {c.lower(): c for c in REGISTRY}
FAMILY_COMMANDS = {name: {c.lower() for c in fam.get("commands", [])} for name, fam in _FAMILIES.items()}
AUTO_USE_FAMILIES = {name for name, fam in _FAMILIES.items() if fam.get("auto_use")}


def known(command):
    """True if the engine registry knows this command."""
    return str(command or "").lower() in _REG_LOWER


def info(command):
    """The registry record of a command, or None."""
    real = _REG_LOWER.get(str(command or "").lower())
    return REGISTRY.get(real) if real else None


def family_info(family):
    return _FAMILIES.get(family)


def families_of(command):
    """Names of every family (wired or not) that lists this command."""
    c = str(command or "").lower()
    return sorted(name for name, cmds in FAMILY_COMMANDS.items() if c in cmds)


def in_family(ability, *families):
    """True if the ability's engine command is listed in one of the families, and every such family is wired (auto_use).

    An ability the brain has no wired family for is never matched, so it is never used automatically."""
    c = str((ability or {}).get("command", "")).lower()
    if not c:
        return False
    for fam in families:
        if fam not in AUTO_USE_FAMILIES:
            continue
        if c in FAMILY_COMMANDS.get(fam, ()):
            return True
    return False


def unclassified(command):
    """Known to the engine but in no wired family: never used automatically."""
    return known(command) and not any(f in AUTO_USE_FAMILIES for f in families_of(command))


def is_wired(ability):
    """True if the ability's command is in at least one family the brain uses automatically."""
    c = str((ability or {}).get("command", "")).lower()
    return bool(c) and any(c in FAMILY_COMMANDS.get(f, ()) for f in AUTO_USE_FAMILIES)
