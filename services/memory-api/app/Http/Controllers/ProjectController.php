<?php

namespace App\Http\Controllers;

use App\Http\Requests\RegisterProjectRequest;
use App\Http\Resources\ProjectResource;
use App\Models\Project;
use Illuminate\Http\JsonResponse;

class ProjectController extends Controller
{
    public function store(RegisterProjectRequest $request): JsonResponse
    {
        $attributes = $request->validated();
        $project = Project::query()->firstOrNew(['id' => $attributes['id']]);

        if (array_key_exists('name', $attributes)) {
            $project->name = $attributes['name'];
        }

        $project->save();

        return (new ProjectResource($project))->response()->setStatusCode(200);
    }
}
