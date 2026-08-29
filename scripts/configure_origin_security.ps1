# YARTRADER - PRODUCTION ORIGIN SECURITY & FIREWALL HARDENING SCRIPT
# This script configures Windows Defender Firewall rules and portproxy bindings for YarTrader Production.
# MUST BE RUN AS ADMINISTRATOR ON WINDOWS SERVER HOST.

[CmdletBinding()]
param(
    [switch]$RestrictPort80ToCloudflare = $true,
    [switch]$RemoveObsoleteRules = $true
)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  YARTRADER PRODUCTION ORIGIN SECURITY HARDENING" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Ensure Administrator execution
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error "This script requires Administrator privileges. Please re-run from an elevated PowerShell prompt."
    exit 1
}

# 1. Obsolete Firewall Rules Cleanup
if ($RemoveObsoleteRules) {
    Write-Host "`n[1/3] Auditing and removing obsolete Firewall rules..." -ForegroundColor Yellow
    $obsoleteRules = @(
        "TradeYarAI 8000",
        "TradeYarAI Port 8000",
        "TradeYar AI API 8000",
        "TradeYar DevOps API 5000"
    )

    foreach ($ruleName in $obsoleteRules) {
        $existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
        if ($existing) {
            Remove-NetFirewallRule -DisplayName $ruleName
            Write-Host "  [REMOVED] Firewall rule: '$ruleName'" -ForegroundColor Green
        } else {
            Write-Host "  [OK] Rule '$ruleName' does not exist." -ForegroundColor Gray
        }
    }
}

# 2. Enforce Port 8000 Localhost-Only & Remove direct public access to 8000/5000
Write-Host "`n[2/3] Verifying Port 8000 & 5000 exposure..." -ForegroundColor Yellow

$port8000Rules = Get-NetFirewallRule -ErrorAction SilentlyContinue | Where-Object {
    $r = $_
    $portFilter = Get-NetFirewallPortFilter -AssociatedNetFirewallRule $r -ErrorAction SilentlyContinue
    return ($portFilter.LocalPort -contains "8000" -or $portFilter.LocalPort -contains "5000") -and $r.Direction -eq "Inbound" -and $r.Action -eq "Allow"
}

foreach ($r in $port8000Rules) {
    Disable-NetFirewallRule -Name $r.Name
    Write-Host "  [DISABLED] Direct inbound rule allowing public access to port 8000/5000: '$($r.DisplayName)'" -ForegroundColor Yellow
}

# Ensure Portproxy maps Port 80 -> 127.0.0.1:8000
Write-Host "`nVerifying netsh portproxy Port 80 -> 127.0.0.1:8000 mapping..." -ForegroundColor Yellow
netsh interface portproxy delete v4tov4 listenport=80 listenaddress=0.0.0.0 | Out-Null
netsh interface portproxy add v4tov4 listenport=80 listenaddress=0.0.0.0 connectport=8000 connectaddress=127.0.0.1 | Out-Null
Write-Host "  [OK] Portproxy bound 0.0.0.0:80 -> 127.0.0.1:8000" -ForegroundColor Green


# 3. Cloudflare IP Ranges Lockdown for Port 80 Ingress
if ($RestrictPort80ToCloudflare) {
    Write-Host "`n[3/3] Restricting Inbound Port 80 Ingress to Official Cloudflare IPv4 & IPv6 Ranges..." -ForegroundColor Yellow

    # Official Cloudflare IP Ranges (https://www.cloudflare.com/ips/)
    $cloudflareIPv4 = @(
        "173.245.48.0/20",
        "103.21.244.0/22",
        "103.22.200.0/22",
        "103.31.4.0/22",
        "141.101.64.0/18",
        "108.162.192.0/18",
        "190.93.240.0/20",
        "188.114.96.0/20",
        "197.234.240.0/22",
        "198.41.128.0/17",
        "162.158.0.0/15",
        "104.16.0.0/13",
        "104.24.0.0/14",
        "172.64.0.0/13",
        "131.0.72.0/22"
    )

    $cloudflareIPv6 = @(
        "2400:cb00::/32",
        "2606:4700::/32",
        "2803:f800::/32",
        "2405:b500::/32",
        "2405:8100::/32",
        "2a06:98c0::/29",
        "2c0f:f248::/32"
    )

    $allCloudflareIPs = $cloudflareIPv4 + $cloudflareIPv6

    # Remove existing custom YarTrader Cloudflare rule if present
    Remove-NetFirewallRule -DisplayName "YarTrader Inbound Cloudflare HTTP 80" -ErrorAction SilentlyContinue

    New-NetFirewallRule -DisplayName "YarTrader Inbound Cloudflare HTTP 80" `
                        -Direction Inbound `
                        -LocalPort 80 `
                        -Protocol TCP `
                        -Action Allow `
                        -RemoteAddress $allCloudflareIPs `
                        -Description "Restricts HTTP Port 80 traffic exclusively to official Cloudflare edge proxy IP ranges." `
                        | Out-Null

    Write-Host "  [SUCCESS] Firewall rule 'YarTrader Inbound Cloudflare HTTP 80' applied with $($allCloudflareIPs.Count) Cloudflare CIDR blocks." -ForegroundColor Green
}

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host "  ORIGIN SECURITY HARDENING COMPLETED SUCCESSFULLY" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
