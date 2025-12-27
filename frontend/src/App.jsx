import { useState, useEffect } from 'react'
import './App.css'
import GenerateForm from './components/GenerateForm'
import { generateQuiz as apiGenerateQuiz } from './services/api'

function App() {
  const [quiz, setQuiz] = useState(null)
  const [quizUrl, setQuizUrl] = useState(null)
  const [generating, setGenerating] = useState(false)
  const [selected, setSelected] = useState([])
  const [submitted, setSubmitted] = useState(false)
  const [score, setScore] = useState(null)
  const [formKey, setFormKey] = useState(0) // used to remount form when asking new article

  // reset selection state whenever a new quiz is loaded
  useEffect(() => {
    if (quiz?.questions) {
      setSelected(Array(quiz.questions.length).fill(null))
      setSubmitted(false)
      setScore(null)
    }
  }, [quiz])

  function handleSelect(qIdx, option) {
    if (submitted) return
    setSelected((s) => {
      const next = [...s]
      next[qIdx] = option
      return next
    })
  }

  function handleSubmitQuiz() {
    if (!quiz?.questions) return
    const unanswered = selected.filter((s) => !s).length
    if (unanswered > 0) {
      const proceed = window.confirm(
        `You have ${unanswered} unanswered question${unanswered > 1 ? 's' : ''}.\n\nPress OK to submit anyway, or Cancel to review your answers.`
      )
      if (!proceed) return
    }

    const total = quiz.questions.length
    let correct = 0
    for (let i = 0; i < total; i++) {
      const q = quiz.questions[i]
      if (!q) continue
      if (selected[i] && selected[i] === q.answer) correct++
    }
    // scale to score out of 10
    const scaled = Math.round((correct / Math.max(1, total)) * 10)
    setScore(scaled)
    setSubmitted(true)
  }

  function handleRetake() {
    setSelected(Array(quiz.questions.length).fill(null))
    setSubmitted(false)
    setScore(null)
  }

  function handleNewArticle() {
    setQuiz(null)
    setSelected([])
    setSubmitted(false)
    setScore(null)
    setFormKey((k) => k + 1)
  }

  return (
    <div className="min-h-screen w-full bg-gradient-to-b from-indigo-50 to-white dark:from-slate-900 dark:to-slate-800 text-slate-900 dark:text-slate-100 py-8">
      <header className="max-w-5xl mx-auto text-center mb-6 px-4">
        <div className="inline-block px-4 py-2 rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 text-white shadow-lg">AI • Wiki Quiz</div>
        <h1 className="mt-5 text-3xl sm:text-4xl font-extrabold">AI Wiki Quiz Generator</h1>
        <p className="mt-2 text-slate-600 dark:text-slate-300">Paste a Wikipedia article URL — get a concise practice quiz (answers hidden until submission).</p>
      </header>

      <main className="max-w-5xl mx-auto px-4">
        <GenerateForm key={formKey} onResult={(data, url) => { setQuiz(data); setQuizUrl(url) }} />

        {quiz && (
          <section className="mt-8 p-6 bg-white dark:bg-slate-800/60 rounded-2xl shadow-xl border border-white/10">
            <div className="mb-4">
              <h2 className="text-2xl font-semibold text-slate-800 dark:text-slate-100">{quiz.title || quiz.url}</h2>
              {quiz.summary && <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{quiz.summary}</p>}
            </div>

            <ol className="mt-6 space-y-4">
              {quiz.questions?.map((q, i) => {
                const userAns = selected[i]
                return (
                  <li key={i} className="p-4 rounded-lg border border-white/5 bg-slate-50/60 dark:bg-slate-900/40">
                    <div className="font-medium text-slate-800 dark:text-slate-100">{i + 1}. {q.question}</div>
                    <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {q.options?.map((o, j) => {
                        const isSelected = userAns === o
                        const isCorrect = o === q.answer
                        let classes = 'px-3 py-2 rounded-lg text-sm cursor-pointer select-none'
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
                  </li>
                )
              })}
            </ol>

            <div className="mt-6 flex flex-col sm:flex-row items-center gap-3 justify-between">
              <div className="text-sm text-slate-600 dark:text-slate-300">Answered: {selected.filter(Boolean).length}/{quiz.questions?.length || 0}</div>
              <div className="flex gap-3">
                {!submitted ? (
                  <button
                    className="px-4 py-2 rounded-lg bg-emerald-600 text-white font-semibold disabled:opacity-60"
                    onClick={handleSubmitQuiz}
                  >
                    Submit Answers
                  </button>
                ) : (
                  <div className="flex items-center gap-3">
                    <div className="text-sm font-semibold">Your score: <span className="ml-2 text-indigo-600 dark:text-indigo-300">{score}/10</span></div>
                    <button className="px-3 py-2 rounded-lg bg-indigo-500 text-white" onClick={handleRetake}>Retake</button>
                    <button className="px-3 py-2 rounded-lg bg-slate-200 dark:bg-slate-700" onClick={handleNewArticle}>New Article</button>
                    <button
                      className="px-3 py-2 rounded-lg bg-violet-600 text-white"
                      onClick={async () => {
                        if (!quizUrl) return
                        try {
                          setGenerating(true)
                          const newQuiz = await apiGenerateQuiz(quizUrl)
                          setQuiz(newQuiz)
                          setSelected(Array(newQuiz.questions.length).fill(null))
                          setSubmitted(false)
                          setScore(null)
                        } catch (e) {
                          console.error(e)
                        } finally {
                          setGenerating(false)
                        }
                      }}
                      disabled={generating}
                    >
                      {generating ? 'Generating...' : 'Another Quiz (Same Article)'}
                    </button>
                  </div>
                )}
              </div>
            </div>
          </section>
        )}
      </main>
    </div>
  )
}

export default App
