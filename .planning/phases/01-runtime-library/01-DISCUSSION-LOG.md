# Phase 1: Runtime Library - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-07
**Phase:** 1-runtime-library
**Areas discussed:** Provider abstraction shape, Token counting + budget enforcement, Agent output typing, LLM test strategy

---

## Provider Abstraction Shape

### How to implement multi-provider abstraction?
| Option | Description | Selected |
|--------|-------------|----------|
| LiteLLM wrapper (Recommended) | Use LiteLLM as backbone — covers Anthropic/OpenAI/Ollama/100+ providers, unified OpenAI-style interface, streaming, costs, retries | ✓ |
| Roll our own thin layer | Native SDK calls behind ModelProvider protocol. Full control, more code | |
| Hybrid: own protocol, LiteLLM default impl | Define ModelProvider interface; ship LiteLLM-backed default; users can swap | |

### Streaming support in v1?
| Option | Description | Selected |
|--------|-------------|----------|
| No streaming v1 (Recommended) | Sync/await full responses only. Simpler ContextScope/BudgetScope semantics | ✓ |
| Yes, streaming primitive | Token-by-token via async iterator. More complex budget enforcement | |

### Provider config mechanism?
| Option | Description | Selected |
|--------|-------------|----------|
| Env vars + voss_runtime.config (Recommended) | Standard env keys; voss_runtime.configure() for overrides | ✓ |
| Per-call kwargs only | Pass model=, api_key= explicitly each call | |
| Config file (.voss/config.toml) | Project-level config file read on import | |

### Cost tracking in v1?
| Option | Description | Selected |
|--------|-------------|----------|
| Yes, track per-call USD (Recommended) | LiteLLM gives this for free; required for `cost: $0.02` budgets | ✓ |
| Defer | BudgetScope cost limit becomes no-op v1 | |

### Which providers gate v1 runtime tests?
| Option | Description | Selected |
|--------|-------------|----------|
| Anthropic + Ollama (Recommended) | Anthropic = primary, Ollama = local/no-key for CI | |
| Anthropic only | Other providers untested in v1 | |
| All three (Anthropic, OpenAI, Ollama) | Full test matrix | ✓ |

**Notes:** User picked all three providers — wider coverage commitment than the recommended option.

---

## Token Counting + Budget Enforcement

### Token counting source?
| Option | Description | Selected |
|--------|-------------|----------|
| LiteLLM token_counter (Recommended) | Single API, dispatches per-provider | ✓ |
| tiktoken everywhere (approximate) | Fast, no API call, slightly off for non-OpenAI | |
| Per-provider exact + approximate fallback | Most accurate, more code | |

### Token estimation timing for ctx blocks?
| Option | Description | Selected |
|--------|-------------|----------|
| Per ctx.add() call (Recommended) | Count when content added; trigger compression immediately if over budget | ✓ |
| On ctx.ask() only | Single count at model-call time | |
| Static-only at compile time | Compiler estimates; runtime trusts it | |

### BudgetScope latency enforcement?
| Option | Description | Selected |
|--------|-------------|----------|
| asyncio.wait_for wrapper (Recommended) | Wrap primary block; on TimeoutError cancel + run fallback | ✓ |
| Soft check between calls | Check elapsed at each ctx.ask() boundary | |
| Both layered | Soft checks + hard wait_for | |

### On BudgetExceededError without fallback?
| Option | Description | Selected |
|--------|-------------|----------|
| Raise to caller (Recommended) | Bubbles up; user catches with try/catch | ✓ |
| Log + return partial | Best-effort partial result + warning | |
| Configurable per-scope | BudgetScope(on_exceed=raise|warn|return_partial) | |

---

## Agent Output Typing

### How to parse model output to typed agent return?
| Option | Description | Selected |
|--------|-------------|----------|
| Pydantic + structured outputs (Recommended) | LiteLLM response_format=PydanticModel; provider-native structured outputs under the hood | ✓ |
| JSON schema prompt + parse | Inject schema into prompt, parse JSON, validate | |
| Free text + post-validate | Take string output, run typed extraction with second LLM call | |

### How are Voss types like Report mapped to Pydantic?
| Option | Description | Selected |
|--------|-------------|----------|
| Compile-time class gen (Recommended) | Voss class codegens to Pydantic BaseModel | ✓ |
| Runtime dataclass + adapter | Codegen dataclasses; runtime converts to Pydantic | |
| Phase 1 stub: string-only | Phase 1 supports only `-> string`; typed returns in Phase 4 | |

### Retry behavior on parse failure?
| Option | Description | Selected |
|--------|-------------|----------|
| Up to retries= count, then raise (Recommended) | Agent.retries governs both API and parse failures | ✓ |
| Separate retry budgets | API retries vs parse-error retries tracked independently | |
| Parse fail = hard fail | No retry on parse; raise on first error | |

### @tool schema generation strategy?
| Option | Description | Selected |
|--------|-------------|----------|
| inspect + typing + docstring (Recommended) | inspect.signature, typing.get_type_hints, first-line docstring | ✓ |
| Require explicit Pydantic models | Tool args must be Pydantic BaseModel | |
| Both (auto-gen, override w/ Pydantic) | Auto-gen by default; allow @tool(schema=MyModel) override | |

---

## LLM Test Strategy

### Primary test strategy for LLM-dependent classes?
| Option | Description | Selected |
|--------|-------------|----------|
| Stub provider + opt-in real (Recommended) | Default = StubProvider; `pytest -m live` runs against real providers | ✓ |
| VCR-style recorded fixtures | Record real API responses to YAML; replay in CI | |
| Real APIs always | Every test hits live providers | |

### Ollama in CI?
| Option | Description | Selected |
|--------|-------------|----------|
| GitHub Actions service container (Recommended) | ollama/ollama container with small model in live-mode CI job | ✓ |
| Local-only (skip in CI) | Live Ollama tests only on dev machines | |
| Mock Ollama HTTP | Mock the Ollama HTTP API at network layer | |

### Coverage target for v1 runtime?
| Option | Description | Selected |
|--------|-------------|----------|
| 90%+ on pure logic, smoke tests on LLM paths (Recommended) | Strict on data structures; smoke on LLM paths | ✓ |
| 80%+ overall, no per-class targets | Single overall threshold | |
| Tests pass = good enough | No coverage gate | |

### Compression strategy verification?
| Option | Description | Selected |
|--------|-------------|----------|
| Stub-summarizer + size assertions (Recommended) | Deterministic summarize stub; assert ContextScope shrinks correctly | ✓ |
| Real LLM round-trip | Live test verifying actual summarization quality | |
| Skip compression tests v1 | Verified ad-hoc | |

---

## Claude's Discretion
- Internal package layout under `voss_runtime/` (file split per class vs. logical grouping)
- Specific stub provider response format (dict, callable, fixture file)
- Exception class hierarchy beyond `BudgetExceededError`
- Channel API surface for inter-agent messaging
- Working memory eviction policy when crossing ctx boundaries

## Deferred Ideas
- Streaming model output → post-v1
- Distributed/multi-process agents → explicitly out of scope
- Public PyPI publication + onboarding polish → v2
- Custom (non-LiteLLM) provider plug-ins beyond default → v2
- Compression strategies beyond summarize (middle-out, semantic drop) → post-v1
- Richer channel API (pub/sub, persistent) → post-v1
