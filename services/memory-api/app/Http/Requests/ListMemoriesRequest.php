<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Validator;

class ListMemoriesRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    protected function prepareForValidation(): void
    {
        if ($this->has('pinned') && is_string($this->input('pinned'))) {
            $pinned = strtolower($this->input('pinned'));

            if ($pinned === 'true' || $pinned === 'false') {
                $this->merge(['pinned' => $pinned === 'true']);
            }
        }
    }

    public function rules(): array
    {
        return [
            'kind' => ['sometimes', 'string', 'in:note,convention,decision'],
            'pinned' => ['sometimes', 'boolean'],
            'limit' => ['sometimes', 'integer', 'min:1', 'max:100'],
            'cursor' => ['sometimes', 'string'],
        ];
    }

    public function after(): array
    {
        return [
            function (Validator $validator): void {
                if ($this->filled('cursor') && $this->cursorOffset() === null) {
                    $validator->errors()->add('cursor', 'The cursor is invalid.');
                }
            },
        ];
    }

    public function cursorOffset(): ?int
    {
        if (! $this->filled('cursor')) {
            return 0;
        }

        $cursor = $this->input('cursor');

        if (! is_string($cursor)) {
            return null;
        }

        if (! is_string($cursor)) {
            return null;
        }

        $decoded = base64_decode(strtr($cursor, '-_', '+/'), true);

        if ($decoded === false || ! preg_match('/\A(?:0|[1-9][0-9]*)\z/', $decoded)) {
            return null;
        }

        return (int) $decoded;
    }
}
