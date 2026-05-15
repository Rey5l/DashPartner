# Генерация самоподписанного SSL сертификата для Telegram Webhook

$certPath = "C:\DashPartner\cert.pem"
$keyPath = "C:\DashPartner\key.pem"
$ip = "81.29.146.68"

Write-Host "Генерация SSL сертификата для IP: $ip"

# Проверка наличия OpenSSL
$opensslPath = "C:\Program Files\Git\usr\bin\openssl.exe"

if (-not (Test-Path $opensslPath)) {
    Write-Host "OpenSSL не найден. Установите Git для Windows или OpenSSL."
    Write-Host "Скачать Git: https://git-scm.com/download/win"
    exit 1
}

# Генерация приватного ключа
& $opensslPath genrsa -out $keyPath 2048

# Генерация самоподписанного сертификата
& $opensslPath req -new -x509 -key $keyPath -out $certPath -days 365 -subj "/C=RU/ST=Moscow/L=Moscow/O=DashPartner/CN=$ip"

Write-Host "SSL сертификат создан:"
Write-Host "  Сертификат: $certPath"
Write-Host "  Ключ: $keyPath"
Write-Host ""
Write-Host "Сертификат действителен 365 дней"
