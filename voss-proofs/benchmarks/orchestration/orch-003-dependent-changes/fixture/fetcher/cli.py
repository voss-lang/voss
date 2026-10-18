import argparse
from collections.abc import Callable

from .client import Client
from .settings import load


def main(argv: list[str], send: Callable[[str, float], str]) -> Client:
    parser = argparse.ArgumentParser(prog="fetch")
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args(argv)
    return Client(load({"timeout": args.timeout}), send)
