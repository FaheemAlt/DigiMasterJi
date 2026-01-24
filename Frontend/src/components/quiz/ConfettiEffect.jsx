import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

/**
 * ConfettiEffect Component
 * Celebration animation for quiz completion
 * Creates a fun, engaging celebration effect
 */

// Confetti piece component
const ConfettiPiece = ({ color, delay, startX, startY }) => {
  const randomRotation = Math.random() * 720 - 360;
  const randomX = (Math.random() - 0.5) * 400;
  const randomY = Math.random() * 600 + 200;
  const duration = Math.random() * 2 + 2;

  return (
    <motion.div
      initial={{
        x: startX,
        y: startY,
        rotate: 0,
        opacity: 1,
        scale: 1,
      }}
      animate={{
        x: startX + randomX,
        y: startY + randomY,
        rotate: randomRotation,
        opacity: 0,
        scale: 0.5,
      }}
      transition={{
        duration,
        delay,
        ease: 'easeOut',
      }}
      className="absolute pointer-events-none"
      style={{ zIndex: 100 }}
    >
      <div
        className="w-3 h-3 rounded-sm"
        style={{ backgroundColor: color }}
      />
    </motion.div>
  );
};

// Star burst component
const StarBurst = ({ delay }) => {
  return (
    <motion.div
      initial={{ scale: 0, opacity: 1 }}
      animate={{ scale: 3, opacity: 0 }}
      transition={{ duration: 0.8, delay }}
      className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
    >
      <span className="text-6xl">⭐</span>
    </motion.div>
  );
};

// Emoji burst component
const EmojiBurst = ({ emoji, delay, startX, startY }) => {
  const randomX = (Math.random() - 0.5) * 300;
  const randomY = -(Math.random() * 200 + 100);

  return (
    <motion.div
      initial={{
        x: startX,
        y: startY,
        scale: 0,
        opacity: 1,
      }}
      animate={{
        x: startX + randomX,
        y: startY + randomY,
        scale: 1.5,
        opacity: 0,
      }}
      transition={{
        duration: 1.5,
        delay,
        ease: 'easeOut',
      }}
      className="absolute text-4xl pointer-events-none"
      style={{ zIndex: 100 }}
    >
      {emoji}
    </motion.div>
  );
};

export default function ConfettiEffect({ 
  isActive, 
  duration = 3000,
  intensity = 'high', // 'low', 'medium', 'high'
  celebrationEmojis = ['🎉', '🎊', '🌟', '✨', '🏆', '💯', '🔥'],
}) {
  const [pieces, setPieces] = useState([]);
  const [emojis, setEmojis] = useState([]);
  const [showStars, setShowStars] = useState(false);

  const colors = [
    '#8B5CF6', // violet
    '#6366F1', // indigo
    '#EC4899', // pink
    '#F59E0B', // amber
    '#10B981', // emerald
    '#3B82F6', // blue
    '#EF4444', // red
    '#F97316', // orange
  ];

  const pieceCount = {
    low: 30,
    medium: 60,
    high: 100,
  };

  useEffect(() => {
    if (isActive) {
      // Generate confetti pieces
      const newPieces = Array.from({ length: pieceCount[intensity] }, (_, i) => ({
        id: i,
        color: colors[Math.floor(Math.random() * colors.length)],
        delay: Math.random() * 0.5,
        startX: Math.random() * window.innerWidth,
        startY: -20,
      }));
      setPieces(newPieces);

      // Generate celebration emojis
      const newEmojis = Array.from({ length: 15 }, (_, i) => ({
        id: i,
        emoji: celebrationEmojis[Math.floor(Math.random() * celebrationEmojis.length)],
        delay: Math.random() * 0.8,
        startX: Math.random() * window.innerWidth,
        startY: window.innerHeight * 0.6,
      }));
      setEmojis(newEmojis);

      // Show star bursts
      setShowStars(true);

      // Clear after duration
      const timer = setTimeout(() => {
        setPieces([]);
        setEmojis([]);
        setShowStars(false);
      }, duration);

      return () => clearTimeout(timer);
    }
  }, [isActive, intensity, duration]);

  return (
    <AnimatePresence>
      {isActive && (
        <div className="fixed inset-0 pointer-events-none overflow-hidden" style={{ zIndex: 99 }}>
          {/* Star bursts in center */}
          {showStars && (
            <>
              <StarBurst delay={0} />
              <StarBurst delay={0.2} />
              <StarBurst delay={0.4} />
            </>
          )}

          {/* Confetti pieces */}
          {pieces.map((piece) => (
            <ConfettiPiece
              key={piece.id}
              color={piece.color}
              delay={piece.delay}
              startX={piece.startX}
              startY={piece.startY}
            />
          ))}

          {/* Celebration emojis */}
          {emojis.map((item) => (
            <EmojiBurst
              key={`emoji-${item.id}`}
              emoji={item.emoji}
              delay={item.delay}
              startX={item.startX}
              startY={item.startY}
            />
          ))}

          {/* Glow effect overlay */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="absolute inset-0 bg-gradient-to-b from-violet-500/10 via-transparent to-transparent"
          />
        </div>
      )}
    </AnimatePresence>
  );
}

// Export a simpler celebration burst for inline use
export function CelebrationBurst({ isActive }) {
  return (
    <AnimatePresence>
      {isActive && (
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          exit={{ scale: 0, opacity: 0 }}
          className="absolute inset-0 flex items-center justify-center pointer-events-none"
        >
          <motion.div
            animate={{
              scale: [1, 1.2, 1],
              rotate: [0, 10, -10, 0],
            }}
            transition={{
              duration: 0.5,
              repeat: 2,
            }}
            className="text-6xl"
          >
            🎉
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
