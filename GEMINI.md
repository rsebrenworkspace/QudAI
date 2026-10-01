# QudAI Project Rules & Operating Directives

## The Three-Strikes Rule: Engine Truth Over Heuristic Patches
If an interaction, navigation, combat, or progression issue is not resolved cleanly after **two consecutive attempts** (on the 3rd iteration):
1. **STOP** writing speculative Python heuristics, regex band-aids, or hardcoded state overrides.
2. **GO DIRECTLY TO THE BINARY OR DOCUMENTATION**:
   - Inspect `Assembly-CSharp.dll` using `dnfile` or reflection in `scratch/`.
   - Read the exact method signatures, class hierarchies, and properties of the native engine systems (e.g., `XRL.World.Capabilities.AutoAct`, `XRL.World.AI.Pathfinding`, `XRL.World.SkillFactory`).
   - Check the raw XML blueprints in `CoQ_Data/StreamingAssets/Base/ObjectBlueprints/`.
3. **Integrate Native Engine APIs**: Delegate heavy lifting to Qud's native engine methods (such as `AutoAct.TryFindEdgeStep` and `AutoAct.TryFindPathStep`) rather than re-inventing pathfinding or mechanics from scratch.
