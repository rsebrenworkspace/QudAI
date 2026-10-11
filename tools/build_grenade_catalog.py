"""Builds data/grenades.json from the game's ObjectBlueprints (Items.xml): every grenade blueprint with its mark, tier and engine parameters, plus what each kind does.

Usage: python tools/build_grenade_catalog.py [path to ObjectBlueprints]   (default: the Steam install used by sync_mod.py)

The XML gives the numbers (density, temperature delta, radius, force, duration, level). The per-kind notes (effect, area, hazards, when to use) are written here by hand from the engine
classes (ThermalGrenade, GasGrenade, HEGrenade, ...) and the wiki, and every note carries a confidence tag. Nothing here is a Python copy of an engine rule that the game could tell us
at run time (AGENTS.md R3): it is a catalogue the brain reads, regenerated from the files.
"""
import glob
import json
import os
import re
import sys

DEFAULT_BASE = r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\StreamingAssets\Base\ObjectBlueprints"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "grenades.json")

# kind -> what the part is, the area it affects, and the hazards. Confidence tags: [verified in code] = read from the decompiled engine classes, [wiki] = the community wiki,
# [verified in game] = seen in a capture, [unverified] = a guess to be measured.
KINDS = {
    "gas": {
        "parts": ["GasGrenade"],
        "area": "A cloud: the thrown cell and its adjacent cells receive the gas (GasGrenade.DoDetonate creates a Gas object in each of them, `[verified in code]`), then it spreads by itself every turn: above density 10 a 25 percent chance to move into 1-4 neighbours, at 10 or less a 50 percent chance to vanish; non-seeping gas stays in corridors for hundreds of turns `[wiki]`. No fixed radius.",
        "min_safe_dist": 4,
        "preferred_dist": 5,
        "hazards": ["the cloud drifts back toward the thrower and into corridors and rooms", "companions and the thrower take the effect too", "seeping gases pass through walls"],
        "measured": "mark I and II poison gas in the open (grenade lab 2026-10-11): at 5 tiles the gas never reached a thrower who stood still, at 4 it came adjacent but not onto his cell, at 3 a mark II killed a level 1 character, at 2 it is on his cell the next turn; a mark I cloud lasts 14-20 turns, a mark II 44; BACKLOG B33 results 1-5",
    },
    "thermal": {
        "parts": ["ThermalGrenade"],
        "area": "A blast around the thrown cell: the cell and its neighbours get a TemperatureChange of TemperatureDelta (ThermalGrenade.DoDetonate uses GetAdjacentCells, `[verified in code]`); the wiki gives the freeze grenade a blast radius of 2 and a freeze grenade froze its thrower at 2 tiles `[verified in game 2026-10-10]`, so the radius is treated as 2.",
        "min_safe_dist": 4,
        "hazards": ["cold freezes creatures solid and turns water to ice", "heat ignites grass, plants, oil and flammable creatures and starts fires that spread", "the thrower is hit at 2 tiles or less"],
    },
    "he": {
        "parts": ["HEGrenade"],
        "area": "An explosion: HEGrenade.DoDetonate calls Explode(Force); force falls off cell by cell, reduced by the weight of what it hits, until it is about 100, so the reach depends on the surroundings `[wiki]`. Damage is Force/250 plus dice. No fixed radius; open ground reaches farthest.",
        "min_safe_dist": 5,
        "hazards": ["damages and pushes everything, including the thrower and companions", "explosions can cross zone borders `[wiki]`", "walls and objects absorb force; whether they are damaged is unknown `[unverified]`"],
    },
    "emp": {
        "parts": ["EMPGrenade"],
        "area": "Radius from the part (EMPGrenade.DoDetonate calls EMP(radius, duration), `[verified in code]`); disables electronics, powered items and robots for the duration, and can hit the thrower's own cybernetics and devices `[unverified]`.",
        "min_safe_dist": None,
        "hazards": ["a thrower with cybernetics or powered gear inside the radius is affected `[unverified]`"],
    },
    "flashbang": {
        "parts": ["FlashbangGrenade"],
        "area": "Radius from the part (FlashbangGrenade.DoDetonate calls Flashbang(radius, duration)); blinds creatures that can see it for the duration `[verified in code]`.",
        "min_safe_dist": None,
        "hazards": ["blinds the thrower and companions that see the flash `[unverified]`"],
    },
    "gravity": {
        "parts": ["GravityGrenade"],
        "area": "Radius from the part: the grenade implodes and pulls creatures toward the centre with Force and ForceDropoff (GravityGrenade.DoDetonate: Fall, Accelerate; needs usable reality distortion), `[verified in code]`.",
        "min_safe_dist": None,
        "hazards": ["pulls the thrower and companions in too if they are inside the radius", "fails where reality distortion is stabilized (a normality gas cloud, the Ontological Anchor)"],
    },
    "sunder": {
        "parts": ["SunderGrenade"],
        "area": "Radius 3 from the part: SunderGrenade.DoDetonate calls Disintegrate (it destroys things in the radius; the effect on creatures and walls is unknown), `[verified in code]` for the call, `[unverified]` for the effect.",
        "min_safe_dist": 5,
        "hazards": ["could destroy the thrower's own items or walls nearby `[unverified]`"],
    },
    "time_dilation": {
        "parts": ["TimeDilationGrenade"],
        "area": "A time-dilation field (TimeDilationGrenade.DoDetonate calls ApplyField with Range and Level), `[verified in code]`; the effect is the Time Dilation mutation's: affected creatures act on a different clock `[unverified]`.",
        "min_safe_dist": None,
        "hazards": ["slows or speeds whoever is inside, which may include him `[unverified]`"],
    },
    "phase": {
        "parts": ["PhaseGrenade"],
        "area": "Radius 2: creatures in the adjacent cells are phased out of the world for the duration (PhaseGrenade.DoDetonate: ForceApplyEffect), needs usable reality distortion, `[verified in code]`.",
        "min_safe_dist": 4,
        "hazards": ["a phased creature cannot be hit, and cannot hit; the thrower may be phased too"],
    },
    "deployment": {
        "parts": ["DeploymentGrenade"],
        "area": "Places objects around the thrown cell within Radius: microturrets loyal to the thrower for the fire support grenade, a stasis field for the stasis grenade (DeploymentGrenade: Blueprint, Count, Radius, Duration), `[verified in code]`.",
        "min_safe_dist": None,
        "hazards": ["a stasis field freezes everything inside it, the thrower included if close", "microturrets are loyal to the thrower: an ally"],
    },
}

