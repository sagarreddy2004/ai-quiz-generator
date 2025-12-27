import { useState } from 'react'
import { generateQuiz } from '../services/api'

export default function GenerateForm({ onResult }) {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!url) {
      setErr('Please enter a Wikipedia URL')
      return
    }
    setLoading(true)
    setErr(null)
    try {
      const data = await generateQuiz(url)
      onResult(data, url)
    } catch (e) {
      setErr(String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="max-w-3xl mx-auto p-6 bg-white/80 dark:bg-slate-800/70 backdrop-blur rounded-2xl shadow-lg border border-white/10">
      <div className="flex items-center justify-between mb-3">
        <div>
          <label className="block text-sm font-semibold text-slate-700 dark:text-slate-200">Wikipedia article URL</label>
          <p className="text-xs text-slate-500 dark:text-slate-400">Paste any English Wikipedia article link (or the full URL).</p>
        </div>
        <div className="text-xs text-slate-400">Tip: use a short URL</div>
      </div>

      <div className="flex gap-3 flex-col sm:flex-row">
        <input
          className="flex-1 rounded-lg border border-slate-200 dark:border-slate-700 px-4 py-3 bg-transparent focus:outline-none focus:ring-2 focus:ring-indigo-400"
          placeholder="https://en.wikipedia.org/wiki/Python_(programming_language)"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
        />

        <button
          className="flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-gradient-to-r from-indigo-500 to-indigo-600 text-white font-semibold shadow-md hover:scale-[1.01] transition-transform disabled:opacity-60"
          disabled={loading}
        >
          {loading ? (
            <svg className="w-5 h-5 animate-spin" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
            </svg>
          ) : null}
          {loading ? 'Generating...' : 'Generate Quiz'}
        </button>
      </div>

      {err && <p className="mt-3 text-sm text-red-600">{err}</p>}
    </form>
  )
}
