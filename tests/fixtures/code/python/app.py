"""Minimal Python fixture for M10 code-intel tests."""

def shared_entry(x: int) -> int:
    return helper_value(x) + 1


def helper_value(n: int) -> int:
    return n * 2


class HelperClass:
    def method(self) -> str:
        return "hello"


if __name__ == "__main__":
    print(shared_entry(41))
