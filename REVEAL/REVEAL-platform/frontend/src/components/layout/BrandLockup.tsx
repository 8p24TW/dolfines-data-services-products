import Image from "next/image";
import Link from "next/link";

export function BrandLockup({
  href = "/dashboard",
  compact = false,
}: {
  href?: string;
  compact?: boolean;
}) {
  return (
    <Link href={href} className="inline-flex items-center gap-3">
      <Image
        src="/brand/logo-white.png"
        alt="8p2 Advisory"
        width={compact ? 112 : 144}
        height={compact ? 34 : 40}
        priority
        className={compact ? "h-auto w-[112px]" : "h-auto w-[144px]"}
      />
      <span className="font-dolfines text-lg font-semibold tracking-[0.14em] text-white">
        REVEAL
      </span>
    </Link>
  );
}
