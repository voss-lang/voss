import asyncio
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from voss.harness import oauth
from voss.harness.server import app as appmod, preview

REAL_TURN = appmod._run_turn


@pytest.fixture
def setup(monkeypatch, tmp_path):
    engine, repo = tmp_path / 'engine', tmp_path / 'repo'
    engine.mkdir(); repo.mkdir()
    monkeypatch.chdir(engine)
    monkeypatch.setenv('XDG_CONFIG_HOME', str(engine / 'config'))
    def git(*args):
        return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.DEVNULL)
    git('init'); git('config', 'user.email', 'synthetic@example.test'); git('config', 'user.name', 'Synthetic')
    (repo / 'a.txt').write_text('original')
    git('add', 'a.txt'); git('commit', '-m', 'fixture')
    calls, turns = [], []
    graph = preview.Graph(tasks=[preview.Node(id='first', goal='Implement change', files=['a.txt'], criteria=['Change covered']),
                                 preview.Node(id='second', goal='Review change', depends_on=['first'], criteria=['Scope respected'])])
    availability = oauth.Availability(harness='codex', provider='openai', model='gpt-6-astra', available=True, code='oauth_present', message='synthetic', checked_at='synthetic')
    class Provider:
        blocked = None
        async def complete(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(parsed=graph)
        async def aclose(self): pass
    monkeypatch.setattr(oauth, 'prepare', lambda body: (availability, Provider() if availability.available else None))
    async def turn(session, text, mode):
        turns.append((session.execution_node, json.loads(text), mode))
        session.turn_outcome = 'done'
    monkeypatch.setattr(appmod, '_run_turn', turn)
    app = appmod.create_app('synthetic-preview', oauth_only=True)
    body = {'source': {'kind':'objective', 'text':'Implement a scoped change'}, 'cwd':str(repo), 'harness':'codex', 'model':'gpt-6-astra',
            'tier':'apply', 'scope':{'allow':['**/*'], 'deny':['.env*']}, 'context':[{'id':'brief','text':'Synthetic project context'}]}
    yield SimpleNamespace(app=app, body=body, graph=graph, calls=calls, turns=turns, repo=repo, engine=engine, git=git, availability=availability)
    app.state.sessions.journal.close()


def client(f):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=f.app), base_url='http://test', headers={'Authorization':'Bearer synthetic-preview'})


@pytest.mark.asyncio
@pytest.mark.parametrize('kind', ['objective','prd','issue'])
async def test_preview_is_read_only_and_start_dispatches_exact_graph_once(setup, kind):
    f = setup
    f.body['source'].update(kind=kind, reference='synthetic-source', revision='r1')
    before = f.git('status','--porcelain')
    async with client(f) as api:
        response = (await api.post('/plans/preview', json=f.body)).json()
        assert response['status'] == 'prepared'
        plan = response['preview']
        assert plan['accepted_context'] == ['brief']
        assert plan['tasks'][1]['depends_on'] == [plan['tasks'][0]['id']]
        assert f.calls[0]['response_format'] is preview.Graph
        assert json.loads(f.calls[0]['messages'][1]['content'])['context'] == f.body['context']
        assert f.turns == [] and f.app.state.sessions.list() == []
        assert list(f.engine.iterdir()) == []
        assert f.git('status','--porcelain') == before
        body = {'revision':plan['revision'], 'briefing':f.body}
        first, second = await asyncio.gather(*(api.post(f"/plans/{plan['id']}/start", json=body) for _ in range(2)))
        assert first.json() == second.json()
        result = first.json()
        assert result['status'] == 'accepted'
        session = f.app.state.sessions.get(result['session_id'])
        if session.task: await session.task
        assert [row[0] for row in f.turns] == [node['id'] for node in plan['tasks']]
        assert [row[1]['approved_task'] for row in f.turns] == plan['tasks']
        assert len(f.calls) == 1
        snapshot = (await api.get(f"/session/{session.id}/task")).json()
        assert snapshot['execution_plan'] == plan
        assert snapshot['phase'] == 'completed'
        assert set(snapshot['node_states'].values()) == {'completed'}
        assert [node['id'] for node in snapshot['graph']['nodes']] == [node['id'] for node in plan['tasks']]
        assert snapshot['graph']['revision'] == plan['revision']
        assert all(node['attempts'][0]['plan_revision'] == plan['revision'] for node in snapshot['graph']['nodes'])
        assert (await api.post(f'/session/{session.id}/message', json={'parts':[{'text':'replace graph'}]})).json()['status'] == 'preview_required'
        f.app.state.sessions.journal.close()
        restarted = appmod.create_app('synthetic-preview', oauth_only=True)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=restarted), base_url='http://test', headers=api.headers) as reopened:
            assert (await reopened.post(f"/plans/{plan['id']}/start", json=body)).json() == result
            assert restarted.state.sessions.list() == []
        restarted.state.sessions.journal.close()


