import React, { useState, useRef } from 'react';
import {
  Upload, FileText, CheckCircle2, Sparkles, ArrowRight,
  AlertCircle, BookOpen, Layers, ShieldCheck, Cpu, Film, 
  Presentation as PresentationIcon, X, Network, Award, GitBranch,
  Clock, PlayCircle
} from 'lucide-react';
import { textbookAPI } from '../services/api';
import { useTextbook } from '../context/TextbookContext';

export const UploadPage = ({ onOpenWorkspace }) => {
  const { textbooks, selectTextbook, fetchTextbooks, setActiveTab } = useTextbook();
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [uploadedData, setUploadedData] = useState(null);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  const processingSteps = [
    { label: "Uploading material to secure server...", icon: Upload },
    { label: "Detecting file type & extracting multimodal content (text, slides, speech)...", icon: FileText },
    { label: "Extracting embedded figures, tables, speaker notes & keyframes...", icon: Layers },
    { label: "Creating unified knowledge chunks & vector indexing with source provenance...", icon: Cpu },
    { label: "Preparing multimodal AI learning tools & multilingual cache...", icon: Sparkles }
  ];

  const isSupportedFile = (f) => {
    if (!f) return false;
    const name = f.name.toLowerCase();
    return name.endsWith('.pdf') || name.endsWith('.ppt') || name.endsWith('.pptx') || name.endsWith('.mp4');
  };

  const getFileCategoryLabel = (filename) => {
    if (!filename) return "Material Ready";
    const name = filename.toLowerCase();
    if (name.endsWith('.pdf')) return "PDF Document Ready";
    if (name.endsWith('.pptx') || name.endsWith('.ppt')) return "PowerPoint Presentation Ready";
    if (name.endsWith('.mp4')) return "MP4 Lecture Video Ready";
    return "Material Ready";
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (isSupportedFile(droppedFile)) {
        setFile(droppedFile);
        setError(null);
      } else {
        setError("Unsupported format. Please upload a PDF textbook (.pdf), PowerPoint slides (.ppt, .pptx), or MP4 lecture video (.mp4).");
      }
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      if (isSupportedFile(selectedFile)) {
        setFile(selectedFile);
        setError(null);
      } else {
        setError("Unsupported format. Please upload a PDF textbook (.pdf), PowerPoint slides (.ppt, .pptx), or MP4 lecture video (.mp4).");
      }
    }
  };

  const handleClearSelectedFile = (e) => {
    if (e) e.stopPropagation();
    setFile(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const runPipelineSteps = async (formData) => {
    setUploading(true);
    setError(null);
    setCurrentStep(0);

    // Animate stepped progress
    const stepInterval = setInterval(() => {
      setCurrentStep(prev => {
        if (prev < processingSteps.length - 1) {
          return prev + 1;
        }
        return prev;
      });
    }, 600);

    try {
      const response = await textbookAPI.uploadPDF(formData);
      clearInterval(stepInterval);
      setCurrentStep(processingSteps.length);
      
      const newMetadata = response.metadata;
      setUploadedData(newMetadata);

      // Refresh list and select this newly uploaded material in context
      const updatedList = await fetchTextbooks();
      const matched = (Array.isArray(updatedList) && updatedList.find(t => t.id === newMetadata?.id)) || newMetadata;
      selectTextbook(matched);

      // Reset the file input so the user can immediately upload another material if they wish!
      setFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (err) {
      clearInterval(stepInterval);
      const message = err.response?.data?.detail
        || (err.code === 'ECONNABORTED' ? 'Processing is taking longer than expected. Please check your course workspace or retry.' : null)
        || err.message
        || 'Failed to process file. Please check that the file is valid.';
      setError(message);
    } finally {
      setUploading(false);
    }
  };

  const handleStartUpload = () => {
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    runPipelineSteps(formData);
  };

  const handleOpenWorkspaceTab = (tabId = 'summary') => {
    if (setActiveTab) {
      setActiveTab(tabId);
    }
    if (onOpenWorkspace) {
      onOpenWorkspace();
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 space-y-8 animate-fade-in text-slate-900 dark:text-slate-100">

      {/* Header */}
      <div className="text-center space-y-2">
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
          Upload Course Material
        </h1>
        <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 max-w-xl mx-auto">
          Upload any PDF textbook, PowerPoint presentation (.ppt/.pptx), or MP4 lecture video. TextIQ automatically extracts content, slides, speech, and keyframes with source grounding.
        </p>
      </div>

      {/* 1. MAIN DRAG & DROP UPLOAD OPTION — ALWAYS VISIBLE! */}
      <div className="academic-card p-6 sm:p-8 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-6 rounded-2xl">
        <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 flex items-center justify-center font-bold">
              <Upload className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900 dark:text-white">
                Add New Material
              </h2>
              <p className="text-3xs text-slate-400">PDF Document, PowerPoint Presentation, or MP4 Lecture Video</p>
            </div>
          </div>
          {file && (
            <button
              onClick={handleClearSelectedFile}
              className="text-xs text-rose-500 hover:text-rose-600 font-semibold flex items-center space-x-1 cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
              <span>Clear File</span>
            </button>
          )}
        </div>

        <div
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-2xl p-8 sm:p-10 text-center cursor-pointer transition-all flex flex-col items-center justify-center space-y-4 ${
            dragActive
              ? 'border-indigo-600 bg-indigo-50/50 dark:bg-indigo-950/40 scale-[1.01]'
              : file
                ? 'border-emerald-500 bg-emerald-50/30 dark:bg-emerald-950/20'
                : 'border-slate-300 dark:border-slate-700 hover:border-indigo-400 dark:hover:border-indigo-500 bg-slate-50/50 dark:bg-slate-800/40'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.ppt,.pptx,.mp4,application/pdf,application/vnd.ms-powerpoint,application/vnd.openxmlformats-officedocument.presentationml.presentation,video/mp4"
            onChange={handleFileChange}
            className="hidden"
          />

          <div className={`w-16 h-16 rounded-2xl flex items-center justify-center shadow-xs transition-colors ${
            file ? 'bg-emerald-500 text-white' : 'bg-indigo-100 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400'
          }`}>
            {file && file.name.toLowerCase().endsWith('.mp4') ? (
              <Film className="w-8 h-8" />
            ) : file && (file.name.toLowerCase().endsWith('.pptx') || file.name.toLowerCase().endsWith('.ppt')) ? (
              <PresentationIcon className="w-8 h-8" />
            ) : (
              <Upload className="w-8 h-8" />
            )}
          </div>

          {file ? (
            <div className="space-y-1">
              <p className="font-bold text-sm text-slate-900 dark:text-white">{file.name}</p>
              <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">
                {(file.size / (1024 * 1024)).toFixed(2)} MB &bull; {getFileCategoryLabel(file.name)}
              </p>
              <div className="flex items-center justify-center space-x-2 pt-1">
                <span className="inline-block text-2xs font-semibold px-2 py-0.5 rounded bg-emerald-100 dark:bg-emerald-900/60 text-emerald-800 dark:text-emerald-300">
                  Ready to process
                </span>
                <span className="text-2xs text-slate-400 underline">Click to choose another</span>
              </div>
            </div>
          ) : (
            <div className="space-y-1">
              <p className="font-bold text-sm text-slate-900 dark:text-slate-100">
                Drag and drop your course material here, or <span className="text-indigo-600 dark:text-indigo-400 underline font-semibold">browse files</span>
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Supported formats: <strong>PDF (.pdf)</strong>, <strong>PowerPoint (.ppt, .pptx)</strong>, <strong>MP4 Video (.mp4)</strong>
              </p>
            </div>
          )}
        </div>

        {error && (
          <div className="p-3 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-rose-700 dark:text-rose-300 text-xs rounded-lg flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Stepped Progress Pipeline while uploading */}
        {uploading && (
          <div className="space-y-4 pt-2 animate-fade-in">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-700 dark:text-slate-300">
              <span>Multimodal Processing Pipeline</span>
              <span>{Math.min(100, Math.round(((currentStep + 1) / processingSteps.length) * 100))}%</span>
            </div>

            {/* Progress bar */}
            <div className="w-full h-2 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-indigo-600 dark:bg-indigo-500 transition-all duration-300 rounded-full"
                style={{ width: `${Math.min(100, ((currentStep + 1) / processingSteps.length) * 100)}%` }}
              />
            </div>

            {/* Steps List */}
            <div className="space-y-2 pt-2">
              {processingSteps.map((step, idx) => {
                const Icon = step.icon;
                const isDone = currentStep > idx;
                const isCurrent = currentStep === idx;

                return (
                  <div
                    key={idx}
                    className={`p-2.5 rounded-lg text-xs flex items-center space-x-3 transition-all ${
                      isDone
                        ? 'bg-emerald-50/70 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
                        : isCurrent
                          ? 'bg-indigo-50 dark:bg-indigo-950/50 text-indigo-900 dark:text-indigo-200 border border-indigo-200 dark:border-indigo-800 font-semibold'
                          : 'text-slate-400 dark:text-slate-600 opacity-60'
                    }`}
                  >
                    {isDone ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 flex-shrink-0" />
                    ) : isCurrent ? (
                      <div className="w-4 h-4 border-2 border-indigo-600 dark:border-indigo-400 border-t-transparent rounded-full animate-spin flex-shrink-0" />
                    ) : (
                      <Icon className="w-4 h-4 text-slate-400 dark:text-slate-600 flex-shrink-0" />
                    )}
                    <span className="truncate">{step.label}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Action Button */}
        <div className="flex items-center justify-center pt-2">
          <button
            onClick={handleStartUpload}
            disabled={!file || uploading}
            className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 px-8 py-3 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs sm:text-sm font-bold rounded-xl shadow-sm transition-all cursor-pointer"
          >
            <span>{uploading ? 'Processing & Extracting Content...' : 'Upload & Process Material'}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* 2. RECENTLY ANALYZED MATERIAL RESULT CARD (Displayed right when analysis completes!) */}
      {uploadedData && (
        <div className="academic-card p-6 sm:p-8 bg-white dark:bg-slate-900 border-2 border-emerald-500/80 dark:border-emerald-500/60 shadow-lg space-y-6 text-center animate-fade-in rounded-2xl relative overflow-hidden">
          
          <div className="absolute top-3 right-3">
            <button
              onClick={() => setUploadedData(null)}
              className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              title="Dismiss analysis card"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="flex flex-col items-center space-y-2">
            <div className="w-14 h-14 rounded-2xl bg-emerald-500 text-white flex items-center justify-center shadow-md">
              {uploadedData.source_type === 'video' ? (
                <Film className="w-7 h-7" />
              ) : uploadedData.source_type === 'presentation' ? (
                <PresentationIcon className="w-7 h-7" />
              ) : (
                <CheckCircle2 className="w-7 h-7" />
              )}
            </div>
            <div className="space-y-1">
              <span className="inline-block uppercase tracking-wider text-3xs font-extrabold px-2.5 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300">
                ✓ Analysis Complete &amp; Indexed
              </span>
              <h2 className="text-lg sm:text-xl font-extrabold text-slate-900 dark:text-white">
                {uploadedData.title}
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400 max-w-lg mx-auto">
                Extracted multimodal knowledge, structured chapters, and generated concept graph provenance.
              </p>
            </div>
          </div>

          {/* Quick Stats Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 max-w-xl mx-auto text-left">
            <div className="p-3 bg-slate-50 dark:bg-slate-800/80 rounded-xl border border-slate-200 dark:border-slate-700">
              <p className="text-3xs font-semibold text-slate-500 dark:text-slate-400 uppercase">Format</p>
              <p className="text-xs font-bold text-slate-900 dark:text-slate-100 uppercase mt-0.5">
                {uploadedData.source_type || 'PDF Document'}
              </p>
            </div>
            <div className="p-3 bg-slate-50 dark:bg-slate-800/80 rounded-xl border border-slate-200 dark:border-slate-700">
              <p className="text-3xs font-semibold text-slate-500 dark:text-slate-400 uppercase">
                {uploadedData.source_type === 'presentation' ? 'Total Slides' : (uploadedData.source_type === 'video' ? 'Duration' : 'Total Pages')}
              </p>
              <p className="text-xs font-bold text-slate-900 dark:text-slate-100 mt-0.5">
                {uploadedData.source_type === 'presentation'
                  ? `${uploadedData.total_slides || uploadedData.total_pages} Slides`
                  : (uploadedData.source_type === 'video'
                    ? (uploadedData.duration_str || `${Math.round(uploadedData.duration_seconds || 0)}s`)
                    : `${uploadedData.total_pages} Pages`)}
              </p>
            </div>
            <div className="p-3 bg-slate-50 dark:bg-slate-800/80 rounded-xl border border-slate-200 dark:border-slate-700">
              <p className="text-3xs font-semibold text-slate-500 dark:text-slate-400 uppercase">File Size</p>
              <p className="text-xs font-bold text-slate-900 dark:text-slate-100 mt-0.5">
                {(uploadedData.file_size_bytes / (1024 * 1024)).toFixed(1)} MB
              </p>
            </div>
            <div className="p-3 bg-slate-50 dark:bg-slate-800/80 rounded-xl border border-slate-200 dark:border-slate-700">
              <p className="text-3xs font-semibold text-slate-500 dark:text-slate-400 uppercase">
                {uploadedData.source_type === 'video' ? 'Lecture Parts' : 'Chapters'}
              </p>
              <p className="text-xs font-bold text-slate-900 dark:text-slate-100 mt-0.5">
                {uploadedData.chapters?.length || 1} {uploadedData.source_type === 'video' ? 'Parts' : 'Chapters'}
              </p>
            </div>
          </div>

          {/* Action: Open in Workspace & Quick Learning Links */}
          <div className="space-y-4 pt-2">
            <button
              onClick={() => handleOpenWorkspaceTab('summary')}
              className="inline-flex items-center space-x-2 px-8 py-3.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-sm rounded-xl shadow-md transition-all cursor-pointer"
            >
              <span>Open in Course Workspace &rarr;</span>
              <ArrowRight className="w-4 h-4" />
            </button>

            {/* Direct Tool Launchers */}
            <div className="flex flex-wrap items-center justify-center gap-2 pt-2 border-t border-slate-100 dark:border-slate-800 text-xs">
              <span className="text-3xs font-bold text-slate-400 uppercase mr-1">Study Direct:</span>
              <button
                onClick={() => handleOpenWorkspaceTab('summary')}
                className="px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-indigo-50 dark:hover:bg-indigo-950/60 text-slate-700 dark:text-slate-300 hover:text-indigo-600 font-semibold transition-colors flex items-center space-x-1"
              >
                <FileText className="w-3.5 h-3.5" />
                <span>Chapter Summary</span>
              </button>
              <button
                onClick={() => handleOpenWorkspaceTab('graph')}
                className="px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-indigo-50 dark:hover:bg-indigo-950/60 text-slate-700 dark:text-slate-300 hover:text-indigo-600 font-semibold transition-colors flex items-center space-x-1"
              >
                <Network className="w-3.5 h-3.5" />
                <span>Concept Graph</span>
              </button>
              <button
                onClick={() => handleOpenWorkspaceTab('explain')}
                className="px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-indigo-50 dark:hover:bg-indigo-950/60 text-slate-700 dark:text-slate-300 hover:text-indigo-600 font-semibold transition-colors flex items-center space-x-1"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Adaptive Explain</span>
              </button>
              <button
                onClick={() => handleOpenWorkspaceTab('visualize')}
                className="px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-indigo-50 dark:hover:bg-indigo-950/60 text-slate-700 dark:text-slate-300 hover:text-indigo-600 font-semibold transition-colors flex items-center space-x-1"
              >
                <GitBranch className="w-3.5 h-3.5" />
                <span>Visual Flowcharts</span>
              </button>
              <button
                onClick={() => handleOpenWorkspaceTab('quiz')}
                className="px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-indigo-50 dark:hover:bg-indigo-950/60 text-slate-700 dark:text-slate-300 hover:text-indigo-600 font-semibold transition-colors flex items-center space-x-1"
              >
                <Award className="w-3.5 h-3.5" />
                <span>Quiz Assessment</span>
              </button>
            </div>
          </div>

        </div>
      )}

      {/* 3. RECENTLY INDEXED MATERIALS GALLERY */}
      {textbooks && textbooks.length > 0 && (
        <div className="academic-card p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4 rounded-2xl">
          <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
            <div className="flex items-center space-x-2">
              <BookOpen className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                Indexed Course Materials ({textbooks.length})
              </h3>
            </div>
            <span className="text-3xs text-slate-400">Click any material to study in workspace</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-80 overflow-y-auto custom-scrollbar p-1">
            {textbooks.slice(0, 8).map((tb) => {
              const isCurrent = uploadedData?.id === tb.id;
              return (
                <div
                  key={tb.id}
                  onClick={() => {
                    selectTextbook(tb);
                    handleOpenWorkspaceTab('summary');
                  }}
                  className={`p-3 rounded-xl border cursor-pointer transition-all flex items-start space-x-3 group ${
                    isCurrent
                      ? 'border-indigo-500 bg-indigo-50/40 dark:bg-indigo-950/30 ring-1 ring-indigo-500/30'
                      : 'border-slate-200 dark:border-slate-700 hover:border-indigo-400 bg-slate-50/60 dark:bg-slate-800/50 hover:bg-white dark:hover:bg-slate-800'
                  }`}
                >
                  <div className={`p-2 rounded-lg flex-shrink-0 transition-colors ${
                    tb.source_type === 'video'
                      ? 'bg-rose-100 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400'
                      : tb.source_type === 'presentation'
                        ? 'bg-amber-100 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400'
                        : 'bg-indigo-100 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400'
                  }`}>
                    {tb.source_type === 'video' ? (
                      <Film className="w-4 h-4" />
                    ) : tb.source_type === 'presentation' ? (
                      <PresentationIcon className="w-4 h-4" />
                    ) : (
                      <FileText className="w-4 h-4" />
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <h4 className="text-xs font-bold text-slate-900 dark:text-slate-100 truncate group-hover:text-indigo-600 dark:group-hover:text-indigo-400">
                      {tb.title}
                    </h4>
                    <p className="text-3xs text-slate-400 dark:text-slate-500 font-medium mt-0.5">
                      <span className="uppercase font-bold text-slate-600 dark:text-slate-300">{tb.source_type || 'PDF'}</span> &bull;{' '}
                      {tb.source_type === 'presentation'
                        ? `${tb.total_slides || tb.total_pages || 0} Slides`
                        : tb.source_type === 'video'
                          ? (tb.duration_str || `${Math.round(tb.duration_seconds || 0)}s`)
                          : `${tb.total_pages || 0} Pages`} &bull;{' '}
                      {tb.chapters?.length || 1} Chapters
                    </p>
                  </div>
                  <ArrowRight className="w-3.5 h-3.5 text-slate-300 group-hover:text-indigo-600 self-center flex-shrink-0 transition-colors" />
                </div>
              );
            })}
          </div>
        </div>
      )}

    </div>
  );
};
