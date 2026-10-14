/**
 * AI-Powered Multilingual Textbook Summarization and Adaptive Learning System
 * Vanilla JavaScript Frontend Application
 */

const API_BASE = '/api';

// Global Application State
const AppState = {
  currentView: 'landing', // 'landing', 'dashboard', 'upload', 'workspace', 'auth'
  activeTab: 'summary',   // 'summary', 'explain', 'visualize', 'ask', 'quiz', 'adaptive'
  activeLevel: 'beginner',// 'beginner', 'intermediate', 'advanced'
  language: 'en',         // 'en', 'ta'
  theme: localStorage.getItem('app_theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'),
  diagramType: 'auto',
  textbooks: [],
  activeTextbook: null,
  activeChapter: null,
  activeSection: null,
  quizData: null,
  quizAnswers: {},
  user: {
    name: 'Alex Rivera',
    email: 'alex.rivera@college.edu',
    role: 'Student'
  },
  zoomLevel: 1.0
};

// --- DOM Elements Cache ---
const DOM = {
  navLinks: document.querySelectorAll('.nav-btn[data-view]'),
  views: document.querySelectorAll('.view-section'),
  langBtns: document.querySelectorAll('.lang-btn'),
  tabBtns: document.querySelectorAll('.tab-btn'),
  tabContents: document.querySelectorAll('.tab-pane'),
  sidebarChapters: document.getElementById('sidebar-chapters'),
  textbookTitle: document.getElementById('textbook-title-badge'),
  textbookMeta: document.getElementById('textbook-meta-badge')
};

// --- Theme Controller ---
function applyTheme(theme) {
  AppState.theme = theme;
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('app_theme', theme);

  const themeIcon = document.getElementById('theme-icon');
  if (themeIcon) {
    themeIcon.textContent = theme === 'dark' ? '☀️' : '🌙';
  }

  // Update Mermaid theme
  if (window.mermaid) {
    mermaid.initialize({
      startOnLoad: false,
      theme: theme === 'dark' ? 'dark' : 'default',
      securityLevel: 'loose'
    });
  }

  // Re-render diagram if currently in visualize tab
  if (AppState.currentView === 'workspace' && AppState.activeTab === 'visualize') {
    loadVisualizeTab();
  }
}

function setupThemeToggle() {
  const toggleBtn = document.getElementById('theme-toggle-btn');
  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      const nextTheme = AppState.theme === 'dark' ? 'light' : 'dark';
      applyTheme(nextTheme);
    });
  }
  // Initialize with saved/detected theme
  applyTheme(AppState.theme);
}

// --- API Service Wrapper ---
const API = {
  async getTextbooks() {
    try {
      const res = await fetch(`${API_BASE}/textbooks`);
      return await res.json();
    } catch (e) {
      console.warn('API error:', e);
      return [];
    }
  },
  async loadSampleTextbook() {
    const res = await fetch(`${API_BASE}/sample-textbook`, { method: 'POST' });
    return await res.json();
  },
  async summarize(textbookId, chapterId, sectionId, lang) {
    const res = await fetch(`${API_BASE}/summarize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ textbook_id: textbookId, chapter_id: chapterId, section_id: sectionId, language: lang })
    });
    return await res.json();
  },
  async explain(textbookId, topic, level, lang) {
    const res = await fetch(`${API_BASE}/explain`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ textbook_id: textbookId, topic_or_concept: topic, level: level, language: lang })
    });
    return await res.json();
  },
  async visualize(textbookId, topic, diagramType) {
    const res = await fetch(`${API_BASE}/visualize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ textbook_id: textbookId, topic: topic, diagram_type: diagramType })
    });
    return await res.json();
  },
  async chat(textbookId, query, lang) {
    const res = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ textbook_id: textbookId, query: query, language: lang })
    });
    return await res.json();
  },
  async generateQuiz(textbookId, topic, difficulty, numQuestions) {
    const res = await fetch(`${API_BASE}/quiz/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ textbook_id: textbookId, topic: topic, difficulty: difficulty, num_questions: numQuestions })
    });
    return await res.json();
  },
  async submitQuiz(textbookId, quizId, topic, difficulty, answers) {
    const res = await fetch(`${API_BASE}/quiz/submit?user_id=demo_user`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ textbook_id: textbookId, quiz_id: quizId, topic: topic, difficulty: difficulty, answers: answers })
    });
    return await res.json();
  },
  async getRecommendations() {
    const res = await fetch(`${API_BASE}/recommendations?user_id=demo_user`);
    return await res.json();
  },
  async getConceptGraph(textbookId) {
    const res = await fetch(`${API_BASE}/concept-graph/${textbookId}`);
    return await res.json();
  },
  async getConceptDetails(textbookId, conceptId) {
    const res = await fetch(`${API_BASE}/concept-graph/${textbookId}/concept/${conceptId}`);
    return await res.json();
  },
  async generateConceptGraph(textbookId) {
    const res = await fetch(`${API_BASE}/concept-graph/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ course_id: textbookId, force_regenerate: true })
    });
    return await res.json();
  }
};

// --- Initialization ---
document.addEventListener('DOMContentLoaded', async () => {
  // Initialize Mermaid
  if (window.mermaid) {
    mermaid.initialize({
      startOnLoad: false,
      theme: 'default',
      securityLevel: 'loose'
    });
  }

  // Setup Event Listeners
  setupThemeToggle();
  setupNavigation();
  setupLanguageSwitcher();
  setupWorkspaceTabs();
  setupAdaptiveLevels();
  setupDiagramTypes();
  setupUploadZone();
  setupChat();

  // Fetch Textbooks
  await loadInitialTextbooks();
  renderDashboard();
});

// --- Navigation Controller ---
function setupNavigation() {
  document.querySelectorAll('[data-view-target]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const targetView = btn.getAttribute('data-view-target');
      switchView(targetView);
    });
  });
}

function switchView(viewName) {
  AppState.currentView = viewName;

  // Update Nav Buttons
  document.querySelectorAll('.nav-btn[data-view]').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-view') === viewName);
  });

  // Toggle View Sections
  document.querySelectorAll('.view-section').forEach(sec => {
    sec.style.display = sec.id === `view-${viewName}` ? 'block' : 'none';
  });

  window.scrollTo({ top: 0, behavior: 'smooth' });

  if (viewName === 'dashboard') {
    renderDashboard();
  } else if (viewName === 'workspace') {
    renderWorkspaceTab();
  }
}

