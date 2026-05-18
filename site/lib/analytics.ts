"use client";

import posthog from "posthog-js";

export type OutboundTarget = "docs" | "github" | "prd";

export function captureOutboundClick(target: OutboundTarget) {
  posthog.capture("outbound_click", { target });
}

export function captureCopyInstall(command: string) {
  posthog.capture("copy_install_command", { command });
}
