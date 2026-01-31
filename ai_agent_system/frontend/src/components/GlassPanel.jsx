import React, { useState } from 'react';
import { motion } from 'framer-motion';

const icons = {
  chat: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
    </svg>
  ),
  agents: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
    </svg>
  ),
  stats: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
    </svg>
  ),
  map: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
    </svg>
  ),
  data: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
    </svg>
  ),
  events: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
    </svg>
  )
};

function GlassPanel({ 
  title, 
  icon, 
  children, 
  className = '',
  flipEnabled = false,
  backContent = null
}) {
  const [isFlipped, setIsFlipped] = useState(false);
  const [isHovered, setIsHovered] = useState(false);

  const handleCornerClick = (e) => {
    if (flipEnabled) {
      setIsFlipped(!isFlipped);
    }
  };

  const handleCornerDoubleClick = (e) => {
    if (flipEnabled) {
      setIsFlipped(!isFlipped);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className={`panel-container ${className}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{ perspective: '2000px' }}
    >
      <motion.div
        className={`panel-flipper ${isFlipped ? 'flipped' : ''}`}
        animate={{
          rotateY: isFlipped ? 180 : 0,
          y: isHovered ? -5 : 0
        }}
        transition={{ duration: 0.6, ease: [0.23, 1, 0.32, 1] }}
        style={{ transformStyle: 'preserve-3d' }}
      >
        {/* Front panel */}
        <div className="panel-front glass-panel p-4 h-full" style={{ backfaceVisibility: 'hidden' }}>
          {/* Corner triggers */}
          {flipEnabled && (
            <>
              <div 
                className="corner-trigger top-left" 
                onClick={handleCornerClick}
                onDoubleClick={handleCornerDoubleClick}
              />
              <div 
                className="corner-trigger top-right" 
                onClick={handleCornerClick}
                onDoubleClick={handleCornerDoubleClick}
              />
              <div 
                className="corner-trigger bottom-left" 
                onClick={handleCornerClick}
                onDoubleClick={handleCornerDoubleClick}
              />
              <div 
                className="corner-trigger bottom-right" 
                onClick={handleCornerClick}
                onDoubleClick={handleCornerDoubleClick}
              />
            </>
          )}

          {/* Header */}
          <div className="flex items-center gap-3 mb-4">
            <div className="text-neon-blue">
              {icons[icon]}
            </div>
            <h2 className="font-orbitron text-sm tracking-wider text-gray-300">
              {title}
            </h2>
            {flipEnabled && (
              <div className="ml-auto text-xs text-gray-500">
                Click corners to flip
              </div>
            )}
          </div>

          {/* Content */}
          <div className="h-[calc(100%-3rem)] overflow-hidden">
            {children}
          </div>

          {/* Decorative elements */}
          <div className="absolute top-0 left-0 w-20 h-20 pointer-events-none">
            <svg className="w-full h-full opacity-30">
              <path d="M0 20 L20 0 L20 5 L5 20 Z" fill="url(#neonGradient)" />
            </svg>
          </div>
          <div className="absolute bottom-0 right-0 w-20 h-20 pointer-events-none rotate-180">
            <svg className="w-full h-full opacity-30">
              <path d="M0 20 L20 0 L20 5 L5 20 Z" fill="url(#neonGradient)" />
            </svg>
          </div>
        </div>

        {/* Back panel */}
        {flipEnabled && (
          <div 
            className="panel-back glass-panel p-4 h-full absolute inset-0"
            style={{ backfaceVisibility: 'hidden', transform: 'rotateY(180deg)' }}
          >
            {/* Corner triggers */}
            <div 
              className="corner-trigger top-left" 
              onClick={handleCornerClick}
              onDoubleClick={handleCornerDoubleClick}
            />
            <div 
              className="corner-trigger top-right" 
              onClick={handleCornerClick}
              onDoubleClick={handleCornerDoubleClick}
            />
            <div 
              className="corner-trigger bottom-left" 
              onClick={handleCornerClick}
              onDoubleClick={handleCornerDoubleClick}
            />
            <div 
              className="corner-trigger bottom-right" 
              onClick={handleCornerClick}
              onDoubleClick={handleCornerDoubleClick}
            />

            {/* Header */}
            <div className="flex items-center gap-3 mb-4">
              <div className="text-neon-purple">
                {icons[icon]}
              </div>
              <h2 className="font-orbitron text-sm tracking-wider text-gray-300">
                {title} • LIVE VIEW
              </h2>
            </div>

            {/* Back content */}
            <div className="h-[calc(100%-3rem)] overflow-hidden">
              {backContent}
            </div>
          </div>
        )}
      </motion.div>

      {/* SVG gradient definition */}
      <svg className="absolute w-0 h-0">
        <defs>
          <linearGradient id="neonGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#00f0ff" />
            <stop offset="100%" stopColor="#bf00ff" />
          </linearGradient>
        </defs>
      </svg>
    </motion.div>
  );
}

export default GlassPanel;
