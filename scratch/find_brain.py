import subprocess

cmd = ['powershell', '-NoProfile', '-Command', "Get-CimInstance Win32_Process | Where-Object { $_.Name -like '*python*' } | Select-Object ProcessId, CommandLine | Format-List"]
res = subprocess.run(cmd, capture_output=True, text=True, errors='ignore')
print(res.stdout)
