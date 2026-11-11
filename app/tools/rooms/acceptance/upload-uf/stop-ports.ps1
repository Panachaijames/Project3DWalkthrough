# Final check (UF): stops whatever listens on the given ports and the app's dev processes (concurrently, vite, uvicorn
# with --reload and its worker), then lists what is left. Usage: powershell -NoProfile -File stop-ports.ps1 5710 8710
param([int[]]$Ports)
$pids = @()
foreach ($p in $Ports) {
  $pids += Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess
}
$app = 'Project walkthrough'
$procs = Get-CimInstance Win32_Process | Where-Object {
  $_.CommandLine -and $_.CommandLine -like "*$app*" -and (
    $_.CommandLine -like '*concurrently*' -or $_.CommandLine -like '*vite*' -or $_.CommandLine -like '*uvicorn*' -or
    $_.CommandLine -like '*run-api.mjs*' -or $_.CommandLine -like '*npm-cli.js*run dev*' -or $_.CommandLine -like '*walkthrough_api*')
}
$pids += $procs | Select-Object -ExpandProperty ProcessId
# uvicorn --reload: the server is a child of the reloader (multiprocessing spawn); take children of every pid too
$all = Get-CimInstance Win32_Process
$more = @()
foreach ($id in $pids) { $more += $all | Where-Object { $_.ParentProcessId -eq $id } | Select-Object -ExpandProperty ProcessId }
$pids = ($pids + $more) | Where-Object { $_ -and $_ -ne $PID } | Sort-Object -Unique
foreach ($id in $pids) {
  try { Stop-Process -Id $id -Force -ErrorAction Stop; "stopped $id" } catch { "gone $id" }
}
Start-Sleep -Seconds 2
foreach ($p in $Ports) {
  $left = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
  if ($left) { "port $p still listening: $($left.OwningProcess)" } else { "port $p free" }
}
