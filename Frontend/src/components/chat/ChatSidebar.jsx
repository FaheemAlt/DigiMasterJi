import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Plus, 
  Search, 
  MessageSquare, 
  ChevronLeft,
  Clock,
  BookOpen,
  FlaskConical,
  Calculator,
  Atom,
  Trash2,
  MoreHorizontal,
} from 'lucide-react';

// Subject icons mapping
const subjectIcons = {
  'Biology': BookOpen,
  'Chemistry': FlaskConical,
  'Physics': Atom,
  'Math': Calculator,
  'Science': FlaskConical,
  default: MessageSquare,
};

/**
 * Parse timestamp ensuring UTC interpretation
 * Backend returns UTC timestamps without 'Z' suffix, so we need to handle that
 */
const parseUTCTimestamp = (timestamp) => {
  if (!timestamp) return null;
  // If timestamp doesn't end with Z or timezone offset, treat it as UTC
  if (typeof timestamp === 'string' && !timestamp.endsWith('Z') && !timestamp.match(/[+-]\d{2}:\d{2}$/)) {
    return new Date(timestamp + 'Z');
  }
  return new Date(timestamp);
};

/**
 * ChatSidebar Component
 * Shows conversation history with search and new chat button
 */
export default function ChatSidebar({
  conversations = [],
  activeConversationId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  isCollapsed = false,
  onToggleCollapse,
  isLoading = false,
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [hoveredId, setHoveredId] = useState(null);

  // Filter conversations by search query
  const filteredConversations = conversations.filter((conv) =>
    conv.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    conv.subject_tag?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Group conversations by date
  const groupedConversations = filteredConversations.reduce((groups, conv) => {
    const date = parseUTCTimestamp(conv.updated_at || conv.created_at);
    if (!date || isNaN(date.getTime())) {
      // Invalid date - put in 'Older' group
      if (!groups['Older']) groups['Older'] = [];
      groups['Older'].push(conv);
      return groups;
    }
    
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const lastWeek = new Date(today);
    lastWeek.setDate(lastWeek.getDate() - 7);

    let group;
    if (date.toDateString() === today.toDateString()) {
      group = 'Today';
    } else if (date.toDateString() === yesterday.toDateString()) {
      group = 'Yesterday';
    } else if (date > lastWeek) {
      group = 'This Week';
    } else {
      group = 'Older';
    }

    if (!groups[group]) groups[group] = [];
    groups[group].push(conv);
    return groups;
  }, {});

  // Format relative time (handles UTC timestamps from backend)
  const formatTime = (timestamp) => {
    if (!timestamp) return '';
    const date = parseUTCTimestamp(timestamp);
    if (!date || isNaN(date.getTime())) return '';
    
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return date.toLocaleDateString();
  };

  // Get icon for subject
  const getSubjectIcon = (subject) => {
    return subjectIcons[subject] || subjectIcons.default;
  };

  // Collapsed view
  if (isCollapsed) {
    return (
      <motion.div
        initial={{ width: 280 }}
        animate={{ width: 72 }}
        className="flex-shrink-0 h-full border-r border-white/10 bg-white/5 backdrop-blur-sm flex flex-col"
      >
        <div className="p-4 flex flex-col items-center gap-4">
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={onToggleCollapse}
            className="p-3 rounded-xl bg-white/10 text-white/70 hover:bg-white/20 hover:text-white transition-all"
          >
            <ChevronLeft className="w-5 h-5 rotate-180" />
          </motion.button>

          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={onNewConversation}
            className="p-3 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 text-white shadow-lg shadow-violet-500/30"
          >
            <Plus className="w-5 h-5" />
          </motion.button>
        </div>

        <div className="flex-1 overflow-y-auto py-2">
          {conversations.slice(0, 10).map((conv) => {
            const Icon = getSubjectIcon(conv.subject_tag);
            const isActive = conv._id === activeConversationId || conv.id === activeConversationId;
            
            return (
              <motion.button
                key={conv._id || conv.id}
                whileHover={{ scale: 1.05 }}
                onClick={() => onSelectConversation(conv)}
                className={`
                  w-full p-3 flex items-center justify-center
                  ${isActive 
                    ? 'bg-violet-500/20 text-violet-300' 
                    : 'text-white/60 hover:bg-white/10 hover:text-white'
                  }
                  transition-all
                `}
                title={conv.title}
              >
                <Icon className="w-5 h-5" />
              </motion.button>
            );
          })}
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ width: 72 }}
      animate={{ width: 280 }}
      className="flex-shrink-0 h-full border-r border-white/10 bg-white/5 backdrop-blur-sm flex flex-col"
    >
      {/* Header */}
      <div className="p-4 border-b border-white/10">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-violet-400" />
            <h2 className="font-semibold text-white">Chats</h2>
          </div>
          <button
            onClick={onToggleCollapse}
            className="p-2 rounded-lg text-white/40 hover:text-white/70 hover:bg-white/10 transition-all"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
        </div>

        {/* New Chat Button */}
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={onNewConversation}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 text-white font-medium shadow-lg shadow-violet-500/30 hover:from-violet-700 hover:to-indigo-700 transition-all"
        >
          <Plus className="w-5 h-5" />
          New Chat
        </motion.button>
      </div>

      {/* Search */}
      <div className="px-4 py-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
          <input
            type="text"
            placeholder="Search conversations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder-white/40 focus:outline-none focus:border-violet-500/50 focus:bg-white/10 transition-all"
          />
        </div>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto px-2 pb-4 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="w-8 h-8 border-2 border-violet-500/30 border-t-violet-500 rounded-full animate-spin" />
          </div>
        ) : filteredConversations.length === 0 ? (
          <div className="text-center py-12 px-4">
            <MessageSquare className="w-12 h-12 text-white/20 mx-auto mb-3" />
            <p className="text-white/40 text-sm">
              {searchQuery ? 'No matching conversations' : 'No conversations yet'}
            </p>
            <p className="text-white/30 text-xs mt-1">
              {searchQuery ? 'Try a different search' : 'Start a new chat to begin learning!'}
            </p>
          </div>
        ) : (
          Object.entries(groupedConversations).map(([group, convs]) => (
            <div key={group} className="mb-4">
              <div className="flex items-center gap-2 px-3 py-2">
                <Clock className="w-3 h-3 text-white/30" />
                <span className="text-xs font-medium text-white/40 uppercase tracking-wider">
                  {group}
                </span>
              </div>

              <AnimatePresence>
                {convs.map((conv) => {
                  const Icon = getSubjectIcon(conv.subject_tag);
                  const isActive = conv._id === activeConversationId || conv.id === activeConversationId;
                  const isHovered = hoveredId === (conv._id || conv.id);

                  return (
                    <motion.div
                      key={conv._id || conv.id}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -20 }}
                      onMouseEnter={() => setHoveredId(conv._id || conv.id)}
                      onMouseLeave={() => setHoveredId(null)}
                      className="relative"
                    >
                      <button
                        onClick={() => onSelectConversation(conv)}
                        className={`
                          w-full flex items-start gap-3 px-3 py-3 rounded-xl
                          text-left transition-all duration-200
                          ${isActive 
                            ? 'bg-violet-500/20 border border-violet-500/30' 
                            : 'hover:bg-white/10 border border-transparent'
                          }
                        `}
                      >
                        {/* Icon */}
                        <div className={`
                          flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center
                          ${isActive 
                            ? 'bg-violet-500/30 text-violet-300' 
                            : 'bg-white/10 text-white/60'
                          }
                        `}>
                          <Icon className="w-4 h-4" />
                        </div>

                        {/* Content */}
                        <div className="flex-1 min-w-0">
                          <h3 className={`font-medium text-sm truncate ${isActive ? 'text-white' : 'text-white/80'}`}>
                            {conv.title || 'New Conversation'}
                          </h3>
                          <div className="flex items-center gap-2 mt-0.5">
                            {conv.subject_tag && (
                              <span className="text-xs text-violet-400/70">
                                {conv.subject_tag}
                              </span>
                            )}
                            <span className="text-xs text-white/30">
                              {formatTime(conv.updated_at || conv.created_at)}
                            </span>
                          </div>
                          {conv.message_count > 0 && (
                            <span className="text-xs text-white/30">
                              {conv.message_count} message{conv.message_count !== 1 ? 's' : ''}
                            </span>
                          )}
                        </div>
                      </button>

                      {/* Delete button on hover */}
                      {isHovered && onDeleteConversation && (
                        <motion.button
                          initial={{ opacity: 0, scale: 0.8 }}
                          animate={{ opacity: 1, scale: 1 }}
                          onClick={(e) => {
                            e.stopPropagation();
                            onDeleteConversation(conv);
                          }}
                          className="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-lg bg-rose-500/20 text-rose-400 hover:bg-rose-500/30 transition-all"
                        >
                          <Trash2 className="w-4 h-4" />
                        </motion.button>
                      )}
                    </motion.div>
                  );
                })}
              </AnimatePresence>
            </div>
          ))
        )}
      </div>
    </motion.div>
  );
}
