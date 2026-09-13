<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class Memory extends Model
{
    public const STATUS_ACTIVE = 'active';

    public const STATUS_SUPERSEDED = 'superseded';

    public const STATUS_DELETED = 'deleted';

    public const KIND_NOTE = 'note';

    public const KIND_CONVENTION = 'convention';

    public const KIND_DECISION = 'decision';

    public $incrementing = false;

    protected $keyType = 'string';

    protected $fillable = [
        'id',
        'project_id',
        'kind',
        'body',
        'revision',
        'pinned',
        'status',
        'superseded_by',
        'provenance',
    ];

    protected function casts(): array
    {
        return [
            'revision' => 'integer',
            'pinned' => 'boolean',
            'provenance' => 'array',
        ];
    }

    public function project(): BelongsTo
    {
        return $this->belongsTo(Project::class);
    }

    public function scopeActive(Builder $query): Builder
    {
        return $query->where('status', 'active');
    }
}