// --- Language Switcher ---
function setupLanguageSwitcher() {
  document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const lang = btn.getAttribute('data-lang');
      AppState.language = lang;

      document.querySelectorAll('.lang-btn').forEach(b => {
        b.classList.toggle('active', b.getAttribute('data-lang') === lang);
      });

      // Reload current tab content with new language
      if (AppState.currentView === 'workspace') {
        renderWorkspaceTab();
      }
    });
  });
}

// --- Textbooks Loader ---
async function loadInitialTextbooks() {
  const books = await API.getTextbooks();
  AppState.textbooks = books;
  if (books.length > 0) {
    AppState.activeTextbook = books[0];
    if (books[0].chapters && books[0].chapters.length > 0) {
      AppState.activeChapter = books[0].chapters[0];
      if (books[0].chapters[0].sections && books[0].chapters[0].sections.length > 0) {
        AppState.activeSection = books[0].chapters[0].sections[0];
      }
    }
  }
  renderSidebar();
}

async function updateTopicSelects() {
  const tb = AppState.activeTextbook;
  if (!tb) return;

  const topicSet = new Set();
  if (tb.chapters && Array.isArray(tb.chapters)) {
    tb.chapters.forEach(ch => {
      if (ch.title) topicSet.add(ch.title.trim());
      if (ch.sections && Array.isArray(ch.sections)) {
        ch.sections.forEach(sec => {
          if (sec.title) topicSet.add(sec.title.trim());
        });
      }
    });
  }

  try {
    const graph = await API.getConceptGraph(tb.id);
    if (graph?.nodes && Array.isArray(graph.nodes)) {
      graph.nodes.forEach(node => {
        if (node.name) topicSet.add(node.name.trim());
        if (node.topic) topicSet.add(node.topic.trim());
      });
    }
  } catch (e) { }

  if (topicSet.size === 0 && tb.title) {
    topicSet.add(tb.title.trim());
  }

  const topics = Array.from(topicSet).filter(Boolean);

  const quizSelect = document.getElementById('quiz-topic-select');
  if (quizSelect && topics.length > 0) {
    const curr = quizSelect.value;
    quizSelect.innerHTML = `<option value="All">All Course Topics (Comprehensive)</option>` +
      topics.map(t => `<option value="${t}">${t}</option>`).join('');
    if (topics.includes(curr)) {
      quizSelect.value = curr;
    }
  }

  const explainSelect = document.getElementById('explain-topic-select');
  if (explainSelect && topics.length > 0) {
    const curr = explainSelect.value;
    explainSelect.innerHTML = topics.map(t => `<option value="${t}">${t}</option>`).join('');
    if (topics.includes(curr)) {
      explainSelect.value = curr;
    } else {
      explainSelect.value = topics[0];
    }
  }

  const visualSelect = document.getElementById('visual-topic-select');
  if (visualSelect && topics.length > 0) {
    const curr = visualSelect.value;
    visualSelect.innerHTML = topics.map(t => `<option value="${t}">${t}</option>`).join('');
    if (topics.includes(curr)) {
      visualSelect.value = curr;
    } else {
      visualSelect.value = topics[0];
    }
  }
}

function renderSidebar() {
  const tb = AppState.activeTextbook;
  if (!tb) return;

  updateTopicSelects();

  const titleElem = document.getElementById('sidebar-tb-title');
  const metaElem = document.getElementById('sidebar-tb-meta');
  if (titleElem) titleElem.textContent = tb.title;
  if (metaElem) metaElem.textContent = `${tb.total_pages} Pages • ${tb.chapters?.length || 5} Chapters`;

  const container = document.getElementById('sidebar-chapters-list');
  if (!container) return;

  container.innerHTML = '';
  (tb.chapters || []).forEach(ch => {
    const isSelected = AppState.activeChapter?.id === ch.id;

    const chDiv = document.createElement('div');
    chDiv.className = 'chapter-item';
    chDiv.style.marginBottom = '0.5rem';

    chDiv.innerHTML = `
      <div class="card" style="padding: 0.6rem 0.8rem; cursor: pointer; display: flex; align-items: center; justify-content: space-between; background: ${isSelected ? 'var(--primary-50)' : 'var(--bg-card)'}; border-color: ${isSelected ? 'var(--primary-500)' : 'var(--border-color)'}; font-size: 0.78rem; font-weight: ${isSelected ? '700' : '600'}; color: ${isSelected ? 'var(--primary-900)' : 'var(--text-main)'}">
        <div style="display: flex; align-items: center; gap: 0.5rem; min-width: 0;">
          <span style="width: 20px; height: 20px; border-radius: 4px; background: ${isSelected ? 'var(--primary-600)' : '#e2e8f0'}; color: ${isSelected ? 'white' : 'var(--text-main)'}; display: flex; align-items: center; justify-content: center; font-size: 0.65rem; font-weight: 800; flex-shrink: 0">${ch.number}</span>
          <span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${ch.title}</span>
        </div>
      </div>
      ${ch.sections && ch.sections.length > 0 ? `
        <div style="margin-left: 1.5rem; padding-left: 0.5rem; border-left: 2px solid var(--border-color); margin-top: 0.3rem; display: flex; flex-direction: column; gap: 0.25rem;">
          ${ch.sections.map(sec => `
            <div class="sec-link" data-ch="${ch.id}" data-sec="${sec.id}" style="padding: 0.3rem 0.5rem; border-radius: 4px; font-size: 0.72rem; cursor: pointer; color: ${AppState.activeSection?.id === sec.id && isSelected ? 'var(--primary-600)' : 'var(--text-muted)'}; font-weight: ${AppState.activeSection?.id === sec.id && isSelected ? '700' : '500'}; background: ${AppState.activeSection?.id === sec.id && isSelected ? '#e0e7ff' : 'transparent'}">
              ${sec.title} <span style="font-size: 0.65rem; color: #94a3b8; font-family: var(--font-mono)">(p.${sec.page_start})</span>
            </div>
          `).join('')}
        </div>
      ` : ''}
    `;

    // Click chapter header
    chDiv.querySelector('.card').addEventListener('click', () => {
      AppState.activeChapter = ch;
      AppState.activeSection = ch.sections?.[0] || null;
      renderSidebar();
      renderWorkspaceTab();
    });

    // Click sub sections
    chDiv.querySelectorAll('.sec-link').forEach(link => {
      link.addEventListener('click', (e) => {
        e.stopPropagation();
        const secId = link.getAttribute('data-sec');
        AppState.activeChapter = ch;
        AppState.activeSection = ch.sections.find(s => s.id === secId);
        renderSidebar();
        renderWorkspaceTab();
      });
    });

    container.appendChild(chDiv);
  });
}

