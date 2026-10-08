"""Input/output guardrails: prompt-injection screening and PII redaction."""
import re

_INJECTION = re.compile(
    r"ignore (all |any )?(previous|prior|above) (instructions|rules)|reveal (your )?(system )?prompt|you are now|disregard .* (instructions|rules)",
    re.I,
)
_CARD = re.compile(r"\b(?:\d[ -]?){13,16}\b")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


def is_injection(text: str) -> bool:
    return bool(_INJECTION.search(text))


def redact_pii(text: str) -> str:
    text = _CARD.sub("[CARD]", text)
    text = _SSN.sub("[SSN]", text)
    return _EMAIL.sub("[EMAIL]", text)
