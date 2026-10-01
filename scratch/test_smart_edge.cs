using System;
using XRL.World;
using XRL.World.Capabilities;

public class Test {
    public static void Foo(GameObject player, string direction) {
        bool moved = false;
        Cell targetCell = player.CurrentCell != null ? player.CurrentCell.GetCellFromDirection(direction, false) : null;
        if (targetCell != null && targetCell.IsPassable(player, false)) {
            moved = player.Move(direction);
        }
        if (!moved) {
            char edgeChar = direction[0];
            string step;
            if (AutoAct.TryFindEdgeStep(edgeChar, out step) && !string.IsNullOrEmpty(step) && step != ".") {
                moved = player.Move(step);
            }
        }
    }
}
