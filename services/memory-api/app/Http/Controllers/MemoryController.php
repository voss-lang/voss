<?php

namespace App\Http\Controllers;

use App\Exceptions\ApiException;
use App\Http\Requests\CreateMemoryRequest;
use App\Http\Requests\DeleteMemoryRequest;
use App\Http\Requests\ListMemoriesRequest;
use App\Http\Requests\UpdateMemoryRequest;
use App\Http\Resources\MemoryResource;
use App\Models\Memory;
use App\Models\Project;
use App\Services\MemoryMutationService;
use Illuminate\Http\JsonResponse;

class MemoryController extends Controller
{
    public function __construct(private readonly MemoryMutationService $mutations) {}

    public function index(ListMemoriesRequest $request, string $project): JsonResponse
    {
        $this->project($project);
        $attributes = $request->validated();
        $limit = isset($attributes['limit']) ? (int) $attributes['limit'] : 50;
        $offset = $request->cursorOffset();

        $memories = Memory::query()
            ->active()
            ->where('project_id', $project)
            ->when(isset($attributes['kind']), fn ($query) => $query->where('kind', $attributes['kind']))
            ->when(array_key_exists('pinned', $attributes), fn ($query) => $query->where('pinned', $request->boolean('pinned')))
            ->orderByDesc('created_at')
            ->orderByDesc('id')
            ->offset($offset)
            ->limit($limit + 1)
            ->get();

        $hasNextPage = $memories->count() > $limit;
        $page = $memories->take($limit);

        return response()->json([
            'data' => MemoryResource::collection($page)->resolve($request),
            'next_cursor' => $hasNextPage ? $this->encodeCursor($offset + $limit) : null,
        ]);
    }

    public function store(CreateMemoryRequest $request, string $project): JsonResponse
    {
        $projectModel = $this->project($project);
        $attributes = $request->validated();
        $payload = [
            'kind' => $attributes['kind'],
            'body' => $attributes['body'],
        ];

        if (array_key_exists('provenance', $attributes)) {
            $payload['provenance'] = $attributes['provenance'];
        }

        $result = $this->mutations->create($projectModel, $request->idempotencyKey(), $payload);

        return (new MemoryResource($result['memory']))->response()->setStatusCode($result['status']);
    }

    public function show(string $project, string $memory): JsonResponse
    {
        $this->project($project);
        $record = Memory::query()->where('project_id', $project)->whereKey($memory)->first();

        if ($record === null || $record->status === Memory::STATUS_DELETED) {
            throw new ApiException('not_found', 'Memory was not found.', 404);
        }

        return (new MemoryResource($record))->response();
    }

    public function update(UpdateMemoryRequest $request, string $project, string $memory): JsonResponse
    {
        $projectModel = $this->project($project);
        $validated = $request->validated();
        $attributes = [
            'expected_revision' => $request->integer('expected_revision'),
        ];

        foreach (['body', 'pinned', 'superseded_by'] as $field) {
            if (array_key_exists($field, $validated)) {
                $attributes[$field] = $field === 'pinned' ? $request->boolean($field) : $validated[$field];
            }
        }

        $result = $this->mutations->update($projectModel, $memory, $request->idempotencyKey(), $attributes);

        return (new MemoryResource($result['memory']))->response()->setStatusCode($result['status']);
    }

    public function destroy(DeleteMemoryRequest $request, string $project, string $memory): JsonResponse
    {
        $projectModel = $this->project($project);
        $result = $this->mutations->delete($projectModel, $memory, $request->idempotencyKey(), $request->integer('expected_revision'));

        return response()->json(['data' => $result['data']], $result['status']);
    }

    private function project(string $project): Project
    {
        $record = Project::query()->find($project);

        if ($record === null) {
            throw new ApiException('not_found', 'Project was not found.', 404);
        }

        return $record;
    }

    private function encodeCursor(int $offset): string
    {
        return rtrim(strtr(base64_encode((string) $offset), '+/', '-_'), '=');
    }
}
