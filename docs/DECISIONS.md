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
| A preference for dry land over swimming water (a swim term in every movement tie-break, and a router cost of 3 per swimming step) | Dropped by the human on 2026-10-12 for "cleaner, smoother movement until an issue makes us rethink it": the only measured cost of swimming is the engine's move-speed penalty (ENGINE_INTERNALS 14.40), and the repeated-tile movement on lakes came from engine routes that cannot see water, which the router fixed. Rethink if swimming turns out to cost items, a chase, or real time; the retreat rule can still step into water and a swimmer is slower than a land chaser `[inferred]` | issue 168 |
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

## Reversing the decisions of 2026-10-12 (the water, retreat and safety changes)

Each row says what was decided, why, what evidence should make us reverse it, and the cheapest way back. Commits are on `main`; `git revert <hash>` undoes a whole change but also its tests, so the notes name the tests that moved. Always run the checks in AGENTS.md section 3 after a reversal, and note the reversal in `docs/HANDOFF.md` and here. Do not reverse by deleting code; use the knob where there is one. Revert newest first (169 before 168, 168 before 163): the later commits rewrite the lines the earlier ones touched, and an out-of-order revert conflicts.

| Decision (issue, commit) | Why | Reverse it when | The knob (cheapest) | The full revert |
|---|---|---|---|---|
| **No water bias in movement** (168, `9394647`; human: "cleaner, smoother movement until an issue makes us rethink it") | The only measured cost of swimming is the engine's move-speed penalty (ENGINE_INTERNALS 14.40); the out-and-back legs came from dry-only engine routes, not from the water term | A capture shows swimming costs items, a lost chase (the retreat rule steps into water and a swimmer is slower than a land chaser `[inferred]`), or `move_speed` shows a large penalty (ENGINE_INTERNALS 14.40 reads swimming as HALF speed for every character; the human knew this on 2026-10-12 and kept the bias out, HANDOFF issue 171: so the trigger is a swim that costs a chase or a fight, not the number itself) | In `AIBrainPart.cs` `RouteSearch`, change the step cost `res.Dist[cur] + 1` to `res.Dist[cur] + (swim ? 3 : 1)` (the old cost; `swim` is already computed there). In `brain.py` put `1 if is_swim_move(m, surroundings) else 0` back as the LAST element of the sort keys of `get_best_move_towards`, the frontier scouting sort, the fallback `ranked` sort, the Loop Breaker `open_escapes` sort and `dist_away_from_cycle` | `git revert 9394647` (Python, C#, Test 179; the `move_speed` export goes with it, which loses the measurement: keep that part) |
| **Shortest-route navigation** (169, `d0ad0b5`) | The engine's edge and path steps are dry-only and wind round lakes (57 of 124 east-exit steps went away from the exit) | The router sends him through a door, a trap or a creature the engine would have avoided; or exit walks get slower | `SwimShortcutMinSaving` in `AIBrainPart.cs` (6): raise it to 1000 and the engine decides everywhere except when there is no dry route at all | `git revert d0ad0b5` (frontier targets go back to the engine-checked, straight-line list; Test 180 goes away, Test 179's router text check must be put back to `dist[cur] + 1`) |
| **Swim-capable router, oscillation override, swim-reachable edges** (163, `ddc1516`) | The engine's pathfinders do not swim (ENGINE_INTERNALS 14.38) | `reachable_edges` lists an edge he cannot actually reach | `SwimEdgeReachableCached` call in the `reachable_edges` export; the override threshold `oscSeen >= 2` | `git revert ddc1516` (Test 175) |
| **Retreat from equal-speed melee-only Impossible enemies, and no opening shots** (167, `312fee5`; human: "build 1 and 2") | A level 1 Dream Tortoise died to a level 13 wedge it shot at and walked toward (Gen 42) | He avoids fights he could win and progress stalls (override rate and XP per 1000 turns, see the calibration note below), or he is chased into dead ends | `RETREAT_EQUAL_MIN_DIST` in `brain.py`: set to 999 to switch the equal-speed retreat off; delete the `decision = veto_engage_unwinnable(...)` line in `query_decision` to switch the veto off | `git revert 312fee5` (Tests 167, 168, 169 go back to "equal speed means nothing"; Test 178 goes away) |
| **Tighten Carapace hidden; self-ability repeat guard** (166, `b6bfb1d`) | Tighten is a stance the next action ends (ENGINE_INTERNALS 14.39); the model used it 61 times in a row | A build wants to wait in a stance (a camping or defensive build); or the guard replaces a legitimate repeat | `data/ability_families.json`: `tighten` `auto_use` true shows it again; `ABILITY_REPEAT_MAX` in `brain.py` (2) loosens the guard | `git revert b6bfb1d` (Test 177, Test 174 text) |
| **Exit written off on the wrong edge; adjacent exit crossed** (161, `99016d2`) | A Dream Tortoise paced the north shore for 149 turns heading for a south exit | He crosses into a zone he should not (the adjacent exit is taken only after an oscillation is detected) | `near_exit_border` in `brain.py` (the old check was "within 1 of ANY edge") | `git revert 99016d2` (Test 173) |
| **Release Sleep Gas wired** (162, `99016d2`) | Command name read from the live export | The model uses it with a companion near | `data/ability_families.json`: `sleep_gas` `auto_use` false hides it | part of `99016d2` |

| **Bow is an optional opener for melee builds** (170, this commit; human: "most combats were initiated using the bow ... until the character ran out of ammo") | 14 of 31 fights opened with a missile and all 70 arrows were gone by row 3263; arrows cannot be recovered (ENGINE_INTERNALS 14.41) | The build wastes chances to soften tough enemies, or a fight is lost with the bow idle | `BOW_RESERVE`, `BOW_MIN_DIST` and `BOW_WORTH_DIFFICULTIES` in `brain.py`: set `BOW_RESERVE` to 0 and `BOW_MIN_DIST` to 1 to offer the bow almost as before | `git revert` the commit (Test 181 goes away) |

**Calibration note (human, 2026-10-12):** the aim is an agent that is competent and tries to win a run, not one that optimises for safety (every added rule is a layer of avoidance; about a dozen deterministic layers run before the model decides). The test for any new safety rule: a death or a loop as evidence, a budget or timeout, and a way to see how often it fires. The generation report (HANDOFF issue 172) now gives the progress side (median level and turns per life, repeated causes); the override-rate side (the share of turns each safety rule decided) is not built yet. Build it before adding more rules.
