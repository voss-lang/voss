from voss.harness.em.loop import _execute_plan
from voss.harness.em.schema import CreateTicketOp, EMPlanResponse, SetACOp


class RecordingHandle:
    def __init__(self):
        self.tickets = []
        self.acs = []

    def create_ticket(self, **kw):
        self.tickets.append(kw)

    def set_ac(self, card_id, text):
        self.acs.append((card_id, text))


def test_create_ticket_keeps_one_criterion_per_line():
    handle = RecordingHandle()
    plan = EMPlanResponse(ops=[CreateTicketOp(
        original_idea="idea", acceptance_criteria=["handles a, b, and c", "logs errors"],
        dod=["tests pass", "docs updated"], worker_role="backend",
    )])
    assert _execute_plan(handle, plan) == []
    [ticket] = handle.tickets
    assert ticket["acceptance_criteria"] == "handles a, b, and c\nlogs errors"
    assert ticket["dod"] == "tests pass, docs updated"


def test_set_ac_keeps_one_criterion_per_line():
    handle = RecordingHandle()
    assert _execute_plan(handle, EMPlanResponse(ops=[SetACOp(card_id="x", acceptance_criteria=["one, two", "three"])])) == []
    assert handle.acs == [("x", "one, two\nthree")]
