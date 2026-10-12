import React from 'react';
import { Globe } from 'lucide-react';
import { useTextbook } from '../context/TextbookContext';

export const LanguageSwitch = () => {
  const { language, setLanguage } = useTextbook();

  return (
    <div className="flex items-center bg-slate-100 dark:bg-slate-800/90 p-0.5 rounded-lg border border-slate-200 dark:border-slate-700/80 transition-colors">
      <div className="flex items-center px-2 py-1 text-slate-500 dark:text-slate-400 text-xs font-medium">
        <Globe className="w-3.5 h-3.5 mr-1.5 text-indigo-600 dark:text-indigo-400" />
        <span className="hidden md:inline text-2xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500 mr-0.5">Lang:</span>
      </div>
      <button
        onClick={() => setLanguage('en')}
        className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-all duration-150 ${
          language === 'en'
            ? 'bg-white dark:bg-slate-700 text-indigo-700 dark:text-indigo-300 shadow-sm border border-slate-200/80 dark:border-slate-600'
            : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200/50 dark:hover:bg-slate-700/50'
        }`}
      >
        English
      </button>
      <button
        onClick={() => setLanguage('ta')}
        className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-all duration-150 ${
          language === 'ta'
            ? 'bg-indigo-600 text-white shadow-sm font-bold'
            : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200/50 dark:hover:bg-slate-700/50'
        }`}
      >
        தமிழ் (Tamil)
      </button>
    </div>
  );
};
