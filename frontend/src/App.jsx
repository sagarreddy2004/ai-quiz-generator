import { useEffect, useState } from 'react'
import './App.css'
import GenerateForm from './components/GenerateForm'
import { generateQuiz as apiGenerateQuiz, getHistory, getQuiz } from './services/api'

function TakeQuizCard({ quiz, quizUrl, onRegenerate, allowRegenerate = false }) {
  const questions = quiz?.quiz || quiz?.questions || []
  const [selected, setSelected] = useState([])
  const [submitted, setSubmitted] = useState(false)
  const [score, setScore] = useState(null)
  const [generating, setGenerating] = useState(false)

  useEffect(() => {
    setSelected(Array(questions.length).fill(null))
    setSubmitted(false)
    setScore(null)
  }, [quiz?.id, questions.length])

  function handleSelect(qIdx, option) {
    if (submitted) return
    setSelected((s) => {
      const next = [...s]
      next[qIdx] = option
      return next
    })
  }

  function handleSubmitQuiz() {
    if (!questions.length) return
    const unanswered = selected.filter((s) => !s).length
    if (unanswered > 0) {
      const proceed = window.confirm(
        `You have ${unanswered} unanswered question${unanswered > 1 ? 's' : ''}.\n\nPress OK to submit anyway, or Cancel to review your answers.`
      )
      if (!proceed) return
    }

    const total = questions.length
    let correct = 0
    for (let i = 0; i < total; i++) {
      const q = questions[i]
      if (!q) continue
      if (selected[i] && selected[i] === q.answer) correct++
    }
    const scaled = Math.round((correct / Math.max(1, total)) * 10)
    setScore(scaled)
    setSubmitted(true)
  }

  function handleRetake() {
    setSelected(Array(questions.length).fill(null))
    setSubmitted(false)
    setScore(null)
  }

  async function handleRegenerate() {
    if (!onRegenerate || !quizUrl) return
    try {
      setGenerating(true)
      await onRegenerate()
    } finally {
      setGenerating(false)
    }
  }

  return (
    <section className="mt-6 p-6 bg-white dark:bg-slate-800/60 rounded-2xl shadow-xl border border-white/10">
      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="inline-flex items-center gap-2 text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">Quiz</div>
          <h2 className="text-2xl font-semibold text-slate-800 dark:text-slate-100">{quiz?.title || quiz?.url || 'Quiz'}</h2>
          {quiz?.summary && <p className="mt-2 text-sm text-slate-600 dark:text-slate-300 max-w-3xl">{quiz.summary}</p>}
        </div>
        {quizUrl && <span className="text-xs text-slate-500 break-all">Source: {quizUrl}</span>}
      </div>

      <ol className="mt-6 space-y-4">
        {questions.map((q, i) => {
          const userAns = selected[i]
          return (
            <li key={i} className="p-4 rounded-lg border border-white/5 bg-slate-50/60 dark:bg-slate-900/40">
              <div className="flex items-start justify-between gap-3">
                <div className="font-medium text-slate-800 dark:text-slate-100">{i + 1}. {q.question}</div>
                <span className="px-2 py-1 text-xs rounded-full bg-slate-200 dark:bg-slate-700 text-slate-800 dark:text-slate-100">{q.difficulty || '—'}</span>
              </div>
              <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3">
                {q.options?.map((o, j) => {
                  const isSelected = userAns === o
                  const isCorrect = o === q.answer
                  let classes = 'px-3 py-2 rounded-lg text-sm cursor-pointer select-none transition-transform'
                  if (submitted) {
                    if (isCorrect) classes += ' bg-green-600 text-white font-semibold'
                    else if (isSelected && !isCorrect) classes += ' bg-red-600 text-white'
                    else classes += ' bg-white/60 dark:bg-slate-800/30 text-slate-700 dark:text-slate-200'
                  } else {
                    classes += isSelected ? ' bg-indigo-500 text-white font-semibold' : ' bg-white/60 dark:bg-slate-800/30 text-slate-700 dark:text-slate-200 hover:scale-[1.01]'
                  }
                  return (
                    <div
                      key={j}
                      className={classes}
                      onClick={() => handleSelect(i, o)}
                      role="button"
                    >
                      {o}
                    </div>
                  )
                })}
              </div>
              {submitted ? (
                <div className="mt-3 text-sm text-slate-600 dark:text-slate-300">
                  <strong>Answer:</strong> {q.answer}
                  {q.explanation ? <span className="block mt-1">Explanation: {q.explanation}</span> : null}
                </div>
              ) : null}
            </li>
          )
        })}
      </ol>

      <div className="mt-6 flex flex-col sm:flex-row items-center gap-3 justify-between">
        <div className="text-sm text-slate-600 dark:text-slate-300">Answered: {selected.filter(Boolean).length}/{questions.length || 0}</div>
        <div className="flex flex-wrap gap-3">
          {!submitted ? (
            <button className="px-4 py-2 rounded-lg bg-emerald-600 text-white font-semibold disabled:opacity-60" onClick={handleSubmitQuiz}>
              Submit Answers
            </button>
          ) : (
            <div className="flex items-center gap-3">
              <div className="text-sm font-semibold">Your score: <span className="ml-2 text-indigo-600 dark:text-indigo-300">{score}/10</span></div>
              <button className="px-3 py-2 rounded-lg bg-indigo-500 text-white" onClick={handleRetake}>Retake</button>
            </div>
          )}
          {allowRegenerate && (
            <button
              className="px-3 py-2 rounded-lg bg-violet-600 text-white disabled:opacity-60"
              onClick={handleRegenerate}
              disabled={generating}
            >
              {generating ? 'Generating...' : 'Another Quiz (Same Article)'}
            </button>
          )}
        </div>
      </div>
    </section>
  )
}

