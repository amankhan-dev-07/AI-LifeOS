import React, { useRef, useMemo, useEffect, useState, useCallback } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { ThreeScene, ThreeSceneFallback, ThreeSceneProps } from './ThreeScene';

/**
 * AI Core States - matches existing AI Command Center states
 */
export type AICoreState = 'idle' | 'thinking' | 'processing' | 'responding' | 'success' | 'error';

export interface AICore3DProps extends Omit<ThreeSceneProps, 'children'> {
  /** Current AI state driving visual behavior */
  state: AICoreState;
  /** Size of the core container */
  size?: number;
  /** Enable pointer interaction (parallax/rotation) */
  enablePointerInteraction?: boolean;
  /** Override quality settings for this instance */
  qualityOverride?: Partial<{
    particleCount: number;
    enableRings: boolean;
    enableOuterField: boolean;
    enableParticles: boolean;
  }>;
}

/**
 * Ring configuration for energy rings
 */
interface RingConfig {
  radius: number;
  rotationSpeed: { x: number; y: number; z: number };
  color: THREE.ColorRepresentation;
  opacity: number;
  segments: number;
}

/**
 * Particle configuration for orbiting particles
 */
interface ParticleConfig {
  count: number;
  radius: number;
  speed: number;
  size: number;
  color: THREE.ColorRepresentation;
}

/**
 * State-driven visual configuration
 */
const STATE_CONFIG: Record<AICoreState, {
  coreIntensity: number;
  coreScale: number;
  corePulseSpeed: number;
  ringSpeeds: number[];
  ringOpacities: number[];
  outerFieldIntensity: number;
  outerFieldPulseSpeed: number;
  particleActivity: number;
  particleSpeed: number;
  colorShift: { r: number; g: number; b: number };
}> = {
  idle: {
    coreIntensity: 0.4,
    coreScale: 1.0,
    corePulseSpeed: 0.5,
    ringSpeeds: [0.02, -0.015, 0.01],
    ringOpacities: [0.15, 0.1, 0.08],
    outerFieldIntensity: 0.15,
    outerFieldPulseSpeed: 0.3,
    particleActivity: 0.3,
    particleSpeed: 0.5,
    colorShift: { r: 0.0, g: 0.7, b: 1.0 }, // Cyan
  },
  thinking: {
    coreIntensity: 0.7,
    coreScale: 1.05,
    corePulseSpeed: 1.2,
    ringSpeeds: [0.05, -0.04, 0.03],
    ringOpacities: [0.3, 0.2, 0.15],
    outerFieldIntensity: 0.3,
    outerFieldPulseSpeed: 0.8,
    particleActivity: 0.6,
    particleSpeed: 1.2,
    colorShift: { r: 0.2, g: 0.5, b: 1.0 }, // Blue-cyan
  },
  processing: {
    coreIntensity: 0.9,
    coreScale: 1.1,
    corePulseSpeed: 2.0,
    ringSpeeds: [0.08, -0.06, 0.05],
    ringOpacities: [0.4, 0.3, 0.2],
    outerFieldIntensity: 0.5,
    outerFieldPulseSpeed: 1.5,
    particleActivity: 0.9,
    particleSpeed: 2.0,
    colorShift: { r: 0.5, g: 0.3, b: 1.0 }, // Violet
  },
  responding: {
    coreIntensity: 0.8,
    coreScale: 1.08,
    corePulseSpeed: 1.5,
    ringSpeeds: [0.06, -0.04, 0.04],
    ringOpacities: [0.35, 0.25, 0.18],
    outerFieldIntensity: 0.4,
    outerFieldPulseSpeed: 1.0,
    particleActivity: 0.7,
    particleSpeed: 1.5,
    colorShift: { r: 0.3, g: 0.8, b: 1.0 }, // Bright cyan
  },
  success: {
    coreIntensity: 0.6,
    coreScale: 1.02,
    corePulseSpeed: 1.0,
    ringSpeeds: [0.03, -0.02, 0.015],
    ringOpacities: [0.25, 0.18, 0.12],
    outerFieldIntensity: 0.35,
    outerFieldPulseSpeed: 0.6,
    particleActivity: 0.5,
    particleSpeed: 0.8,
    colorShift: { r: 0.2, g: 1.0, b: 0.4 }, // Emerald
  },
  error: {
    coreIntensity: 0.8,
    coreScale: 1.0,
    corePulseSpeed: 3.0,
    ringSpeeds: [0.1, -0.08, 0.06],
    ringOpacities: [0.4, 0.3, 0.2],
    outerFieldIntensity: 0.6,
    outerFieldPulseSpeed: 2.5,
    particleActivity: 0.8,
    particleSpeed: 2.5,
    colorShift: { r: 1.0, g: 0.3, b: 0.3 }, // Rose/Red
  },
};

