from dataclasses import replace

import pytest

from api.config import get_settings


def test_production_rejects_razorpay_demo_mode() -> None:
    settings = replace(
        get_settings(),
        environment="production",
        razorpay_demo_mode=True,
    )

    with pytest.raises(RuntimeError, match="RAZORPAY_DEMO_MODE is forbidden"):
        settings.validate()
