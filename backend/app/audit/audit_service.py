from datetime import datetime


def record_gateway_event(event_type: str, data: dict) -> dict:
    """Build a gateway audit event.

    This placeholder returns the event object. A later version will append it
    to backend/logs/gateway-audit.jsonl.
    """
    return {
        "type": event_type,
        "created_at": datetime.utcnow().isoformat(),
        "data": data,
    }

