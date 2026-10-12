import React, { useState, useEffect } from 'react';
import { 
  AlertCircle, Sparkles, CheckCircle, RefreshCw, 
  ArrowRight, BookOpen, Layers, CheckCircle2,
  GitBranch, Network 
} from 'lucide-react';
import { textbookAPI } from '../../services/api';
import { useTextbook } from '../../context/TextbookContext';
import { MermaidViewer } from '../../components/MermaidViewer';

export const AdaptiveRevisionTab = ({ onRetakeQuiz }) => {
  const { activeTextbook, setActiveTab, language } = useTextbook();
  const [recommendation, setRecommendation] = useState(null);
  const [misconceptions, setMisconceptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [practiceAnswers, setPracticeAnswers] = useState({});
  const [practiceSubmitted, setPracticeSubmitted] = useState(false);

  const loadRecommendation = async () => {
    try {
      setLoading(true);
      const data = await textbookAPI.getRecommendations('demo_user', null, language || 'en', activeTextbook?.id);
      setRecommendation(data);
      setPracticeAnswers({});
      setPracticeSubmitted(false);

      if (activeTextbook) {
        try {
          const miscData = await textbookAPI.getMisconceptions(activeTextbook.id, 'demo_user');
          setMisconceptions(miscData.misconceptions || []);
        } catch (mErr) {
          console.error('Error fetching misconceptions:', mErr);
        }
      }
    } catch (err) {
      console.error('Error loading recommendations:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRecommendation();
  }, [activeTextbook, language]);

  const handleSelectPractice = (qId, key) => {
    if (practiceSubmitted) return;
    setPracticeAnswers(prev => ({ ...prev, [qId]: key }));
  };

  return (
    <div className="space-y-6 text-slate-900 dark:text-slate-100">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-xl font-bold text-slate-900 dark:text-white">Personalized Adaptive Remediation</h2>
            <span className="text-2xs font-semibold px-2 py-0.5 rounded-full bg-rose-50 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800">
              Targeted Weak Topic
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Automatically curates micro-diagrams, simplified conceptual models, and targeted drills to strengthen identified weaknesses.
          </p>
        </div>

        <div className="flex items-center space-x-2.5">
          <button
            onClick={loadRecommendation}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 text-xs font-semibold rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh Analysis</span>
          </button>
        </div>
      </div>

      {loading ? (
        <div className="py-20 text-center space-y-3">
          <div className="w-10 h-10 border-3 border-indigo-600 dark:border-indigo-400 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-sm font-medium text-slate-600 dark:text-slate-400">
            Analyzing quiz error patterns & constructing targeted remediation module...
          </p>
        </div>
      ) : recommendation ? (
        <div className="space-y-6 animate-fade-in">
          
          {/* Diagnostic Alert Card */}
          <div className="academic-card p-5 bg-gradient-to-r from-amber-50 to-orange-50 dark:from-amber-950/30 dark:to-orange-950/20 border border-amber-200 dark:border-amber-900/50 rounded-xl">
            <div className="flex items-start space-x-3">
              <div className="p-2 bg-amber-500/20 text-amber-800 dark:text-amber-300 rounded-lg flex-shrink-0 mt-0.5">
                <AlertCircle className="w-5 h-5" />
              </div>
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-amber-900 dark:text-amber-200">
                    Target Weak Area: {recommendation.topic}
                  </h3>
                  <div className="flex items-center space-x-1.5">
                    <button
                      onClick={() => setActiveTab('visualize')}
                      className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-lg bg-amber-200/80 hover:bg-amber-300/80 dark:bg-amber-900/60 dark:hover:bg-amber-800/80 text-amber-900 dark:text-amber-200 text-3xs font-bold transition"
                    >
                      <GitBranch className="w-3 h-3" />
                      <span>Visual Diagram</span>
                    </button>
                    <button
                      onClick={() => setActiveTab('graph')}
                      className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-lg bg-amber-200/80 hover:bg-amber-300/80 dark:bg-amber-900/60 dark:hover:bg-amber-800/80 text-amber-900 dark:text-amber-200 text-3xs font-bold transition"
                    >
                      <Network className="w-3 h-3" />
                      <span>Learning Path</span>
                    </button>
                  </div>
                </div>
                <p className="text-xs text-amber-800 dark:text-amber-300 leading-relaxed">
                  {recommendation.weakness_reason}
                </p>
              </div>
            </div>
          </div>

          {/* Active Diagnosed Misconceptions List */}
          {misconceptions && misconceptions.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-xs font-bold text-slate-900 dark:text-white flex items-center space-x-2">
                <Sparkles className="w-4 h-4 text-amber-500" />
                <span>Active Misconception Diagnostics ({misconceptions.length})</span>
              </h4>
              <div className="grid grid-cols-1 gap-3">
                {misconceptions.map((m, idx) => (
                  <div key={idx} className="p-4 bg-amber-50/70 dark:bg-amber-950/25 border border-amber-200 dark:border-amber-800/60 rounded-xl space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-xs text-amber-900 dark:text-amber-200">
                        {m.misconception_title}
                      </span>
                      <span className="text-3xs font-mono font-bold px-2 py-0.5 rounded bg-amber-200/60 dark:bg-amber-900/60 text-amber-900 dark:text-amber-300 capitalize">
                        Confidence: {m.confidence} ({m.occurrence_count}x detected)
                      </span>
                    </div>
                    <p className="text-2xs text-amber-900 dark:text-amber-200/90 leading-relaxed">
                      {m.hypothesis_text}
                    </p>
                    <div className="p-2 bg-white/70 dark:bg-slate-900/60 rounded text-3xs text-slate-700 dark:text-slate-300">
                      <span className="font-bold text-slate-900 dark:text-slate-200">Expected Understanding: </span>
                      {m.expected_understanding}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Remediation Concept Breakdown */}
          <div className="academic-card p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl space-y-4">
            <div className="flex items-center space-x-2 text-indigo-700 dark:text-indigo-400 font-bold text-sm">
              <BookOpen className="w-4 h-4" />
              <span>Simplified Remediation Concept</span>
            </div>
            <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed whitespace-pre-line">
              {recommendation.short_explanation}
            </p>

            <div className="pt-2">
              <h4 className="text-2xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">
                Core Rules to Remember:
              </h4>
              <ul className="space-y-2">
                {recommendation.important_points.map((pt, idx) => (
                  <li key={idx} className="flex items-start space-x-2 text-xs text-slate-700 dark:text-slate-300">
                    <CheckCircle className="w-4 h-4 text-emerald-600 dark:text-emerald-400 flex-shrink-0 mt-0.5" />
                    <span>{pt}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Micro Mermaid Remediation Diagram */}
          {recommendation.mermaid_diagram && (
            <MermaidViewer
              chart={recommendation.mermaid_diagram}
              title={`Remediation Diagram: ${recommendation.topic}`}
              sourceReference="Textbook Grounded Decomposition"
            />
          )}

          {/* Target Practice Questions */}
          {recommendation.practice_questions && recommendation.practice_questions.length > 0 && (
            <div className="academic-card p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2 text-emerald-700 dark:text-emerald-400 font-bold text-sm">
                  <Sparkles className="w-4 h-4" />
                  <span>Targeted Mastery Check ({recommendation.topic})</span>
                </div>
                <span className="text-3xs text-slate-500 dark:text-slate-400 font-medium">
                  {recommendation.practice_questions.length} Remediation Drills
                </span>
              </div>

              <div className="space-y-4 pt-2">
                {recommendation.practice_questions.map((q, idx) => {
                  const selKey = practiceAnswers[q.id];
                  const isCorrect = selKey === q.correct_key;

                  return (
                    <div key={q.id} className="p-4 bg-slate-50 dark:bg-slate-800/60 rounded-xl border border-slate-200 dark:border-slate-700/80 space-y-2.5">
                      <p className="text-xs font-semibold text-slate-900 dark:text-white">
                        {idx + 1}. {q.question}
                      </p>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {q.options.map((opt) => {
                          const isOptSelected = selKey === opt.key;
                          let style = 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200';

                          if (practiceSubmitted) {
                            if (opt.key === q.correct_key) {
                              style = 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-500 text-emerald-900 dark:text-emerald-300 font-semibold';
                            } else if (isOptSelected) {
                              style = 'bg-rose-50 dark:bg-rose-950/40 border-rose-500 text-rose-900 dark:text-rose-300';
                            }
                          } else if (isOptSelected) {
                            style = 'bg-indigo-50 dark:bg-indigo-950/50 border-indigo-600 dark:border-indigo-400 text-indigo-900 dark:text-indigo-200 font-semibold';
                          }

                          return (
                            <div
                              key={opt.key}
                              onClick={() => handleSelectPractice(q.id, opt.key)}
                              className={`p-2.5 rounded-lg border text-xs cursor-pointer select-none transition-all flex items-center space-x-2 ${style}`}
                            >
                              <span className="font-mono text-2xs font-bold w-4 h-4 rounded-full bg-slate-100 dark:bg-slate-700 flex items-center justify-center flex-shrink-0 text-slate-700 dark:text-slate-300">
                                {opt.key}
                              </span>
                              <span>{opt.text}</span>
                            </div>
                          );
                        })}
                      </div>

                      {practiceSubmitted && (
                        <p className={`text-2xs font-medium pt-1 ${isCorrect ? 'text-emerald-700 dark:text-emerald-400' : 'text-rose-700 dark:text-rose-400'}`}>
                          {isCorrect ? '✓ Correct! You mastered this key concept.' : `✗ Incorrect. Correct answer is ${q.correct_key}: ${q.explanation}`}
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>

              <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-3 border-t border-slate-100 dark:border-slate-800">
                <button
                  onClick={() => setPracticeSubmitted(true)}
                  disabled={practiceSubmitted || Object.keys(practiceAnswers).length === 0}
                  className="w-full sm:w-auto px-5 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white font-bold text-xs rounded-xl shadow-sm transition-all"
                >
                  Verify Practice Answers
                </button>

                <button
                  onClick={onRetakeQuiz}
                  className="w-full sm:w-auto inline-flex items-center justify-center space-x-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs rounded-xl shadow-sm transition-all"
                >
                  <span>Retake Full Quiz Assessment</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
};
