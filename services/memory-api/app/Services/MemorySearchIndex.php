<?php

namespace App\Services;

use App\Models\Memory;
use Illuminate\Support\Facades\DB;

class MemorySearchIndex
{
    public function replace(Memory $memory): void
    {
        $this->remove($memory->id);

        if ($memory->status !== 'active' || $memory->body === null) {
            return;
        }

        DB::table('memory_search')->insert([
            'memory_id' => $memory->id,
            'project_id' => $memory->project_id,
            'kind' => $memory->kind,
            'body' => $this->indexedBody($memory->body),
        ]);
    }

    public function remove(string $memoryId): void
    {
        DB::table('memory_search')->where('memory_id', $memoryId)->delete();
    }

    public function query(string $query): string
    {
        $normalizedQuery = $this->normalizeSymbols($query);
        preg_match_all('/[\\p{L}\\p{N}]+/u', $normalizedQuery, $matches);

        $terms = array_values(array_unique($matches[0]));

        if ($terms === []) {
            return '';
        }

        return implode(' AND ', array_map(
            static fn (string $term): string => '"'.str_replace('"', '""', $term).'"',
            $terms,
        ));
    }

    private function indexedBody(string $body): string
    {
        return $body."\n".$this->normalizeSymbols($body);
    }

    private function normalizeSymbols(string $value): string
    {
        $withCamelCaseBoundaries = preg_replace('/(?<=[a-z0-9])(?=[A-Z])/u', ' ', $value) ?? $value;

        return preg_replace('/[_\\/\\\\.:-]+/u', ' ', $withCamelCaseBoundaries) ?? $withCamelCaseBoundaries;
    }
}
