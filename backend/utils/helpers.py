import hashlib
import re


def sanitize_filename(filename: str) -> str:
    """Remove unsafe characters from filenames."""
    return re.sub(r"[^\w\s\-_\.]", "", filename).strip()


def compute_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def truncate_text(text: str, max_length: int = 500, suffix: str = "...") -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def safe_json_field(value, default=None):
    """Return value or default if value is None, ensuring safe JSON serialization."""
    if value is None:
        return default
    return value


def estimate_tokens(text: str) -> int:
    """Rough token estimation: ~4 chars per token."""
    return max(1, len(text) // 4)


def risk_level_to_int(risk_level: str) -> int:
    mapping = {"low": 1, "medium": 2, "high": 3, "critical": 4}
    return mapping.get(risk_level.lower(), 1)


def int_to_risk_level(risk_int: int) -> str:
    mapping = {1: "low", 2: "medium", 3: "high", 4: "critical"}
    return mapping.get(risk_int, "low")
