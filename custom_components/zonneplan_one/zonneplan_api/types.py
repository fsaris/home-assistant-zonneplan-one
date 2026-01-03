from typing import Any, TypedDict


class ZonneplanContract(TypedDict):
    uuid: str
    label: str
    type: str
    start_date: str
    end_date: str | None
    meta: dict[str, Any]


class ZonneplanConnection(TypedDict):
    uuid: str
    ean: str | None
    market_segment: str
    contracts: list[ZonneplanContract]
    features: list[dict[str, Any]]
    buttons: list[Any]


class ZonneplanAddress(TypedDict):
    id: str
    zipcode: str
    street: str
    number: str
    addition: str
    city: str
    sunrise: str
    sunset: str


class ZonneplanAddressGroup(TypedDict):
    uuid: str
    connections: list[ZonneplanConnection]
    address: ZonneplanAddress
    is_representative: bool
    organization_uuid: str


class ZonneplanUserAccount(TypedDict):
    initials: str | None
    uuid: str
    email: str
    first_name: str
    full_name: str
    is_representative: bool


class ZonneplanAccountsData(TypedDict):
    user_account: ZonneplanUserAccount
    address_groups: list[ZonneplanAddressGroup]
