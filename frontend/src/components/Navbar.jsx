import React, { useState, useRef, useEffect } from 'react';
import {
  BookOpen, LayoutDashboard, Upload, BookMarked,
  Home, Menu, X, ChevronRight, LogOut, Building, GraduationCap, Briefcase
} from 'lucide-react';
import { LanguageSwitch } from './LanguageSwitch';
import { ThemeToggle } from './ThemeToggle';
import { useTextbook } from '../context/TextbookContext';
import { useAuth } from '../context/AuthContext';

export const Navbar = ({ currentView, setCurrentView, onNavigateUpload }) => {
  const { activeTextbook } = useTextbook();
  const { user, isAuthenticated, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [profileDropdownOpen, setProfileDropdownOpen] = useState(false);
  const profileRef = useRef(null);

  // Close profile dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (profileRef.current && !profileRef.current.contains(e.target)) {
        setProfileDropdownOpen(false);
      }
    };
    if (profileDropdownOpen) {
      document.addEventListener('click', handleClickOutside);
    }
    return () => document.removeEventListener('click', handleClickOutside);
  }, [profileDropdownOpen]);

  const navItems = [
    { id: 'landing', label: 'Home', icon: Home },
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'upload', label: 'Upload Material', icon: Upload },
    { id: 'workspace', label: 'Workspace', icon: BookMarked, isSpecial: true },
  ];

  const handleNavClick = (viewId) => {
    if (viewId === 'upload' && onNavigateUpload) {
      onNavigateUpload();
    } else {
      setCurrentView(viewId);
    }
    setMobileMenuOpen(false);
  };

  return (
    <header className="sticky top-0 z-40 bg-white/90 dark:bg-slate-900/90 backdrop-blur-md border-b border-slate-200/80 dark:border-slate-800 shadow-xs transition-colors duration-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 gap-4">

          {/* Brand Logo & Name */}
          <div
            className="flex items-center space-x-3 cursor-pointer select-none group flex-shrink-0"
            onClick={() => handleNavClick('landing')}
          >
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-700 to-emerald-500 flex items-center justify-center text-white shadow-md shadow-indigo-500/20 group-hover:scale-105 transition-all duration-200">
              <BookOpen className="w-5 h-5" />
            </div>
            <div className="flex flex-col">
              <div className="flex items-center space-x-2">
                <span className="font-extrabold text-lg tracking-tight bg-gradient-to-r from-indigo-600 via-indigo-800 to-slate-900 dark:from-white dark:via-indigo-200 dark:to-indigo-400 bg-clip-text text-transparent">
                  TextIQ
                </span>
                <span className="bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 text-[10px] font-bold px-2 py-0.5 rounded-full border border-indigo-500/20 tracking-wide uppercase">
                  AI Studio
                </span>
              </div>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 font-medium hidden sm:block leading-none mt-0.5">
                Multilingual Textbook Intelligence
              </p>
            </div>
          </div>

          {/* Desktop Navigation Items */}
          <nav className="hidden md:flex items-center space-x-1.5">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = currentView === item.id;

              if (item.isSpecial) {
                return (
                  <button
                    key={item.id}
                    onClick={() => handleNavClick(item.id)}
                    className={`flex items-center space-x-1.5 px-3.5 py-1.5 text-xs font-bold rounded-lg transition-all duration-150 ${isActive
                        ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-500/30'
                        : 'text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-950/50 hover:bg-indigo-100 dark:hover:bg-indigo-900/60 border border-indigo-200/60 dark:border-indigo-800/60'
                      }`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    <span>{item.label}</span>
                  </button>
                );
              }

              return (
                <button
                  key={item.id}
                  onClick={() => handleNavClick(item.id)}
                  className={`flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg transition-all duration-150 ${isActive
                      ? 'bg-slate-100 dark:bg-slate-800 text-indigo-600 dark:text-indigo-400 font-bold'
                      : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100/70 dark:hover:bg-slate-800/60'
                    }`}
                >
                  <Icon className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500" />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>

          {/* Right Controls: Theme Toggle + Language switcher + User profile + Logout */}
          <div className="flex items-center space-x-2.5 sm:space-x-3">

            {/* Theme Toggle Button */}
            <ThemeToggle />

            {/* Language Switcher */}
            <div className="hidden sm:block">
              <LanguageSwitch />
            </div>

            {/* User Profile Pill & Dropdown (Read-only summary, no input fields!) */}
            {isAuthenticated && (
              <div className="relative" ref={profileRef}>
                <div
                  onClick={() => setProfileDropdownOpen(!profileDropdownOpen)}
                  className="flex items-center space-x-2 pl-2 border-l border-slate-200 dark:border-slate-800 cursor-pointer hover:opacity-85 transition-opacity"
                  title="View your profile details"
                >
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 text-white flex items-center justify-center font-bold text-xs shadow-xs ring-2 ring-indigo-500/20 overflow-hidden">
                    {user?.profile_picture ? (
                      <img src={user.profile_picture} alt={user?.name || "User"} className="w-full h-full object-cover" />
                    ) : (
                      <span>{user?.name ? user.name[0].toUpperCase() : 'U'}</span>
                    )}
                  </div>
                  <div className="hidden sm:block text-left text-xs">
                    <p className="font-bold text-slate-800 dark:text-slate-200 leading-tight truncate max-w-32">
                      {user?.name || 'Account'}
                    </p>
                  </div>
                </div>

                {/* Read-Only Profile Card (Does NOT prompt or ask for anything!) */}
                {profileDropdownOpen && (
                  <div className="absolute right-0 mt-2 w-72 bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 p-4 space-y-3 z-50 animate-in fade-in zoom-in-95">
                    {/* User Header */}
                    <div className="flex items-center space-x-3 pb-3 border-b border-slate-100 dark:border-slate-800">
                      <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-purple-600 text-white flex items-center justify-center font-bold text-sm shadow-md overflow-hidden">
                        {user?.profile_picture ? (
                          <img src={user.profile_picture} alt={user?.name} className="w-full h-full object-cover" />
                        ) : (
                          <span>{user?.name ? user.name[0].toUpperCase() : 'U'}</span>
                        )}
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="font-bold text-sm text-slate-900 dark:text-white truncate">{user?.name || 'Student'}</p>
                        <p className="text-xs text-slate-500 dark:text-slate-400 truncate">{user?.email}</p>
                      </div>
                    </div>

                    {/* Details (Read-only badges) */}
                    <div className="space-y-1.5 text-xs">
                      {user?.organisation && (
                        <div className="flex items-center justify-between py-1.5 px-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 text-slate-600 dark:text-slate-300">
                          <span className="text-slate-400 font-medium">Institution:</span>
                          <span className="font-semibold truncate max-w-[140px] text-right">{user.organisation} {user.org_type ? `(${user.org_type})` : ''}</span>
                        </div>
                      )}
                      {user?.department && (
                        <div className="flex items-center justify-between py-1.5 px-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 text-slate-600 dark:text-slate-300">
                          <span className="text-slate-400 font-medium">Department:</span>
                          <span className="font-semibold truncate max-w-[140px] text-right">{user.department}</span>
                        </div>
                      )}
                      <div className="flex items-center justify-between py-1.5 px-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 text-slate-600 dark:text-slate-300">
                        <span className="text-slate-400 font-medium">AI Language:</span>
                        <span className="font-semibold">{user?.preferred_language === 'ta' ? 'தமிழ் (Tamil)' : 'English (EN)'}</span>
                      </div>
                    </div>

                    {/* Quick Logout Button */}
                    <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
                      <button
                        type="button"
                        onClick={() => {
                          setProfileDropdownOpen(false);
                          logout();
                        }}
                        className="w-full flex items-center justify-center space-x-1.5 py-2 bg-rose-50 dark:bg-rose-950/40 hover:bg-rose-600 hover:text-white text-rose-600 dark:text-rose-400 font-bold text-xs rounded-xl transition-all border border-rose-200 dark:border-rose-900/60 cursor-pointer"
                      >
                        <LogOut className="w-3.5 h-3.5" />
                        <span>Log Out</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Direct One-Click Log Out Button in Navbar */}
            {isAuthenticated && (
              <button
                type="button"
                onClick={logout}
                className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-bold text-rose-600 dark:text-rose-400 hover:text-white hover:bg-rose-600 dark:hover:bg-rose-600 rounded-lg transition-all border border-rose-200 dark:border-rose-900/60 cursor-pointer"
                title="Log Out of your account"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Log Out</span>
              </button>
            )}

            {/* Mobile menu hamburger button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>

        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-900/95 backdrop-blur-md px-4 pt-3 pb-5 space-y-3 animate-fade-in shadow-xl">
          <div className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = currentView === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => handleNavClick(item.id)}
                  className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-semibold transition-colors ${isActive
                      ? 'bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 font-bold'
                      : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                    }`}
                >
                  <div className="flex items-center space-x-2.5">
                    <Icon className="w-4 h-4" />
                    <span>{item.label}</span>
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-400" />
                </button>
              );
            })}
          </div>

          {/* Profile & Logout in mobile menu */}
          {isAuthenticated && (
            <div className="pt-2 border-t border-slate-200 dark:border-slate-800 space-y-2">
              <div className="px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-800 text-xs">
                <p className="font-bold text-slate-900 dark:text-white">{user?.name}</p>
                <p className="text-slate-500 dark:text-slate-400 text-[11px]">{user?.email}</p>
                {user?.organisation && (
                  <p className="text-slate-500 dark:text-slate-400 text-[11px] mt-0.5">{user.organisation} • {user.department}</p>
                )}
              </div>
              <button
                type="button"
                onClick={() => {
                  setMobileMenuOpen(false);
                  logout();
                }}
                className="w-full flex items-center justify-center space-x-2 px-3 py-2 rounded-lg text-xs font-bold text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/40 hover:bg-rose-600 hover:text-white transition-colors border border-rose-200 dark:border-rose-900/60"
              >
                <LogOut className="w-4 h-4" />
                <span>Log Out</span>
              </button>
            </div>
          )}

          <div className="pt-2 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between">
            <span className="text-xs text-slate-500 dark:text-slate-400 font-medium">Language</span>
            <LanguageSwitch />
          </div>
        </div>
      )}
    </header>
  );
};
