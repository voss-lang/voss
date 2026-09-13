<?php

namespace App\Http\Controllers;

use App\Exceptions\ApiException;
use App\Http\Requests\SearchMemoryRequest;
use App\Http\Resources\MemoryResource;
use App\Models\Memory;
use App\Models\Project;
use App\Services\MemorySearchIndex;
use Illuminate\Http\JsonResponse;
use Illuminate\Support\Facades\DB;

class SearchController extends Controller
{
    public function store(SearchMemoryRequest $request, string $project, MemorySearchIndex $searchIndex): JsonResponse
    {
        $projectModel = Project::query()->find($project);

        if ($projectModel === null) {
            throw new ApiException('not_found', 'Project was not found.', 404);
        }

        $attributes = $request->validated();
        $match = $searchIndex->query($attributes['query']);

        if ($match === '') {
            throw new ApiException('validation_error', 'The query must contain searchable terms.', 422);
        }

        $topK = isset($attributes['top_k']) ? (int) $attributes['top_k'] : 10;
        $rows = DB::table('memory_search')
            ->join('memories', 'memories.id', '=', 'memory_search.memory_id')
            ->where('memory_search.project_id', $projectModel->id)
            ->where('memories.status', Memory::STATUS_ACTIVE)
            ->whereRaw('memory_search MATCH ?', [$match])
            ->when(isset($attributes['kinds']), fn ($query) => $query->whereIn('memories.kind', $attributes['kinds']))
            ->select(['memories.*', DB::raw('-bm25(memory_search) as search_score')])
            ->orderByDesc('search_score')
            ->orderByDesc('memories.pinned')
            ->orderByDesc('memories.created_at')
            ->orderByDesc('memories.id')
            ->limit($topK)
            ->get();

        $memories = Memory::hydrate($rows->map(static fn ($row): array => (array) $row)->all());

        return response()->json([
            'data' => MemoryResource::collection($memories)->resolve($request),
        ]);
    }
}
