import { type ComponentPropsWithoutRef, type ReactNode } from "react";
import Link from "next/link";
import { ArrowRightIcon } from "@radix-ui/react-icons";
import { cn } from "@/lib/utils";

interface BentoGridProps extends ComponentPropsWithoutRef<"div"> {
  children: ReactNode;
}

interface BentoCardProps extends ComponentPropsWithoutRef<"div"> {
  name: string;
  className?: string;
  background?: ReactNode;
  Icon: React.ElementType;
  description: string;
  href: string;
  cta?: string;
}

export function BentoGrid({ children, className, ...props }: BentoGridProps) {
  return (
    <div
      className={cn(
        "grid w-full auto-rows-[17rem] grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function BentoCard({
  name,
  className,
  background,
  Icon,
  description,
  href,
  cta = "Open module",
  ...props
}: BentoCardProps) {
  return (
    <div
      className={cn(
        "group relative flex flex-col justify-between overflow-hidden rounded-2xl border border-neutral-200/80 bg-white",
        "shadow-[0_0_0_1px_rgba(0,0,0,.02),0_2px_4px_rgba(0,0,0,.03),0_12px_24px_rgba(0,0,0,.04)]",
        className
      )}
      {...props}
    >
      <div className="pointer-events-none absolute inset-0 opacity-60">{background}</div>
      <div className="relative z-10 flex h-full flex-col justify-between p-5">
        <div className="flex transform-gpu flex-col gap-2 transition-all duration-300 lg:group-hover:-translate-y-2">
          <Icon className="h-8 w-8 text-teal-700 transition-all duration-300 group-hover:scale-90" />
          <h3 className="font-display text-lg font-semibold text-neutral-900">{name}</h3>
          <p className="max-w-sm text-[13px] leading-relaxed text-neutral-500">
            {description}
          </p>
        </div>
        <Link
          href={href}
          className="pointer-events-auto mt-4 inline-flex items-center gap-1.5 text-[13px] font-medium text-teal-700 opacity-100 transition lg:translate-y-2 lg:opacity-0 lg:group-hover:translate-y-0 lg:group-hover:opacity-100"
        >
          {cta}
          <ArrowRightIcon className="h-3.5 w-3.5" />
        </Link>
      </div>
      <div className="pointer-events-none absolute inset-0 transition-colors duration-300 group-hover:bg-teal-50/40" />
    </div>
  );
}
