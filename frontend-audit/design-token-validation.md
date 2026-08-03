# design-token-validation.md

## Design Token Validation & Theme System

Ensures that no custom, hardcoded styles or static values override the standardized system token rules.

### 1. Typography Tokens
- **Brand Font**: `Geist` or `Roboto Mono` (Monospaced layouts for telemetry prices).
- **Size Scale**:
  - `Display`: `48px` / `line-height: 1.1`
  - `Title`: `24px` / `line-height: 1.3`
  - `Body`: `14px` / `line-height: 1.5`
  - `Caption`: `11px` / `line-height: 1.6`

### 2. Spacing and Shadow Tokens
- **Spacing scale**: Custom `8pt` layout grids (`8px`, `16px`, `24px`, `32px`, `48px`, `64px`).
- **Shadows**:
  - `glow-emerald`: `0 0 15px rgba(16, 185, 129, 0.4)` (Used for ONLINE status)
  - `glow-crimson`: `0 0 15px rgba(239, 68, 68, 0.4)` (Used for RISK_HIGH / BLOCKED status)
  - `glow-amber`: `0 0 15px rgba(245, 158, 11, 0.4)` (Used for WARNING status)

### 3. Theme Audit Verification
- Dark theme enforces contrast ratio of at least `7.0` (AA Premium grade) for body copy.
- Real-time data tables utilize green-up/red-down background alerts conforming to the system design system color rules.
