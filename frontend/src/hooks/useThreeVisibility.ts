import { useEffect, useState, useRef, useCallback } from 'react';
import { useReducedMotion } from './useReducedMotion';

export interface UseThreeVisibilityOptions {
  /** Threshold for intersection (0-1) */
  threshold?: number;
  /** Root margin for intersection observer */
  rootMargin?: string;
  /** Once visible, stay visible (don't pause when scrolling away) */
  once?: boolean;
  /** Minimum time (ms) to stay visible before allowing pause */
  minVisibleTime?: number;
}

/**
 * Hook to detect if a 3D component is visible on screen.
 * Uses Intersection Observer for performance.
 *
 * Returns:
 * - isVisible: boolean - whether the component is currently visible
 * - ref: React.RefObject<HTMLDivElement> - attach to the container element
 * - forceVisible: () => void - programmatically force visibility (e.g., on user interaction)
 */
export function useThreeVisibility(options: UseThreeVisibilityOptions = {}) {
  const {
    threshold = 0.1,
    rootMargin = '100px',
    once = false,
    minVisibleTime = 1000,
  } = options;

  const [isVisible, setIsVisible] = useState(false);
  const [hasBeenVisible, setHasBeenVisible] = useState(false);
  const elementRef = useRef<HTMLDivElement>(null);
  const observerRef = useRef<IntersectionObserver | null>(null);
  const visibleStartTimeRef = useRef<number | null>(null);
  const forcedVisibleRef = useRef(false);

  const forceVisible = useCallback(() => {
    forcedVisibleRef.current = true;
    setIsVisible(true);
    setHasBeenVisible(true);
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined' || !elementRef.current) return;

    const element = elementRef.current;

    // Clean up previous observer
    if (observerRef.current) {
      observerRef.current.disconnect();
    }

    // Create new observer
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const isIntersecting = entry.isIntersecting;

          if (isIntersecting) {
            if (!hasBeenVisible) {
              visibleStartTimeRef.current = Date.now();
              setHasBeenVisible(true);
            }
            setIsVisible(true);
            forcedVisibleRef.current = true;
          } else {
            // Only hide if not forced visible and min visible time has passed
            if (!forcedVisibleRef.current) {
              const visibleTime = visibleStartTimeRef.current
                ? Date.now() - visibleStartTimeRef.current
                : 0;

              if (visibleTime >= minVisibleTime) {
                setIsVisible(false);
              }
            } else if (once && hasBeenVisible) {
              // If 'once' is true and we've been visible, stay visible
              setIsVisible(true);
            }
          }
        });
      },
      {
        threshold,
        rootMargin,
      }
    );

    observer.observe(element);
    observerRef.current = observer;

    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect();
        observerRef.current = null;
      }
    };
  }, [threshold, rootMargin, once, minVisibleTime, hasBeenVisible]);

  return {
    isVisible: isVisible || forcedVisibleRef.current,
    hasBeenVisible,
    ref: elementRef,
    forceVisible,
  };
}

/**
 * Hook to manage WebGL rendering state based on visibility and performance.
 */
export function useWebGLRenderControl(
  isVisible: boolean,
  reducedMotion: boolean,
  options: {
    /** Pause rendering when not visible */
    pauseWhenHidden?: boolean;
    /** Minimum frame interval (ms) - use 0 for no limit */
    minFrameInterval?: number;
    /** Maximum frame rate (FPS) - use 0 for no limit */
    maxFPS?: number;
  } = {}
) {
  const {
    pauseWhenHidden = true,
    minFrameInterval = 0,
    maxFPS = 60,
  } = options;

  const [shouldRender, setShouldRender] = useState(true);
  const [currentFPS, setCurrentFPS] = useState(60);
  const frameCountRef = useRef(0);
  const lastTimeRef = useRef(performance.now());
  const animationFrameRef = useRef<number | null>(null);

  useEffect(() => {
    // Determine if we should render.
    // The original expression was `(pauseWhenHidden ? true : true)` — the same
    // value either way, so the flag did nothing and the canvas kept its
    // default `frameloop="always"` even when scrolled out of view. Honour it.
    const render = isVisible && (!pauseWhenHidden ? true : !reducedMotion);
    setShouldRender(render);
  }, [isVisible, reducedMotion, pauseWhenHidden]);

  // FPS monitoring
  useEffect(() => {
    if (!shouldRender) return;

    const measureFPS = (now: number) => {
      frameCountRef.current++;
      const elapsed = now - lastTimeRef.current;

      if (elapsed >= 1000) {
        setCurrentFPS(frameCountRef.current);
        frameCountRef.current = 0;
        lastTimeRef.current = now;
      }

      animationFrameRef.current = requestAnimationFrame(measureFPS);
    };

    animationFrameRef.current = requestAnimationFrame(measureFPS);

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [shouldRender]);

  // Auto-pause if FPS drops too low
  useEffect(() => {
    if (maxFPS > 0 && currentFPS < maxFPS * 0.5) {
      // Could implement adaptive quality here
    }
  }, [currentFPS, maxFPS]);

  return {
    shouldRender,
    currentFPS,
    isPerformant: currentFPS >= (maxFPS * 0.75),
  };
}

/**
 * Combined hook for 3D component visibility and render control.
 */
export function useThreeScene(
  options: UseThreeVisibilityOptions & {
    pauseWhenHidden?: boolean;
    maxFPS?: number;
  } = {}
) {
  const reducedMotion = useReducedMotion();
  const visibility = useThreeVisibility(options);
  const renderControl = useWebGLRenderControl(visibility.isVisible, reducedMotion, {
    pauseWhenHidden: options.pauseWhenHidden,
    maxFPS: options.maxFPS,
  });

  return {
    ...visibility,
    ...renderControl,
    reducedMotion,
  };
}