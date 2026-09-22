# PowerShell IIS Reverse Proxy Automation Script for YarTrader
# Location: C:\Projects\YarTrader\scripts\setup_iis_reverse_proxy.ps1
#
# Idempotency Rule: This script can be run multiple times safely.
# It automates resolving IIS physical paths, checking SSL bindings, configuring URL Rewrite rules,
# writing secure web.config files with enterprise security headers, and setting up static caching.

$SiteName = "Default Web Site"
$AppPoolName = "DefaultAppPool"
$DefaultProductionPath = "C:\inetpub\wwwroot"
$StagingPath = "C:\inetpub\YarTrader-Edge-Staging"
$BackendUrl = "http://127.0.0.1:8000"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "IIS Reverse Proxy Setup & Secure Web.config Generator" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Check Administrator Privileges
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

$IISModule = Get-Module -ListAvailable -Name WebAdministration
$HasHttpsBinding = $false
$ResolvedProductionPath = $DefaultProductionPath

# ------------------------------------------------------------------------------
# STEP 1: RESOLVE IIS SITE PHYSICAL PATH AND BINDINGS BEFORE WRITING WEB.CONFIG
# ------------------------------------------------------------------------------
Write-Host "`n[+] Step 1: Resolving IIS Site Physical Path & SSL Bindings..." -ForegroundColor Cyan

if ($isAdmin -and $IISModule) {
    try {
        Import-Module WebAdministration -ErrorAction Stop
        Write-Host "  [OK] WebAdministration module loaded successfully." -ForegroundColor Green

        # Resolve Production Site Path & Bindings
        $TargetSite = $null
        if (Test-Path "IIS:\Sites\$SiteName") {
            $TargetSite = Get-Item "IIS:\Sites\$SiteName" -ErrorAction Stop
        } elseif (Test-Path "IIS:\Sites\TradeYarAI") {
            $SiteName = "TradeYarAI"
            $TargetSite = Get-Item "IIS:\Sites\$SiteName" -ErrorAction Stop
        }

        if ($TargetSite) {
            $SitePath = $TargetSite.physicalPath
            if ($SitePath) {
                $SitePath = [System.Environment]::ExpandEnvironmentVariables($SitePath)
            }

            if ($SitePath -and (Test-Path $SitePath)) {
                $ResolvedProductionPath = $SitePath
                Write-Host "  [OK] Resolved live IIS site '$SiteName' physicalPath: $ResolvedProductionPath" -ForegroundColor Green
            } else {
                Write-Host "  [FAIL] IIS site '$SiteName' exists but physicalPath '$SitePath' is invalid or missing on disk!" -ForegroundColor Red
                Write-Error "Deployment Failed: Resolved IIS physicalPath '$SitePath' for site '$SiteName' is invalid or missing!"
                Exit 1
            }

            # Check if any HTTPS binding exists on the resolved production site
            $Bindings = Get-WebBinding -Name $SiteName -ErrorAction SilentlyContinue
            foreach ($b in $Bindings) {
                if ($b.protocol -eq "https") {
                    $HasHttpsBinding = $true
                    break
                }
            }
            Write-Host "  [INFO] Production site HTTPS binding detected: $HasHttpsBinding" -ForegroundColor Yellow
        } else {
            Write-Host "  [INFO] IIS site '$SiteName' does not exist in IIS manager yet. Using default initial path: $DefaultProductionPath" -ForegroundColor Yellow
            $ResolvedProductionPath = $DefaultProductionPath
        }

        # Check Staging Site Bindings & physicalPath if Staging Site exists in IIS
        if (Test-Path "IIS:\Sites\YarTrader-Edge-Staging") {
            $StagingSite = Get-Item "IIS:\Sites\YarTrader-Edge-Staging" -ErrorAction Stop

            $StagingSitePath = $StagingSite.physicalPath
            if ($StagingSitePath) {
                $StagingSitePath = [System.Environment]::ExpandEnvironmentVariables($StagingSitePath)
            }

            if ($StagingSitePath -and (Test-Path $StagingSitePath)) {
                $StagingPath = $StagingSitePath
                Write-Host "  [OK] Resolved live IIS staging site physicalPath: $StagingPath" -ForegroundColor Green
            } else {
                Write-Host "  [FAIL] IIS staging site 'YarTrader-Edge-Staging' exists but physicalPath '$($StagingSite.physicalPath)' is invalid or missing on disk!" -ForegroundColor Red
                Write-Error "Deployment Failed: Resolved IIS staging physicalPath '$($StagingSite.physicalPath)' is invalid or missing!"
                Exit 1
            }
        }
    } catch {
        Write-Host "  [FAIL] Critical Exception during IIS WebAdministration site inspection: $_" -ForegroundColor Red
        Write-Error "Deployment Failed: Unable to inspect IIS site configuration safely! Exiting to prevent fail-open path resolution."
        Exit 1
    }
} else {
    Write-Host "  [FAIL] WebAdministration module is missing or script is not running as Administrator!" -ForegroundColor Red
    Write-Error "Deployment Failed: IIS reverse proxy configuration requires Administrator privileges and the WebAdministration module! Refusing to fall back to unverified default path."
    Exit 1
}

