$managedDir = "D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed"
[System.IO.Directory]::SetCurrentDirectory($managedDir)

[System.AppDomain]::CurrentDomain.add_AssemblyResolve({
    param($sender, $args)
    $name = ($args.Name -split ',')[0]
    $path = Join-Path $managedDir "$name.dll"
    if (Test-Path $path) {
        return [System.Reflection.Assembly]::LoadFrom($path)
    }
    return $null
})

$asm = [System.Reflection.Assembly]::LoadFrom((Join-Path $managedDir "Assembly-CSharp.dll"))
$goType = $asm.GetType("XRL.World.GameObject")
$methods = $goType.GetMethods([System.Reflection.BindingFlags]"Public,NonPublic,Instance,Static") | Where-Object { 
    $_.Name -match "^(BuyStat|GetStat|UseMP|UseAP|Stat|LevelUp)$"
}
foreach ($m in $methods) {
    Write-Output ($m.ReturnType.Name + " " + $m.Name + "(" + (($m.GetParameters() | ForEach-Object { $_.ParameterType.Name + " " + $_.Name }) -join ", ") + ")")
}
