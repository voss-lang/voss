<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('mutation_receipts', function (Blueprint $table): void {
            $table->id();
            $table->string('project_id', 64);
            $table->string('idempotency_key', 128);
            $table->string('operation', 32);
            $table->char('request_hash', 64);
            $table->uuid('resource_id')->nullable();
            $table->unsignedInteger('resource_revision')->nullable();
            $table->string('resource_status', 20)->nullable();
            $table->unsignedSmallInteger('response_status');
            $table->timestamps();

            $table->foreign('project_id')->references('id')->on('projects')->cascadeOnDelete();
            $table->unique(['project_id', 'idempotency_key']);
            $table->index(['project_id', 'resource_id']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('mutation_receipts');
    }
};