function App() {
  const [activeTab, setActiveTab] = useState('generate')
  const [quiz, setQuiz] = useState(null)
  const [quizUrl, setQuizUrl] = useState(null)
  const [formKey, setFormKey] = useState(0)
  const [history, setHistory] = useState([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyError, setHistoryError] = useState(null)
  const [detailQuiz, setDetailQuiz] = useState(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [detailLoading, setDetailLoading] = useState(false)
  const [showTopics, setShowTopics] = useState(false)

  // Fetch history only when tab is opened (lazy)
  useEffect(() => {
    if (activeTab !== 'history' || history.length) return
    (async () => {
      try {
        setHistoryLoading(true)
        const data = await getHistory()
        setHistory(data)
      } catch (e) {
        setHistoryError(String(e))
      } finally {
        setHistoryLoading(false)
      }
    })()
  }, [activeTab, history.length])

  async function regenerateSameArticle() {
    if (!quizUrl) return
    const newQuiz = await apiGenerateQuiz(quizUrl)
    setQuiz(newQuiz)
  }

  async function openDetails(id) {
    try {
      setDetailLoading(true)
      const data = await getQuiz(id)
      setDetailQuiz({ ...data, id })
      setDetailOpen(true)
    } catch (e) {
      setHistoryError(String(e))
    } finally {
      setDetailLoading(false)
    }
  }

  function resetForm() {
    setQuiz(null)
    setQuizUrl(null)
    setFormKey((k) => k + 1)
  }

  return (
    <div className="min-h-screen w-full bg-gradient-to-b from-indigo-50 to-white dark:from-slate-900 dark:to-slate-800 text-slate-900 dark:text-slate-100 py-8">
      <header className="max-w-6xl mx-auto text-center mb-6 px-4">
        <div className="inline-block px-4 py-2 rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 text-white shadow-lg">AI • Wiki Quiz</div>
        <h1 className="mt-5 text-3xl sm:text-4xl font-extrabold">AI Wiki Quiz Generator</h1>
        <p className="mt-2 text-slate-600 dark:text-slate-300">Paste a Wikipedia article URL — get a quiz with answers, explanations, and related topics.</p>
      </header>

      <main className="max-w-6xl mx-auto px-4">
        <div className="mb-4 flex gap-2">
          <button
            className={`px-4 py-2 rounded-lg border ${activeTab === 'generate' ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white/70 dark:bg-slate-800/60 border-slate-200 dark:border-slate-700'}`}
            onClick={() => setActiveTab('generate')}
          >
            Generate Quiz
          </button>
          <button
            className={`px-4 py-2 rounded-lg border ${activeTab === 'history' ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white/70 dark:bg-slate-800/60 border-slate-200 dark:border-slate-700'}`}
            onClick={() => setActiveTab('history')}
          >
            Past Quizzes
          </button>
        </div>

        {activeTab === 'generate' && (
          <div>
            <GenerateForm
              key={formKey}
              onResult={(data, url) => {
                setQuiz(data)
                setQuizUrl(url)
                setShowTopics(false)
                setActiveTab('generate')
              }}
            />
            {quiz ? (
              <>
                <TakeQuizCard quiz={quiz} quizUrl={quizUrl} onRegenerate={regenerateSameArticle} allowRegenerate />
                <div className="mt-4 flex flex-col gap-3">
                  <div className="flex gap-3 flex-wrap">
                    <button className="px-3 py-2 rounded-lg bg-slate-200 dark:bg-slate-700" onClick={resetForm}>New Article</button>
                    {quiz?.related_topics?.length ? (
                      <button
                        className="px-3 py-2 rounded-lg bg-indigo-600 text-white"
                        onClick={() => setShowTopics((v) => !v)}
                      >
                        {showTopics ? 'Hide related topics' : 'Related topics'} ({quiz.related_topics.length})
                      </button>
                    ) : null}
                  </div>
                  {showTopics && quiz?.related_topics?.length ? (
                    <div className="flex flex-wrap gap-2">
                      {quiz.related_topics.map((t, idx) => {
                        const url = `https://en.wikipedia.org/wiki/${encodeURIComponent(t.replace(/\s+/g, '_'))}`
                        return (
                          <a
                            key={idx}
                            href={url}
                            target="_blank"
                            rel="noreferrer"
                            className="px-2 py-1 rounded-full bg-indigo-100 text-indigo-800 dark:bg-indigo-900/50 dark:text-indigo-100 text-xs hover:underline"
                          >
                            {t}
                          </a>
                        )
                      })}
                    </div>
                  ) : null}
                </div>
              </>
            ) : (
              <p className="mt-6 text-sm text-slate-600 dark:text-slate-400">Submit a Wikipedia URL to generate your first quiz.</p>
            )}
          </div>
        )}

        {activeTab === 'history' && (
          <section className="mt-2 p-4 bg-white dark:bg-slate-800/60 rounded-2xl shadow-xl border border-white/10">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-xl font-semibold">Past quizzes</h2>
              <button className="text-sm text-indigo-600" onClick={async () => { setHistoryLoading(true); try { const data = await getHistory(); setHistory(data); } finally { setHistoryLoading(false); } }}>Refresh</button>
            </div>
            {historyLoading ? <p className="text-sm text-slate-500">Loading history...</p> : null}
            {historyError ? <p className="text-sm text-red-600">{historyError}</p> : null}
            {!historyLoading && history.length === 0 ? (
              <p className="text-sm text-slate-500">No quizzes yet. Generate one in the first tab.</p>
            ) : null}
            {history.length > 0 && (
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead className="text-left text-slate-500">
                    <tr>
                      <th className="py-2 pr-3">Title</th>
                      <th className="py-2 pr-3">URL</th>
                      <th className="py-2 pr-3">Summary</th>
                      <th className="py-2 pr-3">Generated</th>
                      <th className="py-2 pr-3">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((item) => (
                      <tr key={item.id} className="border-t border-slate-100 dark:border-slate-700">
                        <td className="py-2 pr-3 font-semibold text-slate-800 dark:text-slate-100">{item.title || 'Untitled'}</td>
                        <td className="py-2 pr-3 text-slate-600 dark:text-slate-300 max-w-[220px] truncate" title={item.url}>{item.url}</td>
                        <td className="py-2 pr-3 text-slate-600 dark:text-slate-300 max-w-[260px] truncate" title={item.summary}>{item.summary || '—'}</td>
                        <td className="py-2 pr-3 text-slate-600 dark:text-slate-300">{item.date_generated ? new Date(item.date_generated).toLocaleString() : '—'}</td>
                        <td className="py-2 pr-3">
                          <button className="px-3 py-1 rounded-lg bg-indigo-600 text-white text-xs" onClick={() => openDetails(item.id)} disabled={detailLoading}>
                            {detailLoading ? 'Loading...' : 'Details'}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        )}
      </main>

      {detailOpen && detailQuiz ? (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="max-w-5xl w-full bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-white/10 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-4 border-b border-white/10">
              <h3 className="text-lg font-semibold">Quiz details</h3>
              <button className="text-sm text-slate-500" onClick={() => setDetailOpen(false)}>Close</button>
            </div>
            <div className="p-4">
              <TakeQuizCard quiz={detailQuiz} quizUrl={detailQuiz.url} allowRegenerate={false} />
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}

export default App
