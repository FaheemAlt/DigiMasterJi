import apiClient from './axios';

/**
 * Profile Management API
 * Handles the individual learner profiles under a master account
 */

export const profilesApi = {
  /**
   * List all profiles under the logged in master account
   */
  getAllProfiles: () => {
    return apiClient.get('/profiles');
  },

  /**
   * Create a new student profile
   * @param {Object} data - { name, age, grade, language, avatar }
   */
  createProfile: (data) => {
    return apiClient.post('/profiles', data);
  },

  /**
   * Get specific profile stats like XP, streaks
   * @param {string} id - Profile ID
   */
  getProfileById: (id) => {
    return apiClient.get(`/profiles/${id}`);
  },

  /**
   * Update profile 
   * @param {string} id - Profile ID
   * @param {Object} data - { avatar, language, ... }
   */
  updateProfile: (id, data) => {
    return apiClient.put(`/profiles/${id}`, data);
  },

  /**
   * Delete a student profile.
   * @param {string} id - Profile ID
   */
  deleteProfile: (id) => {
    return apiClient.delete(`/profiles/${id}`);
  },

  /**
   * Generate a temporary access token for this specific profile
   * Used for chat sessions to identify the active student
   * @param {string} id - Profile ID
   */
  getProfileAccessToken: (id) => {
    // Requesting a 1-week token duration
    return apiClient.post(`/profiles/${id}/access`, { expiresIn: '7d' });
  },
};

/**
 * Helper: Check if the current student session is valid
 * Use this before entering the Chat/Quiz routes
 * @returns {boolean}
 */
export const isProfileSessionValid = () => {
  const token = localStorage.getItem('profile_access_token');
  const expiry = localStorage.getItem('profile_token_expiry');

  if (!token || !expiry) return false;

  const now = new Date().getTime();
  return now < parseInt(expiry, 10);
};

/**
 * Helper: Store the student token with expiry
 * Call this after successfully getting the token from `getProfileAccessToken`
 * @param {string} token - The JWT string
 * @param {number} expiresInDays - Default 7 days
 */
export const setProfileSession = (token, expiresInDays = 7) => {
  const now = new Date().getTime();
  const expiryTime = now + (expiresInDays * 24 * 60 * 60 * 1000);
  
  localStorage.setItem('profile_access_token', token);
  localStorage.setItem('profile_token_expiry', expiryTime.toString());
};
