import re
import unicodedata

_LEET_TRANSLATION = str.maketrans({
    "0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t",
    "@": "a", "$": "s",
})


GLOBAL_QUERY_PATTERNS = [
    (r"\b(click here|verify now|limited time|account (?:will be )?(?:closed|blocked))\b", "PHISHING_URGENCY"),
    (r"\b(ignore|disregard|forget|override|disable|evade|reveal|unrestricted|developer mode|system command|role[ -]?play|pretend).{0,100}\b(system prompt|secret prompt|private instructions?|previous instructions?|security polic(?:y|ies)|bank rules?|safeguards?|guardian|policy checks?|safety filters?|restrictions?|identity checks?|verification)\b", "PROMPT_INJECTION"),
    (r"\b(print|provide|expose|output|reveal).{0,80}\b(system prompt|secret prompt|private instructions?|customer passwords?|account secrets?)\b", "PROMPT_INJECTION"),
    (r"\b(mark (?:this )?request safe|approve my transfer|authorize the payment|no restrictions)\b", "PROMPT_INJECTION"),
    (r"\b(bypass|skip|disable|evade|override).{0,40}\b(verification|identity check|security|policy|controls?)\b", "POLICY_OVERRIDE"),
]

FINANCE_QUERY_PATTERNS = [
    (r"\b(share|send|provide|give|tell).{0,40}\b(card number|account number|aadhaar|pan number)\b", "REQUESTING_PII"),
]

GLOBAL_ANSWER_PATTERNS = [
    (r"\b(click here|verify now|limited time)\b", "PHISHING_URGENCY"),
    (r"\b(wire transfer|send money|move money|transfer funds?|buy (?:a )?gift card|crypto transfer)\b", "UNSAFE_TRANSFER_INSTRUCTIONS"),
    (r"\b(bypass|skip|disable|evade|override).{0,40}\b(verification|identity check|security|policy|controls?)\b", "POLICY_OVERRIDE"),
]

FINANCE_ANSWER_PATTERNS = [
    (r"\b(refund (?:is )?guaranteed|guarantee (?:a )?refund|guaranteed (?:an )?instant refund)\b", "UNAUTHORIZED_REFUND_PROMISE"),
    (r"\b(we will not investigate|no need to verify|skip (?:the )?investigation)\b", "SKIPPING_VERIFICATION"),
]

HEALTHCARE_QUERY_PATTERNS = [
    (
        r"\b(diagnose me|what disease do i have|prescribe|change my dosage|stop taking my medication)\b",
        "MEDICAL_DIAGNOSIS_REQUEST",
    ),
]

HEALTHCARE_ANSWER_PATTERNS = [
    (
        r"\b(you (?:definitely )?have|your diagnosis is|take \d+ ?mg|stop taking your medication)\b",
        "UNSAFE_MEDICAL_GUIDANCE",
    ),
]

ECOMMERCE_ANSWER_PATTERNS = [
    (
        r"\b(pay|send money).{0,40}\b(outside (?:the )?(?:marketplace|platform)|gift card|crypto)\b",
        "OFF_PLATFORM_PAYMENT",
    ),
    (
        r"\b(refund (?:is )?guaranteed|guaranteed full refund)\b",
        "UNAUTHORIZED_REFUND_PROMISE",
    ),
]

# Compatibility constants retain the original direct-scanner behavior.
QUERY_PATTERNS = [*GLOBAL_QUERY_PATTERNS, *FINANCE_QUERY_PATTERNS]
ANSWER_PATTERNS = [*GLOBAL_ANSWER_PATTERNS, *FINANCE_ANSWER_PATTERNS]

CRITICAL_VIOLATIONS = {
    "REQUESTING_CREDENTIALS",
    "PHISHING_URGENCY",
    "UNSAFE_TRANSFER_INSTRUCTIONS",
    "PROMPT_INJECTION",
    "POLICY_OVERRIDE",
}

WARNING_VIOLATIONS = {
    "REQUESTING_PII",
    "UNAUTHORIZED_REFUND_PROMISE",
    "SKIPPING_VERIFICATION",
    "MEDICAL_DIAGNOSIS_REQUEST",
}

CRITICAL_VIOLATIONS.update({"UNSAFE_MEDICAL_GUIDANCE", "OFF_PLATFORM_PAYMENT"})


