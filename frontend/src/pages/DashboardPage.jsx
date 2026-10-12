import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, Award, AlertTriangle, BookOpen, 
  ArrowRight, Clock, CheckCircle2, Sparkles, Upload, 
  Layers, BarChart2, Network, Trash2
} from 'lucide-react';
import { 
  ResponsiveContainer, BarChart, Bar, XAxis, 
  YAxis, Tooltip, CartesianGrid, Cell 
} from 'recharts';
import { textbookAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useTextbook } from '../context/TextbookContext';
import { useTheme } from '../context/ThemeContext';

export const DashboardPage = ({ onNavigateWorkspace, onNavigateUpload }) => {
  const { user } = useAuth();
  const { textbooks, selectTextbook, setActiveTab, deleteTextbook, clearAllTextbooks } = useTextbook();
  const { isDark } = useTheme();
  const [performance, setPerformance] = useState(null);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState(null);
  const [clearing, setClearing] = useState(false);

  const handleRemoveSpecific = async (e, tb) => {
    e.stopPropagation();
    const confirmed = window.confirm(`Remove "${tb.title}" from your materials?`);
    if (!confirmed) return;
    try {
      setDeletingId(tb.id);
      await deleteTextbook(tb.id);
    } catch (err) {
      alert('Failed to remove material: ' + (err.response?.data?.detail || err.message));
    } finally {
      setDeletingId(null);
    }
  };

  const handleClearAll = async () => {
    if (!textbooks || textbooks.length === 0) return;
    const confirmed = window.confirm(`Are you sure you want to clear all ${textbooks.length} materials? This will empty your list.`);
    if (!confirmed) return;
    try {
      setClearing(true);
      await clearAllTextbooks();
    } catch (err) {
      alert('Failed to clear materials: ' + (err.response?.data?.detail || err.message));
    } finally {
      setClearing(false);
    }
  };

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true);
        const data = await textbookAPI.getPerformance(user?.id || 'demo_user');
        setPerformance(data);
      } catch (err) {
        console.error('Error fetching dashboard metrics:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
  }, [user]);

  const handleLaunchRevision = (weakTopic) => {
    setActiveTab('adaptive');
    onNavigateWorkspace();
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-fade-in text-slate-900 dark:text-slate-100">
      
      {/* Welcome Banner */}
      <div 
        style={{ backgroundColor: '#0f172a' }}
        className="relative overflow-hidden rounded-2xl p-6 sm:p-7 bg-slate-900 bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white shadow-xl border border-indigo-500/30"
      >
        {/* Subtle ambient decorative glows */}
        <div className="absolute -top-24 -right-24 w-72 h-72 bg-indigo-500/20 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 w-72 h-72 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-5">
          <div className="space-y-2">
            <div className="inline-flex items-center space-x-1.5 bg-indigo-500/25 px-3 py-1 rounded-full text-xs text-indigo-200 font-semibold border border-indigo-400/30 backdrop-blur-xs">
              <Sparkles className="w-3.5 h-3.5 text-indigo-300" />
              <span>Adaptive Study Dashboard</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Welcome back, {user?.name || 'Alex'}!
            </h1>
            <p className="text-xs sm:text-sm text-slate-200 max-w-xl leading-relaxed">
              Your overall textbook mastery is progressing well.{' '}
              {performance?.weak_topics?.[0] ? (
                <>
                  We detected conceptual gaps in{' '}
                  <span className="text-amber-300 font-extrabold bg-amber-500/20 px-2 py-0.5 rounded border border-amber-400/40">
                    {performance.weak_topics[0]}
                  </span>{' '}
                  that require revision.
                </>
              ) : (
                <>Continue your multimodal course reading and interactive diagnostic assessments.</>
              )}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <button
              onClick={() => {
                setActiveTab('graph');
                onNavigateWorkspace();
              }}
              className="inline-flex items-center space-x-1.5 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold rounded-xl border border-emerald-400/40 shadow-sm transition-all duration-150 cursor-pointer"
            >
              <Network className="w-4 h-4 text-emerald-100" />
              <span>Concept Graph</span>
            </button>
            <button
              onClick={onNavigateUpload}
              className="inline-flex items-center space-x-1.5 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl border border-indigo-400/50 shadow-md hover:shadow-indigo-500/25 transition-all duration-150 cursor-pointer"
            >
              <Upload className="w-4 h-4 text-indigo-100" />
              <span>Upload PDF</span>
            </button>
            <button
              onClick={() => {
                setActiveTab('summary');
                onNavigateWorkspace();
              }}
              className="inline-flex items-center space-x-1.5 px-4 py-2.5 bg-white hover:bg-slate-100 text-slate-900 text-xs font-extrabold rounded-xl shadow-md transition-all duration-150 cursor-pointer"
            >
              <span>Open Workspace</span>
              <ArrowRight className="w-4 h-4 text-slate-900" />
            </button>
          </div>
        </div>
      </div>

      {/* 4 Top Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* Learning Progress */}
        <div className="academic-card p-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl flex items-center justify-between">
          <div>
            <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold uppercase tracking-wider">Learning Progress</p>
            <h3 className="text-2xl font-extrabold text-slate-900 dark:text-white mt-1">
              {performance?.overall_progress || 72}%
            </h3>
            <p className="text-3xs text-emerald-600 dark:text-emerald-400 font-medium mt-0.5 flex items-center">
              <TrendingUp className="w-3 h-3 mr-1" />
              +8% from last week
            </p>
          </div>
          <div className="w-12 h-12 rounded-xl bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 flex items-center justify-center">
            <Award className="w-6 h-6" />
          </div>
        </div>

        {/* Quizzes Completed */}
        <div className="academic-card p-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl flex items-center justify-between">
          <div>
            <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold uppercase tracking-wider">Quizzes Taken</p>
            <h3 className="text-2xl font-extrabold text-slate-900 dark:text-white mt-1">
              {performance?.quizzes_completed || 3}
            </h3>
            <p className="text-3xs text-slate-500 dark:text-slate-400 font-medium mt-0.5">
              {performance?.questions_answered || 25} total questions
            </p>
          </div>
          <div className="w-12 h-12 rounded-xl bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
            <CheckCircle2 className="w-6 h-6" />
          </div>
        </div>

        {/* Strong Topics */}
        <div className="academic-card p-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl flex items-center justify-between">
          <div>
            <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold uppercase tracking-wider">Strong Topics</p>
            <h3 className="text-2xl font-extrabold text-emerald-600 dark:text-emerald-400 mt-1">
              {performance?.strong_topics?.length || 4}
            </h3>
            <p className="text-3xs text-slate-500 dark:text-slate-400 font-medium mt-0.5">
              &gt; 75% accuracy
            </p>
          </div>
          <div className="w-12 h-12 rounded-xl bg-teal-50 dark:bg-teal-950/60 text-teal-600 dark:text-teal-400 flex items-center justify-center">
            <Layers className="w-6 h-6" />
          </div>
        </div>

        {/* Weak Topics */}
        <div className="academic-card p-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl flex items-center justify-between">
          <div>
            <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold uppercase tracking-wider">Weak Topics</p>
            <h3 className="text-2xl font-extrabold text-rose-600 dark:text-rose-400 mt-1">
              {performance?.weak_topics?.length || 2}
            </h3>
            <p className="text-3xs text-rose-600 dark:text-rose-400 font-medium mt-0.5">
              Action recommended
            </p>
          </div>
          <div className="w-12 h-12 rounded-xl bg-rose-50 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400 flex items-center justify-center">
            <AlertTriangle className="w-6 h-6" />
          </div>
        </div>

      </div>

      {/* Main 2-Column: Left (Topic Mastery Chart & Diagnostic Cards) & Right (Recent Textbooks & Activity) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left 2 Cols: Topic Mastery Chart & Recommendations */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Personalized Recommendation Hero Card */}
          <div className="academic-card p-6 bg-gradient-to-r from-amber-500/10 via-orange-500/5 to-rose-500/10 border border-amber-200 dark:border-amber-900/50 rounded-xl">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div className="flex items-start space-x-3.5">
                <div className="p-2.5 bg-amber-500 text-white rounded-xl shadow-xs flex-shrink-0">
                  <AlertTriangle className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-3xs font-extrabold uppercase px-2 py-0.5 bg-amber-200 dark:bg-amber-900/60 text-amber-900 dark:text-amber-200 rounded-full">
                    Adaptive Recommendation
                  </span>
                  <h3 className="text-base font-bold text-slate-900 dark:text-white mt-1">
                    {performance?.weak_topics?.[0] ? `Revise: ${performance.weak_topics[0]}` : 'Adaptive Assessment & Revision'}
                  </h3>
                  <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5 leading-relaxed">
                    {performance?.weak_topics?.[0]
                      ? `Targeted remediation drill and misconception-aware diagnostics recommended for ${performance.weak_topics[0]}.`
                      : 'Take your dynamic diagnostic drill in the workspace to get real-time misconception feedback.'}
                  </p>
                </div>
              </div>

              <button
                onClick={() => handleLaunchRevision(performance?.weak_topics?.[0] || 'All')}
                className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 px-5 py-2.5 bg-slate-900 dark:bg-indigo-600 hover:bg-slate-800 dark:hover:bg-indigo-500 text-white text-xs font-bold rounded-xl shadow-sm transition-all flex-shrink-0"
              >
                <span>{performance?.weak_topics?.[0] ? `Revise ${performance.weak_topics[0]} Now` : 'Start Practice Drill'}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Topic Mastery Bar Chart */}
          <div className="academic-card p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
              <div className="flex items-center space-x-2">
                <BarChart2 className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
                <h3 className="font-bold text-slate-900 dark:text-white text-sm">Topic Mastery Breakdown</h3>
              </div>
              <span className="text-3xs text-slate-400 dark:text-slate-500 font-medium">Updated after each AI quiz</span>
            </div>

            <div className="h-64 w-full">
              {performance?.topic_masteries && performance.topic_masteries.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart 
                    data={performance.topic_masteries}
                    margin={{ top: 10, right: 10, left: -20, bottom: 20 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={isDark ? "#334155" : "#f1f5f9"} />
                    <XAxis 
                      dataKey="topic" 
                      tick={{ fontSize: 9, fill: isDark ? '#94a3b8' : '#64748b' }} 
                      interval={0}
                      angle={-15}
                      textAnchor="end"
                    />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: isDark ? '#94a3b8' : '#64748b' }} />
                    <Tooltip 
                      formatter={(val) => [`${val}% Mastery`, 'Accuracy']}
                      contentStyle={{ 
                        backgroundColor: isDark ? '#0f172a' : '#1e293b', 
                        borderColor: isDark ? '#334155' : '#475569',
                        borderRadius: '8px', 
                        color: '#fff', 
                        fontSize: '11px' 
                      }}
                    />
                    <Bar dataKey="mastery_percentage" radius={[4, 4, 0, 0]}>
                      {performance.topic_masteries.map((entry, index) => (
                        <Cell 
                          key={`cell-${index}`} 
                          fill={entry.mastery_percentage >= 75 ? '#10b981' : entry.mastery_percentage >= 60 ? '#f59e0b' : '#ef4444'} 
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-xs text-slate-400 dark:text-slate-500">
                  No quiz history yet. Take your first quiz in the workspace!
                </div>
              )}
            </div>

            <div className="flex items-center justify-center space-x-6 text-2xs text-slate-600 dark:text-slate-400 pt-2 border-t border-slate-100 dark:border-slate-800">
              <span className="flex items-center space-x-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
                <span>Strong (&gt;75%)</span>
              </span>
              <span className="flex items-center space-x-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
                <span>Moderate (60-74%)</span>
              </span>
              <span className="flex items-center space-x-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500"></span>
                <span>Weak (&lt;60%)</span>
              </span>
            </div>
          </div>

          {/* Strong vs Weak Topics Lists */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            
            {/* Strong Topics */}
            <div className="academic-card p-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl">
              <div className="flex items-center space-x-2 text-emerald-700 dark:text-emerald-400 font-bold text-xs uppercase tracking-wider mb-3">
                <CheckCircle2 className="w-4 h-4" />
                <span>Strong Topics</span>
              </div>
              <ul className="space-y-2">
                {(performance?.strong_topics || [
                  "Introduction & Relational Model",
                  "Database Keys & Constraints",
                  "First Normal Form (1NF)",
                  "Transactions & ACID Properties"
                ]).map((t, idx) => (
                  <li key={idx} className="flex items-center justify-between p-2 bg-emerald-50/50 dark:bg-emerald-950/30 rounded-lg text-xs font-medium text-slate-800 dark:text-slate-200 border border-emerald-100 dark:border-emerald-900/40">
                    <span className="truncate pr-2">{t}</span>
                    <span className="text-3xs font-bold text-emerald-700 dark:text-emerald-400 bg-emerald-100 dark:bg-emerald-900/60 px-1.5 py-0.5 rounded">
                      Passed
                    </span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Weak Topics */}
            <div className="academic-card p-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl">
              <div className="flex items-center space-x-2 text-rose-700 dark:text-rose-400 font-bold text-xs uppercase tracking-wider mb-3">
                <AlertTriangle className="w-4 h-4" />
                <span>Weak Topics (Needs Review)</span>
              </div>
              <ul className="space-y-2">
                {(performance?.weak_topics || [
                  "Second Normal Form (2NF)",
                  "Third Normal Form (3NF)"
                ]).map((t, idx) => (
                  <li key={idx} className="flex items-center justify-between p-2 bg-rose-50/50 dark:bg-rose-950/30 rounded-lg text-xs font-medium text-slate-800 dark:text-slate-200 border border-rose-100 dark:border-rose-900/40">
                    <span className="truncate pr-2">{t}</span>
                    <button
                      onClick={() => handleLaunchRevision(t)}
                      className="text-3xs font-bold text-rose-700 dark:text-rose-300 hover:text-rose-900 dark:hover:text-white bg-rose-100 dark:bg-rose-900/60 px-2 py-0.5 rounded hover:bg-rose-200 transition-colors"
                    >
                      Revise &rarr;
                    </button>
                  </li>
                ))}
              </ul>
            </div>

          </div>

        </div>

        {/* Right 1 Col: Recent Textbooks & Activity Timeline */}
        <div className="space-y-6">
          
          {/* Recently Uploaded Textbooks */}
          <div className="academic-card p-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
              <h3 className="font-bold text-slate-900 dark:text-white text-sm flex items-center space-x-2">
                <BookOpen className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
                <span>Textbooks</span>
                {textbooks.length > 0 && (
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400">
                    {textbooks.length}
                  </span>
                )}
              </h3>
              <div className="flex items-center space-x-2">
                {textbooks.length > 0 && (
                  <button
                    type="button"
                    onClick={handleClearAll}
                    disabled={clearing}
                    className="text-rose-500 hover:text-rose-700 dark:text-rose-400 dark:hover:text-rose-300 text-xs font-semibold flex items-center space-x-1 px-2 py-1 rounded-md hover:bg-rose-50 dark:hover:bg-rose-950/40 transition-colors disabled:opacity-50 cursor-pointer"
                    title="Clear all materials and empty list"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>{clearing ? 'Clearing...' : 'Clear'}</span>
                  </button>
                )}
                <button
                  onClick={onNavigateUpload}
                  className="inline-flex items-center space-x-1 px-2.5 py-1 bg-indigo-50 dark:bg-indigo-950/60 hover:bg-indigo-100 dark:hover:bg-indigo-900 text-indigo-600 dark:text-indigo-400 text-xs font-bold rounded-lg border border-indigo-200/60 dark:border-indigo-800 transition-colors cursor-pointer"
                  title="Upload new PDF or course materials"
                >
                  <Upload className="w-3 h-3" />
                  <span>+ Upload</span>
                </button>
              </div>
            </div>

            <div className="space-y-3 max-h-[460px] overflow-y-auto pr-1">
              {textbooks.length === 0 ? (
                <div className="text-center py-8 text-slate-400 dark:text-slate-500 text-xs space-y-3">
                  <BookOpen className="w-9 h-9 mx-auto opacity-30 text-indigo-500" />
                  <p className="font-semibold text-slate-600 dark:text-slate-400">No materials in your library yet.</p>
                  <button
                    type="button"
                    onClick={onNavigateUpload}
                    className="inline-flex items-center space-x-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl shadow-sm transition-all cursor-pointer"
                  >
                    <Upload className="w-3.5 h-3.5" />
                    <span>Upload PDF or Course Slides</span>
                  </button>
                </div>
              ) : (
                textbooks.map((tb) => (
                  <div
                    key={tb.id}
                    className="p-3 bg-slate-50 dark:bg-slate-800/70 hover:bg-indigo-50/50 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl transition-all flex items-center justify-between group"
                  >
                    <div
                      onClick={() => {
                        selectTextbook(tb);
                        onNavigateWorkspace();
                      }}
                      className="flex items-start space-x-3 flex-1 min-w-0 cursor-pointer"
                    >
                      <div className="p-2 bg-indigo-100 dark:bg-indigo-900/60 text-indigo-700 dark:text-indigo-300 rounded-lg group-hover:bg-indigo-600 group-hover:text-white transition-colors flex-shrink-0 mt-0.5">
                        <BookOpen className="w-4 h-4" />
                      </div>
                      <div className="flex-1 min-w-0 pr-2">
                        <h4 className="text-xs font-bold text-slate-900 dark:text-slate-100 truncate group-hover:text-indigo-600 dark:group-hover:text-indigo-400">
                          {tb.title}
                        </h4>
                        <p className="text-3xs text-slate-500 dark:text-slate-400 font-medium mt-0.5">
                          {tb.total_pages} Pages &bull; {tb.chapters?.length || 5} Chapters
                        </p>
                      </div>
                    </div>

                    {/* Specific PDF Remove Button */}
                    <button
                      type="button"
                      disabled={deletingId === tb.id}
                      onClick={(e) => handleRemoveSpecific(e, tb)}
                      title={`Remove "${tb.title}"`}
                      className="p-1.5 text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/60 rounded-lg transition-colors flex-shrink-0 disabled:opacity-50 cursor-pointer"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Recent Quiz Activity Timeline */}
          <div className="academic-card p-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl space-y-4">
            <div className="flex items-center space-x-2 border-b border-slate-100 dark:border-slate-800 pb-3">
              <Clock className="w-4 h-4 text-slate-600 dark:text-slate-400" />
              <h3 className="font-bold text-slate-900 dark:text-white text-sm">Recent Activity</h3>
            </div>

            <div className="space-y-3">
              {(performance?.recent_activity || [
                { topic: "Second Normal Form (2NF)", difficulty: "Medium", score_percentage: 40.0, taken_at: "Today, 3:20 PM" },
                { topic: "Database Keys & Constraints", difficulty: "Easy", score_percentage: 100.0, taken_at: "Today, 11:30 AM" },
                { topic: "First Normal Form (1NF)", difficulty: "Medium", score_percentage: 80.0, taken_at: "Today, 9:15 AM" }
              ]).map((act, idx) => (
                <div key={idx} className="p-2.5 bg-slate-50 dark:bg-slate-800/60 rounded-lg border border-slate-200/80 dark:border-slate-700/80 text-xs">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-slate-800 dark:text-slate-200 truncate pr-2">{act.topic}</span>
                    <span className={`px-1.5 py-0.5 rounded font-mono font-bold text-3xs ${
                      act.score_percentage >= 75 
                        ? 'bg-emerald-100 dark:bg-emerald-900/60 text-emerald-800 dark:text-emerald-300' 
                        : 'bg-rose-100 dark:bg-rose-900/60 text-rose-800 dark:text-rose-300'
                    }`}>
                      {act.score_percentage}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-3xs text-slate-500 dark:text-slate-400">
                    <span>Difficulty: {act.difficulty}</span>
                    <span>{act.taken_at}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

        </div>

      </div>

    </div>
  );
};
