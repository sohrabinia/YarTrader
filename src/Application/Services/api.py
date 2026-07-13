from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from src.Infrastructure.exceptions import ValidationException


@dataclass(frozen=True)
class ServiceRequestDTO:
    client_id: str
    token: str
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ServiceResponseDTO:
    status_code: int
    data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


class ServiceOrchestrator:
    """Orchestrates API endpoints, applies validation and authorization."""
    def __init__(self) -> None:
        self._auth_db = {"client_1": "secret_token_1", "client_2": "secret_token_2"}
        self._permissions = {"client_1": ["read", "write"], "client_2": ["read"]}
        self._metrics = {"total_requests": 0, "failed_requests": 0}

    def authenticate(self, client_id: str, token: str) -> bool:
        return self._auth_db.get(client_id) == token

    def authorize(self, client_id: str, required_scope: str) -> bool:
        return required_scope in self._permissions.get(client_id, [])

    def handle_request(self, endpoint: str, dto: ServiceRequestDTO) -> ServiceResponseDTO:
        self._metrics["total_requests"] += 1

        # 1. Authentication Check
        if not self.authenticate(dto.client_id, dto.token):
            self._metrics["failed_requests"] += 1
            return ServiceResponseDTO(status_code=401, error_message="Authentication failed.")

        # 2. Authorization Check
        if not self.authorize(dto.client_id, "read"):
            self._metrics["failed_requests"] += 1
            return ServiceResponseDTO(status_code=403, error_message="Unauthorized scope access.")

        # Middleware validation check
        try:
            self._validate_middleware(endpoint, dto.payload)
        except ValidationException as e:
            self._metrics["failed_requests"] += 1
            return ServiceResponseDTO(status_code=400, error_message=str(e))

        # 3. Endpoint Routing
        if endpoint == "/v1/health":
            return ServiceResponseDTO(status_code=200, data={"status": "Healthy", "system_time": datetime.now().isoformat()})
        elif endpoint == "/v1/metrics":
            return ServiceResponseDTO(status_code=200, data=self._metrics)
        elif endpoint == "/v1/intelligence":
            asset = dto.payload.get("asset", "UNKNOWN")
            return ServiceResponseDTO(
                status_code=200,
                data={
                    "asset": asset,
                    "sentiment": "bullish",
                    "confidence_score": 0.88,
                    "compiled_at": datetime.now().isoformat()
                }
            )

        self._metrics["failed_requests"] += 1
        return ServiceResponseDTO(status_code=404, error_message=f"Endpoint '{endpoint}' not found.")

    def _validate_middleware(self, endpoint: str, payload: Dict[str, Any]) -> None:
        """Simulates endpoint parameter validation middleware."""
        # Forbidden keywords check
        forbidden_keywords = {"order", "position", "broker", "execute", "buy", "sell"}
        for k, v in payload.items():
            if isinstance(v, str):
                for fk in forbidden_keywords:
                    if fk in v.lower():
                        raise ValidationException(f"Middleware Security Rejection: Payload parameter '{k}' has forbidden term '{fk}'.")

        if endpoint == "/v1/intelligence":
            if "asset" not in payload:
                raise ValidationException("Middleware Validation: 'asset' is required for /v1/intelligence endpoint.")