// Default ring configurations
const DEFAULT_RINGS: RingConfig[] = [
  {
    radius: 1.3,
    rotationSpeed: { x: 0, y: 0.02, z: 0.01 },
    color: 0x06b6d4,
    opacity: 0.15,
    segments: 64,
  },
  {
    radius: 1.6,
    rotationSpeed: { x: 0.01, y: -0.015, z: 0 },
    color: 0x8b5cf6,
    opacity: 0.1,
    segments: 64,
  },
  {
    radius: 1.9,
    rotationSpeed: { x: -0.01, y: 0, z: 0.01 },
    color: 0x22d3ee,
    opacity: 0.08,
    segments: 64,
  },
];

// Default particle configuration
const DEFAULT_PARTICLES: ParticleConfig = {
  count: 30,
  radius: 2.2,
  speed: 0.5,
  size: 0.02,
  color: 0x06b6d4,
};

/**
 * Generate particle positions on a sphere
 */
function generateParticlePositions(count: number, radius: number): THREE.Vector3[] {
  const positions: THREE.Vector3[] = [];
  for (let i = 0; i < count; i++) {
    const phi = Math.acos(2 * Math.random() - 1);
    const theta = 2 * Math.PI * Math.random();
    const r = radius * (0.8 + 0.2 * Math.random());
    positions.push(
      new THREE.Vector3(
        r * Math.sin(phi) * Math.cos(theta),
        r * Math.sin(phi) * Math.sin(theta),
        r * Math.cos(phi)
      )
    );
  }
  return positions;
}

/**
 * Core sphere mesh - lightweight emissive sphere
 */
function CoreSphere({
  intensity,
  scale,
  pulseSpeed,
  colorShift,
}: {
  intensity: number;
  scale: number;
  pulseSpeed: number;
  colorShift: { r: number; g: number; b: number };
}) {
  const meshRef = useRef<THREE.Mesh>(null);
  const materialRef = useRef<THREE.MeshBasicMaterial>(null);
  const timeRef = useRef(0);
  const baseScale = useRef(scale);

  useFrame((_, delta) => {
    timeRef.current += delta * pulseSpeed;
    const pulse = Math.sin(timeRef.current * 2) * 0.02 * intensity;
    const currentScale = baseScale.current + pulse;
    if (meshRef.current) {
      meshRef.current.scale.setScalar(currentScale);
    }
    // Animate opacity for pulse effect (since MeshBasicMaterial has no emissive)
    if (materialRef.current) {
      const pulseOpacity = 0.7 + 0.3 * Math.sin(timeRef.current * 3);
      materialRef.current.opacity = 0.9 * pulseOpacity * intensity;
    }
  });

  const geometry = useMemo(() => new THREE.SphereGeometry(0.6, 32, 32), []);
  const material = useMemo(() => {
    const mat = new THREE.MeshBasicMaterial({
      color: new THREE.Color().setRGB(colorShift.r, colorShift.g, colorShift.b),
      transparent: true,
      opacity: 0.9,
      depthWrite: false,
    });
    materialRef.current = mat;
    return mat;
  }, [colorShift]);

  const innerGlowMaterial = useMemo(() => new THREE.MeshBasicMaterial({
    color: new THREE.Color().setRGB(colorShift.r, colorShift.g, colorShift.b),
    transparent: true,
    opacity: 0.3,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  }), [colorShift]);

  return (
    <mesh ref={meshRef} geometry={geometry} material={material} scale={scale}>
      {/* Inner glow layer */}
      <mesh
        geometry={geometry}
        material={innerGlowMaterial}
        scale={1.05}
      />
    </mesh>
  );
}

