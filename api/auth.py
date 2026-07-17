from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Header, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.config import Settings, get_settings
from api.db.models import PlatformRole, UserProfile
from api.errors import APIError


@dataclass(frozen=True, slots=True)
class Principal:
    user_id: str
    email: str
    email_verified: bool
    assurance_level: str

    @property
    def has_mfa(self) -> bool:
        return self.assurance_level == "aal2"


class SupabaseTokenVerifier:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.jwks = jwt.PyJWKClient(settings.supabase_jwks_url, cache_keys=True)

    def verify(self, token: str) -> Principal:
        try:
            signing_key = self.jwks.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256", "ES256"],
                audience=self.settings.supabase_jwt_audience,
                issuer=f"{self.settings.supabase_url}/auth/v1",
                options={"require": ["exp", "iat", "sub"]},
            )
        except jwt.PyJWTError as exc:
            raise APIError(401, "invalid_session", "Authentication is invalid or expired.") from exc
        email = str(claims.get("email") or "").strip().lower()
        if not email:
            raise APIError(401, "invalid_session", "The session has no verified email identity.")
        return Principal(
            user_id=str(claims["sub"]),
            email=email,
            email_verified=bool(
                claims.get("email_confirmed_at")
                or claims.get("email_verified")
                or claims.get("user_metadata", {}).get("email_verified")
            ),
            assurance_level=str(claims.get("aal") or "aal1"),
        )


@lru_cache(maxsize=4)
def _verifier(settings: Settings | None = None) -> SupabaseTokenVerifier:
    return SupabaseTokenVerifier(settings or get_settings())


def _bearer_value(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() != "bearer" or not value:
        return None
    return value.strip()


def get_principal(
    request: Request,
    authorization: str | None = Header(default=None),
    x_dev_user: str | None = Header(default=None),
    x_dev_email: str | None = Header(default=None),
    x_dev_aal: str | None = Header(default=None),
) -> Principal:
    settings: Settings = request.app.state.settings
    if settings.auth_mode == "development":
        if not x_dev_user:
            raise APIError(
                401,
                "authentication_required",
                "Set X-Dev-User for local development authentication.",
            )
        email = (x_dev_email or f"{x_dev_user}@example.local").strip().lower()
        principal = Principal(
            user_id=x_dev_user[:128],
            email=email[:320],
            email_verified=True,
            assurance_level=x_dev_aal or "aal1",
        )
        _rate_limit_principal(request, principal)
        return principal

    token = _bearer_value(authorization)
    if not token:
        raise APIError(401, "authentication_required", "Sign in to continue.")
    principal = _verifier(settings).verify(token)
    _rate_limit_principal(request, principal)
    return principal


def _rate_limit_principal(request: Request, principal: Principal) -> None:
    limiter = getattr(request.app.state, "rate_limiter", None)
    if limiter is None:
        return
    limit = request.app.state.settings.public_rate_limit_per_minute
    client_ip = request.client.host if request.client else "unknown"
    limiter.check(f"dashboard-ip:{client_ip}", limit * 6)
    limiter.check(f"user:{principal.user_id}", limit * 4)


def sync_user_profile(session: Session, principal: Principal) -> UserProfile:
    profile = session.get(UserProfile, principal.user_id)
    if profile is None:
        profile = UserProfile(
            auth_user_id=principal.user_id,
            email=principal.email,
            email_verified=principal.email_verified,
        )
        session.add(profile)
        session.flush()
    else:
        profile.email = principal.email
        profile.email_verified = principal.email_verified
    return profile


def require_verified_principal(principal: Principal) -> Principal:
    if not principal.email_verified:
        raise APIError(403, "email_verification_required", "Verify your email to continue.")
    return principal


def require_platform_admin(session: Session, principal: Principal) -> PlatformRole:
    if not principal.has_mfa:
        raise APIError(403, "mfa_required", "Platform administration requires MFA.")
    value = session.scalar(
        select(PlatformRole).where(PlatformRole.auth_user_id == principal.user_id)
    )
    if value is None:
        raise APIError(403, "platform_access_denied", "Platform access is not permitted.")
    return value