# Fail-closed validation for production directory
if (-not (Test-Path $ResolvedProductionPath)) {
    try {
        New-Item -ItemType Directory -Force -Path $ResolvedProductionPath -ErrorAction Stop | Out-Null
        Write-Host "  [OK] Created production directory: $ResolvedProductionPath" -ForegroundColor Green
    } catch {
        Write-Error "Deployment Failed: Unable to create or access production directory '$ResolvedProductionPath'!"
        Exit 1
    }
}

# ------------------------------------------------------------------------------
# STEP 2: GENERATE RE-MEDIATED WEB.CONFIG TEMPLATE & 503 ERROR PAGE
# ------------------------------------------------------------------------------
Write-Host "`n[+] Step 2: Writing web.config & 503.html to resolved IIS paths..." -ForegroundColor Cyan

$503Content = @"
<!DOCTYPE html>
<html lang="fa">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>سامانه موقتاً در دسترس نیست | YarTrader</title>
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
        <p>کاربر گرامی، موتور اجرای پس‌زمینه YarTrader در حال حاضر آفلاین است، در حال راه‌اندازی مجدد است، یا عملیات نگهداری SRE بر روی آن در حال انجام است.</p>
        <p>لطفاً چند لحظه دیگر مجدداً تلاش نمایید. از شکیبایی شما سپاسگزاریم.</p>

        <div class="english">
            <h2 style="color: #1d3557; font-size: 1.4em;">Service Temporarily Unavailable (503 Error)</h2>
            <p>The downstream YarTrader background execution service is currently offline, restarting, or undergoing active SRE maintenance.</p>
            <p>Please try again in a few moments. Thank you for your patience.</p>
        </div>
    </div>
</body>
</html>
"@

# Construct Rewrite Rules conditionally based on SSL availability
$RewriteRulesXml = ""
if ($HasHttpsBinding) {
    $RewriteRulesXml = @"
        <!-- Rule 1: Redirect HTTP to HTTPS (Active HTTPS Binding Detected) -->
        <rule name="Redirect HTTP to HTTPS" stopProcessing="true">
          <match url="(.*)" />
          <conditions>
            <add input="{HTTPS}" pattern="off" ignoreCase="true" />
          </conditions>
          <action type="Redirect" url="https://{HTTP_HOST}/{R:1}" redirectType="Permanent" />
        </rule>

        <!-- Rule 2: Reverse Proxy HTTPS requests to YarTrader FastAPI on Port 8000 -->
        <rule name="Reverse Proxy to YarTrader FastAPI" stopProcessing="true">
          <match url="(.*)" />
          <conditions>
            <add input="{HTTPS}" pattern="on" ignoreCase="true" />
          </conditions>
          <action type="Rewrite" url="${BackendUrl}/{R:1}" logRewrittenUrl="true" />
        </rule>
"@
} else {
    $RewriteRulesXml = @"
        <!-- Rule 1: Reverse Proxy HTTP requests directly to YarTrader FastAPI on Port 8000 -->
        <rule name="Reverse Proxy to YarTrader FastAPI" stopProcessing="true">
          <match url="(.*)" />
          <action type="Rewrite" url="${BackendUrl}/{R:1}" logRewrittenUrl="true" />
        </rule>
"@
}

