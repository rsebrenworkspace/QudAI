
using System;
using XRL.World;
using XRL.World.Capabilities;
public class Test {
    public static void Foo(Cell c) {
        string step;
        bool b = AutoAct.TryFindPathStep(c, out step);
    }
}
