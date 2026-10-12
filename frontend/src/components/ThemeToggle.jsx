import React from 'react';
import { Sun, Moon } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

export const ThemeToggle = ({ className = "" }) => {
  const { theme, toggleTheme, isDark } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      type="button"
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      title={isDark ? "Switch to light mode" : "Switch to dark mode"}
      className={`relative inline-flex items-center justify-center w-9 h-9 rounded-lg transition-all duration-200 
        bg-slate-100 hover:bg-slate-200 text-slate-600 border border-slate-200/80
        dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-amber-300 dark:border-slate-700
        focus:outline-none focus:ring-2 focus:ring-indigo-500/50 shadow-2xs ${className}`}
    >
      <span className="sr-only">Toggle theme</span>
      <div className="relative w-4 h-4 flex items-center justify-center">
        <Sun
          className={`w-4 h-4 transform transition-all duration-300 text-amber-500 absolute ${
            isDark ? 'rotate-90 scale-0 opacity-0' : 'rotate-0 scale-100 opacity-100'
          }`}
        />
        <Moon
          className={`w-4 h-4 transform transition-all duration-300 text-indigo-400 absolute ${
            isDark ? 'rotate-0 scale-100 opacity-100' : '-rotate-90 scale-0 opacity-0'
          }`}
        />
      </div>
    </button>
  );
};
