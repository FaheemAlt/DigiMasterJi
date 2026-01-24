import { useRef, useEffect, useState, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Play,
  Pause,
  Volume2,
  VolumeX,
  RotateCcw,
  Loader2,
  AlertCircle,
} from 'lucide-react';
import WaveSurfer from 'wavesurfer.js';

export default function AudioPlayer({
  audioUrl,
  audioBase64,
  format = 'mp3',
  compact = false,
  accentColor = 'violet',
  onPlay,
  onPause,
  onEnded,
}) {
  const containerRef = useRef(null);
  const wavesurferRef = useRef(null);

  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [isMuted, setIsMuted] = useState(false);
  const [volume, setVolume] = useState(0.8);

  /* ---------------- Colors ---------------- */

  const colorSchemes = {
    violet: {
      waveColor: 'rgba(139, 92, 246, 0.4)',
      progressColor: 'rgba(139, 92, 246, 1)',
      cursorColor: 'rgba(255, 255, 255, 0.8)',
    },
    emerald: {
      waveColor: 'rgba(52, 211, 153, 0.4)',
      progressColor: 'rgba(52, 211, 153, 1)',
      cursorColor: 'rgba(255, 255, 255, 0.8)',
    },
    indigo: {
      waveColor: 'rgba(99, 102, 241, 0.4)',
      progressColor: 'rgba(99, 102, 241, 1)',
      cursorColor: 'rgba(255, 255, 255, 0.8)',
    },
  };

  const colors = useMemo(() => {
    return colorSchemes[accentColor] || colorSchemes.violet;
  }, [accentColor]);

  /* ---------------- Audio source ---------------- */

  const getAudioSource = useCallback(() => {
    if (audioUrl) {
      return audioUrl.startsWith('data:') ? audioUrl : audioUrl;
    }
    if (audioBase64) {
      return `data:audio/${format};base64,${audioBase64}`;
    }
    return null;
  }, [audioUrl, audioBase64, format]);

  /* ---------------- Create WaveSurfer ONCE ---------------- */

  useEffect(() => {
    if (!containerRef.current) return;

    const ws = WaveSurfer.create({
      container: containerRef.current,
      waveColor: colors.waveColor,
      progressColor: colors.progressColor,
      cursorColor: colors.cursorColor,
      cursorWidth: 2,
      barWidth: compact ? 2 : 3,
      barGap: compact ? 1 : 2,
      barRadius: 3,
      height: compact ? 32 : 48,
      normalize: true,
      hideScrollbar: true,
      fillParent: true,
      minPxPerSec: 50,
      autoCenter: true,
      backend: 'WebAudio',
    });

    wavesurferRef.current = ws;

    ws.on('ready', () => {
      setIsLoading(false);
      setDuration(ws.getDuration());
      ws.setVolume(isMuted ? 0 : volume);
    });

    ws.on('audioprocess', () => {
      setCurrentTime(ws.getCurrentTime());
    });

    ws.on('seeking', () => {
      setCurrentTime(ws.getCurrentTime());
    });

    ws.on('play', () => {
      setIsPlaying(true);
      onPlay?.();
    });

    ws.on('pause', () => {
      setIsPlaying(false);
      onPause?.();
    });

    ws.on('finish', () => {
      setIsPlaying(false);
      setCurrentTime(0);
      ws.seekTo(0);
      onEnded?.();
    });

    ws.on('error', (err) => {
      if (err?.name !== 'AbortError') {
        console.error('WaveSurfer error:', err);
        setError('Failed to load audio');
        setIsLoading(false);
      }
    });

    return () => {
      ws.destroy(); // aborts fetch safely
      wavesurferRef.current = null;
    };
  }, []); // 👈 intentional: only once

  /* ---------------- Load audio when source changes ---------------- */

  useEffect(() => {
    const ws = wavesurferRef.current;
    const source = getAudioSource();

    if (!ws || !source) {
      setError('No audio source provided');
      setIsLoading(false);
      return;
    }

    setError(null);
    setIsLoading(true);

    ws.load(source).catch((err) => {
      if (err?.name !== 'AbortError') {
        console.error(err);
        setError('Failed to load audio');
        setIsLoading(false);
      }
    });
  }, [getAudioSource]);

  /* ---------------- Volume / mute (NO reload) ---------------- */

  useEffect(() => {
    if (wavesurferRef.current) {
      wavesurferRef.current.setVolume(isMuted ? 0 : volume);
    }
  }, [volume, isMuted]);

  /* ---------------- Controls ---------------- */

  const togglePlayPause = () => {
    wavesurferRef.current?.playPause();
  };

  const toggleMute = () => {
    setIsMuted((m) => !m);
  };

  const restart = () => {
    if (!wavesurferRef.current) return;
    wavesurferRef.current.seekTo(0);
    wavesurferRef.current.play();
  };

  const formatTime = (seconds) => {
    if (!seconds || isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  /* ---------------- Error UI ---------------- */

  if (error) {
    return (
      <div
        className={`
          flex items-center gap-2 px-3 py-2 rounded-xl
          bg-rose-500/10 border border-rose-500/20
          ${compact ? 'text-xs' : 'text-sm'}
        `}
      >
        <AlertCircle className="w-4 h-4 text-rose-400" />
        <span className="text-rose-300">{error}</span>
      </div>
    );
  }

  /* ---------------- Compact Layout ---------------- */

  if (compact) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center gap-2 w-full max-w-xs overflow-hidden"
      >
        <motion.button
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={togglePlayPause}
          disabled={isLoading}
          className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-gradient-to-r from-violet-600 to-indigo-600 text-white shadow-lg disabled:opacity-50"
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : isPlaying ? (
            <Pause className="w-4 h-4" />
          ) : (
            <Play className="w-4 h-4 ml-0.5" />
          )}
        </motion.button>

        <div className="flex-1 min-w-0 relative overflow-hidden">
          <div ref={containerRef} className="w-full cursor-pointer" />
        </div>

        <span className="text-xs text-white/50 tabular-nums flex-shrink-0 min-w-[32px]">
          {formatTime(currentTime)}
        </span>
      </motion.div>
    );
  }

  /* ---------------- Full Layout ---------------- */

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full p-4 rounded-2xl bg-white/5 backdrop-blur-sm border border-white/10 overflow-hidden"
    >
      <div className="relative mb-3 overflow-hidden">
        <div ref={containerRef} className="w-full cursor-pointer rounded-lg overflow-hidden" />

        <AnimatePresence>
          {isLoading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 flex items-center justify-center bg-white/5 backdrop-blur-sm"
            >
              <Loader2 className="w-5 h-5 animate-spin text-white/60" />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <motion.button
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            onClick={restart}
            disabled={isLoading}
            className="p-2 rounded-xl text-white/40 hover:text-white/70 hover:bg-white/10 disabled:opacity-50"
          >
            <RotateCcw className="w-4 h-4" />
          </motion.button>

          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={togglePlayPause}
            disabled={isLoading}
            className="w-12 h-12 rounded-full flex items-center justify-center bg-gradient-to-r from-violet-600 to-indigo-600 text-white shadow-lg disabled:opacity-50"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : isPlaying ? (
              <Pause className="w-5 h-5" />
            ) : (
              <Play className="w-5 h-5 ml-0.5" />
            )}
          </motion.button>

          <motion.button
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            onClick={toggleMute}
            disabled={isLoading}
            className="p-2 rounded-xl text-white/40 hover:text-white/70 hover:bg-white/10 disabled:opacity-50"
          >
            {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
          </motion.button>
        </div>

        <div className="text-sm text-white/70 tabular-nums">
          {formatTime(currentTime)} <span className="text-white/30">/</span>{' '}
          <span className="text-white/50">{formatTime(duration)}</span>
        </div>
      </div>
    </motion.div>
  );
}
