<?php

namespace App\Services;

use App\Exceptions\ApiException;
use App\Models\Memory;
use App\Models\MutationReceipt;
use App\Models\Project;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

class MemoryMutationService
{
    public function __construct(private readonly MemorySearchIndex $searchIndex) {}

    /**
     * @param  array{kind: string, body: string, provenance?: array<string, mixed>|null}  $attributes
     * @return array{memory: Memory, status: int}
     */
    public function create(Project $project, string $idempotencyKey, array $attributes): array
    {
        return DB::transaction(function () use ($project, $idempotencyKey, $attributes): array {
            $hash = $this->requestHash('create', $project->id, null, $attributes);
            $receipt = $this->receipt($project, $idempotencyKey);

            if ($receipt !== null) {
                $this->assertMatchingReceipt($receipt, 'create', $hash);

                return $this->replayMemoryMutation($receipt, $project);
            }

            $memory = new Memory;
            $memory->fill([
                'id' => (string) Str::uuid(),
                'project_id' => $project->id,
                'kind' => $attributes['kind'],
                'body' => $attributes['body'],
                'revision' => 1,
                'pinned' => false,
                'status' => Memory::STATUS_ACTIVE,
                'superseded_by' => null,
                'provenance' => $attributes['provenance'] ?? null,
            ]);
            $memory->save();
            $this->searchIndex->replace($memory);

            $this->recordReceipt($project, $idempotencyKey, 'create', $hash, $memory, 201);

            return ['memory' => $memory, 'status' => 201];
        }, 3);
    }

    /**
     * @param  array{expected_revision: int, body?: string, pinned?: bool, superseded_by?: string|null}  $attributes
     * @return array{memory: Memory, status: int}
     */
    public function update(Project $project, string $memoryId, string $idempotencyKey, array $attributes): array
    {
        return DB::transaction(function () use ($project, $memoryId, $idempotencyKey, $attributes): array {
            $hash = $this->requestHash('update', $project->id, $memoryId, $attributes);
            $receipt = $this->receipt($project, $idempotencyKey);

            if ($receipt !== null) {
                $this->assertMatchingReceipt($receipt, 'update', $hash);

                return $this->replayMemoryMutation($receipt, $project);
            }

            $memory = $this->memory($project, $memoryId);

            if ($memory->status === Memory::STATUS_DELETED) {
                throw new ApiException('memory_deleted', 'Memory has been deleted.', 409);
            }

            if ($memory->status !== Memory::STATUS_ACTIVE) {
                throw new ApiException('memory_inactive', 'Only active memories can be updated.', 409);
            }

            if ($memory->revision !== $attributes['expected_revision']) {
                throw new ApiException('revision_conflict', 'Memory revision does not match expected_revision.', 409);
            }

            if (array_key_exists('body', $attributes)) {
                $memory->body = $attributes['body'];
            }

            if (array_key_exists('pinned', $attributes)) {
                $memory->pinned = $attributes['pinned'];
            }

            if (array_key_exists('superseded_by', $attributes) && $attributes['superseded_by'] !== null) {
                $target = Memory::query()
                    ->where('project_id', $project->id)
                    ->whereKey($attributes['superseded_by'])
                    ->first();

                if ($target === null) {
                    throw new ApiException('not_found', 'Supersession target was not found.', 404);
                }

                if ($target->id === $memory->id) {
                    throw new ApiException('conflict', 'A memory cannot supersede itself.', 409);
                }

                if ($target->status !== Memory::STATUS_ACTIVE) {
                    throw new ApiException('conflict', 'Supersession target must be active.', 409);
                }

                $memory->status = Memory::STATUS_SUPERSEDED;
                $memory->pinned = false;
                $memory->superseded_by = $target->id;
            }

            $memory->revision++;
            $memory->save();
            $this->searchIndex->replace($memory);

            $this->recordReceipt($project, $idempotencyKey, 'update', $hash, $memory, 200);

            return ['memory' => $memory, 'status' => 200];
        }, 3);
    }

