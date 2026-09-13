<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Validator;

class SearchMemoryRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'query' => ['required', 'string'],
            'kinds' => ['sometimes', 'array', 'max:3'],
            'kinds.*' => ['string', 'in:note,convention,decision'],
            'top_k' => ['sometimes', 'integer', 'min:1', 'max:50'],
        ];
    }

    public function after(): array
    {
        return [
            function (Validator $validator): void {
                if (is_string($this->input('query')) && preg_match('/\A\s*\z/u', $this->input('query')) === 1) {
                    $validator->errors()->add('query', 'The query must not be blank.');
                }
            },
        ];
    }
}
