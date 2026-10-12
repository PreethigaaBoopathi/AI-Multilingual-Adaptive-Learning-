import React, { useState, useEffect } from 'react';
import {
  BookOpen, FileText, Sparkles, GitBranch,
  MessageSquare, Award, AlertCircle, Search,
  ChevronRight, ChevronDown, Menu, X, BookMarked,
  Network, ArrowLeft, Upload, Check, Plus, Film, Presentation as PresentationIcon, Trash2
} from 'lucide-react';
import { useTextbook } from '../context/TextbookContext';
import { SummaryTab } from './tabs/SummaryTab';
import { ExplainTab } from './tabs/ExplainTab';
import { VisualizeTab } from './tabs/VisualizeTab';
import { ConceptGraphTab } from './tabs/ConceptGraphTab';
import { AskTab } from './tabs/AskTab';
import { QuizTab } from './tabs/QuizTab';
import { AdaptiveRevisionTab } from './tabs/AdaptiveRevisionTab';

export const WorkspacePage = ({ onNavigateUpload }) => {
  const {
    textbooks,
    activeTextbook,
    selectTextbook,
    activeChapter,
    activeSection,
    selectChapter,
    setActiveSection,
    deleteTextbook,
    clearAllTextbooks,
    activeTab,
    setActiveTab
  } = useTextbook();

  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedChapters, setExpandedChapters] = useState({});
  const [courseDropdownOpen, setCourseDropdownOpen] = useState(false);

  // Auto-expand active chapter on load or switch
  useEffect(() => {
    if (activeChapter?.id) {
      setExpandedChapters(prev => ({
        ...prev,
        [activeChapter.id]: true
      }));
    }
  }, [activeChapter?.id]);

  const toggleChapterExpand = (chId) => {
    setExpandedChapters(prev => ({
      ...prev,
      [chId]: !prev[chId]
    }));
  };

  const tabs = [
    { id: 'summary', label: 'Summary', icon: FileText, badge: null },
    { id: 'graph', label: 'Concept Graph', icon: Network, badge: null },
    { id: 'explain', label: 'Adaptive Explain', icon: Sparkles, badge: null },
    { id: 'visualize', label: 'Visualize', icon: GitBranch, badge: null },
    { id: 'ask', label: 'Ask Textbook', icon: MessageSquare, badge: null },
    { id: 'quiz', label: 'Quiz Drill', icon: Award, badge: null },
    { id: 'adaptive', label: 'Adaptive Revision', icon: AlertCircle, badge: null, isSpecial: true },
  ];

  const filteredChapters = (activeTextbook?.chapters || []).filter(ch => {
    if (!searchQuery) return true;
    const matchCh = ch.title.toLowerCase().includes(searchQuery.toLowerCase());
    const matchSec = ch.sections?.some(s => s.title.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchCh || matchSec;
  });

  return (
    <div className="flex-1 flex flex-col md:flex-row h-auto md:h-[calc(100vh-4rem)] md:max-h-[calc(100vh-4rem)] md:overflow-hidden bg-slate-100/70 dark:bg-slate-950 text-slate-900 dark:text-slate-100 transition-colors duration-200">

      {/* Mobile Sidebar Toggle Button */}
      <div className="md:hidden bg-white dark:bg-slate-900 px-4 py-2.5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between flex-shrink-0">
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="flex items-center space-x-2 text-xs font-bold text-slate-800 dark:text-slate-200"
        >
          <Menu className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
          <span>{sidebarOpen ? 'Hide Textbook Index' : 'Show Textbook Index'}</span>
        </button>
        <span className="text-3xs text-slate-500 dark:text-slate-400 truncate max-w-40">
          {activeChapter?.title || 'Table of Contents'}
        </span>
      </div>

      {/* LEFT COLUMN: Textbook Navigation Sidebar */}
      <aside
        className={`${sidebarOpen ? 'flex' : 'hidden'
          } md:flex w-full md:w-80 lg:w-96 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 flex-shrink-0 flex-col h-auto md:h-full z-20 transition-colors overflow-hidden`}
      >
        {/* Textbook Header */}
        <div className="flex-shrink-0 p-4 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/80 space-y-3 relative">
          
          {/* Back to Upload button */}
          {onNavigateUpload && (
            <div className="pb-1">
              <button
                onClick={onNavigateUpload}
                className="inline-flex items-center space-x-1.5 text-2xs font-bold text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300 hover:underline cursor-pointer"
              >
                <ArrowLeft className="w-3 h-3" />
                <span>Back to Upload / Add Material</span>
              </button>
            </div>
          )}

          <div 
            onClick={() => setCourseDropdownOpen(!courseDropdownOpen)}
            className="flex items-start justify-between cursor-pointer p-1.5 -m-1.5 rounded-xl hover:bg-slate-200/50 dark:hover:bg-slate-800/60 transition-colors group select-none"
            title="Click to switch course material or upload new"
          >
            <div className="flex items-start space-x-2.5 min-w-0">
              <div className="p-2 bg-indigo-600 text-white rounded-lg flex-shrink-0 shadow-xs">
                {activeTextbook?.source_type === 'video' ? (
                  <Film className="w-4 h-4" />
                ) : activeTextbook?.source_type === 'presentation' ? (
                  <PresentationIcon className="w-4 h-4" />
                ) : (
                  <BookMarked className="w-4 h-4" />
                )}
              </div>
              <div className="min-w-0">
                <h3 className="font-bold text-xs text-slate-900 dark:text-white leading-tight truncate">
                  {activeTextbook?.title || 'Course Material'}
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 font-medium mt-0.5">
                  <span className="uppercase font-bold text-indigo-600 dark:text-indigo-400">{activeTextbook?.source_type || 'PDF'}</span> &bull;{' '}
                  {activeTextbook?.source_type === 'presentation' 
                    ? `${activeTextbook?.total_slides || activeTextbook?.total_pages || 0} Slides`
                    : activeTextbook?.source_type === 'video'
                    ? (activeTextbook?.duration_str || `${Math.round(activeTextbook?.duration_seconds || 0)}s`)
                    : `${activeTextbook?.total_pages || 0} Pages`} &bull; {activeTextbook?.chapters?.length || 0} Chapters
                </p>
              </div>
            </div>
            <div className="ml-1 text-slate-400 group-hover:text-indigo-600 transition-colors p-1">
              <ChevronDown className={`w-4 h-4 transition-transform duration-200 ${courseDropdownOpen ? 'rotate-180 text-indigo-600' : ''}`} />
            </div>
          </div>

          {/* Course Material Switcher Dropdown Menu */}
          {courseDropdownOpen && (
            <div className="absolute top-full left-3 right-3 mt-1 z-50 bg-white dark:bg-slate-900 rounded-xl shadow-xl border border-slate-200 dark:border-slate-800 p-2 space-y-1 animate-fade-in max-h-72 overflow-y-auto custom-scrollbar">
              <div className="flex items-center justify-between px-2 py-1 text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
                <span>All Materials ({textbooks.length})</span>
                {textbooks.length > 0 && (
                  <button
                    type="button"
                    onClick={async (e) => {
                      e.stopPropagation();
                      const confirmed = window.confirm(`Clear all ${textbooks.length} materials from your workspace?`);
                      if (!confirmed) return;
                      try {
                        await clearAllTextbooks();
                        setCourseDropdownOpen(false);
                      } catch (err) {
                        alert('Failed to clear: ' + (err.response?.data?.detail || err.message));
                      }
                    }}
                    className="text-rose-500 hover:text-rose-700 dark:text-rose-400 font-bold lowercase flex items-center space-x-0.5 cursor-pointer"
                  >
                    <Trash2 className="w-2.5 h-2.5 mr-0.5" />
                    <span>clear all</span>
                  </button>
                )}
              </div>

              {textbooks.map((tb) => {
                const isSelected = activeTextbook?.id === tb.id;
                return (
                  <div
                    key={tb.id}
                    onClick={() => {
                      selectTextbook(tb);
                      setCourseDropdownOpen(false);
                    }}
                    className={`p-2 rounded-lg cursor-pointer flex items-center justify-between text-xs transition-colors group ${
                      isSelected
                        ? 'bg-indigo-50 dark:bg-indigo-950/60 text-indigo-900 dark:text-indigo-200 font-bold border border-indigo-200 dark:border-indigo-800'
                        : 'hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300'
                    }`}
                  >
                    <div className="min-w-0 pr-2 flex-1">
                      <p className="truncate text-xs font-semibold">{tb.title}</p>
                      <p className="text-xs text-slate-400 dark:text-slate-500 font-medium">
                        <span className="uppercase text-indigo-600 dark:text-indigo-400 font-bold">{tb.source_type || 'PDF'}</span> &bull; {tb.total_pages || tb.total_slides || 0} units
                      </p>
                    </div>
                    <div className="flex items-center space-x-1 flex-shrink-0">
                      {isSelected && <Check className="w-4 h-4 text-indigo-600 dark:text-indigo-400 flex-shrink-0" />}
                      <button
                        type="button"
                        onClick={async (e) => {
                          e.stopPropagation();
                          const confirmed = window.confirm(`Remove "${tb.title}" from your materials?`);
                          if (!confirmed) return;
                          try {
                            await deleteTextbook(tb.id);
                          } catch (err) {
                            alert('Failed to remove: ' + (err.response?.data?.detail || err.message));
                          }
                        }}
                        title={`Remove "${tb.title}"`}
                        className="p-1 text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/60 rounded-md transition-colors cursor-pointer"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                );
              })}

              {onNavigateUpload && (
                <div className="pt-1.5 border-t border-slate-100 dark:border-slate-800 mt-1">
                  <button
                    onClick={() => {
                      setCourseDropdownOpen(false);
                      onNavigateUpload();
                    }}
                    className="w-full flex items-center justify-center space-x-1.5 p-2 rounded-lg text-xs font-bold bg-indigo-50 hover:bg-indigo-100 dark:bg-indigo-950/50 dark:hover:bg-indigo-900/60 text-indigo-700 dark:text-indigo-300 transition-colors"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Upload New Course Material</span>
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Search Filter */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500 absolute left-2.5 top-2.5" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search chapters or sections..."
              className="w-full pl-8 pr-3 py-1.5 text-xs bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 rounded-lg focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 placeholder:text-slate-400 dark:placeholder:text-slate-500"
            />
          </div>
        </div>

        {/* Chapters and Sections Tree */}
        <div className="flex-1 min-h-0 overflow-y-auto overscroll-contain p-3 space-y-1.5 custom-scrollbar">
          <p className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider px-2 py-1">
            Table of Contents
          </p>

          {filteredChapters.map((ch) => {
            const isSelected = activeChapter?.id === ch.id;
            const isExpanded = expandedChapters[ch.id] ?? true;

            return (
              <div key={ch.id} className="rounded-xl overflow-hidden">
                {/* Chapter Row */}
                <div
                  onClick={() => {
                    selectChapter(ch);
                    toggleChapterExpand(ch.id);
                  }}
                  className={`p-2.5 rounded-lg cursor-pointer transition-all flex items-start justify-between text-xs select-none ${isSelected
                      ? 'bg-indigo-50 dark:bg-indigo-950/60 text-indigo-950 dark:text-indigo-200 font-bold border border-indigo-200/80 dark:border-indigo-800/80 shadow-2xs'
                      : 'hover:bg-slate-50 dark:hover:bg-slate-800/60 text-slate-800 dark:text-slate-200 font-medium'
                    }`}
                >
                  <div className="flex items-start space-x-2 min-w-0">
                    <span className={`w-5 h-5 rounded flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5 ${isSelected ? 'bg-indigo-600 text-white' : 'bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300'
                      }`}>
                      {ch.number}
                    </span>
                    <span className="leading-snug text-xs">{ch.title}</span>
                  </div>

                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleChapterExpand(ch.id);
                    }}
                    className="text-slate-400 hover:text-slate-700 dark:text-slate-500 dark:hover:text-slate-300 ml-1.5 p-0.5"
                  >
                    {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                  </button>
                </div>

                {/* Nested Sections */}
                {isExpanded && ch.sections && ch.sections.length > 0 && (
                  <div className="ml-5 pl-2.5 border-l-2 border-slate-200 dark:border-slate-800 space-y-1 my-1">
                    {ch.sections.filter(sec => sec.title && sec.title.trim().length > 0).map((sec) => {
                      const isSecSelected = activeSection?.id === sec.id && isSelected;
                      return (
                        <div
                          key={sec.id}
                          onClick={() => {
                            selectChapter(ch);
                            setActiveSection(sec);
                          }}
                          className={`p-1.5 px-2.5 rounded-lg cursor-pointer text-xs transition-all flex items-center justify-between ${isSecSelected
                              ? 'bg-indigo-600 text-white font-semibold shadow-xs'
                              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800/80 hover:text-slate-900 dark:hover:text-slate-200 font-medium'
                            }`}
                        >
                          <span className="truncate pr-1.5 text-xs">{sec.title}</span>
                          <span className={`text-xs font-mono font-medium flex-shrink-0 ${isSecSelected ? 'text-indigo-100 bg-indigo-700/70 px-1 rounded' : 'text-slate-400 dark:text-slate-500'
                            }`}>
                            p.{sec.page_start}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>

      </aside>

      {/* RIGHT COLUMN: Main Learning Workspace */}
      <main className="flex-1 min-h-0 h-full overflow-y-auto overscroll-contain p-4 sm:p-6 lg:p-8 custom-scrollbar">
        <div className="max-w-5xl mx-auto w-full pb-12">

          {/* Top Control Bar with Back to Upload and Language Switch */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3 px-1">
            <div className="flex items-center space-x-2 text-xs text-slate-500 dark:text-slate-400 min-w-0">
              {onNavigateUpload && (
                <button
                  onClick={onNavigateUpload}
                  className="inline-flex items-center space-x-1.5 text-xs font-semibold px-2.5 py-1 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 shadow-2xs transition-colors flex-shrink-0 cursor-pointer"
                  title="Return to Course Material Upload"
                >
                  <ArrowLeft className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
                  <span>Back to Upload</span>
                </button>
              )}
              <span className="font-semibold text-slate-700 dark:text-slate-300 truncate max-w-sm sm:max-w-md">
                {activeTextbook?.title ? `Course: ${activeTextbook.title}` : 'Course Material'}
              </span>
            </div>
            <div className="flex items-center space-x-2 self-end sm:self-auto">
              {onNavigateUpload && (
                <button
                  onClick={onNavigateUpload}
                  className="inline-flex items-center space-x-1 text-2xs font-semibold px-2 py-1 rounded-lg border border-indigo-200 dark:border-indigo-800 bg-indigo-50 dark:bg-indigo-950/50 hover:bg-indigo-100 text-indigo-700 dark:text-indigo-300 transition-colors cursor-pointer"
                >
                  <Upload className="w-3 h-3" />
                  <span>+ Add Material</span>
                </button>
              )}
            </div>

          </div>

          {/* Top Navigation Tabs Strip */}
          <div className="academic-card p-1.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 mb-6 flex items-center justify-between gap-2 overflow-x-auto shadow-2xs rounded-xl">
            <div className="flex items-center space-x-1">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;

                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center space-x-1.5 px-3 py-2 rounded-lg text-xs font-bold whitespace-nowrap transition-all select-none ${isActive
                        ? tab.isSpecial
                          ? 'bg-rose-600 text-white shadow-sm'
                          : 'bg-indigo-600 text-white shadow-sm'
                        : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100/70 dark:hover:bg-slate-800'
                      }`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    <span>{tab.label}</span>
                    {tab.badge && (
                      <span className={`text-3xs px-1.5 py-0.2 rounded font-extrabold uppercase ${isActive ? 'bg-white/20 text-white' : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300'
                        }`}>
                        {tab.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Tab Viewport */}
          <div className="academic-card p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 min-h-[500px] rounded-2xl">
            {activeTab === 'summary' && <SummaryTab />}
            {activeTab === 'graph' && <ConceptGraphTab />}
            {activeTab === 'explain' && <ExplainTab />}
            {activeTab === 'visualize' && <VisualizeTab />}
            {activeTab === 'ask' && <AskTab />}
            {activeTab === 'quiz' && (
              <QuizTab onNavigateToRevision={() => setActiveTab('adaptive')} />
            )}
            {activeTab === 'adaptive' && (
              <AdaptiveRevisionTab onRetakeQuiz={() => setActiveTab('quiz')} />
            )}
          </div>

        </div>
      </main>

    </div>
  );
};
