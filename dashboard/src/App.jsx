import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  API, getJSON, postJSON, loadPrefs, savePrefs, updateStreak, totalXp, globalLevel,
  presetById, personaFromVibe, PRESETS, MOODS,
} from './lib'
import { Kingdom, World, Quest, Gauntlet, Maps, ModelView, Reflection, Settings } from './views'
import { I18nProvider, useI18n, makeT, detectLocale, LOCALES, LOCALE_NAMES } from './i18n'
import './App.css'

const NAV = [
  { id: 'kingdom', emoji: '🏰', key: 'nav.kingdom' },
  { id: 'quest', emoji: '🐋', key: 'nav.quest' },
  { id: 'gauntlet', emoji: '⚔️', key: 'nav.gauntlet' },
  { id: 'maps', emoji: '🗺️', key: 'nav.maps' },
  { id: 'model', emoji: '🧩', key: 'nav.model' },
  { id: 'reflection', emoji: '📊', key: 'nav.reflection' },
  { id: 'settings', emoji: '⚙️', key: 'nav.settings' },
]

function defaultPrefs() {
  return {
    onboarded: false,
    persona: { preset: 'sage', strict: 0.5, humor: 0.35, auto: false, mood: null },
    chat: [],
    dyslexia: false,
    streak: 0,
    lastDay: null,
  }
}

