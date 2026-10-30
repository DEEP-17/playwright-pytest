from typing import Any

from utils.config import Settings
from utils.test_data import load_test_data


def test_settings_are_read_from_environment_values() -> None:
    settings = Settings.from_environment(
        {
            "BASE_URL": "https://example.test/",
            "USER_EMAIL": "test@example.test",
            "USER_PASSWORD": "test-password",
        }
    )

    assert settings.base_url == "https://example.test"
    assert settings.user_email == "test@example.test"
    assert settings.user_password == "test-password"


def test_test_data_contains_all_end_to_end_scenarios() -> None:
    assert set(load_test_data()) == {"flight", "hotel", "trip"}


def test_shared_pytest_fixtures_are_registered(
    settings: Settings, test_data: dict[str, Any]
) -> None:
    assert isinstance(settings, Settings)
    assert set(test_data) == {"flight", "hotel", "trip"}
