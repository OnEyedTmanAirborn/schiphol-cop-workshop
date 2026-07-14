from __future__ import annotations

import argparse

from schiphol_ops import board, gates, stats
from schiphol_ops.data import load_flights, load_gates
from schiphol_ops.filters import apply_filters, find_flight
from schiphol_ops.models import Direction, Status

_STATUS_CHOICES = [status.value for status in Status]
_TERMINAL_CHOICES = ["B", "C", "D", "E", "F", "G", "H"]
_SORT_CHOICES = ["time", "destination", "delay"]


def _add_board_arguments(parser: argparse.ArgumentParser, city_flag: str) -> None:
    parser.add_argument(
        "--terminal",
        choices=_TERMINAL_CHOICES,
        type=str.upper,
        help="only flights from this pier",
    )
    parser.add_argument(
        "--status",
        choices=_STATUS_CHOICES,
        type=str.lower,
        help="only flights with this status",
    )
    parser.add_argument(
        "--airline",
        metavar="CODE",
        help="two-letter IATA airline code, e.g. KL",
    )
    parser.add_argument(
        f"--{city_flag}",
        dest="city",
        metavar="CITY",
        help=f"only flights matching this {city_flag}",
    )
    parser.add_argument(
        "--sort",
        choices=_SORT_CHOICES,
        default="time",
        help="order board by time, destination, or delay",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="schiphol-ops",
        description="Schiphol airside operations from your terminal.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    departures = subparsers.add_parser("departures", help="show the departures board")
    _add_board_arguments(departures, "destination")

    arrivals = subparsers.add_parser("arrivals", help="show the arrivals board")
    _add_board_arguments(arrivals, "origin")

    gates_parser = subparsers.add_parser("gates", help="show gate occupancy")
    gates_parser.add_argument(
        "--pier",
        choices=_TERMINAL_CHOICES,
        type=str.upper,
        help="only gates on this pier",
    )
    gates_parser.add_argument(
        "--conflicts",
        action="store_true",
        help="show double-booked gates instead of the occupancy list",
    )

    stats_parser = subparsers.add_parser("stats", help="show operations summary")
    stats_parser.add_argument(
        "--by",
        choices=["airline", "terminal"],
        help="break the summary down per airline or per terminal",
    )

    search = subparsers.add_parser("search", help="show one flight in detail")
    search.add_argument("flight", metavar="FLIGHT", help="flight number, e.g. KL1001")

    return parser


def _board_command(args: argparse.Namespace, direction: Direction) -> int:
    flights = apply_filters(
        load_flights(),
        direction=direction,
        terminal=args.terminal,
        status=Status(args.status) if args.status else None,
        airline=args.airline,
        city=args.city,
        sort_by=args.sort,
    )
    print(board.render_board(flights, direction))
    return 0


def _gates_command(args: argparse.Namespace) -> int:
    flights = load_flights()
    if args.conflicts:
        print(gates.render_conflicts(gates.find_conflicts(flights)))
        return 0
    print(gates.render_gates(flights, load_gates(), pier=args.pier))
    return 0


def _stats_command(args: argparse.Namespace) -> int:
    print(stats.render_stats(load_flights(), by=args.by))
    return 0


def _search_command(args: argparse.Namespace) -> int:
    flight = find_flight(load_flights(), args.flight)
    if flight is None:
        print(f"No flight found matching {args.flight!r}.")
        return 1
    print(board.render_detail(flight))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "departures":
        return _board_command(args, Direction.DEPARTURE)
    if args.command == "arrivals":
        return _board_command(args, Direction.ARRIVAL)
    if args.command == "gates":
        return _gates_command(args)
    if args.command == "stats":
        return _stats_command(args)
    return _search_command(args)


if __name__ == "__main__":
    raise SystemExit(main())
