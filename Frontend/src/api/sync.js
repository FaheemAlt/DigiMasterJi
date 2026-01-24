/**
 * Sync API Client
 * ================
 * API client for data synchronization endpoints.
 * 
 * DigiMasterJi - Multilingual AI Tutor for Rural Education
 */

import apiClient from './axios';

/**
 * Sync API endpoints
 * Uses master user token for authentication
 */
export const syncApi = {
  /**
   * Pull all user data for sync.
   * Fetches profiles, conversations, and messages from the server.
   * 
   * Backend: GET /sync/pull?days=N
   * Requires master user token (access_token)
   * 
   * @param {number} days - Number of days of message history to fetch (default: 15, max: 90)
   * @returns {Promise} - SyncPullResponse with nested data structure
   * 
   * Response structure:
   * {
   *   success: boolean,
   *   sync_timestamp: string,
   *   message: string,
   *   user_id: string,
   *   user_email: string,
   *   user_full_name: string,
   *   profiles: [{
   *     _id, master_user_id, name, age, grade_level, preferred_language, avatar,
   *     gamification: { xp, current_streak_days, last_activity_date, badges },
   *     learning_preferences: { voice_enabled },
   *     created_at, updated_at,
   *     conversations: [{
   *       _id, profile_id, title, subject_tag, created_at, updated_at,
   *       messages: [{ _id, conversation_id, profile_id, role, content, timestamp, ... }]
   *     }]
   *   }],
   *   total_profiles: number,
   *   total_conversations: number,
   *   total_messages: number,
   *   sync_period_days: number
   * }
   */
  pull: (days = 15) => {
    return apiClient.get('/sync/pull', {
      params: { days },
      timeout: 60000, // 60 seconds for large data sync
    });
  },

  /**
   * Push local changes to server (for future implementation)
   * Backend: POST /sync/push
   * 
   * @param {Object} data - Local changes to push
   * @returns {Promise} - Push result
   */
  push: (data) => {
    return apiClient.post('/sync/push', data, {
      timeout: 60000,
    });
  },
};

export default syncApi;
