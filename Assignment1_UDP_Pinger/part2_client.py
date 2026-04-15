from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from udp_pinger.cli import main


if __name__ == "__main__":
    max_losses = input(
        "Maximum consecutive losses before declaring the server unavailable [3]: "
    ).strip()
    args = ["heartbeat", "--timeout", "1"]
    if max_losses:
        args.extend(["--max-consecutive-losses", max_losses])
    raise SystemExit(main(args))
