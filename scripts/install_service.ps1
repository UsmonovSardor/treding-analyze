# MT5 Trade Journal — Windows Task Scheduler orqali avto-ishga tushirish.
# Kompyuter yonganda (login) xizmat o'zi ishga tushadi.
#
# Ishlatish (PowerShell, Administrator sifatida):
#   .\scripts\install_service.ps1
#
# O'chirish:
#   Unregister-ScheduledTask -TaskName "MT5TradeJournal" -Confirm:$false

$ErrorActionPreference = "Stop"

# Loyiha ildizi (bu skript scripts/ ichida)
$ProjectRoot = Split-Path -Parent $PSScriptRoot

# Python topish (venv bo'lsa uni, aks holda tizim python)
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    $Python = $VenvPython
} else {
    $Python = (Get-Command python).Source
}

Write-Host "Loyiha:  $ProjectRoot"
Write-Host "Python:  $Python"

$Action = New-ScheduledTaskAction -Execute $Python `
    -Argument "-m src.main" -WorkingDirectory $ProjectRoot

# Login bo'lganda ishga tushadi
$Trigger = New-ScheduledTaskTrigger -AtLogOn

# Uzluksiz ishlashi uchun sozlamalar
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero)

Register-ScheduledTask -TaskName "MT5TradeJournal" `
    -Action $Action -Trigger $Trigger -Settings $Settings `
    -Description "MT5 savdolarini Google Sheets/Excel jurnaliga avtomatik yozadi" `
    -Force

Write-Host "`nTayyor! 'MT5TradeJournal' vazifasi ro'yxatga olindi." -ForegroundColor Green
Write-Host "Hozir ishga tushirish uchun:  Start-ScheduledTask -TaskName MT5TradeJournal"
