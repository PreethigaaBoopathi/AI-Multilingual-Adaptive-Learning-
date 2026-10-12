import React, { useState, useEffect } from 'react';
import { 
  CheckCircle2, XCircle, Award, AlertTriangle, 
  HelpCircle, ArrowRight, RotateCcw, Sparkles,
  BookOpen, Calculator, FileText, Compass,
  Lightbulb, RefreshCw, MessageSquare, ShieldCheck,
  ChevronRight, Check, CornerDownRight
} from 'lucide-react';
import { textbookAPI } from '../../services/api';
import { useTextbook } from '../../context/TextbookContext';

export const QuizTab = ({ onNavigateToRevision }) => {
  const { activeTextbook, language } = useTextbook();
  const [topic, setTopic] = useState('All');
  const [availableTopics, setAvailableTopics] = useState([]);
  const [difficulty, setDifficulty] = useState('medium');
  const [questionTypeFilter, setQuestionTypeFilter] = useState('all');
  const [numQuestions, setNumQuestions] = useState(5);
  const [quizData, setQuizData] = useState(null);
  const [userAnswers, setUserAnswers] = useState({});
  const [submissionResult, setSubmissionResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  
  // Extract course topics dynamically from uploaded textbook and concept graph
  useEffect(() => {
    let isMounted = true;
    const extractTopics = async () => {
      if (!activeTextbook) {
        if (isMounted) setAvailableTopics([]);
        return;
      }
      const topicSet = new Set();

      // 1. Extract from textbook chapters & sections
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

      // 2. Extract from dynamic concept graph
      try {
        const graph = await textbookAPI.getConceptGraph(activeTextbook.id);
        if (graph?.nodes && Array.isArray(graph.nodes)) {
          graph.nodes.forEach(node => {
            if (node.name) topicSet.add(node.name.trim());
            if (node.topic) topicSet.add(node.topic.trim());
          });
        }
      } catch (e) {
        // Concept graph optional
      }

      // 3. Fallback to active textbook title
      if (topicSet.size === 0 && activeTextbook.title) {
        topicSet.add(activeTextbook.title.trim());
      }

      const list = Array.from(topicSet).filter(Boolean);
      if (isMounted) {
        setAvailableTopics(list);
        setTopic('All');
      }
    };

    extractTopics();
    return () => { isMounted = false; };
  }, [activeTextbook]);

  // Clarification state for uncertain misconceptions
  const [clarifyingInputs, setClarifyingInputs] = useState({});
  const [clarifiedResponses, setClarifiedResponses] = useState({});
  const [clarifyingLoading, setClarifyingLoading] = useState({});

  // Adaptive next step state
  const [adaptiveStep, setAdaptiveStep] = useState(null);
  const [adaptiveLoading, setAdaptiveLoading] = useState(false);

  const startAssessment = async (overrideDifficulty = null, overrideConcept = null) => {
    if (!activeTextbook) return;
    try {
      setLoading(true);
      setSubmissionResult(null);
      setUserAnswers({});
      setClarifyingInputs({});
      setClarifiedResponses({});
      setAdaptiveStep(null);

      const qTypes = questionTypeFilter === 'all' 
        ? ['mcq', 'short_answer', 'numerical', 'concept_relationship']
        : [questionTypeFilter];

      const data = await textbookAPI.generateAssessment(
        activeTextbook.id,
        overrideConcept || topic,
        overrideDifficulty || difficulty,
        qTypes,
        numQuestions,
        'demo_user',
        overrideConcept,
        null,
        language
      );

      setQuizData(data);
    } catch (err) {
      console.error('Assessment generate error:', err);
      // Fallback to legacy quiz generation
      try {
        const fallbackTopic = topic === 'All' 
          ? (availableTopics[0] || activeTextbook.title || 'Course Material') 
          : topic;
        const fallback = await textbookAPI.generateQuiz(
          activeTextbook.id,
          fallbackTopic,
          overrideDifficulty || difficulty,
          numQuestions,
          language
        );
        setQuizData(fallback);
      } catch (fErr) {
        console.error('Fallback error:', fErr);
      }
    } finally {
      setLoading(false);
    }
  };

  // Re-generate / re-localize assessment questions when language toggles
  useEffect(() => {
    if (quizData && quizData.questions && quizData.questions.length > 0 && !submissionResult && !loading) {
      startAssessment();
    }
  }, [language]);

  const handleSelectOption = (questionId, optionKey) => {
    if (submissionResult) return;
    setUserAnswers(prev => ({
      ...prev,
      [questionId]: optionKey
    }));
  };

  const handleTextAnswerChange = (questionId, value) => {
    if (submissionResult) return;
    setUserAnswers(prev => ({
      ...prev,
      [questionId]: value
    }));
  };

  const handleSubmitAssessment = async () => {
    if (!quizData || submitting) return;
    try {
      setSubmitting(true);
      const answersPayload = quizData.questions.map(q => ({
        question_id: q.id,
        student_answer: userAnswers[q.id] || (q.question_type === 'mcq' ? 'NONE' : ''),
        question_text: q.question,
        topic: q.topic,
        concept_name: q.concept_name || q.topic,
        question_type: q.question_type || 'mcq',
        difficulty: q.difficulty || difficulty
      }));

      const result = await textbookAPI.submitAssessment(
        activeTextbook.id,
        answersPayload,
        'demo_user',
        language
      );
      setSubmissionResult(result);

      // Trigger adaptive next step analysis
      fetchAdaptiveNextStep();
    } catch (err) {
      console.error('Assessment submit error:', err);
      // Fallback to submitQuiz
      try {
        const legacyAnswers = quizData.questions.map(q => ({
          question_id: typeof q.id === 'number' ? q.id : 1,
          selected_key: userAnswers[q.id] || 'NONE'
        }));
        const fallbackRes = await textbookAPI.submitQuiz(
          activeTextbook.id,
          quizData.quiz_id || 'quiz_auto',
          topic,
          legacyAnswers,
          'demo_user',
          language
        );
        setSubmissionResult(fallbackRes);
      } catch (fErr) {
        console.error('Fallback submit error:', fErr);
      }
    } finally {
      setSubmitting(false);
    }
  };

  const fetchAdaptiveNextStep = async () => {
    try {
      setAdaptiveLoading(true);
      const nextStepData = await textbookAPI.getAdaptiveNextStep(
        activeTextbook.id,
        topic,
        null,
        null,
        null,
        'demo_user'
      );
      setAdaptiveStep(nextStepData);
    } catch (err) {
      console.error('Error fetching adaptive next step:', err);
    } finally {
      setAdaptiveLoading(false);
    }
  };

  const handleClarifySubmit = async (questionId, conceptName) => {
    const text = clarifyingInputs[questionId];
    if (!text || text.trim() === '') return;

    try {
      setClarifyingLoading(prev => ({ ...prev, [questionId]: true }));
      const res = await textbookAPI.clarifyReasoning(
        activeTextbook.id,
        questionId,
        conceptName,
        text,
        'demo_user'
      );
      setClarifiedResponses(prev => ({ ...prev, [questionId]: res }));
    } catch (err) {
      console.error('Clarify reasoning error:', err);
    } finally {
      setClarifyingLoading(prev => ({ ...prev, [questionId]: false }));
    }
  };

  const getQuestionTypeBadge = (type) => {
    switch (type) {
      case 'short_answer':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md bg-sky-50 dark:bg-sky-950/60 text-sky-700 dark:text-sky-300 border border-sky-200 dark:border-sky-800 text-3xs font-semibold">
            <FileText className="w-3 h-3" />
            <span>Short Answer</span>
          </span>
        );
      case 'numerical':
      case 'problem_solving':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800 text-3xs font-semibold">
            <Calculator className="w-3 h-3" />
            <span>Numerical / Problem</span>
          </span>
        );
      case 'concept_relationship':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md bg-purple-50 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800 text-3xs font-semibold">
            <Compass className="w-3 h-3" />
            <span>Prerequisite & Relationship</span>
          </span>
        );
      case 'mcq':
      default:
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 text-3xs font-semibold">
            <BookOpen className="w-3 h-3" />
            <span>Multiple Choice</span>
          </span>
        );
    }
  };

  return (
    <div className="space-y-6 text-slate-900 dark:text-slate-100">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-xl font-bold text-slate-900 dark:text-white">Misconception-Aware Adaptive Assessment</h2>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Dynamic evidence-grounded questions across MCQs, short answers, numerical calculations, and prerequisite graphs with misconception diagnostics.
          </p>
        </div>

        {quizData && (
          <div className="flex items-center space-x-2.5">
            <button
              onClick={() => {
                setQuizData(null);
                setSubmissionResult(null);
                setUserAnswers({});
                setAdaptiveStep(null);
              }}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 text-xs font-semibold rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-all shadow-2xs"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>New Assessment</span>
            </button>
          </div>
        )}
      </div>

      {/* Assessment Configuration if not started */}
      {!quizData && (
        <div className="academic-card p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-5 animate-fade-in rounded-xl">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-sm text-slate-900 dark:text-white flex items-center space-x-2">
              <Sparkles className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
              <span>Configure Dynamic Assessment Drill</span>
            </h3>
            <span className="text-3xs text-slate-500 dark:text-slate-400">
              Course: {activeTextbook?.title || 'Selected Course'}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            
            {/* Topic Selection */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                Target Topic / Concept
              </label>
              <select
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                className="w-full text-xs bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg p-2.5 font-medium text-slate-800 dark:text-slate-200 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
              >
                <option value="All">All Course Topics (Comprehensive)</option>
                {availableTopics.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>

            {/* Question Modality Filter */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                Question Modality
              </label>
              <select
                value={questionTypeFilter}
                onChange={(e) => setQuestionTypeFilter(e.target.value)}
                className="w-full text-xs bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg p-2.5 font-medium text-slate-800 dark:text-slate-200 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
              >
                <option value="all">All Types (MCQ, Short, Calc, Graph)</option>
                <option value="mcq">Multiple Choice Only</option>
                <option value="short_answer">Short Answer Only</option>
                <option value="numerical">Numerical / Problem-Solving</option>
                <option value="concept_relationship">Prerequisite & Relationship</option>
              </select>
            </div>

            {/* Difficulty Selection */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                Difficulty Level
              </label>
              <div className="grid grid-cols-3 gap-1 bg-slate-100 dark:bg-slate-800 p-1 rounded-lg border border-slate-200 dark:border-slate-700 text-xs font-semibold">
                {['easy', 'medium', 'hard'].map((lvl) => (
                  <button
                    key={lvl}
                    type="button"
                    onClick={() => setDifficulty(lvl)}
                    className={`py-1.5 rounded-md capitalize transition-all ${
                      difficulty === lvl
                        ? 'bg-white dark:bg-slate-700 text-indigo-700 dark:text-indigo-300 shadow-2xs font-bold'
                        : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                    }`}
                  >
                    {lvl}
                  </button>
                ))}
              </div>
            </div>

            {/* Number of questions */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                Question Count
              </label>
              <div className="grid grid-cols-3 gap-1 bg-slate-100 dark:bg-slate-800 p-1 rounded-lg border border-slate-200 dark:border-slate-700 text-xs font-semibold">
                {[3, 5, 8].map((cnt) => (
                  <button
                    key={cnt}
                    type="button"
                    onClick={() => setNumQuestions(cnt)}
                    className={`py-1.5 rounded-md transition-all ${
                      numQuestions === cnt
                        ? 'bg-white dark:bg-slate-700 text-indigo-700 dark:text-indigo-300 shadow-2xs font-bold'
                        : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                    }`}
                  >
                    {cnt} Qs
                  </button>
                ))}
              </div>
            </div>

          </div>

          <button
            onClick={() => startAssessment()}
            disabled={loading}
            className="w-full sm:w-auto px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-bold rounded-xl shadow-sm transition-all"
          >
            {loading ? 'Generating Evidence-Grounded Questions...' : 'Start Adaptive Assessment'}
          </button>
        </div>
      )}

      {/* Active Assessment Form */}
      {quizData && (
        <div className="space-y-6 animate-fade-in">
          
          {/* Submission Result Summary Banner */}
          {submissionResult && (
            <div className="academic-card p-6 bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white shadow-md space-y-4 rounded-xl border-none">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="flex items-center space-x-3">
                  <div className="w-12 h-12 rounded-xl bg-white/10 flex items-center justify-center text-emerald-400 font-extrabold text-xl">
                    {submissionResult.score_percentage}%
                  </div>
                  <div>
                    <h3 className="font-bold text-base">Assessment Evaluation Result</h3>
                    <p className="text-xs text-slate-300">
                      You answered {submissionResult.correct_count} of {submissionResult.total_questions} questions correctly.
                    </p>
                  </div>
                </div>

                {submissionResult.weak_concepts && submissionResult.weak_concepts.length > 0 && (
                  <button
                    onClick={onNavigateToRevision}
                    className="inline-flex items-center space-x-2 px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-bold text-xs rounded-xl shadow-sm transition-all"
                  >
                    <span>Remediate in Adaptive Revision</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>

              {/* Recommendation Note */}
              <div className="text-xs text-indigo-200 bg-indigo-900/50 p-3 rounded-lg border border-indigo-700/50">
                <span className="font-bold text-white">AI Diagnostic Insight: </span>
                {submissionResult.next_recommendation || submissionResult.recommendation}
              </div>
            </div>
          )}

          {/* Adaptive Next Step / Prerequisite Banner */}
          {submissionResult && adaptiveStep && (
            <div className="academic-card p-5 bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-900/60 rounded-xl space-y-3 animate-fade-in">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start space-x-2.5">
                  <div className="p-1.5 bg-indigo-600 text-white rounded-lg flex-shrink-0 mt-0.5">
                    <Sparkles className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-indigo-950 dark:text-indigo-200 uppercase tracking-wider">
                      {adaptiveStep.action_type === 'prerequisite_drill' && 'Prerequisite Remediation Recommended'}
                      {adaptiveStep.action_type === 'difficulty_increase' && 'Adaptive Level-Up Available'}
                      {adaptiveStep.action_type === 'misconception_resolution' && 'Targeted Misconception Contrast Drill'}
                      {adaptiveStep.action_type === 'mastery_check' && 'Next Adaptive Practice Drill'}
                    </h4>
                    <p className="text-xs text-indigo-900 dark:text-indigo-300 mt-1 leading-relaxed">
                      {adaptiveStep.rationale}
                    </p>
                  </div>
                </div>

                {adaptiveStep.next_question && (
                  <button
                    onClick={() => {
                      setQuizData({
                        course_id: activeTextbook.id,
                        topic: adaptiveStep.next_question.topic,
                        difficulty: adaptiveStep.next_question.difficulty,
                        questions: [adaptiveStep.next_question]
                      });
                      setSubmissionResult(null);
                      setUserAnswers({});
                      setAdaptiveStep(null);
                    }}
                    className="inline-flex items-center space-x-1.5 px-3.5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs rounded-xl shadow-sm transition-all flex-shrink-0"
                  >
                    <span>Take Adaptive Drill</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Question List */}
          <div className="space-y-5">
            {quizData.questions.map((q, idx) => {
              const selectedAnswer = userAnswers[q.id];
              const evalInfo = submissionResult?.evaluations?.find(e => e.question_id === q.id) ||
                               submissionResult?.results?.find(r => r.question_id === q.id);

              const citation = q.source_citation || { page: q.source_page, filename: 'Course Material' };
              const misconception = evalInfo?.misconception;

              return (
                <div key={q.id || idx} className="academic-card p-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-4 rounded-xl">
                  
                  {/* Question Header & Modality Badges */}
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="flex items-start space-x-2">
                      <span className="w-6 h-6 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-400 font-bold flex items-center justify-center text-xs flex-shrink-0">
                        {idx + 1}
                      </span>
                      <div>
                        <div className="flex items-center space-x-2 mb-1">
                          {getQuestionTypeBadge(q.question_type)}
                          <span className="text-3xs font-medium px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 capitalize">
                            Difficulty: {q.difficulty || 'medium'}
                          </span>
                        </div>
                        <p className="text-xs font-semibold text-slate-900 dark:text-white leading-snug">
                          {q.question}
                        </p>
                      </div>
                    </div>

                    {/* Source Citation Pill */}
                    <div className="flex items-center space-x-1 px-2 py-0.5 bg-slate-100 dark:bg-slate-800/80 rounded text-3xs font-mono text-slate-600 dark:text-slate-300">
                      <ShieldCheck className="w-3 h-3 text-indigo-500" />
                      <span>
                        {citation.timestamp ? `Time: ${citation.timestamp}` : (citation.slide ? `Slide ${citation.slide}` : `Page ${citation.page || 1}`)}
                      </span>
                    </div>
                  </div>

                  {/* MCQ Options Rendering */}
                  {(!q.question_type || q.question_type === 'mcq' || q.question_type === 'concept_relationship') && q.options && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
                      {q.options.map((opt) => {
                        const isSelected = selectedAnswer === opt.key;
                        let optionStyle = 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600 text-slate-700 dark:text-slate-200';

                        if (submissionResult && evalInfo) {
                          if (opt.key === q.correct_key) {
                            optionStyle = 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-500 text-emerald-900 dark:text-emerald-300 font-medium ring-1 ring-emerald-500';
                          } else if (isSelected && opt.key !== q.correct_key) {
                            optionStyle = 'bg-rose-50 dark:bg-rose-950/40 border-rose-500 text-rose-900 dark:text-rose-300 font-medium';
                          }
                        } else if (isSelected) {
                          optionStyle = 'bg-indigo-50 dark:bg-indigo-950/50 border-indigo-600 dark:border-indigo-400 text-indigo-900 dark:text-indigo-200 font-semibold ring-1 ring-indigo-600';
                        }

                        return (
                          <div
                            key={opt.key}
                            onClick={() => handleSelectOption(q.id, opt.key)}
                            className={`p-3 rounded-lg border text-xs cursor-pointer select-none transition-all flex items-start space-x-2.5 ${optionStyle}`}
                          >
                            <span className="font-bold font-mono text-2xs uppercase w-4 h-4 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center flex-shrink-0 text-slate-700 dark:text-slate-300">
                              {opt.key}
                            </span>
                            <span className="leading-snug">{opt.text}</span>
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {/* Short Answer Input Rendering */}
                  {q.question_type === 'short_answer' && (
                    <div className="space-y-2 pt-1">
                      <textarea
                        rows={3}
                        disabled={!!submissionResult}
                        value={userAnswers[q.id] || ''}
                        onChange={(e) => handleTextAnswerChange(q.id, e.target.value)}
                        placeholder="Type your explanation here based on course principles..."
                        className="w-full text-xs p-3 rounded-lg bg-slate-50 dark:bg-slate-800/80 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                      />
                    </div>
                  )}

                  {/* Numerical Input Rendering */}
                  {(q.question_type === 'numerical' || q.question_type === 'problem_solving') && (
                    <div className="space-y-2 pt-1">
                      <div className="flex items-center space-x-2 max-w-sm">
                        <input
                          type="text"
                          disabled={!!submissionResult}
                          value={userAnswers[q.id] || ''}
                          onChange={(e) => handleTextAnswerChange(q.id, e.target.value)}
                          placeholder="Enter calculated numerical result..."
                          className="w-full text-xs p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/80 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                        />
                      </div>
                    </div>
                  )}

                  {/* Post-Submission Grounded Feedback & Evaluation */}
                  {submissionResult && evalInfo && (
                    <div className="space-y-3 pt-2">
                      <div className={`p-3 rounded-lg text-xs border ${
                        evalInfo.is_correct 
                          ? 'bg-emerald-50/60 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-900/50 text-emerald-900 dark:text-emerald-300' 
                          : evalInfo.score > 0 
                            ? 'bg-amber-50/60 dark:bg-amber-950/30 border-amber-200 dark:border-amber-900/50 text-amber-900 dark:text-amber-300'
                            : 'bg-rose-50/60 dark:bg-rose-950/30 border-rose-200 dark:border-rose-900/50 text-rose-900 dark:text-rose-300'
                      }`}>
                        <div className="flex items-center justify-between font-bold mb-1">
                          <div className="flex items-center space-x-1.5">
                            {evalInfo.is_correct ? (
                              <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                            ) : (
                              <XCircle className="w-4 h-4 text-rose-600 dark:text-rose-400" />
                            )}
                            <span>
                              {evalInfo.is_correct ? 'Correct Answer' : (evalInfo.score > 0 ? 'Partially Correct' : 'Incorrect')}
                            </span>
                          </div>
                          <span className="text-3xs font-mono font-bold">
                            Score: {evalInfo.score !== undefined ? `${Math.round(evalInfo.score * 100)}%` : (evalInfo.is_correct ? '100%' : '0%')}
                          </span>
                        </div>

                        <p className="text-slate-700 dark:text-slate-300 text-2xs leading-relaxed mt-1">
                          {evalInfo.feedback || evalInfo.explanation || q.explanation}
                        </p>
                      </div>

                      {/* Possible Misconception Diagnostic Card */}
                      {misconception && (
                        <div className="p-3.5 bg-amber-50/80 dark:bg-amber-950/25 border border-amber-300 dark:border-amber-800/60 rounded-xl space-y-2.5 animate-fade-in">
                          <div className="flex items-center space-x-2 text-amber-900 dark:text-amber-200 font-bold text-xs">
                            <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 flex-shrink-0" />
                            <span>Possible Misconception Hypothesis: {misconception.misconception_title}</span>
                          </div>

                          <p className="text-2xs text-amber-900 dark:text-amber-200/90 leading-relaxed">
                            {misconception.hypothesis_text}
                          </p>

                          <div className="p-2.5 bg-white/70 dark:bg-slate-900/60 rounded-lg text-3xs space-y-1 border border-amber-200/60 dark:border-amber-800/30">
                            <span className="font-bold text-amber-950 dark:text-amber-100">Expected Understanding: </span>
                            <span className="text-slate-700 dark:text-slate-300">{misconception.expected_understanding}</span>
                          </div>

                          {/* Clarify Student Reasoning if Confidence is Moderate/Uncertain */}
                          {misconception.clarifying_question && (
                            <div className="pt-2 border-t border-amber-200/60 dark:border-amber-800/40 space-y-2">
                              <div className="flex items-center space-x-1.5 text-2xs font-semibold text-slate-800 dark:text-slate-200">
                                <MessageSquare className="w-3.5 h-3.5 text-indigo-500" />
                                <span>Clarifying Follow-Up: {misconception.clarifying_question}</span>
                              </div>

                              {!clarifiedResponses[q.id] ? (
                                <div className="flex flex-col sm:flex-row gap-2">
                                  <input
                                    type="text"
                                    value={clarifyingInputs[q.id] || ''}
                                    onChange={(e) => setClarifyingInputs(prev => ({ ...prev, [q.id]: e.target.value }))}
                                    placeholder="Explain your reasoning here..."
                                    className="flex-1 text-2xs p-2 rounded-lg bg-white dark:bg-slate-900 border border-amber-200 dark:border-slate-700 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                                  />
                                  <button
                                    onClick={() => handleClarifySubmit(q.id, q.concept_name || q.topic)}
                                    disabled={clarifyingLoading[q.id] || !clarifyingInputs[q.id]}
                                    className="px-3 py-1.5 bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white font-bold text-2xs rounded-lg transition-all"
                                  >
                                    {clarifyingLoading[q.id] ? 'Submitting...' : 'Clarify Reasoning'}
                                  </button>
                                </div>
                              ) : (
                                <div className="p-2 bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800/40 rounded text-3xs text-emerald-900 dark:text-emerald-300">
                                  ✓ {clarifiedResponses[q.id].updated_feedback}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}

                </div>
              );
            })}
          </div>

          {/* Submit Action Bar */}
          {!submissionResult && (
            <div className="flex justify-end pt-2">
              <button
                onClick={handleSubmitAssessment}
                disabled={submitting || Object.keys(userAnswers).length === 0}
                className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-bold rounded-xl shadow-sm transition-all"
              >
                {submitting ? 'Evaluating Answers with Evidence Grounding...' : `Submit Assessment (${Object.keys(userAnswers).length}/${quizData.questions.length} Answered)`}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
