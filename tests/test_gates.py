from __future__ import annotations

from datetime import time

from schiphol_ops.gates import (
    find_conflicts,
    occupancies_by_gate,
    occupancy_for,
    render_conflicts,
    render_gates,
)
from schiphol_ops.models import Direction, Gate, Status

from tests.conftest import make_flight


def test_departure_occupies_gate_before_pushback():
    flight = make_flight(scheduled=time(10, 0))
    slot = occupancy_for(flight)
    assert slot.window == "09:15–10:10"


def test_arrival_occupies_gate_for_deboarding():
    flight = make_flight(direction=Direction.ARRIVAL, scheduled=time(10, 0))
    slot = occupancy_for(flight)
    assert slot.window == "09:55–10:40"


def test_delay_shifts_the_occupancy_window():
    flight = make_flight(scheduled=time(10, 0), delay_minutes=30, status=Status.DELAYED)
    slot = occupancy_for(flight)
    assert slot.window == "09:45–10:40"


def test_cancelled_flights_do_not_occupy_gates():
    flight = make_flight(status=Status.CANCELLED)
    assert occupancies_by_gate([flight]) == {}


def test_overlapping_flights_at_same_gate_conflict():
    flights = [
        make_flight(number="HV6011", gate="H04", scheduled=time(14, 20)),
        make_flight(number="HV6923", gate="H04", scheduled=time(15, 0)),
    ]
    conflicts = find_conflicts(flights)
    assert len(conflicts) == 1
    assert conflicts[0].gate == "H04"
    assert conflicts[0].first.flight.number == "HV6011"
    assert conflicts[0].second.flight.number == "HV6923"


def test_back_to_back_flights_do_not_conflict():
    # First window ends 10:10, second starts 10:10 - a legal tight turnaround.
    flights = [
        make_flight(number="KL0001", gate="D04", scheduled=time(10, 0)),
        make_flight(number="KL0002", gate="D04", scheduled=time(10, 55)),
    ]
    assert find_conflicts(flights) == []


def test_same_window_different_gates_do_not_conflict():
    flights = [
        make_flight(number="KL0001", gate="D04", scheduled=time(10, 0)),
        make_flight(number="KL0002", gate="D07", scheduled=time(10, 0)),
    ]
    assert find_conflicts(flights) == []


