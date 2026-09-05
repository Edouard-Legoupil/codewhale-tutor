import { useCallback, useEffect, useState } from 'react'

const API = '/api'

function pct(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—'
  return `${Math.round(Number(value) * 100)}%`
}

function fmtDate(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString()
}

async function getJSON(url) {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export default function App() {
  const [view, setView] = useState('overview')
  const [students, setStudents] = useState([])
  const [summary, setSummary] = useState(null)
  const [exams, setExams] = useState([])
  const [selectedStudent, setSelectedStudent] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const loadOverview = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [s, sum, e] = await Promise.all([
        getJSON(`${API}/students`),
        getJSON(`${API}/analytics/summary`).catch(() => null),
        getJSON(`${API}/exams`).catch(() => []),
      ])
      setStudents(Array.isArray(s) ? s : [])
      setSummary(sum)
      setExams(Array.isArray(e) ? e : [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadOverview()
  }, [loadOverview])

  const openStudent = (student) => {
    setSelectedStudent(student)
    setView('student')
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>🧠 Tutor Dashboard</h1>
        <nav className="header-nav">
          <button onClick={() => { setSelectedStudent(null); setView('overview') }}>Overview</button>
          <button onClick={() => setView('exams')}>Exams</button>
          <button onClick={loadOverview}>Refresh</button>
        </nav>
      </header>

      <main className="app-main">
        {loading && <div className="loading">Loading…</div>}
        {error && <div className="weakness-section">⚠️ {error} — is the backend running? (python tutor_dashboard.py)</div>}

        {!loading && view === 'overview' && (
          <div className="dashboard">
            {summary && (
              <div className="stats-grid">
                <StatCard label="Students" value={summary.total_students} />
                <StatCard label="Syllabi" value={summary.total_syllabi} />
                <StatCard label="Exams" value={summary.total_exams} />
                <StatCard label="Learning rate" value={pct(summary.avg_learning_rate)} />
              </div>
            )}

            <div className="students-section">
              <h3>Students</h3>
              {students.length === 0 ? (
                <p className="loading">No students yet. Complete a tutoring session to populate progress data.</p>
              ) : (
                <div className="students-grid">
                  {students.map((s) => (
                    <div className="student-card" key={s.student_id} onClick={() => openStudent(s)}>
                      <div className="student-avatar">🎓</div>
                      <div className="student-info">
                        <h4>{s.name}</h4>
                        <p>Style: {s.learning_style}</p>
                        <p>Syllabi: {(s.active_syllabi || []).join(', ') || '—'}</p>
                        <button className="view-btn">View progress</button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {summary && summary.recent_activity && summary.recent_activity.length > 0 && (
              <div className="recent-activity">
                <h3>Recent Activity</h3>
                <div className="activity-list">
                  {summary.recent_activity.map((a, i) => (
                    <div className="activity-item" key={i}>
                      <span className="activity-student">{a.student}</span>
                      <span>{a.concept}</span>
                      <span className="activity-confidence">{a.confidence}% confidence</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {!loading && view === 'student' && selectedStudent && (
          <StudentView student={selectedStudent} onBack={() => setView('overview')} />
        )}

        {!loading && view === 'exams' && <ExamsView exams={exams} />}
      </main>
    </div>
  )
}

function StatCard({ label, value }) {
  return (
    <div className="stat-card">
      <h3>{label}</h3>
      <div className="stat-number">{value}</div>
    </div>
  )
}

function StudentView({ student, onBack }) {
  const [progressList, setProgressList] = useState([])
  const [analytics, setAnalytics] = useState(null)
  const [syllabusId, setSyllabusId] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const [prog, an] = await Promise.all([
          getJSON(`${API}/students/${student.student_id}/progress`),
          getJSON(`${API}/students/${student.student_id}/analytics`).catch(() => null),
        ])
        if (cancelled) return
        const list = Array.isArray(prog) ? prog : [prog]
        setProgressList(list)
        setAnalytics(an)
        if (list.length > 0 && !syllabusId) setSyllabusId(list[0].syllabus_id)
      } catch (err) {
        if (!cancelled) setError(err.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [student.student_id])

  const current = progressList.find((p) => p.syllabus_id === syllabusId) || progressList[0]

  return (
    <div className="student-view">
      <button className="back-btn" onClick={onBack}>← Back</button>
      <h2>🎓 {student.name}</h2>

      {loading && <div className="loading">Loading…</div>}
      {error && <div className="weakness-section">⚠️ {error}</div>}

      {!loading && analytics && (
        <div className="student-stats">
          <StatCard label="Concepts" value={analytics.total_concepts} />
          <StatCard label="Weak concepts" value={analytics.weak_concepts_count} />
          <StatCard label="Sessions" value={analytics.total_sessions} />
          <StatCard label="Learning rate" value={pct(analytics.learning_rate)} />
        </div>
      )}

      {!loading && analytics && (analytics.error_patterns?.length > 0 || analytics.overconfidence > 0) && (
        <div className="chart-card">
          <h3>🔍 Error patterns & calibration</h3>
          {analytics.error_patterns?.length > 0 && (
            <div className="weakness-tags">
              {analytics.error_patterns.map(([t, n]) => (
                <span className="weakness-tag" key={t}>{t}: {n}</span>
              ))}
            </div>
          )}
          {analytics.overconfidence > 0 && (
            <p className="response-text">
              Overconfidence: {pct(analytics.overconfidence)} (predicted confidence above actual accuracy)
            </p>
          )}
          {analytics.attempt_count != null && (
            <p className="response-meta">{analytics.attempt_count} practice attempts recorded</p>
          )}
        </div>
      )}

      {!loading && progressList.length > 0 && (
        <>
          <div className="syllabus-selector">
            {progressList.map((p) => (
              <button
                key={p.syllabus_id}
                className={p.syllabus_id === syllabusId ? 'active' : ''}
                onClick={() => setSyllabusId(p.syllabus_id)}
              >
                {p.syllabus_name || p.syllabus_id}
              </button>
            ))}
          </div>

          {current && (
            <>
              <div className="stats-grid">
                <StatCard label="Stage" value={`${Math.round(current.current_stage || 0)}%`} />
                <StatCard label="Overall mastery" value={pct(current.overall_mastery)} />
                <StatCard label="Sessions" value={current.session_count} />
                <StatCard label="Last session" value={fmtDate(current.last_session)} />
              </div>

              {current.weaknesses && current.weaknesses.length > 0 && (
                <div className="weakness-section">
                  <h3>⚠️ Weaknesses</h3>
                  <div className="weakness-tags">
                    {current.weaknesses.map((w) => (
                      <span className="weakness-tag" key={w}>{w}</span>
                    ))}
                  </div>
                </div>
              )}

              {current.learning_objectives && current.learning_objectives.length > 0 && (
                <div className="chart-card">
                  <h3>🎯 Competencies (Compétences visées)</h3>
                  <div className="responses-list">
                    {current.learning_objectives.map((o, i) => (
                      <div className="response-item" key={i}>
                        <span className="response-concept">{i + 1}.</span> <span className="response-text">{o}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="chart-card">
                <h3>Concept Mastery</h3>
                {(current.concept_mastery || []).map((c) => (
                  <div className="concept-row" key={c.concept}>
                    <span className="concept-name">{c.concept}</span>
                    <div className="concept-bar">
                      <div
                        className="concept-bar-fill"
                        style={{ width: pct(c.mastery) }}
                        data-trend={c.trend}
                      />
                    </div>
                    <span className="concept-value">{pct(c.mastery)}</span>
                  </div>
                ))}
              </div>

              <div className="recent-responses">
                <h3>Recent Responses</h3>
                <div className="responses-list">
                  {(current.response_history || []).slice().reverse().map((r, i) => (
                    <div className="response-item" key={i}>
                      <div className="response-header">
                        <span className="response-concept">{r.concept}</span>
                        <span className="response-confidence">{r.confidence != null ? `${r.confidence}%` : pct(r.mastery)}</span>
                      </div>
                      {r.response && <div className="response-text">{r.response}</div>}
                      <div className="response-meta">{fmtDate(r.timestamp)}</div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </>
      )}
    </div>
  )
}

function ExamsView({ exams }) {
  return (
    <div className="dashboard">
      <h2>📊 Exams</h2>
      {exams.length === 0 ? (
        <p className="loading">No exams analyzed yet.</p>
      ) : (
        <div className="stats-grid">
          {exams.map((e) => (
            <div className="stat-card" key={e.exam_id}>
              <h4>{e.exam_id}</h4>
              <p>Syllabus: {e.syllabus_id}</p>
              <p>Questions: {e.total_questions}</p>
              <p>Avg length: {Math.round(e.avg_question_length || 0)} chars</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
