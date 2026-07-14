from __future__ import annotations

from schiphol_ops.filters import (
    apply_filters,
    by_airline,
    by_city,
    by_delay,
    by_destination,
    by_direction,
    by_status,
    by_terminal,
    by_time,
    find_flight,
)
from schiphol_ops.models import Direction, Status

from tests.conftest import make_flight


def test_by_direction_splits_departures_and_arrivals(sample_flights):
    departures = by_direction(sample_flights, Direction.DEPARTURE)
    arrivals = by_direction(sample_flights, Direction.ARRIVAL)
    assert {f.number for f in departures} == {"KL1001", "HV5821", "KL0643"}
    assert {f.number for f in arrivals} == {"KL1002", "DL0046"}


def test_by_terminal_is_case_insensitive_on_input(sample_flights):
    assert [f.number for f in by_terminal(sample_flights, "e")] == ["KL0643", "DL0046"]


def test_by_status(sample_flights):
    delayed = by_status(sample_flights, Status.DELAYED)
    assert [f.number for f in delayed] == ["KL0643"]


def test_by_airline_is_case_insensitive_on_input(sample_flights):
    assert {f.number for f in by_airline(sample_flights, "kl")} == {
        "KL1001",
        "KL0643",
        "KL1002",
    }


def test_by_city_matches_the_board_entry(sample_flights):
    matches = by_city(sample_flights, "London (LHR)")
    assert {f.number for f in matches} == {"KL1001", "KL1002"}


def test_by_city_no_match_returns_empty_list(sample_flights):
    assert by_city(sample_flights, "Atlantis (ATL)") == []


def test_by_city_case_insensitive_substring_match(sample_flights):
    """Regression test for OPS-3: city filter should match case-insensitively."""
    # Lowercase input should match flights with "London (LHR)"
    matches = by_city(sample_flights, "london")
    assert {f.number for f in matches} == {"KL1001", "KL1002"}
    
    # Partial match with unique substring
    matches = by_city(sample_flights, "lhr")
    assert {f.number for f in matches} == {"KL1001", "KL1002"}
    
    # Mixed case partial match
    matches = by_city(sample_flights, "new york")
    assert {f.number for f in matches} == {"KL0643", "DL0046"}


def test_by_time_orders_by_scheduled_then_flight_number(sample_flights):
    assert [f.number for f in by_time(sample_flights)] == [
        "KL1001",
        "HV5821",
        "KL0643",
        "DL0046",
        "KL1002",
    ]


def test_by_destination_orders_case_insensitive_city_name(sample_flights):
    assert [f.number for f in by_destination(sample_flights)] == [
        "HV5821",
        "KL1001",
        "KL1002",
        "KL0643",
        "DL0046",
    ]


def test_by_delay_orders_delayed_first_then_scheduled(sample_flights):
    assert [f.number for f in by_delay(sample_flights)] == [
        "KL0643",
        "KL1001",
        "HV5821",
        "DL0046",
        "KL1002",
    ]


def test_apply_filters_combines_criteria(sample_flights):
    result = apply_filters(
        sample_flights,
        direction=Direction.DEPARTURE,
        terminal="E",
        airline="KL",
    )
    assert [f.number for f in result] == ["KL0643"]


def test_apply_filters_without_criteria_returns_everything(sample_flights):
    assert apply_filters(sample_flights) == sample_flights


def test_apply_filters_sorts_after_filtering(sample_flights):
    result = apply_filters(
        sample_flights,
        direction=Direction.DEPARTURE,
        sort_by="destination",
    )
    assert [f.number for f in result] == ["HV5821", "KL1001", "KL0643"]


def test_find_flight_ignores_case_and_spaces(sample_flights):
    assert find_flight(sample_flights, "kl 1001") == sample_flights[0]


def test_find_flight_returns_none_for_unknown_number(sample_flights):
    assert find_flight(sample_flights, "XX9999") is None


def test_terminal_filter_on_flight_with_delay():
    flight = make_flight(terminal="F", gate="F07", delay_minutes=30, status=Status.DELAYED)
    assert by_terminal([flight], "F") == [flight]
