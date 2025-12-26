import { useState } from 'react'
import { generateQuiz } from '../services/api'

export default function GenerateForm({ onResult }) {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setErr(null)
    try {
      const data = await generateQuiz(url)
      onResult(data)
    } catch (e) {
      setErr(String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3 max-w-xl mx-auto p-4">
      <label className="block text-sm font-medium">Wikipedia article URL</label>
      <input
        className="w-full border rounded px-3 py-2"
        placeholder="https://en.wikipedia.org/wiki/Python_(programming_language)"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
      />
      <div className="flex gap-2">
        <button className="px-3 py-1 bg-blue-600 text-white rounded" disabled={loading}>
          {loading ? 'Generating...' : 'Generate Quiz'}
        </button>
      </div>
      {err && <p className="text-red-600">{err}</p>}
    </form>
  )
}
