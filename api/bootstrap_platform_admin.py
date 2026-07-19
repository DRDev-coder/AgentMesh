from __future__ import annotations

import argparse

from api.config import get_settings
from api.db.base import Database
from api.db.models import PlatformRole, UserProfile
from api.services.audit import record_audit
from api.tenancy import TenantContext, set_platform_database_context


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Grant platform administration to an existing verified identity."
    )
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--granted-by", required=True)
    args = parser.parse_args()
    database = Database(get_settings())
    with database.session() as session:
        set_platform_database_context(session, True)
        user = session.get(UserProfile, args.user_id)
        if user is None or not user.email_verified:
            raise SystemExit("The user must sign in and verify email before bootstrap.")
        role = session.get(PlatformRole, args.user_id)
        if role is None:
            session.add(
                PlatformRole(
                    auth_user_id=args.user_id,
                    role="PLATFORM_ADMIN",
                    granted_by=args.granted_by,
                )
            )
            record_audit(
                session,
                TenantContext(
                    organization_id=None,
                    workspace_id=None,
                    actor_id=args.granted_by,
                    actor_type="BOOTSTRAP_COMMAND",
                    role="platform",
                ),
                "platform.role_granted",
                "platform_role",
                args.user_id,
                {"role": "PLATFORM_ADMIN"},
            )
    print(f"Platform admin granted to {args.user_id}.")


if __name__ == "__main__":
    main()
