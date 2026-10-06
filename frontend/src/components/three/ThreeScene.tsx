import React, { Suspense, useRef, useEffect, useMemo } from 'react';
import { Canvas, useThree } from '@react-three/fiber';
import { useThreeScene } from '../../hooks/useThreeVisibility';
import { useReducedMotion } from '../../hooks/useReducedMotion';
import { ThreeSceneFallback } from './ThreeSceneFallback';

/**
 * Re-exported so existing importers of `./three` keep resolving it.
 *
 * The implementation now lives in `ThreeSceneFallback.tsx`, which imports no
 * Three.js. That separation is what allows a consumer to render the fallback
 * without pulling the 3D runtime into its own chunk.
 */
export { ThreeSceneFallback };

/**
 * Inner component that actually renders the Three.js Canvas.
 */
interface ThreeSceneInnerProps {
  children: React.ReactNode;
  cameraPosition?: [number, number, number];
  fov?: number;
  shadows?: boolean;
  dpr?: number;
  antialias?: boolean;
  background?: string | number;
  shouldRender?: boolean;
  onReady?: () => void;
  onError?: (error: Error) => void;
}

function ThreeSceneInner({
  children,
  cameraPosition = [0, 0, 5],
  fov = 50,
  shadows = false,
  dpr = 1,
  antialias = true,
  background = 'transparent',
  shouldRender = true,
  onReady,
  onError,
}: ThreeSceneInnerProps) {
  const readyFired = useRef(false);

  const { gl } = useThree();

  useEffect(() => {
    if (gl && !readyFired.current) {
      readyFired.current = true;
      onReady?.();
    }
  }, [gl, onReady]);

  // Configure renderer
  const canvasProps = useMemo(
    () => ({
      camera: { position: cameraPosition, fov },
      gl: { antialias, preserveDrawingBuffer: false, alpha: background === 'transparent' },
      shadows,
      dpr: Math.min(dpr, window.devicePixelRatio), // Cap at dpr prop
      // Stop the render loop entirely while the scene is scrolled out of view
      // or motion is reduced. Previously this only fed R3F's internal DPR
      // scaling (`performance.min/max`), which is not a frame-rate control —
      // the canvas kept rendering at full rate regardless, so an off-screen
      // 3D scene still burned a core. This is the switch that actually gates it.
      frameloop: shouldRender ? ('always' as const) : ('never' as const),
    }),
    [cameraPosition, fov, shadows, dpr, antialias, background, shouldRender]
  );

  return (
    <Canvas
      {...canvasProps}
      onCreated={({ gl: renderer }) => {
        // Configure renderer for performance
        renderer.setPixelRatio(Math.min(dpr, window.devicePixelRatio));
        (renderer as any).physicallyCorrectLights = false;
        (renderer as any).toneMapping = 0; // No tone mapping for performance
      }}
      style={{ width: '100%', height: '100%', display: 'block' }}
    >
      <color attach="background" args={[background]} />
      {children}
    </Canvas>
  );
}

ThreeSceneInner.displayName = 'ThreeSceneInner';

/**
 * Main ThreeScene wrapper component.
 * Handles lazy loading, visibility detection, and reduced motion fallback.
 */
export interface ThreeSceneProps {
  /** Content to render inside the Canvas */
  children: React.ReactNode;
  /** Fallback content while loading or when 3D is disabled */
  fallback?: React.ReactNode;
  /** Container className */
  className?: string;
  /** Container style */
  style?: React.CSSProperties;
  /** Camera position */
  cameraPosition?: [number, number, number];
  /** Field of view */
  fov?: number;
  /** Whether to pause when not visible */
  pauseWhenHidden?: boolean;
  /** Maximum FPS */
  maxFPS?: number;
  /** Once visible, stay visible */
  onceVisible?: boolean;
  /** Enable shadows (performance cost) */
  shadows?: boolean;
  /** DPR cap (default 1 for performance) */
  dpr?: number;
  /** Antialiasing */
  antialias?: boolean;
  /** Background color */
  background?: string | number;
  /** Callback when scene is ready */
  onReady?: () => void;
  /** Callback on error */
  onError?: (error: Error) => void;
}

export function ThreeScene({
  children,
  fallback,
  className = '',
  style,
  cameraPosition = [0, 0, 5],
  fov = 50,
  pauseWhenHidden = true,
  maxFPS = 30,
  onceVisible = true,
  shadows = false,
  dpr = 1,
  antialias = true,
  background = 'transparent',
  onReady,
  onError,
}: ThreeSceneProps) {
  const reducedMotion = useReducedMotion();
  const containerRef = useRef<HTMLDivElement>(null);

  const scene = useThreeScene({
    threshold: 0.1,
    rootMargin: '100px',
    once: onceVisible,
    minVisibleTime: 1000,
    pauseWhenHidden,
    maxFPS,
  });

  // Force visibility on user interaction
  const handleInteraction = () => {
    scene.forceVisible();
  };

  // If reduced motion or not yet visible, show fallback
  if (reducedMotion || !scene.hasBeenVisible) {
    return (
      <div
        ref={containerRef}
        className={`relative w-full h-full ${className}`}
        style={style}
        onMouseEnter={handleInteraction}
        onFocus={handleInteraction}
        onClick={handleInteraction}
        tabIndex={0}
        role="img"
        aria-label="3D scene (reduced motion mode)"
      >
        {fallback || <ThreeSceneFallback />}
      </div>
    );
  }

  // Scene is visible and user allows motion - render the 3D scene
  return (
    <div
      ref={containerRef}
      className={`relative w-full h-full ${className}`}
      style={style}
      onMouseEnter={handleInteraction}
      onFocus={handleInteraction}
      onClick={handleInteraction}
      tabIndex={0}
      role="img"
      aria-label="Interactive 3D scene"
    >
      <Suspense fallback={fallback || <ThreeSceneFallback />}>
        <ThreeSceneInner
          cameraPosition={cameraPosition}
          fov={fov}
          shadows={shadows}
          dpr={dpr}
          antialias={antialias}
          background={background}
          shouldRender={scene.shouldRender}
          onReady={onReady}
          onError={onError}
        >
          {children}
        </ThreeSceneInner>
      </Suspense>
    </div>
  );
}

export default ThreeScene;