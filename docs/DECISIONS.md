# QudAI: Decisions and Dead Ends

> Check here before trying an approach. Add an entry when you decide something non-obvious or when an approach fails.
> Each entry: **status**, **why**, **evidence/reference** (iteration numbers refer to `PROJECT_HISTORY.md`).
> Statuses: `adopted`, `proposed`, `reverted`, `rejected`.

## Decisions

### D-001: Hybrid hierarchical decision engine (adopted)
Deterministic safe mode (Phase A), local LLM for combat tactics (Phase B), deterministic class fallbacks (Phase C).
**Why:** LLM latency (2-4 s/turn) is too slow for exploration; pure heuristics are too weak for combat. Fallbacks keep the
agent alive when the LLM is slow, offline, or returns invalid output. *Ref: Iteration 0.*

### D-002: C# Harmony mod + file-based JSON IPC (adopted)
**Why:** Screen scraping failed (see Dead ends). Direct engine access gives exact state and headless execution.
**Trade-off:** File IPC is non-atomic and has no turn id. Known weakness; see HANDOFF issues 3 and 4. *Ref: Iteration 2.*

### D-003: Delegate navigation to native engine pathfinders (adopted)
Use `AutoAct.FindAutoexploreStep`, `TryFindPathStep`, `TryFindEdgeStep`. Never hand-roll 1-step vector movement.
**Why:** Hand-written heuristics produced a long series of oscillation bugs (Iterations 10, 11, 15, 24, 25, 27, 37, 38, 39, 40).
*Ref: AGENTS.md R1, R6.*

### D-004: Native autoexplore must not exit zones (adopted)
`FindAutoexploreStep(false, ...)`. **Why:** with `true` it walked to zone exits and bypassed the driver's water-traversal logic. *Ref: Iteration 18.*

### D-005: Combat is exempt from the exploration loop breaker (adopted)
**Why:** the breaker once overwrote ability casts with `NAVIGATE_TO_CELL` mid-fight. *Ref: Iteration 30.*
**Caveat:** this exemption also hides combat-action no-op loops (HANDOFF issue 1).

### D-006: Organic random exit selection per zone, cached (adopted, needs seeding)
Random among novel exits, committed for the zone. **Why:** runs should not feel on-rails for viewers. **Needs:** seed `random`
per run and log the seed so failures reproduce. *Ref: Iteration 28.*

### D-007: C# owns `zone_fully_explored` (proposed)
**Why:** the field has been set or overridden from both sides and flip-flopped (Iterations 26, 37, 38, 40). The engine can see
ground truth; Python should read it. *Ref: AGENTS.md R2, ARCHITECTURE 6b.*

### D-008: Engine exports legal purchases; Python picks from the list (proposed)
For skills, mutations, and attributes. **Why:** Python mirrors of engine rules drifted repeatedly (mutation cap, Agi 21 requirement,
the 4-MP purchase modal, 0-cost powers). Replaces `SKILL_DATABASE`. *Ref: Iterations 20, 21, 22.*

### D-009: Model chooses intents, deterministic code executes movement (proposed)
**Why:** per-tile LLM movement is too slow on a 16 GB local model and its loops would be hard to diagnose. Intents ("explore this zone",
"take the north exit", "delve", "rest") give the model steering without per-step conflicts.

### D-010: Single movement arbiter (proposed)
Autoexplore owns movement until it reports done/stuck; other behaviors act only as explicit interrupts (combat, hunger, pending
level-up) and then hand control back.

### D-011: Lock the build template per character (proposed)
**Why:** `detect_build()` runs on live state every turn, so gaining a mutation can switch archetype mid-run.

### D-012: Failure memory as structured lessons with retrieval (proposed)
Store killer, depth, level, calling, HP trajectory, ability states, nearby enemies, plus the aphorism; retrieve the few relevant lessons
per fight instead of the last four. **Why:** the current 20-word aphorisms from action names carry little information and will not scale
in a small context window.

## Dead ends (do not retry without new evidence)

