<?php

use Illuminate\Database\QueryException;
use Illuminate\Foundation\Application;
use Illuminate\Foundation\Configuration\Exceptions;
use Illuminate\Foundation\Configuration\Middleware;
use Illuminate\Foundation\Http\Middleware\ConvertEmptyStringsToNull;
use Illuminate\Foundation\Http\Middleware\TrimStrings;
use Illuminate\Http\Request;
use Illuminate\Validation\ValidationException;
use Symfony\Component\HttpKernel\Exception\NotFoundHttpException;

return Application::configure(basePath: dirname(__DIR__))
    ->withRouting(
        api: __DIR__.'/../routes/api.php',
        apiPrefix: '',
    )
    ->withMiddleware(function (Middleware $middleware): void {
        $middleware->remove([
            TrimStrings::class,
            ConvertEmptyStringsToNull::class,
        ]);
    })
    ->withExceptions(function (Exceptions $exceptions): void {
        $exceptions->shouldRenderJsonWhen(
            fn (Request $request) => $request->is('v1/*') || $request->expectsJson(),
        );

        $exceptions->render(function (ValidationException $exception, Request $request) {
            if (! $request->is('v1/*')) {
                return null;
            }

            return response()->json([
                'error' => [
                    'code' => 'validation_error',
                    'message' => 'Request validation failed.',
                ],
            ], 422);
        });

        $exceptions->render(function (NotFoundHttpException $exception, Request $request) {
            if (! $request->is('v1/*')) {
                return null;
            }

            return response()->json([
                'error' => [
                    'code' => 'not_found',
                    'message' => 'The requested resource was not found.',
                ],
            ], 404);
        });

        $exceptions->render(function (QueryException $exception, Request $request) {
            if (! $request->is('v1/*')) {
                return null;
            }

            return response()->json([
                'error' => [
                    'code' => 'unavailable',
                    'message' => 'Memory service is unavailable.',
                ],
            ], 503);
        });
    })->create();