# What each gas does (the Gas blueprint's parts, `[verified in the XML]`; saves and durations `[unverified]`)
GAS_EFFECTS = {
    "AcidGas": "damages creatures and their equipment with acid each turn (not items lying on the ground: ExcludeTag Item); the wiki lists corrosive gas as seeping through walls but the XML sets no Seeping `[conflict, unverified]`",
    "PoisonGas": "poisons creatures that breathe (a respiration gas) and damages them",
    "SleepGas": "puts creatures that breathe to sleep (involuntary sleep, a save against density)",
    "StunGas": "stuns creatures that breathe",
    "DefoliantGas": "damages live plants, photosynthetic skin, and plant-based equipment and cybernetics; seeps through walls; harmless to most creatures",
    "FungicideGas": "damages live fungi and fungal infections; seeps through walls",
    "NormalityGas": "stabilizes reality: damages entropic and extradimensional creatures and blocks reality-distortion abilities in the cloud (teleporting, phasing, gravity grenades); seeps through walls",
    "GlitterGas": "glittering dust that refracts light (light-based attacks scatter); no damage",
    "Plasma": "damages with plasma and coats in plasma (heat); seeps through walls; creatures take a hundredth of the item damage",
    "ConfusionGas": "confuses creatures that breathe",
}


def kind_of(parts):
    for kind, spec in KINDS.items():
        if any(p in parts for p in spec["parts"]):
            return kind
    return None


def parse(base):
    objs = {}
    for f in glob.glob(os.path.join(base, "*.xml")):
        x = open(f, encoding="utf-8").read()
        for m in re.finditer(r'<object Name="([^"]+)"(?: Inherits="([^"]*)")?[^>]*>(.*?)</object>', x, re.S):
            objs[m.group(1)] = (m.group(2), m.group(3))

    def inherits(n, target):
        seen = set()
        while n and n not in seen:
            if n == target:
                return True
            seen.add(n)
            n = objs.get(n, (None,))[0]
        return False

    out = {}
    for name in sorted(objs):
        if name == "Grenade" or not inherits(name, "Grenade"):
            continue
        inh, body = objs[name]
        parts = {}
        for pn, attrs in re.findall(r'<part Name="([^"]+)"([^>]*)/?>', body):
            parts[pn] = dict(re.findall(r'(\w+)="([^"]*)"', attrs))
        tags = dict((t, v) for t, v in re.findall(r'<tag Name="([^"]+)"(?: Value="([^"]*)")?', body))
        kind = kind_of(parts)
        if not kind:
            continue
        part = next(parts[p] for p in KINDS[kind]["parts"] if p in parts)
        rec = {
            "kind": kind,
            "mark": int(tags.get("Mark", 0) or 0),
            "tier": int(tags.get("Tier", 0) or 0),
            "display": re.sub(r"\{\{[^|]*\||\}\}", "", (re.search(r'DisplayName="([^"]+)"', body) or [None, name])[1]),
            "params": part,
        }
        if kind == "gas":
            rec["gas"] = part.get("GasObject")
            rec["gas_effect"] = GAS_EFFECTS.get(part.get("GasObject"), "")
        out[name] = rec
    return out


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASE
    grenades = parse(base)
    data = {
        "_meta": {
            "purpose": "Every grenade blueprint with its parameters and what each kind does, for the brain's grenade rules (BACKLOG B33). Regenerate with tools/build_grenade_catalog.py.",
            "confidence": "numbers: [verified in the game XML]; per-kind notes carry their own tags",
            "note": "min_safe_dist is the brain's own floor (a distance in tiles from the thrower, a guess where marked), not an engine value; None = no floor needed beyond the engine's radius",
            "count": len(grenades),
        },
        "kinds": {k: {"area": v["area"], "min_safe_dist": v["min_safe_dist"], "hazards": v["hazards"]} for k, v in KINDS.items()},
        "gases": GAS_EFFECTS,
        "grenades": grenades,
    }
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=1, sort_keys=False, ensure_ascii=False)
        f.write("\n")
    print(f"wrote {OUT}: {len(grenades)} grenades")


if __name__ == "__main__":
    main()
