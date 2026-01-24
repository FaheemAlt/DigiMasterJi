import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Menu, 
  X, 
  ArrowLeft, 
  Sparkles,
  User,
  AlertCircle,
  RefreshCw,
  Trophy,
  BookOpen,
} from 'lucide-react';
import { ChatSidebar, ChatWindow } from '../../components/chat';
import { NetworkStatusBadge, OfflineBanner, LowBandwidthToggle, useLowBandwidthMode } from '../../components/ui';
import { useProfile } from '../../hooks/useProfile';
import { useChatService } from '../../hooks/useChatService';
import { useNetworkStatus } from '../../contexts/NetworkStatusContext';

/**
 * ChatPage Component
 * Main chat interface with sidebar and chat window
 * Connected to real API via useChatService hook
 * Supports text input, voice recording (STT), and audio responses (TTS)
 */
export default function ChatPage() {
  const navigate = useNavigate();
  const { activeProfile, isProfileSessionValid, deactivateProfile } = useProfile();
  const { isOnline, isSyncing } = useNetworkStatus();
  
  // Low bandwidth mode for diagram generation (ASCII instead of SVG)
  const { isLowBandwidth } = useLowBandwidthMode();
  
  // Chat service hook - manages all chat state and API calls
  const {
    conversations,
    activeConversation,
    messages,
    error,
    isLoadingConversations,
    isLoadingMessages,
    isSendingMessage,
    isTyping,
    fetchConversations,
    createConversation,
    selectConversation,
    sendMessage,
    sendMessageStream,
    sendVoiceMessage,
    deleteConversation,
    clearActiveConversation,
    clearError,
    resetChatState,
  } = useChatService();

  // UI state
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [sessionChecked, setSessionChecked] = useState(false);
  const [enableTTS, setEnableTTS] = useState(true); // TTS preference
  
  // Ref to track if we've initiated a fetch for this mount
  const fetchInitiatedRef = useRef(false);

  // Check if profile session is valid on mount only
  useEffect(() => {
    const checkSession = () => {
      if (!isProfileSessionValid()) {
        navigate('/profiles', { replace: true });
      } else {
        setSessionChecked(true);
      }
    };
    checkSession();
    // Only run once on mount
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Fetch conversations ONCE on mount (after session check)
  useEffect(() => {
    // Only fetch once per component mount
    if (fetchInitiatedRef.current) {
      return;
    }
    
    // Wait for session check and profile to be ready
    if (!sessionChecked || !activeProfile) {
      return;
    }
    
    const currentProfileId = activeProfile._id || activeProfile.id;
    
    // Mark that we've initiated a fetch - do this IMMEDIATELY
    fetchInitiatedRef.current = true;
    
    // Fetch conversations
    fetchConversations(currentProfileId);
    
  }, [sessionChecked, activeProfile, fetchConversations]);

  // Handle selecting a conversation
  const handleSelectConversation = (conv) => {
    selectConversation(conv);
    setIsMobileSidebarOpen(false);
  };

  // Handle creating a new conversation
  const handleNewConversation = async () => {
    clearActiveConversation();
    setIsMobileSidebarOpen(false);
  };

  // Handle going back to profile selection - deactivate profile first to ensure clean state
  const handleBackToProfiles = () => {
    // Reset chat state to prevent showing old profile's chats on next profile
    resetChatState();
    deactivateProfile();
    navigate('/profiles');
  };

  // Handle sending a message (with streaming)
  const handleSendMessage = async (content, options = {}) => {
    if (!content?.trim()) return;
    try {
      // Pass profileId for creating new conversations
      const profileId = activeProfile?._id || activeProfile?.id;
      // Include TTS preference in the message
      const includeAudio = options.includeAudio !== undefined ? options.includeAudio : enableTTS;
      // Use streaming by default for real-time token display
      // Pass lowBandwidth flag for ASCII diagrams instead of SVG when data saver is on
      await sendMessageStream(content, profileId, { 
        includeAudio,
        lowBandwidth: isLowBandwidth,
        includeDiagram: true, // Always request diagrams when appropriate
      });
    } catch (err) {
      console.error('Error sending message:', err);
    }
  };

  // Handle sending a voice message (STT -> AI -> TTS)
  const handleSendVoice = async (audioBlob, options = {}) => {
    if (!audioBlob) return;
    try {
      const profileId = activeProfile?._id || activeProfile?.id;
      // Include TTS preference in the voice message
      const includeAudio = options.includeAudio !== undefined ? options.includeAudio : enableTTS;
      await sendVoiceMessage(audioBlob, profileId, {
        autoSend: true,
        includeAudio,
        slowAudio: false,
        lowBandwidth: isLowBandwidth,
        includeDiagram: true,
      });
    } catch (err) {
      console.error('Error sending voice message:', err);
    }
  };

  // Handle delete conversation
  const handleDeleteConversation = async (conv) => {
    try {
      await deleteConversation(conv);
    } catch (err) {
      console.error('Error deleting conversation:', err);
    }
  };

  // Handle retry on error
  const handleRetry = () => {
    clearError();
    const profileId = activeProfile?._id || activeProfile?.id;
    fetchConversations(profileId);
  };

  // Show loading until session is checked
  if (!sessionChecked) {
    return (
      <div className="h-screen bg-gradient-to-br from-slate-950 via-violet-950 to-slate-950 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-violet-500/30 border-t-violet-500 rounded-full animate-spin" />
          <p className="text-white/60">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen bg-gradient-to-br from-slate-950 via-violet-950 to-slate-950 flex overflow-hidden">
      {/* Animated Background */}
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

      {/* Mobile Header */}
      <div className="absolute top-0 left-0 right-0 z-30 lg:hidden">
        {/* Offline Banner - Shows when offline or syncing */}
        <OfflineBanner />
        
        <div className="flex items-center justify-between p-4 bg-slate-950/80 backdrop-blur-sm border-b border-white/10">
          <button
            onClick={() => setIsMobileSidebarOpen(true)}
            className="p-2 rounded-xl bg-white/10 text-white"
          >
            <Menu className="w-5 h-5" />
          </button>

          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-violet-400" />
            <span className="font-semibold text-white">DigiMasterJi</span>
            {/* Network Status Badge - Mobile */}
            <NetworkStatusBadge variant="minimal" size="sm" />
          </div>

          <div className="flex items-center gap-2">
            {/* Quiz Button - Mobile */}
            <button
              onClick={() => navigate('/quiz')}
              className="p-2 rounded-xl bg-violet-500/20 text-violet-400 hover:bg-violet-500/30 transition-colors"
              title="Daily Quiz"
            >
              <BookOpen className="w-5 h-5" />
            </button>
            
            {/* Progress Button - Mobile */}
            <button
              onClick={() => navigate('/progress')}
              className="p-2 rounded-xl bg-amber-500/20 text-amber-400 hover:bg-amber-500/30 transition-colors"
              title="My Progress"
            >
              <Trophy className="w-5 h-5" />
            </button>
            
            {/* Low Bandwidth Toggle - Mobile */}
            <LowBandwidthToggle size="sm" showTooltip={false} />
            
            <button
              onClick={handleBackToProfiles}
              className="p-2 rounded-xl bg-white/10 text-white"
            >
              <User className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Sidebar Overlay */}
      <AnimatePresence>
        {isMobileSidebarOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsMobileSidebarOpen(false)}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
            />
            <motion.div
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="fixed left-0 top-0 bottom-0 z-50 lg:hidden"
            >
              <div className="relative h-full">
                <button
                  onClick={() => setIsMobileSidebarOpen(false)}
                  className="absolute top-4 right-4 p-2 rounded-xl bg-white/10 text-white z-10"
                >
                  <X className="w-5 h-5" />
                </button>
                <ChatSidebar
                  conversations={conversations}
                  activeConversationId={activeConversation?._id || activeConversation?.id}
                  onSelectConversation={handleSelectConversation}
                  onNewConversation={handleNewConversation}
                  onDeleteConversation={handleDeleteConversation}
                  isCollapsed={false}
                />
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Desktop Sidebar */}
      <div className="hidden lg:block relative z-10">
        <ChatSidebar
          conversations={conversations}
          activeConversationId={activeConversation?._id || activeConversation?.id}
          onSelectConversation={handleSelectConversation}
          onNewConversation={handleNewConversation}
          onDeleteConversation={handleDeleteConversation}
          isCollapsed={isSidebarCollapsed}
          onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
          isLoading={isLoadingConversations}
        />
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col relative z-10 pt-16 lg:pt-0">
        {/* Error Banner */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="absolute top-16 lg:top-0 left-0 right-0 z-20 p-3 bg-red-500/20 border-b border-red-500/30 backdrop-blur-sm"
            >
              <div className="flex items-center justify-between max-w-4xl mx-auto">
                <div className="flex items-center gap-2 text-red-200">
                  <AlertCircle className="w-4 h-4" />
                  <span className="text-sm">{error}</span>
                </div>
                <button
                  onClick={handleRetry}
                  className="flex items-center gap-1 px-3 py-1 rounded-lg bg-red-500/30 hover:bg-red-500/50 text-red-200 text-sm transition-colors"
                >
                  <RefreshCw className="w-3 h-3" />
                  Retry
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Desktop Header */}
        <div className="hidden lg:flex items-center justify-between px-6 py-4 border-b border-white/10 bg-white/5 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <button
              onClick={handleBackToProfiles}
              className="p-2 rounded-xl hover:bg-white/10 transition-colors"
            >
              <ArrowLeft className="w-5 h-5 text-white/60" />
            </button>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center">
                <Sparkles className="w-4 h-4 text-white" />
              </div>
              <div>
                <h1 className="font-semibold text-white">DigiMasterJi</h1>
                <p className="text-xs text-white/50">AI Tutor</p>
              </div>
            </div>
            {/* Network Status Badge - Desktop */}
            <NetworkStatusBadge variant="pill" size="sm" />
          </div>

          {activeProfile && (
            <div className="flex items-center gap-4">
              {/* Quiz Button - Desktop */}
              <button
                onClick={() => navigate('/quiz')}
                className="flex items-center gap-2 px-3 py-2 rounded-xl bg-violet-500/20 text-violet-400 hover:bg-violet-500/30 transition-colors"
                title="Daily Quiz"
              >
                <BookOpen className="w-4 h-4" />
                <span className="text-sm font-medium">Quiz</span>
              </button>
              
              {/* Progress Button - Desktop */}
              <button
                onClick={() => navigate('/progress')}
                className="flex items-center gap-2 px-3 py-2 rounded-xl bg-amber-500/20 text-amber-400 hover:bg-amber-500/30 transition-colors"
                title="My Progress"
              >
                <Trophy className="w-4 h-4" />
                <span className="text-sm font-medium">Progress</span>
              </button>
              
              {/* Low Bandwidth Toggle - Desktop */}
              <LowBandwidthToggle size="md" showTooltip={true} />
              
              <span className="text-sm text-white/60">
                Learning as <span className="text-violet-400 font-medium">{activeProfile.name}</span>
              </span>
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-orange-400 to-rose-500 flex items-center justify-center">
                <span className="text-sm">🦊</span>
              </div>
            </div>
          )}
        </div>

        {/* Chat Window */}
        <ChatWindow
          conversation={activeConversation}
          messages={messages}
          isLoading={isLoadingMessages}
          isTyping={isTyping}
          isSending={isSendingMessage}
          onSendMessage={handleSendMessage}
          onSendVoice={handleSendVoice}
          activeProfile={activeProfile}
          enableTTS={enableTTS}
        />
      </div>
    </div>
  );
}
