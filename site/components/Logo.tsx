import Image from "next/image";
import vossMark from "@/branding/voss-mark-ignite-2048.png";
import { cn } from "@/lib/utils";

type LogoMarkProps = {
  className?: string;
};

export function LogoMark({ className = "h-7 w-7" }: LogoMarkProps) {
  return (
    <Image
      src={vossMark}
      alt=""
      aria-hidden="true"
      className={cn("shrink-0 object-contain", className)}
    />
  );
}
