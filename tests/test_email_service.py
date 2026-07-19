from __future__ import annotations

import resend

from api.config import Settings
from api.services.email import _render_email, _send_with_resend


def test_team_invitation_email_escapes_values() -> None:
    subject, html, text = _render_email(
        "team_invitation",
        {
            "role": "admin<script>",
            "invite_url": "https://app.example.com/accept?token=a&b=c",
        },
    )

    assert subject == "You're invited to AgentMesh"
    assert "<script>" not in html
    assert "admin&lt;script&gt;" in html.lower()
    assert "a&amp;b=c" in html
    assert "https://app.example.com/accept?token=a&b=c" in text


def test_resend_payload_uses_runtime_configuration(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("RESEND_API_KEY", "re_test_value")
    monkeypatch.setenv("RESEND_FROM", "AgentMesh <onboarding@resend.dev>")
    settings = Settings.from_env()
    captured: dict = {}

    def fake_send(payload: dict) -> dict:
        captured.update(payload)
        return {"id": "email_test_123"}

    monkeypatch.setattr(resend.Emails, "send", fake_send)

    message_id = _send_with_resend(
        settings,
        "owner@example.org",
        "review_required",
        {"escalation_id": "esc_123", "priority": "high"},
    )

    assert resend.api_key == "re_test_value"
    assert message_id == "email_test_123"
    assert captured["from"] == "AgentMesh <onboarding@resend.dev>"
    assert captured["to"] == ["owner@example.org"]
    assert captured["subject"] == "AgentMesh review required: HIGH"
    assert "esc_123" in captured["html"]