/**
 * Energy ring mesh
 */
function EnergyRing({
  config,
  speedMultiplier,
  opacity,
}: {
  config: RingConfig;
  speedMultiplier: number;
  opacity: number;
}) {
  const ringRef = useRef<THREE.Mesh>(null);
  const timeRef = useRef(0);

  useFrame((_, delta) => {
    timeRef.current += delta;
    if (ringRef.current) {
      ringRef.current.rotation.x += config.rotationSpeed.x * speedMultiplier * delta * 60;
      ringRef.current.rotation.y += config.rotationSpeed.y * speedMultiplier * delta * 60;
      ringRef.current.rotation.z += config.rotationSpeed.z * speedMultiplier * delta * 60;
    }
  });

  const geometry = useMemo(
    () => new THREE.RingGeometry(config.radius * 0.95, config.radius, config.segments),
    [config.radius, config.segments]
  );

  const material = useMemo(
    () => new THREE.MeshBasicMaterial({
      color: config.color,
      transparent: true,
      opacity: opacity * config.opacity,
      side: THREE.DoubleSide,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    }),
    [config.color, config.opacity, opacity]
  );

  return <mesh ref={ringRef} geometry={geometry} material={material} />;
}

/**
 * Outer energy field - soft transparent shell
 */
function OuterField({
  intensity,
  pulseSpeed,
  colorShift,
}: {
  intensity: number;
  pulseSpeed: number;
  colorShift: { r: number; g: number; b: number };
}) {
  const meshRef = useRef<THREE.Mesh>(null);
  const materialRef = useRef<THREE.MeshBasicMaterial>(null);
  const timeRef = useRef(0);
  const baseScale = useRef(2.5);

  useFrame((_, delta) => {
    timeRef.current += delta * pulseSpeed;
    const pulse = Math.sin(timeRef.current) * 0.05 * intensity;
    if (meshRef.current) {
      meshRef.current.scale.setScalar(baseScale.current + pulse);
    }
    if (materialRef.current) {
      materialRef.current.opacity = intensity * (0.05 + 0.03 * Math.sin(timeRef.current * 2));
    }
  });

  const geometry = useMemo(() => new THREE.SphereGeometry(2.5, 16, 16), []);
  const material = useMemo(() => {
    const mat = new THREE.MeshBasicMaterial({
      color: new THREE.Color().setRGB(colorShift.r, colorShift.g, colorShift.b),
      transparent: true,
      opacity: intensity * 0.08,
      side: THREE.BackSide,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });
    materialRef.current = mat;
    return mat;
  }, [colorShift, intensity]);

  return <mesh ref={meshRef} geometry={geometry} material={material} />;
}

/**
 * Orbiting particles
 */
