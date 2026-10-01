$asm = [System.Reflection.Assembly]::LoadFrom('D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed\Assembly-CSharp.dll')
$type = $asm.GetType('XRL.World.GameObject')
$methods = $type.GetMethods() | Where-Object { $_.Name -eq 'Die' }
foreach ($m in $methods) {
    $p = ($m.GetParameters() | ForEach-Object { $_.ParameterType.Name + ' ' + $_.Name }) -join ', '
    Write-Host "Die($p)"
}
