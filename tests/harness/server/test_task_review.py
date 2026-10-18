import json
import subprocess

import httpx
import pytest

from voss.harness.server import app as appmod, task_graph
from voss.harness.decision_review import candidate_review_path


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.DEVNULL).decode().strip()


@pytest.mark.asyncio
async def test_exact_attempt_review_is_read_only_and_changes_invalidate_evidence(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    repo = tmp_path / 'repo'; repo.mkdir()
    git(repo, 'init', '-b', 'main')
    git(repo, 'config', 'user.name', 'Fixture'); git(repo, 'config', 'user.email', 'fixture@example.invalid')
    (repo / '.gitignore').write_text('.voss/\n')
    git(repo, 'add', '.'); git(repo, 'commit', '-m', 'Synthetic base')
    base = git(repo, 'rev-parse', 'HEAD')
    (repo / 'file').write_text('candidate')
    git(repo, 'add', '.'); git(repo, 'commit', '-m', 'Synthetic candidate')
    head = git(repo, 'rev-parse', 'HEAD')
    app = appmod.create_app('synthetic-review')
    journal = app.state.sessions.journal
    journal.register('owner')
    graph = task_graph.Graph(source='swarm', plan_id='swarm', revision='plan-revision', owner_session_id='owner', nodes=[
        task_graph.Node(id='node', goal='AC-1: first\nAC-2: second', criteria=['AC-1: first', 'AC-2: second'], attempts=[
            task_graph.Attempt(id='attempt', run_id='run', plan_revision='plan-revision', worktree=str(repo), repository=str(repo),
                branch='main', base_revision=base, candidate_revision=head)])])
    journal.update('owner', graph=graph.model_dump())
    path = candidate_review_path(repo, 'swarm', 'node'); path.parent.mkdir(parents=True)
    payload = {'task_review': {'v':1, 'swarm_id':'swarm','task_id':'node','attempt_id':'attempt', 'candidate_revision':head,
        'criteria':[{'id':'AC-1','text':'first'}, {'id':'AC-2','text':'second'}], 'criteria_source':'task_goal',
        'checks':[{'name':'tests','status':'failed'}, {'name':'scope','status':'passed'}]},
        'receipts':[{'purpose':'review.requirements', 'mode':'shadow', 'status':'answered', 'detail':{
            'criterion_ids':['AC-1','AC-2'], 'candidate':{'head':head}, 'labels':{'AC-1':'supported','AC-2':'contradicted'}}}]}
    def save(): path.write_text(json.dumps(payload))
    save()
    before = journal.snapshot('owner').watermark
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test', headers={'Authorization':'Bearer synthetic-review'}) as api:
        async def read(attempt='attempt'):
            response = await api.get('/session/owner/review', params={'node_id':'node','attempt_id':attempt})
            assert response.status_code == 200, response.text
            return response.json()
        first = await read()
        assert first['status'] == 'available' and first['base_revision'] == base
        assert first['rows'][0]['test_outcome'] == 'failed' and first['rows'][0]['reviewer_outcome'] == 'supported'
        assert first['rows'][1]['reviewer_outcome'] == 'contradicted'
        assert (await read())['evidence_revision'] == first['evidence_revision']
        assert (await read('wrong'))['status'] == 'unavailable'
        for status in ['passed','skipped','not_run','unavailable','stale']:
            payload['task_review']['checks'][0]['status'] = status; save()
            result = await read()
            assert result['rows'][0]['test_outcome'] == status
            assert result['rows'][1]['unresolved']
            assert result['evidence_revision'] != first['evidence_revision']
        graph.revision = 'changed-plan'
        journal.update('owner', graph=graph.model_dump())
        assert (await read())['status'] == 'stale'
        graph.revision = 'plan-revision'
        journal.update('owner', graph=graph.model_dump())
        payload['task_review']['attempt_id'] = 'other'; save()
        assert all(r['test_outcome'] == 'unavailable' for r in (await read())['rows'])
        payload['task_review']['attempt_id'] = 'attempt'
        payload['receipts'][0]['detail']['candidate']['head'] = base; save()
        assert (await read())['status'] == 'stale'
        payload['receipts'][0]['detail']['candidate']['head'] = head
        payload['receipts'][0]['detail']['labels']['AC-1'] = ['malformed']; save()
        assert (await read())['status'] == 'partial'
        path.unlink()
        assert (await read())['status'] == 'partial'
        save()
        (repo / 'file').write_text('dirty')
        assert (await read())['status'] == 'stale'
        git(repo, 'add', '.'); git(repo, 'commit', '-m', 'Synthetic changed candidate')
        assert (await read())['status'] == 'stale'
        graph.source = 'preview'
        journal.update('owner', graph=graph.model_dump())
        before = journal.snapshot('owner').watermark
        assert all(r['reviewer_outcome'] == 'unavailable' for r in (await read())['rows'])
    assert app.state.sessions.list() == []
    assert journal.snapshot('owner').watermark == before
    journal.close()
