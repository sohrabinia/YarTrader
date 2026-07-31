from enum import Enum

class PositionStatus(str, Enum):
    OPEN = "OPEN"
    MONITORING = "MONITORING"
    CLOSED = "CLOSED"

class PositionResult(str, Enum):
    WIN = "WIN"
    LOSS = "LOSS"
    NEUTRAL = "NEUTRAL"
