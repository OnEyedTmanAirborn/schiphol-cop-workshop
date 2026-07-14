from __future__ import annotations

from schiphol_ops.models import Direction, Flight, Status


def by_direction(flights: list[Flight], direction: Direction) -> list[Flight]:
    return [f for f in flights if f.direction is direction]


def by_terminal(flights: list[Flight], terminal: str) -> list[Flight]:
    return [f for f in flights if f.terminal == terminal.upper()]


def by_status(flights: list[Flight], status: Status) -> list[Flight]:
    return [f for f in flights if f.status is status]


def by_airline(flights: list[Flight], airline: str) -> list[Flight]:
    return [f for f in flights if f.airline == airline.upper()]


def by_city(flights: list[Flight], city: str) -> list[Flight]:
    return [f for f in flights if city.lower() in f.city.lower()]


def apply_filters(
    flights: list[Flight],
    *,
    direction: Direction | None = None,
    terminal: str | None = None,
    status: Status | None = None,
    airline: str | None = None,
    city: str | None = None,
) -> list[Flight]:
    result = flights
    if direction is not None:
        result = by_direction(result, direction)
    if terminal is not None:
        result = by_terminal(result, terminal)
    if status is not None:
        result = by_status(result, status)
    if airline is not None:
        result = by_airline(result, airline)
    if city is not None:
        result = by_city(result, city)
    return result


def find_flight(flights: list[Flight], number: str) -> Flight | None:
    wanted = number.replace(" ", "").upper()
    for flight in flights:
        if flight.number == wanted:
            return flight
    return None
