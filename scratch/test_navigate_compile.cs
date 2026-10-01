using System;
using XRL.World;
using XRL.World.Capabilities;

public class Test {
    public static void Foo(GameObject player, string act) {
        if (act.StartsWith("NAVIGATE_ZONE_EXIT:")) {
            string dirStr = act.Substring(19).Trim().ToUpper();
            char edgeChar = !string.IsNullOrEmpty(dirStr) ? dirStr[0] : 'E';
            string step;
            bool ok = AutoAct.TryFindEdgeStep(edgeChar, out step);
        }
        if (act.StartsWith("NAVIGATE_TO:")) {
            string[] parts = act.Substring(12).Split(',');
            int tx = int.Parse(parts[0]);
            int ty = int.Parse(parts[1]);
            Cell targetCell = player.CurrentCell.ParentZone.GetCell(tx, ty);
            string step;
            bool ok = AutoAct.TryFindPathStep(targetCell, out step);
        }
    }
}
