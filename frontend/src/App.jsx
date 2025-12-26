import { useState } from 'react'
import './App.css'
import GenerateForm from './components/GenerateForm'

function App() {
  const [quiz, setQuiz] = useState(null)

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-slate-100">
      <header className="max-w-4xl mx-auto py-8">
        <h1 className="text-3xl font-bold">AI Wiki Quiz Generator</h1>
        <p className="text-sm text-slate-600 dark:text-slate-400">Enter a Wikipedia URL and generate a quiz.</p>
      </header>
      <main className="max-w-4xl mx-auto">
        <GenerateForm onResult={setQuiz} />

        {quiz && (
          <section className="mt-6 p-4 bg-white dark:bg-slate-800 rounded shadow">
            <h2 className="text-xl font-semibold">{quiz.title || quiz.url}</h2>
            {quiz.summary && <p className="mt-2 text-sm">{quiz.summary}</p>}
            <ol className="mt-4 list-decimal list-inside space-y-3">
              {quiz.questions?.map((q, i) => (
                <li key={i}>
                  <div className="font-medium">{q.question}</div>
                  <ul className="mt-1 ml-4 list-disc">
                    {q.options?.map((o, j) => (
                      <li key={j} className={o === q.answer ? 'font-bold' : ''}>{o}</li>
                    ))}
                  </ul>
                </li>
              ))}
            </ol>
          </section>
        )}
      </main>
    </div>
  )
}

export default App
