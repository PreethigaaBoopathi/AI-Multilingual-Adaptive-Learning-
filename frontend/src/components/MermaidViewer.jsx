import React, { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';
import { 
  Code, Download, ZoomIn, ZoomOut, RotateCcw, 
  Copy, Check, Edit3, Eye, Sparkles, Wand2, RefreshCw 
} from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

/**
 * Automatically cleans and sanitizes Mermaid syntax:
 * 1. Strips markdown fences (```mermaid ... ```).
 * 2. Wraps unquoted node labels in double quotes ["..."] to prevent syntax errors
 *    from parentheses (e.g. O(L)), ampersands (&), question marks, colons, or dashes.
 * 3. Converts legacy arrow labels (A -- Yes --> B) to pipe syntax (A -->|Yes| B).
 * 4. Cleans LaTeX commands (\mathcal, \le, \ge, \models, \in, \text) that crash Mermaid.
 * 5. Guarantees a valid diagram declaration (e.g. 'graph TD\n').
 */
export function cleanMermaidCode(raw) {
  if (!raw || typeof raw !== 'string' || !raw.trim()) {
    return 'graph TD\n  A["Diagram Not Available"]';
  }

  let code = raw.trim();

  // 1. Strip markdown code fences
  code = code.replace(/^```(?:mermaid)?\s*/i, '');
  code = code.replace(/```\s*$/, '').trim();

  // 2. Ensure diagram starts with valid declaration (skipping comments)
  const validHeaders = [
    'graph ', 'flowchart ', 'sequenceDiagram', 'classDiagram',
    'stateDiagram', 'erDiagram', 'timeline', 'gantt', 'pie',
    'quadrantChart', 'mindmap', 'gitGraph', 'journey', 'C4Context'
  ];
  const firstContentLine = code.split('\n').map(l => l.trim()).find(l => l && !l.startsWith('%%')) || '';
  if (!validHeaders.some(h => firstContentLine.startsWith(h))) {
    code = 'graph TD\n' + code;
  }

  // Special case: sequence diagrams have a distinct syntax (no graph subgraphs/brackets)
  if (firstContentLine.startsWith('sequenceDiagram') || code.startsWith('sequenceDiagram')) {
    const seqLines = code.split('\n').map(line => {
      let l = line.replace(/\\mathcal/g, 'Math_').replace(/\\in/g, 'in').replace(/\\ge/g, '>=').replace(/\\le/g, '<=');
      l = l.replace(/\\models/g, '|=').replace(/\\text/g, '').replace(/\\/g, '');
      return l;
    });
    return seqLines.join('\n').trim();
  }

  // 3. Process lines for flowcharts, concept maps, hierarchies, etc.
  const lines = code.split('\n').map(line => {
    const trimmed = line.trim();
    if (!trimmed) return '';

    // Preserve styling, class definitions, clicks, etc.
    if (/^(?:style|classDef|class|end|click|autonumber)\b/.test(trimmed)) {
      return line;
    }

    let l = line;

    // Standardize subgraphs with unquoted bracket titles: subgraph ID [Title] -> subgraph ID ["Title"]
    l = l.replace(/subgraph\s+([A-Za-z0-9_-]+)\s*\[([^"\]\n][^\]\n]*?)\]/g, (m, id, text) => {
      const safeText = text.replace(/"/g, "'");
      return `subgraph ${id} ["${safeText}"]`;
    });

    if (/^subgraph\b/.test(trimmed)) {
      return l;
    }

    // Standardize edge labels: 'A -- Yes --> B' or 'A -- "Yes" --> B' -> 'A -->|Yes| B'
    l = l.replace(/\s+--\s+["']?([^->\n|'"]+?)["']?\s+-->\s+/g, ' -->|$1| ');

    // Standardize dotted arrows: 'A -. Yes .-> B' or 'A -. "Yes" .-> B' -> 'A -.->|Yes| B'
    l = l.replace(/\s+-\.\s*["']?([^->\n|'"]+?)["']?\s*\.->\s+/g, ' -.->|$1| ');

    // Wrap unquoted square brackets: ID[label] -> ID["label"]
    l = l.replace(/(\b[A-Za-z0-9_-]+)\[([^"\]\n][^\]\n]*?)\]/g, (match, id, text) => {
      const safeText = text.replace(/"/g, "'");
      return `${id}["${safeText}"]`;
    });

    // Wrap unquoted rhombus / decision: ID{label} -> ID{"label"}
    l = l.replace(/(\b[A-Za-z0-9_-]+)\{([^"\}\n][^\}\n]*?)\}/g, (match, id, text) => {
      const safeText = text.replace(/"/g, "'");
      return `${id}{"${safeText}"}`;
    });

    // Clean LaTeX commands that crash Mermaid lexer
    l = l.replace(/\\mathcal/g, 'Math_').replace(/\\in/g, 'in').replace(/\\ge/g, '>=').replace(/\\le/g, '<=');
    l = l.replace(/\\models/g, '|=').replace(/\\text/g, '').replace(/\\/g, '');

    return l;
  });

  return lines.filter(Boolean).join('\n');
}

/**
 * Resilient recovery generator if original Mermaid code fails rendering.
 * Extracts text concepts and reconstructs a guaranteed-valid flowchart.
 */
export function generateRecoveryMermaid(raw) {
  if (!raw || typeof raw !== 'string') {
    return 'graph TD\n  Start["Course Concept Overview"] --> End["Analysis Complete"]';
  }

  // 1. If it's a sequence diagram, recover as valid sequence
  if (raw.includes('sequenceDiagram')) {
    const msgMatches = [...raw.matchAll(/(?:actor|participant)\s+([A-Za-z0-9_-]+)/g)];
    const actors = Array.from(new Set(msgMatches.map(m => m[1]))).slice(0, 4);
    if (actors.length >= 2) {
      let out = 'sequenceDiagram\n  autonumber\n';
      actors.forEach(a => { out += `  participant ${a}\n`; });
      out += `  ${actors[0]}->>${actors[1]}: 1. Request / Ingestion\n`;
      out += `  ${actors[1]}->>${actors[actors.length - 1]}: 2. Execute Operation\n`;
      out += `  ${actors[actors.length - 1]}-->>${actors[0]}: 3. Return Verified Results\n`;
      return out;
    }
  }

  const matches = [...raw.matchAll(/\["([^"]+)"\]|\{"([^"]+)"\}|\[([^\]]+)\]/g)];
  const labels = matches
    .map(m => m[1] || m[2] || m[3])
    .filter(Boolean)
    .map(l => l.replace(/["\n]/g, "'").trim())
    .filter(l => l.length > 1)
    .slice(0, 7);

  if (labels.length >= 2) {
    let out = 'graph TD\n';
    labels.forEach((lbl, i) => {
      const cleanLbl = lbl.slice(0, 40);
      out += `  N${i+1}["${cleanLbl}"]\n`;
      if (i > 0) {
        out += `  N${i} --> N${i+1}\n`;
      }
    });
    labels.forEach((_, i) => {
      out += `  style N${i+1} fill:#e0e7ff,stroke:#6366f1,stroke-width:1.5px\n`;
    });
    return out;
  }

  // Fallback extracting words from raw if no brackets
  const words = raw.replace(/[^\w\s]/g, ' ').split(/\s+/).filter(w => w.length > 3 && !['graph', 'flowchart', 'sequenceDiagram', 'participant', 'autonumber', 'style', 'classDef'].includes(w)).slice(0, 4);
  const stepA = words[0] ? words[0].toUpperCase() + ' Ingestion' : 'Concept Overview';
  const stepB = words[1] ? words[1].toUpperCase() + ' Processing' : 'Operational Traversal';
  const stepC = words[2] ? words[2].toUpperCase() + ' Verification' : 'Verified Output';

  return `graph TD\n  Start["${stepA}"] --> Step1["${stepB}"] --> Step2["${stepC}"]\n  style Start fill:#ecfdf5,stroke:#10b981\n  style Step1 fill:#eff6ff,stroke:#3b82f6\n  style Step2 fill:#fef3c7,stroke:#f59e0b`;
}

export const MermaidViewer = ({ 
  chart, 
  title = "Visual Flowchart", 
  sourceReference = "", 
  onRegenerate = null 
}) => {
  const { isDark } = useTheme();
  const containerRef = useRef(null);
  const [svgContent, setSvgContent] = useState('');
  const [zoom, setZoom] = useState(1);
  const [error, setError] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [currentCode, setCurrentCode] = useState(chart || '');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    setCurrentCode(chart || '');
  }, [chart]);

  const renderDiagram = async (codeToRender) => {
    if (!codeToRender || !codeToRender.trim()) return;
    const sanitized = cleanMermaidCode(codeToRender);
    const uniqueId = 'mermaid_' + Math.random().toString(36).substring(2, 9);

    try {
      setError(null);
      mermaid.initialize({
        startOnLoad: false,
        theme: isDark ? 'dark' : 'default',
        securityLevel: 'loose',
        suppressErrorRendering: true,
        fontFamily: 'Inter, system-ui, sans-serif',
        themeVariables: isDark ? {
          fontFamily: 'Inter, system-ui, sans-serif',
          primaryColor: '#312e81',
          primaryTextColor: '#f8fafc',
          primaryBorderColor: '#6366f1',
          lineColor: '#94a3b8',
          secondaryColor: '#1e293b',
          tertiaryColor: '#0f172a',
          background: '#0f172a',
          mainBkg: '#1e293b',
          nodeBorder: '#6366f1'
        } : {
          fontFamily: 'Inter, system-ui, sans-serif',
          primaryColor: '#e0f2fe',
          primaryTextColor: '#0f172a',
          primaryBorderColor: '#38bdf8',
          lineColor: '#64748b',
          secondaryColor: '#fef3c7',
          tertiaryColor: '#f1f5f9',
        }
      });

      // Clear any prior stray Mermaid error elements from the DOM
      if (typeof document !== 'undefined') {
        const stray = document.querySelectorAll('[id^="dmermaid_"]');
        stray.forEach(el => el.remove());
      }

      const { svg } = await mermaid.render(uniqueId, sanitized);
      setSvgContent(svg);
      setError(null);
    } catch (err) {
      console.warn('Initial Mermaid render failed, attempting auto-repair recovery:', err);
      // Remove any error DOM nodes mermaid might have injected
      if (typeof document !== 'undefined') {
        const errEl = document.getElementById('d' + uniqueId);
        if (errEl) errEl.remove();
      }

      // Auto-Recovery: build a clean, guaranteed-working sequence from extracted nodes
      try {
        const recoveryId = 'mermaid_rec_' + Math.random().toString(36).substring(2, 9);
        const fallbackCode = generateRecoveryMermaid(sanitized);
        const { svg: fallbackSvg } = await mermaid.render(recoveryId, fallbackCode);
        setSvgContent(fallbackSvg);
        setError(null);
      } catch (recErr) {
        console.error('All Mermaid render attempts failed:', recErr);
        setError('Unable to render diagram syntax. You can edit the code in the Source editor.');
      }
    }
  };

  useEffect(() => {
    renderDiagram(currentCode);
  }, [currentCode, isDark]);

  const handleAutoRepair = () => {
    const repaired = cleanMermaidCode(currentCode);
    setCurrentCode(repaired);
    renderDiagram(repaired);
  };

  const handleForceRecovery = () => {
    const fallback = generateRecoveryMermaid(currentCode);
    setCurrentCode(fallback);
    renderDiagram(fallback);
  };

  const handleZoomIn = () => setZoom(prev => Math.min(prev + 0.15, 2.5));
  const handleZoomOut = () => setZoom(prev => Math.max(prev - 0.15, 0.5));
  const handleResetZoom = () => setZoom(1);

  const handleCopyCode = () => {
    navigator.clipboard.writeText(currentCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadSVG = () => {
    if (!svgContent) return;
    const blob = new Blob([svgContent], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${title.toLowerCase().replace(/\s+/g, '_')}_diagram.svg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="academic-card border border-slate-200 dark:border-slate-800 overflow-hidden bg-white dark:bg-slate-900 shadow-sm flex flex-col my-4 rounded-xl">
      {/* Header Toolbar */}
      <div className="bg-slate-50 dark:bg-slate-800/80 px-4 py-3 border-b border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center space-x-2">
          <div className="p-1.5 bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 rounded-md">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-slate-800 dark:text-white">{title}</h4>
            {sourceReference && (
              <p className="text-xs text-slate-500 dark:text-slate-400 font-medium truncate max-w-sm">
                Source: {sourceReference}
              </p>
            )}
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center space-x-1 sm:space-x-2">
          {/* Zoom controls */}
          <div className="flex items-center bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg p-0.5 shadow-2xs">
            <button
              onClick={handleZoomOut}
              title="Zoom Out"
              className="p-1.5 text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 rounded"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <span className="text-2xs font-mono px-1.5 text-slate-500 dark:text-slate-400 min-w-10 text-center">
              {Math.round(zoom * 100)}%
            </span>
            <button
              onClick={handleZoomIn}
              title="Zoom In"
              className="p-1.5 text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 rounded"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={handleResetZoom}
              title="Reset Zoom"
              className="p-1.5 text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 rounded border-l border-slate-200 dark:border-slate-700"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Edit / View Source Toggle */}
          <button
            onClick={() => setIsEditing(!isEditing)}
            className={`flex items-center space-x-1 px-2.5 py-1.5 text-xs font-semibold rounded-lg border transition-all ${
              isEditing 
                ? 'bg-indigo-600 text-white border-indigo-600' 
                : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700'
            }`}
          >
            {isEditing ? <Eye className="w-3.5 h-3.5" /> : <Code className="w-3.5 h-3.5" />}
            <span className="hidden sm:inline">{isEditing ? 'View Diagram' : 'View Source'}</span>
          </button>

          {/* Download SVG */}
          <button
            onClick={handleDownloadSVG}
            title="Download SVG Diagram"
            className="flex items-center space-x-1 px-2.5 py-1.5 text-xs font-medium bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700 rounded-lg"
          >
            <Download className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Export</span>
          </button>
        </div>
      </div>

      {/* Editor Modal or Visual Stage */}
      {isEditing ? (
        <div className="p-4 bg-slate-900 text-slate-100">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center space-x-2">
              <Edit3 className="w-4 h-4 text-indigo-400" />
              <span className="text-xs font-semibold text-slate-300">Mermaid Diagram Source Code (Live Editable)</span>
            </div>
            <div className="flex items-center space-x-2">
              <button
                onClick={handleAutoRepair}
                className="flex items-center space-x-1 text-xs text-indigo-300 hover:text-white bg-indigo-900/60 hover:bg-indigo-800 border border-indigo-700/60 px-2.5 py-1 rounded transition"
                title="Automatically fix unquoted brackets, arrows, and special characters"
              >
                <Wand2 className="w-3.5 h-3.5 text-indigo-400" />
                <span>Auto-Repair Syntax</span>
              </button>
              <button
                onClick={handleCopyCode}
                className="flex items-center space-x-1 text-xs text-slate-300 hover:text-white bg-slate-800 px-2 py-1 rounded"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Copied' : 'Copy Code'}</span>
              </button>
            </div>
          </div>
          <textarea
            value={currentCode}
            onChange={(e) => setCurrentCode(e.target.value)}
            rows={10}
            className="w-full bg-slate-950 text-emerald-300 font-mono text-xs p-3 rounded-md border border-slate-800 focus:outline-none focus:border-indigo-500 leading-relaxed"
            placeholder="Enter Mermaid diagram code..."
          />
          <div className="flex justify-end mt-2 space-x-2">
            <button
              onClick={() => setCurrentCode(chart)}
              className="px-3 py-1 text-xs text-slate-400 hover:text-white"
            >
              Reset to Original
            </button>
            <button
              onClick={() => {
                renderDiagram(currentCode);
                setIsEditing(false);
              }}
              className="px-4 py-1.5 text-xs font-semibold bg-indigo-600 hover:bg-indigo-700 text-white rounded-md shadow-sm"
            >
              Apply & Render Diagram
            </button>
          </div>
        </div>
      ) : (
        <div className="p-6 bg-slate-50/50 dark:bg-slate-950 min-h-[320px] flex items-center justify-center overflow-auto">
          {error ? (
            <div className="text-center p-6 text-rose-600 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 rounded-xl max-w-lg shadow-sm space-y-3">
              <div className="flex items-center justify-center space-x-2 text-rose-700 dark:text-rose-400 font-semibold text-sm">
                <Sparkles className="w-4 h-4" />
                <span>{error}</span>
              </div>
              <p className="text-2xs text-slate-500 dark:text-slate-400 max-w-md mx-auto">
                Diagram syntax contained unsupported characters or formatting. You can auto-repair it instantly or edit the source.
              </p>
              <div className="flex flex-wrap items-center justify-center gap-2 pt-1">
                <button
                  onClick={handleAutoRepair}
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg shadow-sm transition"
                >
                  <Wand2 className="w-3.5 h-3.5" />
                  <span>Auto-Repair Syntax</span>
                </button>
                <button
                  onClick={handleForceRecovery}
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold bg-slate-200 hover:bg-slate-300 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-lg transition"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Synthesize Safe Diagram</span>
                </button>
                <button
                  onClick={() => setIsEditing(true)}
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-indigo-600 dark:text-indigo-400 hover:underline"
                >
                  <Edit3 className="w-3.5 h-3.5" />
                  <span>Edit Code</span>
                </button>
              </div>
            </div>
          ) : (
            <div 
              ref={containerRef}
              style={{ transform: `scale(${zoom})`, transformOrigin: 'top center', transition: 'transform 0.15s ease-out' }}
              className="w-full flex justify-center py-2"
              dangerouslySetInnerHTML={{ __html: svgContent }}
            />
          )}
        </div>
      )}
    </div>
  );
};
