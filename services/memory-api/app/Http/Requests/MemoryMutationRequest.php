<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Validator;

class MemoryMutationRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    protected function prepareForValidation(): void
    {
        $idempotencyKey = $this->header('Idempotency-Key');

        $this->merge(['idempotency_key' => is_string($idempotencyKey) ? $idempotencyKey : null]);
    }

    public function idempotencyKey(): string
    {
        return $this->string('idempotency_key')->toString();
    }

    protected function idempotencyKeyRules(): array
    {
        return [
            'required',
            'string',
            'regex:/\A[\x21-\x7e]{1,128}\z/',
        ];
    }

    protected function bodyRules(bool $required): array
    {
        return $required ? ['required', 'string'] : ['sometimes', 'string'];
    }

    public function after(): array
    {
        return [
            function (Validator $validator): void {
                if ($this->exists('body') && is_string($this->input('body'))) {
                    $body = $this->input('body');

                    if (preg_match('/\A\s*\z/u', $body) === 1) {
                        $validator->errors()->add('body', 'The body must not be blank.');
                    }

                    if (mb_strlen($body, '8bit') > 65536) {
                        $validator->errors()->add('body', 'The body may not be larger than 65536 bytes.');
                    }
                }

                if ($this->exists('provenance') && is_array($this->input('provenance'))) {
                    $payload = json_decode($this->getContent());
                    $provenanceIsJsonObject = is_object($payload) && property_exists($payload, 'provenance') && is_object($payload->provenance);

                    if (! $provenanceIsJsonObject && ($this->input('provenance') !== [] || $this->getContent() !== '')) {
                        $validator->errors()->add('provenance', 'The provenance must be an object.');
                    }
                }
            },
        ];
    }
}