@pytest.mark.asyncio
async def test_switching_branch_at_the_same_head_requires_a_new_preview(setup):
    f = setup
    async with client(f) as api:
        plan = (await api.post('/plans/preview', json=f.body)).json()['preview']
        f.git('checkout', '-b', 'other-fixture-branch')
        assert f.git('rev-parse', 'HEAD').decode().strip() == plan['base_revision']
        result = (await api.post(f"/plans/{plan['id']}/start", json={'revision':plan['revision'], 'briefing':f.body})).json()
        assert result['status'] == 'stale'
        assert f.turns == []


@pytest.mark.asyncio
@pytest.mark.parametrize('change', ['source','scope','context','harness','tier','head','working_tree','policy','global_policy','model','revision'])
async def test_stale_start_launches_nothing(setup, change):
    f = setup
    async with client(f) as api:
        plan = (await api.post('/plans/preview',json=f.body)).json()['preview']
        request = {'revision':plan['revision'],'briefing':f.body}
        if change == 'head': f.git('commit','--allow-empty','-m','new base')
        elif change == 'working_tree': (f.repo/'a.txt').write_text('changed after preview')
        elif change == 'policy':
            (f.repo/'.voss').mkdir(); (f.repo/'.voss/permissions.yml').write_text('changed policy')
        elif change == 'global_policy':
            policy = f.engine / 'config/voss/permissions.json'
            policy.parent.mkdir(parents=True); policy.write_text('{}')
        elif change == 'model': f.body['model'] = 'different-model'
        elif change == 'revision': request['revision'] = 'different'
        elif change == 'source': f.body['source']['text'] = 'Changed objective'
        elif change == 'scope': f.body['scope']['allow'] = ['elsewhere/*']
        elif change == 'context': f.body['context'][0]['text'] = 'Changed context'
        else: f.body[change] = {'harness':'claude','tier':'plan'}[change]
        assert (await api.post(f"/plans/{plan['id']}/start",json=request)).json()['status'] == 'stale'
        assert f.turns == [] and f.app.state.sessions.list() == []


@pytest.mark.asyncio
async def test_auth_loss_and_unsupported_guarantees_never_dispatch(setup):
    f = setup
    async with client(f) as api:
        for update in [{'tier':'autonomous'}, {'swarm':{'builders':2,'agent':'codex'}}]:
            assert (await api.post('/plans/preview',json={**f.body,**update})).json()['status'] == 'unsupported'
        assert f.calls == []
        plan = (await api.post('/plans/preview',json=f.body)).json()['preview']
        request = {'revision':plan['revision'],'briefing':f.body}
        f.availability.available = False
        assert (await api.post(f"/plans/{plan['id']}/start",json=request)).json()['status'] == 'unavailable'
        assert f.turns == [] and f.app.state.sessions.list() == []
        f.availability.available = True
        assert (await api.get(f"/plans/{plan['id']}")).json()['status'] == 'prepared'
        assert f.turns == []
        result = (await api.post(f"/plans/{plan['id']}/start",json=request)).json()
        assert result['status'] == 'accepted'
        session = f.app.state.sessions.get(result['session_id'])
        if session.task: await session.task


@pytest.mark.asyncio
@pytest.mark.parametrize('invalid', ['cycle','missing','duplicate','scope'])
async def test_invalid_graph_is_never_offered_for_start(setup, invalid):
    f = setup
    if invalid == 'cycle': f.graph.tasks[0].depends_on = ['second']
    elif invalid == 'missing': f.graph.tasks[0].depends_on = ['absent']
    elif invalid == 'duplicate': f.graph.tasks[1].id = 'first'
    else: f.graph.tasks[0].files = ['.env']
    async with client(f) as api:
        assert (await api.post('/plans/preview', json=f.body)).json()['status'] == 'invalid'
    assert f.app.state.previews == {} and f.turns == []


@pytest.mark.asyncio
async def test_scope_cannot_be_expanded_by_path_traversal_shell_or_permission_approval(setup):
    f = setup
    async with client(f) as api:
        plan = (await api.post('/plans/preview',json=f.body)).json()['preview']
    gate = SimpleNamespace(check=lambda *args, **kwargs: (True,'approved'))
    session = SimpleNamespace(execution_plan=plan, execution_node=plan['tasks'][0]['id'])
    preview.install_scope(gate, session)
    assert gate.check('fs_write',{'path':'a.txt'},is_mutating=True)[0]
    (f.repo/'linked.txt').symlink_to(f.engine/'outside.txt')
    for name,args,kwargs in [('fs_write',{'path':'../outside.txt'},{'is_mutating':True}), ('fs_edit',{'path':'.env'},{'is_mutating':True}),
                             ('fs_write',{'path':'linked.txt'},{'is_mutating':True}), ('shell_run',{'cmd':'git commit'},{'is_mutating':True}),
                             ('custom_writer',{}, {'is_mutating':True}), ('fetch',{}, {'is_network':True})]:
        assert not gate.check(name,args,**kwargs)[0]


