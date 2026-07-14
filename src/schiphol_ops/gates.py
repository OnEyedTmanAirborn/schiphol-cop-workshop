from __future__ import annotations

from dataclasses import dataclass

from schiphol_ops.models import Direction, Flight, Gate, format_minutes, minutes_since_midnight

# How long a flight occupies its gate, in minutes around the scheduled time.
# Departures: boarding opens 45m before scheduled, pushback ~10m after.
# Arrivals: docking 5m before scheduled, deboarding + turnaround prep ~40m after.
_DEPARTURE_WINDOW = (-45, 10)
_ARRIVAL_WINDOW = (-5, 40)


@dataclass(frozen=True)
class Occupancy:
    flight: Flight
    start: int
    end: int

    @property
    def window(self) -> str:
        return f"{format_minutes(self.start)}–{format_minutes(self.end)}"


@dataclass(frozen=True)
class Conflict:
    gate: str
    first: Occupancy
    second: Occupancy

    @property
    def overlap(self) -> str:
        start = max(self.first.start, self.second.start)
        end = min(self.first.end, self.second.end)
        return f"{format_minutes(start)}–{format_minutes(end)}"


def occupancy_for(flight: Flight) -> Occupancy:
    before, after = (
        _DEPARTURE_WINDOW if flight.direction is Direction.DEPARTURE else _ARRIVAL_WINDOW
    )
    scheduled = minutes_since_midnight(flight.scheduled) + flight.delay_minutes
    return Occupancy(flight=flight, start=scheduled + before, end=scheduled + after)


def occupancies_by_gate(flights: list[Flight]) -> dict[str, list[Occupancy]]:
    by_gate: dict[str, list[Occupancy]] = {}
    for flight in flights:
        if flight.is_cancelled:
            continue
        by_gate.setdefault(flight.gate, []).append(occupancy_for(flight))
    for slots in by_gate.values():
        slots.sort(key=lambda o: o.start)
    return by_gate


def _overlaps(a: Occupancy, b: Occupancy) -> bool:
    return a.start < b.end and b.start < a.end


def find_conflicts(flights: list[Flight]) -> list[Conflict]:
    """Flag flights whose occupancy windows overlap at the same gate."""
    conflicts: list[Conflict] = []
    for gate, slots in sorted(occupancies_by_gate(flights).items()):
        for i in range(len(slots)):
            for j in range(i + 1, len(slots)):
                if _overlaps(slots[i], slots[j]):
                    conflicts.append(Conflict(gate=gate, first=slots[i], second=slots[j]))
    return conflicts


def render_gates(
    flights: list[Flight], gates: list[Gate], pier: str | None = None
) -> str:
    selected = [g for g in gates if pier is None or g.pier == pier.upper()]
    if not selected:
        return f"No gates found for pier {pier}."
    by_gate = occupancies_by_gate(flights)
    lines = ["GATE OCCUPANCY - Schiphol (AMS)", ""]
    for gate in selected:
        slots = by_gate.get(gate.code, [])
        tags = "schengen" if gate.schengen else "non-schengen"
        if gate.wide_body:
            tags += ", wide-body"
        lines.append(f"{gate.code} ({tags})")
        if not slots:
            lines.append("    free all day")
        for slot in slots:
            lines.append(f"    {slot.window}  {slot.flight.number}  {slot.flight.city}")
        lines.append("")
    return "\n".join(lines).rstrip()


def render_conflicts(conflicts: list[Conflict]) -> str:
    if not conflicts:
        return "No gate conflicts detected."
    noun = "conflict" if len(conflicts) == 1 else "conflicts"
    lines = [f"{len(conflicts)} gate {noun} detected", ""]
    for conflict in conflicts:
        lines.append(
            f"{conflict.gate}: {conflict.first.flight.number} ({conflict.first.window}) "
            f"overlaps {conflict.second.flight.number} ({conflict.second.window}) "
            f"during {conflict.overlap}"
        )
    return "\n".join(lines)