    /**
     * @return array{data: array{id: string, revision: int, status: string}, status: int}
     */
    public function delete(Project $project, string $memoryId, string $idempotencyKey, int $expectedRevision): array
    {
        return DB::transaction(function () use ($project, $memoryId, $idempotencyKey, $expectedRevision): array {
            $attributes = ['expected_revision' => $expectedRevision];
            $hash = $this->requestHash('delete', $project->id, $memoryId, $attributes);
            $receipt = $this->receipt($project, $idempotencyKey);

            if ($receipt !== null) {
                $this->assertMatchingReceipt($receipt, 'delete', $hash);

                return $this->replayDelete($receipt);
            }

            $memory = $this->memory($project, $memoryId);

            if ($memory->status === Memory::STATUS_DELETED) {
                throw new ApiException('memory_deleted', 'Memory has already been deleted.', 409);
            }

            if ($memory->revision !== $expectedRevision) {
                throw new ApiException('revision_conflict', 'Memory revision does not match expected_revision.', 409);
            }

            $memory->body = null;
            $memory->pinned = false;
            $memory->status = Memory::STATUS_DELETED;
            $memory->superseded_by = null;
            $memory->provenance = null;
            $memory->revision++;
            $memory->save();
            $this->searchIndex->remove($memory->id);

            $this->recordReceipt($project, $idempotencyKey, 'delete', $hash, $memory, 200);

            return [
                'data' => [
                    'id' => $memory->id,
                    'revision' => $memory->revision,
                    'status' => Memory::STATUS_DELETED,
                ],
                'status' => 200,
            ];
        }, 3);
    }

    private function receipt(Project $project, string $idempotencyKey): ?MutationReceipt
    {
        return MutationReceipt::query()
            ->where('project_id', $project->id)
            ->where('idempotency_key', $idempotencyKey)
            ->lockForUpdate()
            ->first();
    }

    private function memory(Project $project, string $memoryId): Memory
    {
        $memory = Memory::query()
            ->where('project_id', $project->id)
            ->whereKey($memoryId)
            ->first();

        if ($memory === null) {
            throw new ApiException('not_found', 'Memory was not found.', 404);
        }

        return $memory;
    }

    private function assertMatchingReceipt(MutationReceipt $receipt, string $operation, string $hash): void
    {
        if ($receipt->operation !== $operation || ! hash_equals($receipt->request_hash, $hash)) {
            throw new ApiException('idempotency_conflict', 'Idempotency key was already used for a different request.', 409);
        }
    }

    /**
     * @return array{memory: Memory, status: int}
     */
    private function replayMemoryMutation(MutationReceipt $receipt, Project $project): array
    {
        $memory = Memory::query()
            ->where('project_id', $project->id)
            ->whereKey($receipt->resource_id)
            ->first();

        if ($memory === null || $memory->status === Memory::STATUS_DELETED) {
            throw new ApiException('memory_deleted', 'Memory has been deleted.', 409);
        }

        if ($memory->revision !== $receipt->resource_revision || $memory->status !== $receipt->resource_status) {
            throw new ApiException('stale_replay', 'Idempotency result is no longer current.', 409);
        }

        return ['memory' => $memory, 'status' => $receipt->response_status];
    }

    /**
     * @return array{data: array{id: string, revision: int, status: string}, status: int}
     */
    private function replayDelete(MutationReceipt $receipt): array
    {
        if ($receipt->resource_status !== Memory::STATUS_DELETED) {
            throw new ApiException('stale_replay', 'Idempotency result is no longer current.', 409);
        }

        return [
            'data' => [
                'id' => $receipt->resource_id,
                'revision' => $receipt->resource_revision,
                'status' => Memory::STATUS_DELETED,
            ],
            'status' => $receipt->response_status,
        ];
    }

    private function recordReceipt(Project $project, string $idempotencyKey, string $operation, string $hash, Memory $memory, int $responseStatus): void
    {
        MutationReceipt::query()->create([
            'project_id' => $project->id,
            'idempotency_key' => $idempotencyKey,
            'operation' => $operation,
            'request_hash' => $hash,
            'resource_id' => $memory->id,
            'resource_revision' => $memory->revision,
            'resource_status' => $memory->status,
            'response_status' => $responseStatus,
        ]);
    }

    private function requestHash(string $operation, string $projectId, ?string $memoryId, array $attributes): string
    {
        $attributes = $this->canonicalize($attributes);

        return hash('sha256', json_encode([
            'operation' => $operation,
            'project_id' => $projectId,
            'memory_id' => $memoryId,
            'attributes' => $attributes,
        ], JSON_THROW_ON_ERROR | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));
    }

    private function canonicalize(mixed $value): mixed
    {
        if (! is_array($value)) {
            return $value;
        }

        if (array_is_list($value)) {
            return array_map(fn (mixed $item): mixed => $this->canonicalize($item), $value);
        }

        ksort($value);

        foreach ($value as $key => $item) {
            $value[$key] = $this->canonicalize($item);
        }

        return $value;
    }
}
