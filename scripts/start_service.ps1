# Start YarTrader Windows Service Script

$ServiceName = "YarTrader"

Write-Host "Starting $ServiceName service..." -ForegroundColor Cyan

# Check Admin privileges
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error "Error: This script must be run as an Administrator!"
    Exit 1
}

# Start the service
$service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if (-not $service) {
    Write-Error "Error: Service '$ServiceName' is not installed. Please run .\install_service.ps1 first."
    Exit 1
}

if ($service.Status -eq "Running") {
    Write-Host "Service '$ServiceName' is already running!" -ForegroundColor Green
} else {
    Start-Service -Name $ServiceName
    Start-Sleep -Seconds 3
    $service = Get-Service -Name $ServiceName
    if ($service.Status -eq "Running") {
        Write-Host "Service '$ServiceName' started successfully!" -ForegroundColor Green
    } else {
        Write-Error "Failed to start service. Please check the Windows Event Viewer or TradeYar AI application logs."
    }
}
