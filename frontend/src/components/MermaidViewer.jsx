import React, { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';
import { 
  Code, Download, ZoomIn, ZoomOut, RotateCcw, 
  Copy, Check, Edit3, X, Eye, Sparkles 
} from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

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
    setCurrentCode(chart);
  }, [chart]);

  const renderDiagram = async (codeToRender) => {
    if (!codeToRender || !codeToRender.trim()) return;
    try {
      setError(null);
      mermaid.initialize({
        startOnLoad: false,
        theme: isDark ? 'dark' : 'default',
        securityLevel: 'loose',
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

      const uniqueId = `mermaid_${Date.now()}_${Math.floor(Math.random() * 1000)}`;
      const { svg } = await mermaid.render(uniqueId, codeToRender);
      setSvgContent(svg);
    } catch (err) {
      console.error('Mermaid render error:', err);
      setError('Unable to render diagram syntax. You can edit the code in the Source editor.');
    }
  };

  useEffect(() => {
    renderDiagram(currentCode);
  }, [currentCode, isDark]);

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
            <button
              onClick={handleCopyCode}
              className="flex items-center space-x-1 text-xs text-slate-300 hover:text-white bg-slate-800 px-2 py-1 rounded"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'Copied' : 'Copy Code'}</span>
            </button>
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
            <div className="text-center p-6 text-rose-600 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 rounded-lg max-w-md">
              <p className="font-semibold text-sm mb-2">{error}</p>
              <button
                onClick={() => setIsEditing(true)}
                className="text-xs text-indigo-600 dark:text-indigo-400 font-semibold underline hover:text-indigo-800"
              >
                Open Source Editor to Fix
              </button>
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
