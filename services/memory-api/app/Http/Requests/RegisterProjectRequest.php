<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class RegisterProjectRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'id' => ['required', 'string', 'regex:/\A[A-Za-z0-9_-]{1,64}\z/'],
            'name' => ['sometimes', 'nullable', 'string', 'max:255'],
        ];
    }
}
