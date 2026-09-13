<?php

use App\Http\Controllers\MemoryController;
use App\Http\Controllers\ProjectController;
use App\Http\Controllers\SearchController;
use App\Http\Middleware\AuthenticateMemoryApi;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Route;

Route::prefix('v1')->group(function (): void {
    Route::get('/health', static function () {
        try {
            DB::select('select 1');
            $hasSearchTable = DB::table('sqlite_master')->where('type', 'table')->where('name', 'memory_search')->exists();

            if (! $hasSearchTable) {
                return response()->json([
                    'error' => [
                        'code' => 'unavailable',
                        'message' => 'Memory service is unavailable.',
                    ],
                ], 503);
            }
        } catch (Throwable) {
            return response()->json([
                'error' => [
                    'code' => 'unavailable',
                    'message' => 'Memory service is unavailable.',
                ],
            ], 503);
        }

        return response()->json([
            'api_version' => 1,
            'status' => 'ready',
        ]);
    });

    Route::middleware(AuthenticateMemoryApi::class)->group(function (): void {
        Route::post('/projects', [ProjectController::class, 'store']);

        Route::get('/projects/{project}/memories', [MemoryController::class, 'index'])
            ->where('project', '[A-Za-z0-9_-]{1,64}');
        Route::post('/projects/{project}/memories', [MemoryController::class, 'store'])
            ->where('project', '[A-Za-z0-9_-]{1,64}');
        Route::get('/projects/{project}/memories/{memory}', [MemoryController::class, 'show'])
            ->where('project', '[A-Za-z0-9_-]{1,64}');
        Route::patch('/projects/{project}/memories/{memory}', [MemoryController::class, 'update'])
            ->where('project', '[A-Za-z0-9_-]{1,64}');
        Route::delete('/projects/{project}/memories/{memory}', [MemoryController::class, 'destroy'])
            ->where('project', '[A-Za-z0-9_-]{1,64}');
        Route::post('/projects/{project}/search', [SearchController::class, 'store'])
            ->where('project', '[A-Za-z0-9_-]{1,64}');

        Route::any('/{any}', static fn () => response()->json([
            'error' => [
                'code' => 'not_found',
                'message' => 'The requested resource was not found.',
            ],
        ], 404))->where('any', '.*');
    });
});

Route::fallback(static function (Request $request) {
    abort(404);
});
