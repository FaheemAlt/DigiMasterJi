import { motion } from 'framer-motion';
import { Bot, User, Mic } from 'lucide-react';
import AudioPlayer from './AudioPlayer';

/**
 * AudioMessageBubble Component
 * Specialized bubble for voice/audio-only messages
 * Used when the message is primarily audio (voice recordings or TTS-only responses)
 */
export default function AudioMessageBubble({
  message,
  isUser = false,
  showAvatar = true,
}) {
  // Format timestamp
  const formatTime = (timestamp) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  };

  // Get audio source
  const audioSource = message.audio_url || message.audio_base64;
  if (!audioSource) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
    >
      {/* Avatar */}
      {showAvatar && (
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.1, type: 'spring', stiffness: 200 }}
          className={`
            flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center
            ${isUser
              ? 'bg-gradient-to-br from-violet-500 to-indigo-600'
              : 'bg-gradient-to-br from-emerald-400 to-teal-500'
            }
            shadow-lg
          `}
        >
          {isUser ? (
            <Mic className="w-5 h-5 text-white" />
          ) : (
            <Bot className="w-5 h-5 text-white" />
          )}
        </motion.div>
      )}

      {/* Audio Content */}
      <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} max-w-[80%] sm:max-w-[70%]`}>
        {/* Audio Player Container */}
        <div
          className={`
            relative w-full min-w-[240px] sm:min-w-[280px]
            ${isUser
              ? 'bg-gradient-to-br from-violet-600/80 to-indigo-600/80 rounded-tr-sm'
              : 'bg-white/10 backdrop-blur-sm border border-white/10 rounded-tl-sm'
            }
            rounded-2xl overflow-hidden
          `}
        >
          {/* Voice Message Label */}
          <div className={`
            flex items-center gap-2 px-4 pt-3 pb-1
            ${isUser ? 'text-white/80' : 'text-white/60'}
          `}>
            <Mic className="w-3.5 h-3.5" />
            <span className="text-xs font-medium">
              {isUser ? 'Voice Message' : 'Audio Response'}
            </span>
          </div>

          {/* Audio Player */}
          <div className="px-2 pb-2">
            <AudioPlayer
              audioUrl={message.audio_url}
              audioBase64={message.audio_base64}
              format={message.audio_format || 'mp3'}
              compact={true}
              accentColor={isUser ? 'violet' : 'emerald'}
            />
          </div>

          {/* Transcription (if available) */}
          {message.content && (
            <div className={`
              px-4 py-2 border-t
              ${isUser ? 'border-white/20' : 'border-white/10'}
            `}>
              <p className="text-xs text-white/60 italic leading-relaxed">
                "{message.content}"
              </p>
            </div>
          )}
        </div>

        {/* Timestamp */}
        <div className={`flex items-center gap-2 mt-1 px-1 ${isUser ? 'flex-row-reverse' : ''}`}>
          <span className="text-xs text-white/40">
            {formatTime(message.timestamp)}
          </span>
        </div>
      </div>
    </motion.div>
  );
}
