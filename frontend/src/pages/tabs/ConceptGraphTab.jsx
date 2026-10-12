import React, { useState, useEffect } from 'react';
import { 
  Network, GitFork, ArrowRight, ArrowLeft, RefreshCw, 
  Sparkles, BookOpen, Presentation, Video, 
  Layers, CheckCircle2, ChevronRight, HelpCircle, 
  Compass, Lightbulb, ExternalLink, ShieldCheck,
  AlertCircle, Play, FileText, Info, Award,
  Check, Lock, AlertTriangle, CheckSquare, Square,
  GitBranch, Target, X, CheckCheck, PlayCircle, Eye,
  ChevronDown, ChevronUp
} from 'lucide-react';
import { textbookAPI } from '../../services/api';
import { useTextbook } from '../../context/TextbookContext';
import { ConceptGraphViewer } from '../../components/ConceptGraphViewer';

export const ConceptGraphTab = () => {
  const { activeTextbook, setActiveTab, language } = useTextbook();
  const [viewMode, setViewMode] = useState('graph'); // 'graph' or 'learning_path'
  const [graphData, setGraphData] = useState(null);
  const [selectedConcept, setSelectedConcept] = useState(null);
  const [conceptDetails, setConceptDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [graphError, setGraphError] = useState(null);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [regenerating, setRegenerating] = useState(false);

  // Innovation 5 & Multimodal Adaptive Learning Path state
  const [targetConceptName, setTargetConceptName] = useState('');
  const [learningPathData, setLearningPathData] = useState(null);
  const [pathLoading, setPathLoading] = useState(false);
  const [studyingProgress, setStudyingProgress] = useState({});

  // Multimodal verification & resource modal states
  const [activeVerificationStep, setActiveVerificationStep] = useState(null);
  const [verificationAnswer, setVerificationAnswer] = useState('');
  const [verificationSubmitting, setVerificationSubmitting] = useState(false);
  const [verificationResult, setVerificationResult] = useState(null);
  const [selectedResourcePreview, setSelectedResourcePreview] = useState(null);
  const [expandedAlternatives, setExpandedAlternatives] = useState({});

  // Escape key handler to close any active modal
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        if (activeVerificationStep) {
          setActiveVerificationStep(null);
        } else if (selectedResourcePreview) {
          setSelectedResourcePreview(null);
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [activeVerificationStep, selectedResourcePreview]);


  // Load Graph Data
  const loadGraph = async (forceRegenerate = false) => {
    if (!activeTextbook) return;
    try {
      setGraphError(null);
      if (forceRegenerate) setRegenerating(true);
      else setLoading(true);

      const data = forceRegenerate 
        ? await textbookAPI.generateConceptGraph(activeTextbook.id, true)
        : await textbookAPI.getConceptGraph(activeTextbook.id);

      setGraphData(data);

      // Auto-select first concept if none selected
      if (data.nodes && data.nodes.length > 0) {
        if (!selectedConcept) {
          handleSelectConcept(data.nodes[0]);
        }
        if (!targetConceptName) {
          // Set default target concept
          setTargetConceptName(data.nodes[data.nodes.length - 1].name);
        }
      }
    } catch (err) {
      console.error('Error fetching concept graph:', err);
      setGraphError(err.response?.data?.detail || err.message || 'Unable to extract concept graph. Click retry.');
    } finally {
      setLoading(false);
      setRegenerating(false);
    }
  };

  useEffect(() => {
    loadGraph(false);
  }, [activeTextbook]);

  // Load Granular Concept Details when Node is Clicked
  const handleSelectConcept = async (node) => {
    setSelectedConcept(node);
    if (!activeTextbook) return;
    try {
      setDetailsLoading(true);
      const details = await textbookAPI.getConceptDetails(activeTextbook.id, node.id);
      setConceptDetails(details);
    } catch (err) {
      console.error('Error fetching concept details:', err);
    } finally {
      setDetailsLoading(false);
    }
  };

  // Load Personalized Learning Path (Innovation 5)
  const loadPersonalizedPath = async (targetConcept = targetConceptName) => {
    if (!activeTextbook) return;
    try {
      setPathLoading(true);
      const pathRes = await textbookAPI.getPersonalizedLearningPath(
        activeTextbook.id,
        targetConcept || null,
        'demo_user',
        language || 'en'
      );
      setLearningPathData(pathRes);
      if (pathRes.target_concept && !targetConceptName) {
        setTargetConceptName(pathRes.target_concept);
      }
    } catch (err) {
      console.error('Error loading personalized learning path:', err);
    } finally {
      setPathLoading(false);
    }
  };

  useEffect(() => {
    if (activeTextbook && (viewMode === 'learning_path' || targetConceptName)) {
      loadPersonalizedPath(targetConceptName);
    }
  }, [activeTextbook, viewMode, targetConceptName, language]);

  // Handle student marking a concept as studied (Innovation 5)
  const handleToggleStudied = async (step) => {
    if (!activeTextbook) return;
    const isCurrentlyStudied = step.mastery_status === 'studied' || studyingProgress[step.concept_id] === 'studied';
    const newStatus = isCurrentlyStudied ? 'ready' : 'studied';

    setStudyingProgress(prev => ({
      ...prev,
      [step.concept_id]: newStatus
    }));

    try {
      await textbookAPI.updateConceptProgress(
        activeTextbook.id,
        step.concept_id,
        step.concept_name,
        newStatus,
        'demo_user'
      );
      // Reload path to sync statuses
      loadPersonalizedPath(targetConceptName);
    } catch (err) {
      console.error('Error updating concept study progress:', err);
    }
  };

  // Open targeted verification assessment modal

  const handleOpenVerification = (step) => {
    setActiveVerificationStep(step);
    setVerificationAnswer('');
    setVerificationResult(null);
  };

  // Submit targeted assessment verification
  const handleSubmitVerification = async () => {
    if (!activeTextbook || !activeVerificationStep || !verificationAnswer.trim()) return;
    try {
      setVerificationSubmitting(true);
      const q = activeVerificationStep.targeted_assessment || {};
      const res = await textbookAPI.verifyLearningPathStep({
        courseId: activeTextbook.id,
        conceptName: activeVerificationStep.concept_name,
        questionId: q.id || `q_${activeVerificationStep.concept_id}`,
        studentAnswer: verificationAnswer.trim(),
        targetConcept: targetConceptName,
        stepId: activeVerificationStep.concept_id,
        questionType: q.question_type || 'mcq',
        questionText: q.question || '',
        correctAnswer: q.expected_answer || q.correct_key || '',
        options: q.options || [],
        userId: 'demo_user',
        language: language || 'en'
      });
      setVerificationResult(res);
      if (res.refreshed_learning_path) {
        setLearningPathData(res.refreshed_learning_path);
      } else {
        loadPersonalizedPath(targetConceptName);
      }
    } catch (err) {
      console.error('Error verifying step:', err);
      let errorMsg = 'Verification could not be evaluated.';
      const rawDetail = err.response?.data?.detail;
      if (typeof rawDetail === 'string') {
        errorMsg = rawDetail;
      } else if (Array.isArray(rawDetail)) {
        errorMsg = rawDetail.map(d => (typeof d === 'string' ? d : d.msg || JSON.stringify(d))).join('; ');
      } else if (rawDetail && typeof rawDetail === 'object') {
        errorMsg = rawDetail.msg || rawDetail.message || JSON.stringify(rawDetail);
      } else if (err.message) {
        errorMsg = err.message;
      }
      setVerificationResult({
        status: 'error',
        is_correct: false,
        score: 0.0,
        feedback: errorMsg
      });
    } finally {
      setVerificationSubmitting(false);
    }
  };

  const toggleAlternative = (conceptId) => {
    setExpandedAlternatives(prev => ({
      ...prev,
      [conceptId]: !prev[conceptId]
    }));
  };

  const renderModalityBadge = (type) => {
    switch (type) {
      case 'video_segment':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-3xs font-extrabold bg-rose-50 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800">
            <Video className="w-3 h-3 text-rose-500" />
            <span>Lecture Video</span>
          </span>
        );
      case 'presentation_slide':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-3xs font-extrabold bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
            <Presentation className="w-3 h-3 text-amber-500" />
            <span>Slide Deck</span>
          </span>
        );
      case 'diagram':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-3xs font-extrabold bg-cyan-50 dark:bg-cyan-950/60 text-cyan-700 dark:text-cyan-300 border border-cyan-200 dark:border-cyan-800">
            <Layers className="w-3 h-3 text-cyan-500" />
            <span>Course Diagram</span>
          </span>
        );
      case 'visual_model':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-3xs font-extrabold bg-purple-50 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800">
            <Sparkles className="w-3 h-3 text-purple-500" />
            <span>Visual Model</span>
          </span>
        );
      case 'worked_example':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-3xs font-extrabold bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
            <Lightbulb className="w-3 h-3 text-blue-500" />
            <span>Worked Example</span>
          </span>
        );
      case 'targeted_quiz':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-3xs font-extrabold bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
            <Award className="w-3 h-3 text-emerald-500" />
            <span>Targeted Quiz</span>
          </span>
        );
      case 'pdf_passage':
      default:
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-3xs font-extrabold bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
            <FileText className="w-3 h-3 text-indigo-500" />
            <span>Textbook Passage</span>
          </span>
        );
    }
  };

  const renderSourceLocationText = (res) => {
    if (!res) return 'Verified Course Material';
    if (res.page_number) {
      return `${res.filename} • Page ${res.page_number}`;
    }
    if (res.slide_number) {
      return `${res.filename} • Slide ${res.slide_number}`;
    }
    if (res.timestamp_str) {
      return `${res.filename} • Time ${res.timestamp_str}`;
    }
    if (res.provenance_ref) {
      return `${res.filename} • ${res.provenance_ref}`;
    }
    return res.filename || 'Course Material';
  };

  return (

    <div className="space-y-6 text-slate-900 dark:text-slate-100">
      
      {/* Top Header & View Mode Switcher */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center space-x-2">
              <Network className="w-5 h-5 text-indigo-500" />
              <span>Concept Graph & Personalized Learning Paths</span>
            </h2>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Explore the course knowledge network or follow an adaptive learning path personalized by your assessment results and active misconceptions.
          </p>
        </div>

        {/* View Switcher & Action Buttons */}
        <div className="flex items-center space-x-2">
          <div className="flex items-center p-1 bg-slate-100 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700">
            <button
              onClick={() => setViewMode('graph')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                viewMode === 'graph'
                  ? 'bg-white dark:bg-slate-900 text-indigo-600 dark:text-indigo-400 shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <Network className="w-3.5 h-3.5" />
              <span>Concept Graph</span>
            </button>
            <button
              onClick={() => {
                setViewMode('learning_path');
                loadPersonalizedPath(targetConceptName);
              }}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                viewMode === 'learning_path'
                  ? 'bg-white dark:bg-slate-900 text-emerald-600 dark:text-emerald-400 shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <GitFork className="w-3.5 h-3.5" />
              <span>Personalized Learning Path</span>
            </button>
          </div>

          <button
            onClick={() => loadGraph(true)}
            disabled={regenerating}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-indigo-50 hover:bg-indigo-100 dark:bg-indigo-950/70 dark:hover:bg-indigo-900 text-indigo-700 dark:text-indigo-300 rounded-lg text-xs font-bold border border-indigo-200 dark:border-indigo-800/80 transition disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${regenerating ? 'animate-spin' : ''}`} />
            <span>{regenerating ? 'Re-indexing...' : 'Re-index'}</span>
          </button>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* VIEW 1: PERSONALIZED LEARNING PATHS (Innovation 5) */}
      {/* ========================================================================= */}
      {viewMode === 'learning_path' && (
        <div className="space-y-6 animate-fade-in">
          
          {/* Target Concept Selector & Personalization Header */}
          <div className="academic-card p-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl space-y-4 shadow-sm">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="space-y-1">
                <span className="text-3xs font-extrabold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 flex items-center space-x-1.5">
                  <GitFork className="w-3.5 h-3.5" />
                  <span>Adaptive Learning Pathway</span>
                </span>
                <h3 className="text-base font-bold text-slate-900 dark:text-white">
                  Target Concept: <span className="text-indigo-600 dark:text-indigo-400">{learningPathData?.target_concept || targetConceptName}</span>
                </h3>
              </div>

              {/* Target Concept dropdown selector */}
              <div className="flex items-center space-x-2">
                <span className="text-xs font-medium text-slate-600 dark:text-slate-400">Target Goal:</span>
                <select
                  value={targetConceptName}
                  onChange={(e) => {
                    const newTarget = e.target.value;
                    setTargetConceptName(newTarget);
                    loadPersonalizedPath(newTarget);
                  }}
                  className="text-xs bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg px-2.5 py-1.5 font-semibold text-slate-800 dark:text-slate-200 shadow-2xs focus:ring-1 focus:ring-emerald-500 focus:outline-none max-w-xs truncate"
                >
                  {(learningPathData?.available_target_concepts || graphData?.nodes?.map(n => n.name) || []).map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Personalization Status Pill */}
            <div className="flex flex-wrap items-center justify-between gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
              <div className="flex items-center space-x-2">
                {learningPathData?.is_personalized_with_assessment ? (
                  <span className="inline-flex items-center space-x-1.5 text-3xs font-bold px-2.5 py-1 rounded-full bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
                    <span>Personalized via Assessment & Diagnostic History</span>
                  </span>
                ) : (
                  <span className="inline-flex items-center space-x-1.5 text-3xs font-bold px-2.5 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-300 dark:border-slate-700">
                    <Info className="w-3.5 h-3.5 text-slate-500" />
                    <span>Standard Prerequisite Pathway (Complete a Quiz to unlock adaptive mastery)</span>
                  </span>
                )}
              </div>

              {/* Progress Counters */}
              {learningPathData && (
                <span className="text-2xs font-semibold text-slate-500 dark:text-slate-400">
                  Step Progress: <span className="font-bold text-slate-900 dark:text-white">{learningPathData.completed_steps} of {learningPathData.total_steps} Verified/Completed</span>
                </span>
              )}
            </div>
          </div>

          {/* Innovation: Student Learning Gap Diagnosis Card */}
          {learningPathData?.student_learning_gap_diagnosis && (
            <div className="academic-card p-4 bg-slate-50 dark:bg-slate-900/90 border border-slate-200 dark:border-slate-800 rounded-2xl space-y-2.5 shadow-2xs">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center space-x-2">
                  <Compass className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
                  <h4 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                    Student Learning Gap Diagnosis
                  </h4>
                </div>
                <div className="flex flex-wrap items-center gap-1.5 text-3xs font-semibold">
                  <span className="px-2 py-0.5 rounded-full bg-rose-100 dark:bg-rose-950/80 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800">
                    Demonstrated Gaps: {learningPathData.student_learning_gap_diagnosis.demonstrated_gaps_count}
                  </span>
                  <span className="px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-950/80 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
                    Active Misconceptions: {learningPathData.student_learning_gap_diagnosis.active_misconceptions_count}
                  </span>
                  <span className="px-2 py-0.5 rounded-full bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                    Untested Prerequisites: {learningPathData.student_learning_gap_diagnosis.untested_prerequisites_count}
                  </span>
                  <span className="px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                    Verified Foundations: {learningPathData.student_learning_gap_diagnosis.verified_prerequisites_count}
                  </span>
                </div>
              </div>
              <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                {learningPathData.student_learning_gap_diagnosis.diagnostic_summary}
              </p>
            </div>
          )}

          {/* Next Recommended Concept Action Card (Enhanced with Multimodal Resource) */}
          {learningPathData && (
            <div className="academic-card p-5 bg-gradient-to-r from-indigo-50/80 via-emerald-50/50 to-slate-50 dark:from-indigo-950/40 dark:via-emerald-950/20 dark:to-slate-900 border border-indigo-200 dark:border-indigo-800/80 rounded-2xl space-y-3 shadow-xs">
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                <div className="flex items-start space-x-3">
                  <div className="p-2.5 bg-indigo-600 text-white rounded-xl flex-shrink-0 shadow-xs mt-0.5">
                    <Sparkles className="w-5 h-5" />
                  </div>
                  <div className="space-y-1">
                    <span className="text-3xs font-extrabold uppercase tracking-wider text-indigo-700 dark:text-indigo-400">
                      Recommended Next Step #{learningPathData.next_recommended_step_number} • {learningPathData.recommended_action_type?.replace('_', ' ')}
                    </span>
                    <h4 className="text-base font-extrabold text-slate-900 dark:text-white">
                      {learningPathData.next_recommended_concept}
                    </h4>
                    <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed max-w-2xl">
                      {learningPathData.recommendation_rationale}
                    </p>
                  </div>
                </div>

                {/* Quick Action buttons */}
                <div className="flex flex-wrap sm:flex-col gap-2 flex-shrink-0">
                  <button
                    onClick={() => setActiveTab('visualize')}
                    className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-lg shadow-xs transition"
                  >
                    <GitBranch className="w-3.5 h-3.5" />
                    <span>View Visual Diagram</span>
                  </button>
                  <button
                    onClick={() => setActiveTab('quiz')}
                    className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-200 text-xs font-bold rounded-lg transition"
                  >
                    <Award className="w-3.5 h-3.5 text-amber-500" />
                    <span>Take Mastery Quiz</span>
                  </button>
                </div>
              </div>

              {/* Multimodal Recommended Resource Spotlight */}
              {learningPathData.next_recommended_resource && (
                <div className="p-3.5 bg-white/90 dark:bg-slate-900/90 border border-indigo-200/80 dark:border-indigo-800/60 rounded-xl space-y-2 mt-2 shadow-2xs">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center space-x-2">
                      {renderModalityBadge(learningPathData.next_recommended_resource.resource_type)}
                      <span className="text-xs font-bold text-slate-900 dark:text-white">
                        {learningPathData.next_recommended_resource.title}
                      </span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="text-3xs font-semibold px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                        {renderSourceLocationText(learningPathData.next_recommended_resource)}
                      </span>
                      <button
                        onClick={() => setSelectedResourcePreview(learningPathData.next_recommended_resource)}
                        className="px-2.5 py-1 rounded-lg bg-indigo-50 hover:bg-indigo-100 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 text-3xs font-bold border border-indigo-200 dark:border-indigo-800 flex items-center space-x-1 transition"
                      >
                        <Eye className="w-3 h-3" />
                        <span>Inspect Material</span>
                      </button>
                      <button
                        onClick={() => {
                          const targetStep = learningPathData.steps?.find(s => s.concept_name === learningPathData.next_recommended_concept);
                          if (targetStep) handleOpenVerification(targetStep);
                        }}
                        className="px-2.5 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-3xs font-bold flex items-center space-x-1 transition shadow-2xs"
                      >
                        <Target className="w-3 h-3" />
                        <span>Verify Understanding</span>
                      </button>
                    </div>
                  </div>
                  <p className="text-3xs text-slate-600 dark:text-slate-300 leading-relaxed font-mono bg-slate-50 dark:bg-slate-800/50 p-2 rounded-lg line-clamp-2">
                    "{learningPathData.next_recommended_resource.content_snippet}"
                  </p>
                  {learningPathData.next_recommended_resource.selection_criteria && (
                    <p className="text-3xs text-indigo-700 dark:text-indigo-400 font-medium">
                      <span className="font-bold">Selection Rationale: </span>
                      {learningPathData.next_recommended_resource.selection_criteria}
                    </p>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Step-by-Step Path Cards Sequence */}
          {pathLoading ? (
            <div className="py-20 text-center space-y-3">
              <div className="w-10 h-10 border-3 border-emerald-500 border-t-transparent rounded-full animate-spin mx-auto" />
              <p className="text-xs font-semibold text-slate-400">Building personalized learning path with topological prerequisite sort...</p>
            </div>
          ) : learningPathData?.steps && (
            <div className="space-y-3">
              <h4 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider flex items-center space-x-2">
                <span>Personalized Concept Steps ({learningPathData.steps.length}):</span>
              </h4>

              <div className="space-y-3">
                {learningPathData.steps.map((step, idx) => {
                  const isNext = step.concept_name === learningPathData.next_recommended_concept;
                  const isTarget = step.is_target;
                  const isStudied = step.mastery_status === 'studied' || studyingProgress[step.concept_id] === 'studied';
                  
                  return (
                    <div
                      key={step.concept_id || idx}
                      className={`p-4 rounded-2xl border transition-all ${
                        isNext
                          ? 'bg-white dark:bg-slate-900 border-indigo-500 ring-2 ring-indigo-500/20 shadow-sm'
                          : isTarget
                          ? 'bg-white dark:bg-slate-900 border-purple-400/80 dark:border-purple-600/80 shadow-xs'
                          : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800'
                      }`}
                    >
                      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                        <div className="flex items-start space-x-3">
                          {/* Step Number Circle */}
                          <div className={`w-8 h-8 rounded-xl flex items-center justify-center font-bold text-xs flex-shrink-0 ${
                            step.mastery_status === 'mastered'
                              ? 'bg-emerald-600 text-white'
                              : step.mastery_status === 'needs_revision'
                              ? 'bg-rose-600 text-white'
                              : isNext
                              ? 'bg-indigo-600 text-white animate-pulse'
                              : isTarget
                              ? 'bg-purple-600 text-white'
                              : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300'
                          }`}>
                            {step.step_number}
                          </div>

                          <div className="space-y-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <h5 className="text-sm font-bold text-slate-900 dark:text-white">
                                {step.concept_name}
                              </h5>
                              <span className="text-3xs font-semibold px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                                {step.topic}
                              </span>
                              {step.is_target && (
                                <span className="text-3xs font-extrabold px-2 py-0.5 rounded bg-purple-100 dark:bg-purple-950 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800">
                                  🎯 Target Goal
                                </span>
                              )}
                              {step.is_prerequisite && (
                                <span className="text-3xs font-semibold px-2 py-0.5 rounded bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                                  Prerequisite Foundation
                                </span>
                              )}
                              {step.is_followup && (
                                <span className="text-3xs font-semibold px-2 py-0.5 rounded bg-cyan-100 dark:bg-cyan-950 text-cyan-700 dark:text-cyan-300 border border-cyan-200 dark:border-cyan-800">
                                  Advanced Follow-up
                                </span>
                              )}
                            </div>

                            <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                              {step.description}
                            </p>

                            {/* Recommendation / Mastery Rationale */}
                            <div className="flex items-center space-x-1.5 text-2xs text-slate-500 dark:text-slate-400 mt-1">
                              <span className="font-bold">Recommendation:</span>
                              <span>{step.recommendation_reason}</span>
                            </div>
                          </div>
                        </div>

                        {/* Status Badge & Actions */}
                        <div className="flex flex-wrap sm:flex-col items-end gap-2 flex-shrink-0 self-start">
                          {/* Mastery Status Pill */}
                          {step.mastery_status === 'mastered' ? (
                            <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-3xs font-extrabold bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-200 border border-emerald-300 dark:border-emerald-800">
                              <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                              <span>Mastered ({step.mastery_percentage}% Quiz Accuracy)</span>
                            </span>
                          ) : step.mastery_status === 'needs_revision' ? (
                            <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-3xs font-extrabold bg-rose-100 dark:bg-rose-950 text-rose-800 dark:text-rose-200 border border-rose-300 dark:border-rose-800">
                              <AlertTriangle className="w-3 h-3 text-rose-600" />
                              <span>Needs Revision</span>
                            </span>
                          ) : isStudied ? (
                            <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-3xs font-extrabold bg-cyan-100 dark:bg-cyan-950 text-cyan-800 dark:text-cyan-200 border border-cyan-300 dark:border-cyan-800">
                              <Check className="w-3 h-3 text-cyan-600" />
                              <span>Self-Studied (Untested)</span>
                            </span>
                          ) : isNext ? (
                            <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-3xs font-extrabold bg-indigo-100 dark:bg-indigo-950 text-indigo-800 dark:text-indigo-200 border border-indigo-300 dark:border-indigo-800">
                              <Sparkles className="w-3 h-3 text-indigo-600" />
                              <span>Ready / Next Up</span>
                            </span>
                          ) : (
                            <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-3xs font-extrabold bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                              <Lock className="w-3 h-3" />
                              <span>Step #{step.step_number}</span>
                            </span>
                          )}

                          {/* Quick Interactive Actions */}
                          <div className="flex items-center space-x-1.5 mt-1">
                            <button
                              onClick={() => handleToggleStudied(step)}
                              title={isStudied ? "Mark unstudied" : "Mark studied"}
                              className={`p-1.5 rounded-lg border text-2xs font-semibold flex items-center space-x-1 transition ${
                                isStudied
                                  ? 'bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border-emerald-200'
                                  : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:bg-slate-50'
                              }`}
                            >
                              {isStudied ? <CheckSquare className="w-3.5 h-3.5 text-emerald-600" /> : <Square className="w-3.5 h-3.5" />}
                              <span>{isStudied ? 'Studied' : 'Mark Studied'}</span>
                            </button>
                            <button
                              onClick={() => setActiveTab('visualize')}
                              className="p-1.5 rounded-lg bg-indigo-50 hover:bg-indigo-100 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 transition"
                              title="View Visual Diagram"
                            >
                              <GitBranch className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => setActiveTab('explain')}
                              className="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 transition"
                              title="Study Concept"
                            >
                              <BookOpen className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>
                      </div>

                      {/* Multimodal Resource Recommendation for Step */}
                      {step.recommended_resource && (
                        <div className="mt-3 p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/80 space-y-2">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <div className="flex items-center space-x-2">
                              {renderModalityBadge(step.recommended_resource.resource_type)}
                              <span className="text-3xs font-bold text-slate-700 dark:text-slate-300">
                                {renderSourceLocationText(step.recommended_resource)}
                              </span>
                            </div>
                            <div className="flex items-center space-x-1.5">
                              <button
                                onClick={() => setSelectedResourcePreview(step.recommended_resource)}
                                className="px-2 py-1 rounded bg-indigo-50 hover:bg-indigo-100 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 text-3xs font-bold border border-indigo-200 dark:border-indigo-800 flex items-center space-x-1 transition"
                              >
                                <Eye className="w-3 h-3" />
                                <span>Inspect Source</span>
                              </button>
                              {step.targeted_assessment && (
                                <button
                                  onClick={() => handleOpenVerification(step)}
                                  className="px-2 py-1 rounded bg-emerald-600 hover:bg-emerald-700 text-white text-3xs font-bold flex items-center space-x-1 transition shadow-2xs"
                                >
                                  <Target className="w-3 h-3" />
                                  <span>Verify Understanding</span>
                                </button>
                              )}
                            </div>
                          </div>

                          <p className="text-3xs text-slate-600 dark:text-slate-400 italic line-clamp-2 leading-relaxed">
                            "{step.recommended_resource.content_snippet}"
                          </p>

                          {step.recommended_resource.selection_criteria && (
                            <div className="text-3xs text-slate-500 dark:text-slate-400 flex items-center space-x-1">
                              <span className="font-semibold text-slate-700 dark:text-slate-300">Selection Criteria:</span>
                              <span className="truncate">{step.recommended_resource.selection_criteria}</span>
                            </div>
                          )}

                          {/* Alternative Resources Toggle */}
                          {step.alternative_resources && step.alternative_resources.length > 0 && (
                            <div className="pt-1.5 border-t border-slate-200 dark:border-slate-700/60">
                              <button
                                onClick={() => toggleAlternative(step.concept_id)}
                                className="text-3xs font-bold text-indigo-600 dark:text-indigo-400 hover:underline flex items-center space-x-1"
                              >
                                <span>{expandedAlternatives[step.concept_id] ? 'Hide' : 'View'} {step.alternative_resources.length} Alternative Format{step.alternative_resources.length > 1 ? 's' : ''}</span>
                                {expandedAlternatives[step.concept_id] ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                              </button>

                              {expandedAlternatives[step.concept_id] && (
                                <div className="mt-2 space-y-1.5 pl-2 border-l-2 border-indigo-300 dark:border-indigo-700">
                                  {step.alternative_resources.map((alt, aIdx) => (
                                    <div 
                                      key={alt.resource_id || aIdx}
                                      className="flex items-center justify-between p-2 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-3xs"
                                    >
                                      <div className="flex items-center space-x-2">
                                        {renderModalityBadge(alt.resource_type)}
                                        <span className="font-medium text-slate-700 dark:text-slate-300 truncate max-w-xs">
                                          {renderSourceLocationText(alt)}
                                        </span>
                                      </div>
                                      <button
                                        onClick={() => setSelectedResourcePreview(alt)}
                                        className="px-2 py-0.5 rounded bg-slate-100 hover:bg-slate-200 dark:bg-slate-700 text-slate-800 dark:text-slate-200 font-semibold"
                                      >
                                        View
                                      </button>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Active Misconception Alert if diagnosed */}
                      {step.has_active_misconception && (
                        <div className="mt-3 p-3 bg-rose-50/80 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800/80 rounded-xl flex items-start space-x-2 text-xs">
                          <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
                          <div className="space-y-0.5">
                            <span className="font-bold text-rose-900 dark:text-rose-200">
                              Active Misconception: {step.active_misconception_title}
                            </span>
                            <p className="text-3xs text-rose-800 dark:text-rose-300 leading-relaxed">
                              We recommend viewing the visual diagram and reviewing targeted remediation before testing again.
                            </p>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

        </div>
      )}


      {/* ========================================================================= */}
      {/* VIEW 2: ORIGINAL SOURCE-LINKED CONCEPT GRAPH (Innovation 2) */}
      {/* ========================================================================= */}
      {viewMode === 'graph' && (
        <div className="space-y-6 animate-fade-in">
          
          {/* Stats Bar */}
          {graphData?.stats && (
            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-5 gap-3">
              <div className="p-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl">
                <span className="text-3xs text-slate-400 font-bold uppercase tracking-wider">Concepts Discovered</span>
                <p className="text-lg font-extrabold text-indigo-600 dark:text-indigo-400 mt-0.5">
                  {graphData.stats.total_concepts}
                </p>
              </div>
              <div className="p-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl">
                <span className="text-3xs text-slate-400 font-bold uppercase tracking-wider">Prerequisite Links</span>
                <p className="text-lg font-extrabold text-emerald-600 dark:text-emerald-400 mt-0.5">
                  {graphData.stats.total_prerequisites}
                </p>
              </div>
              <div className="p-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl">
                <span className="text-3xs text-slate-400 font-bold uppercase tracking-wider">Cross-Modal Links</span>
                <p className="text-lg font-extrabold text-cyan-600 dark:text-cyan-400 mt-0.5">
                  {graphData.stats.cross_modal_concepts}
                </p>
              </div>
              <div className="p-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl">
                <span className="text-3xs text-slate-400 font-bold uppercase tracking-wider">Total Provenances</span>
                <p className="text-lg font-extrabold text-amber-600 dark:text-amber-400 mt-0.5">
                  {graphData.stats.total_sources}
                </p>
              </div>
              <div className="p-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl col-span-2 sm:col-span-1">
                <span className="text-3xs text-slate-400 font-bold uppercase tracking-wider">Course Topics</span>
                <p className="text-lg font-extrabold text-purple-600 dark:text-purple-400 mt-0.5">
                  {graphData.stats.total_topics}
                </p>
              </div>
            </div>
          )}

          {/* Recommended Learning Path Sequence */}
          {graphData?.learning_paths && graphData.learning_paths.length > 0 && (
            <div className="p-4 bg-slate-900 border-2 border-emerald-500/40 rounded-2xl shadow-xl">
              <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                <div className="flex items-center space-x-2">
                  <div className="px-3 py-1 rounded-lg bg-emerald-500/20 border border-emerald-400/50 text-emerald-300 font-extrabold text-xs uppercase tracking-wider flex items-center space-x-2 shadow-xs">
                    <GitFork className="w-4 h-4 text-emerald-400" />
                    <span>Recommended Prerequisite Sequence</span>
                  </div>
                </div>
                <span className="text-2xs font-semibold text-slate-400">
                  Follow this sequence to master concepts step-by-step
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-2 text-xs font-bold text-white">
                {graphData.learning_paths[0].map((step, idx) => {
                  const cleanStep = step.replace(/^\d+[\.\s\-]+/, '');
                  const displayStep = cleanStep.trim() || step;

                  return (
                    <React.Fragment key={idx}>
                      <button 
                        type="button"
                        onClick={() => {
                          const matched = graphData.nodes.find(n => n.name.toLowerCase() === step.toLowerCase());
                          if (matched) handleSelectConcept(matched);
                        }}
                        className="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-white rounded-xl border border-slate-600 hover:border-emerald-400 cursor-pointer transition shadow-md flex items-center space-x-2.5 group"
                        title={`Jump to ${step} in graph`}
                      >
                        <span className="w-5 h-5 rounded-md bg-emerald-500 text-slate-950 text-xs flex items-center justify-center font-black shrink-0">
                          {idx + 1}
                        </span>
                        <span className="group-hover:text-emerald-200 transition-colors">{displayStep}</span>
                      </button>
                      {idx < graphData.learning_paths[0].length - 1 && (
                        <ArrowRight className="w-4 h-4 text-emerald-400 shrink-0" />
                      )}
                    </React.Fragment>
                  );
                })}
              </div>
            </div>
          )}

          {/* Main Graph Interactive Canvas */}
          {loading ? (
            <div className="w-full h-[620px] rounded-2xl bg-slate-950 border border-slate-800 flex flex-col items-center justify-center space-y-3">
              <div className="w-10 h-10 border-3 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
              <p className="text-xs font-semibold text-slate-400">Extracting course concepts, sources, and prerequisites...</p>
            </div>
          ) : graphError && (!graphData || !graphData.nodes || graphData.nodes.length === 0) ? (
            <div className="w-full h-[620px] rounded-2xl bg-slate-950 border border-slate-800 flex flex-col items-center justify-center p-6 text-center space-y-4">
              <div className="w-12 h-12 rounded-full bg-rose-950/60 border border-rose-800 flex items-center justify-center text-rose-400">
                <AlertCircle className="w-6 h-6" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-white mb-1">Concept Graph Notice</h4>
                <p className="text-xs text-slate-400 max-w-md">{graphError}</p>
              </div>
              <button
                onClick={() => loadGraph(true)}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg shadow-sm transition flex items-center space-x-1.5"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Retry Concept Graph</span>
              </button>
            </div>
          ) : (
            <ConceptGraphViewer
              graph={graphData}
              selectedConceptId={selectedConcept?.id}
              onSelectConcept={handleSelectConcept}
            />
          )}

          {/* Concept Details & Multimodal Provenance Panel */}
          {selectedConcept && (
            <div className="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl space-y-6 shadow-sm">
              
              {/* Header */}
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="text-3xs font-extrabold px-2.5 py-0.5 rounded-md bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 border border-indigo-300 dark:border-indigo-800 uppercase">
                      {selectedConcept.topic}
                    </span>
                    {selectedConcept.subtopic && selectedConcept.subtopic !== selectedConcept.topic && (
                      <span className="text-3xs font-semibold text-slate-500 dark:text-slate-400">
                        &bull; {selectedConcept.subtopic}
                      </span>
                    )}
                  </div>
                  <h3 className="text-2xl font-extrabold text-slate-900 dark:text-white mt-1.5">
                    {selectedConcept.name}
                  </h3>
                  <p className="text-xs text-slate-600 dark:text-slate-300 mt-2 leading-relaxed max-w-3xl">
                    {selectedConcept.description}
                  </p>
                </div>

                {/* Quick action buttons */}
                <div className="flex flex-wrap sm:flex-col gap-2 flex-shrink-0">
                  <button
                    onClick={() => setActiveTab('explain')}
                    className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-bold shadow-xs transition"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>Adaptive Explain</span>
                  </button>
                  <button
                    onClick={() => setActiveTab('quiz')}
                    className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 rounded-lg text-xs font-bold border border-slate-300 dark:border-slate-700 transition"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                    <span>Test Knowledge</span>
                  </button>
                </div>
              </div>

              {/* 3-Column Detailed Information Grid */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                
                {/* Column 1: Multimodal Sources Provenance */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider flex items-center space-x-1.5">
                      <Layers className="w-4 h-4 text-indigo-500" />
                      <span>Multimodal Provenance ({conceptDetails?.sources?.length || selectedConcept.sources?.length || 0})</span>
                    </h4>
                  </div>

                  <div className="space-y-2.5 max-h-80 overflow-y-auto pr-1">
                    {(conceptDetails?.sources || selectedConcept.sources || []).map((src, idx) => (
                      <div
                        key={src.id || idx}
                        className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/80 space-y-1.5 text-xs"
                      >
                        <div className="flex items-center justify-between">
                          <span className="inline-flex items-center space-x-1.5 font-bold">
                            {src.source_type === 'pdf' && (
                              <>
                                <BookOpen className="w-3.5 h-3.5 text-red-500" />
                                <span className="text-red-600 dark:text-red-400">Textbook (PDF)</span>
                              </>
                            )}
                            {src.source_type === 'presentation' && (
                              <>
                                <Presentation className="w-3.5 h-3.5 text-amber-500" />
                                <span className="text-amber-600 dark:text-amber-400">Lecture Slides</span>
                              </>
                            )}
                            {src.source_type === 'video' && (
                              <>
                                <Video className="w-3.5 h-3.5 text-purple-500" />
                                <span className="text-purple-600 dark:text-purple-400">Lecture Video</span>
                              </>
                            )}
                          </span>

                          <span className="text-3xs font-mono font-extrabold px-2 py-0.5 rounded-full bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300">
                            {src.source_type === 'pdf' && `Page ${src.page_number || 1}`}
                            {src.source_type === 'presentation' && `Slide ${src.slide_number || 1}`}
                            {src.source_type === 'video' && (src.timestamp_str || '00:00')}
                          </span>
                        </div>

                        {src.filename && (
                          <p className="text-3xs text-slate-400 truncate">
                            File: {src.filename}
                          </p>
                        )}

                        {src.excerpt && (
                          <p className="text-3xs text-slate-600 dark:text-slate-300 bg-white dark:bg-slate-900 p-2 rounded-lg border border-slate-100 dark:border-slate-800 italic leading-relaxed">
                            "{src.excerpt}"
                          </p>
                        )}
                      </div>
                    ))}

                    {(!conceptDetails?.sources || conceptDetails.sources.length === 0) && (
                      <p className="text-2xs text-slate-400 italic">No direct source units attached.</p>
                    )}
                  </div>
                </div>

                {/* Column 2: Prerequisite Concept Dependencies */}
                <div className="space-y-3">
                  <h4 className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider flex items-center space-x-1.5">
                    <ArrowRight className="w-4 h-4 text-emerald-500" />
                    <span>Prerequisites ({conceptDetails?.prerequisites?.length || selectedConcept.prerequisites?.length || 0})</span>
                  </h4>

                  <div className="space-y-2.5 max-h-80 overflow-y-auto pr-1">
                    {conceptDetails?.prerequisites && conceptDetails.prerequisites.length > 0 ? (
                      conceptDetails.prerequisites.map((p, idx) => (
                        <div 
                          key={p.concept_id || idx}
                          onClick={() => {
                            const matched = graphData?.nodes?.find(n => n.id === p.concept_id || n.name.toLowerCase() === p.name.toLowerCase());
                            if (matched) handleSelectConcept(matched);
                          }}
                          className="p-3 rounded-xl bg-emerald-50/50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800/80 space-y-1 text-xs cursor-pointer hover:border-emerald-500 transition"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-emerald-800 dark:text-emerald-300">
                              {p.name}
                            </span>
                            <span className="text-3xs text-emerald-600 dark:text-emerald-400 font-semibold">
                              Must learn first
                            </span>
                          </div>
                          <p className="text-3xs text-slate-600 dark:text-slate-400 leading-relaxed">
                            <span className="font-bold text-slate-500">Evidence:</span> {p.evidence}
                          </p>
                        </div>
                      ))
                    ) : (
                      <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-dashed border-slate-300 dark:border-slate-700 text-3xs text-slate-400 space-y-1">
                        <p className="font-semibold text-slate-500 dark:text-slate-400">Foundational Concept</p>
                        <p>No prior prerequisites required in this course sequence.</p>
                      </div>
                    )}

                    {/* Dependent concepts (Unlocks Next) */}
                    {conceptDetails?.dependents && conceptDetails.dependents.length > 0 && (
                      <div className="pt-2 border-t border-slate-200 dark:border-slate-800 space-y-1.5">
                        <p className="text-3xs font-extrabold uppercase text-slate-400">Enables & Unlocks Next:</p>
                        {conceptDetails.dependents.map((d, idx) => (
                          <div 
                            key={d.concept_id || idx}
                            onClick={() => {
                              const matched = graphData?.nodes?.find(n => n.id === d.concept_id || n.name.toLowerCase() === d.name.toLowerCase());
                              if (matched) handleSelectConcept(matched);
                            }}
                            className="p-2 bg-slate-50 dark:bg-slate-800/60 rounded-lg text-2xs font-semibold text-indigo-700 dark:text-indigo-300 flex items-center justify-between cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                          >
                            <span>{d.name}</span>
                            <ChevronRight className="w-3 h-3 text-slate-400" />
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* Column 3: Related Concepts & Semantic Links */}
                <div className="space-y-3">
                  <h4 className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider flex items-center space-x-1.5">
                    <Compass className="w-4 h-4 text-cyan-500" />
                    <span>Related Concepts ({conceptDetails?.related_concepts?.length || 0})</span>
                  </h4>

                  <div className="space-y-2.5 max-h-80 overflow-y-auto pr-1">
                    {conceptDetails?.related_concepts && conceptDetails.related_concepts.length > 0 ? (
                      conceptDetails.related_concepts.map((r, idx) => (
                        <div 
                          key={r.concept_id || idx}
                          onClick={() => {
                            const matched = graphData?.nodes?.find(n => n.id === r.concept_id || n.name.toLowerCase() === r.name.toLowerCase());
                            if (matched) handleSelectConcept(matched);
                          }}
                          className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700/80 space-y-1 text-xs cursor-pointer hover:border-cyan-500 transition"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-slate-800 dark:text-slate-200">
                              {r.name}
                            </span>
                            <span className="text-3xs font-extrabold uppercase px-2 py-0.5 rounded-full bg-cyan-100 dark:bg-cyan-950 text-cyan-700 dark:text-cyan-300 border border-cyan-300 dark:border-cyan-800">
                              {r.relationship_type}
                            </span>
                          </div>
                          <p className="text-3xs text-slate-500 dark:text-slate-400 leading-relaxed">
                            {r.evidence}
                          </p>
                        </div>
                      ))
                    ) : (
                      <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-dashed border-slate-300 dark:border-slate-700 text-3xs text-slate-400">
                        No additional semantic relationships identified.
                      </div>
                    )}
                  </div>
                </div>

              </div>

            </div>
          )}

        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL 1: TARGETED ASSESSMENT VERIFICATION MODAL */}
      {/* ========================================================================= */}
      {activeVerificationStep && (
        <div 
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              setActiveVerificationStep(null);
            }
          }}
          className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 md:p-6 bg-slate-950/80 backdrop-blur-sm animate-fade-in overflow-hidden"
        >
          <div className="academic-card w-full max-w-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl flex flex-col max-h-[90vh] sm:max-h-[85vh] overflow-hidden">
            
            {/* STICKY HEADER: Always visible at top */}
            <div className="flex-shrink-0 flex items-start justify-between p-4 sm:p-5 pb-3 border-b border-slate-100 dark:border-slate-800 bg-white/95 dark:bg-slate-900/95 backdrop-blur-xs">
              <div className="pr-3">
                <div className="flex items-center space-x-2">
                  <span className="px-2 py-0.5 rounded-full text-3xs font-extrabold bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                    Targeted Assessment Verification
                  </span>
                  <span className="text-3xs text-slate-500 font-semibold">Step #{activeVerificationStep.step_number}</span>
                </div>
                <h3 className="text-sm sm:text-base font-bold text-slate-900 dark:text-white mt-1">
                  {activeVerificationStep.concept_name}
                </h3>
                {activeVerificationStep.measurable_objective && (
                  <p className="text-3xs text-slate-500 dark:text-slate-400 mt-0.5 line-clamp-2">
                    Objective: {activeVerificationStep.measurable_objective}
                  </p>
                )}
              </div>
              <button
                onClick={() => setActiveVerificationStep(null)}
                className="p-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition flex-shrink-0 cursor-pointer shadow-2xs"
                title="Close modal (Esc)"
                aria-label="Close modal"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* SCROLLABLE BODY: Always reacts to mousewheel/touch scrolling */}
            <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-4 overscroll-contain">
              {activeVerificationStep.targeted_assessment ? (
                <>
                  <div className="p-3 bg-slate-50 dark:bg-slate-800/60 rounded-xl border border-slate-200 dark:border-slate-700/70">
                    <span className="text-3xs font-bold uppercase tracking-wider text-slate-400">Target Question:</span>
                    <p className="text-xs font-semibold text-slate-900 dark:text-slate-100 mt-1 leading-relaxed">
                      {activeVerificationStep.targeted_assessment.question}
                    </p>
                  </div>

                  {/* Options for MCQ */}
                  {activeVerificationStep.targeted_assessment.options && activeVerificationStep.targeted_assessment.options.length > 0 ? (
                    <div className="space-y-2">
                      <span className="text-3xs font-bold uppercase tracking-wider text-slate-400">Select Answer:</span>
                      {activeVerificationStep.targeted_assessment.options.map((opt, oIdx) => {
                        const optKey = typeof opt === 'string' ? opt : (opt.key || opt.text);
                        const optText = typeof opt === 'string' ? opt : (opt.text || opt.key);
                        const isSelected = verificationAnswer === (opt.key || optText);
                        return (
                          <button
                            key={oIdx}
                            onClick={() => setVerificationAnswer(opt.key || optText)}
                            className={`w-full text-left p-3 rounded-xl border text-xs font-medium transition flex items-start space-x-2.5 cursor-pointer ${
                              isSelected
                                ? 'bg-indigo-50 dark:bg-indigo-950/50 border-indigo-500 text-indigo-900 dark:text-indigo-200 ring-1 ring-indigo-500'
                                : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200 hover:border-slate-300 dark:hover:border-slate-600'
                            }`}
                          >
                            <span className="w-5 h-5 rounded-md bg-slate-100 dark:bg-slate-700 flex items-center justify-center text-3xs font-bold flex-shrink-0 mt-0.5">
                              {opt.key || String.fromCharCode(65 + oIdx)}
                            </span>
                            <span className="leading-relaxed">{optText}</span>
                          </button>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="space-y-1.5">
                      <label className="text-3xs font-bold uppercase tracking-wider text-slate-400">Your Grounded Explanation:</label>
                      <textarea
                        value={verificationAnswer}
                        onChange={(e) => setVerificationAnswer(e.target.value)}
                        rows={3}
                        placeholder="Explain the core principles in your own words based on the course materials..."
                        className="w-full text-xs p-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                      />
                    </div>
                  )}

                  {/* Verification Evaluation Result Feedback */}
                  {verificationResult && (
                    <div className={`p-3.5 rounded-xl border text-xs space-y-1.5 animate-fade-in ${
                      verificationResult.is_correct
                        ? 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-300 dark:border-emerald-800 text-emerald-900 dark:text-emerald-200'
                        : 'bg-rose-50 dark:bg-rose-950/40 border-rose-300 dark:border-rose-800 text-rose-900 dark:text-rose-200'
                    }`}>
                      <div className="flex items-center space-x-2 font-bold">
                        {verificationResult.is_correct ? (
                          <>
                            <CheckCheck className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                            <span>Verified! Concept Mastered</span>
                          </>
                        ) : (
                          <>
                            <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
                            <span>Needs Revision ({Math.round(verificationResult.score * 100)}% Score)</span>
                          </>
                        )}
                      </div>
                      <p className="text-3xs leading-relaxed">
                        {typeof verificationResult.feedback === 'string'
                          ? verificationResult.feedback
                          : (verificationResult.feedback?.msg || JSON.stringify(verificationResult.feedback || ''))}
                      </p>
                      {verificationResult.active_misconception && (
                        <div className="mt-1 p-2 rounded-lg bg-rose-100/60 dark:bg-rose-900/40 border border-rose-200 dark:border-rose-800 text-3xs">
                          <span className="font-bold">Identified Misconception: </span>
                          {typeof verificationResult.active_misconception === 'string'
                            ? verificationResult.active_misconception
                            : (verificationResult.active_misconception.misconception_title || 'Needs targeted review')}
                        </div>
                      )}
                    </div>
                  )}
                </>
              ) : (
                <div className="py-6 text-center text-xs text-slate-500">
                  No targeted question available for this concept.
                </div>
              )}
            </div>

            {/* STICKY FOOTER: Always pinned at bottom */}
            <div className="flex-shrink-0 p-3.5 sm:p-4 border-t border-slate-100 dark:border-slate-800 bg-slate-50/95 dark:bg-slate-900/95 backdrop-blur-xs flex items-center justify-between gap-2">
              <button
                onClick={() => setActiveVerificationStep(null)}
                className="inline-flex items-center space-x-1.5 px-3.5 py-2 text-xs font-semibold rounded-xl bg-slate-200/80 hover:bg-slate-300/80 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 transition cursor-pointer shadow-2xs"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Back to Learning Path</span>
              </button>

              <div className="flex items-center space-x-2">
                <button
                  disabled={verificationSubmitting || !verificationAnswer.trim()}
                  onClick={handleSubmitVerification}
                  className="px-4 py-2 text-xs font-bold rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white transition flex items-center space-x-1.5 disabled:opacity-50 cursor-pointer shadow-sm"
                >
                  {verificationSubmitting ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Evaluating...</span>
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>{verificationResult ? 'Retest Answer' : 'Submit & Verify'}</span>
                    </>
                  )}
                </button>
              </div>
            </div>

          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL 2: MULTIMODAL RESOURCE INSPECT / SOURCE LOCATION MODAL */}
      {/* ========================================================================= */}
      {selectedResourcePreview && (
        <div 
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              setSelectedResourcePreview(null);
            }
          }}
          className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 md:p-6 bg-slate-950/80 backdrop-blur-sm animate-fade-in overflow-hidden"
        >
          <div className="academic-card w-full max-w-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl flex flex-col max-h-[90vh] sm:max-h-[85vh] overflow-hidden">
            
            {/* Header */}
            <div className="flex-shrink-0 flex items-start justify-between p-4 sm:p-5 pb-3 border-b border-slate-100 dark:border-slate-800 bg-white/95 dark:bg-slate-900/95 backdrop-blur-xs">
              <div className="space-y-1 pr-3">
                <div className="flex items-center space-x-2">
                  {renderModalityBadge(selectedResourcePreview.resource_type)}
                  <span className="text-3xs font-bold text-slate-500">{selectedResourcePreview.filename}</span>
                </div>
                <h3 className="text-sm sm:text-base font-bold text-slate-900 dark:text-white">
                  {selectedResourcePreview.title}
                </h3>
              </div>
              <button
                onClick={() => setSelectedResourcePreview(null)}
                className="p-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition flex-shrink-0 cursor-pointer shadow-2xs"
                title="Close modal (Esc)"
                aria-label="Close modal"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Scrollable Body */}
            <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-3 overscroll-contain">
              {/* Exact Source Location Pill */}
              <div className="p-3 bg-slate-50 dark:bg-slate-800/60 rounded-xl border border-slate-200 dark:border-slate-700 text-xs space-y-1">
                <span className="text-3xs font-bold uppercase text-slate-400">Verified Location:</span>
                <p className="font-semibold text-slate-800 dark:text-slate-200">
                  {renderSourceLocationText(selectedResourcePreview)}
                </p>
                {selectedResourcePreview.provenance_ref && (
                  <p className="text-3xs text-slate-500">Provenance: {selectedResourcePreview.provenance_ref}</p>
                )}
              </div>

              {/* Content Excerpt */}
              <div className="space-y-1">
                <span className="text-3xs font-bold uppercase text-slate-400">Extracted Course Content:</span>
                <div className="p-3 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-xs text-slate-700 dark:text-slate-300 leading-relaxed max-h-48 overflow-y-auto font-mono text-3xs whitespace-pre-wrap">
                  {selectedResourcePreview.content_snippet}
                </div>
              </div>

              {/* Selection Rationale */}
              {selectedResourcePreview.selection_criteria && (
                <div className="p-2.5 rounded-lg bg-indigo-50/60 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800/80 text-3xs text-indigo-900 dark:text-indigo-200">
                  <span className="font-bold">Selection Rationale: </span>
                  {selectedResourcePreview.selection_criteria}
                </div>
              )}
            </div>

            {/* Sticky Footer */}
            <div className="flex-shrink-0 p-3.5 sm:p-4 border-t border-slate-100 dark:border-slate-800 bg-slate-50/95 dark:bg-slate-900/95 backdrop-blur-xs flex items-center justify-between gap-2">
              <button
                onClick={() => setSelectedResourcePreview(null)}
                className="inline-flex items-center space-x-1.5 px-3.5 py-2 text-xs font-semibold rounded-xl bg-slate-200/80 hover:bg-slate-300/80 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 transition cursor-pointer shadow-2xs"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Back to Learning Path</span>
              </button>
              <button
                onClick={() => {
                  setSelectedResourcePreview(null);
                  setActiveTab('explain');
                }}
                className="px-3.5 py-2 text-xs font-bold rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white transition flex items-center space-x-1.5 cursor-pointer shadow-sm"
              >
                <BookOpen className="w-3.5 h-3.5" />
                <span>Study with AI Tutor</span>
              </button>
            </div>

          </div>
        </div>
      )}

    </div>
  );
};

