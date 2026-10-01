using System;
using System.Reflection;

public class FindDeclaringType {
    public static void Main() {
        Assembly asm = Assembly.LoadFrom(@"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll");
        foreach (Type t in asm.GetTypes()) {
            try {
                foreach (MethodInfo m in t.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static | BindingFlags.Instance)) {
                    if (m.Name == "SetAutoexploreSuppression" || m.Name == "FindAutoexploreStep") {
                        Console.WriteLine(t.FullName + " :: " + m.Name);
                    }
                }
            } catch {}
        }
    }
}
