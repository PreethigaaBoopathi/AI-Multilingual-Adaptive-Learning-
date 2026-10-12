import React, { useState, useEffect } from 'react';
import { 
  Sparkles, BookOpen, Lightbulb, GraduationCap, 
  Layers, CheckCircle, ShieldCheck, HelpCircle,
  Activity, Award, AlertTriangle, RefreshCw, ArrowRight,
  Check, X, Compass, ExternalLink, Play, CheckCircle2,
  ChevronRight, BarChart2, GitFork, Target
} from 'lucide-react';
import { textbookAPI } from '../../services/api';
import { useTextbook } from '../../context/TextbookContext';
import { SourceCitation } from '../../components/SourceCitation';
import { MermaidViewer } from '../../components/MermaidViewer';

const VISUAL_FORMATS = [
  { id: 'auto', label: 'Auto (Content-Driven)', icon: '✨' },
  { id: 'flowchart', label: 'Flowchart', icon: '🔀' },
  { id: 'concept_map', label: 'Concept Map', icon: '🕸️' },
  { id: 'block_diagram', label: 'Block Diagram', icon: '🧱' },
  { id: 'sequence', label: 'Sequence', icon: '🔄' },
  { id: 'comparison', label: 'Comparison', icon: '⚖️' },
  { id: 'timeline', label: 'Timeline', icon: '⏳' },
  { id: 'hierarchy', label: 'Hierarchy', icon: '🌳' },
  { id: 'cycle', label: 'Cycle', icon: '🔁' }
];

