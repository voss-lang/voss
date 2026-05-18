"use client";

import Link from "next/link";
import { forwardRef, type ComponentProps } from "react";
import { captureOutboundClick, type OutboundTarget } from "@/lib/analytics";

type TrackedOutboundLinkProps = ComponentProps<typeof Link> & {
  analyticsTarget: OutboundTarget;
};

const TrackedOutboundLink = forwardRef<HTMLAnchorElement, TrackedOutboundLinkProps>(
  function TrackedOutboundLink({ analyticsTarget, onClick, ...props }, ref) {
    return (
      <Link
        ref={ref}
        target="_blank"
        rel="noreferrer"
        onClick={(event) => {
          captureOutboundClick(analyticsTarget);
          onClick?.(event);
        }}
        {...props}
      />
    );
  },
);

export default TrackedOutboundLink;
