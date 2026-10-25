import React, { useMemo } from 'react';

const PASTEL_COLORS = ['#7664E8', '#6BA1F5', '#E68FC4', '#DFE1F2', '#ECECFA'];

export const BackgroundStars: React.FC = () => {
  const stars = useMemo(() => {
    return Array.from({ length: 28 }, (_, i) => ({
      id: i,
      x: Math.random() * 96 + 2,
      y: Math.random() * 90 + 5,
      size: Math.random() * 3 + 2,
      color: PASTEL_COLORS[i % PASTEL_COLORS.length],
      opacity: Math.random() * 0.45 + 0.25,
      duration: Math.random() * 4 + 3,
    }));
  }, []);

  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden z-0">
      {/* Soft atmospheric gradient washes */}
      <div className="absolute top-0 left-0 w-[550px] h-[550px] rounded-full blur-[110px] opacity-40 bg-[#F7E8F5] pointer-events-none" />
      <div className="absolute top-0 right-0 w-[550px] h-[550px] rounded-full blur-[110px] opacity-40 bg-[#E3EEFF] pointer-events-none" />
      <div className="absolute bottom-10 left-1/2 -translate-x-1/2 w-[700px] h-[400px] rounded-full blur-[120px] opacity-35 bg-[#ECECFA] pointer-events-none" />

      {/* Floating ambient motes */}
      {stars.map((star) => (
        <div
          key={star.id}
          className="absolute rounded-full animate-pulse"
          style={{
            left: `${star.x}%`,
            top: `${star.y}%`,
            width: `${star.size}px`,
            height: `${star.size}px`,
            backgroundColor: star.color,
            opacity: star.opacity,
            animationDuration: `${star.duration}s`,
            boxShadow: `0 0 6px 1px ${star.color}40`,
          }}
        />
      ))}
    </div>
  );
};
