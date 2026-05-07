class VossRuntimeError(Exception):
    """Base for all voss_runtime errors."""

class BudgetExceededError(VossRuntimeError):
    def __init__(self, *, reason: str, limit: float, observed: float, scope: str = ""):
        self.reason = reason          # "tokens" | "latency" | "cost"
        self.limit = limit
        self.observed = observed
        self.scope = scope
        super().__init__(f"Budget exceeded ({reason}): {observed} > {limit} in {scope or '<unnamed>'}")

class ProviderError(VossRuntimeError):
    """Raised when a ModelProvider call fails after retries."""

class ParseError(VossRuntimeError):
    """Raised when structured-output parsing fails after retries."""

class ConfidenceTooLowError(VossRuntimeError):
    """Raised by ProbableValue.unwrap() when confidence is below threshold."""
