# Centralized Timeframe Registry - Single Source of Truth
# All validation, mapping, and core intelligence layers use this registry.

SUPPORTED_TIMEFRAMES = {
    "M1": {
        "minutes": 1,
        "category": "intraday"
    },
    "M5": {
        "minutes": 5,
        "category": "intraday"
    },
    "M15": {
        "minutes": 15,
        "category": "intraday"
    },
    "H1": {
        "minutes": 60,
        "category": "intraday"
    },
    "H4": {
        "minutes": 240,
        "category": "swing"
    },
    "D1": {
        "minutes": 1440,
        "category": "daily"
    },
    "W1": {
        "minutes": 10080,
        "category": "macro"
    },
    "MN1": {
        "minutes": 43200,
        "category": "macro"
    }
}
