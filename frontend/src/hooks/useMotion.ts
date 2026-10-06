import { useReducedMotion, useReducedAnimations } from './useReducedMotion';
import type { Variants, Transition } from 'motion/react';

/**
 * Standard animation durations (ms)
 */
export const durations = {
  instant: 0,
  fast: 100,
  normal: 200,
  slow: 300,
  slower: 400,
  slowest: 600,
} as const;

/**
 * Standard easing functions
 */
export const easings = {
  default: [0.4, 0, 0.2, 1] as const,
  spring: [0.34, 1.56, 0.64, 1] as const,
  springGentle: [0.25, 1.2, 0.5, 1] as const,
  springStiff: [0.4, 1.4, 0.6, 1] as const,
  easeOutExpo: [0.16, 1, 0.3, 1] as const,
  easeOutQuart: [0.25, 1, 0.5, 1] as const,
  easeInOut: [0.4, 0, 0.2, 1] as const,
} as const;

/**
 * Transition presets
 */
export const transitions = {
  instant: { duration: 0 },
  fast: { duration: durations.fast / 1000, ease: easings.default },
  normal: { duration: durations.normal / 1000, ease: easings.default },
  slow: { duration: durations.slow / 1000, ease: easings.default },
  slower: { duration: durations.slower / 1000, ease: easings.default },
  spring: { duration: durations.slower / 1000, ease: easings.spring },
  springGentle: { duration: durations.slowest / 1000, ease: easings.springGentle },
  springStiff: { duration: durations.slower / 1000, ease: easings.springStiff },
  easeOutExpo: { duration: durations.slower / 1000, ease: easings.easeOutExpo },
  easeOutQuart: { duration: durations.slowest / 1000, ease: easings.easeOutQuart },
} as const satisfies Record<string, Transition>;

/**
 * Page enter/exit variants for AnimatePresence
 */
export const pageVariants: Variants = {
  enter: {
    opacity: 1,
    y: 0,
    transition: transitions.easeOutExpo,
  },
  exit: {
    opacity: 0,
    y: -16,
    transition: { duration: durations.normal / 1000, ease: easings.default },
  },
  initial: {
    opacity: 0,
    y: 16,
    transition: transitions.easeOutExpo,
  },
};

/**
 * Staggered children container variant
 */
export const staggerContainer: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.06,
      delayChildren: 0.04,
    },
  },
};

/**
 * Fast stagger for dense lists
 */
export const staggerContainerFast: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.03,
      delayChildren: 0.02,
    },
  },
};

/**
 * Medium stagger
 */
export const staggerContainerMed: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.05,
      delayChildren: 0.03,
    },
  },
};

/**
 * 3D stagger with depth entrance
 */
export const staggerContainer3D: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.08,
      delayChildren: 0.05,
    },
  },
};

/**
 * Fade in variants
 */
export const fadeVariants: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: transitions.normal },
  exit: { opacity: 0, transition: transitions.fast },
};

/**
 * Fade in up variants
 */
export const fadeInUpVariants: Variants = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0, transition: transitions.slower },
  exit: { opacity: 0, y: -8, transition: transitions.fast },
};

/**
 * Fade in down variants
 */
export const fadeInDownVariants: Variants = {
  hidden: { opacity: 0, y: -12 },
  visible: { opacity: 1, y: 0, transition: transitions.slower },
  exit: { opacity: 0, y: 8, transition: transitions.fast },
};

/**
 * Slide in up variants
 */
export const slideInUpVariants: Variants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: transitions.easeOutExpo },
  exit: { opacity: 0, y: -16, transition: { duration: durations.normal / 1000, ease: easings.default } },
};

/**
 * Slide in down variants
 */
export const slideInDownVariants: Variants = {
  hidden: { opacity: 0, y: -20 },
  visible: { opacity: 1, y: 0, transition: transitions.easeOutExpo },
  exit: { opacity: 0, y: 16, transition: { duration: durations.normal / 1000, ease: easings.default } },
};

/**
 * Slide in left variants
 */
export const slideInLeftVariants: Variants = {
  hidden: { opacity: 0, x: -20 },
  visible: { opacity: 1, x: 0, transition: transitions.slower },
  exit: { opacity: 0, x: 16, transition: transitions.fast },
};

/**
 * Slide in right variants
 */
export const slideInRightVariants: Variants = {
  hidden: { opacity: 0, x: 20 },
  visible: { opacity: 1, x: 0, transition: transitions.slower },
  exit: { opacity: 0, x: -16, transition: transitions.fast },
};

/**
 * Scale in variants
 */