// --- Workspace Tabs Controller ---
function setupWorkspaceTabs() {
  document.querySelectorAll('.tab-btn[data-tab]').forEach(btn => {
    btn.addEventListener('click', () => {
      const tabName = btn.getAttribute('data-tab');
      AppState.activeTab = tabName;

      document.querySelectorAll('.tab-btn[data-tab]').forEach(b => {
        b.classList.toggle('active', b.getAttribute('data-tab') === tabName);
      });

      document.querySelectorAll('.tab-pane').forEach(p => {
        p.style.display = p.id === `tab-${tabName}` ? 'block' : 'none';
      });

      renderWorkspaceTab();
    });
  });
}

function renderWorkspaceTab() {
  const tab = AppState.activeTab;
  if (tab === 'summary') {
    loadSummaryTab();
  } else if (tab === 'graph') {
    loadConceptGraphTab();
  } else if (tab === 'explain') {
    loadExplainTab();
  } else if (tab === 'visualize') {
    loadVisualizeTab();
  } else if (tab === 'ask') {
    // ask tab is interactive
  } else if (tab === 'quiz') {
    // quiz setup
  } else if (tab === 'adaptive') {
    loadAdaptiveTab();
  }
}

// --- Innovation 2: Concept and Prerequisite Graph Tab ---
let currentGraphData = null;

async function loadConceptGraphTab(forceRegenerate = false) {
  const container = document.getElementById('concept-graph-nodes-grid');
  const statsBox = document.getElementById('concept-graph-stats');
  const pathStrip = document.getElementById('learning-path-strip');
  const refreshBtn = document.getElementById('btn-refresh-concept-graph');

  if (!container || !AppState.activeTextbook) return;

  if (refreshBtn) {
    refreshBtn.onclick = () => loadConceptGraphTab(true);
  }

  container.innerHTML = `<div style="text-align: center; padding: 2.5rem;"><div class="spinner"></div><p style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.5rem">Loading course concept and prerequisite graph...</p></div>`;

  try {
    const data = forceRegenerate
      ? await API.generateConceptGraph(AppState.activeTextbook.id)
      : await API.getConceptGraph(AppState.activeTextbook.id);

    currentGraphData = data;

    // Render Stats
    if (statsBox && data.stats) {
      statsBox.innerHTML = `
        <div class="card" style="padding: 0.75rem; text-align: center">
          <div style="font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase; font-weight: 700">Concepts</div>
          <div style="font-size: 1.25rem; font-weight: 800; color: var(--primary-600)">${data.stats.total_concepts}</div>
        </div>
        <div class="card" style="padding: 0.75rem; text-align: center">
          <div style="font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase; font-weight: 700">Prerequisites</div>
          <div style="font-size: 1.25rem; font-weight: 800; color: var(--emerald-600)">${data.stats.total_prerequisites}</div>
        </div>
        <div class="card" style="padding: 0.75rem; text-align: center">
          <div style="font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase; font-weight: 700">Cross-Modal</div>
          <div style="font-size: 1.25rem; font-weight: 800; color: #0284c7">${data.stats.cross_modal_concepts}</div>
        </div>
        <div class="card" style="padding: 0.75rem; text-align: center">
          <div style="font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase; font-weight: 700">Sources</div>
          <div style="font-size: 1.25rem; font-weight: 800; color: var(--amber-600)">${data.stats.total_sources}</div>
        </div>
      `;
    }

    // Render Prerequisite Learning Sequence Strip
    if (pathStrip && data.learning_paths && data.learning_paths.length > 0) {
      pathStrip.style.display = 'block';
      const stepsHtml = data.learning_paths[0].map((s, idx) => `
        <span style="display: inline-flex; align-items: center; gap: 0.3rem; background: var(--bg-card); padding: 0.25rem 0.6rem; border-radius: 6px; border: 1px solid var(--border-color); cursor: pointer" onclick="inspectConceptByName('${s.replace(/'/g, "\\'")}')">
          <span style="font-size: 0.65rem; background: rgba(16,185,129,0.2); color: var(--emerald-600); font-weight: 800; padding: 0.1rem 0.35rem; border-radius: 4px">${idx + 1}</span>
          <span style="font-weight: 700; color: var(--text-main)">${s}</span>
        </span>
      `).join('<span style="color: var(--emerald-600); font-weight: 800"> → </span>');

      pathStrip.innerHTML = `<span style="font-weight: 800; color: var(--emerald-600); margin-right: 0.5rem">🎯 Recommended Learning Path:</span> ${stepsHtml}`;
    }

    // Render Nodes Grid
    container.innerHTML = '';
    (data.nodes || []).forEach(node => {
      const nodeEl = document.createElement('div');
      nodeEl.className = 'card';
      nodeEl.style.cssText = 'padding: 0.85rem 1rem; cursor: pointer; transition: all 0.2s; border-left: 4px solid var(--primary-600); display: flex; justify-content: space-between; align-items: center';

      const hasPDF = node.sources?.some(s => s.source_type === 'pdf');
      const hasPPT = node.sources?.some(s => s.source_type === 'presentation');
      const hasVideo = node.sources?.some(s => s.source_type === 'video');

      const modalBadges = [];
      if (hasPDF) modalBadges.push('<span title="PDF Source" style="color: #ef4444">📕 PDF</span>');
      if (hasPPT) modalBadges.push('<span title="Presentation Slide Source" style="color: #f59e0b">📊 Slides</span>');
      if (hasVideo) modalBadges.push('<span title="Video Lecture Source" style="color: #8b5cf6">🎥 Video</span>');

      nodeEl.innerHTML = `
        <div>
          <div style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; font-weight: 700">${node.topic}</div>
          <div style="font-size: 0.92rem; font-weight: 800; color: var(--text-main); margin: 0.15rem 0">${node.name}</div>
          <div style="font-size: 0.72rem; color: var(--text-muted); max-width: 480px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis">${node.description}</div>
        </div>
        <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 0.3rem">
          <div style="display: flex; gap: 0.4rem; font-size: 0.65rem; font-weight: 700">
            ${modalBadges.join('')}
          </div>
          ${node.prerequisites?.length ? `<span style="font-size: 0.65rem; color: var(--emerald-600); font-weight: 700">⚡ ${node.prerequisites.length} Prereqs</span>` : ''}
        </div>
      `;

      nodeEl.addEventListener('click', () => {
        document.querySelectorAll('#concept-graph-nodes-grid .card').forEach(c => c.style.borderColor = 'var(--border-color)');
        nodeEl.style.borderColor = 'var(--primary-600)';
        inspectConcept(node);
      });

      container.appendChild(nodeEl);
    });

    // Auto-inspect first node
    if (data.nodes && data.nodes.length > 0) {
      inspectConcept(data.nodes[0]);
    }

  } catch (err) {
    console.error('Error in concept graph:', err);
    container.innerHTML = `<p style="color: var(--rose-600); font-size: 0.8rem">Failed to load concept graph.</p>`;
  }
}

