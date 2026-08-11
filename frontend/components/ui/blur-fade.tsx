"use client";

import { useRef } from "react";
import {
  AnimatePresence,
  motion,
  useInView,
  type MotionProps,
  type UseInViewOptions,
  type Variants,
} from "motion/react";

type MarginType = UseInViewOptions["margin"];

interface BlurFadeProps extends MotionProps {
  children: React.ReactNode;
  className?: string;
  duration?: number;
  delay?: number;
  offset?: number;
  direction?: "up" | "down" | "left" | "right";
  inView?: boolean;
  inViewMargin?: MarginType;
  blur?: string;
}

export function BlurFade({
  children,
  className,
  duration = 0.4,
  delay = 0,
  offset = 8,
  direction = "up",
  inView = false,
  inViewMargin = "-40px",
  blur = "6px",
  ...props
}: BlurFadeProps) {
  const ref = useRef(null);
  const inViewResult = useInView(ref, { once: true, margin: inViewMargin });
  const isInView = !inView || inViewResult;

  const defaultVariants: Variants = {
    hidden: {
      [direction === "left" || direction === "right" ? "x" : "y"]:
        direction === "right" || direction === "down" ? -offset : offset,
      opacity: 0,
      filter: `blur(${blur})`,
    },
    visible: {
      [direction === "left" || direction === "right" ? "x" : "y"]: 0,
      opacity: 1,
      filter: "blur(0px)",
    },
  };

  return (
    <AnimatePresence>
      <motion.div
        ref={ref}
        initial="hidden"
        animate={isInView ? "visible" : "hidden"}
        exit="hidden"
        variants={defaultVariants}
        transition={{
          delay: 0.04 + delay,
          duration,
          ease: "easeOut",
          filter: { duration },
        }}
        className={className}
        {...props}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}
