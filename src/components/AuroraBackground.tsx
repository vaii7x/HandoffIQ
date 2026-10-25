import React, { useMemo } from 'react';
import { ScreenId } from '../types/agent';

interface AuroraBackgroundProps {
  stage?: ScreenId;
  milestone?: string | null;
}

const PASTEL_MOTES = [
  { id: 1, x: 12, y: 28, size: 3.5, color: '#C7B7FF', duration: 7, delay: 0 },
  { id: 2, x: 22, y: 64, size: 2.5, color: '#F5C7EB', duration: 9, delay: 1.5 },
  { id: 3, x: 84, y: 32, size: 3, color: '#B9DDFB', duration: 8, delay: 0.8 },
  { id: 4, x: 76, y: 72, size: 2.5, color: '#DDD5FF', duration: 11, delay: 2 },
  { id: 5, x: 48, y: 18, size: 2, color: '#C7B7FF', duration: 10, delay: 3 },
  { id: 6, x: 52, y: 82, size: 3, color: '#F5C7EB', duration: 8.5, delay: 1 },
  { id: 7, x: 92, y: 55, size: 2, color: '#B9DDFB', duration: 12, delay: 2.5 },
  { id: 8, x: 8, y: 48, size: 2.5, color: '#DDD5FF', duration: 9.5, delay: 0.5 },
];

