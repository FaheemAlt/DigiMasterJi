/**
 * Sync Service
 * =============
 * Handles data synchronization between local IndexedDB and backend MongoDB.
 * 
 * Features:
 * - Pull data from server on login
 * - Store data locally for offline access
 * - Network status detection
 * - Automatic sync when coming back online
 * 
 * DigiMasterJi - Multilingual AI Tutor for Rural Education
 */

import { db } from '../db';
import { syncApi } from '../api/sync';

// Sync configuration - can be overridden via environment variable
const SYNC_DAYS = parseInt(import.meta.env.VITE_SYNC_DAYS || '180', 10); // Number of days of messages to sync
const SYNC_META_KEY = 'lastSync';

/**
 * SyncService class
 * Manages all synchronization operations
 */
class SyncService {
  constructor() {
    this._isSyncing = false;
    this._listeners = new Set();
    this._isOnline = typeof navigator !== 'undefined' ? navigator.onLine : true;

    // Setup network listeners
    if (typeof window !== 'undefined') {
      window.addEventListener('online', this._handleOnline.bind(this));
      window.addEventListener('offline', this._handleOffline.bind(this));
    }
  }

  /**
   * Get current sync status
   */
  get isSyncing() {
    return this._isSyncing;
  }

  /**
   * Get current online status
   */
  get isOnline() {
    return this._isOnline;
  }

  /**
   * Subscribe to sync status changes
   * @param {Function} listener - Callback function
   * @returns {Function} - Unsubscribe function
   */
  subscribe(listener) {
    this._listeners.add(listener);
    return () => this._listeners.delete(listener);
  }

  /**
   * Notify all listeners of status change
   */
  _notify(status) {
    this._listeners.forEach((listener) => {
      try {
        listener(status);
      } catch (err) {
        console.error('Sync listener error:', err);
      }
    });
  }

  /**
   * Handle coming online
   */
  _handleOnline() {
    console.log('[Sync] Network online');
    this._isOnline = true;
    this._notify({ type: 'online', isOnline: true });
    
    // Trigger sync when coming back online
    this.syncIfNeeded();
  }

  /**
   * Handle going offline
   */
  _handleOffline() {
    console.log('[Sync] Network offline');
    this._isOnline = false;
    this._notify({ type: 'offline', isOnline: false });
  }

  /**
   * Pull data from server and store locally
   * Called on login or manual sync
   * 
   * @param {number} days - Number of days of messages to fetch
   * @returns {Object} - Sync result
   */
  async pullFromServer(days = SYNC_DAYS) {
    if (this._isSyncing) {
      console.log('[Sync] Already syncing, skipping...');
      return { success: false, reason: 'already_syncing' };
    }

    if (!this._isOnline) {
      console.log('[Sync] Offline, cannot sync');
      return { success: false, reason: 'offline' };
    }

    this._isSyncing = true;
    this._notify({ type: 'sync_start', isSyncing: true });

    try {
      console.log(`[Sync] Pulling data from server (${days} days)...`);
      
      // Fetch data from server
      const response = await syncApi.pull(days);
      const data = response.data;

      if (!data.success) {
        throw new Error(data.message || 'Sync failed');
      }

      console.log(`[Sync] Received: ${data.total_profiles} profiles, ${data.total_conversations} conversations, ${data.total_messages} messages, ${data.total_quizzes || 0} quizzes`);

      // Store data locally (includes profiles, conversations, messages, and quizzes)
      await this._storeDataLocally(data);

      // Update sync metadata
      await db.syncMeta.put({
        key: SYNC_META_KEY,
        timestamp: new Date().toISOString(),
        syncPeriodDays: days,
        totalProfiles: data.total_profiles,
        totalConversations: data.total_conversations,
        totalMessages: data.total_messages,
        totalQuizzes: data.total_quizzes || 0,
        userId: data.user_id,
      });

      console.log('[Sync] Data stored locally');

      this._notify({ 
        type: 'sync_complete', 
        isSyncing: false, 
        success: true,
        stats: {
          profiles: data.total_profiles,
          conversations: data.total_conversations,
          messages: data.total_messages,
          quizzes: data.total_quizzes || 0,
        }
      });

      return {
        success: true,
        profiles: data.total_profiles,
        conversations: data.total_conversations,
        messages: data.total_messages,
        quizzes: data.total_quizzes || 0,
        syncTimestamp: data.sync_timestamp,
      };

    } catch (err) {
      console.error('[Sync] Pull failed:', err);
      
      this._notify({ 
        type: 'sync_error', 
        isSyncing: false, 
        error: err.message 
      });

      return {
        success: false,
        error: err.response?.data?.detail || err.message || 'Sync failed',
      };
    } finally {
      this._isSyncing = false;
    }
  }

