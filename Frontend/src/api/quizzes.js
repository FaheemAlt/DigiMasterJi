import apiClient from './axios';

/**
 * Quiz & Gamification API
 * Handles the daily streak and AI assessment logic
 */

export const quizzesApi = {
  /**
   * Trigger AI to generate a quiz based on recent chats
   * @param {Object} data - { conversation_id, difficulty }
   */
  generateQuiz: (data) => {
    return apiClient.post('/quizzes/generate', data);
  },

  /**
   * Check if any generated quizzes are ready to be taken
   * @param {string} profileId
   */
  getPendingQuizzes: (profileId) => {
    return apiClient.get('/quizzes/pending', {
      params: { profile_id: profileId },
    });
  },

  /**
   * Get today's quiz for the current profile
   * Returns the daily quiz if available
   */
  getTodayQuiz: () => {
    return apiClient.get('/quizzes/today');
  },

  /**
   * Fetch the actual quiz questions.
   * @param {string} quizId
   */
  getQuizById: (quizId) => {
    return apiClient.get(`/quizzes/${quizId}`);
  },

  /**
   * Submit answers and calculates score and updates XP
   * @param {string} quizId
   * @param {Object} answers - { answers: { q_id: option_id } }
   */
  submitQuiz: (quizId, answers) => {
    return apiClient.post(`/quizzes/${quizId}/submit`, answers);
  },

  /**
   * Get leaderboard data (Family or Global).
   * @param {string} scope - 'family' or 'global' (default is 'family')
   */
  getLeaderboard: (scope = 'family') => {
    return apiClient.get('/leaderboard', {
      params: { scope },
    });
  },

  /**
   * Get all completed quizzes with full questions for revision
   * @param {number} days - Number of days to look back (default: 30)
   */
  getQuizzesForRevision: (days = 30) => {
    return apiClient.get('/quizzes/revision/all', {
      params: { days },
    });
  },

  /**
   * Get dates where quizzes were missed (backlog)
   * @param {number} days - Number of days to check (default: 30)
   */
  getBacklogDates: (days = 30) => {
    return apiClient.get('/quizzes/backlog/dates', {
      params: { days },
    });
  },

  /**
   * Generate a backlog quiz for a missed date
   * Note: Backlog quizzes award XP but don't affect streak
   * @param {string} targetDate - Date in YYYY-MM-DD format
   */
  generateBacklogQuiz: (targetDate) => {
    return apiClient.post('/quizzes/backlog/generate', null, {
      params: { target_date: targetDate },
    });
  },

  /**
   * Check current streak status
   */
  checkStreakStatus: () => {
    return apiClient.get('/quizzes/streak/check');
  },

  /**
   * Cleanup old quizzes (admin function)
   * @param {number} days - Keep quizzes from last N days (default: 30)
   */
  cleanupOldQuizzes: (days = 30) => {
    return apiClient.delete('/quizzes/cleanup/old', {
      params: { days },
    });
  },

  // ============================================
  // Quiz Summary & Learning Insights
  // ============================================

  /**
   * Generate AI-powered summary for a completed quiz
   * Returns personalized insights based on current and historical performance
   * @param {string} quizId - The completed quiz ID
   * @returns {Promise} Quiz summary with performance analysis, study tips, and concept explanations
   */
  generateQuizSummary: (quizId) => {
    return apiClient.post(`/quizzes/${quizId}/summary`);
  },

  /**
   * Get comprehensive AI-powered learning insights for the student
   * This generates insights on-demand (may take longer)
   * @param {number} days - Number of days to analyze (default: 30)
   * @returns {Promise} Subject-wise insights, weak topics, recommendations, weekly goals
   */
  getLearningInsights: (days = 30) => {
    return apiClient.get('/quizzes/insights/learning', {
      params: { days },
    });
  },

  /**
   * Get stored/cached learning insights from user profile
   * These are auto-generated after each quiz completion
   * Falls back to generating if no stored insights exist
   * @returns {Promise} Stored insights with generated_at timestamp
   */
  getStoredInsights: () => {
    return apiClient.get('/quizzes/insights/stored');
  },

  /**
   * Manually trigger a refresh of the learning insights
   * Use when user wants updated analysis
   * @returns {Promise} Newly generated insights
   */
  refreshInsights: () => {
    return apiClient.post('/quizzes/insights/refresh');
  },
};
