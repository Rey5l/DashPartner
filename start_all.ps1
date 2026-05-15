# start_all.ps1
# Запуск бота и webhook сервера одновременно

$botPath = "C:\DashPartner"
$venvPython = "$botPath\.venv\Scripts\python.exe"

Write-Host "Запуск DashPartner Bot и Webhook Server..." -ForegroundColor Green
Write-Host ""

# Запуск бота в отдельном окне
Write-Host "Запуск Telegram бота (polling)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$botPath'; .\.venv\Scripts\Activate.ps1; python main.py"
) -WindowStyle Normal

Start-Sleep -Seconds 2

# Запуск webhook сервера в отдельном окне
Write-Host "Запуск Webhook сервера (порт 8000)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$botPath'; .\.venv\Scripts\Activate.ps1; python webhook_server.py"
) -WindowStyle Normal

Write-Host ""
Write-Host "✅ Сервисы запущены!" -ForegroundColor Green
Write-Host ""
Write-Host "Telegram Bot: работает в режиме polling" -ForegroundColor Yellow
Write-Host "Webhook Server: http://81.29.146.68:8000" -ForegroundColor Yellow
Write-Host ""
Write-Host "Webhook endpoints:" -ForegroundColor White
Write-Host "  Flyer:  http://81.29.146.68:8000/webhook/flyer" -ForegroundColor Gray
Write-Host "  TGrass: http://81.29.146.68:8000/webhook/tgrass" -ForegroundColor Gray
Write-Host "  Health: http://81.29.146.68:8000/health" -ForegroundColor Gray
Write-Host ""
Write-Host "Для остановки закройте оба окна PowerShell" -ForegroundColor Red