| Approach | Why it failed | Ref |
| Opening a chest by firing the "Open" event (what the engine's autoexplore does) | `Container.AttemptOpen` shows the trade screen for the player; the mod cannot answer that screen, so the run would hang. Containers are emptied directly from their `Inventory` part instead (T-1.34). `[verified in code]` | R-2 |
|---|---|---|
| OS screen capture + OCR + simulated keypresses | OCR >600 ms/frame, misread tiles, modal popups stole focus, dropped keys | Iter 1 |
| Targeting every visible entity as an "unexplored frontier" | Hundreds of harmless objects; character tried to step on all of them (800+ turns in one zone) | Iter 19 |
| Compile-checking the mod locally with the game's Roslyn (`Microsoft.CodeAnalysis*.dll` in `CoQ_Data/Managed`) from Windows PowerShell 5.1 | Those assemblies target Unity's Mono; PowerShell throws `Could not load type System.Span` (and a StackOverflow without a resolve guard). No .NET SDK is installed. Verify C# by launching Qud and reading `build_log.txt` ("Success :)") plus the braces check. | T-1.12 |
| Python deciding a zone is "explored" from its own signals (autoexplore stuck, oscillation, a failed `NAVIGATE_TO_CELL`) and remembering it in `EXPLORED_ZONE_SET` for the session | Five writers; one stalled autoexplore (e.g. a lake) made the brain claim "Zone fully explored" with 1251 cells unrevealed and never explore that zone again; also read the *new* zone's flag when leaving the old one. Iterations 38/40 reverted each other for the same reason. Only the engine's flag is remembered now. | HANDOFF 17/29, T-1.15 |
| Camping and cooking to relieve hunger (`MAKE_CAMP` + `COOK_MEAL` tried before `EAT`) | `COOK_MEAL` called `ClearHunger()` even with no ingredient (a free meal) and otherwise did nothing `EAT` does not, for 2+ extra turns and a fire risk. Removed from hunger relief in T-1.13; the commands remain for later cooking work. | HANDOFF 34, T-1.13 |
| Remembering companions **by display name** (C# `RegisteredCompanionNames`, Python `CHARMED_COMPANION_NAMES`) | One Proselytize on a baboon made every baboon a "companion": hostiles dropped out of `is_enemy`, threats and `is_in_combat`, the agent rested at 6 HP and 2 HP next to a biting baboon, and offensive abilities aborted. Use engine truth (`is_companion`, `[COMPANION:]` tags, coordinates, IDs after a real engine check). | 2026-10-04 run, T-1.10 |
| 1-step Euclidean / Chebyshev movement toward a target | Ping-pongs along fences, walls, shorelines, canyon cliffs | Iter 10, 24, 25, 27, 39 |
| Loop detection threshold `count >= 3` in a window of 10 | Mathematically unreachable for a 5-tile cycle; replaced by window 24 + unique-position entropy | Iter 15 |
| Treating deep water as impassable | Rivers/lakes trapped the character on the shoreline | Iter 16, 17 |
| Forcing `zone_fully_explored = False` on the surface when `unexplored_cells > 35` | Almost every surface zone has permanent fog (e.g. Joppa); zones never completed. Added in Iter 38, reverted in Iter 40 | Iter 38, 40 |
| Treating the unexplored-cell centroid as a travel target | Can be inside a wall; distance-1 dead zone made the character bounce | Iter 20, 27 |
| `ATTACK_WALL` burrowing in towns | Vandalized huts; mistook interiors for enclosed pockets | Iter 30 |
| Matching pits via substring `"pit"` | Matched "seed-spitting vine"; overwrote real stairs | Iter 34 |
| Setting `isZoneFullyExplored = true` on any single null autoexplore step | New zones return null on turn 1 (DMap not seeded); character left zones immediately | Iter 26 |
| `GameObject.SetProperty`, `pStomach` | Do not exist in current Qud; compile errors | Iter 11, 15 |
| Opening campfire/camp UI programmatically | Opens modals that stall headless play; placing the object and applying effects directly works | Iter 15 |
