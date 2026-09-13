<?php

namespace App\Http\Requests;

class DeleteMemoryRequest extends MemoryMutationRequest
{
    public function rules(): array
    {
        return [
            'expected_revision' => ['required', 'integer', 'min:1'],
            'idempotency_key' => $this->idempotencyKeyRules(),
        ];
    }
}
