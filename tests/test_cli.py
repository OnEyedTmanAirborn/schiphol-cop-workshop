from __future__ import annotations

import pytest

from schiphol_ops.cli import main


def test_departures_shows_only_departures(cli_data, capsys):
    assert main(["departures"]) == 0
    output = capsys.readouterr().out
    assert "DEPARTURES - Schiphol (AMS)" in output
    assert "KL1001" in output
    assert "DL0046" not in output


def test_arrivals_shows_only_arrivals(cli_data, capsys):
    assert main(["arrivals"]) == 0
    output = capsys.readouterr().out
    assert "ARRIVALS - Schiphol (AMS)" in output
    assert "DL0046" in output
    assert "KL1001" not in output


def test_departures_terminal_filter(cli_data, capsys):
    assert main(["departures", "--terminal", "E"]) == 0
    output = capsys.readouterr().out
    assert "KL0643" in output
    assert "KL1001" not in output


def test_departures_status_filter(cli_data, capsys):
    assert main(["departures", "--status", "delayed"]) == 0
    output = capsys.readouterr().out
    assert "KL0643" in output
    assert "Showing 1 flight -" in output


def test_departures_airline_filter_accepts_lowercase(cli_data, capsys):
    assert main(["departures", "--airline", "hv"]) == 0
    output = capsys.readouterr().out
    assert "HV5821" in output
    assert "KL1001" not in output


def test_departures_sort_by_destination(cli_data, capsys):
    assert main(["departures", "--sort", "destination"]) == 0
    output = capsys.readouterr().out
    assert output.index("HV5821") < output.index("KL1001")
    assert output.index("KL1001") < output.index("KL0643")


def test_departures_sort_by_delay(cli_data, capsys):
    assert main(["departures", "--sort", "delay"]) == 0
    output = capsys.readouterr().out
    assert output.index("KL0643") < output.index("KL1001")
    assert output.index("KL1001") < output.index("HV5821")


def test_departures_sort_combines_with_airline_filter(cli_data, capsys):
    assert main(["departures", "--airline", "KL", "--sort", "delay"]) == 0
    output = capsys.readouterr().out
    assert output.index("KL0643") < output.index("KL1001")


def test_no_matching_flights_still_exits_zero(cli_data, capsys):
    assert main(["departures", "--terminal", "G"]) == 0
    assert "No flights match the given filters." in capsys.readouterr().out


def test_rejects_unknown_status(cli_data):
    with pytest.raises(SystemExit) as excinfo:
        main(["departures", "--status", "vanished"])
    assert excinfo.value.code == 2


def test_rejects_unknown_sort_value(cli_data):
    with pytest.raises(SystemExit) as excinfo:
        main(["departures", "--sort", "speed"])
    assert excinfo.value.code == 2


def test_search_finds_flight(cli_data, capsys):
    assert main(["search", "kl1001"]) == 0
    output = capsys.readouterr().out
    assert "KL1001 (KLM)" in output
    assert "London (LHR)" in output


def test_search_unknown_flight_exits_one(cli_data, capsys):
    assert main(["search", "XX9999"]) == 1
    assert "No flight found" in capsys.readouterr().out


def test_stats_overall(cli_data, capsys):
    assert main(["stats"]) == 0
    output = capsys.readouterr().out
    assert "OPERATIONS SUMMARY" in output
    assert "7 flights" in output


def test_stats_by_airline(cli_data, capsys):
    assert main(["stats", "--by", "airline"]) == 0
    output = capsys.readouterr().out
    assert "By airline:" in output
    assert "Transavia" in output


def test_gates_occupancy_view(cli_data, capsys):
    assert main(["gates"]) == 0
    output = capsys.readouterr().out
    assert "GATE OCCUPANCY" in output
    assert "D04" in output


def test_gates_pier_filter(cli_data, capsys):
    assert main(["gates", "--pier", "B"]) == 0
    output = capsys.readouterr().out
    assert "B16" in output
    assert "D04" not in output


def test_gates_conflicts_all_clear_in_fixture(cli_data, capsys):
    assert main(["gates", "--conflicts"]) == 0
    assert "No gate conflicts detected." in capsys.readouterr().out