$WebConfigContent = @"
<?xml version="1.0" encoding="utf-8"?>
<!--
  YarTrader Enterprise IIS Reverse Proxy web.config
  M-294 Remediation: Direct browser access to standalone YarOperator (port 3000)
  is strictly forbidden at the IIS boundary. All browser traffic, including /Operator,
  /operator, /api/v1/operator/*, and /auth/*, is directed exclusively to YarTrader
  FastAPI (Port 8000), which serves the SPA and guards API endpoints server-side.
-->
<configuration>
  <system.webServer>

    <!-- 1. URL Rewrite Module Rules -->
    <rewrite>
      <rules>
        <!-- Clear any stale legacy or conflicting rules -->
        <clear />
$RewriteRulesXml
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
        <!-- Content Security Policy (Scoped template with Google Identity Services & Vazirmatn Font support) -->
        <add name="Content-Security-Policy" value="default-src 'self' 'unsafe-inline' 'unsafe-eval' data:; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://accounts.google.com/gsi/client; frame-src 'self' https://accounts.google.com/; connect-src 'self' ws: wss: https://accounts.google.com/gsi/; style-src 'self' 'unsafe-inline' https://accounts.google.com/gsi/style https://cdn.jsdelivr.net; font-src 'self' data: https://cdn.jsdelivr.net; img-src 'self' data: blob: https://*.googleusercontent.com https://*.gstatic.com;" />
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

# Write Production web.config and 503.html
$Prod503Path = Join-Path $ResolvedProductionPath "503.html"
$ProdWebConfigPath = Join-Path $ResolvedProductionPath "web.config"

try {
    [System.IO.File]::WriteAllText($Prod503Path, $503Content)
    [System.IO.File]::WriteAllText($ProdWebConfigPath, $WebConfigContent)
    Write-Host "  [OK] Written Production web.config at: $ProdWebConfigPath" -ForegroundColor Green
} catch {
    Write-Error "Failed to write Production web.config or 503.html file!"
    Exit 1
}

# Write Staging web.config and 503.html if Staging path exists or can be created
if (Test-Path $StagingPath) {
    try {
        $Staging503Path = Join-Path $StagingPath "503.html"
        $StagingWebConfigPath = Join-Path $StagingPath "web.config"
        [System.IO.File]::WriteAllText($Staging503Path, $503Content)
        [System.IO.File]::WriteAllText($StagingWebConfigPath, $WebConfigContent)
        Write-Host "  [OK] Synchronized Staging web.config at: $StagingWebConfigPath" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] Critical Error: Failed to write Staging web.config or 503.html to '$StagingPath': $_" -ForegroundColor Red
        Write-Error "Deployment Failed: Unable to write staging IIS web.config file! Exiting fail-closed."
        Exit 1
    }
}

# ------------------------------------------------------------------------------
# STEP 3: CONFIGURE IIS SITE AND APP POOL IF ADMIN
# ------------------------------------------------------------------------------
Write-Host "`n[+] Step 3: Registering IIS Site, App Pool, and ARR Settings..." -ForegroundColor Cyan

try {
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
        New-Website -Name $SiteName -PhysicalPath $ResolvedProductionPath -Port 80 -ApplicationPool $AppPoolName | Out-Null
        Write-Host "  [OK] Created Website: $SiteName on port 80." -ForegroundColor Green
    } else {
        Write-Host "  [OK] Website '$SiteName' already exists. Physical path set to: $ResolvedProductionPath" -ForegroundColor Green
        Set-ItemProperty "IIS:\Sites\$SiteName" -Name physicalPath -Value $ResolvedProductionPath
    }

    # Configure ARR (Application Request Routing) Proxy settings
    Write-Host "  [INFO] Configuring IIS Application Request Routing (ARR) Proxy..." -ForegroundColor Yellow
    $AppCmdPath = Join-Path $env:SystemRoot "System32\inetsrv\appcmd.exe"
    if (Test-Path $AppCmdPath) {
        & $AppCmdPath set config -section:system.webServer/proxy /enabled:"True" /commit:apphost | Out-Null
        & $AppCmdPath set config -section:system.webServer/proxy /preserveHostHeader:"True" /commit:apphost | Out-Null
        Write-Host "  [OK] ARR Proxy Enabled and PreserveHostHeader configured." -ForegroundColor Green
    } else {
        Write-Host "  [WARN] appcmd.exe not found. Please ensure URL Rewrite & ARR are installed manually!" -ForegroundColor Yellow
    }

} catch {
    Write-Host "  [FAIL] Critical Error during IIS site registration: $_" -ForegroundColor Red
    Write-Error "Deployment Failed: Unable to configure IIS website or application pool!"
    Exit 1
}

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host "IIS REVERSE PROXY SETUP COMPLETE!" -ForegroundColor Green
Write-Host "Production web.config: $ProdWebConfigPath" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
