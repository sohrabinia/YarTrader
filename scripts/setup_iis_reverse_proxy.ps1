# PowerShell IIS Reverse Proxy Automation Script for TradeYar AI
# Location: C:\Projects\TradeYar_AI\scripts\setup_iis_reverse_proxy.ps1
#
# Idempotency Rule: This script can be run multiple times safely.
# It automates creating the IIS Website, Application Pool, configuring URL Rewrite rules,
# writing the secure web.config with enterprise security headers, and setting up static caching.

$SiteName = "TradeYarAI"
$AppPoolName = "TradeYarPool"
$PhysicalPath = "C:\inetpub\wwwroot\TradeYarAI"
$BackendUrl = "http://127.0.0.1:8000"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "IIS Reverse Proxy Setup & Secure Web.config Generator" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Check Administrator Privileges
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[-] WARNING: This script was not executed as an Administrator!" -ForegroundColor Yellow
    Write-Host "    WebAdministration and IIS commands will likely fail. Running in Local Configuration Generator mode." -ForegroundColor Yellow
}

# ------------------------------------------------------------------------------
# STEP 1: Ensure Physical Directory and Secure Web.config
# ------------------------------------------------------------------------------
Write-Host "`n[+] Step 1: Creating Physical Site Folder and web.config..." -ForegroundColor Cyan

