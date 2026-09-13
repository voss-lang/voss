<?php

namespace App\Http\Requests;

class CreateMemoryRequest extends MemoryMutationRequest
{
    public function rules(): array
    {
        return [
            'kind' => ['required', 'string', 'in:note,convention,decision'],
            'body' => $this->bodyRules(true),
            'provenance' => ['sometimes', 'nullable', 'array'],
            'idempotency_key' => $this->idempotencyKeyRules(),
        ];
    }
}
