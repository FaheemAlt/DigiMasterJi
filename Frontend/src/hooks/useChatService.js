import { useState, useCallback, useRef, useEffect } from 'react';
import { chatApi } from '../api/chat';
import { syncService } from '../services/syncService';

/**
 * Generate a conversation title from the first message content.
 * Takes the first meaningful words and creates a concise title.
 * @param {string} content - The first message content
 * @returns {string} - Generated title
 */
const generateTitleFromMessage = (content) => {
  if (!content) return 'New Chat';

  // Clean the content
  let title = content.trim();

  // Remove common question starters for cleaner titles
  const startersToRemove = [
    /^(hi|hello|hey|namaste|namaskar)[,!.]?\s*/i,
    /^(can you|could you|would you|please|pls)\s*/i,
    /^(tell me|explain|describe|help me|show me)\s*(about|with)?\s*/i,
    /^(what is|what are|what's|whats)\s*/i,
    /^(how to|how do|how can|how does)\s*/i,
    /^(why is|why are|why do|why does)\s*/i,
    /^(i want to|i need to|i'd like to)\s*/i,
    /^(mujhe|mujhko|batao|bataiye|samjhao)\s*/i,
  ];

  for (const pattern of startersToRemove) {
    title = title.replace(pattern, '');
  }

  // Capitalize first letter
  title = title.charAt(0).toUpperCase() + title.slice(1);

  // Truncate to reasonable length (max 50 chars)
  if (title.length > 50) {
    // Try to cut at a word boundary
    title = title.substring(0, 47);
    const lastSpace = title.lastIndexOf(' ');
    if (lastSpace > 30) {
      title = title.substring(0, lastSpace);
    }
    title += '...';
  }

  // Remove trailing punctuation except ...
  title = title.replace(/[?,!;:]+$/, '');

  return title || 'New Chat';
};

/**
 * useChatService Hook
 * Manages chat state and API interactions for the chat feature.
 * Handles conversations, messages, loading states, and error handling.
 */
export function useChatService() {
  // Conversations state
  const [conversations, setConversations] = useState([]);
  const [activeConversation, setActiveConversation] = useState(null);
  const [messages, setMessages] = useState([]);

  // Loading states
  const [isLoadingConversations, setIsLoadingConversations] = useState(false);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [isSendingMessage, setIsSendingMessage] = useState(false);
  const [isTyping, setIsTyping] = useState(false);

  // Error state
  const [error, setError] = useState(null);

  // Offline mode state
  const [isOfflineModelAvailable, setIsOfflineModelAvailable] = useState(false);
  const [isUsingOfflineModel, setIsUsingOfflineModel] = useState(false);
  const [offlineModelName, setOfflineModelName] = useState(null);

  // Ref to track if initial load has happened
  const initialLoadDone = useRef(false);

  /**
   * Check if offline local model is available
   * Caches the result for performance
   */
  const checkOfflineModelAvailability = useCallback(async () => {
    try {
      const response = await chatApi.getOfflineStatus();
      const { offline_available, model } = response.data;
      setIsOfflineModelAvailable(offline_available);
      setOfflineModelName(model || null);
      return offline_available;
    } catch (err) {
      console.log('[Chat] Offline model not available:', err.message);
      setIsOfflineModelAvailable(false);
      setOfflineModelName(null);
      return false;
    }
  }, []);

  // Check offline model availability on mount (only when online to avoid 401 issues)
  useEffect(() => {
    // Don't make API calls when offline - this prevents auth failure triggers
    if (navigator.onLine) {
      checkOfflineModelAvailability();
    }
  }, [checkOfflineModelAvailability]);

  /**
   * Fetch all conversations for the current profile
   * Supports offline-first: tries API first, falls back to local IndexedDB
   * @param {string} profileId - Profile ID to filter conversations (required for offline)
   * @param {number} limit - Max conversations to fetch
   * @param {number} offset - Pagination offset
   */
  const fetchConversations = useCallback(async (profileId = null, limit = 50, offset = 0) => {
    setIsLoadingConversations(true);
    setError(null);

    const isOnline = navigator.onLine;

    try {
      if (isOnline) {
        // Online: try API first
        try {
          const response = await chatApi.getSessions({ limit, offset });
          const convs = response.data || [];
          setConversations(convs);
          initialLoadDone.current = true;
          return convs;
        } catch (apiErr) {
          // Network error - fall through to local storage
          if (apiErr.code !== 'ERR_NETWORK' && apiErr.message !== 'Network Error') {
            console.error('[Chat] API error (non-network):', apiErr);
            throw apiErr;
          }
        }
      }

      // Offline or network error: load from local IndexedDB
      console.log('[Chat] Loading conversations from local storage for profile:', profileId);
      const localConvs = await syncService.getLocalConversations(profileId);
      setConversations(localConvs);
      initialLoadDone.current = true;
      return localConvs;
    } catch (err) {
      console.error('Failed to fetch conversations:', err);

      // Last resort: try local storage
      if (profileId) {
        try {
          console.log('[Chat] Final fallback - loading from local storage');
          const localConvs = await syncService.getLocalConversations(profileId);
          if (localConvs.length > 0) {
            setConversations(localConvs);
            initialLoadDone.current = true;
            return localConvs;
          }
        } catch (localErr) {
          console.error('Failed to load from local storage:', localErr);
        }
      }

      setError(err.response?.data?.detail || 'Failed to load conversations');
      return [];
    } finally {
      setIsLoadingConversations(false);
    }
  }, []);

  /**
   * Create a new conversation
   * @param {string} profileId - The profile ID (required by backend)
   * @param {string} topic - Optional topic for the conversation
   */
  const createConversation = useCallback(async (profileId, topic = null) => {
    setError(null);

    if (!profileId) {
      setError('Profile ID is required to create a conversation');
      throw new Error('Profile ID is required');
    }

    // Check if offline - can't create conversations offline
    if (!navigator.onLine) {
      setError('Cannot create new conversations while offline');
      throw new Error('Cannot create new conversations while offline');
    }

    try {
      // Backend expects: { profile_id, topic? }
      const response = await chatApi.startSession({ profile_id: profileId, topic });
      const newConv = response.data;

      // Add to conversations list at the top
      setConversations((prev) => [newConv, ...prev]);
      setActiveConversation(newConv);
      setMessages([]);

      // Store locally for offline access (non-blocking)
      syncService.addLocalConversation(newConv).catch(console.error);

      return newConv;
    } catch (err) {
      console.error('Failed to create conversation:', err);
      setError(err.response?.data?.detail || 'Failed to create conversation');
      throw err;
    }
  }, []);

  /**
   * Select a conversation and load its messages
   * Supports offline-first: tries API first, falls back to local IndexedDB
   * @param {Object} conversation - The conversation to select
   */
  const selectConversation = useCallback(async (conversation) => {
    const convId = conversation._id || conversation.id;

    setActiveConversation(conversation);
    setIsLoadingMessages(true);
    setError(null);

    const isOnline = navigator.onLine;

    try {
      if (isOnline) {
        // Online: fetch from API
        const response = await chatApi.getSessionHistory(convId);
        const msgs = response.data || [];
        setMessages(msgs);
      } else {
        // Offline: load from local IndexedDB
        console.log('[Chat] Offline - loading messages from local storage');
        const localMsgs = await syncService.getLocalMessages(convId);
        setMessages(localMsgs);
      }
    } catch (err) {
      console.error('Failed to load messages from API:', err);

      // If API fails, try local storage as fallback
      try {
        console.log('[Chat] API failed - falling back to local messages');
        const localMsgs = await syncService.getLocalMessages(convId);
        if (localMsgs.length > 0) {
          setMessages(localMsgs);
          return;
        }
      } catch (localErr) {
        console.error('Failed to load messages from local storage:', localErr);
      }

      setError(err.response?.data?.detail || 'Failed to load messages');
      setMessages([]);
    } finally {
      setIsLoadingMessages(false);
    }
  }, []);

  /**
   * Send a message and get AI response
   * @param {string} content - The message content
   * @param {string} profileId - The profile ID (required if no active conversation)
   * @param {Object} options - { includeAudio?: boolean, slowAudio?: boolean, lowBandwidth?: boolean, enableWebSearch?: boolean }
   * @returns {Object} - The AI response message
   */
  const sendMessage = useCallback(async (content, profileId = null, options = {}) => {
    if (!content?.trim()) return null;

    const {
      includeAudio = false,
      slowAudio = false,
      lowBandwidth = false, // Low bandwidth mode for data saving
      enableWebSearch = false, // Enable web search for real-time information
    } = options;

    setError(null);
    let conversationId = activeConversation?._id || activeConversation?.id;
    let currentConversation = activeConversation;

    // Create new conversation if none active
    if (!conversationId) {
      if (!profileId) {
        setError('Profile ID is required to start a new conversation');
        return null;
      }
      try {
        const newConv = await createConversation(profileId);
        if (!newConv) {
          setError('Failed to create conversation');
          return null;
        }
        conversationId = newConv._id || newConv.id;
        currentConversation = newConv;
      } catch (err) {
        console.error('Failed to create conversation:', err);
        setError('Failed to create conversation. Please try again.');
        return null;
      }
    }

    // Create optimistic user message
    const userMessage = {
      _id: `temp-user-${Date.now()}`,
      conversation_id: conversationId,
      role: 'user',
      content: content.trim(),
      timestamp: new Date().toISOString(),
    };

    // Add user message immediately (optimistic update)
    setMessages((prev) => [...prev, userMessage]);
    setIsSendingMessage(true);
    setIsTyping(true);

    try {
      // Send message to backend with TTS options
      const response = await chatApi.sendMessage(conversationId, {
        content: content.trim(),
        include_audio: includeAudio,
        slow_audio: slowAudio,
        low_bandwidth: lowBandwidth,
        enable_web_search: enableWebSearch,
      });
      const aiResponse = response.data;

      if (!aiResponse) {
        throw new Error('Empty response from server');
      }

      // Update user message with actual ID if available, and add AI response
      setMessages((prev) => {
        // Replace temp user message with confirmed one and add AI response
        const withoutTemp = prev.filter((m) => m._id !== userMessage._id);
        return [
          ...withoutTemp,
          { ...userMessage, _id: `user-${Date.now()}` }, // Keep user message
          aiResponse, // Add AI response
        ];
      });

      // Store messages locally for offline access (non-blocking)
      syncService.addLocalMessage({ ...userMessage, _id: `user-${Date.now()}` }).catch(console.error);
      if (aiResponse._id) {
        syncService.addLocalMessage(aiResponse).catch(console.error);
      }

      // Check if this is the first message (new conversation) - generate title
      const isFirstMessage = currentConversation &&
        (!currentConversation.title || currentConversation.title === 'New Chat' || currentConversation.message_count === 0);

      if (isFirstMessage) {
        const generatedTitle = generateTitleFromMessage(content);

        // Update title in backend (fire and forget - don't block)
        chatApi.updateSession(conversationId, { title: generatedTitle })
          .then(() => {
            console.log('Conversation title updated:', generatedTitle);
          })
          .catch((err) => {
            console.error('Failed to update conversation title:', err);
          });

        // Update title in local state immediately
        setActiveConversation((prev) => prev ? { ...prev, title: generatedTitle } : prev);
        setConversations((prev) =>
          prev.map((c) => {
            const cId = c._id || c.id;
            if (cId === conversationId) {
              return { ...c, title: generatedTitle };
            }
            return c;
          })
        );
      }

      // Update conversation in list (move to top, update timestamp)
      setConversations((prev) => {
        const updated = prev.map((c) => {
          const cId = c._id || c.id;
          if (cId === conversationId) {
            return {
              ...c,
              updated_at: new Date().toISOString(),
              message_count: (c.message_count || 0) + 2, // user + ai
            };
          }
          return c;
        });
        // Sort by updated_at (most recent first)
        return updated.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
      });

      return aiResponse;
    } catch (err) {
      console.error('Failed to send message:', err);
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to send message. Please try again.';
      setError(errorMessage);

      // Add error message as AI response
      const errorResponse = {
        _id: `error-${Date.now()}`,
        conversation_id: conversationId,
        role: 'assistant',
        content: `Sorry, I couldn't process your message. ${errorMessage}`,
        timestamp: new Date().toISOString(),
        isError: true,
      };
      setMessages((prev) => [...prev, errorResponse]);

      return null;
    } finally {
      setIsSendingMessage(false);
      setIsTyping(false);
    }
  }, [activeConversation, createConversation]);

  /**
   * Send a message and get AI response with streaming (tokens appear as they're generated)
   * @param {string} content - The message content
   * @param {string} profileId - The profile ID (required if no active conversation)
   * @param {Object} options - { includeAudio?: boolean, slowAudio?: boolean, lowBandwidth?: boolean, enableWebSearch?: boolean }
   * @returns {Object} - The AI response message (after streaming completes)
   */
  const sendMessageStream = useCallback(async (content, profileId = null, options = {}) => {
    if (!content?.trim()) return null;

    const {
      includeAudio = false,
      slowAudio = false,
      lowBandwidth = false, // Low bandwidth mode for data saving
      enableWebSearch = false, // Enable web search for real-time information
    } = options;

    setError(null);
    let conversationId = activeConversation?._id || activeConversation?.id;
    let currentConversation = activeConversation;

    // Create new conversation if none active
    if (!conversationId) {
      if (!profileId) {
        setError('Profile ID is required to start a new conversation');
        return null;
      }
      try {
        const newConv = await createConversation(profileId);
        if (!newConv) {
          setError('Failed to create conversation');
          return null;
        }
        conversationId = newConv._id || newConv.id;
        currentConversation = newConv;
      } catch (err) {
        console.error('Failed to create conversation:', err);
        setError('Failed to create conversation. Please try again.');
        return null;
      }
    }

    // Create optimistic user message
    const userMessage = {
      _id: `temp-user-${Date.now()}`,
      conversation_id: conversationId,
      role: 'user',
      content: content.trim(),
      timestamp: new Date().toISOString(),
    };

    // Create placeholder AI message for streaming
    const streamingMessageId = `streaming-${Date.now()}`;
    const streamingMessage = {
      _id: streamingMessageId,
      conversation_id: conversationId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      isStreaming: true,
    };

    // Add user message and empty AI message immediately
    setMessages((prev) => [...prev, userMessage, streamingMessage]);
    setIsSendingMessage(true);
    setIsTyping(true);

    return new Promise((resolve) => {
      let finalAiResponse = null;

      chatApi.sendMessageStream(
        conversationId,
        {
          content: content.trim(),
          include_audio: includeAudio,
          slow_audio: slowAudio,
          low_bandwidth: lowBandwidth,
          enable_web_search: enableWebSearch,
        },
        {
          // Called for each token
          onToken: (token) => {
            setMessages((prev) =>
              prev.map((m) =>
                m._id === streamingMessageId
                  ? { ...m, content: m.content + token }
                  : m
              )
            );
          },

          // Called when streaming completes with full message
          onComplete: (completeMessage) => {
            finalAiResponse = completeMessage;

            // Replace streaming message with final message (without audio initially)
            setMessages((prev) => {
              const withoutStreaming = prev.filter(
                (m) => m._id !== streamingMessageId && m._id !== userMessage._id
              );
              return [
                ...withoutStreaming,
                { ...userMessage, _id: `user-${Date.now()}` },
                { ...completeMessage, isStreaming: false, isLoadingAudio: completeMessage.include_audio },
              ];
            });

            // If audio was requested, fetch TTS separately so text appears immediately
            if (completeMessage.include_audio && completeMessage._id) {
              console.log('[TTS] Fetching audio for message:', completeMessage._id);
              chatApi.generateTTS(completeMessage._id, slowAudio)
                .then((response) => {
                  const ttsData = response.data;
                  if (ttsData.success) {
                    console.log('[TTS] Audio received, updating message');
                    // Update the message with audio data
                    setMessages((prev) =>
                      prev.map((m) =>
                        m._id === completeMessage._id
                          ? {
                              ...m,
                              audio_base64: ttsData.audio_base64,
                              audio_format: ttsData.audio_format,
                              audio_language: ttsData.audio_language,
                              audio_language_name: ttsData.audio_language_name,
                              isLoadingAudio: false,
                            }
                          : m
                      )
                    );
                  }
                })
                .catch((err) => {
                  console.error('[TTS] Failed to generate audio:', err);
                  // Remove loading state on error
                  setMessages((prev) =>
                    prev.map((m) =>
                      m._id === completeMessage._id
                        ? { ...m, isLoadingAudio: false }
                        : m
                    )
                  );
                });
            }

            // Store messages locally for offline access (non-blocking)
            syncService.addLocalMessage({ ...userMessage, _id: `user-${Date.now()}` }).catch(console.error);
            if (completeMessage._id) {
              syncService.addLocalMessage(completeMessage).catch(console.error);
            }

            // Check if this is the first message - generate title
            const isFirstMessage =
              currentConversation &&
              (!currentConversation.title ||
                currentConversation.title === 'New Chat' ||
                currentConversation.message_count === 0);

            if (isFirstMessage) {
              const generatedTitle = generateTitleFromMessage(content);

              chatApi
                .updateSession(conversationId, { title: generatedTitle })
                .then(() => console.log('Conversation title updated:', generatedTitle))
                .catch((err) => console.error('Failed to update conversation title:', err));

              setActiveConversation((prev) =>
                prev ? { ...prev, title: generatedTitle } : prev
              );
              setConversations((prev) =>
                prev.map((c) => {
                  const cId = c._id || c.id;
                  if (cId === conversationId) {
                    return { ...c, title: generatedTitle };
                  }
                  return c;
                })
              );
            }

            // Update conversation in list
            setConversations((prev) => {
              const updated = prev.map((c) => {
                const cId = c._id || c.id;
                if (cId === conversationId) {
                  return {
                    ...c,
                    updated_at: new Date().toISOString(),
                    message_count: (c.message_count || 0) + 2,
                  };
                }
                return c;
              });
              return updated.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
            });

            setIsSendingMessage(false);
            setIsTyping(false);
            resolve(finalAiResponse);
          },

          // Called on error
          onError: (err) => {
            console.error('Streaming error:', err);
            const errorMessage = err.message || 'Failed to send message. Please try again.';
            setError(errorMessage);

            // Replace streaming message with error message
            setMessages((prev) =>
              prev.map((m) =>
                m._id === streamingMessageId
                  ? {
                    ...m,
                    content: `Sorry, I couldn't process your message. ${errorMessage}`,
                    isStreaming: false,
                    isError: true,
                  }
                  : m
              )
            );

            setIsSendingMessage(false);
            setIsTyping(false);
            resolve(null);
          },
        }
      );
    });
  }, [activeConversation, createConversation]);

  /**
   * Send a message using the offline local model (streaming).
   * This uses a smaller local model when network is unavailable or when explicitly requested.
   * Note: Only English responses are supported in offline mode.
   * @param {string} content - The message content
   * @param {string} profileId - The profile ID (required if no active conversation)
   * @returns {Object} - The AI response message with offline_mode: true
   */
  const sendMessageOffline = useCallback(async (content, profileId = null) => {
    if (!content?.trim()) return null;

    // Check if offline model is available
    if (!isOfflineModelAvailable) {
      setError('Offline model is not available. Please check your local Ollama installation.');
      return null;
    }

    setError(null);
    let conversationId = activeConversation?._id || activeConversation?.id;
    let currentConversation = activeConversation;

    // Create new conversation if none active
    if (!conversationId) {
      if (!profileId) {
        setError('Profile ID is required to start a new conversation');
        return null;
      }

      // For offline mode, we may not be able to create new conversations on the server
      // If online, create normally; if offline, show error
      if (!navigator.onLine) {
        setError('Cannot create new conversations while offline. Please use an existing conversation.');
        return null;
      }

      try {
        const newConv = await createConversation(profileId);
        if (!newConv) {
          setError('Failed to create conversation');
          return null;
        }
        conversationId = newConv._id || newConv.id;
        currentConversation = newConv;
      } catch (err) {
        console.error('Failed to create conversation:', err);
        setError('Failed to create conversation. Please try again.');
        return null;
      }
    }

    // Create optimistic user message
    const userMessage = {
      _id: `temp-offline-user-${Date.now()}`,
      conversation_id: conversationId,
      role: 'user',
      content: content.trim(),
      timestamp: new Date().toISOString(),
    };

    // Create placeholder AI message for streaming
    const streamingMessageId = `offline-streaming-${Date.now()}`;
    const streamingMessage = {
      _id: streamingMessageId,
      conversation_id: conversationId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      isStreaming: true,
      offline_mode: true, // Mark as offline mode
    };

    // Add user message and empty AI message immediately
    setMessages((prev) => [...prev, userMessage, streamingMessage]);
    setIsSendingMessage(true);
    setIsTyping(true);
    setIsUsingOfflineModel(true); // Signal that we're using offline model

    return new Promise((resolve) => {
      let finalAiResponse = null;

      chatApi.sendMessageOfflineStream(
        conversationId,
        { content: content.trim() },
        {
          // Called for each token
          onToken: (token) => {
            setMessages((prev) =>
              prev.map((m) =>
                m._id === streamingMessageId
                  ? { ...m, content: m.content + token }
                  : m
              )
            );
          },

          // Called when streaming completes with full message
          onComplete: (completeMessage) => {
            finalAiResponse = completeMessage;

            // Replace streaming message with final message
            setMessages((prev) => {
              const withoutStreaming = prev.filter(
                (m) => m._id !== streamingMessageId && m._id !== userMessage._id
              );
              return [
                ...withoutStreaming,
                { ...userMessage, _id: `offline-user-${Date.now()}` },
                { ...completeMessage, isStreaming: false, offline_mode: true },
              ];
            });

            // Store messages locally for offline access (non-blocking)
            syncService.addLocalMessage({ ...userMessage, _id: `offline-user-${Date.now()}` }).catch(console.error);
            if (completeMessage._id) {
              syncService.addLocalMessage({ ...completeMessage, offline_mode: true }).catch(console.error);
            }

            // Check if this is the first message - generate title
            const isFirstMessage =
              currentConversation &&
              (!currentConversation.title ||
                currentConversation.title === 'New Chat' ||
                currentConversation.message_count === 0);

            if (isFirstMessage && navigator.onLine) {
              const generatedTitle = generateTitleFromMessage(content);

              chatApi
                .updateSession(conversationId, { title: generatedTitle })
                .then(() => console.log('Conversation title updated:', generatedTitle))
                .catch((err) => console.error('Failed to update conversation title:', err));

              setActiveConversation((prev) =>
                prev ? { ...prev, title: generatedTitle } : prev
              );
              setConversations((prev) =>
                prev.map((c) => {
                  const cId = c._id || c.id;
                  if (cId === conversationId) {
                    return { ...c, title: generatedTitle };
                  }
                  return c;
                })
              );
            }

            // Update conversation in list
            setConversations((prev) => {
              const updated = prev.map((c) => {
                const cId = c._id || c.id;
                if (cId === conversationId) {
                  return {
                    ...c,
                    updated_at: new Date().toISOString(),
                    message_count: (c.message_count || 0) + 2,
                  };
                }
                return c;
              });
              return updated.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
            });

            setIsSendingMessage(false);
            setIsTyping(false);
            setIsUsingOfflineModel(false);
            resolve(finalAiResponse);
          },

          // Called on error
          onError: (err) => {
            console.error('Offline streaming error:', err);
            const errorMessage = err.message || 'Failed to get offline AI response.';
            setError(errorMessage);

            // Replace streaming message with error message
            setMessages((prev) =>
              prev.map((m) =>
                m._id === streamingMessageId
                  ? {
                    ...m,
                    content: `Sorry, the offline model couldn't process your message. ${errorMessage}`,
                    isStreaming: false,
                    isError: true,
                    offline_mode: true,
                  }
                  : m
              )
            );

            setIsSendingMessage(false);
            setIsTyping(false);
            setIsUsingOfflineModel(false);
            resolve(null);
          },
        }
      );
    });
  }, [activeConversation, createConversation, isOfflineModelAvailable]);

  /**
   * Upload audio for transcription (STT) and optionally send as message
   * @param {Blob} audioBlob - The recorded audio blob
   * @param {string} profileId - The profile ID (required if no active conversation)
   * @param {Object} options - { autoSend?: boolean, includeAudio?: boolean, slowAudio?: boolean, lowBandwidth?: boolean, enableWebSearch?: boolean }
   * @returns {Object} - { transcribedText, aiResponse? }
   */
  const sendVoiceMessage = useCallback(async (audioBlob, profileId = null, options = {}) => {
    const {
      autoSend = true, // Automatically send transcribed text to AI
      includeAudio = true, // Include TTS in AI response
      slowAudio = false, // Slow down TTS for learning
      lowBandwidth = false, // Low bandwidth mode for data saving
      enableWebSearch = false, // Enable web search for real-time information
    } = options;

    if (!audioBlob) {
      setError('No audio to send');
      return null;
    }

    setError(null);
    let conversationId = activeConversation?._id || activeConversation?.id;
    let currentConversation = activeConversation;

    // Create new conversation if none active
    if (!conversationId) {
      if (!profileId) {
        setError('Profile ID is required to start a new conversation');
        return null;
      }
      try {
        const newConv = await createConversation(profileId);
        if (!newConv) {
          setError('Failed to create conversation');
          return null;
        }
        conversationId = newConv._id || newConv.id;
        currentConversation = newConv;
      } catch (err) {
        console.error('Failed to create conversation:', err);
        setError('Failed to create conversation. Please try again.');
        return null;
      }
    }

    setIsSendingMessage(true);

    try {
      // Step 1: Upload audio for transcription (STT)
      console.log('[Voice] Uploading audio for transcription...');
      const sttResponse = await chatApi.uploadAudio(conversationId, audioBlob);
      const sttResult = sttResponse.data;

      if (!sttResult.success || !sttResult.transcribed_text) {
        throw new Error(sttResult.error || 'Failed to transcribe audio');
      }

      const transcribedText = sttResult.transcribed_text;
      console.log('[Voice] Transcription:', transcribedText);

      // If not auto-sending, just return the transcribed text
      if (!autoSend) {
        setIsSendingMessage(false);
        return { transcribedText, aiResponse: null };
      }

      // Step 2: Create user message (with voice indicator)
      const userMessage = {
        _id: `temp-voice-${Date.now()}`,
        conversation_id: conversationId,
        role: 'user',
        content: transcribedText,
        timestamp: new Date().toISOString(),
        is_voice_message: true,
        detected_language: sttResult.language,
        detected_language_name: sttResult.language_name,
      };

      // Create placeholder AI message for streaming
      const streamingMessageId = `voice-streaming-${Date.now()}`;
      const streamingMessage = {
        _id: streamingMessageId,
        conversation_id: conversationId,
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString(),
        isStreaming: true,
      };

      // Add user message and empty AI message immediately
      setMessages((prev) => [...prev, userMessage, streamingMessage]);
      setIsTyping(true);

      // Step 3: Send transcribed text with streaming AI response (with TTS if requested)
      console.log('[Voice] Sending to AI with streaming + TTS:', includeAudio);

      return new Promise((resolve) => {
        let finalAiResponse = null;

        chatApi.sendMessageStream(
          conversationId,
          {
            content: transcribedText,
            include_audio: includeAudio,
            slow_audio: slowAudio,
            low_bandwidth: lowBandwidth,
            enable_web_search: enableWebSearch,
          },
          {
            // Called for each token
            onToken: (token) => {
              setMessages((prev) =>
                prev.map((m) =>
                  m._id === streamingMessageId
                    ? { ...m, content: m.content + token }
                    : m
                )
              );
            },

            // Called when streaming completes with full message
            onComplete: (completeMessage) => {
              finalAiResponse = completeMessage;

              // Replace streaming message with final message
              setMessages((prev) => {
                const withoutStreamingAndTemp = prev.filter(
                  (m) => m._id !== streamingMessageId && m._id !== userMessage._id
                );
                return [
                  ...withoutStreamingAndTemp,
                  { ...userMessage, _id: `voice-user-${Date.now()}` },
                  { ...completeMessage, isStreaming: false },
                ];
              });

              // Store messages locally for offline access (non-blocking)
              syncService.addLocalMessage({ ...userMessage, _id: `voice-user-${Date.now()}` }).catch(console.error);
              if (completeMessage._id) {
                syncService.addLocalMessage(completeMessage).catch(console.error);
              }

              // Check if this is the first message - generate title
              const isFirstMessage = currentConversation &&
                (!currentConversation.title || currentConversation.title === 'New Chat' || currentConversation.message_count === 0);

              if (isFirstMessage) {
                const generatedTitle = generateTitleFromMessage(transcribedText);

                chatApi.updateSession(conversationId, { title: generatedTitle })
                  .then(() => console.log('Conversation title updated:', generatedTitle))
                  .catch((err) => console.error('Failed to update conversation title:', err));

                setActiveConversation((prev) => prev ? { ...prev, title: generatedTitle } : prev);
                setConversations((prev) =>
                  prev.map((c) => {
                    const cId = c._id || c.id;
                    if (cId === conversationId) {
                      return { ...c, title: generatedTitle };
                    }
                    return c;
                  })
                );
              }

              // Update conversation in list
              setConversations((prev) => {
                const updated = prev.map((c) => {
                  const cId = c._id || c.id;
                  if (cId === conversationId) {
                    return {
                      ...c,
                      updated_at: new Date().toISOString(),
                      message_count: (c.message_count || 0) + 2,
                    };
                  }
                  return c;
                });
                return updated.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
              });

              setIsSendingMessage(false);
              setIsTyping(false);
              resolve({ transcribedText, aiResponse: finalAiResponse });
            },

            // Called on error
            onError: (err) => {
              console.error('[Voice] Streaming error:', err);
              const errorMessage = err.message || 'Failed to get AI response';
              setError(errorMessage);

              // Replace streaming message with error message
              setMessages((prev) =>
                prev.map((m) =>
                  m._id === streamingMessageId
                    ? {
                      ...m,
                      content: `Sorry, I couldn't process your voice message. ${errorMessage}`,
                      isStreaming: false,
                      isError: true,
                    }
                    : m
                )
              );

              setIsSendingMessage(false);
              setIsTyping(false);
              resolve({ transcribedText, aiResponse: null });
            },
          }
        );
      });

    } catch (err) {
      console.error('[Voice] Error:', err);
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to process voice message';
      setError(errorMessage);

      const errorResponse = {
        _id: `error-${Date.now()}`,
        conversation_id: conversationId,
        role: 'assistant',
        content: `Sorry, I couldn't process your voice message. ${errorMessage}`,
        timestamp: new Date().toISOString(),
        isError: true,
      };
      setMessages((prev) => [...prev, errorResponse]);

      return null;
    } finally {
      setIsSendingMessage(false);
      setIsTyping(false);
    }
  }, [activeConversation, createConversation]);

  /**
   * Transcribe audio without sending (STT only)
   * @param {Blob} audioBlob - The recorded audio blob
   * @param {string} profileId - The profile ID (required if no active conversation)
   * @returns {Object} - { success, transcribed_text, language, language_name }
   */
  const transcribeAudio = useCallback(async (audioBlob, profileId = null) => {
    if (!audioBlob) {
      return { success: false, error: 'No audio to transcribe' };
    }

    let conversationId = activeConversation?._id || activeConversation?.id;

    // Create new conversation if none active (needed for the endpoint)
    if (!conversationId) {
      if (!profileId) {
        return { success: false, error: 'Profile ID required' };
      }
      try {
        const newConv = await createConversation(profileId);
        conversationId = newConv._id || newConv.id;
      } catch (err) {
        return { success: false, error: 'Failed to create conversation' };
      }
    }

    try {
      const response = await chatApi.uploadAudio(conversationId, audioBlob);
      return response.data;
    } catch (err) {
      return {
        success: false,
        error: err.response?.data?.detail || err.message || 'Transcription failed'
      };
    }
  }, [activeConversation, createConversation]);

  /**
   * Delete a conversation
   * @param {Object} conversation - The conversation to delete
   */
  const deleteConversation = useCallback(async (conversation) => {
    const convId = conversation._id || conversation.id;
    setError(null);

    try {
      await chatApi.deleteSession(convId);

      // Remove from list
      setConversations((prev) => prev.filter((c) => (c._id || c.id) !== convId));

      // Clear active if it was the deleted one
      const activeId = activeConversation?._id || activeConversation?.id;
      if (activeId === convId) {
        setActiveConversation(null);
        setMessages([]);
      }

      return true;
    } catch (err) {
      console.error('Failed to delete conversation:', err);
      setError(err.response?.data?.detail || 'Failed to delete conversation');
      return false;
    }
  }, [activeConversation]);

  /**
   * Update conversation metadata (title, subject_tag)
   * @param {string} conversationId - The conversation ID
   * @param {Object} updates - { title?, subject_tag? }
   */
  const updateConversation = useCallback(async (conversationId, updates) => {
    setError(null);

    try {
      const response = await chatApi.updateSession(conversationId, updates);
      const updatedConv = response.data;

      // Update in list
      setConversations((prev) =>
        prev.map((c) => {
          const cId = c._id || c.id;
          return cId === conversationId ? updatedConv : c;
        })
      );

      // Update active if it's the same
      const activeId = activeConversation?._id || activeConversation?.id;
      if (activeId === conversationId) {
        setActiveConversation(updatedConv);
      }

      return updatedConv;
    } catch (err) {
      console.error('Failed to update conversation:', err);
      setError(err.response?.data?.detail || 'Failed to update conversation');
      throw err;
    }
  }, [activeConversation]);

  /**
   * Clear the active conversation (go back to empty state)
   */
  const clearActiveConversation = useCallback(() => {
    setActiveConversation(null);
    setMessages([]);
  }, []);

  /**
   * Clear any error
   */
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  /**
   * Check if currently offline
   */
  const isOffline = !navigator.onLine;

  /**
   * Get conversations for a specific profile from local storage
   * Useful for offline-first profile selection
   */
  const getLocalConversationsForProfile = useCallback(async (profileId) => {
    try {
      const allConvs = await syncService.getLocalConversations();
      return allConvs.filter(c => c.profile_id === profileId);
    } catch (err) {
      console.error('Failed to get local conversations for profile:', err);
      return [];
    }
  }, []);

  /**
   * Reset all chat state - used when switching profiles
   * Clears conversations, messages, active conversation, and errors
   */
  const resetChatState = useCallback(() => {
    setConversations([]);
    setActiveConversation(null);
    setMessages([]);
    setError(null);
    initialLoadDone.current = false;
  }, []);

  /**
   * Send a message using TRUE offline mode (WebLLM - runs entirely in browser).
   * This is for when device has NO internet at all (can't reach backend).
   * Uses the WebLLM context for generating responses locally.
   * 
   * @param {string} content - The message content
   * @param {Object} webLLMContext - WebLLM context from useWebLLM()
   * @returns {Object} - The AI response message
   */
  const sendMessageTrueOffline = useCallback(async (content, webLLMContext) => {
    if (!content?.trim()) return null;

    const { generateStreamingResponse, isModelReady } = webLLMContext;

    if (!isModelReady) {
      setError('Offline model not loaded. Please download it first when you have internet.');
      return null;
    }

    setError(null);

    // For true offline, we create local-only messages with local IDs
    const localConversationId = activeConversation?._id || activeConversation?.id || 'local_offline';

    // Create user message
    const userMessage = {
      _id: `local-user-${Date.now()}`,
      conversation_id: localConversationId,
      role: 'user',
      content: content.trim(),
      timestamp: new Date().toISOString(),
      true_offline: true,
    };

    // Create placeholder AI message for streaming
    const streamingMessageId = `local-streaming-${Date.now()}`;
    const streamingMessage = {
      _id: streamingMessageId,
      conversation_id: localConversationId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      isStreaming: true,
      true_offline: true,
    };

    // Add user message and empty AI message immediately
    setMessages((prev) => [...prev, userMessage, streamingMessage]);
    setIsSendingMessage(true);
    setIsTyping(true);

    return new Promise((resolve) => {
      generateStreamingResponse(content.trim(), {
        // Called for each token
        onToken: (token) => {
          setMessages((prev) =>
            prev.map((m) =>
              m._id === streamingMessageId
                ? { ...m, content: m.content + token }
                : m
            )
          );
        },

        // Called when streaming completes
        onComplete: (completeResponse) => {
          const aiMessage = {
            _id: `local-ai-${Date.now()}`,
            conversation_id: localConversationId,
            role: 'assistant',
            content: completeResponse.content,
            timestamp: new Date().toISOString(),
            true_offline: true,
            model: completeResponse.model,
          };

          // Replace streaming message with final message
          setMessages((prev) => {
            const withoutStreaming = prev.filter(
              (m) => m._id !== streamingMessageId
            );
            return [...withoutStreaming, aiMessage];
          });

          // Store locally for persistence (non-blocking)
          syncService.addLocalMessage(userMessage).catch(console.error);
          syncService.addLocalMessage(aiMessage).catch(console.error);

          setIsSendingMessage(false);
          setIsTyping(false);
          resolve(aiMessage);
        },

        // Called on error
        onError: (err) => {
          console.error('True offline streaming error:', err);
          const errorMessage = err.message || 'Failed to generate offline response.';
          setError(errorMessage);

          // Replace streaming message with error message
          setMessages((prev) =>
            prev.map((m) =>
              m._id === streamingMessageId
                ? {
                  ...m,
                  content: `Sorry, the offline model couldn't process your message. ${errorMessage}`,
                  isStreaming: false,
                  isError: true,
                  true_offline: true,
                }
                : m
            )
          );

          setIsSendingMessage(false);
          setIsTyping(false);
          resolve(null);
        },
      });
    });
  }, [activeConversation]);

  return {
    // State
    conversations,
    activeConversation,
    messages,
    error,
    isOffline,

    // Offline mode state (backend-based)
    isOfflineModelAvailable,
    isUsingOfflineModel,
    offlineModelName,

    // Loading states
    isLoadingConversations,
    isLoadingMessages,
    isSendingMessage,
    isTyping,

    // Actions
    fetchConversations,
    createConversation,
    selectConversation,
    sendMessage,
    sendMessageStream,
    sendMessageOffline,
    sendMessageTrueOffline, // NEW: True offline using WebLLM
    sendVoiceMessage,
    transcribeAudio,
    deleteConversation,
    updateConversation,
    clearActiveConversation,
    clearError,
    getLocalConversationsForProfile,
    resetChatState,
    checkOfflineModelAvailability,

    // Helpers
    initialLoadDone: initialLoadDone.current,
  };
}

export default useChatService;

