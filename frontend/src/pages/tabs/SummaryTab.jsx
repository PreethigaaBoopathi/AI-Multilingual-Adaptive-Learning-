import React, { useState, useEffect, useRef } from 'react';
import { 
  FileText, Sparkles, CheckCircle2, Bookmark, 
  RotateCw, ShieldCheck, Languages, ArrowRight, AlertCircle,
  BrainCircuit
} from 'lucide-react';
import { textbookAPI } from '../../services/api';
import { useTextbook } from '../../context/TextbookContext';
import { SourceCitation } from '../../components/SourceCitation';

export const SummaryTab = () => {
  const { activeTextbook, activeChapter, activeSection, language } = useTextbook();
  const [summaryData, setSummaryData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [loadingStep, setLoadingStep] = useState(0);

  // In-memory cache to make tab & language toggles instantaneous
  const cacheRef = useRef({});
  const activeReqIdRef = useRef(0);

  const getCacheKey = () => {
    if (!activeTextbook) return null;
    return `${activeTextbook.id}_${activeChapter?.id || 'all'}_${activeSection?.id || 'all'}_${language}`;
  };

  const loadSummary = async (forceRefresh = false) => {
    if (!activeTextbook) return;

    const cacheKey = getCacheKey();
    if (!forceRefresh && cacheKey && cacheRef.current[cacheKey]) {
      setSummaryData(cacheRef.current[cacheKey]);
      setLoading(false);
      setError(null);
      return;
    }

    const currentReqId = ++activeReqIdRef.current;
    try {
      setLoading(true);
      setError(null);
      setLoadingStep(0);

      const stepTimer1 = setTimeout(() => setLoadingStep(1), 1200);
      const stepTimer2 = setTimeout(() => setLoadingStep(2), 3500);

      const data = await textbookAPI.summarize(
        activeTextbook.id,
        activeChapter ? activeChapter.id : null,
        activeSection ? activeSection.id : null,
        language
      );

      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);

      if (activeReqIdRef.current === currentReqId) {
        if (cacheKey) {
          cacheRef.current[cacheKey] = data;
        }
        setSummaryData(data);
      }
    } catch (err) {
      if (activeReqIdRef.current === currentReqId) {
        console.error('Error generating summary:', err);
        setError('Unable to load live summary. Please check your backend connection or retry.');
      }
    } finally {
      if (activeReqIdRef.current === currentReqId) {
        setLoading(false);
      }
    }
  };

  useEffect(() => {
    loadSummary(false);
  }, [activeTextbook, activeChapter, activeSection, language]);

  const loadingSteps = [
    'Reading textbook chunks & curriculum context...',
    'Synthesizing pedagogical definitions & high-yield exam takeaways...',
    language === 'ta' 
      ? 'Finalizing fluent Tamil translation & bilingual glossary alignment...' 
      : 'Assembling grounded summary & quick revision takeaways...'
  ];

  return (
    <div className="space-y-6 text-slate-900 dark:text-slate-100">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-xl font-bold text-slate-900 dark:text-white">
              {activeChapter ? activeChapter.title : 'Chapter Summary'}
            </h2>
            <span className="text-2xs font-semibold px-2 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
              {language === 'ta' ? 'தமிழ்' : 'English'}
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Grounded AI synthesis of core textbook knowledge and exam-yield concepts.
          </p>
        </div>

        <div className="flex items-center space-x-2.5">
          <button
            onClick={() => loadSummary(true)}
            disabled={loading}
            className="inline-flex items-center justify-center space-x-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-semibold rounded-lg shadow-sm transition-all"
            title="Re-synthesize summary"
          >
            <RotateCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>{loading ? 'Synthesizing...' : 'Generate Summary'}</span>
          </button>
        </div>
      </div>

      {loading ? (
        <div className="py-14 px-6 max-w-xl mx-auto text-center space-y-4">
          <div className="relative w-12 h-12 mx-auto">
            <div className="absolute inset-0 rounded-full border-3 border-indigo-100 dark:border-indigo-950/80" />
            <div className="w-12 h-12 border-3 border-indigo-600 dark:border-indigo-400 border-t-transparent rounded-full animate-spin" />
            <BrainCircuit className="w-5 h-5 text-indigo-600 dark:text-indigo-400 absolute inset-0 m-auto" />
          </div>

          <div className="space-y-1.5">
            <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">
              {loadingSteps[loadingStep] || loadingSteps[0]}
            </p>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Grounded synthesis in progress • {language === 'ta' ? 'தமிழ் பயன்முறை' : 'English academic mode'}
            </p>
          </div>

          {/* Micro Progress Bar */}
          <div className="w-48 h-1.5 bg-slate-100 dark:bg-slate-800 rounded-full mx-auto overflow-hidden">
            <div 
              className="h-full bg-indigo-600 dark:bg-indigo-400 rounded-full transition-all duration-700 ease-out"
              style={{ width: `${Math.min(100, (loadingStep + 1) * 33)}%` }}
            />
          </div>
        </div>
      ) : summaryData ? (
        <div className="space-y-6 animate-fade-in">
          {/* Main Chapter Summary Paragraphs */}
          <div className="academic-card p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl">
            <div className="flex items-center space-x-2 text-indigo-700 dark:text-indigo-400 font-bold text-sm mb-3">
              <FileText className="w-4 h-4" />
              <span>Chapter Summary</span>
            </div>
            <div className="text-slate-700 dark:text-slate-300 text-sm leading-relaxed whitespace-pre-line space-y-3">
              {summaryData.summary}
            </div>
          </div>

          {/* 2-Column Grid: Key Concepts & Important Points */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            
            {/* Key Concepts */}
            <div className="academic-card p-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl flex flex-col justify-between">
              <div>
                <div className="flex items-center space-x-2 text-emerald-700 dark:text-emerald-400 font-bold text-sm mb-3">
                  <Bookmark className="w-4 h-4" />
                  <span>Key Concepts & Definitions</span>
                </div>
                <ul className="space-y-2.5">
                  {(summaryData.key_concepts || []).map((concept, idx) => (
                    <li key={idx} className="flex items-start space-x-2 text-xs text-slate-700 dark:text-slate-300">
                      <span className="w-5 h-5 rounded-full bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 font-bold flex items-center justify-center flex-shrink-0 text-2xs mt-0.5 border border-emerald-200 dark:border-emerald-800/50">
                        {idx + 1}
                      </span>
                      <span className="leading-snug">{concept}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Important Points */}
            <div className="academic-card p-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl flex flex-col justify-between">
              <div>
                <div className="flex items-center space-x-2 text-amber-700 dark:text-amber-400 font-bold text-sm mb-3">
                  <Sparkles className="w-4 h-4" />
                  <span>Important Exam & Review Points</span>
                </div>
                <ul className="space-y-2.5">
                  {(summaryData.important_points || []).map((pt, idx) => (
                    <li key={idx} className="flex items-start space-x-2 text-xs text-slate-700 dark:text-slate-300">
                      <CheckCircle2 className="w-4 h-4 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
                      <span className="leading-snug">{pt}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

          </div>

          {/* Quick Revision Strip */}
          <div className="academic-card p-5 bg-indigo-50/70 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-900/60 rounded-xl">
            <h4 className="text-xs font-bold text-indigo-900 dark:text-indigo-200 uppercase tracking-wider mb-2">
              ⚡ Quick Revision Takeaways
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {(summaryData.quick_revision || []).map((rev, idx) => (
                <div key={idx} className="bg-white dark:bg-slate-900/80 p-2.5 rounded-lg border border-indigo-100 dark:border-indigo-900/50 text-xs text-slate-800 dark:text-slate-200 flex items-center space-x-2">
                  <span className="w-2 h-2 rounded-full bg-indigo-600 dark:bg-indigo-400 flex-shrink-0"></span>
                  <span className="font-medium">{rev}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Source Grounding */}
          <SourceCitation reference={summaryData.source_reference} />
        </div>
      ) : error ? (
        <div className="p-6 rounded-xl border border-rose-200 dark:border-rose-900/50 bg-rose-50/60 dark:bg-rose-950/30 text-rose-800 dark:text-rose-200 text-center space-y-3">
          <AlertCircle className="w-8 h-8 text-rose-500 mx-auto" />
          <p className="text-sm font-semibold">{error}</p>
          <button
            onClick={() => loadSummary(true)}
            className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold rounded-lg shadow-sm transition-all"
          >
            Retry Summary Generation
          </button>
        </div>
      ) : (
        <div className="py-12 text-center text-slate-500 dark:text-slate-400">
          Click "Generate Summary" to summarize this textbook chapter.
        </div>
      )}
    </div>
  );
};
