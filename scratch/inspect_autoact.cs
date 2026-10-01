using System;
using System.Reflection;
using XRL.World;

public class InspectAutoAct {
    public static void Main() {
        Type t1 = typeof(AutoAct);
        Console.WriteLine("--- AutoAct Methods ---");
        foreach (var m in t1.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static)) {
            Console.WriteLine(m.Name + " (" + string.Join(", ", Array.ConvertAll(m.GetParameters(), p => p.ParameterType.Name + " " + p.Name)) + ")");
        }

        Type t2 = typeof(FasterDMapAutoexplore);
        Console.WriteLine("\n--- FasterDMapAutoexplore Methods ---");
        foreach (var m in t2.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static)) {
            Console.WriteLine(m.Name + " (" + string.Join(", ", Array.ConvertAll(m.GetParameters(), p => p.ParameterType.Name + " " + p.Name)) + ")");
        }
    }
}
