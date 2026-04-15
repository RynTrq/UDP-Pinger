"""Wire protocol helpers for UDP pinger clients and servers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

ENCODING = "utf-8"
MAX_DATAGRAM_BYTES = 1400
PING_KIND = "ping"
PONG_KIND = "pong"


class ProtocolError(ValueError):
    """Raised when a UDP datagram does not match the pinger protocol."""


@dataclass(frozen=True)
class PingMessage:
    sequence: int
    sent_at_ns: int
    payload: str = ""


@dataclass(frozen=True)
class PongMessage:
    sequence: int
    sent_at_ns: int
    server_received_at_ns: int
    payload: str = ""


def encode_ping(message: PingMessage) -> bytes:
    _validate_sequence(message.sequence)
    _validate_timestamp(message.sent_at_ns, "sent_at_ns")
    return _encode(
        {
            "kind": PING_KIND,
            "sequence": message.sequence,
            "sent_at_ns": message.sent_at_ns,
            "payload": message.payload,
        }
    )


def encode_pong(message: PongMessage) -> bytes:
    _validate_sequence(message.sequence)
    _validate_timestamp(message.sent_at_ns, "sent_at_ns")
    _validate_timestamp(message.server_received_at_ns, "server_received_at_ns")
    return _encode(
        {
            "kind": PONG_KIND,
            "sequence": message.sequence,
            "sent_at_ns": message.sent_at_ns,
            "server_received_at_ns": message.server_received_at_ns,
            "payload": message.payload,
        }
    )


def decode_ping(datagram: bytes) -> PingMessage:
    obj = _decode(datagram)
    if obj.get("kind") != PING_KIND:
        raise ProtocolError("datagram is not a ping message")
    sequence = _required_int(obj, "sequence")
    sent_at_ns = _required_int(obj, "sent_at_ns")
    payload = _optional_str(obj, "payload")
    _validate_sequence(sequence)
    _validate_timestamp(sent_at_ns, "sent_at_ns")
    return PingMessage(sequence=sequence, sent_at_ns=sent_at_ns, payload=payload)


def decode_pong(datagram: bytes) -> PongMessage:
    obj = _decode(datagram)
    if obj.get("kind") != PONG_KIND:
        raise ProtocolError("datagram is not a pong message")
    sequence = _required_int(obj, "sequence")
    sent_at_ns = _required_int(obj, "sent_at_ns")
    server_received_at_ns = _required_int(obj, "server_received_at_ns")
    payload = _optional_str(obj, "payload")
    _validate_sequence(sequence)
    _validate_timestamp(sent_at_ns, "sent_at_ns")
    _validate_timestamp(server_received_at_ns, "server_received_at_ns")
    return PongMessage(
        sequence=sequence,
        sent_at_ns=sent_at_ns,
        server_received_at_ns=server_received_at_ns,
        payload=payload,
    )


def build_pong(ping: PingMessage, server_received_at_ns: int) -> PongMessage:
    return PongMessage(
        sequence=ping.sequence,
        sent_at_ns=ping.sent_at_ns,
        server_received_at_ns=server_received_at_ns,
        payload=ping.payload,
    )


def _encode(obj: dict[str, Any]) -> bytes:
    try:
        datagram = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode(ENCODING)
    except (TypeError, UnicodeEncodeError) as exc:
        raise ProtocolError(f"message is not serializable: {exc}") from exc

    if len(datagram) > MAX_DATAGRAM_BYTES:
        raise ProtocolError(
            f"message is {len(datagram)} bytes; maximum is {MAX_DATAGRAM_BYTES} bytes"
        )
    return datagram


def _decode(datagram: bytes) -> dict[str, Any]:
    if len(datagram) > MAX_DATAGRAM_BYTES:
        raise ProtocolError(
            f"datagram is {len(datagram)} bytes; maximum is {MAX_DATAGRAM_BYTES} bytes"
        )
    try:
        obj = json.loads(datagram.decode(ENCODING))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError(f"datagram is not valid JSON: {exc}") from exc
    if not isinstance(obj, dict):
        raise ProtocolError("datagram JSON must be an object")
    return obj


def _required_int(obj: dict[str, Any], key: str) -> int:
    value = obj.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ProtocolError(f"{key} must be an integer")
    return value


def _optional_str(obj: dict[str, Any], key: str) -> str:
    value = obj.get(key, "")
    if not isinstance(value, str):
        raise ProtocolError(f"{key} must be a string")
    return value


def _validate_sequence(sequence: int) -> None:
    if sequence < 1:
        raise ProtocolError("sequence must be greater than or equal to 1")


def _validate_timestamp(value: int, name: str) -> None:
    if value < 0:
        raise ProtocolError(f"{name} must be non-negative")

