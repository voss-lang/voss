"""Tiny seed CLI for the analyze fixture."""

import sys


def greet(name: str) -> str:
    return f"Hello, {name}!"


def main() -> None:
    name = sys.argv[1] if len(sys.argv) > 1 else "world"
    print(greet(name))


if __name__ == "__main__":
    main()
