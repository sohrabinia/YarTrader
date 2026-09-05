# YarTrader Authorization Matrix

Defines access control policy across repository endpoints.

| Route / Scope | Anonymous | User | Pro / Premium | Admin | SRE | Agent |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `/` (Landing / Public Docs) | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW |
| `/api/research/*` | ALLOW (Read) | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW |
| `/api/execution/plans` | DENY | ALLOW | ALLOW | ALLOW | ALLOW | DENY (Read Only) |
| `/api/demo/execute` | DENY | DENY | ALLOW | ALLOW | ALLOW | DENY |
| `/api/admin/*` | DENY | DENY | DENY | ALLOW | ALLOW | DENY |
| `/api/wallet/*` | DENY | DENY | DENY | DENY | DENY | DENY (NOT_IMPLEMENTED) |
| `/api/payment/*` | DENY | DENY | DENY | DENY | DENY | DENY (NOT_IMPLEMENTED) |

Note: Production mode strictly rejects mock authentication tokens and enforces JWT / API key validation.
