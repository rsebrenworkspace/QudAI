# Compile-checks mod/QudAIBrain/AIBrainPart.cs against the game's own DLLs. Emits to memory, writes nothing.
# Needs PowerShell 7 (pwsh): it ships Roslyn 5 and runs on modern .NET. Windows PowerShell 5.1 cannot load Roslyn (System.Span).
# Language level is C# 9 because the game's own compiler (Managed\Microsoft.CodeAnalysis 3.11) stops there: code that passes here but needs a newer level would fail at game launch.
#   pwsh -NoProfile -File tools\compile_check.ps1 [-Source path\to\file.cs]
param([string]$Source = (Join-Path $PSScriptRoot "..\mod\QudAIBrain\AIBrainPart.cs"))
$managed = "D:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed"
$text = [System.IO.File]::ReadAllText((Resolve-Path $Source))
$opts = [Microsoft.CodeAnalysis.CSharp.CSharpParseOptions]::new([Microsoft.CodeAnalysis.CSharp.LanguageVersion]::CSharp9)
$tree = [Microsoft.CodeAnalysis.CSharp.CSharpSyntaxTree]::ParseText($text, $opts)
$trees = [System.Collections.Generic.List[Microsoft.CodeAnalysis.SyntaxTree]]::new()
$trees.Add($tree)
$refs = [System.Collections.Generic.List[Microsoft.CodeAnalysis.MetadataReference]]::new()
foreach ($f in Get-ChildItem $managed -Filter *.dll) {
    try { [void][System.Reflection.AssemblyName]::GetAssemblyName($f.FullName); $refs.Add([Microsoft.CodeAnalysis.MetadataReference]::CreateFromFile($f.FullName)) } catch {}
}
$co = [Microsoft.CodeAnalysis.CSharp.CSharpCompilationOptions]::new([Microsoft.CodeAnalysis.OutputKind]::DynamicallyLinkedLibrary)
$comp = [Microsoft.CodeAnalysis.CSharp.CSharpCompilation]::Create("QudAIBrain_check", $trees, $refs, $co)
$ms = [System.IO.MemoryStream]::new()
$res = $comp.Emit($ms)
$errs = @($res.Diagnostics | Where-Object { $_.Severity -eq 'Error' })
foreach ($d in $errs) { Write-Output ($d.ToString()) }
if ($res.Success) { Write-Output "COMPILE OK ($($ms.Length) bytes)" } else { Write-Output "COMPILE FAILED: $($errs.Count) error(s)"; exit 1 }
