"use client";

import React, { type ComponentPropsWithoutRef, type CSSProperties } from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";

type BaseProps = {
  shimmerColor?: string;
  shimmerSize?: string;
  borderRadius?: string;
  shimmerDuration?: string;
  background?: string;
  className?: string;
  children?: React.ReactNode;
};

type ButtonProps = BaseProps &
  Omit<ComponentPropsWithoutRef<"button">, keyof BaseProps> & {
    href?: undefined;
  };

type LinkProps = BaseProps & {
  href: string;
  disabled?: boolean;
};

export type ShimmerButtonProps = ButtonProps | LinkProps;

function shimmerStyle(props: BaseProps): CSSProperties {
  return {
    "--spread": "90deg",
    "--shimmer-color": props.shimmerColor ?? "#ffffff",
    "--radius": props.borderRadius ?? "10px",
    "--speed": props.shimmerDuration ?? "3s",
    "--cut": props.shimmerSize ?? "0.05em",
    "--bg": props.background ?? "#0b1220",
  } as CSSProperties;
}

const shimmerClass = (className?: string) =>
  cn(
    "group relative z-0 inline-flex cursor-pointer items-center justify-center overflow-hidden whitespace-nowrap border border-white/10 px-5 py-2.5 text-[13px] font-medium text-white [background:var(--bg)] [border-radius:var(--radius)]",
    "transform-gpu transition-transform duration-300 ease-in-out active:translate-y-px",
    "disabled:cursor-wait disabled:opacity-70",
    className
  );

function ShimmerLayers({ children }: { children: React.ReactNode }) {
  return (
    <>
      <div className="absolute inset-0 -z-30 overflow-visible blur-[2px]">
        <div className="animate-shimmer-slide absolute inset-0 aspect-square h-full rounded-none">
          <div className="animate-spin-around absolute -inset-full w-auto rotate-0 [background:conic-gradient(from_calc(270deg-(var(--spread)*0.5)),transparent_0,var(--shimmer-color)_var(--spread),transparent_var(--spread))]" />
        </div>
      </div>
      <span className="relative z-10">{children}</span>
      <div
        className={cn(
          "absolute inset-0 size-full rounded-xl shadow-[inset_0_-8px_10px_#ffffff1f]",
          "transform-gpu transition-all duration-300 ease-in-out",
          "group-hover:shadow-[inset_0_-6px_10px_#ffffff3f]",
          "group-active:shadow-[inset_0_-10px_10px_#ffffff3f]"
        )}
      />
      <div
        className="absolute -z-20 [background:var(--bg)] [border-radius:var(--radius)]"
        style={{ inset: "var(--cut)" }}
      />
    </>
  );
}

export const ShimmerButton = React.forwardRef<
  HTMLButtonElement | HTMLAnchorElement,
  ShimmerButtonProps
>(function ShimmerButton(props, ref) {
  if ("href" in props && props.href) {
    const {
      href,
      className,
      children,
      shimmerColor,
      shimmerSize,
      borderRadius,
      shimmerDuration,
      background,
      ...rest
    } = props;
    return (
      <Link
        href={href}
        ref={ref as React.Ref<HTMLAnchorElement>}
        style={shimmerStyle({
          shimmerColor,
          shimmerSize,
          borderRadius,
          shimmerDuration,
          background,
        })}
        className={shimmerClass(className)}
        {...rest}
      >
        <ShimmerLayers>{children}</ShimmerLayers>
      </Link>
    );
  }

  const {
    className,
    children,
    shimmerColor,
    shimmerSize,
    borderRadius,
    shimmerDuration,
    background,
    ...rest
  } = props;

  return (
    <button
      ref={ref as React.Ref<HTMLButtonElement>}
      style={shimmerStyle({
        shimmerColor,
        shimmerSize,
        borderRadius,
        shimmerDuration,
        background,
      })}
      className={shimmerClass(className)}
      {...rest}
    >
      <ShimmerLayers>{children}</ShimmerLayers>
    </button>
  );
});
