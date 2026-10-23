import React, { useState } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import {
  setLoading,
  setError,
  sessionInitialized,
  addUserMessage,
  turnCompleted,
  reportLoaded,
  toggleXRay,
  resetSession,
} from './store/interviewSlice';
import { Terminal, Sparkles, Send, ChevronRight, RefreshCw, Cpu, Layers } from 'lucide-react';

const API_BASE = 'http://127.0.0.1:8000/api/v1';

export default function App() {
  const dispatch = useDispatch();
  const {
    step,
    sessionId,
    syllabus,
    currentTopicIdx,
    probeCount,
    messages,
    latestTelemetry,
    reportData,
    showXRay,
    loading,
    error,
  } = useSelector((state) => state.interview);

  // Local form inputs
  const [jobDesc, setJobDesc] = useState(
    'Full-Stack / AI Engineer role requiring React, Redux Toolkit state optimization, FastAPI, and database performance.'
  );
  const [githubUrl, setGithubUrl] = useState('');
  const [resumeFile, setResumeFile] = useState(null);
  const [inputMessage, setInputMessage] = useState('');

  const handleStartInterview = async (e) => {
    e.preventDefault();
    dispatch(setLoading(true));

    const formData = new FormData();
    formData.append('job_description', jobDesc);
    if (githubUrl.trim()) formData.append('github_url', githubUrl.trim());
    if (resumeFile) {
      formData.append('resume_pdf', resumeFile);
    } else {
      formData.append(
        'resume_text_override',
        'Shubham Saha — B.E. CSE at BMSCE. Built Full-Stack Blog Website using React, Redux Toolkit, Tailwind CSS, and Appwrite.'
      );
    }

    try {
      const res = await fetch(`${API_BASE}/session/init`, { method: 'POST', body: formData });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to start interview session');
      dispatch(sessionInitialized(data));
    } catch (err) {
      dispatch(setError(err.message));
    }
  };

  const fetchReport = async (sid) => {
    try {
      const res = await fetch(`${API_BASE}/session/${sid}/report`);
      const data = await res.json();
      dispatch(reportLoaded(data));
    } catch (err) {
      dispatch(setError('Failed to load final diagnostic report'));
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim() || loading) return;

    const answer = inputMessage;
    setInputMessage('');
    dispatch(addUserMessage(answer));
    dispatch(setLoading(true));

    try {
      const res = await fetch(`${API_BASE}/session/${sessionId}/turn`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_answer: answer }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Error evaluating turn');

      dispatch(turnCompleted(data));
      if (data.is_complete) {
        await fetchReport(sessionId);
      }
    } catch (err) {
      dispatch(setError(err.message));
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900/70 backdrop-blur px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="bg-indigo-600 p-2 rounded-lg text-white">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <h1 className="font-bold text-lg tracking-tight flex items-center gap-2">
              ProbeAI
              <span className="text-indigo-400 text-xs font-mono px-2 py-0.5 bg-indigo-950 rounded border border-indigo-800">
                Hybrid RAG + Cross-Encoder + LangGraph
              </span>
            </h1>
            <p className="text-xs text-slate-400">Adaptive Codebase & Technical Mock Interviewer</p>
          </div>
        </div>

        {step === 'interview' && (
          <div className="flex items-center gap-4">
            <span className="text-xs font-mono text-slate-400">
              Topic {Math.min(currentTopicIdx + 1, syllabus.length)} of {syllabus.length}
            </span>
            <button
              onClick={() => dispatch(toggleXRay())}
              className={`text-xs px-3 py-1.5 rounded-md font-medium border transition flex items-center gap-1.5 cursor-pointer ${
                showXRay
                  ? 'bg-indigo-600 text-white border-indigo-500'
                  : 'bg-slate-900 text-slate-300 border-slate-700'
              }`}
            >
              <Terminal className="w-3.5 h-3.5" /> X-Ray Telemetry
            </button>
          </div>
        )}
      </header>

      <main className="flex-1 flex overflow-hidden">
        {/* STEP 1: SETUP */}
        {step === 'setup' && (
          <div className="flex-1 max-w-2xl mx-auto p-8 flex flex-col justify-center">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
              <h2 className="text-xl font-semibold mb-2 flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-indigo-400" /> Configure Your Interview Session
              </h2>
              <p className="text-sm text-slate-400 mb-6">
                Upload your Resume PDF and link a GitHub repository. ProbeAI will build a session-scoped Hybrid RAG index and test your architectural depth.
              </p>

              {error && (
                <div className="bg-red-950/60 border border-red-800 text-red-300 text-sm p-3 rounded-lg mb-4">
                  {error}
                </div>
              )}

              <form onSubmit={handleStartInterview} className="space-y-4">
                <div>
                  <label className="block text-xs font-medium uppercase tracking-wider text-slate-400 mb-1">
                    Target Job Description
                  </label>
                  <textarea
                    rows={3}
                    value={jobDesc}
                    onChange={(e) => setJobDesc(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-sm focus:outline-none focus:border-indigo-500"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium uppercase tracking-wider text-slate-400 mb-1">
                    Public GitHub Repository URL (Optional)
                  </label>
                  <input
                    type="text"
                    value={githubUrl}
                    onChange={(e) => setGithubUrl(e.target.value)}
                    placeholder="https://github.com/username/repo"
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-sm focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium uppercase tracking-wider text-slate-400 mb-1">
                    Resume PDF
                  </label>
                  <input
                    type="file"
                    accept=".pdf"
                    onChange={(e) => setResumeFile(e.target.files[0])}
                    className="w-full text-sm text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-indigo-600 file:text-white hover:file:bg-indigo-500 cursor-pointer"
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-medium py-3 rounded-lg transition flex items-center justify-center gap-2 mt-6 cursor-pointer disabled:opacity-50"
                >
                  {loading ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" /> Indexing Corpus & Generating Syllabus...
                    </>
                  ) : (
                    <>
                      Start Technical Interview <ChevronRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </form>
            </div>
          </div>
        )}

        {/* STEP 2: INTERVIEW WORKSPACE */}
        {step === 'interview' && (
          <>
            <div className="flex-1 flex flex-col bg-slate-950">
              {/* Syllabus Bar */}
              <div className="bg-slate-900/50 border-b border-slate-800 px-6 py-3 flex items-center gap-2 overflow-x-auto">
                {syllabus.map((topic, idx) => (
                  <span
                    key={idx}
                    className={`text-xs px-3 py-1 rounded-full whitespace-nowrap ${
                      idx === currentTopicIdx
                        ? 'bg-indigo-600 text-white font-medium'
                        : idx < currentTopicIdx
                        ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                        : 'bg-slate-900 text-slate-500'
                    }`}
                  >
                    {idx < currentTopicIdx ? '✓ ' : `${idx + 1}. `}
                    {topic}
                  </span>
                ))}
              </div>

              {/* Chat Messages */}
              <div className="flex-1 overflow-y-auto p-6 space-y-4">
                {messages.map((msg, idx) => (
                  <div key={idx} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div
                      className={`max-w-2xl rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                        msg.sender === 'user'
                          ? 'bg-indigo-600 text-white'
                          : 'bg-slate-900 border border-slate-800 text-slate-200'
                      }`}
                    >
                      <p className="whitespace-pre-wrap">{msg.text}</p>
                    </div>
                  </div>
                ))}
                {loading && (
                  <div className="flex justify-start">
                    <div className="bg-slate-900 border border-slate-800 rounded-2xl px-4 py-3 text-sm text-slate-400 flex items-center gap-2">
                      <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" /> Running Hybrid RAG, Cross-Encoder & Pydantic Grader...
                    </div>
                  </div>
                )}
              </div>

              {/* Input Box */}
              <div className="p-4 bg-slate-900 border-t border-slate-800">
                <form onSubmit={handleSendMessage} className="flex gap-3">
                  <input
                    type="text"
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    placeholder="Explain your architecture, trade-offs, and implementation details..."
                    disabled={loading}
                    className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-indigo-500"
                  />
                  <button
                    type="submit"
                    disabled={loading || !inputMessage.trim()}
                    className="bg-indigo-600 hover:bg-indigo-500 text-white px-5 rounded-xl transition flex items-center justify-center disabled:opacity-50 cursor-pointer"
                  >
                    <Send className="w-4 h-4" />
                  </button>
                </form>
              </div>
            </div>

            {/* X-Ray Telemetry Drawer */}
            {showXRay && (
              <div className="w-96 bg-slate-900 border-l border-slate-800 flex flex-col">
                <div className="p-4 border-b border-slate-800 flex items-center justify-between">
                  <h3 className="text-xs font-mono uppercase tracking-wider text-indigo-400 flex items-center gap-1.5">
                    <Layers className="w-4 h-4" /> X-Ray Telemetry
                  </h3>
                  <span className="text-xs font-mono bg-slate-950 px-2 py-0.5 rounded text-slate-400">
                    Probe Depth: {probeCount}/2
                  </span>
                </div>

                <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs font-mono">
                  {latestTelemetry ? (
                    <>
                      <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 space-y-2">
                        <div className="flex justify-between items-center">
                          <span className="text-slate-400">Specificity Score:</span>
                          <span
                            className={`font-bold px-2 py-0.5 rounded ${
                              latestTelemetry.evaluation.specificity_score < 7
                                ? 'bg-red-950 text-red-400'
                                : 'bg-emerald-950 text-emerald-400'
                            }`}
                          >
                            {latestTelemetry.evaluation.specificity_score}/10
                          </span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-slate-400">Router Action:</span>
                          <span className="text-indigo-300 font-semibold">
                            {latestTelemetry.evaluation.routing_decision}
                          </span>
                        </div>
                        {latestTelemetry.evaluation.missed_or_vague_points?.length > 0 && (
                          <div>
                            <p className="text-slate-400 mb-1">Missed / Vague Points:</p>
                            <ul className="list-disc list-inside text-red-300 space-y-0.5">
                              {latestTelemetry.evaluation.missed_or_vague_points.map((pt, i) => (
                                <li key={i}>{pt}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>

                      <div className="space-y-2">
                        <p className="text-slate-400 uppercase tracking-wider text-[10px]">
                          Reranked Chunks (BM25 + Vector → Cross-Encoder)
                        </p>
                        {latestTelemetry.retrieved_chunks.map((chunk, idx) => (
                          <div key={idx} className="bg-slate-950 border border-slate-800 rounded-lg p-2.5 space-y-1">
                            <div className="flex justify-between text-[10px] text-slate-300">
                              <span className="truncate max-w-[180px]">{chunk.source}</span>
                              <span className="text-indigo-400 font-bold">CE: {chunk.rerank_score}</span>
                            </div>
                            <div className="flex gap-3 text-[10px] text-slate-500">
                              <span>BM25 Rank: #{chunk.bm25_rank ?? 'N/A'}</span>
                              <span>Vector Rank: #{chunk.vector_rank ?? 'N/A'}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </>
                  ) : (
                    <div className="text-center text-slate-500 py-12">
                      Submit an answer to inspect live BM25, Vector, Cross-Encoder, and Pydantic evaluation telemetry.
                    </div>
                  )}
                </div>
              </div>
            )}
          </>
        )}

        {/* STEP 3: FINAL SCORECARD */}
        {step === 'report' && reportData && (
          <div className="flex-1 max-w-3xl mx-auto p-8 overflow-y-auto">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 shadow-2xl space-y-6">
              <div className="flex items-center justify-between border-b border-slate-800 pb-6">
                <div>
                  <h2 className="text-2xl font-bold">Diagnostic Interview Scorecard</h2>
                  <p className="text-sm text-slate-400">Ground-Truth Rubric & Codebase Evaluation</p>
                </div>
                <div className="text-right">
                  <div className="text-3xl font-extrabold text-indigo-400">
                    {reportData.overall_score} <span className="text-sm text-slate-500">/ 10</span>
                  </div>
                  <div className="text-xs text-slate-400 font-mono">Average Specificity</div>
                </div>
              </div>

              <div className="space-y-4">
                {reportData.turn_by_turn_breakdown.map((turn, i) => (
                  <div key={i} className="bg-slate-950 border border-slate-800 rounded-lg p-4 space-y-2">
                    <div className="flex justify-between text-xs font-mono text-slate-400">
                      <span>{turn.topic}</span>
                      <span className={turn.specificity_score < 7 ? 'text-red-400' : 'text-emerald-400'}>
                        Score: {turn.specificity_score}/10 ({turn.routing_decision})
                      </span>
                    </div>
                    <p className="text-sm font-medium text-slate-200">Q: {turn.question}</p>
                    <p className="text-sm text-slate-400 bg-slate-900 p-2.5 rounded">A: {turn.user_answer}</p>
                    {turn.missed_or_vague_points?.length > 0 && (
                      <div className="text-xs text-red-300 bg-red-950/40 p-2 rounded border border-red-900/50">
                        <strong>Gaps Probed:</strong> {turn.missed_or_vague_points.join(' • ')}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              <button
                onClick={() => dispatch(resetSession())}
                className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-medium py-3 rounded-lg transition cursor-pointer"
              >
                Start New Interview Session
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}