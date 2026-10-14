import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 120000,
});

// Automatic JWT Authorization header injection
api.interceptors.request.use(
  (config) => {
    try {
      const token = localStorage.getItem('textiq_auth_token') || sessionStorage.getItem('textiq_auth_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch {
      // ignore storage access errors
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Automatic 401 Unauthorized handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      try {
        localStorage.removeItem('textiq_auth_token');
        localStorage.removeItem('learning_system_user');
        sessionStorage.removeItem('textiq_auth_token');
        sessionStorage.removeItem('learning_system_user');
        window.dispatchEvent(new CustomEvent('auth:unauthorized'));
      } catch {
        // ignore storage errors
      }
    }
    return Promise.reject(error);
  }
);

export const authAPI = {
  login: async (email, password, rememberMe = false) => {
    const res = await api.post('/auth/login', {
      email,
      password,
      remember_me: rememberMe
    });
    return res.data;
  },
  register: async (userData) => {
    const res = await api.post('/auth/register', userData);
    return res.data;
  },
  getMe: async () => {
    const res = await api.get('/auth/me');
    return res.data;
  },
  updateProfile: async (profileData) => {
    const res = await api.put('/auth/profile', profileData);
    return res.data;
  },
  forgotPassword: async (email) => {
    const res = await api.post('/auth/forgot-password', { email });
    return res.data;
  },
  resetPassword: async (email, resetToken, newPassword) => {
    const res = await api.post('/auth/reset-password', {
      email,
      reset_token: resetToken,
      new_password: newPassword
    });
    return res.data;
  },
  logout: async () => {
    try {
      await api.post('/auth/logout');
    } catch {
      // ignore
    }
  }
};

export const textbookAPI = {
  getTextbooks: async () => {
    const res = await api.get('/textbooks');
    return res.data;
  },
  getTextbookById: async (id) => {
    const res = await api.get(`/textbook/${id}`);
    return res.data;
  },
  deleteTextbook: async (id) => {
    const res = await api.delete(`/textbooks/${id}`);
    return res.data;
  },
  clearAllTextbooks: async () => {
    const res = await api.delete('/textbooks');
    return res.data;
  },
  loadSampleTextbook: async () => {
    const res = await api.post('/sample-textbook');
    return res.data;
  },
  uploadPDF: async (formData) => {
    const res = await api.post('/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 600000, // 10 minutes for large videos and multimodal extraction
    });
    return res.data;
  },
  summarize: async (textbookId, chapterId, sectionId, language = 'en') => {
    const res = await api.post('/summarize', {
      textbook_id: textbookId,
      chapter_id: chapterId,
      section_id: sectionId,
      language,
    });
    return res.data;
  },
  explainConcept: async (textbookId, topic, level = 'beginner', language = 'en') => {
    const res = await api.post('/explain', {
      textbook_id: textbookId,
      topic_or_concept: topic,
      level,
      language,
    });
    return res.data;
  },
  visualize: async (textbookId, topic, diagramType = 'auto', level = 'intermediate', language = 'en') => {
    const res = await api.post('/visualize', {
      textbook_id: textbookId,
      topic,
      diagram_type: diagramType,
      level,
      language,
    });
    return res.data;
  },
  chatWithTextbook: async (textbookId, query, language = 'en', enableOutsideKnowledge = false, conversationHistory = []) => {
    const res = await api.post('/chat', {
      textbook_id: textbookId,
      query,
      language,
      enable_outside_knowledge: enableOutsideKnowledge,
      conversation_history: conversationHistory,
    });
    return res.data;
  },
  generateQuiz: async (textbookId, topic, difficulty = 'medium', numQuestions = 5, language = 'en') => {
    const res = await api.post('/quiz/generate', {
      textbook_id: textbookId,
      topic,
      difficulty,
      num_questions: numQuestions,
      language,
    });
    return res.data;
  },
  submitQuiz: async (textbookId, quizId, topic, difficulty, answers, userId = 'demo_user', language = 'en') => {
    const res = await api.post(`/quiz/submit?user_id=${userId}`, {
      quiz_id: quizId,
      textbook_id: textbookId,
      topic,
      difficulty,
      answers,
      language,
    });
    return res.data;
  },
  getPerformance: async (userId = 'demo_user') => {
    const res = await api.get(`/performance?user_id=${userId}`);
    return res.data;
  },
  getRecommendations: async (userId = 'demo_user', topic = null, language = 'en', courseId = null) => {
    let url = `/recommendations?user_id=${userId}&language=${language || 'en'}`;
    if (topic) url += `&topic=${encodeURIComponent(topic)}`;
    if (courseId) url += `&course_id=${encodeURIComponent(courseId)}`;
    const res = await api.get(url);
    return res.data;
  },
  translate: async (text, targetLang = 'ta') => {
    const res = await api.post('/translate', {
      text,
      target_language: targetLang,
    });
    return res.data;
  },
  getConceptGraph: async (textbookId) => {
    const res = await api.get(`/concept-graph/${textbookId}`);
    return res.data;
  },
  generateConceptGraph: async (courseId, forceRegenerate = false) => {
    const res = await api.post('/concept-graph/generate', {
      course_id: courseId,
      force_regenerate: forceRegenerate,
    });
    return res.data;
  },
  getConceptDetails: async (textbookId, conceptId) => {
    const res = await api.get(`/concept-graph/${textbookId}/concept/${conceptId}`);
    return res.data;
  },
  getLearningPaths: async (textbookId) => {
    const res = await api.get(`/concept-graph/${textbookId}/learning-paths`);
    return res.data;
  },
  // --- Innovation 4: Misconception-Aware Adaptive Assessment API ---
  generateAssessment: async (courseId, topic = 'All', difficulty = 'medium', questionTypes = ['mcq', 'short_answer', 'numerical', 'concept_relationship'], numQuestions = 5, userId = 'demo_user', targetConcept = null, focusMisconception = null, language = 'en') => {
    const res = await api.post('/assessment/generate', {
      course_id: courseId,
      topic,
      difficulty,
      question_types: questionTypes,
      num_questions: numQuestions,
      user_id: userId,
      target_concept: targetConcept,
      focus_misconception: focusMisconception,
      language,
    });
    return res.data;
  },
  submitAssessment: async (courseId, answers, userId = 'demo_user', language = 'en') => {
    const res = await api.post('/assessment/submit', {
      course_id: courseId,
      answers,
      user_id: userId,
      language,
    });
    return res.data;
  },
  getAdaptiveNextStep: async (courseId, currentTopic = null, currentConcept = null, lastQuestionId = null, lastWasCorrect = null, userId = 'demo_user') => {
    const res = await api.post('/assessment/adaptive-next', {
      course_id: courseId,
      user_id: userId,
      current_topic: currentTopic,
      current_concept: currentConcept,
      last_question_id: lastQuestionId,
      last_was_correct: lastWasCorrect,
    });
    return res.data;
  },
  getMisconceptions: async (courseId, userId = 'demo_user') => {
    const res = await api.get(`/assessment/misconceptions/${courseId}?user_id=${userId}`);
    return res.data;
  },
  clarifyReasoning: async (courseId, questionId, conceptName, clarifyingAnswer, userId = 'demo_user') => {
    const res = await api.post('/assessment/clarify-reasoning', {
      course_id: courseId,
      user_id: userId,
      question_id: questionId,
      concept_name: conceptName,
      clarifying_answer: clarifyingAnswer,
    });
    return res.data;
  },
  getAssessmentHistory: async (courseId, userId = 'demo_user') => {
    const res = await api.get(`/assessment/history/${courseId}?user_id=${userId}`);
    return res.data;
  },
  // --- Innovation 5: Personalized Learning Paths & Visual Explanations ---
  getPersonalizedLearningPath: async (courseId, targetConcept = null, userId = 'demo_user', language = 'en') => {
    const res = await api.post('/learning-path/personalized', {
      course_id: courseId,
      target_concept: targetConcept,
      user_id: userId,
      language,
    });
    return res.data;
  },
  updateConceptProgress: async (courseId, conceptId, conceptName, status = 'studied', userId = 'demo_user', notes = null) => {
    const res = await api.post('/learning-path/progress', {
      course_id: courseId,
      concept_id: conceptId,
      concept_name: conceptName,
      status,
      user_id: userId,
      notes,
    });
    return res.data;
  },
  getConceptProgress: async (courseId, userId = 'demo_user') => {
    const res = await api.get(`/learning-path/progress/${courseId}?user_id=${userId}`);
    return res.data;
  },
  explainNodeStep: async (courseId, topic, nodeLabel, contextExcerpt = null, language = 'en') => {
    const res = await api.post('/learning-path/node-explain', {
      course_id: courseId,
      topic,
      node_label: nodeLabel,
      context_excerpt: contextExcerpt,
      language,
    });
    return res.data;
  },
  // --- Innovation 6: Adaptive Explanation & Visual Learning API ---
  getAdaptiveExplanation: async (courseId, topic, requestedLevel = 'auto', preferredVisualFormat = 'auto', userId = 'demo_user', language = 'en') => {
    const res = await api.post('/adaptive-explain', {
      textbook_id: courseId,
      topic_or_concept: topic,
      requested_level: requestedLevel,
      preferred_visual_format: preferredVisualFormat,
      user_id: userId,
      language,
    });
    return res.data;
  },
  getDiagnosticQuestion: async (courseId, concept, userId = 'demo_user', language = 'en') => {
    const res = await api.post('/adaptive-explain/diagnostic', {
      textbook_id: courseId,
      concept,
      user_id: userId,
      language,
    });
    return res.data;
  },
  submitDiagnosticSession: async (courseId, conceptName, answers, userId = 'demo_user', language = 'en') => {
    const res = await api.post('/adaptive-explain/diagnostic/submit', {
      course_id: courseId,
      concept_name: conceptName,
      answers,
      user_id: userId,
      language,
    });
    return res.data;
  },
  submitAdaptivePractice: async (courseId, conceptName, questionId, questionType, studentAnswer, currentLevel = 'beginner', userId = 'demo_user', language = 'en') => {
    const res = await api.post('/adaptive-explain/submit-practice', {
      course_id: courseId,
      concept_name: conceptName,
      question_id: questionId,
      question_type: questionType,
      student_answer: studentAnswer,
      current_level: currentLevel,
      user_id: userId,
      language,
    });
    return res.data;
  },
  getConceptMasteryStatus: async (courseId, conceptName, userId = 'demo_user') => {
    const res = await api.get(`/adaptive-explain/concept-status/${courseId}/${encodeURIComponent(conceptName)}?user_id=${userId}`);
    return res.data;
  },
  // --- Multimodal Adaptive Learning Path API ---
  getCourseResources: async (courseId) => {
    const res = await api.get(`/learning-path/resources/${courseId}`);
    return res.data;
  },
  verifyLearningPathStep: async ({
    courseId,
    conceptName,
    questionId,
    studentAnswer,
    targetConcept = null,
    stepId = null,
    questionType = 'mcq',
    questionText = '',
    correctAnswer = '',
    options = [],
    userId = 'demo_user',
    language = 'en'
  }) => {
    const res = await api.post('/learning-path/verify-step', {
      course_id: courseId,
      concept_name: conceptName,
      question_id: questionId,
      student_answer: studentAnswer,
      target_concept: targetConcept,
      step_id: stepId,
      question_type: questionType,
      question_text: questionText,
      correct_answer: correctAnswer,
      options,
      user_id: userId,
      language,
    });
    return res.data;
  },
};



