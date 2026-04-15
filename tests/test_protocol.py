import json
import unittest

from udp_pinger.protocol import (
    MAX_DATAGRAM_BYTES,
    PingMessage,
    PongMessage,
    ProtocolError,
    decode_ping,
    decode_pong,
    encode_ping,
    encode_pong,
)


class ProtocolTests(unittest.TestCase):
    def test_ping_round_trip(self):
        message = PingMessage(sequence=1, sent_at_ns=123, payload="hello")

        decoded = decode_ping(encode_ping(message))

        self.assertEqual(decoded, message)

    def test_pong_round_trip(self):
        message = PongMessage(
            sequence=2,
            sent_at_ns=123,
            server_received_at_ns=456,
            payload="hello",
        )

        decoded = decode_pong(encode_pong(message))

        self.assertEqual(decoded, message)

    def test_rejects_wrong_kind(self):
        datagram = json.dumps({"kind": "pong", "sequence": 1, "sent_at_ns": 1}).encode()

        with self.assertRaises(ProtocolError):
            decode_ping(datagram)

    def test_rejects_oversized_payload_before_send(self):
        message = PingMessage(sequence=1, sent_at_ns=1, payload="x" * MAX_DATAGRAM_BYTES)

        with self.assertRaises(ProtocolError):
            encode_ping(message)


if __name__ == "__main__":
    unittest.main()

