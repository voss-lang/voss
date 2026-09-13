<?php

namespace Tests\Feature;

use App\Models\Memory;
use Illuminate\Foundation\Testing\LazilyRefreshDatabase;
use Illuminate\Support\Facades\DB;
use Illuminate\Testing\TestResponse;
use Tests\TestCase;

class MemoryApiTest extends TestCase
{
    use LazilyRefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();
        config(['voss_memory.api_token' => 'test-token']);
    }

    public function test_health_is_public_and_mutations_require_a_configured_bearer_token(): void
    {
        $health = $this->getJson('/v1/health');

        $health->assertOk()->assertExactJson([
            'api_version' => 1,
            'status' => 'ready',
        ]);

        $unauthorized = $this->postJson('/v1/projects', ['id' => 'project-a']);

        $unauthorized->assertUnauthorized()->assertExactJson([
            'error' => [
                'code' => 'unauthorized',
                'message' => 'A valid bearer token is required.',
            ],
        ]);
    }

    public function test_project_registration_is_validated_and_repeat_registration_does_not_duplicate(): void
    {
        $invalid = $this->postJson('/v1/projects', ['id' => 'project/unsafe'], $this->authHeaders());

        $invalid->assertUnprocessable()->assertJsonPath('error.code', 'validation_error');
        $this->assertDatabaseCount('projects', 0);

        $first = $this->registerProject('project-a', 'Synthetic project');
        $second = $this->registerProject('project-a', 'Synthetic project');

        $first->assertOk()->assertJsonPath('data.id', 'project-a')->assertJsonPath('data.name', 'Synthetic project');
        $second->assertOk()->assertJsonPath('data.id', 'project-a');
        $this->assertDatabaseCount('projects', 1);
    }

    public function test_create_list_and_show_preserve_body_provenance_and_scope(): void
    {
        $this->registerProject('project-a');

        $created = $this->createMemory('project-a', [
            'body' => "  SQLite FTS5 convention\n",
            'provenance' => ['source' => 'synthetic-fixture', 'quote' => 'Keep bytes'],
        ], 'create-preserve');

        $created->assertCreated();
        $created->assertJsonStructure([
            'data' => [
                'id', 'project_id', 'kind', 'body', 'revision', 'pinned', 'status',
                'superseded_by', 'provenance', 'created_at', 'updated_at',
            ],
        ]);
        $created->assertJsonPath('data.body', "  SQLite FTS5 convention\n");
        $created->assertJsonPath('data.provenance.source', 'synthetic-fixture');
        $this->assertDatabaseHas('memories', [
            'project_id' => 'project-a',
            'kind' => 'note',
            'body' => "  SQLite FTS5 convention\n",
            'revision' => 1,
            'status' => Memory::STATUS_ACTIVE,
        ]);

        $memoryId = $this->memoryId($created);
        $listed = $this->getJson('/v1/projects/project-a/memories?kind=note&pinned=false&limit=1', $this->authHeaders());
        $shown = $this->getJson('/v1/projects/project-a/memories/'.$memoryId, $this->authHeaders());

        $listed->assertOk()->assertJsonPath('data.0.id', $memoryId)->assertJsonPath('next_cursor', null);
        $shown->assertOk()->assertJsonPath('data.id', $memoryId)->assertJsonPath('data.body', "  SQLite FTS5 convention\n");

        $emptyProvenance = $this->createMemory('project-a', [
            'body' => 'Empty object provenance',
            'provenance' => new \stdClass,
        ], 'create-empty-provenance');
        $emptyPayload = json_decode($emptyProvenance->getContent(), false, 512, JSON_THROW_ON_ERROR);
        $emptyProvenance->assertCreated();
        $this->assertIsObject($emptyPayload->data->provenance);
    }

    public function test_idempotent_create_replays_unchanged_result_and_conflicts_on_payload_reuse(): void
    {
        $this->registerProject('project-a');
        $payload = ['kind' => 'decision', 'body' => 'Use a local SQLite database.'];

        $first = $this->createMemory('project-a', $payload, 'same-create');
        $replay = $this->createMemory('project-a', $payload, 'same-create');
        $different = $this->createMemory('project-a', ['kind' => 'decision', 'body' => 'Use another database.'], 'same-create');

        $first->assertCreated();
        $replay->assertCreated();
        $this->assertSame($first->json(), $replay->json());
        $different->assertConflict()->assertJsonPath('error.code', 'idempotency_conflict');
        $this->assertDatabaseCount('memories', 1);
    }

    public function test_idempotency_header_cannot_be_supplied_in_json_and_update_checks_revisions(): void
    {
        $this->registerProject('project-a');
        $created = $this->createMemory('project-a', [], 'create-update');
        $memoryId = $this->memoryId($created);

        $missingHeader = $this->postJson('/v1/projects/project-a/memories', [
            'kind' => 'note',
            'body' => 'body field key must not authorize this request',
            'idempotency_key' => 'body-only-key',
        ], $this->authHeaders());
        $updated = $this->updateMemory($memoryId, ['expected_revision' => 1, 'body' => 'Updated body', 'pinned' => true], 'update-one');
        $stale = $this->updateMemory($memoryId, ['expected_revision' => 1, 'body' => 'Stale body'], 'update-stale');
        $replay = $this->updateMemory($memoryId, ['expected_revision' => 1, 'body' => 'Updated body', 'pinned' => true], 'update-one');

        $missingHeader->assertUnprocessable()->assertJsonPath('error.code', 'validation_error');
        $updated->assertOk()->assertJsonPath('data.revision', 2)->assertJsonPath('data.pinned', true)->assertJsonPath('data.body', 'Updated body');
        $stale->assertConflict()->assertJsonPath('error.code', 'revision_conflict');
        $replay->assertOk()->assertJsonPath('data.revision', 2);
        $this->assertDatabaseHas('memories', ['id' => $memoryId, 'body' => 'Updated body', 'revision' => 2, 'pinned' => 1]);
    }

    public function test_replaying_a_revised_update_returns_conflict_without_old_content(): void
    {
        $this->registerProject('project-a');
        $created = $this->createMemory('project-a', ['body' => 'Initial body'], 'create-replay');
        $memoryId = $this->memoryId($created);

        $firstUpdate = $this->updateMemory($memoryId, ['expected_revision' => 1, 'body' => 'First body'], 'update-replay');
        $this->updateMemory($memoryId, ['expected_revision' => 2, 'body' => 'Second body'], 'update-second')->assertOk();
        $staleReplay = $this->updateMemory($memoryId, ['expected_revision' => 1, 'body' => 'First body'], 'update-replay');

        $firstUpdate->assertOk();
        $staleReplay->assertConflict()->assertJsonPath('error.code', 'stale_replay')->assertJsonMissingPath('data.body');
        $this->assertDatabaseHas('memories', ['id' => $memoryId, 'body' => 'Second body', 'revision' => 3]);
    }

    public function test_supersession_unpins_and_replay_returns_the_unchanged_superseded_record(): void
    {
        $this->registerProject('project-a');
        $old = $this->createMemory('project-a', ['body' => 'Old convention'], 'create-old');
        $new = $this->createMemory('project-a', ['body' => 'New convention'], 'create-new');
        $oldId = $this->memoryId($old);
        $newId = $this->memoryId($new);

        $superseded = $this->updateMemory($oldId, ['expected_revision' => 1, 'pinned' => true, 'superseded_by' => $newId], 'supersede-old');
        $replay = $this->updateMemory($oldId, ['expected_revision' => 1, 'pinned' => true, 'superseded_by' => $newId], 'supersede-old');
        $search = $this->searchMemory('project-a', 'Old convention');

        $superseded->assertOk()->assertJsonPath('data.status', Memory::STATUS_SUPERSEDED)->assertJsonPath('data.pinned', false)->assertJsonPath('data.superseded_by', $newId);
        $replay->assertOk()->assertJsonPath('data.status', Memory::STATUS_SUPERSEDED)->assertJsonPath('data.revision', 2);
        $search->assertOk()->assertJsonCount(0, 'data');
        $this->assertDatabaseHas('memories', ['id' => $oldId, 'status' => Memory::STATUS_SUPERSEDED, 'pinned' => 0]);
    }

    public function test_delete_removes_body_provenance_pin_and_search_and_replays_only_a_tombstone(): void
    {
        $this->registerProject('project-a');
        $created = $this->createMemory('project-a', [
            'body' => 'Sensitive synthetic deletion fixture',
            'provenance' => ['evidence_quote' => 'must not remain'],
        ], 'create-delete');
        $memoryId = $this->memoryId($created);
        $this->updateMemory($memoryId, ['expected_revision' => 1, 'pinned' => true], 'pin-before-delete')->assertOk();

        $deleted = $this->deleteMemory($memoryId, 2, 'delete-memory');
        $replay = $this->deleteMemory($memoryId, 2, 'delete-memory');
        $oldCreateReplay = $this->createMemory('project-a', [
            'body' => 'Sensitive synthetic deletion fixture',
            'provenance' => ['evidence_quote' => 'must not remain'],
        ], 'create-delete');
        $list = $this->getJson('/v1/projects/project-a/memories', $this->authHeaders());
        $show = $this->getJson('/v1/projects/project-a/memories/'.$memoryId, $this->authHeaders());
        $search = $this->searchMemory('project-a', 'Sensitive synthetic deletion fixture');

        $deleted->assertOk()->assertExactJson(['data' => ['id' => $memoryId, 'revision' => 3, 'status' => Memory::STATUS_DELETED]]);
        $replay->assertOk()->assertExactJson(['data' => ['id' => $memoryId, 'revision' => 3, 'status' => Memory::STATUS_DELETED]]);
        $oldCreateReplay->assertConflict()->assertJsonPath('error.code', 'memory_deleted')->assertJsonMissingPath('data.body');
        $list->assertOk()->assertJsonCount(0, 'data');
        $show->assertNotFound()->assertJsonPath('error.code', 'not_found');
        $search->assertOk()->assertJsonCount(0, 'data');
        $this->assertDatabaseHas('memories', ['id' => $memoryId, 'body' => null, 'provenance' => null, 'pinned' => 0, 'status' => Memory::STATUS_DELETED, 'revision' => 3]);
        $this->assertSame(0, DB::table('memory_search')->where('memory_id', $memoryId)->count());
    }

    public function test_search_escapes_fts_operators_splits_symbols_and_filters_kinds(): void
    {
        $this->registerProject('project-a');
        $note = $this->createMemory('project-a', ['body' => 'SQLite FTS5 handles foo_bar and CamelCase safely'], 'search-note');
        $this->createMemory('project-a', ['kind' => 'decision', 'body' => 'SQLite decision record'], 'search-decision');
        $noteId = $this->memoryId($note);

        $symbol = $this->searchMemory('project-a', 'CamelCase');
        $operator = $this->searchMemory('project-a', 'foo" OR *', ['kinds' => ['note'], 'top_k' => 1]);
        $punctuation = $this->searchMemory('project-a', '***');

        $symbol->assertOk()->assertJsonPath('data.0.id', $noteId)->assertJsonStructure(['data' => [['score']]]);
        $operator->assertOk()->assertJsonCount(0, 'data');
        $punctuation->assertUnprocessable()->assertJsonPath('error.code', 'validation_error');
    }

    public function test_project_scope_isolation_returns_not_found_and_search_cannot_cross_projects(): void
    {
        $this->registerProject('project-a');
        $this->registerProject('project-b');
        $created = $this->createMemory('project-a', ['body' => 'project A private convention'], 'scope-memory');
        $memoryId = $this->memoryId($created);

        $show = $this->getJson('/v1/projects/project-b/memories/'.$memoryId, $this->authHeaders());
        $update = $this->updateMemoryForProject('project-b', $memoryId, ['expected_revision' => 1, 'body' => 'cross project'], 'scope-update');
        $delete = $this->deleteMemoryForProject('project-b', $memoryId, 1, 'scope-delete');
        $search = $this->searchMemory('project-b', 'private convention');

        $show->assertNotFound()->assertJsonPath('error.code', 'not_found');
        $update->assertNotFound()->assertJsonPath('error.code', 'not_found');
        $delete->assertNotFound()->assertJsonPath('error.code', 'not_found');
        $search->assertOk()->assertJsonCount(0, 'data');
        $this->assertDatabaseHas('memories', ['id' => $memoryId, 'project_id' => 'project-a', 'body' => 'project A private convention']);
    }

    public function test_cursor_pagination_is_bounded_and_opaque(): void
    {
        $this->registerProject('project-a');
        $this->createMemory('project-a', ['body' => 'first'], 'cursor-1');
        $this->createMemory('project-a', ['body' => 'second'], 'cursor-2');

        $first = $this->getJson('/v1/projects/project-a/memories?limit=1', $this->authHeaders());
        $cursor = $first->json('next_cursor');
        $second = $this->getJson('/v1/projects/project-a/memories?limit=1&cursor='.$cursor, $this->authHeaders());
        $malformed = $this->getJson('/v1/projects/project-a/memories?cursor[]=invalid', $this->authHeaders());

        $first->assertOk()->assertJsonCount(1, 'data')->assertJsonPath('next_cursor', $cursor);
        $second->assertOk()->assertJsonCount(1, 'data')->assertJsonPath('next_cursor', null);
        $malformed->assertUnprocessable()->assertJsonPath('error.code', 'validation_error');
        $this->assertNotSame($first->json('data.0.id'), $second->json('data.0.id'));
    }

    public function test_a_non_string_cursor_returns_validation_error(): void
    {
        $this->registerProject('project-a');

        $this->getJson('/v1/projects/project-a/memories?cursor[value]=invalid', $this->authHeaders())
            ->assertUnprocessable()
            ->assertJsonPath('error.code', 'validation_error');
    }

    private function registerProject(string $id, ?string $name = null): TestResponse
    {
        $payload = ['id' => $id];

        if ($name !== null) {
            $payload['name'] = $name;
        }

        return $this->postJson('/v1/projects', $payload, $this->authHeaders());
    }

    private function createMemory(string $project, array $overrides, string $key): TestResponse
    {
        return $this->postJson(
            '/v1/projects/'.$project.'/memories',
            array_merge(['kind' => 'note', 'body' => 'Synthetic memory body'], $overrides),
            $this->authHeaders(['Idempotency-Key' => $key]),
        );
    }

    private function updateMemory(string $memoryId, array $payload, string $key): TestResponse
    {
        return $this->updateMemoryForProject('project-a', $memoryId, $payload, $key);
    }

    private function updateMemoryForProject(string $project, string $memoryId, array $payload, string $key): TestResponse
    {
        return $this->patchJson('/v1/projects/'.$project.'/memories/'.$memoryId, $payload, $this->authHeaders(['Idempotency-Key' => $key]));
    }

    private function deleteMemory(string $memoryId, int $revision, string $key): TestResponse
    {
        return $this->deleteMemoryForProject('project-a', $memoryId, $revision, $key);
    }

    private function deleteMemoryForProject(string $project, string $memoryId, int $revision, string $key): TestResponse
    {
        return $this->deleteJson('/v1/projects/'.$project.'/memories/'.$memoryId, ['expected_revision' => $revision], $this->authHeaders(['Idempotency-Key' => $key]));
    }

    private function searchMemory(string $project, string $query, array $options = []): TestResponse
    {
        return $this->postJson('/v1/projects/'.$project.'/search', array_merge(['query' => $query], $options), $this->authHeaders());
    }

    private function memoryId(TestResponse $response): string
    {
        $id = $response->json('data.id');
        $this->assertIsString($id);

        return $id;
    }

    private function authHeaders(array $extra = []): array
    {
        return array_merge([
            'Authorization' => 'Bearer test-token',
            'Accept' => 'application/json',
        ], $extra);
    }
}