function OrbitParticles({
  config,
  activity,
  speedMultiplier,
  colorShift,
}: {
  config: ParticleConfig;
  activity: number;
  speedMultiplier: number;
  colorShift: { r: number; g: number; b: number };
}) {
  const pointsRef = useRef<THREE.Points>(null);
  const positionsRef = useRef<Float32Array | null>(null);
  const initialPositionsRef = useRef<THREE.Vector3[]>([]);
  const timeRef = useRef(0);

  // Initialize particle positions
  useEffect(() => {
    const positions = generateParticlePositions(config.count, config.radius);
    initialPositionsRef.current = positions;
    const posArray = new Float32Array(config.count * 3);
    positions.forEach((p, i) => {
      posArray[i * 3] = p.x;
      posArray[i * 3 + 1] = p.y;
      posArray[i * 3 + 2] = p.z;
    });
    positionsRef.current = posArray;
  }, [config.count, config.radius]);

  useFrame((_, delta) => {
    timeRef.current += delta * speedMultiplier;
    if (!pointsRef.current || !positionsRef.current) return;

    const positions = positionsRef.current;
    const initialPositions = initialPositionsRef.current;
    const count = config.count;

    for (let i = 0; i < count; i++) {
      const initial = initialPositions[i];
      const t = timeRef.current * config.speed * speedMultiplier;
      // Orbital movement around Y axis with slight variation
      const angle = t + i * 0.5;
      const radius = config.radius * (0.9 + 0.1 * Math.sin(t * 0.5 + i));
      const yOffset = Math.sin(t * 0.7 + i) * 0.3 * activity;

      positions[i * 3] = radius * Math.cos(angle) * (initial.x / config.radius);
      positions[i * 3 + 1] = initial.y + yOffset * activity;
      positions[i * 3 + 2] = radius * Math.sin(angle) * (initial.z / config.radius);
    }

    pointsRef.current.geometry.attributes.position.needsUpdate = true;
    // Vary particle opacity based on activity
    if (pointsRef.current.material instanceof THREE.PointsMaterial) {
      pointsRef.current.material.opacity = 0.3 + 0.4 * activity;
      pointsRef.current.material.size = config.size * (0.8 + 0.4 * activity);
    }
  });

  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry();
    const posArray = new Float32Array(config.count * 3);
    initialPositionsRef.current.forEach((p, i) => {
      posArray[i * 3] = p.x;
      posArray[i * 3 + 1] = p.y;
      posArray[i * 3 + 2] = p.z;
    });
    geo.setAttribute('position', new THREE.BufferAttribute(posArray, 3));
    return geo;
  }, [config.count]);

  const material = useMemo(() => new THREE.PointsMaterial({
    color: new THREE.Color().setRGB(colorShift.r, colorShift.g, colorShift.b),
    size: config.size,
    transparent: true,
    opacity: 0.3,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    sizeAttenuation: true,
  }), [config.size, colorShift]);

  return <points ref={pointsRef} geometry={geometry} material={material} />;
}

/**
 * Pointer interaction controller - subtle camera/core rotation toward cursor
 */
function PointerInteraction({
  enabled,
  reducedMotion,
  isMobile,
}: {
  enabled: boolean;
  reducedMotion: boolean;
  isMobile: boolean;
}) {
  const { camera } = useThree();
  const targetRef = useRef({ x: 0, y: 0 });
  const currentRef = useRef({ x: 0, y: 0 });

  const handlePointerMove = useCallback((event: React.PointerEvent) => {
    if (!enabled || reducedMotion || isMobile) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    const y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    targetRef.current = { x: x * 0.15, y: y * 0.15 }; // Very subtle
  }, [enabled, reducedMotion, isMobile]);

  useFrame(() => {
    if (!enabled || reducedMotion || isMobile) return;
    // Smooth interpolation
    currentRef.current.x += (targetRef.current.x - currentRef.current.x) * 0.02;
    currentRef.current.y += (targetRef.current.y - currentRef.current.y) * 0.02;
    // Apply subtle camera rotation
    camera.rotation.y = currentRef.current.x;
    camera.rotation.x = currentRef.current.y;
  });

  return <div onPointerMove={handlePointerMove} style={{ width: '100%', height: '100%' }} />;
}

/**
 * Inner scene - the actual 3D content rendered inside ThreeScene
 */
