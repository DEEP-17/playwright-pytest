from dataclasses import dataclass


@dataclass(frozen=True)
class PassengerData:
    first_name: str
    middle_name: str
    last_name: str
    date_of_birth: str


@dataclass(frozen=True)
class ContactData:
    address: str
    zip_code: str
    city: str
    phone: str


@dataclass(frozen=True)
class FlightData:
    origin_query: str
    origin_option: str
    destination_query: str
    destination_option: str
    departure_days_from_today: int
    passenger: PassengerData
    contact: ContactData


@dataclass(frozen=True)
class HotelGuestData:
    first_name: str
    last_name: str
    age: str


@dataclass(frozen=True)
class HotelData:
    location_query: str
    location_option: str
    check_in_days_from_today: int
    stay_length_days: int
    guest: HotelGuestData
    contact: ContactData


@dataclass(frozen=True)
class TripData:
    origin_query: str
    origin_option: str
    destination_query: str
    destination_option: str
    start_days_from_today: int
    trip_length_days: int


@dataclass(frozen=True)
class TestData:
    __test__ = False

    flight: FlightData
    hotel: HotelData
    trip: TripData
