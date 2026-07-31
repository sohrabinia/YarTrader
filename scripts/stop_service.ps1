# Stop TradeYar-AI Windows Service Script

$ServiceName = "TradeYar-AI"

Write-Host "Stopping $ServiceName service..." -ForegroundColor Cyan

# Check Admin privileges
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error "Error: This script must be run as an Administrator!"
    Exit 1
}

$service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if (-not $service) {
    Write-Error "Error: Service '$ServiceName' is not installed."
    Exit 1
}

if ($service.Status -eq "Stopped") {
    Write-Host "Service '$ServiceName' is already stopped!" -ForegroundColor Green
} else {
    Stop-Service -Name $ServiceName -Force
    Start-Sleep -Seconds 2
    $service = Get-Service -Name $ServiceName
    if ($service.Status -eq "Stopped") {
        Write-Host "Service '$ServiceName' stopped gracefully." -ForegroundColor Green
    } else {
        Write-Error "Failed to stop service gracefully."
    }
}
