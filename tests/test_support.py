from data.factory import TestDataFactory
from data.objects import TestData
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
    test_data = load_test_data()
    assert isinstance(test_data, TestData)
    assert test_data.flight.origin_query
    assert test_data.hotel.location_query
    assert test_data.trip.origin_query


def test_shared_pytest_fixtures_are_registered(
    settings: Settings, test_data: TestData
) -> None:
    assert isinstance(settings, Settings)
    assert isinstance(test_data, TestData)


def test_data_factory_applies_nested_overrides_without_mutating_source() -> None:
    source = {
        "flight": {
            "fromSearch": "origin",
            "fromSelect": "Origin airport",
            "toSearch": "destination",
            "toSelect": "Destination airport",
            "departureDaysFromToday": 10,
            "passenger": {
                "firstName": "Test",
                "middleName": "Middle",
                "lastName": "User",
                "dob": "1990-01-01",
            },
            "contact": {
                "address": "123 Test St",
                "zip": "12345",
                "city": "Test City",
                "phone": "1234567890",
            },
        },
        "hotel": {
            "location": "hotel",
            "locationSelect": "Hotel location",
            "checkInDaysFromToday": 12,
            "stayLengthDays": 2,
            "guest": {"firstName": "Test", "lastName": "User", "age": "30"},
            "contact": {
                "address": "123 Test St",
                "zip": "12345",
                "city": "Test City",
                "phone": "1234567890",
            },
        },
        "trip": {
            "fromSearch": "origin",
            "fromSelect": "Origin",
            "toSearch": "destination",
            "toSelect": "Destination",
            "startDaysFromToday": 14,
            "tripLengthDays": 3,
        },
    }

    result = TestDataFactory.from_mapping(
        source,
        overrides={"flight": {"passenger": {"firstName": "Override"}}},
    )

    assert result.flight.passenger.first_name == "Override"
    assert source["flight"]["passenger"]["firstName"] == "Test"
