import React from 'react';

/**
 * Fallback component shown while Three.js is loading or when reduced motion is
 * enabled.
 *
 * This lives in its own module on purpose. It used to sit inside
 * `ThreeScene.tsx`, which also imports `@react-three/fiber` — so importing the
 * fallback from there dragged the whole Three.js runtime into the importing
 * chunk. `AICommandView` uses this as its `React.Suspense` fallback while the
 * real 3D core code-splits in, so it must stay importable without Three.js.
 *
 * Only `React` is imported here. Do not add a Three.js import to this file.
 */
export function ThreeSceneFallback({
  children,
  className = '',
  style,
}: {
  children?: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}) {
  return (
    <div
      className={`relative w-full h-full ${className}`}
      style={style}
      aria-hidden="true"
    >
      {children || (
        <div className="absolute inset-0 flex items-center justify-center">
          {/* Static, not animated. This fallback is shown *permanently* on every
              low-end device (`useWebGLCapability` returns false), so anything
              looping here was a permanent background animation for exactly the
              machines least able to afford one. The single `animate-spin` arc
              is a cheap compositor-only rotation and reads as "loading". */}
          <div className="w-16 h-16 rounded-2xl bg-[rgb(var(--accent)/0.1)] border border-[rgb(var(--accent)/0.28)] flex items-center justify-center">
            <div className="w-6 h-6 rounded-full border-2 border-[rgb(var(--accent))] border-t-transparent animate-spin" />
          </div>
        </div>
      )}
    </div>
  );
}

export default ThreeSceneFallback;
