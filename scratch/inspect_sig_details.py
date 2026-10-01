import dnfile

pe = dnfile.dnPE(r"D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll")

for row in pe.net.mdtables.TypeDef:
    if str(row.TypeName) == "GameObject" and str(row.TypeNamespace) == "XRL.World":
        for m in row.MethodList:
            m_name = str(m.row.Name)
            if m_name in ("RemoveOne", "SplitStack", "SplitFromStack"):
                # decode signature
                sig = list(m.row.Signature.value)
                call_conv = sig[0]
                param_count = sig[1]
                print(f"GameObject.{m_name}: param_count={param_count}, sig={sig}")
                for p in getattr(m, 'ParamList', []):
                    try: print(f"    Param: {p.row.Name}")
                    except: pass
