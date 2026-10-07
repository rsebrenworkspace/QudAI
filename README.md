# Caves of Qud Autonomous Agent (QudAI)

An autonomous, streaming-ready artificial intelligence agent that plays **Caves of Qud** live without human intervention. Built on a hierarchical architecture combining headless C# Harmony engine hooks, zero-latency deterministic safety nets, local LLM tactical reasoning, and interactive Twitch chat audience participation.

---

## Key Features

- **Hierarchical Decision Engine**:
  - **Phase A (Deterministic Safe Mode)**: Instant 0ms responses for resting, exploring unknown ground, ammo top-offs, and safe leveling.
  - **Phase B (Tactical LLM Reasoning)**: High-level combat decisions powered by local LLMs (via LM Studio / OpenAI-compatible API) utilizing 5x5 spatial grids, entity radars, status effects, and character doctrines.
  - **Phase C (Multi-Class Deterministic Fallback)**: Class-tailored safety nets ensuring survival if the LLM times out or is offline.
- **Multi-Class Archetypes & Combat Doctrines**:
  - **Issachar Rifle Nomad**: Long-range sniper, sprint kiting, Freezing Ray crowd-control.
  - **Marauder Berserker**: Frontline gap-closer, Charge, Dismember, Cleave, high-penetration trades.
  - **Akimbo Gunslinger**: Mid-range pistol volleys, Chain Fire, Disarming Shot.
  - **Esper Mindflayer**: Long-range psychic nukes (Sunder Mind, Cryokinesis), emergency Force Bubble / Teleportation.
  - **Praetorian Juggernaut**: High-AV face-tanking, Shield Block, Shield Slam knockdown.
- **Headless Harmony Engine Integration**:
  - Direct memory inspection and headless turn execution (`player.UseEnergy(1000)`).
  - Pinpoint missile targeting overriding Qud's default 90-degree fan spray.
  - Auto-direction selection patches for UI pickers (`PickDirection`, `PickTarget`, `PickItem`).
  - Headless attribute, skill, and mutation point allocation.
- **Interactive Twitch Chat Voting**:
  - Viewers vote live on character progression via IRC: `!vote Toughness`, `!vote Agility`, `!vote Rifles`.
  - Consensus votes are automatically executed when the character is in safe resting/explore phases.
- **Ancestral Memory (The Death Chronicler)**:
  - Permadeath events are analyzed post-mortem by the LLM.
  - Tactical aphorisms are distilled into long-term memory and injected into future generations' prompts.

---

## Quickstart Guide

### 1. Prerequisites
- **Caves of Qud** (Steam / GOG, current modern branch)
- **Python 3.10+**
- **LM Studio** (or any local LLM server running on `http://localhost:1234`) with a vision/instruct model loaded (e.g. Qwen 2.5 / Qwen 3 VL / Llama 3)
- Python packages:
  ```powershell
  pip install requests
  ```

### 2. Install the Caves of Qud Mod
Deploy the `QudAIBrain` Harmony mod to Caves of Qud's local mod directory:
```powershell
python sync_mod.py deploy
```
Launch *Caves of Qud*, navigate to **Mod Configuration**, and ensure **QudAIBrain** is checked/enabled.

### 3. Configure Twitch Bot (Optional)
If streaming to Twitch:
1. Copy `twitch_config.example.json` to `twitch_config.json`.
2. Fill in your Twitch channel name, bot username, and OAuth token.
3. Set `"enabled": true`.

### 4. Run the Autonomous Agent
1. Launch *Caves of Qud* and load a character in-game.
2. In a terminal, run:
   ```powershell
   python brain.py
   ```
3. Press **Enter** in the console window to toggle autonomous AI control on/off.

---

## Verification & Testing
Run the 74-scenario multi-class verification test suite to validate all archetypes, fallback matrices, line-of-fire raytracing, pet immunity, staircase delving, skill trees, border navigation, and survival routines:
```powershell
python dry_run.py
```

---

## Project Documentation
- [ENGINE_INTERNALS.md](ENGINE_INTERNALS.md): Definitive reverse-engineering manual, Unity/.NET Standard 2.1 architecture, headless UI picker patches, MinEvent dispatches, companion Rule 0, and survival mechanics.
- [PROJECT_HISTORY.md](PROJECT_HISTORY.md): In-depth chronicle of every project iteration, technical breakdowns, decompiled engine mechanics, and future milestone roadmaps.
