import React from 'react';

interface GradientTextProps {
  children: React.ReactNode;
  colors?: string[];
  animationSpeed?: number;
  showBorder?: boolean;
  className?: string;
}

const GradientText: React.FC<GradientTextProps> = ({
  children,
  colors = ["#ff6b6b", "#4ecdc4", "#45b7d1", "#96ceb4", "#feca57"],
  animationSpeed = 4,
  showBorder = false,
  className = ""
}) => {
  return (
    <span
      className={`inline-block ${className}`}
      style={{
        background: `linear-gradient(to right, ${colors.join(', ')})`,
        backgroundSize: `${colors.length * 100}% 100%`,
        WebkitBackgroundClip: 'text',
        WebkitTextFillColor: 'transparent',
        backgroundClip: 'text',
        color: 'transparent',
        animation: `gradient-shift ${animationSpeed}s ease-in-out infinite`,
        ...(showBorder && { border: '2px solid currentColor' })
      }}
    >
      {children}
      <style>{`
        @keyframes gradient-shift {
          0%, 100% {
            background-position: 0% 50%;
          }
          50% {
            background-position: 100% 50%;
          }
        }
      `}</style>
    </span>
  );
};

export default GradientText;
