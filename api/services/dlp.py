from __future__ import annotations

import re

from api.errors import APIError


_CARD_NUMBER = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
_CREDENTIAL_VALUE = re.compile(
    r"\b(?:otp|pin|cvv|cvc|password|passcode)\s*(?:is|:|=)\s*[A-Za-z0-9@#$%_-]{3,}\b",
    re.IGNORECASE,
)


def _luhn_valid(value: str) -> bool:
    digits = [int(character) for character in value if character.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    parity = len(digits) % 2
    for index, digit in enumerate(digits):
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def reject_sensitive_input(value: str) -> None:
    if _CREDENTIAL_VALUE.search(value):
        raise APIError(
            422,
            "sensitive_data_prohibited",
            "Do not send authentication credentials or secret values to AgentMesh.",
        )
    for match in _CARD_NUMBER.finditer(value):
        if _luhn_valid(match.group(0)):
            raise APIError(
                422,
                "sensitive_data_prohibited",
                "Do not send payment-card numbers to AgentMesh.",
            )
