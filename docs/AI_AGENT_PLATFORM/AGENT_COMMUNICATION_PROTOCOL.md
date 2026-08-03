# 3. Agent Communication Protocol

To maintain maximum reliability, decouple agent states, and prevent message contamination, all specialized agents communicate using a strict, standardized JSON protocol managed by the AI Agent Orchestrator.

---

## 3.1 Protocol Design & Message Envelope
Agents must not communicate via loose, unformatted text. Every interaction consists of a structured envelope containing system-wide headers and a specialized payload.

### Standard Request Envelope Schema
```json
{
  "$schema": "https://tradeyar.ai/schemas/agent-request-v1.json",
  "header": {
    "message_id": "msg_f7b8a91c-e9c1-4091",
    "correlation_id": "corr_38da811b-49fc-48ff",
    "timestamp": "2025-05-18T12:00:00Z",
    "source_agent": "orchestrator",
    "target_agent": "backend_agent"
  },
  "payload": {
    "task": "Implement an API endpoint exposing statistical validation memory under /api/v1/intelligence/memory",
    "context": {
      "target_modules": ["src/Application/Services/web_dashboard.py"],
      "reference_documents": ["docs/LEARNING_SYSTEM_AUDIT.md"],
      "system_limits": {
        "max_active_symbols": 30
      }
    },
    "constraints": [
      "No automated order execution paths",
      "Do not use external network packages not registered in requirements.txt",
      "Ensure response returns within 200ms"
    ],
    "acceptance_criteria": [
      "Endpoint must return JSON format with success state",
      "Return at least 'episodes_processed' and 'active_concepts' indicators"
    ]
  }
}
```

### Standard Response Envelope Schema
```json
{
  "$schema": "https://tradeyar.ai/schemas/agent-response-v1.json",
  "header": {
    "message_id": "msg_9c8d7e6f-5a4b-3c2d",
    "correlation_id": "corr_38da811b-49fc-48ff",
    "timestamp": "2025-05-18T12:05:22Z",
    "source_agent": "backend_agent",
    "target_agent": "orchestrator"
  },
  "payload": {
    "status": "COMPLETED",
    "result": {
      "summary": "Implemented /api/v1/intelligence/memory endpoint returning dynamic cognitive stats.",
      "code_changes": [
        {
          "filepath": "src/Application/Services/web_dashboard.py",
          "action": "MODIFY",
          "description": "Registered GET endpoint and mapped it to the internal MemorySystem metrics."
        }
      ],
      "tests_created": [
        "tests/TRADEYAR_AI.Tests/Services/test_intelligence_endpoints.py"
      ],
      "risks_identified": [
        "Memory file read operations might cause file locks under intensive concurrent requests. Applied asyncio run_in_executor to prevent event loop bottlenecks."
      ]
    }
  }
}
```

---

## 3.2 Error Handling & Resiliency Model
When an agent experiences processing anomalies (e.g., parsing failures, token limit exhaustion, schema discrepancies), it must not crash the Orchestrator. It is required to emit a structured error payload.

### Error Envelope Schema
```json
{
  "header": {
    "message_id": "msg_err_11223344-5566",
    "correlation_id": "corr_38da811b-49fc-48ff",
    "timestamp": "2025-05-18T12:06:01Z",
    "source_agent": "backend_agent",
    "target_agent": "orchestrator"
  },
  "error": {
    "code": "DEPENDENCY_RESOLUTION_FAILED",
    "severity": "FATAL",
    "message": "Failed to resolve imports: 'from src.Core.timeframes import NonExistentTimeframe'. Module not found.",
    "context": {
      "attempted_file": "src/Application/Services/web_dashboard.py",
      "suggested_recovery": "Verify if 'NonExistentTimeframe' exists inside src/Core/timeframes.py or if it was removed in v3.2."
    }
  }
}
```

### Resiliency Policies:
1. **The 3-Strike Rule**: If an agent emits a `FATAL` or `HIGH` severity error, the Orchestrator attempts to self-correct the prompt context and retry up to 3 times with progressive temperature reductions.
2. **Fallback to Safe State**: If 3 attempts fail, the Orchestrator isolates the current session, marks the execution as `DEGRADED`, writes an audit log to `logs/audit/agent_failures.log`, and triggers a **Human Operator Alert**.

---

## 3.3 Agent Handoff Rules
An agent can never trigger an autonomous handover to another agent directly.
- **Strict Orchestrator Mediation**: All communications must flow through the central Orchestrator.
- **Validation Verification**: Before any handoff is scheduled (e.g., transferring a task from Backend Agent to QA Agent), the Orchestrator must validate the outputs against the active schema constraints.
