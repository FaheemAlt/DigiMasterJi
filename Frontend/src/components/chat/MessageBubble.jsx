import { motion } from 'framer-motion';
import { Bot, User, Copy, Check, Volume2, VolumeX, Image, FileText } from 'lucide-react';
import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import AudioPlayer from './AudioPlayer';

/**
 * DiagramRenderer Component
 * Renders SVG diagrams or ASCII art for visual explanations
 */
function DiagramRenderer({ diagram }) {
  const [expanded, setExpanded] = useState(true); // Default to expanded for better visibility

  if (!diagram || !diagram.content) return null;

  const isSvg = diagram.type === 'svg';
  const sizeKb = diagram.size_bytes ? (diagram.size_bytes / 1024).toFixed(1) : null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2, duration: 0.3 }}
      className="mt-4 pt-4 border-t border-white/10"
    >
      {/* Diagram Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 text-sm text-white/70">
          {isSvg ? (
            <Image className="w-4 h-4 text-emerald-400" />
          ) : (
            <FileText className="w-4 h-4 text-amber-400" />
          )}
          <span className="font-medium">
            {diagram.title || (isSvg ? '📊 Visual Diagram' : '📝 ASCII Diagram')}
          </span>
          {sizeKb && (
            <span className="text-white/40 text-xs">({sizeKb} KB)</span>
          )}
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs px-2 py-1 rounded-md bg-white/10 text-white/50 hover:text-white/80 hover:bg-white/20 transition-colors"
        >
          {expanded ? '⬆ Collapse' : '⬇ Expand'}
        </button>
      </div>

      {/* Diagram Content */}
      <motion.div
        initial={false}
        animate={{
          height: expanded ? 'auto' : '100px',
          opacity: expanded ? 1 : 0.7
        }}
        transition={{ duration: 0.3 }}
        className="overflow-hidden rounded-xl"
      >
        {isSvg ? (
          // SVG Diagram - render inline with better sizing
          <div
            className="bg-slate-900/60 rounded-xl p-4 overflow-auto border border-white/5"
            dangerouslySetInnerHTML={{ __html: diagram.content }}
            style={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'flex-start',
              minHeight: expanded ? '200px' : '100px',
              maxHeight: expanded ? '800px' : '100px',
            }}
          />
        ) : (
          // ASCII Art - render in pre tag with better styling
          <pre
            className="bg-slate-900/60 rounded-xl p-4 text-sm font-mono text-emerald-300 overflow-auto whitespace-pre border border-white/5"
            style={{
              lineHeight: '1.4',
              letterSpacing: '0.02em',
              minHeight: expanded ? '150px' : '100px',
              maxHeight: expanded ? '600px' : '100px',
            }}
          >
            {diagram.content}
          </pre>
        )}
      </motion.div>

      {/* Diagram Type Badge */}
      {diagram.diagram_type && (
        <div className="mt-3 flex items-center gap-2">
          <span className={`
            text-xs px-3 py-1 rounded-full font-medium
            ${isSvg
              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
              : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
            }
          `}>
            {diagram.diagram_type.replace('_', ' ').toUpperCase()}
          </span>
          <span className="text-xs text-white/40">
            {isSvg ? 'Interactive visual' : 'Low-bandwidth mode'}
          </span>
        </div>
      )}
    </motion.div>
  );
}

/**
 * MessageBubble Component
 * Displays individual chat messages with different styles for user/assistant
 * Includes integrated audio player for TTS responses
 */