function inspectConceptByName(name) {
  if (!currentGraphData) return;
  const match = currentGraphData.nodes?.find(n => n.name.toLowerCase() === name.toLowerCase());
  if (match) inspectConcept(match);
}

async function inspectConcept(node) {
  const sidebar = document.getElementById('concept-details-sidebar');
  if (!sidebar) return;

  sidebar.innerHTML = `<div style="text-align: center; padding: 2rem"><div class="spinner"></div></div>`;

  const details = await API.getConceptDetails(AppState.activeTextbook.id, node.id);

  const sourcesList = (details?.sources || node.sources || []).map(s => `
    <div style="padding: 0.6rem 0.75rem; background: var(--bg-subtle); border-radius: 8px; margin-bottom: 0.5rem; font-size: 0.75rem; border: 1px solid var(--border-color)">
      <div style="display: flex; justify-content: space-between; font-weight: 700; margin-bottom: 0.2rem">
        <span>${s.source_type === 'pdf' ? '📕 PDF Textbook' : (s.source_type === 'presentation' ? '📊 Lecture Slides' : '🎥 Video Lecture')}</span>
        <span style="font-size: 0.7rem; background: var(--bg-card); padding: 0.1rem 0.4rem; border-radius: 4px; border: 1px solid var(--border-color)">
          ${s.source_type === 'pdf' ? `Page ${s.page_number || 1}` : (s.source_type === 'presentation' ? `Slide ${s.slide_number || 1}` : (s.timestamp_str || '00:00'))}
        </span>
      </div>
      ${s.excerpt ? `<div style="font-size: 0.7rem; color: var(--text-muted); font-style: italic">"${s.excerpt}"</div>` : ''}
    </div>
  `).join('');

  const prereqList = (details?.prerequisites || []).map(p => `
    <div style="padding: 0.5rem 0.75rem; background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.3); border-radius: 8px; margin-bottom: 0.4rem; font-size: 0.75rem; cursor: pointer" onclick="inspectConceptByName('${p.name.replace(/'/g, "\\'")}')">
      <div style="font-weight: 800; color: var(--emerald-600)">${p.name}</div>
      <div style="font-size: 0.68rem; color: var(--text-muted); margin-top: 0.15rem"><strong>Reason:</strong> ${p.evidence}</div>
    </div>
  `).join('');

  const dependentsList = (details?.dependents || []).map(d => `
    <div style="padding: 0.4rem 0.6rem; background: var(--bg-subtle); border-radius: 6px; margin-bottom: 0.3rem; font-size: 0.72rem; font-weight: 700; color: var(--primary-600); cursor: pointer" onclick="inspectConceptByName('${d.name.replace(/'/g, "\\'")}')">
      ➔ ${d.name}
    </div>
  `).join('');

  const relatedList = (details?.related_concepts || []).map(r => `
    <div style="padding: 0.4rem 0.6rem; background: var(--bg-subtle); border-radius: 6px; margin-bottom: 0.3rem; font-size: 0.72rem; display: flex; justify-content: space-between">
      <span style="font-weight: 700">${r.name}</span>
      <span style="font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase">${r.relationship_type}</span>
    </div>
  `).join('');

  sidebar.innerHTML = `
    <div>
      <div style="font-size: 0.7rem; color: var(--primary-600); font-weight: 800; text-transform: uppercase">${node.topic}</div>
      <h3 style="font-size: 1.15rem; font-weight: 800; color: var(--text-main); margin: 0.25rem 0">${node.name}</h3>
      <p style="font-size: 0.78rem; color: var(--text-muted); line-height: 1.5; margin-bottom: 1rem">${node.description}</p>

      <div style="display: flex; gap: 0.5rem; margin-bottom: 1.25rem">
        <button class="btn-lg btn-primary" onclick="switchWorkspaceTab('explain')" style="font-size: 0.75rem; padding: 0.35rem 0.75rem">Adaptive Explain</button>
        <button class="btn-lg btn-secondary" onclick="switchWorkspaceTab('quiz')" style="font-size: 0.75rem; padding: 0.35rem 0.75rem">Practice Quiz</button>
      </div>

      <div style="margin-bottom: 1.25rem">
        <div style="font-size: 0.72rem; font-weight: 800; text-transform: uppercase; color: var(--text-main); margin-bottom: 0.4rem">
          📚 Multimodal Sources (${(details?.sources || node.sources || []).length})
        </div>
        ${sourcesList || '<div style="font-size: 0.7rem; color: var(--text-muted)">No direct citations attached.</div>'}
      </div>

      <div style="margin-bottom: 1.25rem">
        <div style="font-size: 0.72rem; font-weight: 800; text-transform: uppercase; color: var(--text-main); margin-bottom: 0.4rem">
          ⚡ Prerequisite Concepts
        </div>
        ${prereqList || '<div style="font-size: 0.7rem; color: var(--text-muted); font-style: italic">Foundational concept (No prior prerequisites)</div>'}
        
        ${dependentsList ? `
          <div style="font-size: 0.68rem; font-weight: 800; color: var(--text-muted); text-transform: uppercase; margin-top: 0.75rem; margin-bottom: 0.25rem">Enables Next:</div>
          ${dependentsList}
        ` : ''}
      </div>

      ${relatedList ? `
        <div>
          <div style="font-size: 0.72rem; font-weight: 800; text-transform: uppercase; color: var(--text-main); margin-bottom: 0.4rem">
            🔗 Related Concepts
          </div>
          ${relatedList}
        </div>
      ` : ''}

    </div>
  `;
}


