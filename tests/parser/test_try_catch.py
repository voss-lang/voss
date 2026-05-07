from voss.ast_nodes import TryCatch, ReturnStmt, YieldStmt, IncludeStmt, Identifier

def test_try_catch_with_binding(parse_source):
    src = """
try {
  return risky()
} catch e {
  return fallback(e)
}
"""
    p = parse_source(src)
    t = p.body[0]
    assert isinstance(t, TryCatch)
    assert t.exc_name == "e"
    assert len(t.try_body) == 1 and len(t.catch_body) == 1

def test_try_catch_no_binding(parse_source):
    src = """
try {
  return one()
} catch {
  return two()
}
"""
    p = parse_source(src)
    t = p.body[0]
    assert isinstance(t, TryCatch)
    assert t.exc_name is None

def test_return_no_value(parse_source):
    p = parse_source("return")
    s = p.body[0]
    assert isinstance(s, ReturnStmt) and s.value is None

def test_return_with_value(parse_source):
    p = parse_source("return 42")
    s = p.body[0]
    assert isinstance(s, ReturnStmt) and s.value is not None

def test_yield_with_value(parse_source):
    p = parse_source("yield items")
    s = p.body[0]
    assert isinstance(s, YieldStmt) and isinstance(s.value, Identifier)

def test_include_stmt(parse_source):
    p = parse_source("include user_message")
    s = p.body[0]
    assert isinstance(s, IncludeStmt) and isinstance(s.value, Identifier)