@pytest.mark.asyncio
@pytest.mark.parametrize('outcome', ['error', 'authentication', 'cancelled', 'clarify'])
async def test_interrupted_node_never_starts_its_dependents(setup, monkeypatch, outcome):
    f = setup
    entered = asyncio.Event()
    async def turn(session, text, mode):
        f.turns.append(session.execution_node)
        entered.set()
        if outcome == 'cancelled': await asyncio.Event().wait()
        elif outcome == 'authentication':
            session.provider.blocked = f.availability.model_copy(update={'available':False})
        elif outcome == 'clarify':
            session.journal.update(session.id, pending_actions=[{'kind':'clarify'}])
        else: raise RuntimeError('synthetic failure')
    monkeypatch.setattr(appmod, '_run_turn', turn)
    async with client(f) as api:
        plan = (await api.post('/plans/preview',json=f.body)).json()['preview']
        request = {'revision':plan['revision'],'briefing':f.body}
        result = (await api.post(f"/plans/{plan['id']}/start",json=request)).json()
        session = f.app.state.sessions.get(result['session_id'])
        task = session.task
        await entered.wait()
        if outcome == 'cancelled':
            assert (await api.post(f'/session/{session.id}/abort')).json()['status'] == 'cancelled'
        else: await task
        snapshot = session.journal.snapshot(session.id)
        assert snapshot.phase == {'error':'failed','authentication':'waiting','cancelled':'cancelled','clarify':'waiting'}[outcome]
        assert snapshot.node_states[plan['tasks'][1]['id']] == 'queued'
        assert len(f.turns) == 1
        assert (await api.post(f"/plans/{plan['id']}/start",json=request)).json() == result
        assert len(f.turns) == 1
        session.journal.close()
        from voss.harness.server.task_journal import TaskJournal
        reopened = TaskJournal(f.engine / '.voss/task-journal.sqlite3')
        restored = reopened.snapshot(session.id)
        if outcome in {'authentication','clarify'}:
            assert restored.phase == 'interrupted'
            assert restored.node_states[plan['tasks'][0]['id']] == 'interrupted'
        reopened.close()


@pytest.mark.asyncio
async def test_native_turn_uses_only_scoped_file_tools(setup, monkeypatch):
    f = setup
    monkeypatch.delenv('VOSS_SERVE_FAKE_TURN', raising=False)
    monkeypatch.setenv('XDG_CONFIG_HOME', str(f.engine / 'config'))
    def unexpected(*args, **kwargs): raise AssertionError('unexpected auxiliary service')
    monkeypatch.setattr(appmod, 'attach_mcp_tools', unexpected)
    monkeypatch.setattr(appmod, 'open_memory_store', unexpected)
    from voss.harness import cli
    auxiliary_calls = []
    monkeypatch.setattr(cli, '_render_project_index_text', lambda *a, **kw: auxiliary_calls.append('index'))
    monkeypatch.setattr(cli, '_scoped_turn', lambda *a, **kw: auxiliary_calls.append('recall'))
    seen = []
    async def run(text, **kwargs):
        seen.append(kwargs)
        gate = kwargs['permissions']
        assert set(kwargs['tools']) == preview.TOOLS
        assert not gate.check('git_diff', {'path':'--output=outside.txt'})[0]
        assert not gate.check('fs_write', {'path':'outside.txt'}, is_mutating=True)[0]
        assert not gate.check('fs_write', {'path':'a.txt'}, is_mutating=True)[0]  # Plan mode remains read-only.
        return SimpleNamespace(plan=None, run=None, final='synthetic', confidence=1, cost_usd=0)
    monkeypatch.setattr(appmod, 'run_turn', run)
    async with client(f) as api:
        plan = preview.Preview.model_validate((await api.post('/plans/preview',json=f.body)).json()['preview'])
    _, provider = oauth.prepare(oauth.PreflightBody(harness='codex',model='gpt-6-astra'))
    session = f.app.state.sessions.create(cwd=f.repo, model='gpt-6-astra', provider=provider)
    session.execution_plan = plan.model_dump()
    session.execution_node = plan.tasks[0].id
    await REAL_TURN(session, 'approved task', 'plan')
    assert session.turn_outcome == 'unknown'
    assert len(seen) == 1
    assert auxiliary_calls == []
    assert seen[0]['provider'] is provider and seen[0]['code_recall_text'] == ''
