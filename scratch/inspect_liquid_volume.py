import dnfile

pe = dnfile.dnPE(r'D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll')
# Let's inspect LiquidVolume or Cell.HasSwimmingDepthLiquid
for r in pe.net.mdtables.TypeDef:
    if str(r.TypeNamespace) == 'XRL.World' and str(r.TypeName) == 'Cell':
        for m in r.MethodList:
            if str(m.row.Name) in ['HasSwimmingDepthLiquid', 'GetSwimmingDepthLiquid', 'GetOpenLiquidVolume', 'HasWadingDepthLiquid']:
                print(str(m.row.Name), hex(m.row.Rva))

    if str(r.TypeName) == 'LiquidVolume':
        print('Found LiquidVolume in', str(r.TypeNamespace))
        for m in r.MethodList:
            name = str(m.row.Name)
            if any(k in name.lower() for k in ['swim', 'wade', 'depth', 'volume', 'amount']):
                print('  LiquidVolume method:', name)