export const AuroraBackground: React.FC<AuroraBackgroundProps> = ({
  stage: _stage,
  milestone,
}) => {
  const motes = useMemo(() => PASTEL_MOTES, []);

  return (
    <div
      className="absolute inset-0 pointer-events-none overflow-hidden z-0 select-none bg-[#FAF9FC]"
      aria-hidden="true"
    >
      {/* 1. Base Atmospheric Ambient Glows */}
      {/* Central Radiance behind the Particle Sphere */}
      <div
        className="absolute top-[42%] left-1/2 -translate-x-1/2 -translate-y-1/2 w-[480px] sm:w-[620px] md:w-[720px] h-[480px] sm:h-[620px] md:h-[720px] rounded-full pointer-events-none transition-all duration-700 aurora-center-glow"
        style={{
          background:
            'radial-gradient(circle at center, rgba(255, 255, 255, 0.95) 0%, rgba(245, 243, 255, 0.65) 35%, rgba(236, 236, 250, 0.3) 60%, transparent 80%)',
          filter: 'blur(30px)',
        }}
      />

      {/* Top Zenith Soft Lavender Ambient Wash */}
      <div
        className="absolute top-0 inset-x-0 h-[280px] pointer-events-none opacity-60"
        style={{
          background:
            'radial-gradient(ellipse 70% 50% at 50% -10%, rgba(199, 183, 255, 0.25) 0%, rgba(221, 213, 255, 0.12) 45%, transparent 85%)',
        }}
      />

      {/* Left Ambient Halo (Soft Pink & Lavender) */}
      <div
        className="absolute top-[35%] -left-[10%] w-[55vw] max-w-[700px] h-[55vh] max-h-[600px] rounded-full pointer-events-none opacity-60 blur-[80px] aurora-halo-left"
        style={{
          background:
            'radial-gradient(ellipse at center, rgba(245, 199, 235, 0.45) 0%, rgba(199, 183, 255, 0.3) 45%, transparent 75%)',
        }}
      />

      {/* Right Ambient Halo (Icy Blue & Pale Violet) */}
      <div
        className="absolute top-[38%] -right-[10%] w-[55vw] max-w-[700px] h-[55vh] max-h-[600px] rounded-full pointer-events-none opacity-60 blur-[80px] aurora-halo-right"
        style={{
          background:
            'radial-gradient(ellipse at center, rgba(185, 221, 251, 0.48) 0%, rgba(221, 213, 255, 0.32) 45%, transparent 75%)',
        }}
      />

      {/* 2. Flowing Aurora Silk Ribbons (Vector Curves with Luminous Crests) */}
      <svg
        className="absolute inset-0 w-full h-full pointer-events-none"
        viewBox="0 0 1440 900"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        preserveAspectRatio="xMidYMid slice"
      >
        <defs>
          {/* Left Ribbon Main Gradient */}
          <linearGradient id="auroraLeftMain" x1="0%" y1="15%" x2="100%" y2="85%">
            <stop offset="0%" stopColor="#F5C7EB" stopOpacity="0.55" />
            <stop offset="35%" stopColor="#C7B7FF" stopOpacity="0.48" />
            <stop offset="70%" stopColor="#B9DDFB" stopOpacity="0.42" />
            <stop offset="100%" stopColor="#DDD5FF" stopOpacity="0.25" />
          </linearGradient>

          {/* Left Ribbon Crest Stroke Gradient (Luminous Highlights) */}
          <linearGradient id="auroraLeftCrest" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.95" />
            <stop offset="32%" stopColor="#DDD5FF" stopOpacity="0.85" />
            <stop offset="68%" stopColor="#C7B7FF" stopOpacity="0.75" />
            <stop offset="100%" stopColor="#F5C7EB" stopOpacity="0.45" />
          </linearGradient>

          {/* Right Ribbon Main Gradient */}
          <linearGradient id="auroraRightMain" x1="100%" y1="15%" x2="0%" y2="85%">
            <stop offset="0%" stopColor="#B9DDFB" stopOpacity="0.55" />
            <stop offset="35%" stopColor="#DDD5FF" stopOpacity="0.48" />
            <stop offset="70%" stopColor="#C7B7FF" stopOpacity="0.42" />
            <stop offset="100%" stopColor="#F5C7EB" stopOpacity="0.25" />
          </linearGradient>

          {/* Right Ribbon Crest Stroke Gradient (Luminous Highlights) */}
          <linearGradient id="auroraRightCrest" x1="100%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.95" />
            <stop offset="32%" stopColor="#B9DDFB" stopOpacity="0.85" />
            <stop offset="68%" stopColor="#DDD5FF" stopOpacity="0.75" />
            <stop offset="100%" stopColor="#C7B7FF" stopOpacity="0.45" />
          </linearGradient>

          {/* Gaussian Blur Filters */}
          <filter id="auroraBlurWide" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="46" />
          </filter>
          <filter id="auroraBlurMedium" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="24" />
          </filter>
          <filter id="auroraCrestGlow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* LEFT AURORA RIBBON GROUP */}
        <g className="aurora-drift-left">
          {/* Left Secondary Under-Ribbon */}
          <path
            d="M -100 380 C 140 330, 240 560, 440 540 C 540 530, 620 480, 670 450 C 570 560, 340 700, 160 700 C 40 700, -40 640, -100 580 Z"
            fill="url(#auroraLeftMain)"
            opacity="0.7"
            filter="url(#auroraBlurWide)"
          />

          {/* Left Primary Silk Ribbon */}
          <path
            d="M -120 220 C 180 170, 280 480, 520 460 C 630 450, 700 390, 730 365 C 640 480, 400 640, 200 640 C 50 640, -30 570, -120 500 Z"
            fill="url(#auroraLeftMain)"
            filter="url(#auroraBlurWide)"
          />

          {/* Left Luminous Silk Ridge Crest */}
          <path
            d="M -100 240 C 170 190, 260 455, 490 440 C 590 432, 665 385, 715 360"
            stroke="url(#auroraLeftCrest)"
            strokeWidth="4"
            strokeLinecap="round"
            fill="none"
            filter="url(#auroraCrestGlow)"
            className="aurora-crest-left"
          />
        </g>

        {/* RIGHT AURORA RIBBON GROUP */}
        <g className="aurora-drift-right">
          {/* Right Secondary Under-Ribbon */}
          <path
            d="M 1540 390 C 1300 340, 1200 570, 1000 550 C 900 540, 820 490, 770 460 C 870 570, 1100 710, 1280 710 C 1400 710, 1480 650, 1540 590 Z"
            fill="url(#auroraRightMain)"
            opacity="0.7"
            filter="url(#auroraBlurWide)"
          />

          {/* Right Primary Silk Ribbon */}
          <path
            d="M 1560 230 C 1260 180, 1160 490, 920 470 C 810 460, 740 400, 710 375 C 800 490, 1040 650, 1240 650 C 1390 650, 1470 580, 1560 510 Z"
            fill="url(#auroraRightMain)"
            filter="url(#auroraBlurWide)"
          />

          {/* Right Luminous Silk Ridge Crest */}
          <path
            d="M 1540 250 C 1270 200, 1180 465, 950 450 C 850 442, 775 395, 725 370"
            stroke="url(#auroraRightCrest)"
            strokeWidth="4"
            strokeLinecap="round"
            fill="none"
            filter="url(#auroraCrestGlow)"
            className="aurora-crest-right"
          />
        </g>
      </svg>

      {/* 3. Milestone Genuine Success Shimmer Overlay */}
      {milestone && (
        <div
          key={milestone}
          className="absolute inset-0 pointer-events-none animate-in fade-in duration-700 ease-out z-10"
          style={{
            background:
              'radial-gradient(circle at 50% 42%, rgba(255, 255, 255, 0.85) 0%, rgba(199, 183, 255, 0.35) 45%, transparent 75%)',
          }}
        />
      )}

      {/* 4. Delicate Atmospheric Floating Motes */}
      {motes.map((mote) => (
        <div
          key={mote.id}
          className="absolute rounded-full pointer-events-none aurora-mote"
          style={{
            left: `${mote.x}%`,
            top: `${mote.y}%`,
            width: `${mote.size}px`,
            height: `${mote.size}px`,
            backgroundColor: mote.color,
            boxShadow: `0 0 8px 1px ${mote.color}60`,
            animationDuration: `${mote.duration}s`,
            animationDelay: `${mote.delay}s`,
          }}
        />
      ))}

      {/* Embedded GPU CSS Animation Rules */}
      <style>{`
        @keyframes auroraDriftLeft {
          0% {
            transform: translate3d(0, 0, 0) scale(1) rotate(0deg);
          }
          50% {
            transform: translate3d(24px, -18px, 0) scale(1.03) rotate(0.9deg);
          }
          100% {
            transform: translate3d(-14px, 16px, 0) scale(0.98) rotate(-0.7deg);
          }
        }

        @keyframes auroraCrestLeft {
          0% {
            transform: translate3d(0, 0, 0) scale(1);
            opacity: 0.85;
          }
          50% {
            transform: translate3d(16px, -12px, 0) scale(1.02);
            opacity: 1;
          }
          100% {
            transform: translate3d(-12px, 10px, 0) scale(0.98);
            opacity: 0.78;
          }
        }

        @keyframes auroraDriftRight {
          0% {
            transform: translate3d(0, 0, 0) scale(1) rotate(0deg);
          }
          50% {
            transform: translate3d(-26px, -16px, 0) scale(1.04) rotate(-1.1deg);
          }
          100% {
            transform: translate3d(16px, 18px, 0) scale(0.98) rotate(0.8deg);
          }
        }

        @keyframes auroraCrestRight {
          0% {
            transform: translate3d(0, 0, 0) scale(1);
            opacity: 0.85;
          }
          50% {
            transform: translate3d(-18px, -10px, 0) scale(1.02);
            opacity: 1;
          }
          100% {
            transform: translate3d(12px, 12px, 0) scale(0.98);
            opacity: 0.78;
          }
        }

        @keyframes auroraCenterPulse {
          0% {
            transform: translate3d(-50%, -50%, 0) scale(1);
            opacity: 0.88;
          }
          50% {
            transform: translate3d(-50%, -50%, 0) scale(1.05);
            opacity: 1;
          }
          100% {
            transform: translate3d(-50%, -50%, 0) scale(0.97);
            opacity: 0.85;
          }
        }

        @keyframes auroraMotePulse {
          0%, 100% {
            opacity: 0.25;
            transform: translate3d(0, 0, 0) scale(1);
          }
          50% {
            opacity: 0.75;
            transform: translate3d(0, -6px, 0) scale(1.2);
          }
        }

        .aurora-drift-left {
          animation: auroraDriftLeft 17s ease-in-out infinite alternate;
          will-change: transform;
          transform-origin: 20% 40%;
        }

        .aurora-crest-left {
          animation: auroraCrestLeft 13s ease-in-out infinite alternate;
          will-change: transform, opacity;
          transform-origin: 20% 40%;
        }

        .aurora-drift-right {
          animation: auroraDriftRight 19s ease-in-out infinite alternate;
          will-change: transform;
          transform-origin: 80% 40%;
        }

        .aurora-crest-right {
          animation: auroraCrestRight 15s ease-in-out infinite alternate;
          will-change: transform, opacity;
          transform-origin: 80% 40%;
        }

        .aurora-center-glow {
          animation: auroraCenterPulse 14s ease-in-out infinite alternate;
          will-change: transform, opacity;
        }

        .aurora-mote {
          animation: auroraMotePulse 8s ease-in-out infinite;
          will-change: transform, opacity;
        }

        @media (prefers-reduced-motion: reduce) {
          .aurora-drift-left,
          .aurora-crest-left,
          .aurora-drift-right,
          .aurora-crest-right,
          .aurora-center-glow,
          .aurora-mote {
            animation: none !important;
            transform: none !important;
          }
        }
      `}</style>
    </div>
  );
};
