import Image from "next/image";

type Props = {
  src: string;
  alt: string;
  width: number;
  height: number;
  priority?: boolean;
  className?: string;
};

export default function ProductScreenshot({
  src,
  alt,
  width,
  height,
  priority = false,
  className = "",
}: Props) {
  return (
    <div
      className={`overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-[0_30px_80px_-30px_rgba(0,0,0,0.7)] ${className}`}
    >
      <Image
        src={src}
        alt={alt}
        width={width}
        height={height}
        priority={priority}
        sizes="(min-width: 1024px) 560px, calc(100vw - 48px)"
        className="h-auto w-full"
      />
    </div>
  );
}
