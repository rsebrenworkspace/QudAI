import dnfile

pe = dnfile.dnPE(r'D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll')
for t in pe.net.mdtables.TypeDef:
    if str(t.TypeName) == 'AutoAct':
        for m in t.MethodList:
            if 'TryFindPathStep' in str(m.row.Name):
                print(f"Found: {m.row.Name}")
                body = pe.net.metadata.get_method_body(m.row.Rva)
                if body:
                    print(f"Code size: {len(body.instructions)}")
                    for instr in body.instructions[:25]:
                        print(f"  {instr.mnemonic} {instr.operand}")
