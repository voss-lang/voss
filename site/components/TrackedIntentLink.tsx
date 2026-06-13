"use client";

import Link from "next/link";
import { forwardRef, type ComponentProps } from "react";
import { captureIntent, type IntentTarget } from "@/lib/analytics";

type TrackedIntentLinkProps = ComponentProps<typeof Link> & {
  analyticsTarget: IntentTarget;
};

const TrackedIntentLink = forwardRef<HTMLAnchorElement, TrackedIntentLinkProps>(
  function TrackedIntentLink({ analyticsTarget, onClick, ...props }, ref) {
    return (
      <Link
        ref={ref}
        onClick={(event) => {
          captureIntent(analyticsTarget);
          onClick?.(event);
        }}
        {...props}
      />
    );
  },
);

export default TrackedIntentLink;