def normalize_security_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    normalized = normalized.lower().translate(_LEET_TRANSLATION)
    # Preserve word boundaries so separator-obfuscated phrases such as
    # "ignore-system-prompt" still match the deterministic rules. Credential
    # detection separately compacts the normalized text when appropriate.
    normalized = re.sub(r"[._\-]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _scan(text: str, patterns: list[tuple[str, str]]) -> list[str]:
    normalized = normalize_security_text(text)
    return sorted(
        {flag for pattern, flag in patterns if re.search(pattern, normalized)}
    )


def _contains_credential_request(text: str, *, answer: bool = False) -> bool:
    normalized = normalize_security_text(text)
    # Match a credential as a word or an intentionally separator-obfuscated
    # sequence. Compacting the entire sentence caused cross-word false positives:
    # for example, "does not produce" contains the letters "otp" after all
    # spaces are removed.
    credential_present = bool(
        re.search(
            r"\b(?:"
            r"o\s*t\s*p|c\s*v\s*v|c\s*v\s*c|p\s*i\s*n|"
            r"password|passcode|"
            r"one\s*time\s*(?:code|pass\s*code|passcode|password)|"
            r"verification\s*code|security\s*code|"
            r"upi\s*pin|atm\s*pin"
            r")\b",
            normalized,
        )
    )
    if not credential_present:
        return False

    if answer and re.search(
        r"\b(never|do not|don't|must not|should not|cannot|only (?:the )?bank)\b.{0,60}\b(request|share|send|provide|give|reveal|disclose)",
        normalized,
    ):
        return False

    safe_inquiry = re.search(
        r"\b(does (?:the )?bank ever ask|can (?:bank )?(?:staff|support|employees?) request|which channels? must never|who initiates legitimate|according to policy)\b",
        normalized,
    )
    if safe_inquiry:
        return False

    unsafe_context = re.search(
        r"\b(share|send|provide|give|tell|reveal|disclose|collect|output|expose|"
        r"enter|forward|paste|text|type|submit|confirm|dictate|ask the customer|"
        r"request my|must disclose)\b",
        normalized,
    )
    possessive_request = re.search(r"\b(?:i|we|support|agent|caller)\s+(?:need|want|require)\s+your\b", normalized)
    return bool(unsafe_context or possessive_request)


def _contains_unsafe_transfer_request(text: str) -> bool:
    normalized = normalize_security_text(text)
    transfer_action = re.search(
        r"\b(wire|send|move|transfer)\b.{0,20}\b(money|funds?)\b|"
        r"\b(buy (?:a )?gift card|crypto transfer)\b",
        normalized,
    )
    if not transfer_action:
        return False
    unsafe_context = re.search(
        r"\b(unverified|support account|someone else(?:'s)?|another person(?:'s)?|"
        r"without verification|skip verification|bypass verification|stranger|caller|"
        r"secretly|no restrictions?)\b",
        normalized,
    )
    return bool(unsafe_context)


def scan_query(text: str, rule_packs: set[str] | None = None) -> list:
    patterns = GLOBAL_QUERY_PATTERNS
    if rule_packs is None or "FINANCE_SUPPORT" in rule_packs:
        patterns = [*patterns, *FINANCE_QUERY_PATTERNS]
    if rule_packs and "HEALTHCARE_INFORMATION" in rule_packs:
        patterns = [*patterns, *HEALTHCARE_QUERY_PATTERNS]
    flags = _scan(text, patterns)
    if _contains_credential_request(text):
        flags.append("REQUESTING_CREDENTIALS")
    if _contains_unsafe_transfer_request(text):
        flags.append("UNSAFE_TRANSFER_INSTRUCTIONS")
    return sorted(set(flags))


def scan_answer(text: str, rule_packs: set[str] | None = None) -> list:
    patterns = GLOBAL_ANSWER_PATTERNS
    if rule_packs is None or "FINANCE_SUPPORT" in rule_packs:
        patterns = [*patterns, *FINANCE_ANSWER_PATTERNS]
    if rule_packs and "HEALTHCARE_INFORMATION" in rule_packs:
        patterns = [*patterns, *HEALTHCARE_ANSWER_PATTERNS]
    if rule_packs and "ECOMMERCE_SUPPORT" in rule_packs:
        patterns = [*patterns, *ECOMMERCE_ANSWER_PATTERNS]
    flags = _scan(text, patterns)
    if _contains_credential_request(text, answer=True):
        flags.append("REQUESTING_CREDENTIALS")
    return sorted(set(flags))


def severity_for(violations: list[str]) -> str:
    violation_set = set(violations)
    if violation_set & CRITICAL_VIOLATIONS:
        return "CRITICAL"
    if violation_set & WARNING_VIOLATIONS:
        return "WARNING"
    return "SAFE"
