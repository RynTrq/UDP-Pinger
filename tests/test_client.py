import unittest

from udp_pinger.client import PingResult, UDPClient, summarize_results


class ClientTests(unittest.TestCase):
    def test_summary_handles_mixed_results(self):
        results = [
            PingResult(sequence=1, success=True, rtt_ms=10.0),
            PingResult(sequence=2, success=False, error="request timed out"),
            PingResult(sequence=3, success=True, rtt_ms=20.0),
        ]

        summary = summarize_results(results)

        self.assertEqual(summary.sent, 3)
        self.assertEqual(summary.received, 2)
        self.assertEqual(summary.lost, 1)
        self.assertAlmostEqual(summary.loss_percent, 33.33333333333333)
        self.assertEqual(summary.min_rtt_ms, 10.0)
        self.assertEqual(summary.avg_rtt_ms, 15.0)
        self.assertEqual(summary.max_rtt_ms, 20.0)

    def test_summary_handles_empty_results(self):
        summary = summarize_results([])

        self.assertEqual(summary.sent, 0)
        self.assertEqual(summary.received, 0)
        self.assertEqual(summary.loss_percent, 0.0)
        self.assertIsNone(summary.avg_rtt_ms)

    def test_rejects_invalid_configuration(self):
        with self.assertRaises(ValueError):
            UDPClient(port=0)
        with self.assertRaises(ValueError):
            UDPClient(timeout=0)

    def test_heartbeat_rejects_invalid_loss_threshold(self):
        client = UDPClient(port=12000)

        with self.assertRaises(ValueError):
            client.heartbeat(max_consecutive_losses=0, interval=0, max_pings=1)


if __name__ == "__main__":
    unittest.main()