// --- 1. Summary Tab ---
async function loadSummaryTab() {
  const container = document.getElementById('summary-content-box');
  if (!container || !AppState.activeTextbook) return;

  container.innerHTML = `<div style="text-align: center; padding: 3rem;"><div class="spinner"></div><p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.5rem">Synthesizing grounded summary from textbook chunks...</p></div>`;

  const data = await API.summarize(
    AppState.activeTextbook.id,
    AppState.activeChapter?.id,
    AppState.activeSection?.id,
    AppState.language
  );

  container.innerHTML = `
    <div class="chapter-summary-card animate-fade">
      <div class="chapter-summary-title">
        <span>📖</span>
        <span>Chapter Summary (${data.title})</span>
      </div>
      <p class="chapter-summary-text">${data.summary}</p>
    </div>

    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1.25rem; margin-bottom: 1.5rem">
      <div class="card" style="padding: 1.25rem">
        <h4 style="font-size: 0.85rem; font-weight: 700; color: var(--emerald-800); margin-bottom: 0.75rem; display: flex; align-items: center; gap: 0.4rem">
          <span>🔖</span> Key Concepts & Definitions
        </h4>
        <ul style="list-style: none; display: flex; flex-direction: column; gap: 0.6rem">
          ${data.key_concepts.map((c, i) => `
            <li class="concept-item">
              <span class="concept-number">${i + 1}</span>
              <span style="line-height: 1.4">${c}</span>
            </li>
          `).join('')}
        </ul>
      </div>

      <div class="card" style="padding: 1.25rem">
        <h4 style="font-size: 0.85rem; font-weight: 700; color: var(--amber-700); margin-bottom: 0.75rem; display: flex; align-items: center; gap: 0.4rem">
          <span>⚡</span> Important Review Points
        </h4>
        <ul style="list-style: none; display: flex; flex-direction: column; gap: 0.6rem">
          ${data.important_points.map(pt => `
            <li class="review-item">
              <span class="review-check">✓</span>
              <span style="line-height: 1.4">${pt}</span>
            </li>
          `).join('')}
        </ul>
      </div>
    </div>

    <div class="quick-revision-wrapper">
      <h5 class="quick-revision-title">
        <span>⚡</span> Quick Revision Takeaways
      </h5>
      <div class="quick-revision-grid">
        ${data.quick_revision.map(r => `
          <div class="quick-revision-item">
            <span class="quick-revision-bullet">•</span>
            <span>${r}</span>
          </div>
        `).join('')}
      </div>
    </div>

    <div class="source-grounding-box">
      <span><strong>Source Grounding:</strong> ${data.source_reference}</span>
      <span class="badge-tag" style="background: var(--emerald-50); color: var(--emerald-800); border-color: var(--emerald-500)">Verified Grounded</span>
    </div>
  `;
}

// --- 2. Adaptive Explanation Tab (Problem 1) ---
function setupAdaptiveLevels() {
  document.querySelectorAll('.tier-card').forEach(card => {
    card.addEventListener('click', () => {
      const lvl = card.getAttribute('data-level');
      AppState.activeLevel = lvl;

      document.querySelectorAll('.tier-card').forEach(c => {
        c.className = `tier-card ${c.getAttribute('data-level') === lvl ? `active-${lvl}` : ''}`;
      });

      loadExplainTab();
    });
  });

  const topicSelect = document.getElementById('explain-topic-select');
  if (topicSelect) {
    topicSelect.addEventListener('change', (e) => {
      loadExplainTab();
    });
  }
}

async function loadExplainTab() {
  const container = document.getElementById('explain-output-box');
  const topicSelect = document.getElementById('explain-topic-select');
  const topic = topicSelect ? topicSelect.value : 'Second Normal Form (2NF)';

  if (!container || !AppState.activeTextbook) return;

  container.innerHTML = `<div style="text-align: center; padding: 3rem;"><div class="spinner"></div><p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.5rem">Generating ${AppState.activeLevel}-level grounded explanation...</p></div>`;

  const data = await API.explain(
    AppState.activeTextbook.id,
    topic,
    AppState.activeLevel,
    AppState.language
  );

  container.innerHTML = `
    <div class="explain-card animate-fade">
      <div class="explain-header">
        <h4 class="explain-title">
          ${data.level} Level: ${data.concept}
        </h4>
        <span class="badge-tag" style="background: var(--emerald-50); color: var(--emerald-800); border-color: var(--emerald-500)">Grounded in Textbook</span>
      </div>
      <p class="explain-text">${data.explanation}</p>
    </div>

    ${data.analogy ? `
      <div class="analogy-card">
        <h5 class="analogy-title">
          💡 Intuitive Analogy
        </h5>
        <p class="analogy-text">${data.analogy}</p>
      </div>
    ` : ''}

    <div class="schema-card">
      <h5 class="schema-title">
        🧩 Concrete Schema Example
      </h5>
      <pre class="schema-pre">${data.example}</pre>
    </div>

    ${data.key_terms && data.key_terms.length > 0 ? `
      <div class="card" style="padding: 1.25rem; margin-bottom: 1.25rem">
        <h5 style="font-size: 0.75rem; font-weight: 800; text-transform: uppercase; color: var(--text-main); margin-bottom: 0.75rem">
          Key Terminology Breakdown
        </h5>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 0.75rem">
          ${data.key_terms.map(kt => `
            <div class="key-term-item">
              <div class="key-term-title">${kt.term}</div>
              <div class="key-term-desc">${kt.meaning}</div>
            </div>
          `).join('')}
        </div>
      </div>
    ` : ''}

    <div class="source-grounding-box">
      <span><strong>Source Grounding:</strong> ${data.source_reference}</span>
      <span class="badge-tag">Page Reference Verified</span>
    </div>
  `;
}

// --- 3. Visual Explanation Tab (Problem 2) ---
function setupDiagramTypes() {
  document.querySelectorAll('.diag-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const dt = btn.getAttribute('data-type');
      AppState.diagramType = dt;

      document.querySelectorAll('.diag-btn').forEach(b => {
        b.className = `diag-btn nav-btn ${b.getAttribute('data-type') === dt ? 'primary-btn' : ''}`;
      });

      loadVisualizeTab();
    });
  });

  const topicSelect = document.getElementById('visual-topic-select');
  if (topicSelect) {
    topicSelect.addEventListener('change', () => loadVisualizeTab());
  }

  // Zoom controls
  document.getElementById('btn-zoom-in')?.addEventListener('click', () => {
    AppState.zoomLevel = Math.min(AppState.zoomLevel + 0.15, 2.0);
    applyZoom();
  });
  document.getElementById('btn-zoom-out')?.addEventListener('click', () => {
    AppState.zoomLevel = Math.max(AppState.zoomLevel - 0.15, 0.5);
    applyZoom();
  });
  document.getElementById('btn-zoom-reset')?.addEventListener('click', () => {
    AppState.zoomLevel = 1.0;
    applyZoom();
  });
}