if (-not (Test-Path $PhysicalPath)) {
    try {
        New-Item -ItemType Directory -Force -Path $PhysicalPath | Out-Null
        Write-Host "  [OK] Created directory: $PhysicalPath" -ForegroundColor Green
    } catch {
        $PhysicalPath = Join-Path (Split-Path -Parent $PSScriptRoot) "iis_publish"
        if (-not (Test-Path $PhysicalPath)) {
            New-Item -ItemType Directory -Force -Path $PhysicalPath | Out-Null
        }
        Write-Host "  [WARN] Failed to write in C:\inetpub. Using fallback directory: $PhysicalPath" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [OK] Physical directory exists: $PhysicalPath" -ForegroundColor Green
}

$503Path = Join-Path $PhysicalPath "503.html"
$503Content = @"
<!DOCTYPE html>
<html lang="fa">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>سامانه موقتاً در دسترس نیست | TradeYar AI</title>
    <style>
        body {
            font-family: 'Tahoma', 'Segoe UI', Arial, sans-serif;
            text-align: center;
            padding: 100px 20px;
            background-color: #f7f9fa;
            color: #2b2d42;
            direction: rtl;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
            border-top: 6px solid #e71d36;
        }
        h1 {
            color: #1d3557;
            font-size: 1.8em;
            margin-bottom: 20px;
        }
        p {
            font-size: 1.1em;
            line-height: 1.8;
            color: #4a5759;
        }
        .english {
            direction: ltr;
            margin-top: 30px;
            border-top: 1px dashed #edf2f4;
            padding-top: 20px;
            font-family: 'Segoe UI', Arial, sans-serif;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>سامانه موقتاً در دسترس نیست (خطای ۵۰۳)</h1>
        <p>کاربر گرامی، موتور اجرای پس‌زمینه TradeYar AI در حال حاضر آفلاین است، در حال راه‌اندازی مجدد است، یا عملیات نگهداری SRE بر روی آن در حال انجام است.</p>
        <p>لطفاً چند لحظه دیگر مجدداً تلاش نمایید. از شکیبایی شما سپاسگزاریم.</p>

        <div class="english">
            <h2 style="color: #1d3557; font-size: 1.4em;">Service Temporarily Unavailable (503 Error)</h2>
            <p>The downstream TradeYar AI background execution service is currently offline, restarting, or undergoing active SRE maintenance.</p>
            <p>Please try again in a few moments. Thank you for your patience.</p>
        </div>
    </div>
</body>
</html>
"@

try {
    [System.IO.File]::WriteAllText($503Path, $503Content)
    Write-Host "  [OK] Generated custom 503 error page at: $503Path" -ForegroundColor Green
} catch {
    Write-Error "Failed to write 503.html file!"
    Exit 1
}

$WebConfigPath = Join-Path $PhysicalPath "web.config"

# Complete production-ready web.config template
$WebConfigContent = @"
<?xml version="1.0" encoding="utf-8"?>
<!--
  TradeYar AI v3.2 — Enterprise IIS Reverse Proxy web.config
  This file configures:
    1. URL Rewrite rules from Public HTTPS to Local FastAPI (Port 8000).
    2. Enterprise Security Headers (HSTS, clickjacking protection, mime-sniffing block).
    3. Static Content compression and Cache-Control rules.
    4. HTTP 502/503 Graceful custom error page routing.
-->
<configuration>
  <system.webServer>

    <!-- 1. URL Rewrite Module Rules -->
    <rewrite>
      <rules>
        <!-- Rule 1: Redirect HTTP to HTTPS (Required for production SSL) -->
        <rule name="Redirect HTTP to HTTPS" stopProcessing="true">
          <match url="(.*)" />
          <conditions>
            <add input="{HTTPS}" pattern="off" ignoreCase="true" />
          </conditions>
          <action type="Redirect" url="https://{HTTP_HOST}/{R:1}" redirectType="Permanent" />
        </rule>

        <!-- Rule 2: Reverse Proxy all other requests to FastAPI backend on Port 8000 -->
        <rule name="Reverse Proxy to FastAPI" stopProcessing="true">
          <match url="(.*)" />
          <conditions>
            <add input="{HTTPS}" pattern="on" ignoreCase="true" />
          </conditions>
          <action type="Rewrite" url="${BackendUrl}/{R:1}" logRewrittenUrl="true" />
        </rule>
      </rules>
    </rewrite>

    <!-- 2. Security Headers (HSTS, Clickjacking protection, Mime Sniffing block) -->
    <httpProtocol>
      <customHeaders>
        <!-- HTTP Strict Transport Security (HSTS) -->
        <add name="Strict-Transport-Security" value="max-age=31536000; includeSubDomains; preload" />
        <!-- Clickjacking Prevention -->
        <add name="X-Frame-Options" value="SAMEORIGIN" />
        <!-- MIME Sniffing Block -->
        <add name="X-Content-Type-Options" value="nosniff" />
        <!-- Cross-Site Scripting Protection -->
        <add name="X-XSS-Protection" value="1; mode=block" />
        <!-- Referrer Policy -->
        <add name="Referrer-Policy" value="strict-origin-when-cross-origin" />
        <!-- Content Security Policy (Basic restrictive CSP template) -->
        <add name="Content-Security-Policy" value="default-src 'self' 'unsafe-inline' 'unsafe-eval' data:; connect-src 'self' ws: wss:; img-src 'self' data: blob:;" />
      </customHeaders>
    </httpProtocol>

    <!-- 3. Static File Caching Optimization (for dashboard SPA resources under static/*) -->
    <staticContent>
      <clientCache cacheControlMode="UseMaxAge" cacheControlMaxAge="30.00:00:00" />
    </staticContent>

    <!-- 4. Enterprise Request Filtering -->
    <security>
      <requestFiltering>
        <!-- Max content length (approx 50MB) -->
        <requestLimits maxAllowedContentLength="52428800" />
      </requestFiltering>
    </security>

    <!-- 5. Custom 503 HTTP Service Unavailable Error Mapping -->
    <httpErrors errorMode="Custom" existingResponse="Replace">
      <remove statusCode="502" subStatusCode="-1" />
      <error statusCode="502" subStatusCode="-1" prefixLanguageFilePath="" path="503.html" responseMode="File" />
      <remove statusCode="503" subStatusCode="-1" />
      <error statusCode="503" subStatusCode="-1" prefixLanguageFilePath="" path="503.html" responseMode="File" />
    </httpErrors>

  </system.webServer>
</configuration>
"@

try {
    [System.IO.File]::WriteAllText($WebConfigPath, $WebConfigContent)
    Write-Host "  [OK] Generated secure Web.config at: $WebConfigPath" -ForegroundColor Green
} catch {
    Write-Error "Failed to write Web.config file!"
    Exit 1
}

# ------------------------------------------------------------------------------
# STEP 2: Configure IIS (Requires Administrator and WebAdministration Module)
# ------------------------------------------------------------------------------
Write-Host "`n[+] Step 2: Registering IIS Site and App Pool..." -ForegroundColor Cyan

$IISModule = Get-Module -ListAvailable -Name WebAdministration

if ($isAdmin -and $IISModule) {
    try {
        Import-Module WebAdministration
        Write-Host "  [OK] WebAdministration module loaded successfully." -ForegroundColor Green

        # Check App Pool
        if (-not (Test-Path "IIS:\AppPools\$AppPoolName")) {
            Write-Host "  [INFO] Creating Application Pool '$AppPoolName'..." -ForegroundColor Yellow
            $pool = New-Item "IIS:\AppPools\$AppPoolName"
            $pool.managedRuntimeVersion = "" # No Managed Code for reverse proxy pool
            $pool | Set-Item
            Write-Host "  [OK] Created App Pool: $AppPoolName (No Managed Code)" -ForegroundColor Green
        } else {
            Write-Host "  [OK] Application Pool '$AppPoolName' already exists." -ForegroundColor Green
        }

        # Check Site
        if (-not (Test-Path "IIS:\Sites\$SiteName")) {
            Write-Host "  [INFO] Creating IIS Website '$SiteName'..." -ForegroundColor Yellow
            # Create site binding HTTP port 80. Real production SSL must bind Port 443.
            New-Website -Name $SiteName -PhysicalPath $PhysicalPath -Port 80 -ApplicationPool $AppPoolName | Out-Null
            Write-Host "  [OK] Created Website: $SiteName on port 80." -ForegroundColor Green
        } else {
            Write-Host "  [OK] Website '$SiteName' already exists. Reconfiguring root path..." -ForegroundColor Green
            Set-ItemProperty "IIS:\Sites\$SiteName" -Name physicalPath -Value $PhysicalPath
        }

        # Configure ARR (Application Request Routing) Proxy settings
        Write-Host "  [INFO] Configuring IIS Application Request Routing (ARR) Proxy..." -ForegroundColor Yellow
        $AppCmdPath = Join-Path $env:SystemRoot "System32\inetsrv\appcmd.exe"
        if (Test-Path $AppCmdPath) {
            # Enable proxy functionality
            & $AppCmdPath set config -section:system.webServer/proxy /enabled:"True" /commit:apphost | Out-Null
            & $AppCmdPath set config -section:system.webServer/proxy /preserveHostHeader:"True" /commit:apphost | Out-Null
            Write-Host "  [OK] ARR Proxy Enabled and PreserveHostHeader configured." -ForegroundColor Green
        } else {
            Write-Host "  [WARN] appcmd.exe not found. Please ensure URL Rewrite & ARR are installed manually!" -ForegroundColor Yellow
        }

    } catch {
        Write-Host "  [WARN] Exception occurred during IIS PowerShell configuration: $_" -ForegroundColor Yellow
        Write-Host "         Web.config has been generated. Please manually verify site and pool bindings in IIS." -ForegroundColor Yellow
    }
} else {
    Write-Host "  [INFO] Skipping WebAdministration configuration (Not on Windows, not Admin, or IIS WebAdministration missing)." -ForegroundColor Yellow
    Write-Host "         Enterprise Web.config file has been safely written for local validation." -ForegroundColor Green
}

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host "IIS REVERSE PROXY SETUP COMPLETE!" -ForegroundColor Green
Write-Host "Web.config path: $WebConfigPath" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
