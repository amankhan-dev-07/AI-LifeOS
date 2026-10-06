import React from 'react';

/**
 * Performance utilities for the advanced visual architecture.
 * Target hardware: Intel 5th-gen i7, 8GB RAM, integrated GPU
 */

// ============================================
// DEVICE CAPABILITY DETECTION
// ============================================

export interface DeviceCapabilities {
  hardwareConcurrency: number;
  deviceMemory: number | null;
  isLowEnd: boolean;
  isMobile: boolean;
  prefersReducedMotion: boolean;
  supportsWebGL2: boolean;
  maxTextureSize: number | null;
}

/**
 * Detect device capabilities for adaptive rendering.
 * Call once at app startup and cache the result.
 */
export function detectDeviceCapabilities(): DeviceCapabilities {
  if (typeof window === 'undefined') {
    return {
      hardwareConcurrency: 4,
      deviceMemory: 4,
      isLowEnd: true,
      isMobile: false,
      prefersReducedMotion: false,
      supportsWebGL2: false,
      maxTextureSize: null,
    };
  }

  const hardwareConcurrency = navigator.hardwareConcurrency || 4;
  const deviceMemory = (navigator as any).deviceMemory || 4;
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // WebGL2 support detection
  let supportsWebGL2 = false;
  let maxTextureSize: number | null = null;
  try {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl2');
    if (gl) {
      supportsWebGL2 = true;
      maxTextureSize = gl.getParameter(gl.MAX_TEXTURE_SIZE);
    }
  } catch {}

  // Low-end heuristic
  const isLowEnd =
    hardwareConcurrency <= 4 ||
    deviceMemory <= 4 ||
    !supportsWebGL2;

  // Mobile detection
  const isMobile = /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
    (navigator.maxTouchPoints && navigator.maxTouchPoints > 2);

  return {
    hardwareConcurrency,
    deviceMemory,
    isLowEnd,
    isMobile,
    prefersReducedMotion,
    supportsWebGL2,
    maxTextureSize,
  };
}

/**
 * Cached device capabilities (initialized on first call).
 */
let cachedCapabilities: DeviceCapabilities | null = null;

export function getDeviceCapabilities(): DeviceCapabilities {
  if (!cachedCapabilities) {
    cachedCapabilities = detectDeviceCapabilities();
  }
  return cachedCapabilities;
}

// ============================================
// ADAPTIVE QUALITY SETTINGS
// ============================================

export interface QualitySettings {
  // 3D settings
  enable3D: boolean;
  dpr: number;
  antialias: boolean;
  shadows: boolean;
  maxFPS: number;
  particleCount: number;
  geometryComplexity: 'low' | 'medium' | 'high';

  // Animation settings
  enableMotionAnimations: boolean;
  enableGsapAnimations: boolean;
  staggerDelay: number;
  transitionDuration: number;

  // Scroll settings
  enableSmoothScroll: boolean;

  // Effects settings
  enableAmbientParticles: boolean;
  enableMeshGradients: boolean;
  enableBackdropBlur: boolean;
}

/**
 * Get quality settings based on device capabilities and user preferences.
 */
