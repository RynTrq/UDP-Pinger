"""UDP pinger server implementation."""

from __future__ import annotations

import random
import socket
import threading
import time
from dataclasses import dataclass
from typing import Callable

from .protocol import MAX_DATAGRAM_BYTES, ProtocolError, build_pong, decode_ping, encode_pong

RandomSource = Callable[[], float]


@dataclass(frozen=True)
class ServerStats:
    received: int = 0
    responded: int = 0
    dropped: int = 0
    malformed: int = 0


class UDPServer:
    """Listens for UDP pings and replies with matching pong datagrams."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 12000,
        loss_rate: float = 0.0,
        buffer_size: int = MAX_DATAGRAM_BYTES,
        random_source: RandomSource | None = None,
    ) -> None:
        self.host = _validate_host(host)
        self.port = _validate_port(port)
        self.loss_rate = _validate_loss_rate(loss_rate)
        self.buffer_size = _validate_buffer_size(buffer_size)
        self._random_source = random_source or random.random
        self.stats = ServerStats()

    def serve_forever(
        self,
        stop_event: threading.Event | None = None,
        max_packets: int | None = None,
        ready_event: threading.Event | None = None,
    ) -> ServerStats:
        processed = 0
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((self.host, self.port))
            sock.settimeout(0.2)
            self.port = sock.getsockname()[1]
            if ready_event is not None:
                ready_event.set()

            while not _should_stop(stop_event, processed, max_packets):
                try:
                    datagram, address = sock.recvfrom(self.buffer_size)
                except socket.timeout:
                    continue

                processed += 1
                self._handle_datagram(sock, datagram, address)

        return self.stats

    def _handle_datagram(
        self,
        sock: socket.socket,
        datagram: bytes,
        address: tuple[str, int],
    ) -> None:
        self.stats = ServerStats(
            received=self.stats.received + 1,
            responded=self.stats.responded,
            dropped=self.stats.dropped,
            malformed=self.stats.malformed,
        )

        try:
            ping = decode_ping(datagram)
        except ProtocolError:
            self.stats = ServerStats(
                received=self.stats.received,
                responded=self.stats.responded,
                dropped=self.stats.dropped,
                malformed=self.stats.malformed + 1,
            )
            return

        if self._random_source() < self.loss_rate:
            self.stats = ServerStats(
                received=self.stats.received,
                responded=self.stats.responded,
                dropped=self.stats.dropped + 1,
                malformed=self.stats.malformed,
            )
            return

        response = build_pong(ping, server_received_at_ns=time.monotonic_ns())
        sock.sendto(encode_pong(response), address)
        self.stats = ServerStats(
            received=self.stats.received,
            responded=self.stats.responded + 1,
            dropped=self.stats.dropped,
            malformed=self.stats.malformed,
        )


def serve(
    host: str = "127.0.0.1",
    port: int = 12000,
    loss_rate: float = 0.0,
    stop_event: threading.Event | None = None,
    max_packets: int | None = None,
    ready_event: threading.Event | None = None,
) -> ServerStats:
    server = UDPServer(host=host, port=port, loss_rate=loss_rate)
    return server.serve_forever(
        stop_event=stop_event,
        max_packets=max_packets,
        ready_event=ready_event,
    )


def _should_stop(
    stop_event: threading.Event | None,
    processed: int,
    max_packets: int | None,
) -> bool:
    if stop_event is not None and stop_event.is_set():
        return True
    if max_packets is not None and processed >= max_packets:
        return True
    return False


def _validate_host(host: str) -> str:
    if not host or not host.strip():
        raise ValueError("host must not be empty")
    return host.strip()


def _validate_port(port: int) -> int:
    if not 0 <= int(port) <= 65535:
        raise ValueError("port must be between 0 and 65535")
    return int(port)


def _validate_loss_rate(loss_rate: float) -> float:
    loss_rate = float(loss_rate)
    if not 0 <= loss_rate <= 1:
        raise ValueError("loss_rate must be between 0 and 1")
    return loss_rate


def _validate_buffer_size(buffer_size: int) -> int:
    if int(buffer_size) < MAX_DATAGRAM_BYTES:
        raise ValueError(f"buffer_size must be at least {MAX_DATAGRAM_BYTES}")
    return int(buffer_size)
