---
description: Enforce binary and engine inspection after 2 failed attempts rather than adding heuristic patches
trigger: always_on
---

# Three Strikes Rule: Binary & Engine Truth First

When debugging or implementing Caves of Qud AI behaviors:
1. If a problem persists across two attempts, the third attempt **MUST NOT** be another speculative heuristic or local override in Python.
2. Directly decompile, reflect, or inspect the official game binary (`Assembly-CSharp.dll`) and streaming assets (`ObjectBlueprints/*.xml`).
3. Leverage Caves of Qud's built-in engine APIs (e.g. `AutoAct.TryFindEdgeStep`, `AutoAct.TryFindPathStep`, `FasterDMapAutoexplore`, `SkillFactory`, `GameObject.Die`) instead of simulating game physics or pathfinding in python heuristics.
