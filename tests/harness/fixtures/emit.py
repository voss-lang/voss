from __future__ import annotations

import sys
import time


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: emit.py <N>", file=sys.stderr)
        return 2

    count = int(argv[1])
    for i in range(count):
        print(f"line {i}", flush=True)
        time.sleep(0.05)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
