$ErrorActionPreference = 'Stop'

$workdir = 'C:\Users\User\Desktop\Thohago_branding'
$env:PYTHONPATH = 'C:\Users\User\Desktop\Thohago_branding\src'

Set-Location $workdir
python -m thohago bot
