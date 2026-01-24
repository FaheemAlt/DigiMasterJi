import React, { createContext, useState, useEffect, useCallback } from 'react';
import { authApi } from '../api/auth';
import { 
  setAccessToken, 
  setRefreshToken, 
  getAccessToken, 
  clearAllTokens, 
  clearAccessToken, 
  clearRefreshToken 
} from '../utils/token';
import { setAuthFailureCallback } from '../api/axios';
import { syncService } from '../services/syncService';

export const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncError, setSyncError] = useState(null);

  // Initialize state from storage
  useEffect(() => {
    const token = getAccessToken();
    if (token) {
      setIsAuthenticated(true);
      // Optionally fetch user details here if not stored
      // authApi.getAccountDetails().then(res => setUser(res.data)).catch(...)
    }
    setLoading(false);
  }, []);

  // Trigger sync after successful authentication
  const triggerSync = useCallback(async () => {
    if (!navigator.onLine) {
      console.log('Offline - skipping initial sync');
      return;
    }
    
    setIsSyncing(true);
    setSyncError(null);
    
    try {
      await syncService.pullFromServer(15); // Pull last 15 days of data
      console.log('Initial sync completed successfully');
    } catch (error) {
      console.error('Initial sync failed:', error);
      setSyncError(error.message || 'Sync failed');
      // Don't throw - sync failure shouldn't block user
    } finally {
      setIsSyncing(false);
    }
  }, []);

  const logout = useCallback(async () => {
    // Clear local data on logout
    try {
      await syncService.clearLocalData();
      console.log('Local data cleared on logout');
    } catch (error) {
      console.error('Failed to clear local data:', error);
    }
    
    clearAllTokens();
    setUser(null);
    setIsAuthenticated(false);
    // Redirect is handled by the component consuming this or the interceptor callback
    window.location.href = '/login'; 
  }, []);

  // Setup Axios Interceptor callback
  useEffect(() => {
    setAuthFailureCallback(() => {
      logout();
    });
  }, [logout]);

  const login = async (credentials) => {
    try {
      const response = await authApi.login(credentials);
      // Backend returns flat structure: { access_token, refresh_token, expires_at, user_id, email, full_name, ... }
      // It does NOT return a nested 'user' object.
      const { access_token, refresh_token, expires_at, ...rest } = response.data;

      // Store access token with expiry for proactive refresh
      setAccessToken(access_token, expires_at);
      if (refresh_token) {
        setRefreshToken(refresh_token);
      }

      // Construct user object from response
      const userData = {
        id: rest.user_id,
        email: rest.email,
        full_name: rest.full_name,
        ...rest
      };

      setUser(userData);
      setIsAuthenticated(true);
      
      // Trigger background sync after login (non-blocking)
      triggerSync();
      
      return response;
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  };

  const register = async (data) => {
    try {
      const response = await authApi.register(data);
      // Backend RegisterResponse: { access_token, refresh_token, expires_at, token_type, user_id, message }
      // Note: Backend does NOT return email/full_name in register response
      if (response.data.access_token) {
        const { access_token, refresh_token, expires_at, user_id } = response.data;
        setAccessToken(access_token, expires_at);
        if (refresh_token) {
          setRefreshToken(refresh_token);
        }
        
        // Use the data we sent for registration since backend doesn't return it
        const userData = {
          id: user_id,
          email: data.email,
          full_name: data.full_name,
        };
        
        setUser(userData);
        setIsAuthenticated(true);
        
        // Trigger background sync after registration (non-blocking)
        // For new users, this won't pull much data, but sets up sync infrastructure
        triggerSync();
      }
      return response;
    } catch (error) {
      console.error('Registration failed:', error);
      throw error;
    }
  };

  // Manual refresh trigger if needed
  const refreshAuthToken = async () => {
   
    console.log('Manual refresh requested - handled by Axios interceptors automatically on 401');
  };

  const value = {
    user,
    isAuthenticated,
    loading,
    login,
    register,
    logout,
    getAccessToken,
    refreshAuthToken,
    // Sync state
    isSyncing,
    syncError,
    triggerSync
  };

  return (
    <AuthContext.Provider value={value}>
      {!loading && children}
    </AuthContext.Provider>
  );
};
