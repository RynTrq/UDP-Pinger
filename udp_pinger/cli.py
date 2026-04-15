"""Command-line interface for the UDP pinger package."""

from __future__ import annotations

import argparse
import sys

from .client import UDPClient, summarize_results
from .server import UDPServer


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "client":
            return _run_client(args)
        if args.command == "heartbeat":
            return _run_heartbeat(args)
        if args.command == "server":
            return _run_server(args)
    except ValueError as exc:
        parser.error(str(exc))
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130

    parser.print_help()
    return 2


def _run_client(args: argparse.Namespace) -> int:
    client = UDPClient(
        host=args.host,
        port=args.port,
        timeout=args.timeout,
        payload=args.payload,
    )
    print(
        f"Pinging {args.host}:{args.port} with {args.count} UDP datagram(s), "
        f"timeout {args.timeout:.3f}s"
    )
    results = client.ping(count=args.count, interval=args.interval)
    for result in results:
        if result.success:
            print(f"seq={result.sequence} rtt={result.rtt_ms:.3f} ms")
        else:
            print(f"seq={result.sequence} lost ({result.error})")

    summary = summarize_results(results)
    print(
        "\nSummary: "
        f"sent={summary.sent} received={summary.received} lost={summary.lost} "
        f"loss={summary.loss_percent:.1f}%"
    )
    if summary.received:
        print(
            "RTT: "
            f"min={summary.min_rtt_ms:.3f} ms "
            f"avg={summary.avg_rtt_ms:.3f} ms "
            f"max={summary.max_rtt_ms:.3f} ms"
        )
    return 0 if summary.received else 1


def _run_heartbeat(args: argparse.Namespace) -> int:
    client = UDPClient(
        host=args.host,
        port=args.port,
        timeout=args.timeout,
        payload=args.payload,
    )
    print(
        f"Sending heartbeats to {args.host}:{args.port}; "
        f"declaring unavailable after {args.max_consecutive_losses} consecutive loss(es)"
    )
    results = client.heartbeat(
        max_consecutive_losses=args.max_consecutive_losses,
        interval=args.interval,
        max_pings=args.max_pings,
    )
    for result in results:
        if result.success:
            print(f"seq={result.sequence} alive rtt={result.rtt_ms:.3f} ms")
        else:
            print(f"seq={result.sequence} missed ({result.error})")

    summary = summarize_results(results)
    print(
        "\nHeartbeat summary: "
        f"sent={summary.sent} received={summary.received} lost={summary.lost} "
        f"loss={summary.loss_percent:.1f}%"
    )
    if results and results[-1].success:
        return 0
    return 2


def _run_server(args: argparse.Namespace) -> int:
    server = UDPServer(host=args.host, port=args.port, loss_rate=args.loss_rate)
    print(
        f"Serving UDP pings on {args.host}:{args.port} "
        f"with simulated loss rate {args.loss_rate:.0%}"
    )
    stats = server.serve_forever(max_packets=args.max_packets)
    print(
        "Stopped. "
        f"received={stats.received} responded={stats.responded} "
        f"dropped={stats.dropped} malformed={stats.malformed}"
    )
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="udp-pinger",
        description="Measure UDP round-trip latency and simulate UDP packet loss.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    client = subparsers.add_parser("client", help="send UDP pings")
    client.add_argument("--host", default="127.0.0.1", help="server host or IP")
    client.add_argument("--port", type=int, default=12000, help="server UDP port")
    client.add_argument("--count", type=int, default=10, help="number of pings to send")
    client.add_argument("--timeout", type=float, default=1.0, help="seconds to wait per ping")
    client.add_argument("--interval", type=float, default=1.0, help="seconds between pings")
    client.add_argument("--payload", default="", help="optional payload echoed by the server")

    heartbeat = subparsers.add_parser("heartbeat", help="send heartbeats until repeated loss")
    heartbeat.add_argument("--host", default="127.0.0.1", help="server host or IP")
    heartbeat.add_argument("--port", type=int, default=12000, help="server UDP port")
    heartbeat.add_argument("--timeout", type=float, default=1.0, help="seconds to wait per heartbeat")
    heartbeat.add_argument("--interval", type=float, default=1.0, help="seconds between heartbeats")
    heartbeat.add_argument("--payload", default="heartbeat", help="optional payload echoed by the server")
    heartbeat.add_argument(
        "--max-consecutive-losses",
        type=int,
        default=3,
        help="declare the server unavailable after this many consecutive losses",
    )
    heartbeat.add_argument(
        "--max-pings",
        type=int,
        default=None,
        help="optional upper bound for demo and test runs",
    )

    server = subparsers.add_parser("server", help="serve UDP pings")
    server.add_argument("--host", default="127.0.0.1", help="host/IP to bind")
    server.add_argument("--port", type=int, default=12000, help="UDP port to bind")
    server.add_argument(
        "--loss-rate",
        type=float,
        default=0.0,
        help="simulated packet loss rate from 0.0 to 1.0",
    )
    server.add_argument(
        "--max-packets",
        type=int,
        default=None,
        help="stop after processing this many packets; useful for tests and demos",
    )

    return parser


if __name__ == "__main__":
    raise SystemExit(main())
