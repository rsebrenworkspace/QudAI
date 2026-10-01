$managedDir = "D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed"
Get-ChildItem -Path $managedDir -Filter "*.dll" | ForEach-Object {
    try { [System.Reflection.Assembly]::LoadFrom($_.FullName) | Out-Null } catch { }
}

$asm = [System.Reflection.Assembly]::LoadFrom("$managedDir\Assembly-CSharp.dll")
$types = try { $asm.GetTypes() } catch [System.Reflection.ReflectionTypeLoadException] { $_.Exception.Types }

$filtered = $types | Where-Object { $_ -ne $null -and ($_.Name -eq "Stomach" -or $_.Name -eq "Campfire" -or $_.Name -match "Butcher" -or $_.Name -match "Cooking" -or $_.Name -eq "Food") }
foreach ($t in $filtered) {
    Write-Host "TYPE: $($t.FullName)"
    $props = $t.GetProperties() | Select-Object -ExpandProperty Name
    Write-Host "  PROPERTIES: $($props -join ', ')"
    $methods = $t.GetMethods([System.Reflection.BindingFlags]"Public,NonPublic,Instance,Static") | ForEach-Object { $_.Name }
    Write-Host "  METHODS: $(($methods | Select-Object -Unique | Select-Object -First 20) -join ', ')"
}