  /**
   * Store synced data in local IndexedDB
   * @param {Object} data - SyncPullResponse from server
   */
  async _storeDataLocally(data) {
    // Use transaction for atomic operations
    await db.transaction('rw', [db.profiles, db.conversations, db.messages, db.quizzes], async () => {
      // Clear existing data first (full sync)
      await db.profiles.clear();
      await db.conversations.clear();
      await db.messages.clear();
      await db.quizzes.clear();

      let totalQuizzes = 0;

      // Store profiles
      for (const profile of data.profiles) {
        // Flatten the profile structure for storage
        const profileRecord = {
          _id: profile._id,
          master_user_id: profile.master_user_id,
          name: profile.name,
          age: profile.age,
          grade_level: profile.grade_level,
          preferred_language: profile.preferred_language,
          avatar: profile.avatar,
          // Gamification stats
          xp: profile.gamification?.xp || 0,
          current_streak_days: profile.gamification?.current_streak_days || 0,
          last_activity_date: profile.gamification?.last_activity_date,
          badges: profile.gamification?.badges || [],
          // Learning preferences
          voice_enabled: profile.learning_preferences?.voice_enabled ?? true,
          // Timestamps
          created_at: profile.created_at,
          updated_at: profile.updated_at,
        };

        await db.profiles.put(profileRecord);

        // Store conversations for this profile
        for (const conversation of profile.conversations || []) {
          const conversationRecord = {
            _id: conversation._id,
            profile_id: conversation.profile_id,
            title: conversation.title,
            subject_tag: conversation.subject_tag,
            created_at: conversation.created_at,
            updated_at: conversation.updated_at,
            message_count: conversation.messages?.length || 0,
          };

          await db.conversations.put(conversationRecord);

          // Store messages for this conversation
          for (const message of conversation.messages || []) {
            const messageRecord = {
              _id: message._id,
              conversation_id: message.conversation_id,
              profile_id: message.profile_id,
              role: message.role,
              content: message.content,
              content_translated: message.content_translated,
              timestamp: message.timestamp,
              rag_references: message.rag_references || [],
            };

            await db.messages.put(messageRecord);
          }
        }

        // Store quizzes for this profile (now included in sync response)
        for (const quiz of profile.quizzes || []) {
          const quizRecord = {
            _id: quiz._id,
            profile_id: quiz.profile_id,
            topic: quiz.topic,
            difficulty: quiz.difficulty,
            quiz_date: quiz.quiz_date,
            created_at: quiz.created_at,
            status: quiz.status,
            score: quiz.score,
            completed_at: quiz.completed_at,
            xp_earned: quiz.xp_earned,
            questions: quiz.questions || [],
            is_backlog: quiz.is_backlog || false,
          };
          
          await db.quizzes.put(quizRecord);
          totalQuizzes++;
        }
      }

      console.log(`[Sync] Stored ${totalQuizzes} quizzes locally`);
    });
  }