export default function MessageBubble({
  message,
  isUser = false,
  isTyping = false,
  showAvatar = true,
  onPlayAudio,
  showAudioPlayer = true, // Show inline audio player for messages with audio
}) {
  const [copied, setCopied] = useState(false);
  const [audioExpanded, setAudioExpanded] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  // Format timestamp (handles UTC timestamps from backend)
  const formatTime = (timestamp) => {
    if (!timestamp) return '';
    // If timestamp doesn't end with Z or timezone offset, treat it as UTC
    let dateStr = timestamp;
    if (typeof timestamp === 'string' && !timestamp.endsWith('Z') && !timestamp.match(/[+-]\d{2}:\d{2}$/)) {
      dateStr = timestamp + 'Z';
    }
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return '';

    return date.toLocaleTimeString('en-IN', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
      timeZone: 'Asia/Kolkata'
    });
  };

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
            <User className="w-5 h-5 text-white" />
          ) : (
            <Bot className="w-5 h-5 text-white" />
          )}
        </motion.div>
      )}

      {/* Message Content */}
      <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} max-w-[70%]`}>
        {/* Bubble */}
        <div
          className={`
            relative px-4 py-3 rounded-2xl
            ${isUser
              ? 'bg-gradient-to-br from-violet-600 to-indigo-600 text-white rounded-tr-sm'
              : 'bg-white/10 backdrop-blur-sm border border-white/10 text-white rounded-tl-sm'
            }
          `}
        >
          {/* Typing Indicator */}
          {isTyping ? (
            <div className="flex items-center gap-1 py-1 px-2">
              <motion.span
                animate={{ opacity: [0.4, 1, 0.4] }}
                transition={{ duration: 1, repeat: Infinity, delay: 0 }}
                className="w-2 h-2 bg-white/70 rounded-full"
              />
              <motion.span
                animate={{ opacity: [0.4, 1, 0.4] }}
                transition={{ duration: 1, repeat: Infinity, delay: 0.2 }}
                className="w-2 h-2 bg-white/70 rounded-full"
              />
              <motion.span
                animate={{ opacity: [0.4, 1, 0.4] }}
                transition={{ duration: 1, repeat: Infinity, delay: 0.4 }}
                className="w-2 h-2 bg-white/70 rounded-full"
              />
            </div>
          ) : (
            <div className="text-sm sm:text-base leading-relaxed prose prose-invert prose-sm max-w-none">
              <ReactMarkdown
                components={{
                  // Style paragraphs
                  p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                  // Style bold text
                  strong: ({ children }) => <strong className="font-bold text-white">{children}</strong>,
                  // Style italic text
                  em: ({ children }) => <em className="italic">{children}</em>,
                  // Style unordered lists
                  ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>,
                  // Style ordered lists
                  ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>,
                  // Style list items
                  li: ({ children }) => <li className="text-white/90">{children}</li>,
                  // Style headings
                  h1: ({ children }) => <h1 className="text-lg font-bold mb-2">{children}</h1>,
                  h2: ({ children }) => <h2 className="text-base font-bold mb-2">{children}</h2>,
                  h3: ({ children }) => <h3 className="text-sm font-bold mb-1">{children}</h3>,
                  // Style code
                  code: ({ children }) => <code className="bg-white/10 px-1 py-0.5 rounded text-xs">{children}</code>,
                  // Style code blocks
                  pre: ({ children }) => <pre className="bg-white/10 p-2 rounded-lg overflow-x-auto mb-2">{children}</pre>,
                  // Style blockquotes
                  blockquote: ({ children }) => <blockquote className="border-l-2 border-white/30 pl-3 italic text-white/80">{children}</blockquote>,
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}

          {/* Translated Content (if available) */}
          {message.content_translated && !isTyping && (
            <div className="mt-2 pt-2 border-t border-white/10">
              <p className="text-xs text-white/60 italic">
                {message.content_translated}
              </p>
            </div>
          )}

          {/* Diagram (SVG or ASCII art) - for visual learning */}
          {!isUser && !isTyping && message.diagram && (
            <DiagramRenderer diagram={message.diagram} />
          )}
        </div>

        {/* Audio Player - Show for assistant messages with audio */}
        {!isUser && !isTyping && (message.audio_url || message.audio_base64) && showAudioPlayer && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{
              opacity: audioExpanded ? 1 : 0.9,
              height: 'auto'
            }}
            className="mt-2 w-full max-w-full overflow-hidden"
            style={{ contain: 'layout' }}
          >
            {audioExpanded ? (
              // Expanded full player
              <div className="w-full overflow-hidden">
                <AudioPlayer
                  audioUrl={message.audio_url}
                  audioBase64={message.audio_base64}
                  format={message.audio_format || 'mp3'}
                  accentColor="emerald"
                />
              </div>
            ) : (
              // Compact inline player
              <div className="w-full overflow-hidden">
                <AudioPlayer
                  audioUrl={message.audio_url}
                  audioBase64={message.audio_base64}
                  format={message.audio_format || 'mp3'}
                  compact={true}
                  accentColor="emerald"
                />
              </div>
            )}

            {/* Toggle expand button */}
            {/* <button
              onClick={() => setAudioExpanded(!audioExpanded)}
              className="mt-1 text-xs text-white/40 hover:text-white/60 transition-colors"
            >
              {audioExpanded ? 'Collapse' : 'Expand'}
            </button> */}
          </motion.div>
        )}

        {/* Audio Loading Indicator - Show while TTS is being generated */}
        {!isUser && !isTyping && message.isLoadingAudio && !message.audio_base64 && showAudioPlayer && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-2 flex items-center gap-2 text-sm text-white/60"
          >
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
              <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }} />
              <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }} />
            </div>
            <span>Generating audio...</span>
          </motion.div>
        )}

        {/* Message Meta & Actions */}
        {!isTyping && (
          <div className={`flex items-center gap-2 mt-1 px-1 ${isUser ? 'flex-row-reverse' : ''}`}>
            <span className="text-xs text-white/40">
              {formatTime(message.timestamp)}
            </span>

            {/* Action Buttons (only for assistant messages) */}
            {!isUser && (
              <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  onClick={handleCopy}
                  className="p-1 rounded-lg hover:bg-white/10 transition-colors"
                  title="Copy message"
                >
                  {copied ? (
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <Copy className="w-3.5 h-3.5 text-white/40 hover:text-white/70" />
                  )}
                </button>

                {/* Audio toggle button (if audio available but player hidden) */}
                {(message.audio_url || message.audio_base64) && !showAudioPlayer && onPlayAudio && (
                  <button
                    onClick={() => onPlayAudio(message.audio_url || message.audio_base64)}
                    className="p-1 rounded-lg hover:bg-white/10 transition-colors"
                    title="Play audio"
                  >
                    <Volume2 className="w-3.5 h-3.5 text-white/40 hover:text-white/70" />
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </motion.div>
  );
}
