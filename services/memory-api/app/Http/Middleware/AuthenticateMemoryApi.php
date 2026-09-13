<?php

namespace App\Http\Middleware;

use App\Exceptions\ApiException;
use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

class AuthenticateMemoryApi
{
    public function handle(Request $request, Closure $next): Response
    {
        $configuredToken = config('voss_memory.api_token');
        $providedToken = $request->bearerToken();

        if (! is_string($configuredToken) || trim($configuredToken) === '' || ! is_string($providedToken) || ! hash_equals($configuredToken, $providedToken)) {
            throw new ApiException('unauthorized', 'A valid bearer token is required.', 401);
        }

        return $next($request);
    }
}