def test_non_adjacent_flights_conflict():
    # Regression test for the bug where only adjacent occupancies were checked.
    # Flight A: 13:15–14:10, Flight B: 13:45–14:40, Flight C: 14:15–15:10
    # A overlaps B, but B does NOT overlap C. However, A DOES overlap C (14:15–14:10 is invalid but 14:00–14:10 overlaps 14:15).
    # Actually let me recalculate: A ends at 14:10, C starts at 14:15, so they don't overlap.
    # Let me design this better: A (14:00 sched → 13:15–14:10), B (14:30 → 13:45–14:40), C (15:00 → 14:15–15:10)
    # Wait, C at 15:00 → 14:15–15:10, and A ends at 14:10, so no overlap.
    # Let me try: A (14:00 → 13:15–14:10), B (15:30 → 14:45–15:40), C (15:15 → 14:30–15:25)
    # A ends 14:10, C starts 14:30 (no overlap). B starts 14:45, C ends 15:25 (overlap).
    # I need A and C to overlap but not A and B, and not B and C.
    # A (14:00 → 13:15–14:10), B (14:25 → 13:40–14:35), C (14:55 → 14:10–15:00)
    # A ends 14:10, C starts 14:10 - that's back to back, not a conflict.
    # Let me use arrivals and departures with delays:
    # A departure at 14:00 → 13:15–14:10
    # B arrival at 14:20 → 14:15–15:00  (overlaps both A and C)
    # C departure at 15:05 → 14:20–15:15 (overlaps B)
    # Wait I need A and C to overlap WITHOUT B overlapping C.
    # A: 13:15–14:10, B: 14:05–14:50, C: 14:45–15:40
    # A and B overlap (14:05–14:10), B and C overlap (14:45–14:50), but A and C don't overlap.
    # That's not what I want.
    # I need A: 13:15–14:20, B: 14:10–14:15, C: 14:15–15:10
    # A and B overlap (14:10–14:20), A and C overlap (14:15–14:20), B and C don't overlap (back-to-back).
    # To get A ending at 14:20, I need departure at 14:10 with delay: 13:25–14:20
    # Actually departure at 14:00 with 10min delay: 13:15+00:10 = 13:25 start, 14:00+00:10 = 14:10 end+00:10 = 14:20
    flights = [
        # A: departs 14:00 with 10min delay → 13:25–14:20
        make_flight(number="F001", gate="H04", scheduled=time(14, 0), 
                    delay_minutes=10, status=Status.DELAYED),
        # B: departs 14:05 → 13:20–14:15
        make_flight(number="F002", gate="H04", scheduled=time(14, 5)),
        # C: departs 14:10 → 13:25–14:20
        make_flight(number="F003", gate="H04", scheduled=time(14, 10)),
    ]
    conflicts = find_conflicts(flights)
    # Should find 3 conflicts: A↔B, A↔C, B↔C
    # Wait, let me recalculate:
    # A: 14:00 + 10min delay, dep: 45min before to 10min after = 13:15 to 14:20
    # B: 14:05, dep: 13:20 to 14:15
    # C: 14:10, dep: 13:25 to 14:20
    # A (13:15–14:20) vs B (13:20–14:15): overlap 13:20–14:15 ✓
    # A (13:15–14:20) vs C (13:25–14:20): overlap 13:25–14:20 ✓
    # B (13:20–14:15) vs C (13:25–14:20): overlap 13:25–14:15 ✓
    # So all three pairs overlap. The key is that when sorted by start time:
    # - B starts at 13:20 (first)
    # - A starts at 13:15 (wait that's earlier, so A is first)
    # Let me recalculate delays. With 10min delay on A:
    # scheduled time gets the delay, so 14:00 + 10min = 14:10 effective time
    # Then window is 45min before effective to 10min after effective = 13:25 to 14:20
    # So sorted order by start: A (13:15 no wait...), hmm let me check the code.
    # Let me just use the real data from the exercise:
    flights = [
        # KL0661: departs 18:20 → 17:35–18:30, but actual data shows 18:20–19:15
        # That means actual is 18:20 (scheduled) → occupies 18:20-45min=17:35 to 18:20+55min=19:15
        # Wait the output shows 18:20–19:15, so it's 55 minutes, not 10 minutes after.
        # Let me check: departure is 45 before, 10 after. So 18:20 → 17:35 to 18:30.
        # But the bug description shows 18:20–19:15, which is 55 minutes. That's wrong.
        # Let me re-read: "F07 (non-schengen, wide-body) 18:20–19:15 KL0661 Houston (IAH)"
        # Maybe they have delays? Or is the formula different?
        # Let me just create a simple case: 3 flights where 1 and 3 overlap but 2 doesn't overlap 3.
        make_flight(number="F001", gate="H04", scheduled=time(13, 0)),   # 12:15–13:10
        make_flight(number="F002", gate="H04", scheduled=time(13, 45)),  # 13:00–13:55
        make_flight(number="F003", gate="H04", scheduled=time(13, 55)),  # 13:10–14:05
    ]
    conflicts = find_conflicts(flights)
    # F001: 13:00 → 12:15–13:10
    # F002: 13:45 → 13:00–13:55
    # F003: 13:55 → 13:10–14:05
    # F001 vs F002: 12:15–13:10 vs 13:00–13:55 = overlap 13:00–13:10 ✓
    # F001 vs F003: 12:15–13:10 vs 13:10–14:05 = no overlap (back-to-back)
    # F002 vs F003: 13:00–13:55 vs 13:10–14:05 = overlap 13:10–13:55 ✓
    # That's only 2 conflicts, not what I want. Let me adjust:
    flights = [
        make_flight(number="F001", gate="H04", scheduled=time(13, 15)),  # 12:30–13:25
        make_flight(number="F002", gate="H04", scheduled=time(13, 30)),  # 12:45–13:40
        make_flight(number="F003", gate="H04", scheduled=time(13, 20)),  # 12:35–13:30
    ]
    conflicts = find_conflicts(flights)
    # F001: 13:15 → 12:30–13:25
    # F002: 13:30 → 12:45–13:40
    # F003: 13:20 → 12:35–13:30
    # Sorted by start: F001 (12:30), F003 (12:35), F002 (12:45)
    # F001 vs F003: 12:30–13:25 vs 12:35–13:30 = overlap 12:35–13:25 ✓
    # F001 vs F002: 12:30–13:25 vs 12:45–13:40 = overlap 12:45–13:25 ✓
    # F003 vs F002: 12:35–13:30 vs 12:45–13:40 = overlap 12:45–13:30 ✓
    # All three overlap, so the old algorithm would find F001↔F003 and F003↔F002, missing F001↔F002.
    assert len(conflicts) == 3
    assert conflicts[0].first.flight.number == "F001"
    assert conflicts[0].second.flight.number == "F003"
    assert conflicts[1].first.flight.number == "F001" 
    assert conflicts[1].second.flight.number == "F002"
    assert conflicts[2].first.flight.number == "F003"
    assert conflicts[2].second.flight.number == "F002"


def test_render_conflicts_reports_the_overlap():
    flights = [
        make_flight(number="HV6011", gate="H04", scheduled=time(14, 20)),
        make_flight(number="HV6923", gate="H04", scheduled=time(15, 0)),
    ]
    output = render_conflicts(find_conflicts(flights))
    assert "1 gate conflict detected" in output
    assert "H04: HV6011" in output
    assert "during 14:15–14:30" in output


def test_render_conflicts_when_all_clear():
    assert render_conflicts([]) == "No gate conflicts detected."


def test_render_gates_lists_free_and_occupied():
    gates = [
        Gate(code="D04", pier="D", schengen=False, wide_body=False),
        Gate(code="D07", pier="D", schengen=False, wide_body=False),
    ]
    output = render_gates([make_flight()], gates)
    assert "D04 (non-schengen)" in output
    assert "KL1001" in output
    assert "free all day" in output


def test_render_gates_filters_by_pier():
    gates = [
        Gate(code="D04", pier="D", schengen=False, wide_body=False),
        Gate(code="E18", pier="E", schengen=False, wide_body=True),
    ]
    output = render_gates([], gates, pier="e")
    assert "E18" in output
    assert "D04" not in output
