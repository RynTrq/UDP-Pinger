from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from udp_pinger.cli import main


if __name__ == "__main__":
    percent_loss = input("Packet loss percentage to simulate [0]: ").strip()
    loss_rate = float(percent_loss or 0) / 100
    raise SystemExit(main(["server", "--loss-rate", str(loss_rate)]))
