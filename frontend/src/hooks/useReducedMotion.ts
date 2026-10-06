import { useEffect, useState } from 'react';

/**
 * Hook to detect prefers-reduced-motion media query.
 * Returns true if user prefers reduced motion.
 */
export function useReducedMotion(): boolean {
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    // Default to false during SSR/hydration
    if (typeof window === 'undefined') return;

    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setReducedMotion(mediaQuery.matches);

    const handler = (event: MediaQueryListEvent) => {
      setReducedMotion(event.matches);
    };

    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, []);

  return reducedMotion;
}

/**
 * Hook to detect if we should disable complex animations.
 * Returns true for: reduced-motion preference OR low-end device detection.
 */
export function useReducedAnimations(): boolean {
  const reducedMotion = useReducedMotion();
  const [lowEndDevice, setLowEndDevice] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    // Simple heuristic for low-end devices
    const isLowEnd =
      navigator.hardwareConcurrency <= 4 ||
      (navigator as any).deviceMemory !== undefined && (navigator as any).deviceMemory <= 4;

    setLowEndDevice(isLowEnd);
  }, []);

  return reducedMotion || lowEndDevice;
}