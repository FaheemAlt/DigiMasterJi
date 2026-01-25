import React, { createContext, useState, useEffect, useCallback, useRef } from 'react';
import { profilesApi } from '../api/profiles';
import {
  setProfileToken,
  getProfileToken,
  clearProfileToken,
  isTokenExpired
} from '../utils/token';
import { setProfileAuthFailureCallback } from '../api/axios';
import { syncService } from '../services/syncService';

export const ProfileContext = createContext(null);

export const ProfileProvider = ({ children }) => {
  const [profiles, setProfiles] = useState([]);
  const [activeProfile, setActiveProfile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [isOffline, setIsOffline] = useState(!navigator.onLine);

  // Listen for network changes
  useEffect(() => {
    const handleOnline = () => setIsOffline(false);
    const handleOffline = () => setIsOffline(true);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Fetch profiles - with offline fallback to IndexedDB
  const refreshProfiles = useCallback(async () => {
    try {
      setLoading(true);

      // Helper to load from local
      const loadFromLocal = async () => {
        console.log('[Profile] Loading profiles from local storage...');
        const localProfiles = await syncService.getLocalProfiles();
        if (localProfiles && localProfiles.length > 0) {
          console.log(`[Profile] Found ${localProfiles.length} local profiles`);
          setProfiles(localProfiles);
          return true;
        }
        console.log('[Profile] No local profiles found');
        setProfiles([]);
        return false;
      };

      // If clearly offline, skip API
      if (!navigator.onLine) {
        await loadFromLocal();
        return;
      }

      // Try API first
      try {
        const response = await profilesApi.getAllProfiles();
        setProfiles(response.data);
        return;
      } catch (error) {
        // Network error - try local storage
        if (error.code === 'ERR_NETWORK' || error.message === 'Network Error') {
          console.log('[Profile] Network error, falling back to local storage');
          await loadFromLocal();
          return;
        }
        console.error('Failed to fetch profiles from API:', error);
        // Still try local as fallback
        await loadFromLocal();
      }
    } catch (error) {
      console.error('Failed to fetch profiles:', error);
      setProfiles([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // Check for existing active profile session
  useEffect(() => {
    const token = getProfileToken();
    const expiry = localStorage.getItem('profile_access_token_expires');
    const storedProfileId = localStorage.getItem('active_profile_id');

    // If no stored profile ID, nothing to restore
    if (!storedProfileId) return;

    const hasValidToken = token && !isTokenExpired(expiry);
    const isCurrentlyOffline = !navigator.onLine;

    // Allow restore if: valid token OR offline with stored profile
    if (hasValidToken || isCurrentlyOffline) {
      // Try to fetch from API first, fallback to local
      const loadProfile = async () => {
        // Only try API if online and has valid token
        if (navigator.onLine && hasValidToken) {
          try {
            const res = await profilesApi.getProfileById(storedProfileId);
            setActiveProfile(res.data);
            return;
          } catch (err) {
            console.log('[Profile] Failed to fetch active profile from API');
          }
        }

        // Offline or API failed - try local storage
        try {
          const localProfiles = await syncService.getLocalProfiles();
          const localProfile = localProfiles.find(p => p._id === storedProfileId || p.id === storedProfileId);
          if (localProfile) {
            console.log('[Profile] Loaded active profile from local storage');
            setActiveProfile(localProfile);
          } else if (!isCurrentlyOffline) {
            // Profile not found locally and we're online - clear session
            clearProfileSession();
          }
          // If offline and not found locally, don't clear - user might sync later
        } catch (err) {
          console.error('[Profile] Failed to load profile from local storage:', err);
          if (!isCurrentlyOffline) {
            clearProfileSession();
          }
        }
      };

      loadProfile();
    }
  }, []);

  const clearProfileSession = useCallback(() => {
    clearProfileToken();
    localStorage.removeItem('active_profile_id');
    setActiveProfile(null);
    // Use correct route '/profiles' instead of non-existent '/select-profile'
    window.location.href = '/profiles';
  }, []);

  /**
   * Deactivate current profile without clearing all tokens.
   * Used when user wants to switch profiles from chat page.
   * Does not redirect, just clears the active profile state.
   */
  const deactivateProfile = useCallback(() => {
    clearProfileToken();
    localStorage.removeItem('active_profile_id');
    setActiveProfile(null);
  }, []);

  // Register callback for 401 on profile routes
  useEffect(() => {
    setProfileAuthFailureCallback(() => {
      console.warn('Profile session expired or invalid.');
      clearProfileSession();
    });
  }, [clearProfileSession]);

  // Track if activation is in progress to prevent double-activation
  const [isActivating, setIsActivating] = useState(false);
  const activatingProfileIdRef = useRef(null);

  const activateProfile = async (profileId) => {
    // Prevent double-activation of same profile
    if (activatingProfileIdRef.current === profileId) {
      console.log('[Profile] Already activating profile:', profileId, '- skipping');
      return true;
    }

    // If this profile is already active, skip
    const currentActiveId = activeProfile?._id || activeProfile?.id;
    if (currentActiveId === profileId) {
      console.log('[Profile] Profile already active:', profileId, '- skipping');
      return true;
    }

    activatingProfileIdRef.current = profileId;
    setIsActivating(true);

    // Helper function to activate from local storage
    const activateFromLocal = async () => {
      const localProfiles = await syncService.getLocalProfiles();
      const profile = localProfiles.find(p => p._id === profileId);

      if (profile) {
        console.log('[Profile] Activating profile from local storage');
        localStorage.setItem('active_profile_id', profileId);
        setActiveProfile(profile);
        return true;
      }
      throw new Error('Profile not available offline');
    };

    // If offline, use local storage directly
    if (!navigator.onLine) {
      console.log('[Profile] Offline detected, using local storage');
      try {
        return await activateFromLocal();
      } finally {
        activatingProfileIdRef.current = null;
        setIsActivating(false);
      }
    }

    try {
      // Online mode: get token from backend
      const response = await profilesApi.getProfileAccessToken(profileId);
      const { profile_token, expires_in } = response.data;

      // Calculate expiry ISO from expires_in (seconds)
      let expiryISO;
      if (expires_in) {
        const expiryDate = new Date(Date.now() + expires_in * 1000);
        expiryISO = expiryDate.toISOString();
      } else {
        // Fallback to 24 hours if not returned (backend default)
        const expiryDate = new Date(Date.now() + 24 * 60 * 60 * 1000);
        expiryISO = expiryDate.toISOString();
      }

      setProfileToken(profile_token, expiryISO);
      localStorage.setItem('active_profile_id', profileId);

      // Set Active Profile State
      const profile = profiles.find(p => (p._id === profileId || p.id === profileId)) || (await profilesApi.getProfileById(profileId)).data;
      setActiveProfile(profile);

      return true;
    } catch (error) {
      // Network error - fallback to local storage
      if (error.code === 'ERR_NETWORK' || error.message === 'Network Error') {
        console.log('[Profile] Network error, falling back to local storage');
        return await activateFromLocal();
      }
      console.error('Failed to activate profile:', error);
      throw error;
    } finally {
      activatingProfileIdRef.current = null;
      setIsActivating(false);
    }
  };

  const createProfile = async (data) => {
    const response = await profilesApi.createProfile(data);
    await refreshProfiles();
    return response;
  };

  const isProfileSessionValid = () => {
    const token = getProfileToken();
    const expiry = localStorage.getItem('profile_access_token_expires');
    const storedProfileId = localStorage.getItem('active_profile_id');

    // If we have an active profile in context, we're valid
    // This handles cases where profile was activated from local storage
    if (activeProfile) {
      return true;
    }

    // If online, require valid token
    if (navigator.onLine) {
      // 2-minute grace window is handled by isTokenExpired default (120s)
      return token && !isTokenExpired(expiry);
    }

    // If offline, allow access if we have an active profile stored
    // (even without valid token - we'll use local data)
    return !!storedProfileId;
  };

  const value = {
    profiles,
    activeProfile,
    loading,
    isOffline,
    refreshProfiles,
    activateProfile,
    createProfile,
    isProfileSessionValid,
    selectProfile: activateProfile, // Alias as requested
    deactivateProfile, // For switching profiles without full logout
  };

  return (
    <ProfileContext.Provider value={value}>
      {children}
    </ProfileContext.Provider>
  );
};
