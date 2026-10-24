import React, { useMemo } from 'react';

export const BackgroundStars: React.FC = () => {
  const stars = useMemo(() => {
    return Array.from({ length: 32 }, (_, i) => ({
      id: i,
      x: Math.random() * 98 + 1,
      y: Math.random() * 85 + 5,
      size: Math.random() * 2 + 1,
      opacity: Math.random() * 0.6 + 0.2,
      duration: Math.random() * 3 + 2,
    }));
  }, []);

  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden z-0">
      {stars.map((star) => (
        <div
          key={star.id}
          className="absolute rounded-full bg-white animate-pulse"
          style={{
            left: `${star.x}%`,
            top: `${star.y}%`,
            width: `${star.size}px`,
            height: `${star.size}px`,
            opacity: star.opacity,
            animationDuration: `${star.duration}s`,
            boxShadow: star.size > 2 ? '0 0 4px 1px rgba(255, 255, 255, 0.6)' : 'none',
          }}
        />
      ))}
    </div>
  );
};
