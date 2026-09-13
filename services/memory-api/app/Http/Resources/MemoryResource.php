<?php

namespace App\Http\Resources;

use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

class MemoryResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        $provenance = $this->provenance;

        if (is_array($provenance)) {
            $provenance = (object) $provenance;
        }

        $data = [
            'id' => $this->id,
            'project_id' => $this->project_id,
            'kind' => $this->kind,
            'body' => $this->body,
            'revision' => $this->revision,
            'pinned' => $this->pinned,
            'status' => $this->status,
            'superseded_by' => $this->superseded_by,
            'provenance' => $provenance,
            'created_at' => $this->created_at,
            'updated_at' => $this->updated_at,
        ];

        if (array_key_exists('search_score', $this->resource->getAttributes())) {
            $data['score'] = (float) $this->search_score;
        }

        return $data;
    }
}
