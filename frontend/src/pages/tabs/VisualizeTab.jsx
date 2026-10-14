import React, { useState, useEffect } from 'react';
import {
  GitBranch, Sparkles, Workflow, Network,
  RefreshCw, Columns, Compass, ShieldCheck,
  AlertTriangle, ArrowRight, BookOpen, Layers,
  HelpCircle, MessageSquare, Award, Clock,
  Cpu, FileText, Presentation, Video, CheckCircle2,
  X, ChevronRight, Lightbulb
} from 'lucide-react';
import { textbookAPI } from '../../services/api';
import { useTextbook } from '../../context/TextbookContext';
import { MermaidViewer } from '../../components/MermaidViewer';
import { SourceCitation } from '../../components/SourceCitation';

export const VisualizeTab = () => {
  const { activeTextbook, activeChapter, activeSection, setActiveTab, language } = useTextbook();
  const [topic, setTopic] = useState('');
  const [availableTopics, setAvailableTopics] = useState([]);
  const [diagramType, setDiagramType] = useState('auto');
  const [visualData, setVisualData] = useState(null);
  const [loading, setLoading] = useState(false);

  // Interactive Node Inspection state
  const [selectedNode, setSelectedNode] = useState(null);
  const [nodeExplanation, setNodeExplanation] = useState(null);
  const [nodeExplaining, setNodeExplaining] = useState(false);

  // Extract dynamic topics from active textbook & concept graph
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
      } catch (e) { }

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
        } else if (list.length > 0) {
          setTopic(list[0]);
        }
      }
    };

    extractTopics();
    return () => { isMounted = false; };
  }, [activeTextbook]);

  // Sync topic with active chapter/section
  useEffect(() => {
    if (activeSection?.title) {
      setTopic(activeSection.title);
    } else if (activeChapter?.title) {
      setTopic(activeChapter.title);
    }
  }, [activeChapter, activeSection]);

  const diagramTypes = [
    { id: 'auto', label: 'Auto Detect', icon: Sparkles },
    { id: 'flowchart', label: 'Flowchart', icon: GitBranch },
    { id: 'concept_map', label: 'Concept Map', icon: Compass },
    { id: 'block_diagram', label: 'Block Diagram', icon: Cpu },
    { id: 'sequence', label: 'Sequence Diagram', icon: Workflow },
    { id: 'comparison', label: 'Comparison', icon: Columns },
    { id: 'timeline', label: 'Timeline', icon: Clock },
    { id: 'hierarchy', label: 'Hierarchy', icon: Network },
    { id: 'cycle', label: 'State Cycle', icon: RefreshCw },
  ];

  const loadVisual = async (type = diagramType) => {
    if (!activeTextbook || !topic) return;
    try {
      setLoading(true);
      setSelectedNode(null);
      setNodeExplanation(null);
      const data = await textbookAPI.visualize(
        activeTextbook.id,
        topic,
        type,
        'intermediate',
        language || 'en'
      );
      setVisualData(data);
    } catch (err) {
      console.error('Visual generation error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (topic) {
      loadVisual(diagramType);
    }
  }, [topic, diagramType, activeTextbook, language]);

  // Handle clicking on a diagram node/step to inspect
  const handleInspectNode = (step) => {
    setSelectedNode(step);
    setNodeExplanation(null);
  };

  // Request simpler AI tutor explanation for selected node
  const handleExplainNodeSimpler = async () => {
    if (!selectedNode || !activeTextbook) return;
    try {
      setNodeExplaining(true);
      const res = await textbookAPI.explainNodeStep(
        activeTextbook.id,
        topic,
        selectedNode.label,
        selectedNode.description,
        language || 'en'
      );
      setNodeExplanation(res);
    } catch (err) {
      console.error('Error fetching simpler node explanation:', err);
    } finally {
      setNodeExplaining(false);
    }
  };

  return (
    <div className="space-y-6 text-slate-900 dark:text-slate-100">
      {/* Header & Concept selector */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center space-x-2">
              <Sparkles className="w-5 h-5 text-indigo-500" />
              <span>AI-Generated Visual Explanations</span>
            </h2>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Dynamically synthesizes flowcharts, architecture diagrams, sequence protocols, and semantic maps directly grounded in your course materials.
          </p>
        </div>

        {/* Topic selector */}
        <div className="flex items-center space-x-2">
          <span className="text-xs font-medium text-slate-600 dark:text-slate-400">Concept:</span>
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

      {/* Diagram Type Pill Buttons */}
      <div className="flex items-center space-x-2 overflow-x-auto pb-1 custom-scrollbar">
        {diagramTypes.map((dt) => {
          const Icon = dt.icon;
          const isActive = diagramType === dt.id;
          return (
            <button
              key={dt.id}
              onClick={() => setDiagramType(dt.id)}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
                isActive
                  ? 'bg-indigo-600 text-white shadow-sm ring-1 ring-indigo-500'
                  : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{dt.label}</span>
            </button>
          );
        })}
      </div>

      {/* Main Diagram Canvas */}
      {loading ? (
        <div className="py-20 text-center space-y-3">
          <div className="w-10 h-10 border-3 border-indigo-600 dark:border-indigo-400 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-sm font-medium text-slate-600 dark:text-slate-400">
            Extracting course evidence & generating visual Mermaid model...
          </p>
        </div>
      ) : visualData ? (
        <div className="space-y-6 animate-fade-in">

          {/* Insufficient Evidence Warning Banner */}
          {visualData.is_sufficient_evidence === false && (
            <div className="p-4 bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-800 rounded-xl space-y-2">
              <div className="flex items-center space-x-2 text-amber-800 dark:text-amber-300 font-bold text-xs">
                <AlertTriangle className="w-4 h-4 text-amber-600" />
                <span>Source Limitation Notice</span>
              </div>
              <p className="text-2xs text-amber-900 dark:text-amber-200/90 leading-relaxed">
                {visualData.limitation_note || "The uploaded course materials do not contain sufficient evidence to generate an authentic visual diagram without hallucination."}
              </p>
            </div>
          )}

          {/* Interactive Mermaid Diagram Component */}
          <MermaidViewer
            chart={visualData.mermaid_code}
            title={`${visualData.topic} (${(visualData.detected_type || 'DIAGRAM').toUpperCase()})`}
            sourceReference={visualData.source_reference}
          />

          {/* Grounded Diagram Description & Interactive Node Explorer */}
          <div className="academic-card p-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <h4 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider mb-1">
                  Visual Architecture Overview
                </h4>
                <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                  {visualData.description}
                </p>
              </div>
              <div className="flex items-center space-x-2 self-start sm:self-auto flex-shrink-0">
                <button
                  onClick={() => setActiveTab('explain')}
                  className="inline-flex items-center space-x-1 px-2.5 py-1 text-2xs font-semibold bg-indigo-50 hover:bg-indigo-100 dark:bg-indigo-950/60 dark:hover:bg-indigo-900 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 rounded-lg transition"
                >
                  <BookOpen className="w-3 h-3" />
                  <span>Switch to Text Explanation</span>
                </button>
                <button
                  onClick={() => setActiveTab('graph')}
                  className="inline-flex items-center space-x-1 px-2.5 py-1 text-2xs font-semibold bg-emerald-50 hover:bg-emerald-100 dark:bg-emerald-950/60 dark:hover:bg-emerald-900 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 rounded-lg transition"
                >
                  <Network className="w-3 h-3" />
                  <span>View Learning Path</span>
                </button>
              </div>
            </div>

            {/* Interactive Steps / Nodes Grid */}
            {visualData.steps_or_nodes && visualData.steps_or_nodes.length > 0 && (
              <div className="pt-3 border-t border-slate-100 dark:border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <h5 className="text-2xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center space-x-1.5">
                    <span>Grounded Nodes & Process Steps:</span>
                    <span className="text-3xs text-indigo-500 font-normal">(Click any step to inspect evidence)</span>
                  </h5>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {visualData.steps_or_nodes.map((step, idx) => {
                    const isSelected = selectedNode?.label === step.label;
                    const citation = step.source_citation;
                    return (
                      <div
                        key={idx}
                        onClick={() => handleInspectNode(step)}
                        className={`p-3 rounded-xl border text-xs cursor-pointer transition-all ${isSelected
                            ? 'bg-indigo-50/90 dark:bg-indigo-950/70 border-indigo-500 ring-2 ring-indigo-500/20 shadow-xs'
                            : 'bg-slate-50/70 dark:bg-slate-800/60 hover:bg-indigo-50/40 dark:hover:bg-slate-800 border-slate-200 dark:border-slate-700'
                          }`}
                      >
                        <div className="flex items-start justify-between gap-1 mb-1">
                          <p className="font-bold text-slate-900 dark:text-slate-100 truncate">
                            {step.label}
                          </p>
                          <ChevronRight className="w-3.5 h-3.5 text-slate-400 flex-shrink-0 mt-0.5" />
                        </div>
                        <p className="text-slate-600 dark:text-slate-400 leading-relaxed text-2xs line-clamp-2">
                          {step.description}
                        </p>
                        {citation && (
                          <div className="mt-2 pt-2 border-t border-slate-200/60 dark:border-slate-700/60 flex items-center space-x-1.5 text-3xs text-slate-500 dark:text-slate-400">
                            {citation.source_type === 'presentation' ? (
                              <Presentation className="w-3 h-3 text-amber-500" />
                            ) : citation.source_type === 'video' ? (
                              <Video className="w-3 h-3 text-cyan-500" />
                            ) : (
                              <FileText className="w-3 h-3 text-indigo-500" />
                            )}
                            <span className="truncate">
                              {citation.source_type === 'presentation' ? `Slide ${citation.slide || 1}` : citation.source_type === 'video' ? `Timestamp ${citation.timestamp || '00:00'}` : `Page ${citation.page || 1}`}
                            </span>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Interactive Selected Node Inspector Modal / Drawer */}
          {selectedNode && (
            <div className="academic-card p-5 bg-gradient-to-r from-indigo-50/60 via-purple-50/40 to-slate-50 dark:from-slate-900 dark:via-indigo-950/30 dark:to-slate-900 border-2 border-indigo-400 dark:border-indigo-600 rounded-xl space-y-4 animate-fade-in shadow-sm">
              <div className="flex items-start justify-between">
                <div className="flex items-center space-x-2">
                  <div className="p-2 bg-indigo-600 text-white rounded-lg">
                    <Lightbulb className="w-4 h-4" />
                  </div>
                  <div>
                    <span className="text-3xs font-extrabold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
                      Step / Node Inspector
                    </span>
                    <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                      {selectedNode.label}
                    </h3>
                  </div>
                </div>
                <button
                  onClick={() => setSelectedNode(null)}
                  className="p-1 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-800"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Node Detailed Description */}
              <div className="p-3 bg-white dark:bg-slate-800/90 rounded-lg border border-slate-200 dark:border-slate-700 text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
                <span className="font-bold text-slate-900 dark:text-white block mb-0.5">Content Explanation:</span>
                {selectedNode.description}
              </div>

              {/* Source Provenance Citation */}
              {selectedNode.source_citation && (
                <div className="p-3 bg-indigo-50/80 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800/80 rounded-lg space-y-1.5">
                  <div className="flex items-center space-x-1.5 text-2xs font-bold text-indigo-900 dark:text-indigo-300">
                    <ShieldCheck className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
                    <span>Verified Source Grounding</span>
                  </div>
                  <p className="text-3xs text-indigo-800 dark:text-indigo-300 font-mono">
                    {selectedNode.source_citation.filename} &bull; {selectedNode.source_citation.source_type === 'presentation' ? `Slide ${selectedNode.source_citation.slide || 1}` : selectedNode.source_citation.source_type === 'video' ? `Timestamp ${selectedNode.source_citation.timestamp || '00:00'}` : `Page ${selectedNode.source_citation.page || 1}`}
                  </p>
                  {selectedNode.source_citation.excerpt && (
                    <p className="text-3xs text-slate-600 dark:text-slate-400 italic">
                      "{selectedNode.source_citation.excerpt}"
                    </p>
                  )}
                </div>
              )}

              {/* Simpler AI Tutor Explanation Area */}
              {nodeExplanation ? (
                <div className="p-4 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-300 dark:border-emerald-800 rounded-lg space-y-2">
                  <div className="flex items-center space-x-1.5 text-emerald-800 dark:text-emerald-300 font-bold text-xs">
                    <Sparkles className="w-4 h-4 text-emerald-600" />
                    <span>Simple Conceptual Explanation (Grounded AI Tutor)</span>
                  </div>
                  <p className="text-xs text-emerald-950 dark:text-emerald-200 leading-relaxed">
                    {nodeExplanation.simple_explanation}
                  </p>
                  {nodeExplanation.analogy && (
                    <div className="p-2.5 bg-white/80 dark:bg-slate-900/60 rounded text-2xs text-emerald-900 dark:text-emerald-300 border border-emerald-200/60 dark:border-emerald-800/60">
                      <span className="font-bold">Analogy: </span>
                      {nodeExplanation.analogy}
                    </div>
                  )}
                </div>
              ) : null}

              {/* Interactive Node Action Buttons */}
              <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-200/80 dark:border-slate-800">
                <button
                  onClick={handleExplainNodeSimpler}
                  disabled={nodeExplaining}
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-lg shadow-xs transition disabled:opacity-50"
                >
                  <Sparkles className={`w-3.5 h-3.5 ${nodeExplaining ? 'animate-spin' : ''}`} />
                  <span>{nodeExplaining ? 'Asking Tutor...' : 'Explain in Simpler Language'}</span>
                </button>
                <button
                  onClick={() => setActiveTab('quiz')}
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-200 text-xs font-semibold rounded-lg transition"
                >
                  <Award className="w-3.5 h-3.5 text-amber-500" />
                  <span>Take Concept Quiz</span>
                </button>
              </div>
            </div>
          )}

          {/* Source Grounding */}
          <SourceCitation reference={visualData.source_reference} />
        </div>
      ) : null}
    </div>
  );
};