  /**
   * Get local quizzes for a profile
   * @param {string} profileId - Profile ID
   * @param {string} status - Optional status filter ('pending', 'completed', or null for all)
   */
  async getLocalQuizzes(profileId, status = null) {
    let query = db.quizzes.where('profile_id').equals(profileId);
    
    const quizzes = await query.toArray();
    
    if (status) {
      return quizzes.filter(q => q.status === status);
    }
    
    return quizzes.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  }

  /**
   * Get completed quizzes for revision (from local DB)
   * @param {string} profileId - Profile ID
   */
  async getLocalQuizzesForRevision(profileId) {
    const quizzes = await db.quizzes
      .where('profile_id')
      .equals(profileId)
      .and(q => q.status === 'completed')
      .toArray();
    
    return quizzes.sort((a, b) => new Date(b.completed_at) - new Date(a.completed_at));
  }

  /**
   * Update a local quiz after completion
   * @param {Object} quizData - Updated quiz data
   */
  async updateLocalQuiz(quizData) {
    await db.quizzes.put(quizData);
  }

  /**
   * Check if sync is needed and perform if so
   * Called when coming back online
   */
  async syncIfNeeded() {
    const lastSync = await this.getLastSyncInfo();
    
    if (!lastSync) {
      // No previous sync, skip auto-sync (will sync on login)
      return;
    }

    const lastSyncTime = new Date(lastSync.timestamp);
    const hoursSinceSync = (Date.now() - lastSyncTime.getTime()) / (1000 * 60 * 60);

    // Auto-sync if more than 1 hour since last sync
    if (hoursSinceSync > 1) {
      console.log(`[Sync] ${hoursSinceSync.toFixed(1)} hours since last sync, auto-syncing...`);
      await this.pullFromServer();
    }
  }

  /**
   * Get last sync information
   */
  async getLastSyncInfo() {
    return await db.syncMeta.get(SYNC_META_KEY);
  }

  /**
   * Get local profiles
   */
  async getLocalProfiles() {
    return await db.profiles.toArray();
  }

  /**
   * Get local conversations, optionally filtered by profile
   * @param {string} profileId - Optional Profile ID (if not provided, returns all)
   */
  async getLocalConversations(profileId = null) {
    if (profileId) {
      return await db.conversations
        .where('profile_id')
        .equals(profileId)
        .reverse()
        .sortBy('updated_at');
    }
    
    // Return all conversations if no profileId provided
    const all = await db.conversations.toArray();
    return all.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
  }

  /**
   * Get local messages for a conversation
   * @param {string} conversationId - Conversation ID
   */
  async getLocalMessages(conversationId) {
    return await db.messages
      .where('conversation_id')
      .equals(conversationId)
      .sortBy('timestamp');
  }

  /**
   * Add a message to local storage (optimistic update)
   * @param {Object} message - Message to store
   */
  async addLocalMessage(message) {
    await db.messages.put(message);
    
    // Update conversation's message count
    const conversation = await db.conversations.get(message.conversation_id);
    if (conversation) {
      await db.conversations.update(message.conversation_id, {
        message_count: (conversation.message_count || 0) + 1,
        updated_at: new Date().toISOString(),
      });
    }
  }

  /**
   * Add a conversation to local storage
   * @param {Object} conversation - Conversation to store
   */
  async addLocalConversation(conversation) {
    await db.conversations.put({
      ...conversation,
      message_count: 0,
    });
  }

  /**
   * Clear all local data (on logout)
   */
  async clearLocalData() {
    await db.clearUserData();
    console.log('[Sync] Local data cleared');
  }

  /**
   * Get sync statistics
   */
  async getStats() {
    const [profileCount, conversationCount, messageCount, lastSync] = await Promise.all([
      db.profiles.count(),
      db.conversations.count(),
      db.messages.count(),
      this.getLastSyncInfo(),
    ]);

    return {
      profiles: profileCount,
      conversations: conversationCount,
      messages: messageCount,
      lastSync: lastSync?.timestamp,
      isOnline: this._isOnline,
      isSyncing: this._isSyncing,
    };
  }
}

// Export singleton instance
export const syncService = new SyncService();

export default syncService;
