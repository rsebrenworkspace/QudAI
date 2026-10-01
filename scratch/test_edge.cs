
using System;
using XRL.World;
using XRL.World.Capabilities;
public class Test {
    public static void Foo(char dir) {
        string step;
        bool b = AutoAct.TryFindEdgeStep(dir, out step);
    }
}
