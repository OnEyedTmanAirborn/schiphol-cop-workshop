from __future__ import annotations

from dataclasses import dataclass

from schiphol_ops.models import AIRLINE_NAMES, Flight


@dataclass(frozen=True)
class Summary:
    total: int
    on_time: int
    delayed: int
    cancelled: int
    avg_delay: int

    @property
    def on_time_pct(self) -> int:
        movements = self.total - self.cancelled
        if movements == 0:
            return 0
        return round(100 * self.on_time / movements)


def summarize(flights: list[Flight]) -> Summary:
    delayed = [f for f in flights if f.is_delayed]
    cancelled = [f for f in flights if f.is_cancelled]
    on_time = len(flights) - len(delayed) - len(cancelled)
    if delayed:
        avg_delay = round(sum(f.delay_minutes for f in delayed) / len(delayed))
    else:
        avg_delay = 0
    return Summary(
        total=len(flights),
        on_time=on_time,
        delayed=len(delayed),
        cancelled=len(cancelled),
        avg_delay=avg_delay,
    )


def group_key(flight: Flight, by: str) -> str:
    if by == "airline":
        return flight.airline
    if by == "terminal":
        return flight.terminal
    raise ValueError(f"unknown grouping: {by}")


def grouped_summaries(flights: list[Flight], by: str) -> dict[str, Summary]:
    groups: dict[str, list[Flight]] = {}
    for flight in flights:
        groups.setdefault(group_key(flight, by), []).append(flight)
    return {key: summarize(group) for key, group in sorted(groups.items())}


def _summary_line(summary: Summary) -> str:
    return (
        f"{summary.total} flights - {summary.on_time} on time, "
        f"{summary.delayed} delayed, {summary.cancelled} cancelled, "
        f"avg delay {summary.avg_delay}m, on-time {summary.on_time_pct}%"
    )


def render_stats(flights: list[Flight], by: str | None = None) -> str:
    lines = ["OPERATIONS SUMMARY - Schiphol (AMS)", ""]
    lines.append(f"Overall: {_summary_line(summarize(flights))}")
    if by is not None:
        lines.append("")
        lines.append(f"By {by}:")
        for key, summary in grouped_summaries(flights, by).items():
            label = AIRLINE_NAMES.get(key, key) if by == "airline" else f"Terminal {key}"
            lines.append(f"  {label:<20} {_summary_line(summary)}")
    return "\n".join(lines)