export const ExplainTab = () => {
  const { activeTextbook, activeChapter, activeSection, language, setActiveTab } = useTextbook();
  const [level, setLevel] = useState('auto'); // 'auto', 'beginner', 'intermediate', 'advanced'
  const [selectedFormat, setSelectedFormat] = useState('auto');
  const [topic, setTopic] = useState('');
  const [availableTopics, setAvailableTopics] = useState([]);
  const [explanationData, setExplanationData] = useState(null);
  const [loading, setLoading] = useState(false);

  // Interactive Practice State
  const [selectedOption, setSelectedOption] = useState('');
  const [submittingPractice, setSubmittingPractice] = useState(false);
  const [practiceResult, setPracticeResult] = useState(null);

  // Multi-Question Diagnostic State
  const [diagnosticOpen, setDiagnosticOpen] = useState(false);
  const [diagnosticData, setDiagnosticData] = useState(null);
  const [diagnosticLoading, setDiagnosticLoading] = useState(false);
  const [diagnosticIndex, setDiagnosticIndex] = useState(0);
  const [diagnosticAnswers, setDiagnosticAnswers] = useState({});
  const [diagnosticResult, setDiagnosticResult] = useState(null);

  // Extract dynamic topics for uploaded course material
  useEffect(() => {
    let isMounted = true;
    const extractTopics = async () => {
      if (!activeTextbook) {
        if (isMounted) {
          setAvailableTopics([]);
          setTopic('');
        }
        return;
      }
      const topicSet = new Set();

      if (activeTextbook.chapters && Array.isArray(activeTextbook.chapters)) {
        activeTextbook.chapters.forEach(ch => {
          if (ch.title) topicSet.add(ch.title.trim());
          if (ch.sections && Array.isArray(ch.sections)) {
            ch.sections.forEach(sec => {
              if (sec.title) topicSet.add(sec.title.trim());
            });
          }
        });
      }

      try {
        const graph = await textbookAPI.getConceptGraph(activeTextbook.id);
        if (graph?.nodes && Array.isArray(graph.nodes)) {
          graph.nodes.forEach(node => {
            if (node.name) topicSet.add(node.name.trim());
            if (node.topic) topicSet.add(node.topic.trim());
          });
        }
      } catch (e) {}

      if (topicSet.size === 0 && activeTextbook.title) {
        topicSet.add(activeTextbook.title.trim());
      }

      const list = Array.from(topicSet).filter(Boolean);
      if (isMounted) {
        setAvailableTopics(list);
        if (activeSection?.title) {
          setTopic(activeSection.title);
        } else if (activeChapter?.title) {
          setTopic(activeChapter.title);
        } else if (list.length > 0 && !topic) {
          setTopic(list[0]);
        }
      }
    };

    extractTopics();
    return () => { isMounted = false; };
  }, [activeTextbook]);

  // Sync default topic with active chapter/section
  useEffect(() => {
    if (activeSection?.title) {
      setTopic(activeSection.title);
    } else if (activeChapter?.title) {
      setTopic(activeChapter.title);
    }
  }, [activeChapter, activeSection]);

  // Load Adaptive Explanation Pipeline (Innovation 6)
  const loadExplanation = async (reqLevel = level, reqFormat = selectedFormat) => {
    if (!activeTextbook || !topic) return;
    try {
      setLoading(true);
      setPracticeResult(null);
      setSelectedOption('');

      const data = await textbookAPI.getAdaptiveExplanation(
        activeTextbook.id,
        topic,
        reqLevel,
        reqFormat,
        'demo_user',
        language
      );
      setExplanationData(data);
    } catch (err) {
      console.error('Adaptive explanation fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (topic && activeTextbook) {
      loadExplanation(level, selectedFormat);
    }
  }, [topic, level, selectedFormat, language, activeTextbook]);

  // Level Switcher Handler
  const handleLevelChange = (newLevel) => {
    setLevel(newLevel);
  };

  // Practice Question Submission Handler
  const handleSubmitPractice = async () => {
    if (!selectedOption || !explanationData?.practice_question) return;
    try {
      setSubmittingPractice(true);
      const q = explanationData.practice_question;
      const res = await textbookAPI.submitAdaptivePractice(
        activeTextbook.id,
        explanationData.concept,
        q.id || 'q_practice_01',
        q.question_type || 'mcq',
        selectedOption,
        explanationData.level,
        'demo_user',
        language
      );
      setPracticeResult(res);
    } catch (err) {
      console.error('Error submitting practice:', err);
    } finally {
      setSubmittingPractice(false);
    }
  };

  // Multi-Question Diagnostic Modal Trigger
  const handleOpenDiagnostic = async () => {
    if (!activeTextbook || !topic) return;
    try {
      setDiagnosticOpen(true);
      setDiagnosticLoading(true);
      setDiagnosticResult(null);
      setDiagnosticIndex(0);
      setDiagnosticAnswers({});
      const res = await textbookAPI.getDiagnosticQuestion(activeTextbook.id, topic, 'demo_user', language);
      setDiagnosticData(res);
    } catch (err) {
      console.error('Error loading diagnostic assessment:', err);
    } finally {
      setDiagnosticLoading(false);
    }
  };

  // Select Option for Current Diagnostic Question
  const handleSelectDiagnosticOption = (key) => {
    if (diagnosticResult) return;
    setDiagnosticAnswers(prev => ({
      ...prev,
      [diagnosticIndex]: key
    }));
  };

  // Text / Open-ended Answer for Current Diagnostic Question
  const handleTextDiagnosticChange = (text) => {
    if (diagnosticResult) return;
    setDiagnosticAnswers(prev => ({
      ...prev,
      [diagnosticIndex]: text
    }));
  };

  const handleNextDiagnosticQuestion = () => {
    const questions = diagnosticData?.questions || [];
    if (diagnosticIndex < questions.length - 1) {
      setDiagnosticIndex(prev => prev + 1);
    }
  };

  const handlePrevDiagnosticQuestion = () => {
    if (diagnosticIndex > 0) {
      setDiagnosticIndex(prev => prev - 1);
    }
  };

  // Submit Multi-Question Diagnostic Session
  const handleSubmitDiagnostic = async () => {
    const questions = diagnosticData?.questions || [];
    if (questions.length === 0) return;
    try {
      setDiagnosticLoading(true);
      const answersPayload = questions.map((q, idx) => ({
        question_id: q.id || `diag_${idx}`,
        question_type: q.question_type || 'mcq',
        student_answer: diagnosticAnswers[idx] || '',
        concept_name: q.concept_name || diagnosticData.concept,
        topic: q.topic || diagnosticData.concept,
        is_prerequisite: !!q.is_prerequisite,
        prerequisite_concept: q.prerequisite_concept || null,
        diagnostic_aspect: q.diagnostic_aspect || null,
        correct_key: q.correct_key,
        expected_answer: q.expected_answer,
        options: q.options || [],
        difficulty: q.difficulty || 'medium'
      }));

      const res = await textbookAPI.submitDiagnosticSession(
        activeTextbook.id,
        diagnosticData.concept,
        answersPayload,
        'demo_user',
        language
      );
      setDiagnosticResult(res);
    } catch (err) {
      console.error('Error submitting diagnostic assessment:', err);
    } finally {
      setDiagnosticLoading(false);
    }
  };

  const currentActiveLevel = explanationData?.level || (level === 'auto' ? 'beginner' : level);

  const getFormatLabel = (fmt) => {
    if (language !== 'ta') return fmt.label;
    const taMap = {
      'Auto (Content-Driven)': 'தானியங்கி (Auto)',
      'Flowchart': 'பாய்ச்சல் வரைபடம்',
      'Concept Map': 'கருத்து வரைபடம்',
      'Block Diagram': 'தொகுதி வரைபடம்',
      'Sequence': 'வரிசைமுறை',
      'Comparison': 'ஒப்பீடு',
      'Timeline': 'காலவரிசை',
      'Hierarchy': 'படிநிலை',
      'Cycle': 'சுழற்சி வரைபடம்'
    };
    return taMap[fmt.label] || fmt.label;
  };

  return (
    <div className="space-y-6 text-slate-900 dark:text-slate-100">
      
      {/* Header & Concept selector */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-xl font-bold text-slate-900 dark:text-white">
              {language === 'ta' ? 'தகவமைக்கும் விளக்கம் & காட்சி கற்றல்' : 'Adaptive Explanation & Visual Learning'}
            </h2>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            {language === 'ta'
              ? 'கடினத்தன்மை, காட்சி வடிவமைப்பு மற்றும் பயிற்சிகள் உங்கள் தேர்ச்சி நிலைக்கு ஏற்ப தானாகவே மாறுகின்றன.'
              : 'Difficulty, visual representation format, and practice drills dynamically adapt to your demonstrated mastery and topic structure.'}
          </p>
        </div>

        {/* Quick Topic Switcher dropdown */}
        <div className="flex items-center space-x-2 flex-shrink-0">
          <span className="text-xs font-medium text-slate-600 dark:text-slate-400">
            {language === 'ta' ? 'தலைப்பு:' : 'Topic:'}
          </span>
          <select
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            className="text-xs bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg px-2.5 py-1.5 font-medium text-slate-800 dark:text-slate-200 shadow-2xs focus:ring-1 focus:ring-indigo-500 focus:outline-none max-w-xs truncate"
          >
            {availableTopics.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Adaptive Mastery Status Banner */}
      {explanationData && (
        <div className="p-4 rounded-xl bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white border border-indigo-500/30 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <Activity className="w-4 h-4 text-emerald-400" />
              <span className="text-xs font-semibold uppercase tracking-wider text-indigo-300">
                {language === 'ta' ? 'மாணவர் கற்றல் திறன் சுயவிவரம்' : 'Demonstrated Student Mastery Profile'}
              </span>
              <span className={`text-3xs font-bold px-2 py-0.5 rounded-full uppercase ${
                explanationData.mastery_status === 'Mastered' 
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                  : explanationData.mastery_status === 'Developing'
                    ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                    : explanationData.mastery_status === 'Unassessed'
                      ? 'bg-slate-500/20 text-slate-300 border border-slate-500/40'
                      : 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
              }`}>
                {language === 'ta' 
                  ? (explanationData.mastery_status === 'Mastered' ? 'முழு தேர்ச்சி' : explanationData.mastery_status === 'Developing' ? 'வளரும் நிலை' : explanationData.mastery_status === 'Unassessed' ? 'மதிப்பிடப்படவில்லை' : 'மீள் பயிற்சி தேவை')
                  : explanationData.mastery_status}
              </span>
            </div>
            
            <p className="text-xs text-slate-300">
              {language === 'ta' ? 'கருத்து: ' : 'Concept: '}<strong className="text-white">{explanationData.concept}</strong> • {language === 'ta' ? 'அடுக்கு: ' : 'Level: '}<strong className="text-indigo-200 capitalize">
                {language === 'ta' ? (explanationData.level === 'beginner' ? 'அடிப்படை' : explanationData.level === 'intermediate' ? 'இடைநிலை' : 'மேம்பட்ட நிலை') : explanationData.level}
              </strong>
              {explanationData.mastery_score !== null && (
                <span> • {language === 'ta' ? 'துல்லியம்: ' : 'Accuracy: '}<strong className="text-emerald-300">{explanationData.mastery_score}%</strong> ({explanationData.observed_attempts_count} {language === 'ta' ? 'முயற்சிகள்' : 'attempts'})</span>
              )}
              <span className="text-slate-400 ml-1">
                [{language === 'ta' ? 'முறை: ' : 'Determination: '}{explanationData.level_determination_method.replace(/_/g, ' ')}]
              </span>
            </p>

            {/* Misconception Notice */}
            {explanationData.active_misconception && (
              <div className="mt-2 flex items-center space-x-2 text-rose-300 bg-rose-950/60 px-2.5 py-1 rounded border border-rose-800 text-2xs">
                <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 text-rose-400" />
                <span>
                  {language === 'ta' ? 'கண்டறியப்பட்ட தவறான புரிதல்: ' : 'Active Misconception: '}
                  <strong>{explanationData.active_misconception.misconception_title || explanationData.active_misconception.hypothesis_text}</strong>
                  {language === 'ta' ? ' (அடிப்படை நிலை விளக்கம் பொருந்துகிறது)' : ' (Beginner Foundational Explanation Applied)'}
                </span>
              </div>
            )}
          </div>

          {/* Diagnostic Check button if unassessed or want calibration */}
          <button
            onClick={handleOpenDiagnostic}
            className="flex-shrink-0 flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-sm transition"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>{language === 'ta' ? 'அறிவுத்திறன் மதிப்பீடு (3–5 வினாக்கள்)' : 'Diagnostic Assessment (3–5 Questions)'}</span>
          </button>
        </div>
      )}

      {/* 3 Selectable Adaptive Level Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        
        {/* Beginner Card */}
        <div
          onClick={() => handleLevelChange('beginner')}
          className={`cursor-pointer rounded-xl p-4 border transition-all select-none relative ${
            currentActiveLevel === 'beginner'
              ? 'bg-emerald-50/70 dark:bg-emerald-950/40 border-emerald-500 dark:border-emerald-500 ring-2 ring-emerald-500/20 shadow-sm'
              : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 hover:bg-slate-50/50 dark:hover:bg-slate-800/50'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center space-x-2">
              <span className="text-base">🟢</span>
              <h3 className="font-bold text-sm text-slate-900 dark:text-white">
                {language === 'ta' ? 'அடிப்படை (Beginner)' : 'Beginner'}
              </h3>
            </div>
            {currentActiveLevel === 'beginner' && (
              <span className="text-3xs uppercase font-extrabold px-1.5 py-0.5 rounded bg-emerald-600 text-white">
                {language === 'ta' ? 'செயலில் உள்ள நிலை' : 'Active Tier'}
              </span>
            )}
          </div>
          <p className="text-xs text-slate-600 dark:text-slate-400 font-medium">
            {language === 'ta' 
              ? '"எளிமையான மொழி, அன்றாட உள்ளுணர்வு ஒப்புமைகள், எளிய பயிற்சி வினாக்கள்"'
              : '"Simple language, everyday intuitive analogies, zero confusing jargon & easy practice"'}
          </p>
          <div className="mt-3 flex flex-wrap gap-1">
            <span className="text-3xs bg-white dark:bg-slate-800 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/60 px-1.5 py-0.5 rounded">
              {language === 'ta' ? 'அன்றாட ஒப்புமைகள்' : 'Everyday Analogies'}
            </span>
            <span className="text-3xs bg-white dark:bg-slate-800 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/60 px-1.5 py-0.5 rounded">
              {language === 'ta' ? 'அடிப்படை படிகள்' : 'Foundational Steps'}
            </span>
          </div>
        </div>

        {/* Intermediate Card */}
        <div
          onClick={() => handleLevelChange('intermediate')}
          className={`cursor-pointer rounded-xl p-4 border transition-all select-none relative ${
            currentActiveLevel === 'intermediate'
              ? 'bg-amber-50/70 dark:bg-amber-950/40 border-amber-500 dark:border-amber-500 ring-2 ring-amber-500/20 shadow-sm'
              : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 hover:bg-slate-50/50 dark:hover:bg-slate-800/50'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center space-x-2">
              <span className="text-base">🟡</span>
              <h3 className="font-bold text-sm text-slate-900 dark:text-white">
                {language === 'ta' ? 'இடைநிலை (Intermediate)' : 'Intermediate'}
              </h3>
            </div>
            {currentActiveLevel === 'intermediate' && (
              <span className="text-3xs uppercase font-extrabold px-1.5 py-0.5 rounded bg-amber-600 text-white">
                {language === 'ta' ? 'செயலில் உள்ள நிலை' : 'Active Tier'}
              </span>
            )}
          </div>
          <p className="text-xs text-slate-600 dark:text-slate-400 font-medium">
            {language === 'ta'
              ? '"தொழில்நுட்ப கலைச்சொற்கள், நேரடி செய்முறை பயன்பாடுகள் & கருத்துத் தொடர்புகள்"'
              : '"Standard technical terminology, worked application examples & concept relationships"'}
          </p>
          <div className="mt-3 flex flex-wrap gap-1">
            <span className="text-3xs bg-white dark:bg-slate-800 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800/60 px-1.5 py-0.5 rounded">
              {language === 'ta' ? 'கலைச்சொற்கள்' : 'Technical Terms'}
            </span>
            <span className="text-3xs bg-white dark:bg-slate-800 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800/60 px-1.5 py-0.5 rounded">
              {language === 'ta' ? 'செய்முறை பயன்பாடுகள்' : 'Worked Applications'}
            </span>
          </div>
        </div>

        {/* Advanced Card */}
        <div
          onClick={() => handleLevelChange('advanced')}
          className={`cursor-pointer rounded-xl p-4 border transition-all select-none relative ${
            currentActiveLevel === 'advanced'
              ? 'bg-rose-50/70 dark:bg-rose-950/40 border-rose-500 dark:border-rose-500 ring-2 ring-rose-500/20 shadow-sm'
              : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 hover:bg-slate-50/50 dark:hover:bg-slate-800/50'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center space-x-2">
              <span className="text-base">🔴</span>
              <h3 className="font-bold text-sm text-slate-900 dark:text-white">
                {language === 'ta' ? 'மேம்பட்ட நிலை (Advanced)' : 'Advanced'}
              </h3>
            </div>
            {currentActiveLevel === 'advanced' && (
              <span className="text-3xs uppercase font-extrabold px-1.5 py-0.5 rounded bg-rose-600 text-white">
                {language === 'ta' ? 'செயலில் உள்ள நிலை' : 'Active Tier'}
              </span>
            )}
          </div>
          <p className="text-xs text-slate-600 dark:text-slate-400 font-medium">
            {language === 'ta'
              ? '"முறையான வரையறைகள், கோட்பாட்டு மாறிலிகள் மற்றும் எல்லை நிலை சான்றுகள்"'
              : '"Rigorous formal definitions, theoretical invariants, trade-offs & edge-case proofs"'}
          </p>
          <div className="mt-3 flex flex-wrap gap-1">
            <span className="text-3xs bg-white dark:bg-slate-800 text-rose-800 dark:text-rose-300 border border-rose-200 dark:border-rose-800/60 px-1.5 py-0.5 rounded">
              {language === 'ta' ? 'கோட்பாட்டு மாறிலிகள்' : 'Formal Invariants'}
            </span>
            <span className="text-3xs bg-white dark:bg-slate-800 text-rose-800 dark:text-rose-300 border border-rose-200 dark:border-rose-800/60 px-1.5 py-0.5 rounded">
              {language === 'ta' ? 'பிரிப்பு சான்றுகள்' : 'Decomposition Proofs'}
            </span>
          </div>
        </div>

      </div>

      {/* Visual Representation Format Selector Bar */}
      <div className="flex flex-wrap items-center gap-1.5 p-2 bg-slate-100 dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700">
        <span className="text-xs font-semibold text-slate-600 dark:text-slate-400 px-2 flex items-center space-x-1">
          <GitFork className="w-3.5 h-3.5" />
          <span>{language === 'ta' ? 'காட்சி விளக்கம்:' : 'Visual Representation:'}</span>
        </span>
        {VISUAL_FORMATS.map((fmt) => {
          const isCurrentActive = selectedFormat === fmt.id || (selectedFormat === 'auto' && explanationData?.visual_format === fmt.id);
          return (
            <button
              key={fmt.id}
              onClick={() => setSelectedFormat(fmt.id)}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition flex items-center space-x-1 ${
                isCurrentActive
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-700'
              }`}
            >
              <span>{fmt.icon}</span>
              <span>{getFormatLabel(fmt)}</span>
            </button>
          );
        })}
      </div>

      {/* Loading State */}
      {loading ? (
        <div className="py-16 text-center space-y-3">
          <div className="w-10 h-10 border-3 border-indigo-600 dark:border-indigo-400 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-sm font-medium text-slate-600 dark:text-slate-400">
            {language === 'ta'
              ? `"${topic}" பற்றிய ${currentActiveLevel === 'beginner' ? 'அடிப்படை' : currentActiveLevel === 'intermediate' ? 'இடைநிலை' : 'மேம்பட்ட'} நிலை விளக்கமும் காட்சி மாதிரியும் உருவாக்கப்படுகிறது...`
              : `Synthesizing ${currentActiveLevel}-tier grounded explanation and dynamic visual for "${topic}"...`}
          </p>
        </div>
      ) : explanationData ? (
        <div className="space-y-6 animate-fade-in">
          
          {/* Insufficient Evidence Limitation Warning Banner */}
          {!explanationData.is_sufficient_evidence && explanationData.limitation_note && (
            <div className="p-4 bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-800 rounded-xl flex items-start space-x-3 text-amber-800 dark:text-amber-300 text-xs">
              <AlertTriangle className="w-5 h-5 flex-shrink-0 text-amber-600 dark:text-amber-400 mt-0.5" />
              <div>
                <p className="font-bold mb-1">Source Grounding Limitation</p>
                <p className="leading-relaxed">{explanationData.limitation_note}</p>
              </div>
            </div>
          )}

          {/* Dynamic Visual Representation Area (Innovation 5 Integration) */}
          {explanationData.visual_representation?.mermaid_code && (
            <div>
              <div className="flex items-center justify-between mb-1 px-1">
                <span className="text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center space-x-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-indigo-500" />
                  <span>{language === 'ta' ? `காட்சி விளக்கம் (${explanationData.visual_format.replace(/_/g, ' ')})` : `Structure-Driven Visual Explanation (${explanationData.visual_format.replace(/_/g, ' ')})`}</span>
                </span>
                <span className="text-3xs text-slate-500 dark:text-slate-400">
                  {language === 'ta' ? 'உள்ளடக்க அமைப்பு மற்றும் நிலைக்கு ஏற்ப வடிவமைக்கப்பட்டது' : 'Format determined by content structure & difficulty'}
                </span>
              </div>
              <MermaidViewer
                chart={explanationData.visual_representation.mermaid_code}
                title={`${explanationData.concept} (${explanationData.visual_format.replace(/_/g, ' ')})`}
                sourceReference={explanationData.source_reference}
              />
            </div>
          )}

          {/* Main Explanation Body Card */}
          <div className="academic-card p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
              <div className="flex items-center space-x-2">
                <BookOpen className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
                <h4 className="font-bold text-slate-900 dark:text-white text-sm">
                  {language === 'ta' 
                    ? `${explanationData.concept} பற்றிய ${currentActiveLevel === 'beginner' ? 'அடிப்படை' : currentActiveLevel === 'intermediate' ? 'இடைநிலை' : 'மேம்பட்ட'} விளக்கம்`
                    : `${currentActiveLevel.toUpperCase()} Grounded Explanation: ${explanationData.concept}`}
                </h4>
              </div>
              <div className="flex items-center space-x-1.5 text-3xs font-semibold bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 px-2 py-1 rounded-full border border-emerald-200 dark:border-emerald-800">
                <ShieldCheck className="w-3 h-3" />
                <span>{language === 'ta' ? 'பாடப்பகுதி சான்றுகளுடன் கூடியது' : 'Grounded in Course Material'}</span>
              </div>
            </div>

            <div className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed whitespace-pre-line space-y-2 font-normal">
              {explanationData.explanation}
            </div>

            {/* Formal Notes & Limitations (for Advanced Level) */}
            {explanationData.formal_notes_or_limitations && (
              <div className="mt-4 p-3.5 bg-rose-50/60 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900/40 rounded-lg text-xs text-rose-900 dark:text-rose-200">
                <strong className="block mb-1 text-rose-700 dark:text-rose-400">
                  {language === 'ta' ? 'கோட்பாட்டு வரம்புகள் & எல்லை நிபந்தனைகள்:' : 'Theoretical Invariants & Edge Constraints:'}
                </strong>
                {explanationData.formal_notes_or_limitations}
              </div>
            )}
          </div>

          {/* Analogy & Example Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            
            {/* Intuitive Analogy */}
            {explanationData.analogy && (
              <div className="academic-card p-5 bg-gradient-to-br from-amber-50/50 to-orange-50/30 dark:from-amber-950/20 dark:to-orange-950/10 border border-amber-200 dark:border-amber-900/50 rounded-xl">
                <div className="flex items-center space-x-2 text-amber-800 dark:text-amber-300 font-bold text-xs uppercase tracking-wider mb-2">
                  <Lightbulb className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                  <span>{language === 'ta' ? 'உள்ளுணர்வு ஒப்புமை (Intuitive Analogy)' : 'Intuitive Analogy'}</span>
                </div>
                <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed font-medium">
                  {explanationData.analogy}
                </p>
              </div>
            )}

            {/* Concrete Worked Example */}
            <div className={`academic-card p-5 bg-slate-50 dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 rounded-xl ${!explanationData.analogy ? 'md:col-span-2' : ''}`}>
              <div className="flex items-center space-x-2 text-indigo-700 dark:text-indigo-400 font-bold text-xs uppercase tracking-wider mb-2">
                <Layers className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
                <span>{language === 'ta' ? 'எடுத்துக்காட்டு & நடைமுறை பயன்பாடு (Worked Example)' : 'Worked Example & Application'}</span>
              </div>
              <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed font-mono whitespace-pre-line bg-white dark:bg-slate-950 p-3 rounded border border-slate-200 dark:border-slate-800">
                {explanationData.example}
              </p>
            </div>

          </div>

          {/* Key Terminology Breakdown Table */}
          {explanationData.key_terms && explanationData.key_terms.length > 0 && (
            <div className="academic-card p-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl">
              <h4 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider mb-3 flex items-center space-x-1.5">
                <GraduationCap className="w-4 h-4 text-slate-700 dark:text-slate-300" />
                <span>{language === 'ta' ? 'தொழில்நுட்ப கலைச்சொற்கள் விளக்கம்' : 'Technical Terminology Breakdown'}</span>
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                {explanationData.key_terms.map((kt, i) => (
                  <div key={i} className="p-3 bg-slate-50 dark:bg-slate-800/70 rounded-lg border border-slate-200 dark:border-slate-700">
                    <p className="font-bold text-xs text-slate-900 dark:text-white mb-1">{kt.term}</p>
                    <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">{kt.meaning}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Level-Appropriate Practice Activity Card */}
          {explanationData.practice_question && (
            <div className="academic-card p-6 bg-gradient-to-br from-indigo-50/60 to-purple-50/40 dark:from-indigo-950/30 dark:to-purple-950/20 border border-indigo-200 dark:border-indigo-900/60 rounded-xl space-y-4">
              <div className="flex items-center justify-between border-b border-indigo-100 dark:border-indigo-900/50 pb-3">
                <div className="flex items-center space-x-2">
                  <Target className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
                  <h4 className="font-bold text-sm text-slate-900 dark:text-white">
                    {language === 'ta'
                      ? `அறிவுத் திறன் மதிப்பீடு (${explanationData.practice_question.difficulty === 'easy' ? 'எளிதான' : explanationData.practice_question.difficulty === 'medium' ? 'நடுத்தர' : 'கடின'} அடுக்கு)`
                      : `Adaptive Knowledge Check (${explanationData.practice_question.difficulty?.toUpperCase()} Tier)`}
                  </h4>
                </div>
                <span className="text-3xs font-semibold bg-indigo-100 dark:bg-indigo-900/60 text-indigo-800 dark:text-indigo-300 px-2 py-0.5 rounded">
                  {language === 'ta' ? `${currentActiveLevel === 'beginner' ? 'ஆரம்ப நிலை' : currentActiveLevel === 'intermediate' ? 'இடைநிலை' : 'மேம்பட்ட நிலை'}க்கு ஏற்றது` : `Calibrated for ${currentActiveLevel}`}
                </span>
              </div>

              <p className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                {explanationData.practice_question.question}
              </p>

              {/* Options */}
              <div className="space-y-2">
                {explanationData.practice_question.options?.map((opt) => (
                  <label
                    key={opt.key}
                    onClick={() => !practiceResult && setSelectedOption(opt.key)}
                    className={`flex items-start space-x-3 p-3 rounded-lg border text-xs cursor-pointer transition select-none ${
                      selectedOption === opt.key
                        ? 'bg-indigo-600 text-white border-indigo-600 shadow-xs'
                        : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800/60'
                    }`}
                  >
                    <span className={`w-5 h-5 rounded-full flex items-center justify-center font-bold text-3xs flex-shrink-0 ${
                      selectedOption === opt.key ? 'bg-white text-indigo-700' : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400'
                    }`}>
                      {opt.key}
                    </span>
                    <span className="leading-relaxed">{opt.text}</span>
                  </label>
                ))}
              </div>

              {/* Submit / Evaluate Button */}
              {!practiceResult ? (
                <div className="flex justify-end pt-2">
                  <button
                    onClick={handleSubmitPractice}
                    disabled={!selectedOption || submittingPractice}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-lg text-xs font-semibold shadow-sm transition flex items-center space-x-1.5"
                  >
                    {submittingPractice ? (
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Check className="w-3.5 h-3.5" />
                    )}
                    <span>{language === 'ta' ? 'விடையைச் சமர்ப்பித்து சரிபார்க்கவும்' : 'Submit & Evaluate Answer'}</span>
                  </button>
                </div>
              ) : (
                <div className={`p-4 rounded-xl border text-xs space-y-2.5 animate-fade-in ${
                  practiceResult.is_correct
                    ? 'bg-emerald-50/80 dark:bg-emerald-950/40 border-emerald-300 dark:border-emerald-800 text-emerald-900 dark:text-emerald-200'
                    : 'bg-rose-50/80 dark:bg-rose-950/40 border-rose-300 dark:border-rose-800 text-rose-900 dark:text-rose-200'
                }`}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2 font-bold">
                      {practiceResult.is_correct ? <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" /> : <AlertTriangle className="w-4 h-4 text-rose-600 dark:text-rose-400" />}
                      <span>{practiceResult.feedback}</span>
                    </div>
                    <span className="font-bold text-2xs px-2 py-0.5 rounded bg-white/60 dark:bg-black/40">
                      {language === 'ta' ? 'மதிப்பெண்: ' : 'Score: '}{practiceResult.score * 100}%
                    </span>
                  </div>

                  <p className="leading-relaxed">{practiceResult.explanation}</p>
                  
                  {practiceResult.adaptation_summary && (
                    <div className="p-2.5 bg-white/70 dark:bg-slate-900/70 rounded-lg border border-current/20 font-medium">
                      <strong className="block text-2xs mb-0.5 uppercase tracking-wider">
                        {language === 'ta' ? 'தகவமைப்பு பரிந்துரை:' : 'Adaptive Recommendation:'}
                      </strong>
                      {practiceResult.adaptation_summary}
                    </div>
                  )}

                  {/* Level up / switch action button */}
                  {practiceResult.next_recommended_level !== currentActiveLevel && (
                    <div className="flex justify-end pt-1">
                      <button
                        onClick={() => handleLevelChange(practiceResult.next_recommended_level)}
                        className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold shadow-sm transition flex items-center space-x-1"
                      >
                        <span>
                          {language === 'ta'
                            ? `${practiceResult.next_recommended_level === 'beginner' ? 'அடிப்படை' : practiceResult.next_recommended_level === 'intermediate' ? 'இடைநிலை' : 'மேம்பட்ட'} விளக்கத்திற்கு மாறவும்`
                            : `Switch to ${practiceResult.next_recommended_level.toUpperCase()} Explanation`}
                        </span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Grounded Source Reference Citation */}
          <SourceCitation reference={explanationData.source_reference} citations={explanationData.citations} />
        </div>
      ) : null}

      {/* Multi-Question Adaptive Diagnostic Modal (3-5 Questions) */}
      {diagnosticOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-xl w-full p-6 space-y-4 shadow-xl animate-fade-in max-h-[90vh] overflow-y-auto">
            
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
              <div className="flex items-center space-x-2">
                <Sparkles className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
                <div>
                  <h3 className="font-bold text-base text-slate-900 dark:text-white">
                    {language === 'ta' ? 'தகவமைக்கும் அறிவுத்திறன் மதிப்பீடு' : 'Adaptive Diagnostic Assessment'}
                  </h3>
                  <p className="text-2xs text-slate-500 dark:text-slate-400">
                    {language === 'ta' ? 'தலைப்பு: ' : 'Topic: '}<strong className="text-slate-800 dark:text-slate-200">{topic}</strong>
                  </p>
                </div>
              </div>
              <button
                onClick={() => setDiagnosticOpen(false)}
                className="p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-lg"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {diagnosticLoading ? (
              <div className="py-12 text-center space-y-3">
                <RefreshCw className="w-7 h-7 animate-spin mx-auto text-indigo-600" />
                <p className="text-xs font-medium text-slate-600 dark:text-slate-300">
                  {language === 'ta' 
                    ? (diagnosticResult ? "விடைகள் மதிப்பாய்வு செய்யப்பட்டு தேர்ச்சி அடுக்கு அளவிடப்படுகிறது..." : "பாடப்பொருளிலிருந்து சான்றுகளுடன் கூடிய மதிப்பீட்டு வினாக்கள் உருவாக்கப்படுகின்றன...")
                    : (diagnosticResult ? "Evaluating answers & calibrating mastery profile..." : "Generating evidence-grounded diagnostic questions from course materials...")}
                </p>
              </div>
            ) : !diagnosticData?.is_sufficient_evidence ? (
              <div className="p-4 bg-amber-50 dark:bg-amber-950/40 rounded-xl border border-amber-300 dark:border-amber-800 text-xs text-amber-900 dark:text-amber-200 space-y-3">
                <div className="flex items-start space-x-2">
                  <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <strong className="font-semibold block mb-1">
                      {language === 'ta' ? 'போதுமான பாடச்சான்றுகள் இல்லை:' : 'Insufficient Source Material:'}
                    </strong>
                    <p>{diagnosticData?.limitation_note || "The uploaded course materials do not contain sufficient evidence for this topic. Diagnostic questions cannot be generated reliably without course materials."}</p>
                  </div>
                </div>
                <div className="pt-2 border-t border-amber-200 dark:border-amber-800/80">
                  <span className="block font-semibold mb-1.5 text-2xs uppercase tracking-wider">
                    {language === 'ta' ? 'விரும்பிய நிலையை கைமுறையாகத் தேர்ந்தெடுக்கவும்:' : 'Please select your preferred level manually:'}
                  </span>
                  <div className="flex items-center space-x-2">
                    {['beginner', 'intermediate', 'advanced'].map((lvl) => (
                      <button
                        key={lvl}
                        onClick={() => {
                          handleLevelChange(lvl);
                          setDiagnosticOpen(false);
                        }}
                        className="px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-semibold capitalize"
                      >
                        {language === 'ta' ? (lvl === 'beginner' ? 'அடிப்படை' : lvl === 'intermediate' ? 'இடைநிலை' : 'மேம்பட்ட நிலை') : lvl}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            ) : diagnosticResult ? (
              /* Diagnostic Completion Summary Screen */
              <div className="space-y-4 animate-fade-in text-xs">
                
                {/* Result Header Card */}
                <div className="p-4 rounded-xl bg-gradient-to-br from-indigo-900 to-slate-900 text-white border border-indigo-700/50 space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <Award className="w-5 h-5 text-emerald-400" />
                      <span className="font-bold text-sm">
                        {language === 'ta' ? 'அறிவுத்திறன் மதிப்பீடு நிறைவடைந்தது' : 'Diagnostic Assessment Completed'}
                      </span>
                    </div>
                    <span className="font-bold text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                      {language === 'ta' ? 'மதிப்பெண்: ' : 'Score: '}{diagnosticResult.score_percentage}% ({diagnosticResult.correct_count}/{diagnosticResult.total_questions})
                    </span>
                  </div>

                  <div className="flex items-center space-x-2 pt-1">
                    <span className="text-2xs text-slate-300">
                      {language === 'ta' ? 'அளவிடப்பட்ட விளக்க அடுக்கு: ' : 'Calibrated Explanation Level: '}
                    </span>
                    <span className={`text-2xs font-bold px-2.5 py-0.5 rounded uppercase ${
                      diagnosticResult.calibrated_level === 'advanced'
                        ? 'bg-purple-500/30 text-purple-300 border border-purple-500/50'
                        : diagnosticResult.calibrated_level === 'intermediate'
                          ? 'bg-indigo-500/30 text-indigo-300 border border-indigo-500/50'
                          : 'bg-emerald-500/30 text-emerald-300 border border-emerald-500/50'
                    }`}>
                      {language === 'ta' 
                        ? (diagnosticResult.calibrated_level === 'beginner' ? 'அடிப்படை' : diagnosticResult.calibrated_level === 'intermediate' ? 'இடைநிலை' : 'மேம்பட்ட நிலை')
                        : diagnosticResult.calibrated_level}
                    </span>
                    <span className="text-2xs text-slate-400">
                      • {language === 'ta' ? 'பரிந்துரைக்கப்பட்ட காட்சி முறை: ' : 'Recommended Visual: '}
                      <strong className="text-indigo-200 uppercase">{diagnosticResult.recommended_visual_format}</strong>
                    </span>
                  </div>
                </div>

                {/* Demonstrated Strengths */}
                {diagnosticResult.demonstrated_strengths && diagnosticResult.demonstrated_strengths.length > 0 && (
                  <div className="space-y-1.5 p-3 bg-emerald-50/70 dark:bg-emerald-950/30 rounded-xl border border-emerald-200 dark:border-emerald-800">
                    <span className="text-2xs font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-300 block">
                      {language === 'ta' ? 'நிரூபிக்கப்பட்ட பலங்கள்:' : 'Demonstrated Strengths:'}
                    </span>
                    {diagnosticResult.demonstrated_strengths.map((str, idx) => (
                      <div key={idx} className="flex items-center space-x-1.5 text-xs text-emerald-800 dark:text-emerald-200">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 flex-shrink-0" />
                        <span>{str}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Knowledge Gaps */}
                {diagnosticResult.knowledge_gaps && diagnosticResult.knowledge_gaps.length > 0 && (
                  <div className="space-y-1.5 p-3 bg-amber-50/70 dark:bg-amber-950/30 rounded-xl border border-amber-200 dark:border-amber-800">
                    <span className="text-2xs font-bold uppercase tracking-wider text-amber-700 dark:text-amber-300 block">
                      {language === 'ta' ? 'கவனம் செலுத்த வேண்டிய பகுதிகள்:' : 'Knowledge Gaps (To Be Addressed):'}
                    </span>
                    {diagnosticResult.knowledge_gaps.map((gap, idx) => (
                      <div key={idx} className="flex items-center space-x-1.5 text-xs text-amber-800 dark:text-amber-200">
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400 flex-shrink-0" />
                        <span>{gap}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Possible Misconceptions */}
                {diagnosticResult.possible_misconceptions && diagnosticResult.possible_misconceptions.length > 0 && (
                  <div className="p-3 bg-rose-50 dark:bg-rose-950/40 rounded-xl border border-rose-200 dark:border-rose-800 text-xs space-y-1">
                    <span className="font-bold text-rose-700 dark:text-rose-300 flex items-center space-x-1.5">
                      <AlertTriangle className="w-4 h-4 text-rose-500 flex-shrink-0" />
                      <span>{language === 'ta' ? 'சாத்தியமான தவறான புரிதல்:' : 'Possible Misconception Hypothesis:'}</span>
                    </span>
                    <p className="text-rose-900 dark:text-rose-200 leading-relaxed pl-5">
                      {diagnosticResult.possible_misconceptions[0].hypothesis_text || diagnosticResult.possible_misconceptions[0].misconception_title}
                    </p>
                  </div>
                )}

                {/* Diagnostic Summary Narrative */}
                <div className="p-3 bg-slate-50 dark:bg-slate-800/60 rounded-xl border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 leading-relaxed italic">
                  "{diagnosticResult.diagnostic_summary}"
                </div>

                {/* Action Button */}
                <div className="pt-2">
                  <button
                    onClick={() => {
                      setLevel(diagnosticResult.calibrated_level);
                      if (diagnosticResult.recommended_visual_format) {
                        setSelectedFormat(diagnosticResult.recommended_visual_format);
                      }
                      setDiagnosticOpen(false);
                      loadExplanation(diagnosticResult.calibrated_level, diagnosticResult.recommended_visual_format || selectedFormat);
                    }}
                    className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold shadow-sm transition flex items-center justify-center space-x-1.5"
                  >
                    <span>
                      {language === 'ta'
                        ? `${diagnosticResult.calibrated_level === 'beginner' ? 'அடிப்படை' : diagnosticResult.calibrated_level === 'intermediate' ? 'இடைநிலை' : 'மேம்பட்ட'} விளக்க முறைக்கு மாறவும்`
                        : `Apply ${diagnosticResult.calibrated_level.toUpperCase()} Explanation & Visual Representation`}
                    </span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ) : diagnosticData?.questions && diagnosticData.questions.length > 0 ? (
              /* Step-by-Step Diagnostic Questionnaire Flow */
              <div className="space-y-4">
                
                {/* Progress Bar & Aspect Badge */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-2xs">
                    <span className="font-bold text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                      {language === 'ta' 
                        ? `வினா ${diagnosticIndex + 1} / ${diagnosticData.questions.length}` 
                        : `Question ${diagnosticIndex + 1} of ${diagnosticData.questions.length}`}
                    </span>
                    <span className="px-2 py-0.5 rounded font-semibold bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
                      {diagnosticData.questions[diagnosticIndex].diagnostic_aspect || (diagnosticData.questions[diagnosticIndex].is_prerequisite ? "Prerequisite Foundation" : "Core Concept")}
                    </span>
                  </div>
                  <div className="w-full h-1.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-indigo-600 transition-all duration-300 rounded-full"
                      style={{ width: `${((diagnosticIndex + 1) / diagnosticData.questions.length) * 100}%` }}
                    />
                  </div>
                </div>

                {/* Current Question Text */}
                <div className="p-3.5 bg-slate-50/70 dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700">
                  <p className="text-xs font-semibold text-slate-900 dark:text-white leading-relaxed">
                    {diagnosticData.questions[diagnosticIndex].question}
                  </p>
                </div>

                {/* MCQ Options or Open-ended/Numerical Input */}
                {diagnosticData.questions[diagnosticIndex].options && diagnosticData.questions[diagnosticIndex].options.length > 0 ? (
                  <div className="space-y-2">
                    {diagnosticData.questions[diagnosticIndex].options.map((opt) => (
                      <label
                        key={opt.key}
                        onClick={() => handleSelectDiagnosticOption(opt.key)}
                        className={`flex items-start space-x-2.5 p-3 rounded-xl border text-xs cursor-pointer transition select-none ${
                          diagnosticAnswers[diagnosticIndex] === opt.key
                            ? 'bg-indigo-600 text-white border-indigo-600 shadow-xs'
                            : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-750'
                        }`}
                      >
                        <span className="font-bold">{opt.key}.</span>
                        <span className="leading-snug">{opt.text}</span>
                      </label>
                    ))}
                  </div>
                ) : diagnosticData.questions[diagnosticIndex].question_type === 'numerical' ? (
                  <div className="space-y-2">
                    <input
                      type="text"
                      value={diagnosticAnswers[diagnosticIndex] || ''}
                      onChange={(e) => handleTextDiagnosticChange(e.target.value)}
                      placeholder={language === 'ta' ? 'கணக்கிடப்பட்ட எண்ணியல் விடையை உள்ளிடவும்...' : 'Enter your calculated numerical answer...'}
                      className="w-full text-xs p-3 rounded-xl bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 shadow-2xs"
                    />
                  </div>
                ) : (
                  <div className="space-y-2">
                    <textarea
                      rows={4}
                      value={diagnosticAnswers[diagnosticIndex] || ''}
                      onChange={(e) => handleTextDiagnosticChange(e.target.value)}
                      placeholder={language === 'ta' ? 'பாடக் கொள்கைகளின் அடிப்படையில் உங்கள் விளக்கத்தை இங்கே தட்டச்சு செய்யவும்...' : 'Type your explanation here based on course principles...'}
                      className="w-full text-xs p-3 rounded-xl bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 shadow-2xs resize-y"
                    />
                    <p className="text-3xs text-slate-400 dark:text-slate-500">
                      {language === 'ta' ? 'உங்கள் புரிதலை மதிப்பிடுவதற்கு முக்கிய கருத்துக்கள் அல்லது கொள்கைகளை உங்கள் சொந்த வார்த்தைகளில் விளக்குங்கள்.' : 'Explain key concepts, steps, or principles in your own words to calibrate your mastery.'}
                    </p>
                  </div>
                )}

                {/* Navigation & Submit Buttons */}
                <div className="flex items-center justify-between pt-2 border-t border-slate-100 dark:border-slate-800">
                  <button
                    onClick={handlePrevDiagnosticQuestion}
                    disabled={diagnosticIndex === 0}
                    className="px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white disabled:opacity-30 disabled:pointer-events-none rounded-lg"
                  >
                    {language === 'ta' ? '← முந்தையது' : '← Previous'}
                  </button>

                  {diagnosticIndex < diagnosticData.questions.length - 1 ? (
                    <button
                      onClick={handleNextDiagnosticQuestion}
                      disabled={!diagnosticAnswers[diagnosticIndex] || !String(diagnosticAnswers[diagnosticIndex]).trim()}
                      className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 text-white rounded-xl text-xs font-semibold shadow-sm transition flex items-center space-x-1"
                    >
                      <span>{language === 'ta' ? 'அடுத்த வினா' : 'Next Question'}</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  ) : (
                    <button
                      onClick={handleSubmitDiagnostic}
                      disabled={!diagnosticAnswers[diagnosticIndex] || !String(diagnosticAnswers[diagnosticIndex]).trim()}
                      className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-40 text-white rounded-xl text-xs font-semibold shadow-sm transition flex items-center space-x-1"
                    >
                      <Check className="w-3.5 h-3.5" />
                      <span>{language === 'ta' ? 'மதிப்பீட்டை முடித்து அளவிடவும்' : 'Finish & Calibrate Mastery'}</span>
                    </button>
                  )}
                </div>

              </div>
            ) : (
              <p className="text-xs text-rose-500 py-4 text-center">Unable to generate diagnostic questions for this topic.</p>
            )}

          </div>
        </div>
      )}

    </div>
  );
};