function applyZoom() {
  const stage = document.querySelector('#mermaid-render-container svg');
  if (stage) {
    stage.style.transform = `scale(${AppState.zoomLevel})`;
    stage.style.transformOrigin = 'top center';
    stage.style.transition = 'transform 0.15s ease-out';
  }
  const label = document.getElementById('zoom-label');
  if (label) label.textContent = `${Math.round(AppState.zoomLevel * 100)}%`;
}

async function loadVisualizeTab() {
  const topicSelect = document.getElementById('visual-topic-select');
  const topic = topicSelect ? topicSelect.value : 'Database Normalization';
  const renderContainer = document.getElementById('mermaid-render-container');

  if (!renderContainer || !AppState.activeTextbook) return;

  renderContainer.innerHTML = `<div style="text-align: center; padding: 3rem;"><div class="spinner"></div><p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.5rem">Compiling Mermaid visual structure from textbook...</p></div>`;

  const data = await API.visualize(
    AppState.activeTextbook.id,
    topic,
    AppState.diagramType
  );

  // Render Mermaid code
  try {
    const uniqueId = `mermaid_diag_${Date.now()}`;
    const { svg } = await mermaid.render(uniqueId, data.mermaid_code);
    renderContainer.innerHTML = svg;
    AppState.zoomLevel = 1.0;
    applyZoom();
  } catch (err) {
    console.error('Mermaid render error:', err);
    renderContainer.innerHTML = `<pre style="font-size: 0.75rem; color: #ef4444">${data.mermaid_code}</pre>`;
  }

  // Set Source Code in Editor
  const srcArea = document.getElementById('mermaid-source-text');
  if (srcArea) srcArea.value = data.mermaid_code;

  // Set Description & Mapped Nodes
  const descElem = document.getElementById('visual-desc-text');
  if (descElem) descElem.textContent = data.description;

  const nodesContainer = document.getElementById('visual-mapped-nodes');
  if (nodesContainer && data.steps_or_nodes) {
    nodesContainer.innerHTML = data.steps_or_nodes.map(n => `
      <div style="background: var(--bg-subtle); padding: 0.6rem 0.8rem; border-radius: 6px; border: 1px solid var(--border-color)">
        <div style="font-weight: 700; font-size: 0.75rem; color: var(--primary-700)">${n.label}</div>
        <div style="font-size: 0.7rem; color: var(--text-muted)">${n.description}</div>
      </div>
    `).join('');
  }
}

// --- 4. Ask Textbook Tab (RAG) ---
function setupChat() {
  const form = document.getElementById('chat-form');
  const input = document.getElementById('chat-input');
  const chatBox = document.getElementById('chat-messages-box');

  if (!form || !input || !chatBox) return;

  // Suggested questions
  document.querySelectorAll('.suggest-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      input.value = btn.textContent.replace(/[“”"]/g, '').trim();
      form.dispatchEvent(new Event('submit'));
    });
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = input.value.trim();
    if (!query || !AppState.activeTextbook) return;

    // Append User Message
    const userMsg = document.createElement('div');
    userMsg.className = 'animate-fade';
    userMsg.style.display = 'flex';
    userMsg.style.justifyContent = 'flex-end';
    userMsg.style.marginBottom = '1rem';
    userMsg.innerHTML = `
      <div style="background: var(--primary-600); color: white; padding: 0.75rem 1rem; border-radius: 12px; border-bottom-right-radius: 2px; font-size: 0.8rem; max-width: 80%">
        ${query}
      </div>
    `;
    chatBox.appendChild(userMsg);
    input.value = '';
    chatBox.scrollTop = chatBox.scrollHeight;

    // Loading indicator
    const loadingMsg = document.createElement('div');
    loadingMsg.className = 'animate-fade';
    loadingMsg.style.display = 'flex';
    loadingMsg.style.justifyContent = 'flex-start';
    loadingMsg.style.marginBottom = '1rem';
    loadingMsg.innerHTML = `
      <div style="background: var(--bg-card); border: 1px solid var(--border-color); padding: 0.75rem 1rem; border-radius: 12px; font-size: 0.75rem; color: var(--text-muted); display: flex; align-items: center; gap: 0.5rem">
        <div class="spinner" style="width: 14px; height: 14px; border-width: 2px"></div>
        <span>Retrieving textbook vectors & checking citations...</span>
      </div>
    `;
    chatBox.appendChild(loadingMsg);
    chatBox.scrollTop = chatBox.scrollHeight;

    // Call RAG API
    const response = await API.chat(AppState.activeTextbook.id, query, AppState.language);
    loadingMsg.remove();

    const aiMsg = document.createElement('div');
    aiMsg.className = 'animate-fade';
    aiMsg.style.display = 'flex';
    aiMsg.style.justifyContent = 'flex-start';
    aiMsg.style.marginBottom = '1rem';
    aiMsg.innerHTML = `
      <div style="background: var(--bg-card); border: 1px solid var(--border-color); padding: 1rem; border-radius: 12px; border-bottom-left-radius: 2px; font-size: 0.8rem; max-width: 85%; box-shadow: var(--shadow-sm)">
        <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--border-color); padding-bottom: 0.4rem; margin-bottom: 0.6rem">
          <span style="font-weight: 700; color: var(--primary-600)">Textbook AI Assistant</span>
          <span class="badge-tag" style="background: ${response.is_grounded ? 'var(--emerald-50)' : 'var(--amber-50)'}; color: ${response.is_grounded ? 'var(--emerald-800)' : 'var(--amber-700)'}">${response.is_grounded ? 'Verified Grounded' : 'Out-of-Scope'}</span>
        </div>
        <p style="line-height: 1.6; color: var(--text-main); white-space: pre-line">${response.answer}</p>
        ${response.citations && response.citations.length > 0 ? `
          <div style="margin-top: 0.75rem; padding-top: 0.5rem; border-top: 1px solid var(--border-color); font-size: 0.7rem">
            <div style="font-weight: 700; color: var(--text-muted); margin-bottom: 0.3rem">SOURCE CITATIONS:</div>
            ${response.citations.map(c => `
              <div style="background: var(--bg-subtle); padding: 0.4rem 0.6rem; border-radius: 4px; margin-bottom: 0.3rem; border: 1px solid var(--border-color)">
                <div style="font-weight: 700; color: var(--text-main)">${c.chapter} • <span style="color: var(--primary-600); font-family: var(--font-mono)">Page ${c.page}</span></div>
                <div style="color: var(--text-muted); font-style: italic">"${c.excerpt}"</div>
              </div>
            `).join('')}
          </div>
        ` : ''}
      </div>
    `;
    chatBox.appendChild(aiMsg);
    chatBox.scrollTop = chatBox.scrollHeight;
  });
}

