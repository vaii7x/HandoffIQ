import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { AgentPalette } from '../../types/agent';

interface ParticleSphereProps {
  palette: AgentPalette;
  size?: number; // Approximate desktop diameter in px
  compact?: boolean;
}

export const ParticleSphere: React.FC<ParticleSphereProps> = ({
  palette,
  size,
  compact = false,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const targetColorPrimaryRef = useRef(new THREE.Color(palette.primary));
  const targetColorSecondaryRef = useRef(new THREE.Color(palette.secondary));
  const currentColorPrimaryRef = useRef(new THREE.Color(palette.primary));
  const currentColorSecondaryRef = useRef(new THREE.Color(palette.secondary));

  // Update target colors when palette changes
  useEffect(() => {
    targetColorPrimaryRef.current.set(palette.primary);
    targetColorSecondaryRef.current.set(palette.secondary);
  }, [palette]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Check prefers-reduced-motion
    const prefersReducedMotion = window.matchMedia(
      '(prefers-reduced-motion: reduce)'
    ).matches;

    // 1. Scene, Camera, Renderer
    const scene = new THREE.Scene();

    const width = container.clientWidth || (compact ? 110 : 460);
    const height = container.clientHeight || (compact ? 110 : 460);

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
    camera.position.z = 6.2;

    const renderer = new THREE.WebGLRenderer({
      alpha: true,
      antialias: true,
      powerPreference: 'high-performance',
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.25;
    container.appendChild(renderer.domElement);

    // 2. Generate procedural circular glow texture for particles
    const createParticleTexture = () => {
      const canvas = document.createElement('canvas');
      canvas.width = 64;
      canvas.height = 64;
      const ctx = canvas.getContext('2d');
      if (ctx) {
        const gradient = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
        gradient.addColorStop(0, 'rgba(255, 255, 255, 1)');
        gradient.addColorStop(0.2, 'rgba(255, 255, 255, 0.85)');
        gradient.addColorStop(0.5, 'rgba(255, 255, 255, 0.35)');
        gradient.addColorStop(1, 'rgba(255, 255, 255, 0)');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, 64, 64);
      }
      return new THREE.CanvasTexture(canvas);
    };

    const particleTexture = createParticleTexture();

    // Group for the entire sphere structure
    const sphereGroup = new THREE.Group();
    scene.add(sphereGroup);

    // Subtle tilt matching the cinematic reference
    sphereGroup.rotation.x = 0.22;
    sphereGroup.rotation.z = -0.15;

    // 3. Dense Spherical Shell Particles (Fibonacci Sphere)
    const particleCount = 4200;
    const sphereRadius = 2.05;
    const positions = new Float32Array(particleCount * 3);
    const originalPositions = new Float32Array(particleCount * 3);
    const colors = new Float32Array(particleCount * 3);
    const sizes = new Float32Array(particleCount);
    const phases = new Float32Array(particleCount);

    const phi = Math.PI * (Math.sqrt(5) - 1); // golden ratio angle

    for (let i = 0; i < particleCount; i++) {
      const y = 1 - (i / (particleCount - 1)) * 2; // y goes from 1 to -1
      const radiusAtY = Math.sqrt(1 - y * y);
      const theta = phi * i;

      // Add gentle radial thickness jitter
      const r = sphereRadius * (0.94 + Math.random() * 0.1);
      const x = Math.cos(theta) * radiusAtY * r;
      const z = Math.sin(theta) * radiusAtY * r;

      positions[i * 3] = x;
      positions[i * 3 + 1] = y * r;
      positions[i * 3 + 2] = z;

      originalPositions[i * 3] = x;
      originalPositions[i * 3 + 1] = y * r;
      originalPositions[i * 3 + 2] = z;

      sizes[i] = Math.random() * 0.055 + 0.025;
      phases[i] = Math.random() * Math.PI * 2;

      // Color variation across surface
      const col = currentColorPrimaryRef.current;
      colors[i * 3] = col.r;
      colors[i * 3 + 1] = col.g;
      colors[i * 3 + 2] = col.b;
    }

    const particleGeometry = new THREE.BufferGeometry();
    particleGeometry.setAttribute(
      'position',
      new THREE.BufferAttribute(positions, 3)
    );
    particleGeometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    const particleMaterial = new THREE.PointsMaterial({
      size: 0.068,
      map: particleTexture,
      transparent: true,
      opacity: 0.92,
      vertexColors: true,
      blending: THREE.NormalBlending,
      depthWrite: false,
    });

    const particles = new THREE.Points(particleGeometry, particleMaterial);
    sphereGroup.add(particles);

    // 4. Intricate Filament Web (Connecting LineSegments)
    // Connecting nearby points to form the organic mesh visible in reference images
    const linePositions: number[] = [];
    const lineColors: number[] = [];
    const maxDistance = 0.26;
    const maxConnectionsPerPoint = 3;

    for (let i = 0; i < 900; i++) {
      let connections = 0;
      const x1 = positions[i * 3];
      const y1 = positions[i * 3 + 1];
      const z1 = positions[i * 3 + 2];

      for (let j = i + 1; j < 900; j++) {
        if (connections >= maxConnectionsPerPoint) break;
        const x2 = positions[j * 3];
        const y2 = positions[j * 3 + 1];
        const z2 = positions[j * 3 + 2];

        const dist = Math.hypot(x2 - x1, y2 - y1, z2 - z1);
        if (dist < maxDistance) {
          linePositions.push(x1, y1, z1, x2, y2, z2);
          const col = currentColorSecondaryRef.current;
          lineColors.push(col.r, col.g, col.b, col.r, col.g, col.b);
          connections++;
        }
      }
    }

    const lineGeometry = new THREE.BufferGeometry();
    lineGeometry.setAttribute(
      'position',
      new THREE.Float32BufferAttribute(linePositions, 3)
    );
    lineGeometry.setAttribute(
      'color',
      new THREE.Float32BufferAttribute(lineColors, 3)
    );

    const lineMaterial = new THREE.LineBasicMaterial({
      transparent: true,
      opacity: 0.35,
      vertexColors: true,
      blending: THREE.NormalBlending,
      depthWrite: false,
    });

    const lineMesh = new THREE.LineSegments(lineGeometry, lineMaterial);
    sphereGroup.add(lineMesh);

    // 5. Diagonal Luminous Swirling Bands / Auroral Ribbons
    // As seen in the reference images, prominent luminous bands wrap diagonally across the sphere
    const ribbonCount = 2200;
    const ribbonPositions = new Float32Array(ribbonCount * 3);
    const ribbonColors = new Float32Array(ribbonCount * 3);

    for (let i = 0; i < ribbonCount; i++) {
      // Helical curve across spherical surface
      const t = (i / ribbonCount) * Math.PI * 2.8 - Math.PI * 1.4;
      const lat = Math.sin(t * 1.2) * 0.85;
      const lon = t * 1.35;

      const r = sphereRadius * (0.98 + (Math.random() - 0.5) * 0.12);
      const cosLat = Math.cos(lat);
      const rx = cosLat * Math.sin(lon) * r;
      const ry = Math.sin(lat) * r;
      const rz = cosLat * Math.cos(lon) * r;

      // Add ribbon scatter
      ribbonPositions[i * 3] = rx + (Math.random() - 0.5) * 0.14;
      ribbonPositions[i * 3 + 1] = ry + (Math.random() - 0.5) * 0.14;
      ribbonPositions[i * 3 + 2] = rz + (Math.random() - 0.5) * 0.14;

      const col = currentColorPrimaryRef.current;
      ribbonColors[i * 3] = col.r;
      ribbonColors[i * 3 + 1] = col.g;
      ribbonColors[i * 3 + 2] = col.b;
    }

    const ribbonGeometry = new THREE.BufferGeometry();
    ribbonGeometry.setAttribute(
      'position',
      new THREE.BufferAttribute(ribbonPositions, 3)
    );
    ribbonGeometry.setAttribute(
      'color',
      new THREE.BufferAttribute(ribbonColors, 3)
    );

    const ribbonMaterial = new THREE.PointsMaterial({
      size: 0.088,
      map: particleTexture,
      transparent: true,
      opacity: 0.95,
      vertexColors: true,
      blending: THREE.NormalBlending,
      depthWrite: false,
    });

    const ribbonPoints = new THREE.Points(ribbonGeometry, ribbonMaterial);
    sphereGroup.add(ribbonPoints);

    // 6. Outer Luminous Fresnel / Zenith Highlight Rim
    const rimCount = 1200;
    const rimPositions = new Float32Array(rimCount * 3);
    const rimColors = new Float32Array(rimCount * 3);

    for (let i = 0; i < rimCount; i++) {
      const angle = (i / rimCount) * Math.PI * 2;
      const r = sphereRadius * (1.02 + Math.random() * 0.05);

      // Distribute mostly near the silhouette perimeter
      const zOffset = (Math.random() - 0.5) * 0.4;
      const x = Math.cos(angle) * r;
      const y = Math.sin(angle) * r;

      rimPositions[i * 3] = x;
      rimPositions[i * 3 + 1] = y;
      rimPositions[i * 3 + 2] = zOffset;

      // Brighter highlight near the zenith top (spotlight collision)
      const isTop = y > 0.8;
      const col = isTop
        ? new THREE.Color(0xffffff)
        : currentColorPrimaryRef.current;

      rimColors[i * 3] = col.r;
      rimColors[i * 3 + 1] = col.g;
      rimColors[i * 3 + 2] = col.b;
    }

    const rimGeometry = new THREE.BufferGeometry();
    rimGeometry.setAttribute(
      'position',
      new THREE.BufferAttribute(rimPositions, 3)
    );
    rimGeometry.setAttribute('color', new THREE.BufferAttribute(rimColors, 3));

    const rimMaterial = new THREE.PointsMaterial({
      size: 0.075,
      map: particleTexture,
      transparent: true,
      opacity: 0.78,
      vertexColors: true,
      blending: THREE.NormalBlending,
      depthWrite: false,
    });

    const rimPoints = new THREE.Points(rimGeometry, rimMaterial);
    scene.add(rimPoints); // Keep rim facing camera

    // 7. Subtle Overhead Spotlight illumination
    const spotlight = new THREE.SpotLight(
      currentColorPrimaryRef.current.getHex(),
      5.0,
      12,
      Math.PI / 4,
      0.8,
      1.5
    );
    spotlight.position.set(0, 5, 2);
    spotlight.target = sphereGroup;
    scene.add(spotlight);

    // 8. Animation Loop
    let animationFrameId: number;
    let clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);

      if (document.hidden) return; // Pause GPU work when hidden

      const elapsedTime = clock.getElapsedTime();

      // Smooth color interpolation towards active agent palette
      currentColorPrimaryRef.current.lerp(targetColorPrimaryRef.current, 0.05);
      currentColorSecondaryRef.current.lerp(
        targetColorSecondaryRef.current,
        0.05
      );

      // Update particle colors buffer
      const currentPrim = currentColorPrimaryRef.current;
      spotlight.color.copy(currentPrim);

      // Slowly rotate the sphere
      if (!prefersReducedMotion) {
        sphereGroup.rotation.y = elapsedTime * 0.16;
        rimPoints.rotation.z = -elapsedTime * 0.04;

        // Subtle micro-undulation for organic feel
        const posAttr = particleGeometry.attributes.position;
        const posArr = posAttr.array as Float32Array;

        for (let i = 0; i < particleCount; i += 3) {
          const phase = phases[i] + elapsedTime * 1.5;
          const factor = 1 + Math.sin(phase) * 0.012;

          posArr[i * 3] = originalPositions[i * 3] * factor;
          posArr[i * 3 + 1] = originalPositions[i * 3 + 1] * factor;
          posArr[i * 3 + 2] = originalPositions[i * 3 + 2] * factor;
        }
        posAttr.needsUpdate = true;
      }

      // Update colors on active particles with pastel palette: lavender, blush pink, powder blue, white
      const colAttr = particleGeometry.attributes.color;
      const colArr = colAttr.array as Float32Array;

      const colorLavender = new THREE.Color('#7664E8');
      const colorBlush = new THREE.Color('#E68FC4');
      const colorBlue = new THREE.Color('#6BA1F5');
      const colorWhite = new THREE.Color('#FFFFFF');

      for (let i = 0; i < particleCount; i++) {
        const yNorm = positions[i * 3 + 1] / sphereRadius;
        let pCol = colorLavender.clone();

        if (yNorm > 0.35) {
          const t = (yNorm - 0.35) / 0.65;
          pCol.copy(colorBlush).lerp(colorWhite, t * 0.45);
        } else if (yNorm < -0.25) {
          const t = (-yNorm - 0.25) / 0.75;
          pCol.copy(colorLavender).lerp(colorBlue, t * 0.8);
        } else {
          const isSparkle = i % 7 === 0;
          pCol = isSparkle ? colorWhite.clone() : colorLavender.clone();
        }

        colArr[i * 3] = pCol.r;
        colArr[i * 3 + 1] = pCol.g;
        colArr[i * 3 + 2] = pCol.b;
      }
      colAttr.needsUpdate = true;

      // Update ribbon colors: luminous diagonal bands blending white and lavender
      const ribColAttr = ribbonGeometry.attributes.color;
      const ribColArr = ribColAttr.array as Float32Array;
      for (let i = 0; i < ribbonCount; i++) {
        const ribT = i / ribbonCount;
        const ribCol = ribT % 0.2 < 0.1 ? colorWhite : colorLavender;
        ribColArr[i * 3] = ribCol.r;
        ribColArr[i * 3 + 1] = ribCol.g;
        ribColArr[i * 3 + 2] = ribCol.b;
      }
      ribColAttr.needsUpdate = true;

      renderer.render(scene, camera);
    };

    animate();

    // Resize handler
    const handleResize = () => {
      if (!container) return;
      const newWidth = container.clientWidth;
      const newHeight = container.clientHeight;
      camera.aspect = newWidth / newHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(newWidth, newHeight);
    };

    window.addEventListener('resize', handleResize);

    // Cleanup on unmount
    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', handleResize);

      if (container && renderer.domElement) {
        container.removeChild(renderer.domElement);
      }

      particleGeometry.dispose();
      particleMaterial.dispose();
      lineGeometry.dispose();
      lineMaterial.dispose();
      ribbonGeometry.dispose();
      ribbonMaterial.dispose();
      rimGeometry.dispose();
      rimMaterial.dispose();
      particleTexture.dispose();
      renderer.dispose();
    };
  }, []);

  const defaultClasses = compact
    ? "relative w-[84px] h-[84px] sm:w-[96px] sm:h-[96px] md:w-[110px] md:h-[110px] mx-auto flex items-center justify-center pointer-events-none"
    : "relative w-[340px] h-[340px] sm:w-[420px] sm:h-[420px] md:w-[460px] md:h-[460px] mx-auto flex items-center justify-center pointer-events-none";

  return (
    <div
      ref={containerRef}
      className={defaultClasses}
      style={{
        filter: compact
          ? 'drop-shadow(0 4px 16px rgba(118, 100, 232, 0.18))'
          : 'drop-shadow(0 10px 30px rgba(118, 100, 232, 0.16))',
        transition: 'filter 0.6s var(--ease-out)',
        ...(size ? { width: `${size}px`, height: `${size}px` } : {}),
      }}
      aria-label={`${palette.id} particle sphere`}
      role="img"
    />
  );
};
