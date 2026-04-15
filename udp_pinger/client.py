"""UDP pinger client implementation."""

from __future__ import annotations

import socket
import time
from dataclasses import dataclass
from statistics import mean
from typing import Iterable

from .protocol import (
    MAX_DATAGRAM_BYTES,
    PingMessage,
    ProtocolError,
    decode_pong,
    encode_ping,
)


@dataclass(frozen=True)
class PingResult:
    sequence: int
    success: bool
    rtt_ms: float | None = None
    server_received_at_ns: int | None = None
    error: str | None = None


@dataclass(frozen=True)
class PingSummary:
    sent: int
    received: int
    lost: int
    loss_percent: float
    min_rtt_ms: float | None
    avg_rtt_ms: float | None
    max_rtt_ms: float | None


class UDPClient:
    """Sends UDP pings and records round-trip timing."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 12000,
        timeout: float = 1.0,
        payload: str = "",
        buffer_size: int = MAX_DATAGRAM_BYTES,
    ) -> None:
        self.host = _validate_host(host)
        self.port = _validate_port(port)
        self.timeout = _validate_positive_float(timeout, "timeout")
        self.payload = payload
        self.buffer_size = _validate_buffer_size(buffer_size)

    def ping(self, count: int = 10, interval: float = 1.0) -> list[PingResult]:
        count = _validate_count(count)
        interval = _validate_non_negative_float(interval, "interval")
        results: list[PingResult] = []

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(self.timeout)
            for sequence in range(1, count + 1):
                result = self._ping_once(sock, sequence)
                results.append(result)
                if sequence < count and interval > 0:
                    time.sleep(interval)

        return results

    def heartbeat(
        self,
        max_consecutive_losses: int,
        interval: float = 1.0,
        max_pings: int | None = None,
    ) -> list[PingResult]:
        max_consecutive_losses = _validate_count(max_consecutive_losses)
        interval = _validate_non_negative_float(interval, "interval")
        if max_pings is not None:
            max_pings = _validate_count(max_pings)

        results: list[PingResult] = []
        consecutive_losses = 0
        sequence = 1

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(self.timeout)
            while consecutive_losses < max_consecutive_losses:
                if max_pings is not None and sequence > max_pings:
                    break

                result = self._ping_once(sock, sequence)
                results.append(result)
                consecutive_losses = 0 if result.success else consecutive_losses + 1
                sequence += 1

                if consecutive_losses < max_consecutive_losses and interval > 0:
                    time.sleep(interval)

        return results

    def _ping_once(self, sock: socket.socket, sequence: int) -> PingResult:
        sent_at_ns = time.monotonic_ns()
        request = PingMessage(
            sequence=sequence,
            sent_at_ns=sent_at_ns,
            payload=self.payload,
        )

        try:
            sock.sendto(encode_ping(request), (self.host, self.port))
            while True:
                datagram, _ = sock.recvfrom(self.buffer_size)
                received_at_ns = time.monotonic_ns()
                response = decode_pong(datagram)
                if response.sequence != sequence or response.sent_at_ns != sent_at_ns:
                    continue
                return PingResult(
                    sequence=sequence,
                    success=True,
                    rtt_ms=(received_at_ns - sent_at_ns) / 1_000_000,
                    server_received_at_ns=response.server_received_at_ns,
                )
        except socket.timeout:
            return PingResult(sequence=sequence, success=False, error="request timed out")
        except (OSError, ProtocolError) as exc:
            return PingResult(sequence=sequence, success=False, error=str(exc))


def summarize_results(results: Iterable[PingResult]) -> PingSummary:
    result_list = list(results)
    sent = len(result_list)
    rtts = [result.rtt_ms for result in result_list if result.rtt_ms is not None]
    received = len(rtts)
    lost = sent - received
    return PingSummary(
        sent=sent,
        received=received,
        lost=lost,
        loss_percent=(lost / sent * 100) if sent else 0.0,
        min_rtt_ms=min(rtts) if rtts else None,
        avg_rtt_ms=mean(rtts) if rtts else None,
        max_rtt_ms=max(rtts) if rtts else None,
    )


def _validate_host(host: str) -> str:
    if not host or not host.strip():
        raise ValueError("host must not be empty")
    return host.strip()


def _validate_port(port: int) -> int:
    if not 1 <= int(port) <= 65535:
        raise ValueError("port must be between 1 and 65535")
    return int(port)


def _validate_count(count: int) -> int:
    if int(count) < 1:
        raise ValueError("count must be greater than or equal to 1")
    return int(count)


def _validate_buffer_size(buffer_size: int) -> int:
    if int(buffer_size) < MAX_DATAGRAM_BYTES:
        raise ValueError(f"buffer_size must be at least {MAX_DATAGRAM_BYTES}")
    return int(buffer_size)


def _validate_positive_float(value: float, name: str) -> float:
    value = float(value)
    if value <= 0:
        raise ValueError(f"{name} must be greater than 0")
    return value


def _validate_non_negative_float(value: float, name: str) -> float:
    value = float(value)
    if value < 0:
        raise ValueError(f"{name} must be greater than or equal to 0")
    return value