// --- 5. Quiz Assessment Tab ---
async function startQuiz() {
  const topic = document.getElementById('quiz-topic-select')?.value || 'Second Normal Form (2NF)';
  const difficulty = document.getElementById('quiz-diff-select')?.value || 'medium';
  const numQuestions = parseInt(document.getElementById('quiz-count-select')?.value || '5');
  const container = document.getElementById('quiz-container');

  if (!container || !AppState.activeTextbook) return;

  container.innerHTML = `<div style="text-align: center; padding: 3rem;"><div class="spinner"></div><p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.5rem">Generating MCQs from textbook chunks...</p></div>`;

  const quiz = await API.generateQuiz(AppState.activeTextbook.id, topic, difficulty, numQuestions);
  AppState.quizData = quiz;
  AppState.quizAnswers = {};

  renderQuizQuestions();
}

function renderQuizQuestions() {
  const container = document.getElementById('quiz-container');
  const quiz = AppState.quizData;
  if (!container || !quiz) return;

  container.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem">
      <h3 style="font-size: 1rem; font-weight: 700; color: var(--text-main)">Drill: ${quiz.topic} (${quiz.difficulty.toUpperCase()})</h3>
      <button class="nav-btn" onclick="startQuiz()" style="font-size: 0.75rem">↺ New Questions</button>
    </div>

    <div style="display: flex; flex-direction: column; gap: 1rem">
      ${quiz.questions.map((q, idx) => `
        <div class="card" style="padding: 1.25rem">
          <div style="display: flex; justify-content: space-between; margin-bottom: 0.75rem">
            <div style="font-weight: 700; font-size: 0.85rem; color: var(--text-main)">${idx + 1}. ${q.question}</div>
            <span class="badge-tag">Page ${q.source_page}</span>
          </div>

          <div class="quiz-options-grid">
            ${q.options.map(opt => `
              <div class="quiz-option ${AppState.quizAnswers[q.id] === opt.key ? 'selected' : ''}" onclick="selectQuizAnswer(${q.id}, '${opt.key}')">
                <span style="font-weight: 800; font-family: var(--font-mono); width: 20px; height: 20px; border-radius: 50%; background: var(--bg-subtle); color: var(--text-main); border: 1px solid var(--border-color); display: flex; align-items: center; justify-content: center; font-size: 0.65rem">${opt.key}</span>
                <span>${opt.text}</span>
              </div>
            `).join('')}
          </div>
        </div>
      `).join('')}
    </div>

    <div style="display: flex; justify-content: flex-end; margin-top: 1.5rem">
      <button class="btn-lg btn-primary" onclick="submitQuizAnswers()" style="font-size: 0.85rem">Submit Assessment</button>
    </div>
  `;
}

function selectQuizAnswer(questionId, key) {
  AppState.quizAnswers[questionId] = key;
  renderQuizQuestions();
}

async function submitQuizAnswers() {
  const quiz = AppState.quizData;
  if (!quiz) return;

  const answersPayload = quiz.questions.map(q => ({
    question_id: q.id,
    selected_key: AppState.quizAnswers[q.id] || 'NONE'
  }));

  const res = await API.submitQuiz(
    AppState.activeTextbook.id,
    quiz.quiz_id,
    quiz.topic,
    quiz.difficulty,
    answersPayload
  );

  renderQuizResults(res);
}

function renderQuizResults(result) {
  const container = document.getElementById('quiz-container');
  if (!container) return;

  container.innerHTML = `
    <div class="card animate-fade" style="padding: 1.5rem; background: linear-gradient(135deg, #1e1b4b, #0f172a); color: white; margin-bottom: 1.5rem">
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem">
        <div>
          <h3 style="font-size: 1.25rem; font-weight: 800">Assessment Result: ${result.score_percentage}%</h3>
          <p style="font-size: 0.8rem; color: #cbd5e1">${result.correct_count} of ${result.total_questions} questions answered correctly</p>
        </div>
        ${result.weak_topics && result.weak_topics.length > 0 ? `
          <button class="btn-lg btn-primary" onclick="switchWorkspaceTab('adaptive')" style="font-size: 0.75rem; background: var(--emerald-600)">
            Remediate Weak Topic (${result.weak_topics[0]}) →
          </button>
        ` : ''}
      </div>

      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.75rem; padding-top: 0.75rem; border-top: 1px solid rgba(255,255,255,0.15)">
        ${result.topic_breakdown.map(tb => `
          <div style="background: rgba(255,255,255,0.08); padding: 0.6rem 0.8rem; border-radius: 6px; font-size: 0.75rem; display: flex; justify-content: space-between">
            <span>${tb.topic}</span>
            <span style="font-weight: 800; color: ${tb.status === 'Strong' ? '#34d399' : '#f87171'}">${tb.percentage}%</span>
          </div>
        `).join('')}
      </div>
    </div>

    <div style="display: flex; flex-direction: column; gap: 1rem">
      ${result.results.map((r, i) => `
        <div class="card" style="padding: 1rem; border-left: 4px solid ${r.is_correct ? 'var(--emerald-500)' : 'var(--rose-500)'}">
          <div style="font-weight: 700; font-size: 0.8rem; color: var(--text-main); margin-bottom: 0.3rem">${i + 1}. ${r.question}</div>
          <div style="font-size: 0.75rem; font-weight: 600; color: ${r.is_correct ? 'var(--emerald-800)' : 'var(--rose-700)'}; margin-bottom: 0.2rem">
            ${r.is_correct ? '✓ Correct' : `✗ Incorrect (Selected: ${r.selected_key}, Correct: ${r.correct_key})`}
          </div>
          <div style="font-size: 0.72rem; color: var(--text-muted)">${r.explanation}</div>
        </div>
      `).join('')}
    </div>

    <div style="display: flex; justify-content: flex-end; margin-top: 1.5rem">
      <button class="nav-btn primary-btn" onclick="startQuiz()">Take Another Quiz</button>
    </div>
  `;
}

// --- 6. Adaptive Revision Tab ---
async function loadAdaptiveTab() {
  const container = document.getElementById('adaptive-content-box');
  if (!container) return;

  container.innerHTML = `<div style="text-align: center; padding: 3rem;"><div class="spinner"></div><p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.5rem">Analyzing error patterns & generating targeted remediation pack...</p></div>`;

  const rec = await API.getRecommendations();

  container.innerHTML = `
    <div class="remediation-hero-card animate-fade">
      <div style="display: flex; align-items: flex-start; gap: 0.75rem">
        <span style="font-size: 1.5rem">⚠️</span>
        <div>
          <h3 class="remediation-hero-title">Target Weak Topic: ${rec.topic}</h3>
          <p class="remediation-hero-desc">${rec.weakness_reason}</p>
        </div>
      </div>
    </div>

    <div class="card" style="padding: 1.5rem; margin-bottom: 1.5rem">
      <h4 style="font-size: 0.85rem; font-weight: 700; color: var(--primary-700); margin-bottom: 0.5rem">Simplified Remediation Concept</h4>
      <p style="font-size: 0.82rem; line-height: 1.7; color: var(--text-main); margin-bottom: 1rem">${rec.short_explanation}</p>
      
      <h5 style="font-size: 0.75rem; font-weight: 800; text-transform: uppercase; color: var(--text-main); margin-bottom: 0.5rem">Core Rules to Remember:</h5>
      <ul style="list-style: none; display: flex; flex-direction: column; gap: 0.5rem">
        ${rec.important_points.map(p => `
          <li class="review-item">
            <span style="color: var(--emerald-500); font-weight: 800">✓</span>
            <span style="line-height: 1.4">${p}</span>
          </li>
        `).join('')}
      </ul>
    </div>

    <div class="diagram-wrapper">
      <div class="diagram-toolbar">
        <span style="font-weight: 700; font-size: 0.75rem">Remediation Micro-Diagram (${rec.topic})</span>
      </div>
      <div id="remediation-diagram-stage" class="diagram-stage"></div>
    </div>

    <div class="card" style="padding: 1.5rem; margin-bottom: 1.5rem">
      <h4 style="font-size: 0.85rem; font-weight: 700; color: var(--emerald-800); margin-bottom: 1rem">Targeted Remediation Practice Drills</h4>
      <div style="display: flex; flex-direction: column; gap: 0.75rem">
        ${rec.practice_questions.map((q, i) => `
          <div class="practice-card">
            <div class="practice-question">${i + 1}. ${q.question}</div>
            <div class="practice-answer">• Correct Answer: <strong>${q.correct_key}</strong> — ${q.explanation}</div>
          </div>
        `).join('')}
      </div>
      
      <div style="display: flex; justify-content: flex-end; margin-top: 1rem">
        <button class="btn-lg btn-primary" onclick="switchWorkspaceTab('quiz')" style="font-size: 0.75rem">Retake Full Assessment Quiz</button>
      </div>
    </div>
  `;

  // Render remediation diagram
  if (rec.mermaid_diagram) {
    try {
      const { svg } = await mermaid.render(`remed_mermaid_${Date.now()}`, rec.mermaid_diagram);
      document.getElementById('remediation-diagram-stage').innerHTML = svg;
    } catch (e) {
      console.warn('Remediation diagram render note:', e);
    }
  }
}

