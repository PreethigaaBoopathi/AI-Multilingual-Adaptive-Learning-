import React from 'react';
import { 
  BookOpen, Sparkles, Brain, GitBranch, ShieldCheck, 
  Layers, Globe, Award, ArrowRight, CheckCircle2, Play 
} from 'lucide-react';

export const LandingPage = ({ onGetStarted, onOpenWorkspace }) => {
  const features = [
    {
      icon: Layers,
      title: "Adaptive Explanations",
      desc: "3-tier explanations tailored for Beginner, Intermediate, and Advanced learners with analogies and zero fluff.",
      badge: "Adaptive Multi-Tier",
      color: "from-emerald-500 to-teal-600"
    },
    {
      icon: GitBranch,
      title: "Visual Flowcharts & Diagrams",
      desc: "Transforms dense paragraphs into interactive, editable Mermaid.js state machines, cycles, and trees.",
      badge: "Interactive Visuals",
      color: "from-indigo-500 to-blue-600"
    },
    {
      icon: ShieldCheck,
      title: "Grounded RAG Q&A",
      desc: "Zero hallucinations. Answers strictly cite chapter, section, and page numbers directly from your uploaded PDF.",
      badge: "Strict Citations",
      color: "from-purple-500 to-indigo-600"
    },
    {
      icon: Award,
      title: "AI Diagnostic Quizzes",
      desc: "Generates grounded MCQs, detects conceptual weak topics, and provides targeted remediation modules.",
      badge: "Adaptive Mastery",
      color: "from-amber-500 to-orange-600"
    },
    {
      icon: Globe,
      title: "Multilingual (Tamil & English)",
      desc: "Instant language switching between English and Tamil for summaries, explanations, and key concepts.",
      badge: "Dual Language",
      color: "from-blue-500 to-cyan-600"
    },
    {
      icon: Brain,
      title: "Personalized Recommendations",
      desc: "Dynamic student dashboard tracking topic mastery percentages and prescribing high-yield review drills.",
      badge: "Targeted Growth",
      color: "from-rose-500 to-pink-600"
    }
  ];

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex flex-col transition-colors duration-200">
      {/* Hero Section */}
      <section className="relative overflow-hidden pt-12 pb-20 sm:pt-16 sm:pb-24 border-b border-slate-200/80 dark:border-slate-800/80 bg-white dark:bg-slate-900/50">
        <div className="absolute inset-0 bg-[radial-gradient(#e0e7ff_1px,transparent_1px)] dark:bg-[radial-gradient(#312e81_1px,transparent_1px)] [background-size:20px_20px] opacity-50"></div>
        
        <div className="relative max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center space-y-6">
          
          <div className="inline-flex items-center space-x-2 bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200/80 dark:border-indigo-800/80 px-4 py-1.5 rounded-full text-xs font-bold text-indigo-700 dark:text-indigo-300 shadow-2xs">
            <Sparkles className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400 animate-pulse" />
            <span>TextIQ &bull; Next-Gen Multilingual Textbook Intelligence</span>
          </div>

          <h1 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-slate-950 dark:text-white leading-[1.15]">
            Turn Your Textbook Into an <br />
            <span className="bg-gradient-to-r from-indigo-600 via-indigo-700 to-emerald-600 dark:from-indigo-400 dark:via-indigo-300 dark:to-emerald-400 bg-clip-text text-transparent">
              Interactive Learning Experience
            </span>
          </h1>

          <p className="text-base sm:text-lg text-slate-600 dark:text-slate-300 max-w-3xl mx-auto leading-relaxed font-normal">
            Summarize, understand, visualize and master your textbook with AI. Solve one-size-fits-all explanations with 3-tier adaptive models, dense paragraphs with interactive Mermaid.js diagrams, and retain mastery with grounded RAG Q&A.
          </p>

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-4">
            <button
              onClick={onGetStarted}
              className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 px-8 py-3.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-sm rounded-xl shadow-md hover:shadow-indigo-500/25 transition-all duration-150"
            >
              <span>Get Started</span>
              <ArrowRight className="w-4 h-4" />
            </button>
            <button
              onClick={onOpenWorkspace}
              className="w-full sm:w-auto inline-flex items-center justify-center space-x-2 px-6 py-3.5 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 font-bold text-sm rounded-xl border border-slate-200 dark:border-slate-700 transition-all duration-150"
            >
              <Play className="w-4 h-4 text-indigo-600 dark:text-indigo-400 fill-indigo-600 dark:fill-indigo-400" />
              <span>Try Live Demo Textbook</span>
            </button>
          </div>

          {/* Key Metrics Strip */}
          <div className="pt-10 grid grid-cols-2 sm:grid-cols-4 gap-4 max-w-3xl mx-auto border-t border-slate-100 dark:border-slate-800 text-left">
            <div className="p-3 bg-slate-50 dark:bg-slate-800/60 rounded-xl border border-slate-200/80 dark:border-slate-700/80">
              <p className="text-xl font-extrabold text-indigo-600 dark:text-indigo-400">3 Tiers</p>
              <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">Beginner to Advanced</p>
            </div>
            <div className="p-3 bg-slate-50 dark:bg-slate-800/60 rounded-xl border border-slate-200/80 dark:border-slate-700/80">
              <p className="text-xl font-extrabold text-emerald-600 dark:text-emerald-400">Mermaid.js</p>
              <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">Interactive Visuals</p>
            </div>
            <div className="p-3 bg-slate-50 dark:bg-slate-800/60 rounded-xl border border-slate-200/80 dark:border-slate-700/80">
              <p className="text-xl font-extrabold text-purple-600 dark:text-purple-400">100% Grounded</p>
              <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">Page Citations</p>
            </div>
            <div className="p-3 bg-slate-50 dark:bg-slate-800/60 rounded-xl border border-slate-200/80 dark:border-slate-700/80">
              <p className="text-xl font-extrabold text-blue-600 dark:text-blue-400">EN + தமிழ்</p>
              <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">Dual Language</p>
            </div>
          </div>

        </div>
      </section>

      {/* Core Problems Addressed Section */}
      <section className="py-16 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-2xl mx-auto mb-12 space-y-2">
          <h2 className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-white tracking-tight">
            Engineered for Deep Comprehension & Verified Retention
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400">
            A specialized academic architecture designed for students, educators, and lifelong learners.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((f, i) => {
            const Icon = f.icon;
            return (
              <div key={i} className="academic-card p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 flex flex-col justify-between group rounded-xl">
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <div className={`w-10 h-10 rounded-xl bg-gradient-to-tr ${f.color} flex items-center justify-center text-white shadow-sm`}>
                      <Icon className="w-5 h-5" />
                    </div>
                    <span className="text-[10px] font-extrabold uppercase px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                      {f.badge}
                    </span>
                  </div>
                  <h3 className="text-base font-bold text-slate-900 dark:text-white mb-2 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                    {f.title}
                  </h3>
                  <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                    {f.desc}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Workflow Step Progression */}
      <section className="py-16 bg-white dark:bg-slate-900/60 border-t border-slate-200/80 dark:border-slate-800">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-white">End-to-End System Workflow</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">From raw textbook PDF upload to personalized remediation</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-4 bg-slate-50 dark:bg-slate-800/80 rounded-xl border border-slate-200 dark:border-slate-700/80 text-left space-y-2">
              <span className="w-6 h-6 rounded-md bg-indigo-600 text-white font-bold text-xs flex items-center justify-center">1</span>
              <h4 className="font-bold text-xs text-slate-900 dark:text-slate-100">Upload PDF</h4>
              <p className="text-3xs text-slate-600 dark:text-slate-400">PyMuPDF extracts chapters, cleans tables, and creates indexed chunks.</p>
            </div>
            <div className="p-4 bg-slate-50 dark:bg-slate-800/80 rounded-xl border border-slate-200 dark:border-slate-700/80 text-left space-y-2">
              <span className="w-6 h-6 rounded-md bg-indigo-600 text-white font-bold text-xs flex items-center justify-center">2</span>
              <h4 className="font-bold text-xs text-slate-900 dark:text-slate-100">Adaptive Synthesis</h4>
              <p className="text-3xs text-slate-600 dark:text-slate-400">Select Beginner, Intermediate, or Advanced for tailored explanations & flowcharts.</p>
            </div>
            <div className="p-4 bg-slate-50 dark:bg-slate-800/80 rounded-xl border border-slate-200 dark:border-slate-700/80 text-left space-y-2">
              <span className="w-6 h-6 rounded-md bg-indigo-600 text-white font-bold text-xs flex items-center justify-center">3</span>
              <h4 className="font-bold text-xs text-slate-900 dark:text-slate-100">Grounded Q&A & Quiz</h4>
              <p className="text-3xs text-slate-600 dark:text-slate-400">Ask questions with page citations and take AI diagnostic MCQs.</p>
            </div>
            <div className="p-4 bg-slate-50 dark:bg-slate-800/80 rounded-xl border border-slate-200 dark:border-slate-700/80 text-left space-y-2">
              <span className="w-6 h-6 rounded-md bg-emerald-600 text-white font-bold text-xs flex items-center justify-center">4</span>
              <h4 className="font-bold text-xs text-slate-900 dark:text-slate-100">Weakness Remediation</h4>
              <p className="text-3xs text-slate-600 dark:text-slate-400">Detects topics &lt; 60% and automatically prescribes targeted revision packs.</p>
            </div>
          </div>

          {/* Bottom CTA */}
          <div className="mt-12 text-center">
            <button
              onClick={onOpenWorkspace}
              className="inline-flex items-center space-x-2 px-8 py-3.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-sm rounded-xl shadow-md hover:shadow-indigo-500/25 transition-all"
            >
              <span>Launch Interactive Workspace</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="mt-auto py-8 bg-slate-900 dark:bg-slate-950 text-slate-400 text-center text-xs border-t border-slate-800">
        <p className="font-semibold text-slate-300 dark:text-slate-300">
          TextIQ &bull; Multilingual Textbook Summarization & Adaptive Learning System
        </p>
        <p className="text-3xs text-slate-500 dark:text-slate-500 mt-1">
          FastAPI &bull; React &bull; Tailwind CSS &bull; Mermaid.js &bull; RAG Embeddings
        </p>
      </footer>
    </div>
  );
};
