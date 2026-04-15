import socket
import threading
import unittest

from udp_pinger.client import UDPClient
from udp_pinger.protocol import PingMessage, encode_ping
from udp_pinger.server import UDPServer


class ServerTests(unittest.TestCase):
    def test_client_server_local_round_trip(self):
        server = UDPServer(host="127.0.0.1", port=0)
        ready = threading.Event()
        thread = threading.Thread(
            target=server.serve_forever,
            kwargs={"ready_event": ready, "max_packets": 2},
            daemon=True,
        )
        thread.start()
        self.assertTrue(ready.wait(2), "server did not become ready")

        client = UDPClient(host="127.0.0.1", port=server.port, timeout=1.0)
        results = client.ping(count=2, interval=0)

        thread.join(2)
        self.assertFalse(thread.is_alive(), "server did not stop after max_packets")
        self.assertTrue(all(result.success for result in results))
        self.assertEqual(server.stats.received, 2)
        self.assertEqual(server.stats.responded, 2)

    def test_loss_rate_drops_packets(self):
        server = UDPServer(host="127.0.0.1", port=0, loss_rate=1.0)
        ready = threading.Event()
        thread = threading.Thread(
            target=server.serve_forever,
            kwargs={"ready_event": ready, "max_packets": 1},
            daemon=True,
        )
        thread.start()
        self.assertTrue(ready.wait(2), "server did not become ready")

        client = UDPClient(host="127.0.0.1", port=server.port, timeout=0.1)
        [result] = client.ping(count=1, interval=0)

        thread.join(2)
        self.assertFalse(result.success)
        self.assertEqual(server.stats.dropped, 1)
        self.assertEqual(server.stats.responded, 0)

    def test_heartbeat_stops_after_consecutive_losses(self):
        server = UDPServer(host="127.0.0.1", port=0, loss_rate=1.0)
        ready = threading.Event()
        thread = threading.Thread(
            target=server.serve_forever,
            kwargs={"ready_event": ready, "max_packets": 2},
            daemon=True,
        )
        thread.start()
        self.assertTrue(ready.wait(2), "server did not become ready")

        client = UDPClient(host="127.0.0.1", port=server.port, timeout=0.1)
        results = client.heartbeat(max_consecutive_losses=2, interval=0)

        thread.join(2)
        self.assertEqual(len(results), 2)
        self.assertTrue(all(not result.success for result in results))
        self.assertEqual(server.stats.dropped, 2)

    def test_malformed_datagram_is_counted_without_response(self):
        server = UDPServer(host="127.0.0.1", port=0)
        ready = threading.Event()
        thread = threading.Thread(
            target=server.serve_forever,
            kwargs={"ready_event": ready, "max_packets": 1},
            daemon=True,
        )
        thread.start()
        self.assertTrue(ready.wait(2), "server did not become ready")

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(0.1)
            sock.sendto(b"not-json", ("127.0.0.1", server.port))
            with self.assertRaises(socket.timeout):
                sock.recvfrom(1400)

        thread.join(2)
        self.assertEqual(server.stats.malformed, 1)

    def test_ignores_stale_responses_until_matching_sequence(self):
        server = UDPServer(host="127.0.0.1", port=0)
        ready = threading.Event()
        thread = threading.Thread(
            target=server.serve_forever,
            kwargs={"ready_event": ready, "max_packets": 1},
            daemon=True,
        )
        thread.start()
        self.assertTrue(ready.wait(2), "server did not become ready")

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(
                encode_ping(PingMessage(sequence=99, sent_at_ns=1)),
                ("127.0.0.1", server.port),
            )

        thread.join(2)
        self.assertEqual(server.stats.responded, 1)


if __name__ == "__main__":
    unittest.main()
