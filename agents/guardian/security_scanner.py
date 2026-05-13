import re

DANGER_PATTERNS = [
    (r'\b(otp|password|pin|cvv|upi pin|atm pin)\b', "REQUESTING_CREDENTIALS"),
    (r'\b(click here|urgent|immediate action|verify now|act now|limited time)\b', "PHISHING_URGENCY"),
    (r'\b(share your|send me your|provide your|give me your)\b.*\b(card|account|aadhaar|pan)\b', "REQUESTING_PII"),
    (r'\b(wire transfer|send money|transfer funds|gift card)\b', "FINANCIAL_MANIPULATION"),
]

POLICY_VIOLATIONS = [
    (r'\b(instant refund|immediate refund|refund guaranteed)\b', "UNAUTHORIZED_REFUND_PROMISE"),
    (r'\b(we will not investigate|no need to verify)\b', "SKIPPING_VERIFICATION"),
    (r'\b(bypass|override|ignore the policy)\b', "POLICY_OVERRIDE"),
]


def scan_query(text: str) -> list:
    text_lower = text.lower()
    flags = []
    for pattern, flag in DANGER_PATTERNS:
        if re.search(pattern, text_lower):
            flags.append(flag)
    return flags


def scan_answer(text: str) -> list:
    text_lower = text.lower()
    flags = []
    for pattern, flag in POLICY_VIOLATIONS + DANGER_PATTERNS:
        if re.search(pattern, text_lower):
            flags.append(flag)
    return flags
