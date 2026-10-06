// Animation & Motion Hooks
export { useReducedMotion, useReducedAnimations } from './useReducedMotion';
export {
  useMotionProps,
  useStaggerContainer,
  // Variants
  pageVariants,
  staggerContainer,
  staggerContainerFast,
  staggerContainerMed,
  staggerContainer3D,
  fadeVariants,
  fadeInUpVariants,
  fadeInDownVariants,
  slideInUpVariants,
  slideInDownVariants,
  slideInLeftVariants,
  slideInRightVariants,
  scaleInVariants,
  scaleInBounceVariants,
  fadeInUp3DVariants,
  revealLayerVariants,
  slideFadeDepthVariants,
  hoverLiftVariants,
  hoverGlowVariants,
  hoverScaleVariants,
  focusGlowVariants,
  // Constants
  durations,
  easings,
  transitions,
} from './useMotion';

// GSAP Hooks
export {
  useGsapContext,
  useGsapAnimation,
  useGsapEffect,
  useGsapTimeline,
  useScrollTrigger,
  useScrollAnimation,
  gsapUtils,
} from './useGsap';

// Three.js / WebGL Hooks
export {
  useThreeVisibility,
  useWebGLRenderControl,
  useThreeScene,
} from './useThreeVisibility';
export type { UseThreeVisibilityOptions } from './useThreeVisibility';

// Device capability
// `detectLowEndDevice` is intentionally not re-exported: it is a module-private
// helper used only by the hook, which caches its result. Export the hook alone.
export { useWebGLCapability } from './useWebGLCapability';
export type { WebGLCapability } from './useWebGLCapability';