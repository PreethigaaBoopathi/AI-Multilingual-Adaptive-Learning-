import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authAPI } from '../services/api';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(() => {
    try {
      return localStorage.getItem('textiq_auth_token') || sessionStorage.getItem('textiq_auth_token') || null;
    } catch {
      return null;
    }
  });

  const [user, setUser] = useState(() => {
    try {
      const saved = localStorage.getItem('learning_system_user') || sessionStorage.getItem('learning_system_user');
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  const [loading, setLoading] = useState(true);

  // Sync language preference with application
  const applyUserLanguage = useCallback((lang) => {
    if (lang && (lang === 'en' || lang === 'ta')) {
      try {
        localStorage.setItem('textiq_language', lang);
        window.dispatchEvent(new Event('languageChange'));
      } catch (e) {
        console.warn('Language sync warning:', e);
      }
    }
  }, []);

  // Verify and hydrate session on initial mount
  useEffect(() => {
    let isMounted = true;

    const verifySession = async () => {
      const activeToken = localStorage.getItem('textiq_auth_token') || sessionStorage.getItem('textiq_auth_token');
      if (!activeToken) {
        if (isMounted) {
          setUser(null);
          setToken(null);
          setLoading(false);
        }
        return;
      }

      try {
        const freshUser = await authAPI.getMe();
        if (isMounted) {
          setUser(freshUser);
          setToken(activeToken);
          if (freshUser.preferred_language) {
            applyUserLanguage(freshUser.preferred_language);
          }
          // Refresh stored user data
          if (localStorage.getItem('textiq_auth_token')) {
            localStorage.setItem('learning_system_user', JSON.stringify(freshUser));
          } else {
            sessionStorage.setItem('learning_system_user', JSON.stringify(freshUser));
          }
        }
      } catch (err) {
        console.warn('[AuthContext] Session expired or invalid:', err?.response?.data || err.message);
        if (isMounted) {
          localStorage.removeItem('textiq_auth_token');
          localStorage.removeItem('learning_system_user');
          sessionStorage.removeItem('textiq_auth_token');
          sessionStorage.removeItem('learning_system_user');
          setUser(null);
          setToken(null);
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    verifySession();

    // Listen to global 401 unauthorized events from Axios interceptor
    const handleUnauthorized = () => {
      if (isMounted) {
        setUser(null);
        setToken(null);
      }
    };
    window.addEventListener('auth:unauthorized', handleUnauthorized);

    return () => {
      isMounted = false;
      window.removeEventListener('auth:unauthorized', handleUnauthorized);
    };
  }, [applyUserLanguage]);

  const login = async (email, password, rememberMe = false) => {
    const res = await authAPI.login(email, password, rememberMe);
    const { token: authToken, ...userData } = res;

    setUser(userData);
    setToken(authToken);

    if (rememberMe) {
      localStorage.setItem('textiq_auth_token', authToken);
      localStorage.setItem('learning_system_user', JSON.stringify(userData));
      sessionStorage.removeItem('textiq_auth_token');
      sessionStorage.removeItem('learning_system_user');
    } else {
      sessionStorage.setItem('textiq_auth_token', authToken);
      sessionStorage.setItem('learning_system_user', JSON.stringify(userData));
      localStorage.removeItem('textiq_auth_token');
      localStorage.removeItem('learning_system_user');
    }

    if (userData.preferred_language) {
      applyUserLanguage(userData.preferred_language);
    }
    return userData;
  };

  const register = async (registrationData) => {
    const res = await authAPI.register(registrationData);
    const { token: authToken, ...userData } = res;

    setUser(userData);
    setToken(authToken);

    localStorage.setItem('textiq_auth_token', authToken);
    localStorage.setItem('learning_system_user', JSON.stringify(userData));

    if (userData.preferred_language) {
      applyUserLanguage(userData.preferred_language);
    }
    return userData;
  };

  const updateProfile = async (profileUpdates) => {
    const updatedUser = await authAPI.updateProfile(profileUpdates);
    setUser(updatedUser);

    if (localStorage.getItem('textiq_auth_token')) {
      localStorage.setItem('learning_system_user', JSON.stringify(updatedUser));
    } else if (sessionStorage.getItem('textiq_auth_token')) {
      sessionStorage.setItem('learning_system_user', JSON.stringify(updatedUser));
    }

    if (updatedUser.preferred_language) {
      applyUserLanguage(updatedUser.preferred_language);
    }
    return updatedUser;
  };

  const logout = async () => {
    try {
      await authAPI.logout();
    } catch {
      // ignore
    } finally {
      localStorage.removeItem('textiq_auth_token');
      localStorage.removeItem('learning_system_user');
      sessionStorage.removeItem('textiq_auth_token');
      sessionStorage.removeItem('learning_system_user');
      setUser(null);
      setToken(null);
    }
  };

  const forgotPassword = async (email) => {
    return await authAPI.forgotPassword(email);
  };

  const resetPassword = async (email, resetToken, newPassword) => {
    return await authAPI.resetPassword(email, resetToken, newPassword);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        isAuthenticated: Boolean(user && token),
        login,
        register,
        logout,
        updateProfile,
        forgotPassword,
        resetPassword,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
