import React, { useState, useEffect } from 'react';
import { BookOpen } from 'lucide-react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { TextbookProvider } from './context/TextbookContext';
import { ThemeProvider } from './context/ThemeContext';
import { Navbar } from './components/Navbar';
import { ErrorBoundary } from './components/ErrorBoundary';
import { LandingPage } from './pages/LandingPage';
import { AuthPage } from './pages/AuthPage';
import { DashboardPage } from './pages/DashboardPage';
import { UploadPage } from './pages/UploadPage';
import { WorkspacePage } from './pages/WorkspacePage';

export function AppContent() {
  const { isAuthenticated, loading } = useAuth();

  // Derive initial view from window.location.hash
  const getViewFromHash = () => {
    if (!isAuthenticated) return 'auth';
    try {
      const hash = window.location.hash.replace(/^#\/?/, '').toLowerCase();
      if (['landing', 'auth', 'dashboard', 'upload', 'workspace'].includes(hash)) {
        return hash;
      }
    } catch {
      // Fallback
    }
    return 'dashboard';
  };

  const [currentView, setCurrentView] = useState(getViewFromHash);
  const isWorkspace = currentView === 'workspace';

  // Synchronize view changes with browser history & URL hash
  const navigateToView = (view, replace = false) => {
    setCurrentView(view);
    const targetHash = `#${view}`;
    if (window.location.hash !== targetHash) {
      if (replace) {
        window.history.replaceState({ view }, '', targetHash);
      } else {
        window.history.pushState({ view }, '', targetHash);
      }
    }
  };

  // Listen to browser Back (←) and Forward buttons
  useEffect(() => {
    const handlePopState = (e) => {
      const stateView = e.state?.view || getViewFromHash();
      setCurrentView(stateView);
    };

    window.addEventListener('popstate', handlePopState);
    window.addEventListener('hashchange', handlePopState);

    return () => {
      window.removeEventListener('popstate', handlePopState);
      window.removeEventListener('hashchange', handlePopState);
    };
  }, [isAuthenticated]);

  // Route guard: if unauthenticated and trying to access protected views, redirect to 'auth'
  useEffect(() => {
    if (!loading) {
      if (!isAuthenticated) {
        if (currentView !== 'auth') {
          navigateToView('auth', true);
        }
      } else {
        if (currentView === 'auth') {
          navigateToView('dashboard', true);
        }
      }
    }
  }, [isAuthenticated, loading, currentView]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100">
        <div className="flex flex-col items-center space-y-3">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-indigo-600 via-indigo-700 to-emerald-500 flex items-center justify-center text-white shadow-md animate-pulse">
            <BookOpen className="w-6 h-6" />
          </div>
          <div className="text-center">
            <h3 className="font-bold text-sm tracking-wide text-slate-800 dark:text-white">TextIQ AI Studio</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">Verifying secure academic session...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`flex flex-col bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 transition-colors duration-200 ${
      isWorkspace ? 'h-screen max-h-screen overflow-hidden' : 'min-h-screen'
    }`}>
      {/* Navbar displayed ONLY after successful login */}
      {isAuthenticated && (
        <div className="flex-shrink-0 z-40">
          <Navbar 
            currentView={currentView} 
            setCurrentView={navigateToView}
            onNavigateUpload={() => navigateToView('upload')}
          />
        </div>
      )}

      {/* Main View Router */}
      <div className={`flex-1 flex flex-col ${isWorkspace ? 'min-h-0 h-[calc(100vh-4rem)] overflow-hidden' : ''}`}>
        <ErrorBoundary>
          {currentView === 'landing' && (
            <LandingPage
              onGetStarted={() => navigateToView('dashboard')}
              onOpenWorkspace={() => navigateToView('workspace')}
            />
          )}

          {currentView === 'auth' && (
            <AuthPage
              onAuthSuccess={() => navigateToView('dashboard')}
            />
          )}

          {currentView === 'dashboard' && (
            <DashboardPage
              onNavigateWorkspace={() => navigateToView('workspace')}
              onNavigateUpload={() => navigateToView('upload')}
            />
          )}

          {currentView === 'upload' && (
            <UploadPage
              onOpenWorkspace={() => navigateToView('workspace')}
            />
          )}

          {currentView === 'workspace' && (
            <WorkspacePage 
              onNavigateUpload={() => navigateToView('upload')}
            />
          )}
        </ErrorBoundary>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <AuthProvider>
          <TextbookProvider>
            <AppContent />
          </TextbookProvider>
        </AuthProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