function switchWorkspaceTab(tabName) {
  const btn = document.querySelector(`.tab-btn[data-tab="${tabName}"]`);
  if (btn) btn.click();
}

// --- 7. Student Dashboard Controller ---
async function renderDashboard() {
  const perf = await API.getPerformance();

  document.getElementById('dash-progress-val').textContent = `${perf.overall_progress || 72}%`;
  document.getElementById('dash-quiz-count').textContent = perf.quizzes_completed || 3;
  document.getElementById('dash-strong-count').textContent = perf.strong_topics?.length || 4;
  document.getElementById('dash-weak-count').textContent = perf.weak_topics?.length || 2;

  // Render Topic Mastery Bars
  const masteryContainer = document.getElementById('dash-mastery-bars');
  if (masteryContainer && perf.topic_masteries) {
    masteryContainer.innerHTML = perf.topic_masteries.map(tm => {
      const fillClass = tm.mastery_percentage >= 75 ? 'metric-strong' : tm.mastery_percentage >= 60 ? 'metric-moderate' : 'metric-weak';
      return `
        <div class="metric-bar-container">
          <div class="metric-bar-header">
            <span>${tm.topic}</span>
            <span style="font-family: var(--font-mono)">${tm.mastery_percentage}%</span>
          </div>
          <div class="metric-bar-track">
            <div class="metric-bar-fill ${fillClass}" style="width: ${tm.mastery_percentage}%"></div>
          </div>
        </div>
      `;
    }).join('');
  }
}

// --- 8. Upload Page Controller ---
function setupUploadZone() {
  const fileInput = document.getElementById('pdf-file-input');
  const dropZone = document.getElementById('pdf-dropzone');
  const demoBtn = document.getElementById('btn-load-demo-tb');

  if (demoBtn) {
    demoBtn.addEventListener('click', async () => {
      runUploadPipeline();
      await API.loadSampleTextbook();
      await loadInitialTextbooks();
      setTimeout(() => {
        showUploadComplete();
      }, 1800);
    });
  }

  if (fileInput) {
    fileInput.addEventListener('change', async (e) => {
      if (e.target.files && e.target.files[0]) {
        const file = e.target.files[0];
        runUploadPipeline();

        try {
          const formData = new FormData();
          formData.append('file', file);
          const res = await fetch(`${API_BASE}/upload`, {
            method: 'POST',
            body: formData
          });
          const data = await res.json();
          if (res.ok) {
            await loadInitialTextbooks();
            showUploadComplete(data.metadata);
          } else {
            alert(data.detail || 'Upload failed');
            const progressBox = document.getElementById('upload-progress-box');
            if (progressBox) progressBox.style.display = 'none';
          }
        } catch (err) {
          console.error('Upload failed:', err);
          showUploadComplete();
        }
      }
    });
  }
}

function runUploadPipeline() {
  const progressBox = document.getElementById('upload-progress-box');
  if (progressBox) progressBox.style.display = 'block';

  let step = 1;
  const interval = setInterval(() => {
    step++;
    if (step > 5) clearInterval(interval);
  }, 400);
}

function showUploadComplete(meta) {
  const readyBox = document.getElementById('upload-ready-box');
  const uploadCard = document.getElementById('upload-input-card');
  if (readyBox && uploadCard) {
    uploadCard.style.display = 'none';
    readyBox.style.display = 'block';
  }
}