function AICoreInner({
  state,
  qualityOverride,
  enablePointerInteraction,
}: {
  state: AICoreState;
  qualityOverride?: AICore3DProps['qualityOverride'];
  enablePointerInteraction: boolean;
}) {
  const { gl } = useThree();
  const isMobile = (gl?.domElement?.width ?? 0) < 768;
  const reducedMotion = false; // Will be handled by ThreeScene wrapper
  const config = STATE_CONFIG[state];
  const rings = qualityOverride?.enableRings !== false ? DEFAULT_RINGS : [];
  const particleConfig = qualityOverride?.enableParticles !== false ? DEFAULT_PARTICLES : { ...DEFAULT_PARTICLES, count: 0 };
  const particleCount = qualityOverride?.particleCount ?? particleConfig.count;

  // Adjust for mobile/low-end
  const effectiveParticleCount = isMobile ? Math.min(particleCount, 15) : particleCount;
  const effectiveRings = isMobile ? rings.slice(0, 2) : rings;

  return (
    <group>
      {/* Outer energy field */}
      {qualityOverride?.enableOuterField !== false && (
        <OuterField
          intensity={config.outerFieldIntensity}
          pulseSpeed={config.outerFieldPulseSpeed}
          colorShift={config.colorShift}
        />
      )}

      {/* Energy rings */}
      {effectiveRings.map((ring, i) => (
        <EnergyRing
          key={i}
          config={ring}
          speedMultiplier={config.ringSpeeds[i] / DEFAULT_RINGS[i].rotationSpeed.y}
          opacity={config.ringOpacities[i]}
        />
      ))}

      {/* Core sphere */}
      <CoreSphere
        intensity={config.coreIntensity}
        scale={config.coreScale}
        pulseSpeed={config.corePulseSpeed}
        colorShift={config.colorShift}
      />

      {/* Orbiting particles */}
      {effectiveParticleCount > 0 && (
        <OrbitParticles
          config={{ ...particleConfig, count: effectiveParticleCount }}
          activity={config.particleActivity}
          speedMultiplier={config.particleSpeed}
          colorShift={config.colorShift}
        />
      )}

      {/* Pointer interaction handler */}
      <PointerInteraction
        enabled={enablePointerInteraction}
        reducedMotion={reducedMotion}
        isMobile={isMobile}
      />

      {/* Ambient light for material visibility */}
      <ambientLight intensity={0.5} />
      {/* Subtle key light */}
      <directionalLight position={[2, 3, 2]} intensity={0.3} color={0x06b6d4} />
    </group>
  );
}

/**
 * Main AICore3D component - wraps everything in ThreeScene
 */
export function AICore3D({
  state,
  size = 112, // 28 * 4 = 112px default (matches md:w-28 md:h-28)
  enablePointerInteraction = true,
  qualityOverride,
  className = '',
  style,
  fallback,
  onReady,
  onError,
  ...threeSceneProps
}: AICore3DProps) {
  // Determine quality settings based on device
  const isMobile = typeof window !== 'undefined' && window.innerWidth < 768;
  const isLowEnd = typeof window !== 'undefined' &&
    (navigator.hardwareConcurrency <= 4 || (navigator as any).deviceMemory <= 4);

  const effectiveQuality = useMemo(() => ({
    particleCount: isLowEnd ? 10 : isMobile ? 15 : (qualityOverride?.particleCount ?? 30),
    enableRings: qualityOverride?.enableRings !== false && !isLowEnd,
    enableOuterField: qualityOverride?.enableOuterField !== false,
    enableParticles: qualityOverride?.enableParticles !== false && !isLowEnd,
  }), [isMobile, isLowEnd, qualityOverride]);

  return (
    <ThreeScene
      className={className}
      style={{ width: size, height: size, ...style }}
      dpr={1}
      antialias={!isLowEnd}
      shadows={false}
      maxFPS={isLowEnd ? 30 : 60}
      pauseWhenHidden={true}
      onceVisible={true}
      fallback={fallback || <ThreeSceneFallback />}
      onReady={onReady}
      onError={onError}
      cameraPosition={[0, 0, 5]}
      fov={40}
      background="transparent"
      {...threeSceneProps}
    >
      <AICoreInner
        state={state}
        qualityOverride={effectiveQuality}
        enablePointerInteraction={enablePointerInteraction && !isMobile}
      />
    </ThreeScene>
  );
}

export default AICore3D;