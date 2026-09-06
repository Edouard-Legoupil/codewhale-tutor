// Knowledge Quest Academy — shared data helpers, gamification, personas & the local coach.

export const API = '/api'

export async function getJSON(url) {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export async function postJSON(url, body) {
  const res = await fetch(url, {
    method: 'POST',
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export async function putJSON(url, body) {
  const res = await fetch(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export async function delJSON(url) {
  const res = await fetch(url, { method: 'DELETE' })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

// ---------------------------------------------------------------- formatting

export function pct(v) {
  if (v == null || v === '' || Number.isNaN(Number(v))) return '—'
  return `${Math.round(Number(v) * 100)}%`
}

export function int(v) {
  if (v == null || v === '' || Number.isNaN(Number(v))) return '—'
  return `${Math.round(Number(v))}`
}

export function fmtDate(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

export function fmtTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
}

// ---------------------------------------------------------------- gamification

export function masteryStatus(m) {
  return masteryStateInfo(scoreToState(m))
}

export const MASTERY_STATES = [
  { key: 'non_aborde', emoji: '⚪', label: 'Not addressed', cls: 'none' },
  { key: 'en_cours', emoji: '🟡', label: 'In progress', cls: 'learning' },
  { key: 'acquis_avec_aide', emoji: '🟠', label: 'Acquired with help', cls: 'aided' },
  { key: 'acquis', emoji: '🟢', label: 'Acquired', cls: 'mastered' },
  { key: 'maitrise', emoji: '⭐', label: 'Mastered', cls: 'legend' },
]

export function masteryStateInfo(state) {
  return MASTERY_STATES.find((s) => s.key === state) || MASTERY_STATES[0]
}

export function scoreToState(m) {
  if (m == null || Number.isNaN(Number(m))) return 'non_aborde'
  const v = Number(m)
  if (v >= 0.9) return 'maitrise'
  if (v >= 0.7) return 'acquis'
  if (v >= 0.4) return 'en_cours'
  return 'non_aborde'
}

export const ERROR_TYPE_LABELS = {
  knowledge: 'Knowledge',
  representation: 'Representation',
  procedure: 'Procedure',
  execution: 'Execution / calculation',
  interpretation: 'Interpretation',
  reasoning: 'Reasoning',
  strategy: 'Strategy',
  transfer: 'Transfer',
  communication: 'Communication',
}

export function levelFromMastery(m) {
  if (m == null || Number.isNaN(Number(m))) return 1
  return Math.max(1, Math.min(10, Math.round(Number(m) * 10)))
}

export function starsFromMastery(m) {
  if (m == null || Number.isNaN(Number(m))) return 0
  return Math.max(0, Math.min(5, Math.round(Number(m) * 5)))
}

export function stars(n) {
  return '★'.repeat(n) + '☆'.repeat(Math.max(0, 5 - n))
}

const QUEST_THEMES = ['Dungeon', 'Castle', 'Forest', 'Peak', 'Gauntlet', 'Riddle', 'Monster', 'Lab', 'Tower', 'Reef']

export function questTitle(name, idx = 0) {
  if (!name) return 'Start the journey'
  const clean = String(name).trim()
  return `${clean} ${QUEST_THEMES[Math.abs(idx) % QUEST_THEMES.length]}`
}

export function progressForSyllabus(progressList, syllabusId) {
  return (progressList || []).find((p) => p.syllabus_id === syllabusId)
}

export function nextQuestFor(syllabus, detail, progress) {
  if (progress) {
    const weak = (progress.weaknesses || [])[0]
    if (weak) return questTitle(weak)
    const cm = progress.concept_mastery || []
    if (cm.length) {
      const weakest = cm.slice().sort((a, b) => (a.mastery ?? 0) - (b.mastery ?? 0))[0]
      if ((weakest.mastery ?? 1) < 0.7) return questTitle(weakest.concept)
    }
  }
  const first = (detail && detail.concepts && detail.concepts[0]) || null
  if (first) return questTitle(first.name)
  return 'Start the journey'
}

export function totalXp(progressList) {
  let xp = 0
  for (const p of progressList || []) {
    const cm = p.concept_mastery || []
    for (const c of cm) {
      const m = Number(c.mastery) || 0
      if (m >= 0.9) xp += 100
      else if (m >= 0.7) xp += 50
      else if (m >= 0.4) xp += 25
      else xp += 10
    }
    xp += (p.session_count || 0) * 10
  }
  return xp
}

export function globalLevel(progressList) {
  return Math.max(1, Math.min(50, Math.floor(totalXp(progressList) / 200) + 1))
}

export function weakestConcepts(progressList, n = 3) {
  const out = []
  for (const p of progressList || []) {
    for (const c of p.concept_mastery || []) {
      out.push({ concept: c.concept, mastery: Number(c.mastery) || 0, syllabus: p.syllabus_name || p.syllabus_id, syllabus_id: p.syllabus_id })
    }
  }
  return out
    .filter((c) => c.mastery < 0.7)
    .sort((a, b) => a.mastery - b.mastery)
    .slice(0, n)
}

// ---------------------------------------------------------------- personas

export const PRESETS = [
  { id: 'sage', emoji: '🧙', name: 'Socratic Sage', strict: 0.5, humor: 0.35, tag: 'Questions over answers' },
  { id: 'jester', emoji: '🤡', name: 'Fun Jester', strict: 0.2, humor: 0.95, tag: 'Puns & play' },
  { id: 'intense', emoji: '💪', name: 'Intense Drill', strict: 0.95, humor: 0.15, tag: 'Push hard' },
  { id: 'gentle', emoji: '🕊️', name: 'Gentle Coach', strict: 0.3, humor: 0.45, tag: 'Encouraging' },
]

export const MOODS = [
  { id: 'stressed', emoji: '😩', label: 'Stressed' },
  { id: 'tired', emoji: '😴', label: 'Tired' },
  { id: 'energetic', emoji: '⚡', label: 'Energetic' },
  { id: 'curious', emoji: '🤔', label: 'Curious' },
]

export function presetById(id) {
  return PRESETS.find((p) => p.id === id) || PRESETS[0]
}

export function personaFromVibe(vibe, stuck) {
  // vibe: 'hard' | 'soft'  ; stuck: 'think' | 'tell'
  if (vibe === 'hard' && stuck === 'think') return { preset: 'intense', strict: 0.85, humor: 0.2 }
  if (vibe === 'hard' && stuck === 'tell') return { preset: 'sage', strict: 0.65, humor: 0.35 }
  if (vibe === 'soft' && stuck === 'think') return { preset: 'sage', strict: 0.5, humor: 0.5 }
  return { preset: 'gentle', strict: 0.25, humor: 0.55 }
}

export function moodToSliders(moodId) {
  switch (moodId) {
    case 'stressed': return { strict: 0.15, humor: 0.6 }
    case 'tired': return { strict: 0.2, humor: 0.55 }
    case 'energetic': return { strict: 0.9, humor: 0.3 }
    case 'curious': return { strict: 0.55, humor: 0.4 }
    default: return null
  }
}

// ---------------------------------------------------------------- preferences (localStorage)

const PREF_KEY = 'codewhale-quest-v1'

export function loadPrefs() {
  try {
    return JSON.parse(localStorage.getItem(PREF_KEY)) || {}
  } catch {
    return {}
  }
}

export function savePrefs(prefs) {
  try {
    localStorage.setItem(PREF_KEY, JSON.stringify(prefs))
  } catch {
    /* ignore quota/private-mode errors */
  }
}

export function todayKey() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export function yesterdayKey() {
  const d = new Date()
  d.setDate(d.getDate() - 1)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export function updateStreak(prefs) {
  const today = todayKey()
  const p = { ...prefs }
  if (p.lastDay === today) {
    // already counted today
  } else if (p.lastDay === yesterdayKey()) {
    p.streak = (p.streak || 0) + 1
    p.lastDay = today
  } else {
    p.streak = 1
    p.lastDay = today
  }
  return p
}

// ---------------------------------------------------------------- speech (browser TTS)

export function speak(text) {
  if (typeof window === 'undefined' || !('speechSynthesis' in window)) return false
  try {
    const clean = String(text).replace(/[#*_`>|]/g, ' ').replace(/\s+/g, ' ').trim()
    if (!clean) return false
    const u = new SpeechSynthesisUtterance(clean)
    u.lang = /[àâäéèêëîïôöùûüçœ]/.test(clean) ? 'fr-FR' : 'en-US'
    u.rate = 0.95
    window.speechSynthesis.cancel()
    window.speechSynthesis.speak(u)
    return true
  } catch {
    return false
  }
}

// ---------------------------------------------------------------- coach

const pick = (arr) => arr[Math.floor(Math.random() * arr.length)]

const HUMOR_LINES = [
  'By the beard of Pythagoras, that is a fine question! 🧔',
  'Ahoy! 🐋 Let us chart those waters together.',
  'Math is easy... said no whale ever. But we will make it fun.',
  '🐋 + 💡 = a whale of an idea. Let us dive in!',
]

function openers(ctx) {
  const humor = ctx.persona?.humor ?? 0.4
  if (humor > 0.7) return pick(HUMOR_LINES)
  return 'Good. Let us break it into small pieces and think it through. 🐋'
}

function weakestText(ctx) {
  const weak = weakestConcepts(ctx.progress, 3)
  if (!weak.length) {
    return "Right now there is no concept marked as a weakness — either you haven't started a tutoring session yet, or you're cruising. 🎉"
  }
  const rows = weak.map((w) => `• ${w.concept} — ${pct(w.mastery)} (${w.syllabus})`)
  return `Here is your weakness radar, sailor:\n${rows.join('\n')}\n\nPick the lowest one and we will turn it into a strength.`
}

function questText(ctx) {
  const quests = generateQuests(ctx)
  if (!quests.length) return 'The quest board is quiet. Drop a syllabus into ~/.codewhale/syllabi and press Sync, then I will have plenty for you!'
  return `Today's quests, adventurer:\n${quests.map((q, i) => `${i + 1}. ${q.title}${q.sub ? ` — ${q.sub}` : ''}`).join('\n')}`
}

function reviewText(ctx) {
  const mastered = []
  for (const p of ctx.progress || []) {
    for (const c of p.concept_mastery || []) {
      if ((c.mastery ?? 0) >= 0.7) mastered.push(c.concept)
    }
  }
  if (!mastered.length) return "Nothing is ripe for review yet. Let's master something first, then I will schedule its Memory Palace visit. 📖"
  return `Worth a quick revisit: ${pick(mastered.slice(0, 6))} — a 30-second refresher keeps it from sinking back into the deep. 🧠`
}

function gauntletText(ctx) {
  const mocks = (ctx.exams || []).filter((e) => e.kind === 'mock')
  if (!mocks.length) return 'No mock exam has been inferred yet. Add a syllabus (or real exam) and I will forge a Gauntlet for you. ⚔️'
  return `The Final Boss approaches! ⚔️ Your Gauntlet has ${mocks.length} mock battle(s) ready. Train in the weakest area first, review the Treasure Map, then attempt the mini-mock.`
}

function cheatsheetText(ctx) {
  const syllabi = ctx.syllabi || []
  if (!syllabi.length) return 'No Treasure Maps yet. Drop a syllabus and I will draw one for you. 🗺️'
  return `Treasure Maps are ready for: ${syllabi.map((s) => s.name).join(', ')}. Open the Treasure Maps tab to read (or listen to) one. 🗺️`
}

function quizText(ctx) {
  const exam = pick(ctx.exams || [])
  if (!exam) return 'I would love to quiz you, but I need at least one exam or mock exam first. Press Sync after dropping a syllabus. 🎲'
  const q = pick((exam.sample_questions && exam.sample_questions.length ? exam.sample_questions : null) || [])
  if (q && q.text) return `Pop quiz, captain! 🎯\n\n"${q.text}"\n\nTake your time, show your working, then tell me what you think. I will not hand you the answer — that would be cheating the quest.`
  return `Open the Gauntlet tab and pick "${exam.id}" — your training starts there. 🎲`
}

function moodText(ctx, raw) {
  const t = (raw || '').toLowerCase()
  if (/stress|anxieux|anxie/.test(t)) return 'Breathe in… exhale the confusion. We will go slowly, one concept at a time. You are safe here. 🧘'
  if (/tired|fatigu|épuis|epuis/.test(t)) return 'Low battery? No problem. We will keep it gentle and short today. Just one small step counts. 😴'
  if (/energ/.test(t)) return 'Charged up! Then we push. Drop and give me one hard problem, soldier. ⚡'
  if (/curious|curieux/.test(t)) return 'Curiosity is the best compass. What would you like to understand deeply today? 🤔'
  return 'How are you feeling today — 😩 stressed, 😴 tired, ⚡ energetic, or 🤔 curious? I will tune the session to match.'
}

function progressText(ctx) {
  const xp = totalXp(ctx.progress)
  const lvl = globalLevel(ctx.progress)
  const mastered = (ctx.progress || []).reduce((n, p) => n + (p.concept_mastery || []).filter((c) => (c.mastery ?? 0) >= 0.7).length, 0)
  return `You are a Level ${lvl} adventurer with ${xp} XP and ${mastered} mastered concept(s). ${mastered >= 50 ? 'By the beard of Pythagoras! 🎉' : 'Keep forging — every concept counts.'}`
}

function greetText(ctx) {
  const syllabi = ctx.syllabi || []
  const p = ctx.progress || []
  const base = `Ahoy there, knowledge seeker! 🐋 I'm Prof. Whaley.`
  if (!syllabi.length && !p.length) {
    return `${base}\n\nI see an empty harbor. Drop your scrolls (syllabi) and ancient texts (exams) into ~/.codewhale/syllabi and ~/.codewhale/exams, press Sync, and I will chart your Adventure Paths.`
  }
  return `${base}\n\nI've spotted ${syllabi.length} world(s) to explore and ${p.length} progress log(s). Ask me for your quests, weaknesses, a quiz, or a review — or just tell me what you want to learn.`
}

function socraticText(ctx) {
  const weak = weakestConcepts(ctx.progress, 1)[0]
  if (weak) {
    return `${openers(ctx)}\n\nI noticed "${weak.concept}" is at ${pct(weak.mastery)}. Let me ask you this: what do you already understand about it, and where exactly does it get foggy? Explain it back to me like I'm a curious dolphin. 🐬`
  }
  if ((ctx.syllabi || []).length) {
    const first = ctx.syllabi[0]
    return `${openers(ctx)}\n\nWe have a whole world to explore. Which concept would you like to tackle, or shall I suggest the first quest in "${first.name}"?`
  }
  return `${openers(ctx)}\n\nI need a syllabus before I can truly tutor you. Drop one into ~/.codewhale/syllabi and press Sync. Then ask me anything.`
}

export function coachReply(raw, ctx) {
  const t = (raw || '').trim().toLowerCase()
  if (!t) return greetText(ctx)
  if (/(^|\s)(hi|hello|hey|salut|bonjour|hola|yo)\b/.test(t)) return greetText(ctx)
  if (/help|aide|command|what can|start|begin|how do/.test(t)) {
    return `I can help you with:\n• "quests" — today's missions\n• "weaknesses" — your weakness radar\n• "quiz me" — a practice problem\n• "review" — spaced-repetition nudge\n• "cheatsheet" / "treasure map"\n• "exam" / "gauntlet"\n• "how am I doing?" — progress\n• "I feel stressed/tired/energetic/curious"\n\nWhat would you like? 🐋`
  }
  if (/quest|mission|daily|today|aujourd/.test(t)) return questText(ctx)
  if (/weak|faible|difficult|struggle|galer|bloque|radar/.test(t)) return weakestText(ctx)
  if (/review|révis|revis|spaced|memory|rappel|palace/.test(t)) return reviewText(ctx)
  if (/exam|test|mock|gauntlet|contrôle|controle|brevet|prepare|boss/.test(t)) return gauntletText(ctx)
  if (/cheatsheet|fich|triche|summary|résumé|resume|map|treasure|scroll/.test(t)) return cheatsheetText(ctx)
  if (/quiz|question|interro|practice|entraîne|entraine|exercice|problème|probleme/.test(t)) return quizText(ctx)
  if (/feeling|mood|stress|tired|fatigu|épuis|epuis|energ|curious|curieux|anxie/.test(t)) return moodText(ctx, raw)
  if (/progress|level|niveau|xp|avanc|how am i|doing|master/.test(t)) return progressText(ctx)
  return socraticText(ctx)
}

export function generateQuests(ctx) {
  const quests = []
  const first = (ctx.syllabi && ctx.syllabi[0]) || null
  const weak = weakestConcepts(ctx.progress, 1)[0]
  const unmastered = weakestConcepts(ctx.progress, 10)
  const mocks = (ctx.exams || []).filter((e) => e.kind === 'mock')

  if (!ctx.progress || ctx.progress.length === 0) {
    if (!first) {
      quests.push({
        title: 'Add your first syllabus', sub: 'Upload it in Settings',
        titleKey: 'quest.q.add.title', subKey: 'quest.q.add.sub',
        action: { view: 'settings' },
      })
      return quests
    }
    quests.push({
      title: 'Explore your first World', sub: `Open ${first.name} and read its objectives`,
      titleKey: 'quest.q.explore.title', subKey: 'quest.q.explore.sub', vars: { name: first.name },
      action: { view: 'world', syllabusId: first.id },
    })
    quests.push({
      title: 'Unlock a Treasure Map', sub: 'Read (or listen to) a cheatsheet',
      titleKey: 'quest.q.map.title', subKey: 'quest.q.map.sub',
      action: { view: 'maps', syllabusId: first.id },
    })
    quests.push({
      title: 'Talk to Prof. Whaley', sub: 'I\u2019ll show you what I can do',
      titleKey: 'quest.q.talk.title', subKey: 'quest.q.talk.sub',
      action: { view: 'quest', prefill: 'help' },
    })
    return quests
  }

  if (weak) {
    quests.push({
      title: `Defeat the ${weak.concept}`, sub: '5 practice problems',
      titleKey: 'quest.q.defeat.title', subKey: 'quest.q.defeat.sub', vars: { concept: weak.concept },
      action: { view: 'model', syllabusId: weak.syllabus_id },
    })
  }
  if (unmastered.length > 1) {
    quests.push({
      title: `Solve the ${unmastered[1].concept} Riddle`, sub: '1 problem with Socratic questioning',
      titleKey: 'quest.q.riddle.title', subKey: 'quest.q.riddle.sub', vars: { concept: unmastered[1].concept },
      action: { view: 'quest', prefill: 'quiz me' },
    })
  }
  if (mocks.length) {
    quests.push({
      title: 'Challenge the Mock Exam Mini-Boss', sub: `${mocks[0].id}`,
      titleKey: 'quest.q.boss.title', subKey: 'quest.q.boss.sub', vars: { name: mocks[0].id },
      action: { view: 'gauntlet' },
    })
  } else {
    quests.push({
      title: 'Review a Treasure Map', sub: 'Refresh one concept from the cheatsheet',
      titleKey: 'quest.q.reviewMap.title', subKey: 'quest.q.reviewMap.sub',
      action: { view: 'maps', syllabusId: first && first.id },
    })
  }
  return quests.slice(0, 3)
}

export function syllabusEmoji(syllabus) {
  const n = (syllabus && (syllabus.name || syllabus.id)) || ''
  const lower = n.toLowerCase()
  if (/math|alg|analyse|calcul|probab|stat|géom|geome|lineaire|linear/.test(lower)) return '🧮'
  if (/python|program|code|info|data|algo/.test(lower)) return '💻'
  if (/econ|économ|econom|market|marché|marc/.test(lower)) return '📊'
  if (/soci|hist|geo|géo|philo|fran|langue|liter|english|anglais|brevet/.test(lower)) return '📚'
  if (/scien|physi|chimi|bio|svt|techno/.test(lower)) return '🔬'
  return '🏰'
}
