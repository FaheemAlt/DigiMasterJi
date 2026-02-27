import { useRef, useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  MoreVertical,
  Trash2,
  Edit2,
  Share2,
  Sparkles,
  BookOpen,
  ArrowDown,
} from 'lucide-react';
import MessageBubble from './MessageBubble';
import AudioMessageBubble from './AudioMessageBubble';
import ChatInputWithVoice from './ChatInputWithVoice';
import { useNetworkStatus } from '../../contexts/NetworkStatusContext';
import { useWebLLM } from '../../contexts/WebLLMContext';
import { useLowBandwidthMode } from '../ui/LowBandwidthToggle';

/**
 * ChatWindow Component
 * Main chat area with messages and input
 * Supports text messages, voice recording (STT), and audio playback (TTS)
 */
export default function ChatWindow({
  conversation,
  messages = [],
  isLoading = false,
  isTyping = false,
  isSending = false,
  onSendMessage,
  onSendVoice,
  activeProfile,
  enableTTS = true,
}) {
  const messagesEndRef = useRef(null);
  const messagesContainerRef = useRef(null);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const [showMenu, setShowMenu] = useState(false);

  // Network status for disabling input when offline
  const { isOnline } = useNetworkStatus();

  // WebLLM for offline mode - when model is ready, enable input even when offline
  const { isModelReady: isOfflineModelReady } = useWebLLM();

  // Data Saver mode - disables chat input similar to offline mode
  const { isLowBandwidth } = useLowBandwidthMode();

  // Only disable input if offline AND no offline model available
  const isInputDisabled = !isOnline && !isOfflineModelReady;

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  // Check scroll position for "scroll to bottom" button
  const handleScroll = (e) => {
    const { scrollTop, scrollHeight, clientHeight } = e.target;
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
    setShowScrollButton(!isNearBottom);
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Determine if a message should use the audio-only bubble
  // (for voice recordings with no/minimal text content)
  const isAudioOnlyMessage = (message) => {
    const hasAudio = message.audio_url || message.audio_base64;
    const hasMinimalText = !message.content || message.content.length < 10;
    return hasAudio && hasMinimalText && message.is_voice_message;
  };

  // Get placeholder text based on language
  const getPlaceholder = () => {
    const lang = activeProfile?.preferred_language;
    if (lang === 'Hindi' || lang === 'hindi') {
      return "अपना प्रश्न यहाँ लिखें...";
    }
    if (lang === 'Hinglish' || lang === 'hinglish') {
      return "Apna sawaal yahan likho...";
    }
    return "Type your question here...";
  };

  // Empty state when no conversation selected - but still show input
  if (!conversation) {
    return (
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Empty State Content */}
        <div className="flex-1 flex flex-col items-center justify-center p-8">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="text-center max-w-md"
          >
            <div className="w-24 h-24 mx-auto mb-6 rounded-full bg-gradient-to-br from-violet-500/20 to-indigo-500/20 flex items-center justify-center">
              <Sparkles className="w-12 h-12 text-violet-400" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-3">
              {activeProfile?.preferred_language === 'Hindi'
                ? 'नई बातचीत शुरू करें'
                : 'Start a New Conversation'}
            </h2>
            <p className="text-white/60 mb-6">
              {activeProfile?.preferred_language === 'Hindi'
                ? 'अपनी पढ़ाई के बारे में कुछ भी पूछें! मैं आपकी मदद के लिए यहाँ हूं।'
                : 'Ask me anything about your studies! I\'m here to help you learn Science, Math, and more in your preferred language.'}
            </p>
            <div className="flex flex-wrap justify-center gap-2">
              {['Photosynthesis', 'Algebra', 'Physics Laws', 'Chemistry'].map((topic) => (
                <motion.button
                  key={topic}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => onSendMessage?.(topic === 'Photosynthesis' ? 'Explain photosynthesis' : `Help me understand ${topic}`)}
                  className="px-4 py-2 rounded-full bg-white/10 text-white/70 text-sm hover:bg-white/20 hover:text-white transition-all cursor-pointer"
                >
                  {topic}
                </motion.button>
              ))}
            </div>
          </motion.div>
        </div>

        {/* Input Area - Always visible but disabled when offline or Data Saver */}
        <div className="flex-shrink-0 p-4 sm:p-6 border-t border-white/5">
          <ChatInputWithVoice
            onSendMessage={onSendMessage}
            onSendVoice={onSendVoice}
            disabled={isLoading || isSending || isInputDisabled || isLowBandwidth}
            placeholder={getPlaceholder()}
            enableTTS={enableTTS}
            isOffline={isInputDisabled}
            isUsingBrowserAI={!isOnline && isOfflineModelReady}
            isDataSaverMode={isLowBandwidth}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden">
      {/* Chat Header */}
      <div className="flex-shrink-0 flex items-center justify-between px-4 sm:px-6 py-4 border-b border-white/10 bg-white/5 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-emerald-400 to-teal-500 flex items-center justify-center">
            <BookOpen className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="font-semibold text-white truncate max-w-[200px] sm:max-w-xs">
              {conversation.title || 'New Conversation'}
            </h2>
            {conversation.subject_tag && (
              <span className="text-xs text-violet-400">
                {conversation.subject_tag}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Messages Area */}
      <div
        ref={messagesContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto px-4 sm:px-6 py-4 space-y-4 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent"
      >
        {/* Welcome Message for empty conversations */}
        {messages.length === 0 && !isTyping && !isLoading && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col items-center justify-center py-12 text-center"
          >
            <div className="w-16 h-16 rounded-full bg-gradient-to-br from-emerald-400 to-teal-500 flex items-center justify-center mb-4">
              <Sparkles className="w-8 h-8 text-white" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">
              {activeProfile?.preferred_language === 'Hindi'
                ? `नमस्ते${activeProfile?.name ? `, ${activeProfile.name}` : ''}! 👋`
                : `Hello${activeProfile?.name ? `, ${activeProfile.name}` : ''}! 👋`}
            </h3>
            <p className="text-white/60 max-w-sm">
              {activeProfile?.preferred_language === 'Hindi'
                ? 'मैं आपका AI ट्यूटर हूं। अपने विषयों के बारे में कुछ भी पूछें!'
                : 'I\'m your AI tutor. Ask me anything about your subjects, and I\'ll explain it in a way that\'s easy to understand!'}
            </p>
          </motion.div>
        )}

        {/* Loading State for Messages */}
        {isLoading && messages.length === 0 && (
          <div className="space-y-4 py-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className={`flex gap-3 ${i % 2 === 0 ? 'flex-row-reverse' : ''}`}>
                <div className="w-10 h-10 rounded-full bg-white/10 animate-pulse" />
                <div className={`flex-1 max-w-[70%] space-y-2 ${i % 2 === 0 ? 'items-end' : 'items-start'}`}>
                  <div className="h-4 bg-white/10 rounded-lg animate-pulse" style={{ width: `${60 + Math.random() * 30}%` }} />
                  <div className="h-4 bg-white/10 rounded-lg animate-pulse" style={{ width: `${40 + Math.random() * 40}%` }} />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Message List */}
        {messages.map((message, index) => (
          <div key={message._id || message.id || index} className="group">
            {isAudioOnlyMessage(message) ? (
              <AudioMessageBubble
                message={message}
                isUser={message.role === 'user'}
                showAvatar={
                  index === 0 ||
                  messages[index - 1]?.role !== message.role
                }
              />
            ) : (
              <MessageBubble
                message={message}
                isUser={message.role === 'user'}
                isTyping={message.isStreaming && !message.content}
                showAvatar={
                  index === 0 ||
                  messages[index - 1]?.role !== message.role
                }
              />
            )}
          </div>
        ))}

        {/* Typing Indicator - only show when NOT streaming (streaming shows inline) */}
        {isTyping && !messages.some(m => m.isStreaming) && (
          <MessageBubble
            message={{ content: '' }}
            isUser={false}
            isTyping={true}
            showAvatar={true}
          />
        )}

        {/* Scroll anchor */}
        <div ref={messagesEndRef} />
      </div>

      {/* Scroll to Bottom Button */}
      <AnimatePresence>
        {showScrollButton && (
          <motion.button
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            onClick={scrollToBottom}
            className="absolute bottom-24 right-6 p-3 rounded-full bg-violet-600 text-white shadow-lg shadow-violet-500/30 hover:bg-violet-700 transition-colors"
          >
            <ArrowDown className="w-5 h-5" />
          </motion.button>
        )}
      </AnimatePresence>

      {/* Input Area - Disabled when offline without model or Data Saver */}
      <div className="flex-shrink-0 p-4 sm:p-6 border-t border-white/5">
        <ChatInputWithVoice
          onSendMessage={onSendMessage}
          onSendVoice={onSendVoice}
          disabled={isLoading || isSending || isInputDisabled || isLowBandwidth}
          placeholder={getPlaceholder()}
          enableTTS={enableTTS}
          isOffline={isInputDisabled}
          isUsingBrowserAI={!isOnline && isOfflineModelReady}
          isDataSaverMode={isLowBandwidth}
        />
      </div>
    </div>
  );
}
