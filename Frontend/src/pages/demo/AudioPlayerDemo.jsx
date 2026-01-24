import { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  ArrowLeft, 
  Sparkles, 
  Volume2,
  Play,
  Music,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { AudioPlayer, MessageBubble, AudioMessageBubble } from '../../components/chat';
import { Button } from '../../components/ui';

// Sample audio for testing (a short beep sound in base64)
// In production, this would come from the TTS backend
const SAMPLE_AUDIO_BASE64 = null; // Will show loading state if null

// Mock messages with audio for demonstration
const MOCK_MESSAGES_WITH_AUDIO = [
  {
    _id: 'demo-1',
    role: 'user',
    content: 'Photosynthesis kya hai?',
    timestamp: new Date().toISOString(),
  },
  {
    _id: 'demo-2',
    role: 'assistant',
    content: 'Photosynthesis ek aisa process hai jisme paudhe sunlight ka upyog karke apna khana banate hain! 🌱\n\nIsse simple shabdon mein samjhein:\n\n1. **Sunlight** - Paudhe apni pattiyon se sunlight absorb karte hain\n2. **Carbon Dioxide** - Hawa se CO2 lete hain\n3. **Water** - Jaddon se paani absorb karte hain',
    timestamp: new Date().toISOString(),
    // audio_base64 would come from TTS service
    // audio_url: 'https://example.com/audio.mp3',
  },
  {
    _id: 'demo-3',
    role: 'user',
    content: '',
    timestamp: new Date().toISOString(),
    is_voice_message: true,
    audio_url: 'https://www.soundjay.com/misc/sounds/bell-ringing-05.mp3', // Demo audio
  },
  {
    _id: 'demo-4',
    role: 'assistant',
    content: 'Maine aapki awaaz sun li! Aap chlorophyll ke baare mein pooch rahe hain.',
    timestamp: new Date().toISOString(),
    audio_url: 'https://www.soundjay.com/misc/sounds/bell-ringing-05.mp3', // Demo audio
  },
];

/**
 * AudioPlayerDemo Page
 * Demonstrates the audio player components for testing and preview
 */
export default function AudioPlayerDemo() {
  const navigate = useNavigate();
  const [activeDemo, setActiveDemo] = useState('player');

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-violet-950 to-slate-950 relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <motion.div
          animate={{ x: [0, 50, 0], y: [0, -30, 0] }}
          transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
          className="absolute -top-40 -left-40 w-[400px] h-[400px] bg-violet-600/10 rounded-full blur-3xl"
        />
        <motion.div
          animate={{ x: [0, -30, 0], y: [0, 50, 0] }}
          transition={{ duration: 25, repeat: Infinity, ease: 'linear' }}
          className="absolute -bottom-40 -right-40 w-[400px] h-[400px] bg-indigo-600/10 rounded-full blur-3xl"
        />
      </div>

      {/* Header */}
      <header className="relative z-10 flex items-center gap-4 p-6 border-b border-white/10">
        <Button
          variant="ghost"
          size="sm"
          icon={ArrowLeft}
          onClick={() => navigate(-1)}
        >
          Back
        </Button>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center">
            <Volume2 className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">Audio Player Demo</h1>
            <p className="text-sm text-white/50">Sprint 3 - Voice Layer UI</p>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="relative z-10 max-w-4xl mx-auto p-6 space-y-8">
        {/* Demo Selector */}
        <div className="flex gap-2 flex-wrap">
          {[
            { id: 'player', label: 'Standalone Player', icon: Play },
            { id: 'messages', label: 'Message Bubbles', icon: Music },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveDemo(tab.id)}
              className={`
                flex items-center gap-2 px-4 py-2 rounded-xl transition-all
                ${activeDemo === tab.id
                  ? 'bg-violet-600 text-white'
                  : 'bg-white/10 text-white/60 hover:bg-white/20 hover:text-white'
                }
              `}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Standalone Player Demo */}
        {activeDemo === 'player' && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            <div className="p-6 rounded-2xl bg-white/5 border border-white/10">
              <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-violet-400" />
                Full Audio Player
              </h2>
              <p className="text-sm text-white/60 mb-4">
                This player shows the full waveform visualization with all controls.
                It's used for detailed audio playback.
              </p>
              
              {/* Note: In real usage, this would have an actual audio URL */}
              <div className="bg-white/5 rounded-xl p-4">
                <p className="text-sm text-white/50 text-center py-4">
                  Audio player will display when audio URL/base64 is provided from TTS service.
                  <br />
                  <span className="text-violet-400">FE-B will connect this to the chat API response.</span>
                </p>
              </div>
            </div>

            <div className="p-6 rounded-2xl bg-white/5 border border-white/10">
              <h2 className="text-lg font-semibold text-white mb-4">
                Compact Audio Player
              </h2>
              <p className="text-sm text-white/60 mb-4">
                A smaller inline player for embedding within message bubbles.
              </p>
              
              <div className="bg-white/5 rounded-xl p-4 max-w-xs">
                <p className="text-sm text-white/50 text-center py-2">
                  Compact player preview
                </p>
              </div>
            </div>

            {/* Features List */}
            <div className="p-6 rounded-2xl bg-white/5 border border-white/10">
              <h2 className="text-lg font-semibold text-white mb-4">
                AudioPlayer Features
              </h2>
              <ul className="space-y-2 text-sm text-white/70">
                <li className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  Interactive waveform visualization (wavesurfer.js)
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  Play/Pause controls with animated button
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  Click-to-seek on waveform
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  Time display (current / total duration)
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  Mute/unmute toggle
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  Restart button
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  Supports URL and Base64 audio sources
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  Loading state with animated bars
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  Error handling with user feedback
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  Compact mode for inline use
                </li>
              </ul>
            </div>
          </motion.div>
        )}

        {/* Message Bubbles Demo */}
        {activeDemo === 'messages' && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            <div className="p-6 rounded-2xl bg-white/5 border border-white/10">
              <h2 className="text-lg font-semibold text-white mb-4">
                Messages with Audio Integration
              </h2>
              <p className="text-sm text-white/60 mb-6">
                When messages have audio (TTS response), the player is embedded in the bubble.
              </p>

              {/* Demo Messages */}
              <div className="space-y-4 p-4 rounded-xl bg-slate-900/50 max-h-[500px] overflow-y-auto">
                {MOCK_MESSAGES_WITH_AUDIO.map((message, index) => (
                  <div key={message._id} className="group">
                    {message.is_voice_message && (message.audio_url || message.audio_base64) ? (
                      <AudioMessageBubble
                        message={message}
                        isUser={message.role === 'user'}
                        showAvatar={
                          index === 0 ||
                          MOCK_MESSAGES_WITH_AUDIO[index - 1]?.role !== message.role
                        }
                      />
                    ) : (
                      <MessageBubble
                        message={message}
                        isUser={message.role === 'user'}
                        showAvatar={
                          index === 0 ||
                          MOCK_MESSAGES_WITH_AUDIO[index - 1]?.role !== message.role
                        }
                      />
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Integration Notes */}
            <div className="p-6 rounded-2xl bg-amber-500/10 border border-amber-500/20">
              <h2 className="text-lg font-semibold text-amber-400 mb-2">
                Integration Notes for FE-B
              </h2>
              <ul className="space-y-2 text-sm text-white/70">
                <li>• When backend returns <code className="text-violet-400">audio_base64</code> in message response, pass it to MessageBubble</li>
                <li>• Set <code className="text-violet-400">is_voice_message: true</code> for voice recordings</li>
                <li>• The player automatically handles MP3 format from gTTS</li>
                <li>• For voice recordings, use AudioMessageBubble component</li>
              </ul>
            </div>
          </motion.div>
        )}
      </main>
    </div>
  );
}
