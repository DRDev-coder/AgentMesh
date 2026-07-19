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


def test_staging_rejects_local_storage_with_separate_worker() -> None:
    settings = replace(
        get_settings(),
        environment="staging",
        object_storage_backend="local",
        tasks_eager=False,
    )

    with pytest.raises(RuntimeError, match="requires shared object storage"):
        settings.validate()


def test_staging_allows_local_storage_for_eager_demo_ingestion() -> None:
    settings = replace(
        get_settings(),
        environment="staging",
        object_storage_backend="local",
        tasks_eager=True,
    )

    settings.validate()
