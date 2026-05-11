import Image from "next/image";
import vossMark from "@/branding/voss-mark-ignite-2048.png";

type LogoMarkProps = {
  className?: string;
};

export function LogoMark({ className = "h-7 w-7" }: LogoMarkProps) {
  return (
    <Image
      src={vossMark}
      alt=""
      aria-hidden="true"
      className={`shrink-0 object-contain ${className}`}
    />
  );
}