export function getQualitySettings(overrides: Partial<QualitySettings> = {}): QualitySettings {
  const caps = getDeviceCapabilities();
  const prefersReduced = caps.prefersReducedMotion;

  // Base settings for high-end
  const highEnd: QualitySettings = {
    enable3D: true,
    dpr: 1.5,
    antialias: true,
    shadows: true,
    maxFPS: 60,
    particleCount: 100,
    geometryComplexity: 'high',
    enableMotionAnimations: true,
    enableGsapAnimations: true,
    staggerDelay: 60,
    transitionDuration: 300,
    enableSmoothScroll: true,
    enableAmbientParticles: true,
    enableMeshGradients: true,
    enableBackdropBlur: true,
  };

  // Low-end settings
  const lowEnd: QualitySettings = {
    enable3D: true,
    dpr: 1,
    antialias: false,
    shadows: false,
    maxFPS: 30,
    particleCount: 20,
    geometryComplexity: 'low',
    enableMotionAnimations: true,
    enableGsapAnimations: true,
    staggerDelay: 30,
    transitionDuration: 150,
    enableSmoothScroll: false,
    enableAmbientParticles: false,
    enableMeshGradients: false,
    enableBackdropBlur: false,
  };

  // Reduced motion settings (overrides everything)
  const reducedMotion: QualitySettings = {
    enable3D: false,
    dpr: 1,
    antialias: false,
    shadows: false,
    maxFPS: 0,
    particleCount: 0,
    geometryComplexity: 'low',
    enableMotionAnimations: false,
    enableGsapAnimations: false,
    staggerDelay: 0,
    transitionDuration: 0,
    enableSmoothScroll: false,
    enableAmbientParticles: false,
    enableMeshGradients: false,
    enableBackdropBlur: false,
  };

  // Mobile settings
  const mobile: QualitySettings = {
    enable3D: true,
    dpr: 1,
    antialias: false,
    shadows: false,
    maxFPS: 30,
    particleCount: 30,
    geometryComplexity: 'low',
    enableMotionAnimations: true,
    enableGsapAnimations: true,
    staggerDelay: 40,
    transitionDuration: 200,
    enableSmoothScroll: false,
    enableAmbientParticles: true,
    enableMeshGradients: false,
    enableBackdropBlur: false,
  };

  let settings: QualitySettings;

  if (prefersReduced) {
    settings = reducedMotion;
  } else if (caps.isMobile) {
    settings = mobile;
  } else if (caps.isLowEnd) {
    settings = lowEnd;
  } else {
    settings = highEnd;
  }

  // Apply overrides
  return { ...settings, ...overrides };
}

// ============================================
// FRAME BUDGET UTILITIES
// ============================================

/**
 * Frame budget for 60fps = 16.67ms
 * For 30fps = 33.33ms
 */
export const FRAME_BUDGET = {
  fps60: 16.67,
  fps30: 33.33,
  fps20: 50,
} as const;

/**
 * Check if we're within frame budget.
 * Use in requestAnimationFrame loops to skip expensive work.
 */
export function isWithinFrameBudget(startTime: number, targetFPS = 60): boolean {
  const budget = targetFPS === 60 ? FRAME_BUDGET.fps60 : targetFPS === 30 ? FRAME_BUDGET.fps30 : FRAME_BUDGET.fps20;
  return performance.now() - startTime < budget * 0.8; // 80% budget for safety
}

/**
 * Create a frame budget checker for a target FPS.
 */
export function createFrameBudgetChecker(targetFPS = 60) {
  const budget = targetFPS === 60 ? FRAME_BUDGET.fps60 : targetFPS === 30 ? FRAME_BUDGET.fps30 : FRAME_BUDGET.fps20;
  return (startTime: number) => performance.now() - startTime < budget * 0.8;
}

// ============================================
// LAZY LOADING UTILITIES
// ============================================

/**
 * Preload a module (for code splitting).
 * Call during idle time or on user interaction hints.
 */
export function preloadModule(importFn: () => Promise<any>): void {
  if (typeof window === 'undefined') return;

  // Use requestIdleCallback if available, otherwise setTimeout
  const schedule = (window as any).requestIdleCallback || ((cb: () => void) => setTimeout(cb, 1));

  schedule(() => {
    try {
      importFn();
    } catch {}
  });
}

/**
 * Create a lazy component with preload support.
 */
export function createLazyComponent<T extends React.ComponentType<any>>(
  importFn: () => Promise<{ default: T }>,
  preload = false
): React.LazyExoticComponent<T> {
  const LazyComponent = React.lazy(importFn);

  if (preload && typeof window !== 'undefined') {
    preloadModule(importFn);
  }

  return LazyComponent;
}