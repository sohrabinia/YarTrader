# ROUTING_STRUCTURE.md — Routing Structure

This document details the route structure and access guards implemented for the TradeYar AI Client Platform.

## 🗺️ Route Matrix

| Shell | Route Path | Component Name | Required Auth Role | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Public** | `/` | `LandingPage` | GUEST / ANY | High-impact dark landing page, guest demo mode entry, interactive product visualizer |
| **Public** | `/features` | `FeaturesPage` | GUEST / ANY | Explains the 9 mathematically-sound price-action intelligence engines and memory layers |
| **Public** | `/pricing` | `PricingPage` | GUEST / ANY | Billing tiers (User, Pro, Premium, Enterprise) with cryptocurrency gateway specs |
| **Public** | `/blog` | `BlogCatalogPage` | GUEST / ANY | SEO-optimized long-form article directory |
| **Public** | `/blog/:id` | `BlogPostPage` | GUEST / ANY | Individual blog post page supporting JSON-LD schema metadata |
| **Public** | `/login` | `LoginPage` | GUEST / ANY | User login page supporting credentials + Google & Apple OAuth sign-ins |
| **Public** | `/register` | `RegisterPage` | GUEST / ANY | User signup, referrals tracking, and onboarding checklist |
| **Terminal** | `/dashboard` | `TraderTerminal` | USER / PRO / PREMIUM / ADMIN | Unified multi-timeframe dashboard, active symbol selection matrix (ceiling 30 symbols) |
| **Terminal** | `/dashboard/research` | `ResearchIntelligence` | USER / PRO / PREMIUM / ADMIN | Feature extraction pipeline view, statistical QC checks, latest pattern metrics |
| **Terminal** | `/dashboard/strategy` | `StrategyIntelligence` | USER / PRO / PREMIUM / ADMIN | Backtesting simulation results, rule-based core models, confidence parameters |
| **Terminal** | `/dashboard/risk` | `RiskIntelligence` | USER / PRO / PREMIUM / ADMIN | Exposure meters, risk policy checklists, active limit warnings, stop-out limits |
| **Terminal** | `/dashboard/execution` | `ExecutionIntelligence` | USER / PRO / PREMIUM / ADMIN | Passive advisor logs, virtual shadow trade simulation records, audit trail |
| **Terminal** | `/dashboard/learning` | `LearningIntelligence` | USER / PRO / PREMIUM / ADMIN | Multi-layered memory loop visualization, experience promotion pipelines |
| **Admin** | `/admin` | `SreDashboard` | SRE_OPERATOR / ADMIN | Unified system health console, MT5 provider diagnostics, SCM services liveness |
| **Admin** | `/admin/workers` | `WorkerControlPanel` | SRE_OPERATOR / ADMIN | Active service processes, status-aware logs (Research, Intelligence, Shadow workers) |
| **Admin** | `/admin/limits` | `SystemLimitsManager` | SRE_OPERATOR / ADMIN | Dynamic asset ceiling controller (configures symbol metrics, limits and constraints) |

---

## 🛡️ Route Guards and Client-Side Protection

To ensure optimal security and prevent unauthorized screen access, route-guarding logic must be enforced before rendering page components.

```javascript
// Conceptual React Route Guard Hook Example
import { useAuthStore } from '../store/useAuthStore';
import { useRouter } from 'next/router';
import { useEffect } from 'react';

export function withAuth(Component, allowedRoles) {
  return function AuthenticatedComponent(props) {
    const { user, isAuthenticated } = useAuthStore();
    const router = useRouter();

    useEffect(() => {
      if (!isAuthenticated) {
        router.replace('/login');
      } else if (allowedRoles && !allowedRoles.includes(user.role)) {
        router.replace('/403'); // Forbidden page
      }
    }, [isAuthenticated, user, router]);

    if (!isAuthenticated || (allowedRoles && !allowedRoles.includes(user.role))) {
      return <LoadingScreen />; // Render safe loading state during redirect
    }

    return <Component {...props} />;
  };
}
```

### Route Guard Actions:
1. **Unauthenticated Redirects:** Directs users attempting to load `/dashboard/*` or `/admin/*` without an active session to `/login`.
2. **Role Hierarchy Checks:**
   - `USER`, `PRO`, `PREMIUM` roles are permitted to browse `/dashboard/*` screens.
   - `/admin/*` routes strictly require the `ADMIN` or `SRE_OPERATOR` role. Attempting to access these routes redirects the client to `/403` and logs a security event on the console.
3. **No-Secrets Exposure:** Environment configurations and client files must never store server passwords or API keys. Access tokens are transmitted exclusively via secure HTTP headers.
