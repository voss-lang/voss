"use client";

import posthog from "posthog-js";

export type OutboundTarget = "docs" | "github" | "prd";
export type IntentTarget = "install" | "docs" | "audit" | "github";

const OUTBOUND_INTENTS: Partial<Record<OutboundTarget, IntentTarget>> = {
  docs: "docs",
  github: "github",
};

export function captureIntent(target: IntentTarget) {
  posthog.capture(`${target}_intent`, { target });
}

export function captureOutboundClick(target: OutboundTarget) {
  const intent = OUTBOUND_INTENTS[target];
  if (intent) captureIntent(intent);
  posthog.capture("outbound_click", { target });
}

export function captureCopyInstall(command: string) {
  captureIntent("install");
  posthog.capture("copy_install_command", { command });
}
