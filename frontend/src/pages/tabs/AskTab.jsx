import React, { useState } from 'react';
import { 
  Send, MessageSquare, Sparkles, BookOpen, 
  ShieldCheck, AlertCircle, HelpCircle, Check,
  FileText, Presentation, Video, ExternalLink
} from 'lucide-react';
import { textbookAPI } from '../../services/api';
import { useTextbook } from '../../context/TextbookContext';

export const AskTab = () => {
  const { activeTextbook, language } = useTextbook();
  const [query, setQuery] = useState('');
  const [chatHistory, setChatHistory] = useState([
    {
      type: 'assistant',
      text: 'Hello! I am your Evidence-Grounded Course AI Tutor. Ask me any question about your uploaded course materials (PDFs, PPT slides, lecture videos), and I will answer with verified provenance citations and an anti-hallucination validation layer.',
      citations: [],
      evidence_status: 'fully_grounded',
      is_grounded: true,
      related_concepts: [],
      time: 'Just now'
    }
  ]);
  const [loading, setLoading] = useState(false);



  const handleSendQuery = async (queryText = query) => {
    const textToSend = queryText.trim();
    if (!textToSend || !activeTextbook || loading) return;

    // Add user message to history
    const userMsg = {
      type: 'user',
      text: textToSend,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    setChatHistory(prev => [...prev, userMsg]);
    setQuery('');
    setLoading(true);

    try {
      const response = await textbookAPI.chatWithTextbook(
        activeTextbook.id,
        textToSend,
        language,
        false
      );

      const aiMsg = {
        type: 'assistant',
        text: response.answer,
        citations: response.citations || [],
        evidence_status: response.evidence_status || (response.is_grounded ? 'fully_grounded' : 'unsupported'),
        is_grounded: response.is_grounded,
        confidence: response.confidence,
        related_concepts: response.related_concepts || [],
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setChatHistory(prev => [...prev, aiMsg]);
    } catch (err) {
      console.error('Chat error:', err);
      const errorMsg = {
        type: 'assistant',
        text: 'An error occurred while retrieving course evidence. Please check your connection and try again.',
        citations: [],
        evidence_status: 'unsupported',
        is_grounded: false,
        related_concepts: [],
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setChatHistory(prev => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const renderStatusBadge = (status, isGrounded) => {
    switch (status) {
      case 'fully_grounded':
        return (
          <span className="flex items-center space-x-1 text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/60 px-2 py-0.5 rounded font-medium text-3xs border border-emerald-200 dark:border-emerald-800">
            <ShieldCheck className="w-3 h-3" />
            <span>Fully Grounded</span>
          </span>
        );
      case 'partially_grounded':
        return (
          <span className="flex items-center space-x-1 text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/60 px-2 py-0.5 rounded font-medium text-3xs border border-amber-200 dark:border-amber-800">
            <AlertCircle className="w-3 h-3" />
            <span>Partially Grounded</span>
          </span>
        );
      case 'unsupported':
      default:
        return (
          <span className="flex items-center space-x-1 text-rose-700 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/60 px-2 py-0.5 rounded font-medium text-3xs border border-rose-200 dark:border-rose-800">
            <HelpCircle className="w-3 h-3" />
            <span>Unsupported in Course</span>
          </span>
        );
    }
  };

  const formatProvenanceLabel = (c) => {
    if (c.source_type === 'video' || c.timestamp) {
      return `Timestamp ${c.timestamp || '00:00'}`;
    }
    if (c.source_type === 'presentation' || c.slide) {
      return `Slide ${c.slide || c.page || 1}`;
    }
    return `Page ${c.page || 1}`;
  };

  const getSourceIcon = (sourceType) => {
    switch (sourceType) {
      case 'presentation':
        return <Presentation className="w-3 h-3 text-amber-500" />;
      case 'video':
        return <Video className="w-3 h-3 text-rose-500" />;
      case 'pdf':
      default:
        return <FileText className="w-3 h-3 text-indigo-500" />;
    }
  };

  return (
    <div className="space-y-6 text-slate-900 dark:text-slate-100">
      {/* Header */}
      <div className="pb-4 border-b border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-xl font-bold text-slate-900 dark:text-white">Ask Your Course Materials</h2>
            <span className="text-2xs font-semibold px-2 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
              Evidence-Grounded AI Tutor
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Responses are verified with claim-level validation and exact provenance citations across PDF, PPT, and Lecture Videos.
          </p>
        </div>
      </div>



      {/* Chat Messages Container */}
      <div className="academic-card bg-slate-50/50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 p-4 min-h-[380px] max-h-[520px] overflow-y-auto space-y-4 rounded-xl">
        {chatHistory.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in`}
          >
            <div
              className={`max-w-2xl rounded-xl p-4 text-xs leading-relaxed ${
                msg.type === 'user'
                  ? 'bg-indigo-600 text-white shadow-sm rounded-br-none'
                  : 'bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 border border-slate-200 dark:border-slate-800 shadow-2xs rounded-bl-none space-y-2.5'
              }`}
            >
              {msg.type === 'assistant' && (
                <div className="flex items-center justify-between pb-1.5 mb-1.5 border-b border-slate-100 dark:border-slate-800">
                  <div className="flex items-center space-x-1.5 font-bold text-indigo-700 dark:text-indigo-400">
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>TextIQ AI Tutor</span>
                  </div>
                  {renderStatusBadge(msg.evidence_status, msg.is_grounded)}
                </div>
              )}

              <p className="whitespace-pre-line leading-relaxed">{msg.text}</p>

              {/* Related Concepts from Knowledge Graph */}
              {msg.related_concepts && msg.related_concepts.length > 0 && (
                <div className="mt-2.5 pt-2 border-t border-slate-100 dark:border-slate-800">
                  <span className="text-3xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider block mb-1.5">
                    Related Concepts:
                  </span>
                  <div className="flex flex-wrap gap-1">
                    {msg.related_concepts.map((rc, rIdx) => (
                      <button
                        key={rIdx}
                        onClick={() => {
                          const qStr = `Explain ${rc.name} in detail.`;
                          setQuery(qStr);
                          handleSendQuery(qStr);
                        }}
                        className="px-2 py-0.5 text-3xs rounded-full bg-slate-100 dark:bg-slate-800 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-950/60 border border-slate-200 dark:border-slate-700 transition-colors"
                      >
                        {rc.name}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Citations block */}
              {msg.citations && msg.citations.length > 0 && (
                <div className="mt-3 pt-2 border-t border-slate-100 dark:border-slate-800">
                  <p className="text-3xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1.5">
                    Verified Source Citations:
                  </p>
                  <div className="space-y-1.5">
                    {msg.citations.map((c, cIdx) => (
                      <div key={cIdx} className="bg-slate-50 dark:bg-slate-800/70 p-2.5 rounded border border-slate-200 dark:border-slate-700 text-3xs text-slate-600 dark:text-slate-300">
                        <div className="flex justify-between items-center font-bold text-slate-800 dark:text-slate-200 mb-1">
                          <div className="flex items-center space-x-1.5 truncate max-w-sm">
                            {getSourceIcon(c.source_type)}
                            <span className="truncate">{c.filename || c.chapter}</span>
                            {c.section && c.section !== c.chapter && (
                              <span className="text-slate-400 dark:text-slate-500 truncate">&bull; {c.section}</span>
                            )}
                          </div>
                          <span className="text-indigo-600 dark:text-indigo-400 font-mono text-3xs bg-indigo-50 dark:bg-indigo-950/70 px-1.5 py-0.5 rounded ml-2 whitespace-nowrap">
                            {formatProvenanceLabel(c)}
                          </span>
                        </div>
                        <p className="italic text-slate-600 dark:text-slate-300 leading-relaxed">
                          "{c.excerpt}"
                        </p>
                        {c.media_url && (
                          <div className="mt-1 pt-1 border-t border-slate-200/60 dark:border-slate-700/60 flex items-center space-x-1 text-3xs text-indigo-600 dark:text-indigo-400">
                            <ExternalLink className="w-2.5 h-2.5" />
                            <a 
                              href={`http://localhost:8000${c.media_url}`} 
                              target="_blank" 
                              rel="noopener noreferrer" 
                              className="hover:underline font-medium"
                            >
                              View Figure / Slide Media
                            </a>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className={`text-3xs mt-1 text-right ${msg.type === 'user' ? 'text-indigo-200' : 'text-slate-400 dark:text-slate-500'}`}>
                {msg.time}
              </div>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-white dark:bg-slate-900 p-3 rounded-xl border border-slate-200 dark:border-slate-800 shadow-2xs flex items-center space-x-2 text-xs text-slate-500 dark:text-slate-400">
              <div className="w-4 h-4 border-2 border-indigo-600 dark:border-indigo-400 border-t-transparent rounded-full animate-spin" />
              <span>Retrieving multimodal evidence & running anti-hallucination validation...</span>
            </div>
          </div>
        )}
      </div>

      {/* Query Input Bar */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSendQuery();
        }}
        className="flex items-center space-x-2"
      >
        <div className="relative flex-1">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask a question grounded in this course..."
            className="w-full pl-4 pr-10 py-2.5 text-xs bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-slate-100 rounded-xl shadow-2xs focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 focus:outline-none placeholder-slate-400 dark:placeholder-slate-500"
          />
        </div>
        <button
          type="submit"
          disabled={!query.trim() || loading}
          className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-xl text-xs font-bold shadow-sm transition-all flex items-center space-x-1.5"
        >
          <span>Ask</span>
          <Send className="w-3.5 h-3.5" />
        </button>
      </form>
    </div>
  );
};
