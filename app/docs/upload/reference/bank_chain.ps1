$ErrorActionPreference = 'Stop'
$S = 'C:\Users\DWP2\AppData\Local\Temp\claude\c--Users-DWP2-Desktop-Project-walkthrough\e1e2f8a1-5b17-462a-bbe8-01925d989674\scratchpad\bankreader'
$L = 'C:\Users\DWP2\AppData\Local\Temp\claude\c--Users-DWP2-Desktop-Project-walkthrough\e1e2f8a1-5b17-462a-bbe8-01925d989674\scratchpad\p0\tools\libredwg'
$P = 'C:\Users\DWP2\Desktop\Project walkthrough'
$env:PYTHONIOENCODING = 'utf-8'
$env:OPENINGS_DATA = "$S\proj\detector"
Remove-Item "$S\proj\detector\bank1\*", "$S\proj\detector\bank2\*" -Force -Confirm:$false
$runs = @(
  @('dwg2dxf L1', "$L\dwg2dxf.exe", @('-y', '-o', "`"$S\proj\detector\bank1\plan.dxf`"", "`"$P\I1201 - LEVEL 1 GENERAL ARRANGEMENT.dwg`"")),
  @('dwg2dxf L2', "$L\dwg2dxf.exe", @('-y', '-o', "`"$S\proj\detector\bank2\plan.dxf`"", "`"$P\I1202 - LEVEL 2 GENERAL ARRANGEMENT.dwg`"")),
  @('prims L1', 'python', @('-B', 'detector\tools\prims.py', 'bank1')),
  @('prims L2', 'python', @('-B', 'detector\tools\prims.py', 'bank2')),
  @('detector L1', 'python', @('-B', 'detector\openings.py', "`"$S\derivedB_bank1.json`"", 'bank_test\src\detector_out\openings_L1.json')),
  @('detector L2', 'python', @('-B', 'detector\openings.py', "`"$S\derivedB_bank2.json`"", 'bank_test\src\detector_out\openings_L2.json')),
  @('build', 'python', @('-B', 'bank_test\src\build_model.py')),
  @('maxscript', 'python', @('-B', 'bank_test\src\generate_maxscript.py', "`"$S\chain.ms`""))
)
$total = [Diagnostics.Stopwatch]::StartNew()
foreach ($r in $runs) {
  $sw = [Diagnostics.Stopwatch]::StartNew()
  $p = Start-Process -FilePath $r[1] -ArgumentList $r[2] -WorkingDirectory "$S\proj" -PassThru -NoNewWindow -Wait -RedirectStandardOutput "$S\chain_out.txt" -RedirectStandardError "$S\chain_err.txt"
  $sw.Stop()
  "{0}: {1:N2} s" -f $r[0], $sw.Elapsed.TotalSeconds
}
$total.Stop()
"total: {0:N1} s" -f $total.Elapsed.TotalSeconds
