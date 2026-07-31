# TRADEYAR Production Architecture Foundation

The Production Architecture Layer establishes standard, robust production-grade infrastructure, logging conventions, unified error handling, and generic model validation utilities across the TRADEYAR Autonomous Financial Intelligence Platform.

---

## 1. Production Layer Mission

The core mission of the Production Layer is to:
* **Enforce Clean Validation:** Provide a unified validation helper (`ModelValidator`) to check model properties at compile and runtime.
* **Standardize Error Handling:** Define descriptive, decoupled exceptions (`RGException`, `ValidationException`) to ensure error propagation remains predictable.
* **Guarantee Architecture Compliance:** Establish automatic import and dependency check routines to verify that inner packages never import outer modules.

---

## 2. Dependency Architecture

The dependency flow strictly adheres to Clean Architecture rules:
`Core` has zero dependencies.
`Data` depends only on `Core` abstractions.
`Research` depends on `Core` and `Data` abstractions.
`Strategy` depends on `Core` and `Research` abstractions.
`Risk` depends on `Core`, `Research`, and `Strategy` abstractions.
`Decision` depends on `Core`, `Research`, `Strategy`, and `Risk` abstractions.
`Execution` depends on `Core`, `Research`, `Strategy`, `Risk`, and `Decision` abstractions.
`Learning` depends on the abstractions of all lower layers.

---

## 3. Configuration and Error Management

* **ConfigurationLoader:** Accesses environment variables with type-safe fallbacks, allowing seamless zero-config runs in development and full injection in docker containers.
* **Logger Convention:** Structured logging to stdout, detailing timestamps, module paths, and severity levels.
* **Validation Guards:** Every service validates incoming parameters, throwing `ValidationException` immediately if values are negative, blank, or logically inconsistent.
