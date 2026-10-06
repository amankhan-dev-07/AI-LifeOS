import { useEffect, useState } from 'react';

/**
 * Whether this device can afford the full WebGL "AI Core" experience.
 *
 * The 3D core is a genuine product feature, not decoration, so the default is
 * `true` and we only opt *out* when there is positive evidence the device
 * cannot run it. Two signals, both read-only and both free:
 *
 * - `navigator.deviceMemory` — Chromium reports a capped `navigator.hardwareConcurrency`
 *   / deviceMemory tier. Phones and low-end laptops commonly report 4 GB or less.
 * - A real WebGL context probe — if the browser cannot create a context at all,
 *   the canvas would render nothing regardless.
 *
 * The probe result is cached module-side: it only has to run once per page
 * load, and several components may ask for it. Detection is deliberately
 * conservative — a device reporting 8 GB is never treated as low-end, and an
 * inconclusive result keeps the full experience rather than silently degrading
 * a capable machine.
 *
 * This is a progressive enhancement only. Nothing here gates access to the AI
 * Command view; the chat itself works identically either way.
 */

const LOW_MEMORY_THRESHOLD_GB = 4;
const LOW_CONCURRENCY_THRESHOLD = 4;

let cachedResult: boolean | null = null;

function probeWebGL(): boolean {
  if (typeof document === 'undefined') return true;

  try {
    const canvas = document.createElement('canvas');
    const gl =
      canvas.getContext('webgl2') ??
      canvas.getContext('webgl') ??
      canvas.getContext('experimental-webgl');

    return !!gl;
  } catch {
    // If the probe itself throws we have no evidence of a problem, so keep the
    // full experience rather than degrading on a false negative.
    return true;
  }
}

function detectLowEndDevice(): boolean {
  if (cachedResult !== null) return cachedResult;

  if (typeof navigator === 'undefined') {
    cachedResult = false;
    return cachedResult;
  }

  // No WebGL context at all — the canvas cannot render.
  if (!probeWebGL()) {
    cachedResult = true;
    return cachedResult;
  }

  // `deviceMemory` is Chromium-only and absent elsewhere; absence is not
  // evidence of a low-end device, so we fall through to hardwareConcurrency.
  const memory = (navigator as Navigator & { deviceMemory?: number }).deviceMemory;
  if (typeof memory === 'number' && memory <= LOW_MEMORY_THRESHOLD_GB) {
    cachedResult = true;
    return cachedResult;
  }

  // Only consult core count on mobile-width viewports. A 4-core desktop is a
  // perfectly capable machine; a 4-core phone running this scene is not.
  const cores = navigator.hardwareConcurrency;
  const isHandheld = typeof window !== 'undefined' && window.innerWidth < 768;
  if (isHandheld && typeof cores === 'number' && cores <= LOW_CONCURRENCY_THRESHOLD) {
    cachedResult = true;
    return cachedResult;
  }

  cachedResult = false;
  return cachedResult;
}

export interface WebGLCapability {
  /** False when the device is known to be unable to run the 3D core. */
  canRender3D: boolean;
  /** False until detection has run on the client. */
  detected: boolean;
}

/**
 * Detect low-end WebGL capability once per mount.
 *
 * `detected` starts false so the first client render matches the server/client
 * markup and the fallback is not replaced by a canvas mid-hydration.
 */
export function useWebGLCapability(): WebGLCapability {
  const [canRender3D, setCanRender3D] = useState(false);
  const [detected, setDetected] = useState(false);

  useEffect(() => {
    setCanRender3D(detectLowEndDevice());
    setDetected(true);
  }, []);

  return { canRender3D, detected };
}

export default useWebGLCapability;
