import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Send,
  Mic,
  MicOff,
  Square,
  Loader2,
  Volume2,
  VolumeX,
  X,
  AlertCircle,
  WifiOff,
  Zap,
  Globe,
  Cpu
} from 'lucide-react';
import { useAudioRecorder } from '../../hooks/useAudioRecorder';

/**
 * ChatInput Component
 * Text input area with voice recording capability
 * 
 * Features:
 * - Text input with send button
 * - Voice recording with visual feedback
 * - Recording timer and audio level visualization
 * - TTS toggle for AI responses
 * - Web search toggle for live internet searches
 */
export default function ChatInput({
  onSendMessage,
  onSendVoice,
  disabled = false,
  placeholder = "Type your message...",
  showVoiceButton = true,
  enableTTS = true, // Default TTS enabled
  onTTSToggle,
  isOffline = false, // Offline mode - disables input
  isUsingBrowserAI = false, // Using Browser AI (offline but model ready)
  isDataSaverMode = false, // Data Saver mode - disables input to save data
}) {
  const [message, setMessage] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const [ttsEnabled, setTtsEnabled] = useState(enableTTS);
  const [showRecordingUI, setShowRecordingUI] = useState(false);
  const [webSearchEnabled, setWebSearchEnabled] = useState(false);

  // Audio recorder hook
  const {
    isRecording,
    recordingTime,
    formattedTime,
    audioBlob,
    error: recordingError,
    permissionStatus,
    audioLevel,
    startRecording,
    stopRecording,
    cancelRecording,
    clearAudio,
  } = useAudioRecorder();

  // Handle recording completion
  useEffect(() => {
    if (audioBlob && !isRecording) {
      // Auto-send when recording stops
      handleSendVoice();
    }
  }, [audioBlob, isRecording]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      onSendMessage?.(message.trim(), {
        includeAudio: ttsEnabled,
        enableWebSearch: webSearchEnabled,
      });
      setMessage('');
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleMicClick = () => {
    if (isRecording) {
      stopRecording();
    } else {
      setShowRecordingUI(true);
      startRecording();
    }
  };

  const handleCancelRecording = () => {
    cancelRecording();
    setShowRecordingUI(false);
  };

  const handleSendVoice = async () => {
    if (audioBlob && onSendVoice) {
      await onSendVoice(audioBlob, {
        includeAudio: ttsEnabled,
        enableWebSearch: webSearchEnabled,
      });
      clearAudio();
      setShowRecordingUI(false);
    }
  };

  const toggleTTS = () => {
    const newValue = !ttsEnabled;
    setTtsEnabled(newValue);
    onTTSToggle?.(newValue);
  };

  const toggleWebSearch = () => {
    setWebSearchEnabled(!webSearchEnabled);
  };

  // Recording UI
  if (showRecordingUI && (isRecording || audioBlob)) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 20 }}
        className="relative"
      >
        {/* Recording Error */}
        {recordingError && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="absolute -top-16 left-0 right-0 mx-4"
          >
            <div className="flex items-center gap-2 px-4 py-2 bg-red-500/20 border border-red-500/30 rounded-xl text-red-400 text-sm">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{recordingError}</span>
            </div>
          </motion.div>
        )}

        <div className="flex items-center gap-3 p-4 bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl">
          {/* Cancel Button */}
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleCancelRecording}
            className="p-2.5 rounded-xl bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-all"
            title="Cancel recording"
          >
            <X className="w-5 h-5" />
          </motion.button>

          {/* Recording Indicator */}
          <div className="flex-1 flex items-center gap-3">
            {isRecording ? (
              <>
                {/* Pulsing Recording Dot */}
                <motion.div
                  animate={{ scale: [1, 1.2, 1], opacity: [1, 0.7, 1] }}
                  transition={{ duration: 1, repeat: Infinity }}
                  className="w-3 h-3 rounded-full bg-red-500"
                />

                {/* Audio Level Bars */}
                <div className="flex items-center gap-0.5 h-8">
                  {[...Array(20)].map((_, i) => (
                    <motion.div
                      key={i}
                      className="w-1 bg-violet-500 rounded-full"
                      animate={{
                        height: audioLevel > (i * 5) ? `${Math.min(32, 8 + audioLevel * 0.25)}px` : '4px',
                        opacity: audioLevel > (i * 5) ? 1 : 0.3,
                      }}
                      transition={{ duration: 0.05 }}
                    />
                  ))}
                </div>

                {/* Timer */}
                <span className="text-white/80 font-mono text-sm min-w-[50px]">
                  {formattedTime}
                </span>
              </>
            ) : (
              <span className="text-white/60 text-sm">
                Processing audio...
              </span>
            )}
          </div>

          {/* Stop/Send Button */}
          {isRecording ? (
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={stopRecording}
              className="p-3 rounded-xl bg-gradient-to-r from-red-500 to-pink-500 text-white shadow-lg shadow-red-500/30"
              title="Stop recording"
            >
              <Square className="w-5 h-5 fill-current" />
            </motion.button>
          ) : audioBlob ? (
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={handleSendVoice}
              disabled={disabled}
              className="p-3 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 text-white shadow-lg shadow-violet-500/30 disabled:opacity-50"
              title="Send voice message"
            >
              <Send className="w-5 h-5" />
            </motion.button>
          ) : (
            <Loader2 className="w-5 h-5 text-white/50 animate-spin" />
          )}
        </div>
      </motion.div>
    );
  }

  // Normal Text Input UI
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="relative"
    >
      {/* Offline Warning */}
      {isOffline && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="absolute -top-14 left-0 right-0 mx-4"
        >
          <div className="flex items-center gap-2 px-4 py-2 bg-amber-500/20 border border-amber-500/30 rounded-xl text-amber-400 text-sm">
            <WifiOff className="w-4 h-4 flex-shrink-0" />
            <span>You're offline. Chat is disabled until connection is restored.</span>
          </div>
        </motion.div>
      )}

      {/* Browser AI Mode Info */}
      {isUsingBrowserAI && !isOffline && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="absolute -top-14 left-0 right-0 mx-4"
        >
          <div className="flex items-center gap-2 px-4 py-2 bg-orange-500/20 border border-orange-500/30 rounded-xl text-orange-400 text-sm">
            <Cpu className="w-4 h-4 flex-shrink-0" />
            <span>Using Browser AI - Voice features unavailable offline.</span>
          </div>
        </motion.div>
      )}

      {/* Data Saver Mode Warning */}
      {isDataSaverMode && !isOffline && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="absolute -top-14 left-0 right-0 mx-4"
        >
          <div className="flex items-center gap-2 px-4 py-2 bg-amber-500/20 border border-amber-500/30 rounded-xl text-amber-400 text-sm">
            <Zap className="w-4 h-4 flex-shrink-0" />
            <span>Data Saver is ON. Chat is disabled to save data. Turn it off to continue.</span>
          </div>
        </motion.div>
      )}

      {/* Permission Denied Warning */}
      {permissionStatus === 'denied' && showVoiceButton && !isOffline && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="absolute -top-12 left-0 right-0 mx-4"
        >
          <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-500/20 border border-amber-500/30 rounded-lg text-amber-400 text-xs">
            <MicOff className="w-3 h-3" />
            <span>Microphone access denied. Enable in browser settings.</span>
          </div>
        </motion.div>
      )}

      {/* Gradient Border Effect */}
      <div className={`
        absolute -inset-0.5 rounded-2xl
        bg-gradient-to-r from-violet-600 via-indigo-600 to-violet-600
        opacity-0 blur transition-opacity duration-300
        ${isFocused ? 'opacity-50' : ''}
      `} />

      <form
        onSubmit={handleSubmit}
        className={`
          relative flex items-end gap-2 p-3
          bg-white/5 backdrop-blur-xl
          border border-white/10 rounded-2xl
          transition-all duration-300
          ${isFocused ? 'border-violet-500/50 bg-white/10' : ''}
          ${(isOffline || isDataSaverMode) ? 'opacity-60 cursor-not-allowed' : ''}
        `}
      >
        {/* Feature Toggle Buttons Row */}
        <div className="absolute -top-10 left-0 flex items-center gap-2">
          {/* Web Search Toggle */}
          <motion.button
            type="button"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={toggleWebSearch}
            disabled={isDataSaverMode || isOffline}
            className={`
              flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium
              transition-all duration-200
              ${(isDataSaverMode || isOffline)
                ? 'bg-white/5 text-white/20 cursor-not-allowed'
                : webSearchEnabled
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  : 'bg-white/5 text-white/50 border border-white/10 hover:bg-white/10 hover:text-white/70'
              }
            `}
            title={isDataSaverMode ? 'Disabled in Data Saver mode' : webSearchEnabled ? 'Web search enabled' : 'Enable web search'}
          >
            {webSearchEnabled ? (
              <>
                <Globe className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Search</span>
              </>
            ) : (
              <>
                <Globe className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Search</span>
              </>
            )}
          </motion.button>
        </div>

        {/* TTS Toggle Button */}
        <motion.button
          type="button"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={toggleTTS}
          disabled={isDataSaverMode || isOffline || isUsingBrowserAI}
          className={`
            p-2 rounded-xl transition-all
            ${(isDataSaverMode || isOffline || isUsingBrowserAI)
              ? 'bg-white/5 text-white/20 cursor-not-allowed'
              : ttsEnabled
                ? 'bg-emerald-500/20 text-emerald-400'
                : 'bg-white/10 text-white/40 hover:text-white/60'
            }
          `}
          title={isDataSaverMode ? 'Disabled in Data Saver mode' : isUsingBrowserAI ? 'Voice unavailable offline' : ttsEnabled ? 'Voice responses ON' : 'Voice responses OFF'}
        >
          {ttsEnabled ? <Volume2 className="w-5 h-5" /> : <VolumeX className="w-5 h-5" />}
        </motion.button>

        {/* Text Input */}
        <div className="flex-1 relative">
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            onKeyDown={handleKeyDown}
            placeholder={isOffline ? "You're offline..." : isUsingBrowserAI ? "Ask Browser AI..." : isDataSaverMode ? "Data Saver is ON..." : placeholder}
            disabled={disabled || isDataSaverMode}
            rows={1}
            className="
              w-full bg-transparent text-white placeholder-white/40
              resize-none outline-none
              text-sm sm:text-base
              max-h-32 scrollbar-thin scrollbar-thumb-white/20
              disabled:opacity-50 disabled:cursor-not-allowed
            "
            style={{
              minHeight: '24px',
              height: 'auto',
            }}
            onInput={(e) => {
              e.target.style.height = 'auto';
              e.target.style.height = Math.min(e.target.scrollHeight, 128) + 'px';
            }}
          />
        </div>

        {/* Voice Button */}
        {showVoiceButton && (
          <motion.button
            type="button"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleMicClick}
            disabled={disabled || permissionStatus === 'denied' || isDataSaverMode || isOffline || isUsingBrowserAI}
            className={`
              p-2.5 rounded-xl transition-all
              ${(permissionStatus === 'denied' || isDataSaverMode || isOffline || isUsingBrowserAI)
                ? 'bg-white/5 text-white/20 cursor-not-allowed'
                : 'bg-white/10 text-white/70 hover:bg-white/20 hover:text-white'
              }
              disabled:opacity-50 disabled:cursor-not-allowed
            `}
            title={isDataSaverMode ? 'Disabled in Data Saver mode' : isUsingBrowserAI ? 'Voice unavailable offline' : permissionStatus === 'denied' ? 'Microphone access denied' : 'Voice message'}
          >
            <Mic className="w-5 h-5" />
          </motion.button>
        )}

        {/* Send Button */}
        <motion.button
          type="submit"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          disabled={!message.trim() || disabled || isDataSaverMode || isOffline}
          className={`
            p-2.5 rounded-xl
            transition-all duration-200
            ${message.trim() && !disabled && !isDataSaverMode && !isOffline
              ? 'bg-gradient-to-r from-violet-600 to-indigo-600 text-white shadow-lg shadow-violet-500/30'
              : 'bg-white/10 text-white/30 cursor-not-allowed'
            }
          `}
          title={isDataSaverMode ? 'Disabled in Data Saver mode' : 'Send message'}
        >
          {disabled ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Send className="w-5 h-5" />
          )}
        </motion.button>
      </form>

      {/* Character Count */}
      {message.length > 100 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="absolute -top-6 right-2 text-xs text-white/40"
        >
          {message.length} / 5000
        </motion.div>
      )}
    </motion.div>
  );
}
