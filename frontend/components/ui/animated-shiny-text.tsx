import { type ComponentPropsWithoutRef, type CSSProperties, type FC } from "react";
import { cn } from "@/lib/utils";

export interface AnimatedShinyTextProps extends ComponentPropsWithoutRef<"span"> {
  shimmerWidth?: number;
}

export const AnimatedShinyText: FC<AnimatedShinyTextProps> = ({
  children,
  className,
  shimmerWidth = 100,
  ...props
}) => {
  return (
    <span
      style={
        {
          "--shiny-width": `${shimmerWidth}px`,
        } as CSSProperties
      }
      className={cn(
        "inline-flex animate-shiny-text bg-clip-text text-transparent",
        "bg-[linear-gradient(110deg,transparent,45%,rgba(15,23,42,0.75),55%,transparent)]",
        "bg-[length:var(--shiny-width)_100%] bg-no-repeat",
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
};
