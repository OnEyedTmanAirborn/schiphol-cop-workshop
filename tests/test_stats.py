from __future__ import annotations

import pytest

from schiphol_ops.models import Status
from schiphol_ops.stats import grouped_summaries, render_stats, summarize

from tests.conftest import make_flight


def test_summarize_counts_delayed_flights(sample_flights):
    summary = summarize(sample_flights)
    assert summary.total == 5
    assert summary.delayed == 1


def test_summarize_counts_cancelled_flights():
    flights = [
        make_flight(number="KL0001", status=Status.CANCELLED),
        make_flight(number="KL0002", status=Status.CANCELLED),
    ]
    assert summarize(flights).cancelled == 2


def test_average_delay_over_delayed_flights():
    flights = [
        make_flight(number="KL0001", delay_minutes=20, status=Status.DELAYED),
        make_flight(number="KL0002", delay_minutes=40, status=Status.DELAYED),
    ]
    assert summarize(flights).avg_delay == 30


def test_average_delay_is_zero_without_delays():
    flights = [make_flight(number="KL0001"), make_flight(number="KL0002")]
    assert summarize(flights).avg_delay == 0


def test_on_time_count_excludes_delayed():
    flights = [
        make_flight(number="KL0001"),
        make_flight(number="KL0002", status=Status.BOARDING),
        make_flight(number="KL0003", delay_minutes=15, status=Status.DELAYED),
    ]
    summary = summarize(flights)
    assert summary.on_time == 2
    assert summary.on_time_pct == 67


def test_summarize_with_mixed_statuses():
    """Regression test for issue #2: cancelled flights counted as on-time and avg delay computed over all flights."""
    flights = [
        make_flight(number="KL0001", status=Status.ON_TIME),
        make_flight(number="KL0002", status=Status.BOARDING),
        make_flight(number="KL0003", delay_minutes=30, status=Status.DELAYED),
        make_flight(number="KL0004", delay_minutes=50, status=Status.DELAYED),
        make_flight(number="KL0005", status=Status.CANCELLED),
    ]
    summary = summarize(flights)
    # Buckets should add up to total
    assert summary.total == 5
    assert summary.on_time == 2  # excludes cancelled
    assert summary.delayed == 2
    assert summary.cancelled == 1
    assert summary.on_time + summary.delayed + summary.cancelled == summary.total
    # Average delay should be computed over delayed flights only: (30+50)/2 = 40
    assert summary.avg_delay == 40


def test_summarize_empty_list():
    summary = summarize([])
    assert summary.total == 0
    assert summary.on_time_pct == 0


def test_grouped_summaries_by_airline(sample_flights):
    groups = grouped_summaries(sample_flights, "airline")
    assert set(groups) == {"KL", "HV", "DL"}
    assert groups["KL"].total == 3


def test_grouped_summaries_by_terminal(sample_flights):
    groups = grouped_summaries(sample_flights, "terminal")
    assert groups["E"].total == 2


def test_grouped_summaries_rejects_unknown_grouping(sample_flights):
    with pytest.raises(ValueError):
        grouped_summaries(sample_flights, "meal-preference")


def test_render_stats_mentions_overall_and_groups(sample_flights):
    output = render_stats(sample_flights, by="airline")
    assert output.startswith("OPERATIONS SUMMARY")
    assert "Overall:" in output
    assert "KLM" in output
