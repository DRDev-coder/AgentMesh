import pytest
from agents.guardian.security_scanner import scan_query, scan_answer


def test_credential_request_detected():
    flags = scan_query("Please share your OTP for verification")
    assert "REQUESTING_CREDENTIALS" in flags


def test_phishing_urgency_detected():
    flags = scan_query("URGENT: Click here to verify your account immediately")
    assert "PHISHING_URGENCY" in flags


def test_pii_request_detected():
    flags = scan_query("Send me your card number and Aadhaar")
    assert "REQUESTING_PII" in flags


def test_safe_query():
    flags = scan_query("How do I check my account balance?")
    assert len(flags) == 0


def test_unauthorized_refund_promise():
    flags = scan_answer("You will get an instant refund guaranteed, no investigation needed")
    assert "UNAUTHORIZED_REFUND_PROMISE" in flags
