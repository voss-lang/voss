from voss.ast_nodes import LetStmt, TypeRef, Call, IntLit, BudgetArg

def test_let_with_value(parse_source):
    p = parse_source("let x = 42")
    s = p.body[0]
    assert isinstance(s, LetStmt) and s.name == "x"
    assert s.type_annot is None
    assert isinstance(s.value, IntLit) and s.value.value == 42

def test_let_with_type_and_value(parse_source):
    p = parse_source("let intent: probable<string> = classify(text)")
    s = p.body[0]
    assert isinstance(s, LetStmt) and s.name == "intent"
    assert isinstance(s.type_annot, TypeRef)
    assert s.type_annot.name.parts == ("probable",)
    assert isinstance(s.value, Call)

def test_let_no_value_memory_type(parse_source):
    p = parse_source("let history: memory.episodic(capacity: 20 turns)")
    s = p.body[0]
    assert isinstance(s, LetStmt) and s.name == "history"
    assert s.value is None
    assert isinstance(s.type_annot, TypeRef)
    assert s.type_annot.name.parts == ("memory", "episodic")
    assert s.type_annot.kwargs[0].name == "capacity"
    assert isinstance(s.type_annot.kwargs[0].value, BudgetArg)
    assert s.type_annot.kwargs[0].value.unit == "turns"
