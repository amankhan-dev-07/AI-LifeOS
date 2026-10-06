import { useEffect, useRef, useState } from 'react';
import { gsap } from 'gsap';

/** GSAP Context type */
type GSAPContext = ReturnType<typeof gsap.context>;

/**
 * Safe GSAP context hook for React components.
 * Provides automatic cleanup on unmount.
 *
 * Usage:
 * const ctx = useGsapContext();
 *
 * useEffect(() => {
 *   ctx.current?.(() => {
 *     gsap.to(element, { x: 100 });
 *   });
 * }, []);
 *
 * // Cleanup automatic via context
 */
export function useGsapContext(): { current: GSAPContext | null } {
  const contextRef = useRef<GSAPContext | null>(null);

  useEffect(() => {
    // Create new context on mount
    contextRef.current = gsap.context(() => {});

    return () => {
      // Revert all animations in this context on unmount
      if (contextRef.current) {
        contextRef.current.revert();
        contextRef.current = null;
      }
    };
  }, []);

  return contextRef;
}

/**
 * Create a GSAP animation within a context.
 * Returns a cleanup function.
 */
export function useGsapAnimation(
  callback: (ctx: GSAPContext) => void,
  deps: React.DependencyList = []
): () => void {
  const contextRef = useRef<GSAPContext | null>(null);
  const cleanupRef = useRef<() => void>(() => {});

  useEffect(() => {
    // Revert previous animation if any
    if (contextRef.current) {
      contextRef.current.revert();
    }

    // Create new context and run animation
    contextRef.current = gsap.context(callback);

    // Return cleanup function
    cleanupRef.current = () => {
      if (contextRef.current) {
        contextRef.current.revert();
        contextRef.current = null;
      }
    };

    return cleanupRef.current;
  }, deps);

  return cleanupRef.current;
}

/** GSAP instance type */
type GSAPInstance = typeof gsap;

/**
 * Hook for running GSAP animations on mount with proper cleanup.
 *
 * Usage:
 * useGsapEffect(() => {
 *   const tl = gsap.timeline();
 *   tl.from(element, { opacity: 0, y: 20 })
 *     .to(otherElement, { opacity: 1 });
 *   return () => tl.kill();
 * }, []);
 */
export function useGsapEffect(
  effect: (gsap: GSAPInstance) => (() => void) | void,
  deps: React.DependencyList = []
): void {
  const contextRef = useRef<GSAPContext | null>(null);

  useEffect(() => {
    // Revert previous context
    if (contextRef.current) {
      contextRef.current.revert();
    }

    // Create new context with the effect
    contextRef.current = gsap.context(() => {
      const cleanup = effect(gsap);
      if (cleanup) {
        // Store cleanup if needed
      }
    });

    return () => {
      if (contextRef.current) {
        contextRef.current.revert();
        contextRef.current = null;
      }
    };
  }, deps);
}

/**
 * Hook for creating a GSAP timeline with automatic cleanup.
 */
export function useGsapTimeline(
  deps: React.DependencyList = []
): { timeline: gsap.core.Timeline | null; context: GSAPContext | null } {
  const timelineRef = useRef<gsap.core.Timeline | null>(null);
  const contextRef = useRef<GSAPContext | null>(null);

  useEffect(() => {
    contextRef.current = gsap.context(() => {
      timelineRef.current = gsap.timeline({ paused: true });
    });

    return () => {
      if (timelineRef.current) {
        timelineRef.current.kill();
        timelineRef.current = null;
      }
      if (contextRef.current) {
        contextRef.current.revert();
        contextRef.current = null;
      }
    };
  }, deps);

  return { timeline: timelineRef.current, context: contextRef.current };
}

/**
 * Hook for ScrollTrigger integration (when needed).
 * Registers ScrollTrigger plugin and provides cleanup.
 */
export function useScrollTrigger(): { ScrollTrigger: any } {
  const [ScrollTrigger, setScrollTrigger] = useState<any | null>(null);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    import('gsap/ScrollTrigger').then(({ ScrollTrigger: ST }) => {
      gsap.registerPlugin(ST);
      setScrollTrigger(ST);
    });

    return () => {
      if (ScrollTrigger) {
        ScrollTrigger.getAll().forEach((st: any) => st.kill());
      }
    };
  }, []);

  return { ScrollTrigger };
}

/**
 * Hook for creating a ScrollTrigger animation with cleanup.
 */
export function useScrollAnimation(
  trigger: Element | string | null,
  animation: (trigger: Element) => gsap.core.Timeline | gsap.core.Tween,
  deps: React.DependencyList = []
): void {
  const { ScrollTrigger } = useScrollTrigger();
  const contextRef = useRef<GSAPContext | null>(null);

  useEffect(() => {
    if (!ScrollTrigger || !trigger) return;

    contextRef.current = gsap.context(() => {
      const element = typeof trigger === 'string' ? document.querySelector(trigger) : trigger;
      if (element) {
        animation(element as Element);
      }
    });

    return () => {
      if (contextRef.current) {
        contextRef.current.revert();
        contextRef.current = null;
      }
    };
  }, [ScrollTrigger, trigger, ...deps]);
}

/**
 * Safe GSAP utility functions for common patterns.
 * These don't use hooks - call them inside useGsapContext or useGsapEffect.
 */

export const gsapUtils = {
  /**
   * Fade in element
   */
  fadeIn: (element: Element | string, duration = 0.4, delay = 0) =>
    gsap.fromTo(
      element,
      { opacity: 0 },
      { opacity: 1, duration, delay, ease: 'power2.out' }
    ),

  /**
   * Fade out element
   */
  fadeOut: (element: Element | string, duration = 0.3) =>
    gsap.to(element, { opacity: 0, duration, ease: 'power2.in' }),

  /**
   * Slide in from bottom
   */
  slideInUp: (element: Element | string, duration = 0.5, delay = 0, distance = 30) =>
    gsap.fromTo(
      element,
      { opacity: 0, y: distance },
      { opacity: 1, y: 0, duration, delay, ease: 'power3.out' }
    ),

  /**
   * Slide in from top
   */
  slideInDown: (element: Element | string, duration = 0.5, delay = 0, distance = 30) =>
    gsap.fromTo(
      element,
      { opacity: 0, y: -distance },
      { opacity: 1, y: 0, duration, delay, ease: 'power3.out' }
    ),

  /**
   * Scale in
   */
  scaleIn: (element: Element | string, duration = 0.3, delay = 0, fromScale = 0.9) =>
    gsap.fromTo(
      element,
      { opacity: 0, scale: fromScale },
      { opacity: 1, scale: 1, duration, delay, ease: 'back.out(1.7)' }
    ),

  /**
   * Staggered children animation
   */
  staggerIn: (
    elements: Element | Element[] | string,
    duration = 0.4,
    stagger = 0.06,
    from = { opacity: 0, y: 20 }
  ) =>
    gsap.fromTo(
      elements,
      from,
      {
        opacity: 1,
        y: 0,
        duration,
        stagger,
        ease: 'power3.out',
      }
    ),

  /**
   * Create a master timeline for complex sequences
   */
  createSequence: () => gsap.timeline({ defaults: { ease: 'power2.out' } }),

  /**
   * Kill all animations on an element
   */
  kill: (element: Element | string) => gsap.killTweensOf(element),

  /**
   * Get current animated values
   */
  getProperty: (element: Element | string, property: string) => gsap.getProperty(element, property),

  /**
   * Set properties instantly
   */
  set: (element: Element | string, properties: Record<string, any>) => gsap.set(element, properties),
};