<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class MutationReceipt extends Model
{
    protected $fillable = [
        'project_id',
        'idempotency_key',
        'operation',
        'request_hash',
        'resource_id',
        'resource_revision',
        'resource_status',
        'response_status',
    ];

    protected function casts(): array
    {
        return [
            'resource_revision' => 'integer',
            'response_status' => 'integer',
        ];
    }

    public function project(): BelongsTo
    {
        return $this->belongsTo(Project::class);
    }
}
