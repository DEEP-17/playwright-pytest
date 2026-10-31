import copy
import json
from collections.abc import Mapping

from data.objects import (
    ContactData,
    FlightData,
    HotelData,
    HotelGuestData,
    PassengerData,
    TestData,
    TripData,
)
from utils.config import PROJECT_ROOT


class TestDataFactory:
    @classmethod
    def create(
        cls, overrides: Mapping[str, object] | None = None
    ) -> TestData:
        path = PROJECT_ROOT / "data" / "test_data.json"
        with path.open(encoding="utf-8") as data_file:
            data = json.load(data_file)
        if not isinstance(data, dict):
            raise ValueError(f"Test data must be a JSON object: {path}")
        return cls.from_mapping(data, overrides=overrides)

    @classmethod
    def from_mapping(
        cls,
        data: Mapping[str, object],
        *,
        overrides: Mapping[str, object] | None = None,
    ) -> TestData:
        merged = copy.deepcopy(dict(data))
        if overrides is not None:
            _merge_mapping(merged, overrides)

        flight = _mapping(merged, "flight")
        passenger = _mapping(flight, "passenger")
        hotel = _mapping(merged, "hotel")
        guest = _mapping(hotel, "guest")
        trip = _mapping(merged, "trip")

        return TestData(
            flight=FlightData(
                origin_query=_string(flight, "fromSearch"),
                origin_option=_string(flight, "fromSelect"),
                destination_query=_string(flight, "toSearch"),
                destination_option=_string(flight, "toSelect"),
                departure_days_from_today=_integer(
                    flight, "departureDaysFromToday"
                ),
                passenger=PassengerData(
                    first_name=_string(passenger, "firstName"),
                    middle_name=_string(passenger, "middleName"),
                    last_name=_string(passenger, "lastName"),
                    date_of_birth=_string(passenger, "dob"),
                ),
                contact=_contact(_mapping(flight, "contact")),
            ),
            hotel=HotelData(
                location_query=_string(hotel, "location"),
                location_option=_string(hotel, "locationSelect"),
                check_in_days_from_today=_integer(
                    hotel, "checkInDaysFromToday"
                ),
                stay_length_days=_integer(hotel, "stayLengthDays"),
                guest=HotelGuestData(
                    first_name=_string(guest, "firstName"),
                    last_name=_string(guest, "lastName"),
                    age=_string(guest, "age"),
                ),
                contact=_contact(_mapping(hotel, "contact")),
            ),
            trip=TripData(
                origin_query=_string(trip, "fromSearch"),
                origin_option=_string(trip, "fromSelect"),
                destination_query=_string(trip, "toSearch"),
                destination_option=_string(trip, "toSelect"),
                start_days_from_today=_integer(trip, "startDaysFromToday"),
                trip_length_days=_integer(trip, "tripLengthDays"),
            ),
        )


def _merge_mapping(
    destination: dict[str, object], overrides: Mapping[str, object]
) -> None:
    for key, value in overrides.items():
        existing = destination.get(key)
        if isinstance(existing, dict) and isinstance(value, Mapping):
            _merge_mapping(existing, value)
        else:
            destination[key] = copy.deepcopy(value)


def _mapping(data: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = data.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"Test data field '{key}' must be an object.")
    return value


def _string(data: Mapping[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Test data field '{key}' must be a non-empty string.")
    return value


def _integer(data: Mapping[str, object], key: str) -> int:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Test data field '{key}' must be an integer.")
    return value


def _contact(data: Mapping[str, object]) -> ContactData:
    return ContactData(
        address=_string(data, "address"),
        zip_code=_string(data, "zip"),
        city=_string(data, "city"),
        phone=_string(data, "phone"),
    )