export const scaleInVariants: Variants = {
  hidden: { opacity: 0, scale: 0.95 },
  visible: { opacity: 1, scale: 1, transition: transitions.slow },
  exit: { opacity: 0, scale: 0.95, transition: transitions.fast },
};

/**
 * Scale in with bounce
 */
export const scaleInBounceVariants: Variants = {
  hidden: { opacity: 0, scale: 0.9 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: { duration: durations.slower / 1000, ease: easings.spring },
  },
  exit: { opacity: 0, scale: 0.95, transition: transitions.fast },
};

/**
 * 3D entrance with depth
 */
export const fadeInUp3DVariants: Variants = {
  hidden: { opacity: 0, y: 20, z: -50, rotateX: 5 },
  visible: { opacity: 1, y: 0, z: 0, rotateX: 0, transition: transitions.easeOutExpo },
  exit: { opacity: 0, y: -12, z: 50, rotateX: -5, transition: { duration: durations.normal / 1000, ease: easings.default } },
};

/**
 * Reveal layer with subtle scale
 */
export const revealLayerVariants: Variants = {
  hidden: { opacity: 0, y: 16, scale: 0.98 },
  visible: { opacity: 1, y: 0, scale: 1, transition: transitions.easeOutQuart },
  exit: { opacity: 0, y: -12, scale: 0.98, transition: transitions.fast },
};

/**
 * Slide fade from depth
 */
export const slideFadeDepthVariants: Variants = {
  hidden: { opacity: 0, y: 24, z: -100, scale: 0.95 },
  visible: { opacity: 1, y: 0, z: 0, scale: 1, transition: transitions.easeOutExpo },
  exit: { opacity: 0, y: -16, z: 50, scale: 0.95, transition: { duration: durations.normal / 1000, ease: easings.default } },
};

/**
 * Hover lift variants
 */
export const hoverLiftVariants = {
  rest: { y: 0, scale: 1, transition: transitions.fast },
  hover: { y: -4, scale: 1.01, transition: transitions.spring },
  tap: { y: 0, scale: 0.98, transition: { duration: 50 / 1000 } },
} as const;

/**
 * Hover glow variants.
 *
 * `--accent-glow` replaced the old `--glow-cyan`. Cyan glows on a violet-led
 * palette are what made the interface read as uniformly blue, and an animated
 * `box-shadow` is a repaint on every frame — so this is a static ring applied
 * on hover only, not a pulse.
 */
export const hoverGlowVariants = {
  rest: { boxShadow: 'var(--shadow-card)' },
  hover: { boxShadow: '0 0 0 1px rgb(var(--accent) / 0.35), var(--shadow-card-hover)' },
} as const;

/**
 * Hover scale variants
 */
export const hoverScaleVariants = {
  rest: { scale: 1, transition: transitions.fast },
  hover: { scale: 1.02, transition: transitions.fast },
  tap: { scale: 0.98, transition: { duration: 50 / 1000 } },
} as const;

/**
 * Focus glow variants
 */
export const focusGlowVariants = {
  rest: { boxShadow: 'none' },
  focus: { boxShadow: 'var(--focus-ring)' },
} as const;

/**
 * Get motion props based on reduced motion preference
 */
export function getMotionProps<T extends Variants>(
  variants: T,
  initial?: string,
  animate?: string,
  exit?: string
): { initial?: string | false; animate?: string | false; exit?: string | false } {
  const reduced = useReducedAnimations();

  if (reduced) {
    return { initial: false, animate: false, exit: false };
  }

  return {
    initial: initial ?? 'hidden',
    animate: animate ?? 'visible',
    exit: exit ?? 'exit',
  };
}

/**
 * Hook for getting motion props with reduced motion awareness
 */
export function useMotionProps<T extends Variants>(
  variants: T,
  initial?: string,
  animate?: string,
  exit?: string
) {
  const reducedAnimations = useReducedAnimations();

  if (reducedAnimations) {
    return { initial: false, animate: false, exit: false, variants };
  }

  return {
    initial: initial ?? 'hidden',
    animate: animate ?? 'visible',
    exit: exit ?? 'exit',
    variants,
  };
}

/**
 * Hook for getting stagger container props with reduced motion
 */
export function useStaggerContainer(
  containerVariants: Variants = staggerContainer,
  itemVariants?: Variants
) {
  const reducedAnimations = useReducedAnimations();

  if (reducedAnimations) {
    return { variants: { visible: { opacity: 1 } }, initial: false, animate: false };
  }

  return {
    variants: containerVariants,
    initial: 'hidden',
    animate: 'visible',
  };
}