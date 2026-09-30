import os
import json
import time
import datetime
import requests
import re

LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
MEMORY_DIR = r"D:\QudAI\memory"
RUNS_DIR = os.path.join(MEMORY_DIR, "runs")
WISDOM_FILE = os.path.join(MEMORY_DIR, "ancestral_wisdom.json")
CHRONICLES_DIR = r"D:\QudAI\chronicles"

os.makedirs(RUNS_DIR, exist_ok=True)
os.makedirs(CHRONICLES_DIR, exist_ok=True)


def load_ancestral_wisdom():
    """Load accumulated ancestral lessons learned from past runs."""
    if os.path.exists(WISDOM_FILE):
        try:
            with open(WISDOM_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_ancestral_wisdom(wisdom_list):
    """Save updated ancestral lessons."""
    try:
        with open(WISDOM_FILE, "w", encoding="utf-8") as f:
            json.dump(wisdom_list, f, indent=2)
    except Exception as e:
        print(f"[Chronicler Error] Could not save ancestral wisdom: {e}")


def format_ancestral_memory_for_prompt():
    """Format the top lessons from past deaths to inject into the LLM system prompt."""
    wisdom = load_ancestral_wisdom()
    if not wisdom:
        return "No recorded ancestral memories yet. You are the vanguard of your lineage."

    recent = wisdom[-4:]
    lines = ["ANCESTRAL WISDOM FROM FALLEN FOREBEARS:"]
    for w in recent:
        gen = w.get("generation", 1)
        name = w.get("name", "Unknown")
        cause = w.get("death_reason", "slain")
        zone = w.get("zone", "the wastes")
        lesson = w.get("lesson", "Remain vigilant.")
        lines.append(f"- Gen {gen} ({name}, fell in {zone} to '{cause}'): {lesson}")
    return "\n".join(lines)


def distill_lesson(death_data, recent_actions, model_id=None):
    """Ask LLM to distill a 1-sentence tactical lesson from the demise."""
    name = death_data.get("player_name", "Nomad")
    cause = death_data.get("death_reason", "Unknown")
    zone = death_data.get("zone", "Unknown")
    turns = death_data.get("turns", 0)

    action_summary = " -> ".join([a.get("action", "") for a in recent_actions[-6:]])

    prompt = (
        f"A character named {name} died in Caves of Qud.\n"
        f"Zone: {zone} | Turns Survived: {turns} | Cause of Death: {cause}\n"
        f"Final sequence of actions: {action_summary}\n\n"
        "In ONE single imperative sentence (under 20 words), write a concrete tactical lesson "
        "for future generations to avoid this death (e.g., 'Never sprint into unexplored swamp water when snapjaws have missile weapons.')."
    )

    if model_id:
        try:
            payload = {
                "model": model_id,
                "messages": [
                    {"role": "system", "content": "You are a tactical mentor analyzing roguelike post-mortem telemetry."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 64
            }
            res = requests.post(LM_STUDIO_URL, json=payload, timeout=6.0)
            if res.status_code == 200:
                lesson = res.json()["choices"][0]["message"]["content"].strip()
                lesson = lesson.strip('"\'')
                if lesson:
                    return lesson
        except Exception:
            pass

    return f"Exercise extreme caution against '{cause}' in {zone}."


def generate_obsidian_chronicle(death_data, recent_actions, generation, lesson, model_id=None):
    """Generate a dramatic, lore-rich markdown note for Obsidian."""
    name = death_data.get("player_name", "Nomad")
    level = death_data.get("level", 1)
    turns = death_data.get("turns", 0)
    zone = death_data.get("zone", "The Salty Wastes")
    cause = death_data.get("death_reason", "Perished in the depths")
    category = death_data.get("death_category", "Combat")
    timestamp = death_data.get("timestamp", datetime.datetime.utcnow().isoformat())
    date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    # Clean zone and entity names for Obsidian wikilinks
    clean_zone = re.sub(r"[^\w\s-]", "", zone).strip()
    zone_wikilink = f"[[{clean_zone}]]" if clean_zone else "[[The Salt Marshes]]"

    # Narrative generation via LLM
    story_body = None
    if model_id:
        narrative_prompt = f"""You are the Grand Chronicler of Qud, keeper of the canticles and oral histories of the Sultanate.
Write a poignant, atmospheric, mythic retelling of the life and death of {name}.

DETAILS:
- Generation: {generation}
- Final Level: {level}
- Steps/Turns Taken: {turns}
- Place of Passing: {zone}
- Final Doom: {cause}
- Last Tactical Lesson: {lesson}

REQUIREMENTS:
- Style: Caves of Qud lore tone (archaic, poetic, rust-and-salt mysticism, mentioning watervine, chrome, salt, or ancient machinery).
- Use Obsidian [[wikilinks]] for significant nouns, places, and creatures (e.g. [[Snapjaw]], [[Watervine]], [[Joppa]], [[Eater]], [[Grit Gate]], [[Sultan]]).
- Structure:
  1. An epitaph or canticle verse.
  2. The Tale of their Endeavors (their journey across the salt and rust).
  3. The Final Stand (how the end found them).
  4. The Wisdom Carved in Salt (what the next generation remembers).
- Keep length around 250-400 words. Do not wrap in markdown json blocks; write pure markdown prose."""

        try:
            payload = {
                "model": model_id,
                "messages": [
                    {"role": "system", "content": "You are a poet and mythmaker in the apocalyptic sci-fantasy world of Caves of Qud."},
                    {"role": "user", "content": narrative_prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 1024
            }
            res = requests.post(LM_STUDIO_URL, json=payload, timeout=12.0)
            if res.status_code == 200:
                story_body = res.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"[Chronicler] LLM generation error: {e}")

    # Fallback ballad if LLM is offline or timed out
    if not story_body:
        story_body = f"""### Epitaph

> *"Let the rust claim what salt could not preserve;*  
> *Under the dying gaze of the chrome sky, {name} drank deep of the world's sorrows."*

### The Journey
For {turns} turns through the overgrown thickets and ancient ruins of {zone_wikilink}, **{name}** (Level {level}) walked the path of the pilgrims. Armed with iron, lead, and the flicker of torchlight, they braved the mutant beasts and predatory shadows of the Sultanate.

### The Final Stand
Doom arrived not with trumpet blast, but with the ruthless fury of the salt. In {zone_wikilink}, surrounded by hostile shadows, {name} met their fate: **{cause}**. Their water was spilled back into the dry earth; their gear left to pit and corrode beneath the watchful stars.

### The Wisdom Carved in Salt
> **"{lesson}"**

*May the next sibling carry the flame further.*"""

    # Assemble Obsidian Markdown Document
    safe_name = re.sub(r"[^\w-]", "_", name)
    filename = f"Chronicle_Gen{generation}_{safe_name}_{int(time.time())}.md"
    filepath = os.path.join(CHRONICLES_DIR, filename)

    frontmatter = f"""---
title: "The Chronicle of {name} (Gen {generation})"
generation: {generation}
date_recorded: "{date_str}"
turns_survived: {turns}
level: {level}
resting_place: "{zone}"
cause_of_death: "{cause}"
category: "{category}"
tags:
  - caves-of-qud
  - chronicle
  - ancestral-memory
  - gen-{generation}
---

# The Canticle of {name}, Forebear of Generation {generation}

{story_body}

---
*Transcribed by the QudAI Chronicler on {date_str}*
"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(frontmatter)

    print(f"\n[The Obsidian Chronicler] New chronicle etched into stone: {filepath}\n")
    return filepath


def process_death_event(death_data, recent_actions, active_model_id=None):
    """Full lifecycle: archives run, distills ancestral lesson, and writes Obsidian chronicle."""
    print("\n" + "=" * 55)
    print(" [DEATH DETECTED] The Pilgrim Has Fallen")
    print(f" Name: {death_data.get('player_name')} | Turns: {death_data.get('turns')} | Level: {death_data.get('level')}")
    print(f" Zone: {death_data.get('zone')}")
    print(f" Fate: {death_data.get('death_reason')}")
    print("=" * 55 + "\n")

    # 1. Archive raw run telemetry
    timestamp_str = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    archive_file = os.path.join(RUNS_DIR, f"run_{timestamp_str}.json")
    full_run_record = {
        "telemetry": death_data,
        "recent_actions": recent_actions[-30:],
        "archived_at": datetime.datetime.utcnow().isoformat()
    }
    with open(archive_file, "w", encoding="utf-8") as f:
        json.dump(full_run_record, f, indent=2)

    # 2. Update Ancestral Wisdom
    wisdom = load_ancestral_wisdom()
    generation = len(wisdom) + 1

    lesson = distill_lesson(death_data, recent_actions, active_model_id)

    new_memory_entry = {
        "generation": generation,
        "name": death_data.get("player_name", "Unknown"),
        "level": death_data.get("level", 1),
        "turns": death_data.get("turns", 0),
        "zone": death_data.get("zone", "Unknown"),
        "death_reason": death_data.get("death_reason", "Unknown"),
        "lesson": lesson,
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
    wisdom.append(new_memory_entry)
    save_ancestral_wisdom(wisdom)

    print(f"[Ancestral Wisdom Updated] Gen {generation} Lesson: {lesson}")

    # 3. Generate Obsidian Chronicle
    chronicle_path = generate_obsidian_chronicle(death_data, recent_actions, generation, lesson, active_model_id)

    return {
        "generation": generation,
        "lesson": lesson,
        "chronicle_path": chronicle_path
    }
