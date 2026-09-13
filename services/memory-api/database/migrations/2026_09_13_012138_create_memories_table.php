<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('memories', function (Blueprint $table): void {
            $table->uuid('id')->primary();
            $table->string('project_id', 64);
            $table->string('kind', 20);
            $table->text('body')->nullable();
            $table->unsignedInteger('revision')->default(1);
            $table->boolean('pinned')->default(false);
            $table->string('status', 20)->default('active');
            $table->uuid('superseded_by')->nullable();
            $table->json('provenance')->nullable();
            $table->timestamps();

            $table->foreign('project_id')->references('id')->on('projects')->cascadeOnDelete();
            $table->index(['project_id', 'status', 'created_at', 'id']);
            $table->index(['project_id', 'kind', 'status', 'created_at', 'id']);
            $table->index(['project_id', 'pinned', 'status', 'created_at', 'id']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('memories');
    }
};