export default function App() {
  const [view, setView] = useState('kingdom')
  const [selectedSyllabus, setSelectedSyllabus] = useState(null)
  const [syllabi, setSyllabi] = useState([])
  const [details, setDetails] = useState({})
  const [progress, setProgress] = useState([])
  const [analytics, setAnalytics] = useState(null)
  const [exams, setExams] = useState([])
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [error, setError] = useState(null)
  const [prefs, setPrefsState] = useState(() => ({ ...defaultPrefs(), ...loadPrefs() }))
  const [locale, setLocaleState] = useState(() => loadPrefs().locale || detectLocale())
  const [chatPrefill, setChatPrefill] = useState(null)

  const t = useMemo(() => makeT(locale), [locale])
  const setLocale = useCallback((l) => {
    setLocaleState(l)
    setPrefsState((prev) => savePrefs({ ...prev, locale: l }))
  }, [])
  const i18n = useMemo(() => ({ locale, t, setLocale }), [locale, t, setLocale])

  const updatePrefs = useCallback((updater) => {
    setPrefsState((prev) => {
      const next = typeof updater === 'function' ? updater(prev) : updater
      savePrefs(next)
      return next
    })
  }, [])

  // Count today's visit toward the streak exactly once per mount.
  useEffect(() => {
    setPrefsState((prev) => {
      const next = updateStreak(prev)
      savePrefs(next)
      return next
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const loadOverview = useCallback(async () => {
    setLoading(true)
    setError(null)
    let syllabiList
    try {
      syllabiList = await getJSON(`${API}/syllabi`)
    } catch (err) {
      setError(`Cannot reach the tutor API (${err.message}). Is the backend running? (python tutor_dashboard.py)`)
      setSyllabi([]); setProgress([]); setExams([]); setAnalytics(null); setSummary(null); setDetails({})
      setLoading(false)
      return
    }
    syllabiList = Array.isArray(syllabiList) ? syllabiList : []
    const [prog, an, ex, sum] = await Promise.all([
      getJSON(`${API}/progress`).catch(() => []),
      getJSON(`${API}/analytics`).catch(() => null),
      getJSON(`${API}/exams`).catch(() => []),
      getJSON(`${API}/analytics/summary`).catch(() => null),
    ])
    setSyllabi(syllabiList)
    setProgress(Array.isArray(prog) ? prog : [])
    setAnalytics(an)
    setExams(Array.isArray(ex) ? ex : [])
    setSummary(sum)

    const detailEntries = await Promise.all(
      syllabiList.map(async (s) => {
        try { return [s.id, await getJSON(`${API}/syllabi/${s.id}`)] }
        catch { return [s.id, null] }
      }),
    )
    setDetails(Object.fromEntries(detailEntries))
    setLoading(false)
  }, [])

  useEffect(() => { loadOverview() }, [loadOverview])

  const syncNow = async () => {
    setSyncing(true)
    setError(null)
    try {
      await postJSON(`${API}/sync`)
      await loadOverview()
    } catch (err) {
      setError(err.message)
    } finally {
      setSyncing(false)
    }
  }

  const persona = useMemo(() => {
    const p = prefs.persona || {}
    return {
      preset: p.preset || 'sage',
      strict: p.strict ?? 0.5,
      humor: p.humor ?? 0.35,
      auto: !!p.auto,
      mood: p.mood || null,
    }
  }, [prefs.persona])

  const xp = useMemo(() => totalXp(progress), [progress])
  const level = useMemo(() => globalLevel(progress), [progress])

  function navigate(v, opts = {}) {
    if (v === 'world' && opts.syllabusId) {
      const s = syllabi.find((x) => x.id === opts.syllabusId)
      if (s) { setSelectedSyllabus(s); setView('world') }
      else { setSelectedSyllabus(null); setView('kingdom') }
    } else {
      setSelectedSyllabus(null)
      setView(v)
    }
    if (opts.prefill) setChatPrefill(opts.prefill)
  }
  function enterWorld(s) { setSelectedSyllabus(s); setView('world') }
  function finishOnboarding(result) {
    updatePrefs({ ...prefs, onboarded: true, persona: { ...prefs.persona, ...result } })
  }

  const selectedDetail = selectedSyllabus ? details[selectedSyllabus.id] : null
  const selectedProgress = selectedSyllabus
    ? progress.find((p) => p.syllabus_id === selectedSyllabus.id)
    : null
  const selectedExams = selectedSyllabus
    ? exams.filter((e) => e.syllabus_id === selectedSyllabus.id)
    : []

  return (
    <I18nProvider value={i18n}>
      {!prefs.onboarded ? (
        <Onboarding onDone={finishOnboarding} />
      ) : (
        <div className={`app ${prefs.dyslexia ? 'dyslexic' : ''}`}>
          <header className="app-header">
            <div className="brand" onClick={() => navigate('kingdom')} role="button" tabIndex={0}>
              <span className="brand-emoji">🐋</span>
              <span className="brand-name">Knowledge Quest Academy</span>
            </div>

            <nav className="header-nav">
              {NAV.map((n) => (
                <button
                  key={n.id}
                  className={view === n.id ? 'active' : ''}
                  onClick={() => navigate(n.id)}
                  title={t(n.key)}
                >
                  <span className="nav-emoji">{n.emoji}</span>
                  <span className="nav-label">{t(n.key)}</span>
                </button>
              ))}
            </nav>

            <div className="header-tools">
              <div className="header-badges">
                <span className="badge" title={t('header.streak')}>🔥 {prefs.streak || 0}</span>
                <span className="badge" title={t('header.xp')}>✨ {xp}</span>
              </div>
              <select
                className="lang-select"
                value={locale}
                onChange={(e) => setLocale(e.target.value)}
                title={t('header.language')}
              >
                {LOCALES.map((l) => <option key={l} value={l}>{LOCALE_NAMES[l]}</option>)}
              </select>
              <button
                className={`tool-btn ${prefs.dyslexia ? 'active' : ''}`}
                onClick={() => updatePrefs((p) => ({ ...p, dyslexia: !p.dyslexia }))}
                title={t('header.dyslexia')}
              >
                🦋
              </button>
              <PersonaWidget persona={persona} onChange={(patch) => updatePrefs((p) => ({ ...p, persona: { ...p.persona, ...patch } }))} />
              <button className="tool-btn sync" onClick={syncNow} disabled={syncing} title={t('header.sync')}>
                {syncing ? '⟳' : '🔄'}
              </button>
            </div>
          </header>

          <main className="app-main">
            {error && (
              <div className="error-banner">
                ⚠️ {error}
                {!loading && <button className="btn small ghost" onClick={loadOverview}>{t('common.retry')}</button>}
              </div>
            )}

            {loading && <div className="loading">{t('common.loading')}</div>}

            {!loading && view === 'kingdom' && (
              <Kingdom
                syllabi={syllabi} details={details} progress={progress} exams={exams} summary={summary}
                streak={prefs.streak || 0} xp={xp} level={level}
                loading={loading} onEnterWorld={enterWorld} onNavigate={navigate}
              />
            )}
            {!loading && view === 'world' && selectedSyllabus && (
              <World
                syllabus={selectedSyllabus} detail={selectedDetail} progress={selectedProgress}
                exams={selectedExams} onBack={() => navigate('kingdom')} onNavigate={navigate}
              />
            )}
            {!loading && view === 'quest' && (
              <Quest
                syllabi={syllabi} progress={progress} exams={exams}
                prefs={prefs} setPrefs={updatePrefs} persona={persona}
                loading={loading} onNavigate={navigate}
                chatPrefill={chatPrefill} onConsumePrefill={() => setChatPrefill(null)}
              />
            )}
            {!loading && view === 'gauntlet' && <Gauntlet exams={exams} syllabi={syllabi} />}
            {!loading && view === 'maps' && <Maps syllabi={syllabi} details={details} />}
            {!loading && view === 'model' && <ModelView syllabi={syllabi} progress={progress} />}
            {!loading && view === 'reflection' && <Reflection progress={progress} analytics={analytics} summary={summary} />}
            {!loading && view === 'settings' && <Settings syllabi={syllabi} onChanged={loadOverview} />}
          </main>
        </div>
      )}
    </I18nProvider>
  )
}

// ---------------------------------------------------------------- persona widget

function PersonaWidget({ persona, onChange }) {
  const { t } = useI18n()
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    if (!open) return
    function onDoc(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [open])

  const preset = presetById(persona.preset)
  const moodEmoji = persona.mood ? MOODS.find((m) => m.id === persona.mood)?.emoji : null

  return (
    <div className="persona" ref={ref}>
      <button className="persona-btn" onClick={() => setOpen((o) => !o)} title={t('header.switchVibe')}>
        <span className="persona-emoji">{moodEmoji || preset.emoji}</span>
        <span className="persona-name">{moodEmoji ? t('persona.dailyMood') : t(`persona.${preset.id}`)}</span>
        <span className="persona-caret">▾</span>
      </button>

      {open && (
        <div className="persona-drop">
          <div className="persona-presets">
            {PRESETS.map((p) => (
              <button
                key={p.id}
                className={`preset ${persona.preset === p.id && !persona.mood ? 'active' : ''}`}
                onClick={() => onChange({ preset: p.id, strict: p.strict, humor: p.humor })}
              >
                <span className="preset-emoji">{p.emoji}</span>
                <span className="preset-name">{t(`persona.${p.id}`)}</span>
                <span className="preset-tag">{t(`persona.${p.id}.tag`)}</span>
              </button>
            ))}
          </div>

          <div className="slider-row">
            <label>
              <span>{t('persona.strictness')}</span>
              <span className="slider-labels"><span>😎 {t('persona.chill')}</span><span>💪 {t('persona.drill')}</span></span>
              <input
                type="range" min="0" max="1" step="0.05"
                value={persona.strict}
                onChange={(e) => onChange({ strict: Number(e.target.value), preset: null })}
              />
            </label>
          </div>
          <div className="slider-row">
            <label>
              <span>{t('persona.humor')}</span>
              <span className="slider-labels"><span>📚 {t('persona.serious')}</span><span>🤡 {t('persona.joker')}</span></span>
              <input
                type="range" min="0" max="1" step="0.05"
                value={persona.humor}
                onChange={(e) => onChange({ humor: Number(e.target.value), preset: null })}
              />
            </label>
          </div>

          <label className="auto-row">
            <input
              type="checkbox"
              checked={persona.auto}
              onChange={(e) => onChange({ auto: e.target.checked })}
            />
            <span>{t('persona.auto')}</span>
          </label>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------- onboarding

function Onboarding({ onDone }) {
  const { t } = useI18n()
  const [step, setStep] = useState(0)
  const [vibe, setVibe] = useState(null)
  const [stuck, setStuck] = useState(null)

  function chooseVibe(v) { setVibe(v); setStep(1) }
  function chooseStuck(s) {
    const result = personaFromVibe(vibe, s)
    onDone(result)
  }

  return (
    <div className="onboarding">
      <div className="onboard-card">
        <div className="onboard-mascot">🐋</div>
        <h1>{t('onboard.title')}</h1>
        <p className="onboard-sub">{t('onboard.sub')}</p>

        {step === 0 && (
          <div className="onboard-step">
            <h2>{t('onboard.vibe')}</h2>
            <div className="onboard-choices">
              <button className="choice" onClick={() => chooseVibe('hard')}>
                <span className="choice-emoji">🏋️</span>
                <span className="choice-title">{t('onboard.vibe.hard.title')}</span>
                <span className="choice-sub">{t('onboard.vibe.hard.sub')}</span>
              </button>
              <button className="choice" onClick={() => chooseVibe('soft')}>
                <span className="choice-emoji">🧘</span>
                <span className="choice-title">{t('onboard.vibe.soft.title')}</span>
                <span className="choice-sub">{t('onboard.vibe.soft.sub')}</span>
              </button>
            </div>
          </div>
        )}

        {step === 1 && (
          <div className="onboard-step">
            <h2>{t('onboard.stuck')}</h2>
            <div className="onboard-choices">
              <button className="choice" onClick={() => chooseStuck('think')}>
                <span className="choice-emoji">🧠</span>
                <span className="choice-title">{t('onboard.stuck.think.title')}</span>
                <span className="choice-sub">{t('onboard.stuck.think.sub')}</span>
              </button>
              <button className="choice" onClick={() => chooseStuck('tell')}>
                <span className="choice-emoji">💡</span>
                <span className="choice-title">{t('onboard.stuck.tell.title')}</span>
                <span className="choice-sub">{t('onboard.stuck.tell.sub')}</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
