<?php

namespace App\Http\Requests;

use Illuminate\Validation\Validator;

class UpdateMemoryRequest extends MemoryMutationRequest
{
    public function rules(): array
    {
        return [
            'expected_revision' => ['required', 'integer', 'min:1'],
            'body' => $this->bodyRules(false),
            'pinned' => ['sometimes', 'boolean'],
            'superseded_by' => ['sometimes', 'nullable', 'uuid'],
            'idempotency_key' => $this->idempotencyKeyRules(),
        ];
    }

    public function after(): array
    {
        return [
            ...parent::after(),
            function (Validator $validator): void {
                if (! $this->hasAny(['body', 'pinned', 'superseded_by'])) {
                    $validator->errors()->add('update', 'At least one memory field must be supplied.');
                }
            },
        ];
    }
}
