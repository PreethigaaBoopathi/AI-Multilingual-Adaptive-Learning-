import React, { useState } from 'react';
import { BookOpen, ChevronDown, ChevronUp, ShieldCheck, FileText, Presentation, Video, ExternalLink } from 'lucide-react';

export const SourceCitation = ({ reference, citations = [] }) => {
  const [isOpen, setIsOpen] = useState(false);

  if (!reference && (!citations || citations.length === 0)) {
    return null;
  }

  const getSourceIcon = (sourceType) => {
    switch (sourceType) {
      case 'presentation':
        return <Presentation className="w-3.5 h-3.5 text-amber-500" />;
      case 'video':
        return <Video className="w-3.5 h-3.5 text-rose-500" />;
      case 'pdf':
      default:
        return <FileText className="w-3.5 h-3.5 text-indigo-500" />;
    }
  };

  const formatProvenanceBadge = (c) => {
    if (c.source_type === 'video' || c.timestamp) {
      return `Video: ${c.timestamp || '00:00'}`;
    }
    if (c.source_type === 'presentation' || c.slide) {
      return `Slide ${c.slide || c.page || 1}`;
    }
    return `Page ${c.page || 1}`;
  };

  return (
    <div className="mt-4 p-3 bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/80 rounded-lg text-xs text-slate-600 dark:text-slate-300 transition-all">
      <div 
        className="flex items-center justify-between cursor-pointer select-none"
        onClick={() => citations && citations.length > 0 && setIsOpen(!isOpen)}
      >
        <div className="flex items-center space-x-2">
          <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400 flex-shrink-0" />
          <span className="font-semibold text-slate-800 dark:text-slate-200">Source Grounding:</span>
          <span className="text-slate-600 dark:text-slate-400 truncate max-w-md">{reference || `${citations.length} Verified Course Source(s)`}</span>
        </div>
        {citations && citations.length > 0 && (
          <button className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300 flex items-center space-x-1 font-medium ml-2">
            <span>{isOpen ? 'Hide Excerpts' : 'View Source Excerpts'}</span>
            {isOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        )}
      </div>

      {isOpen && citations && citations.length > 0 && (
        <div className="mt-3 pt-2 border-t border-slate-200 dark:border-slate-700 space-y-2 animate-fade-in">
          {citations.map((c, i) => (
            <div key={i} className="bg-white dark:bg-slate-900 p-2.5 rounded border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300">
              <div className="flex items-center justify-between text-slate-500 dark:text-slate-400 font-medium mb-1">
                <div className="flex items-center space-x-1.5 truncate max-w-xs">
                  {getSourceIcon(c.source_type)}
                  <span className="font-semibold text-slate-700 dark:text-slate-200 truncate">
                    {c.filename || c.chapter}
                  </span>
                  {c.section && c.section !== c.chapter && (
                    <span className="text-slate-400 dark:text-slate-500 text-3xs truncate">
                      &bull; {c.section}
                    </span>
                  )}
                </div>
                <span className="bg-indigo-50 dark:bg-indigo-950/70 text-indigo-700 dark:text-indigo-300 px-1.5 py-0.5 rounded font-mono font-semibold text-3xs whitespace-nowrap">
                  {formatProvenanceBadge(c)}
                </span>
              </div>
              <p className="text-slate-600 dark:text-slate-300 italic text-3xs leading-relaxed">
                "{c.excerpt}"
              </p>
              {c.media_url && (
                <div className="mt-1.5 pt-1 border-t border-slate-100 dark:border-slate-800 flex items-center space-x-1 text-3xs text-indigo-600 dark:text-indigo-400">
                  <ExternalLink className="w-3 h-3" />
                  <a href={`http://localhost:8000${c.media_url}`} target="_blank" rel="noopener noreferrer" className="hover:underline">
                    View Associated Figure / Keyframe
                  </a>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
