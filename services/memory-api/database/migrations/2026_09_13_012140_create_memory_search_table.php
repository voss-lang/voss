<?php

use Illuminate\Database\Migrations\Migration;

return new class extends Migration
{
    public function up(): void
    {
        DB::statement("CREATE VIRTUAL TABLE memory_search USING fts5(memory_id UNINDEXED, project_id UNINDEXED, kind UNINDEXED, body, tokenize='unicode61 remove_diacritics 2')");
    }

    public function down(): void
    {
        DB::statement('DROP TABLE IF EXISTS memory_search');
    }
};
