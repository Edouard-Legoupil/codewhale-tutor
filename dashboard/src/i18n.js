import { createContext, useContext } from 'react'

export const LOCALES = ['en', 'fr', 'es', 'de']
export const LOCALE_NAMES = { en: 'English', fr: 'Français', es: 'Español', de: 'Deutsch' }

export function detectLocale() {
  if (typeof navigator === 'undefined') return 'en'
  const langs = (navigator.languages && navigator.languages.length)
    ? navigator.languages
    : [navigator.language]
  for (const l of langs) {
    const base = (l || '').split('-')[0].toLowerCase()
    if (LOCALES.includes(base)) return base
  }
  return 'en'
}

// { key: { en, fr, es, de } }
const STRINGS = {
  // Navigation
  'nav.kingdom': { en: 'Kingdom', fr: 'Royaume', es: 'Reino', de: 'Königreich' },
  'nav.quest': { en: 'Quest', fr: 'Quête', es: 'Misión', de: 'Quest' },
  'nav.gauntlet': { en: 'Gauntlet', fr: 'Arène', es: 'Guantelete', de: 'Prüfung' },
  'nav.maps': { en: 'Maps', fr: 'Cartes', es: 'Mapas', de: 'Karten' },
  'nav.model': { en: 'Model', fr: 'Modèle', es: 'Modelo', de: 'Modell' },
  'nav.reflection': { en: 'Reflection', fr: 'Bilan', es: 'Reflexión', de: 'Rückblick' },

  // Header
  'header.streak': { en: 'Day streak', fr: 'Série de jours', es: 'Racha de días', de: 'Tages-Serie' },
  'header.xp': { en: 'Experience points', fr: 'Points d\u2019expérience', es: 'Puntos de experiencia', de: 'Erfahrungspunkte' },
  'header.dyslexia': { en: 'Dyslexic-friendly mode: larger type, higher contrast, cream background', fr: 'Mode dyslexie : texte agrandi, contraste élevé, fond crème', es: 'Modo dislexia: texto grande, alto contraste, fondo crema', de: 'Legasthenie-Modus: größere Schrift, hoher Kontrast, cremefarbener Hintergrund' },
  'header.sync': { en: 'Re-scan ~/.codewhale/syllabi and ~/.codewhale/exams', fr: 'Re-scanner ~/.codewhale/syllabi et ~/.codewhale/exams', es: 'Reescanear ~/.codewhale/syllabi y ~/.codewhale/exams', de: '~/.codewhale/syllabi und ~/.codewhale/exams neu einlesen' },
  'header.switchVibe': { en: 'Switch tutor vibe', fr: 'Changer le style du tuteur', es: 'Cambiar el estilo del tutor', de: 'Tutor-Stil wechseln' },
  'header.language': { en: 'Language', fr: 'Langue', es: 'Idioma', de: 'Sprache' },

  // Persona
  'persona.sage': { en: 'Socratic Sage', fr: 'Sage socratique', es: 'Sabio socrático', de: 'Sokratischer Weiser' },
  'persona.jester': { en: 'Fun Jester', fr: 'Joueur farceur', es: 'Bufón divertido', de: 'Spaß-Narr' },
  'persona.intense': { en: 'Intense Drill', fr: 'Coach intense', es: 'Entrenador intenso', de: 'Intensiver Drill' },
  'persona.gentle': { en: 'Gentle Coach', fr: 'Coach bienveillant', es: 'Entrenador amable', de: 'Sanfter Coach' },
  'persona.sage.tag': { en: 'Questions over answers', fr: 'Des questions plutôt que des réponses', es: 'Preguntas antes que respuestas', de: 'Fragen statt Antworten' },
  'persona.jester.tag': { en: 'Puns & play', fr: 'Jeux de mots & jeu', es: 'Juegos y chistes', de: 'Wortspiele & Spaß' },
  'persona.intense.tag': { en: 'Push hard', fr: 'Pousse fort', es: 'Exigir al máximo', de: 'Hart fordern' },
  'persona.gentle.tag': { en: 'Encouraging', fr: 'Encourageant', es: 'Alentador', de: 'Ermutigend' },
  'persona.strictness': { en: 'Strictness', fr: 'Exigence', es: 'Exigencia', de: 'Strenge' },
  'persona.chill': { en: 'Chill', fr: 'Détendu', es: 'Relajado', de: 'Entspannt' },
  'persona.drill': { en: 'Drill', fr: 'Sergent', es: 'Sargento', de: 'Drill' },
  'persona.humor': { en: 'Humor', fr: 'Humour', es: 'Humor', de: 'Humor' },
  'persona.serious': { en: 'Serious', fr: 'Sérieux', es: 'Serio', de: 'Ernst' },
  'persona.joker': { en: 'Joker', fr: 'Farceur', es: 'Bromista', de: 'Narr' },
  'persona.auto': { en: 'Auto-adapt my vibe from my performance 🤖', fr: 'Adapter automatiquement mon style à mes résultats 🤖', es: 'Adaptar automáticamente mi estilo a mi rendimiento 🤖', de: 'Meinen Stil automatisch an meine Leistung anpassen 🤖' },
  'persona.dailyMood': { en: 'Daily mood', fr: 'Humeur du jour', es: 'Ánimo del día', de: 'Tagesstimmung' },

  // Onboarding
  'onboard.title': { en: 'Ahoy there, knowledge seeker!', fr: 'Ahoy, explorateur du savoir !', es: '¡Ahoy, buscador de conocimiento!', de: 'Ahoi, Wissenssuchender!' },
  'onboard.sub': { en: "I'm Prof. Whaley. Two quick questions so I can tune my teaching to you — then we set sail.", fr: "Je suis Prof. Whaley. Deux petites questions pour adapter mon enseignement — puis on lève l'ancre.", es: "Soy Prof. Whaley. Dos preguntas rápidas para adaptar mi enseñanza a ti — y luego zarpamos.", de: "Ich bin Prof. Whaley. Zwei kurze Fragen, dann legen wir ab." },
  'onboard.vibe': { en: 'Pick your learning vibe', fr: 'Choisis ton style d\u2019apprentissage', es: 'Elige tu estilo de aprendizaje', de: 'Wähle deinen Lernstil' },
  'onboard.vibe.hard.title': { en: 'Bring it on!', fr: 'Vas-y, lance-moi !', es: '¡Dame caña!', de: 'Fordere mich!' },
  'onboard.vibe.hard.sub': { en: 'Push me, challenge me.', fr: 'Pousse-moi, mets-moi au défi.', es: 'Exígeme, rétame.', de: 'Fordere mich heraus.' },
  'onboard.vibe.soft.title': { en: 'I want to enjoy this.', fr: 'Je veux y prendre du plaisir.', es: 'Quiero disfrutar de esto.', de: 'Ich möchte Spaß dabei haben.' },
  'onboard.vibe.soft.sub': { en: 'Keep it fun and gentle.', fr: 'Garde ça fun et bienveillant.', es: 'Que sea divertido y amable.', de: 'Halte es locker und sanft.' },
  'onboard.stuck': { en: 'When I get stuck, I prefer…', fr: 'Quand je bloque, je préfère…', es: 'Cuando me atasco, prefiero…', de: 'Wenn ich nicht weiterkomme, bevorzuge ich…' },
  'onboard.stuck.think.title': { en: 'Think harder', fr: 'Réfléchir davantage', es: 'Pensar más', de: 'Selbst weiterdenken' },
  'onboard.stuck.think.sub': { en: 'Guide me with questions.', fr: 'Guide-moi avec des questions.', es: 'Guíame con preguntas.', de: 'Leite mich mit Fragen.' },
  'onboard.stuck.tell.title': { en: 'Just tell me the trick', fr: 'Donne-moi l\u2019astuce', es: 'Solo dime el truco', de: 'Sag mir einfach den Trick' },
  'onboard.stuck.tell.sub': { en: 'Show me the way.', fr: 'Montre-moi le chemin.', es: 'Muéstrame el camino.', de: 'Zeig mir den Weg.' },

  // Common
  'common.loading': { en: 'Charting your kingdom…', fr: 'Cartographie de ton royaume…', es: 'Trazando tu reino…', de: 'Dein Königreich wird kartiert…' },
  'common.retry': { en: 'Retry', fr: 'Réessayer', es: 'Reintentar', de: 'Erneut versuchen' },
  'common.back': { en: '← Back to Kingdom', fr: '← Retour au Royaume', es: '← Volver al Reino', de: '← Zurück zum Königreich' },
  'common.listen': { en: 'Listen', fr: 'Écouter', es: 'Escuchar', de: 'Anhören' },
  'common.concepts': { en: '{n} concepts', fr: '{n} notions', es: '{n} conceptos', de: '{n} Konzepte' },

  // Kingdom
  'kingdom.hero.title': { en: 'Ahoy, knowledge seeker! 🐋', fr: 'Ahoy, explorateur du savoir ! 🐋', es: '¡Ahoy, buscador de conocimiento! 🐋', de: 'Ahoi, Wissenssuchender! 🐋' },
  'kingdom.hero.sub': { en: "I see {n} world{s} in your kingdom. Let's turn you into a learning legend.", fr: "Je vois {n} monde{s} dans ton royaume. Faisons de toi une légende du savoir.", es: "Veo {n} mundo{s} en tu reino. Hagamos de ti una leyenda del aprendizaje.", de: "Ich sehe {n} Welt{en} in deinem Königreich. Machen wir dich zur Lern-Legende." },
  'kingdom.hero.subEmpty': { en: "I see an empty harbor. Drop your scrolls into ~/.codewhale/syllabi and press Sync — I'll chart your Adventure Paths.", fr: "Je vois un port vide. Dépose tes documents dans ~/.codewhale/syllabi puis synchronise — je tracerai tes chemins d'aventure.", es: "Veo un puerto vacío. Coloca tus documentos en ~/.codewhale/syllabi y sincroniza — trazaré tus rutas de aventura.", de: "Ich sehe einen leeren Hafen. Lege deine Unterlagen in ~/.codewhale/syllabi ab und synchronisiere." },
  'kingdom.streak': { en: 'Day streak', fr: 'Série de jours', es: 'Racha de días', de: 'Tages-Serie' },
  'kingdom.xp': { en: 'Experience', fr: 'Expérience', es: 'Experiencia', de: 'Erfahrung' },
  'kingdom.level': { en: 'Adventurer level', fr: 'Niveau d\u2019aventurier', es: 'Nivel de aventurero', de: 'Abenteurer-Level' },
  'kingdom.mastered': { en: 'Mastered', fr: 'Maîtrisé', es: 'Dominado', de: 'Gemeistert' },
  'kingdom.quests': { en: "Today's Quests", fr: 'Quêtes du jour', es: 'Misiones de hoy', de: 'Heutige Quests' },
  'kingdom.askWhaley': { en: 'Ask Prof. Whaley for more 🐋', fr: 'Demande-en plus à Prof. Whaley 🐋', es: 'Pregúntale más a Prof. Whaley 🐋', de: 'Frag Prof. Whaley nach mehr 🐋' },
  'kingdom.worlds': { en: 'Your Learning Kingdom', fr: 'Ton Royaume du savoir', es: 'Tu Reino del aprendizaje', de: 'Dein Lern-Königreich' },
  'kingdom.noWorlds.title': { en: 'No worlds discovered yet', fr: 'Aucun monde découvert pour l\u2019instant', es: 'Aún no hay mundos descubiertos', de: 'Noch keine Welten entdeckt' },
  'kingdom.noWorlds.body': { en: 'Drop .md / .txt / .pdf files into ~/.codewhale/syllabi and ~/.codewhale/exams. The library re-syncs automatically, or press Sync.', fr: 'Dépose des fichiers .md / .txt / .pdf dans ~/.codewhale/syllabi et ~/.codewhale/exams. La bibliothèque se synchronise automatiquement, ou appuie sur Synchroniser.', es: 'Coloca archivos .md / .txt / .pdf en ~/.codewhale/syllabi y ~/.codewhale/exams. La biblioteca se sincroniza sola, o pulsa Sincronizar.', de: 'Lege .md / .txt / .pdf Dateien in ~/.codewhale/syllabi und ~/.codewhale/exams ab.' },
  'kingdom.enter': { en: 'Enter world →', fr: 'Entrer dans le monde →', es: 'Entrar al mundo →', de: 'Welt betreten →' },
  'kingdom.radar': { en: 'Weakness Radar', fr: 'Radar des faiblesses', es: 'Radar de debilidades', de: 'Schwächen-Radar' },
  'kingdom.examReady': { en: 'Exam Readiness', fr: 'Préparation aux examens', es: 'Preparación de examen', de: 'Prüfungsbereitschaft' },
  'kingdom.recent': { en: 'Recent Activity', fr: 'Activité récente', es: 'Actividad reciente', de: 'Letzte Aktivität' },
  'kingdom.mock': { en: 'mock exam(s)', fr: 'examen(s) blanc(s)', es: 'examen(es) de prueba', de: 'Probeprüfung(en)' },
  'kingdom.real': { en: 'real exam(s)', fr: 'examen(s) réel(s)', es: 'examen(es) real(es)', de: 'echte Prüfung(en)' },
  'kingdom.enterGauntlet': { en: 'Enter the Gauntlet ⚔️', fr: 'Entrer dans l\u2019Arène ⚔️', es: 'Entrar al Guantelete ⚔️', de: 'Prüfung betreten ⚔️' },

  // World
  'world.objectives': { en: 'Quest Objectives', fr: 'Objectifs de quête', es: 'Objetivos de misión', de: 'Quest-Ziele' },
  'world.concepts': { en: 'Concept Map', fr: 'Carte des notions', es: 'Mapa de conceptos', de: 'Konzept-Karte' },
  'world.exams': { en: 'Linked Exams & Mock Battles', fr: 'Examens liés & batailles blanches', es: 'Exámenes y pruebas vinculados', de: 'Verknüpfte Prüfungen' },
  'world.weak': { en: 'Weak Spots', fr: 'Points faibles', es: 'Puntos débiles', de: 'Schwachstellen' },
  'world.next': { en: '🔓 Next', fr: '🔓 Suivant', es: '🔓 Siguiente', de: '🔓 Nächste' },

  // Treasure map / cheatsheet
  'map.title': { en: 'Treasure Map', fr: 'Carte au trésor', es: 'Mapa del tesoro', de: 'Schatzkarte' },
  'map.loading': { en: 'Unrolling the scroll…', fr: 'Déroulage du parchemin…', es: 'Desenrollando el pergamino…', de: 'Rolle wird entrollt…' },
  'map.empty': { en: 'No cheatsheet yet for {name}.', fr: 'Pas encore de fiche pour {name}.', es: 'Aún no hay chuleta para {name}.', de: 'Noch kein Spickzettel für {name}.' },

  // Quest (chat)
  'quest.title': { en: 'Prof. Whaley', fr: 'Prof. Whaley', es: 'Prof. Whaley', de: 'Prof. Whaley' },
  'quest.sub': { en: 'Your metacognitive tutor — ask me anything about your learning.', fr: 'Ton tuteur métacognitif — demande-moi ce que tu veux sur ton apprentissage.', es: 'Tu tutor metacognitivo — pregúntame lo que quieras sobre tu aprendizaje.', de: 'Dein metakognitiver Tutor — frag mich alles über dein Lernen.' },
  'quest.mood': { en: 'How are you feeling today?', fr: 'Comment te sens-tu aujourd\u2019hui ?', es: '¿Cómo te sientes hoy?', de: 'Wie fühlst du dich heute?' },
  'quest.quests': { en: "Today's Quests", fr: 'Quêtes du jour', es: 'Misiones de hoy', de: 'Heutige Quests' },
  'quest.about': { en: 'About this tutor', fr: 'À propos de ce tuteur', es: 'Sobre este tutor', de: 'Über diesen Tutor' },
  'quest.aboutBody': { en: 'I use Socratic questioning to help you think, not just copy answers. My tone is set by the persona control in the header.', fr: "J'utilise le questionnement socratique pour t'aider à réfléchir. Mon ton se règle via le contrôle en haut.", es: 'Uso preguntas socráticas para ayudarte a pensar. Mi tono se ajusta desde el control superior.', de: 'Ich nutze sokratische Fragen. Mein Ton wird oben im Kopf eingestellt.' },
  'quest.placeholder': { en: 'Try "what should I study today?" or ask about a concept…', fr: 'Essaie « que devrais-je étudier aujourd\u2019hui ? » ou demande une notion…', es: 'Prueba « ¿qué estudio hoy? » o pregunta por un concepto…', de: 'Probiere „Was soll ich heute lernen?" oder frag nach einem Konzept…' },
  'quest.send': { en: 'Send ⚡', fr: 'Envoyer ⚡', es: 'Enviar ⚡', de: 'Senden ⚡' },
  'qa.quests': { en: '📜 Today\u2019s quests', fr: '📜 Quêtes du jour', es: '📜 Misiones de hoy', de: '📜 Heutige Quests' },
  'qa.weak': { en: '🧭 Weaknesses', fr: '🧭 Points faibles', es: '🧭 Debilidades', de: '🧭 Schwächen' },
  'qa.next': { en: '🎯 Next step', fr: '🎯 Prochaine étape', es: '🎯 Siguiente paso', de: '🎯 Nächster Schritt' },
  'qa.quiz': { en: '🎲 Quiz me', fr: '🎲 Quiz-moi', es: '🎲 Hazme un test', de: '🎲 Quiz mich' },
  'qa.review': { en: '📖 Review', fr: '📖 Réviser', es: '📖 Repasar', de: '📖 Wiederholen' },
  'qa.map': { en: '🗺️ Treasure map', fr: '🗺️ Carte au trésor', es: '🗺️ Mapa del tesoro', de: '🗺️ Schatzkarte' },
  'qa.progress': { en: '🏅 Progress', fr: '🏅 Progression', es: '🏅 Progreso', de: '🏅 Fortschritt' },

  // Gauntlet
  'gauntlet.title': { en: '⚔️ The Exam Gauntlet', fr: '⚔️ L\u2019Arène des examens', es: '⚔️ El Guantelete del examen', de: '⚔️ Die Prüfungs-Arena' },
  'gauntlet.sub': { en: 'Choose your weapon: 📖 Sword of Reading · 🎧 Shield of Listening · 🖍️ Bow of Drawing · 🗣️ Staff of Speaking.', fr: 'Choisis ton arme : 📖 Épée de lecture · 🎧 Bouclier d\u2019écoute · 🖍️ Arc du dessin · 🗣️ Bâton de parole.', es: 'Elige tu arma: 📖 Espada de lectura · 🎧 Escudo de escucha · 🖍️ Arco de dibujo · 🗣️ Bastón de habla.', de: 'Wähle deine Waffe: 📖 Schwert des Lesens · 🎧 Schild des Hörens · 🖍️ Bogen des Zeichnens · 🗣️ Stab des Sprechens.' },
  'gauntlet.empty.title': { en: 'The Gauntlet stands empty', fr: 'L\u2019Arène est vide', es: 'El Guantelete está vacío', de: 'Die Arena ist leer' },
  'gauntlet.choose': { en: 'Choose a battle', fr: 'Choisis un combat', es: 'Elige una batalla', de: 'Wähle einen Kampf' },
  'gauntlet.pick': { en: 'Pick a battle to see the portrait', fr: 'Choisis un combat pour voir le portrait', es: 'Elige una batalla para ver el retrato', de: 'Wähle einen Kampf für das Porträt' },
  'gauntlet.scouting': { en: 'Scouting the exam…', fr: 'Reconnaissance de l\u2019examen…', es: 'Reconociendo el examen…', de: 'Prüfung wird erkundet…' },
  'gauntlet.portrait': { en: 'Performance Portrait', fr: 'Portrait de performance', es: 'Retrato de rendimiento', de: 'Leistungs-Porträt' },
  'gauntlet.questions': { en: 'Questions', fr: 'Questions', es: 'Preguntas', de: 'Fragen' },
  'gauntlet.easy': { en: 'Easy', fr: 'Facile', es: 'Fácil', de: 'Leicht' },
  'gauntlet.medium': { en: 'Medium', fr: 'Moyen', es: 'Medio', de: 'Mittel' },
  'gauntlet.hard': { en: 'Hard', fr: 'Difficile', es: 'Difícil', de: 'Schwer' },
  'gauntlet.concepts': { en: 'Concepts tested', fr: 'Notions testées', es: 'Conceptos evaluados', de: 'Geprüfte Konzepte' },
  'gauntlet.samples': { en: 'Sample challenges', fr: 'Défis d\u2019exemple', es: 'Retos de ejemplo', de: 'Beispiel-Aufgaben' },
  'gauntlet.mock': { en: 'Inferred mock exam', fr: 'Examen blanc inféré', es: 'Examen de prueba inferido', de: 'Abgeleitete Probeprüfung' },
  'gauntlet.real': { en: 'Real exam', fr: 'Examen réel', es: 'Examen real', de: 'Echte Prüfung' },

  // Maps
  'maps.title': { en: '🗺️ Treasure Maps', fr: '🗺️ Cartes au trésor', es: '🗺️ Mapas del tesoro', de: '🗺️ Schatzkarten' },
  'maps.sub': { en: 'Concise cheatsheets for every world — read them, listen to them, or add your own "ah-ha!" notes.', fr: 'Des fiches concises pour chaque monde — lis-les, écoute-les, ou ajoute tes notes.', es: 'Chuletas concisas para cada mundo — léelas, escúchalas o añade tus notas.', de: 'Kompakte Spickzettel für jede Welt — lesen, anhören oder eigene Notizen ergänzen.' },
  'maps.worlds': { en: 'Worlds', fr: 'Mondes', es: 'Mundos', de: 'Welten' },
  'maps.overview': { en: 'Concept overview — {name}', fr: 'Vue d\u2019ensemble — {name}', es: 'Resumen de conceptos — {name}', de: 'Konzept-Übersicht — {name}' },
  'maps.empty.title': { en: 'No maps yet', fr: 'Pas encore de cartes', es: 'Aún no hay mapas', de: 'Noch keine Karten' },

  // Model
  'model.title': { en: '🧩 The Learning Model', fr: '🧩 Le Modèle d\u2019apprentissage', es: '🧩 El Modelo de aprendizaje', de: '🧩 Das Lernmodell' },
  'model.sub': { en: 'Curriculum → observable competencies → prerequisite graph → evidence → inferred mastery → next action.', fr: 'Référentiel → compétences observables → graphe de prérequis → preuves → maîtrise inférée → prochaine action.', es: 'Currículo → competencias observables → grafo de prerrequisitos → evidencia → dominio → siguiente acción.', de: 'Lehrplan → Kompetenzen → Voraussetzungs-Graph → Evidenz → Beherrschung → nächste Aktion.' },
  'model.empty.title': { en: 'No model yet', fr: 'Pas encore de modèle', es: 'Aún no hay modelo', de: 'Noch kein Modell' },
  'model.next': { en: 'Recommended next action', fr: 'Prochaine action recommandée', es: 'Siguiente acción recomendada', de: 'Empfohlene nächste Aktion' },
  'model.domains': { en: 'Domains', fr: 'Domaines', es: 'Dominios', de: 'Domänen' },
  'model.competences': { en: 'Observable competencies', fr: 'Compétences observables', es: 'Competencias observables', de: 'Beobachtbare Kompetenzen' },
  'model.graph': { en: 'Prerequisite graph', fr: 'Graphe des prérequis', es: 'Grafo de prerrequisitos', de: 'Voraussetzungs-Graph' },
  'model.mastery': { en: 'Inferred mastery (5 states)', fr: 'Maîtrise inférée (5 états)', es: 'Dominio inferido (5 estados)', de: 'Abgeleitete Beherrschung (5 Stufen)' },
  'model.masteryBody': { en: 'Mastery is inferred from evidence (attempts, autonomy, transfer) — never hard-coded in the syllabus.', fr: 'La maîtrise est inférée des preuves (essais, autonomie, transfert) — jamais codée dans le syllabus.', es: 'El dominio se infiere de la evidencia (intentos, autonomía, transferencia) — nunca está en el programa.', de: 'Beherrschung wird aus Evidenz abgeleitet — nie im Lehrplan festgeschrieben.' },

  // Reflection
  'refl.title': { en: '📊 Your Learning Scroll', fr: '📊 Ton Parchemin d\u2019apprentissage', es: '📊 Tu Pergamino de aprendizaje', de: '📊 Deine Lern-Rolle' },
  'refl.sub': { en: "A reflection on how far you've sailed — with the humor you deserve.", fr: 'Un bilan du chemin parcouru — avec l\u2019humour que tu mérites.', es: 'Una reflexión sobre lo lejos que has llegado — con el humor que mereces.', de: 'Ein Rückblick auf deinen Weg — mit dem Humor, den du verdienst.' },
  'refl.empty.title': { en: 'Nothing to reflect on yet', fr: 'Rien à analyser pour l\u2019instant', es: 'Nada que reflexionar aún', de: 'Noch nichts zum Reflektieren' },
  'refl.scroll': { en: 'Weekly Scroll', fr: 'Parchemin hebdomadaire', es: 'Pergamino semanal', de: 'Wochen-Rolle' },
  'refl.patterns': { en: 'Pattern Recognition', fr: 'Reconnaissance des motifs', es: 'Reconocimiento de patrones', de: 'Mustererkennung' },
  'refl.calibration': { en: 'Calibration', fr: 'Calibrage', es: 'Calibración', de: 'Kalibrierung' },
  'refl.allies': { en: 'Strongest Allies', fr: 'Alliés les plus forts', es: 'Aliados más fuertes', de: 'Stärkste Verbündete' },
  'refl.nemeses': { en: 'Arch-nemeses', fr: 'Némésis', es: 'Archienemigos', de: 'Erzfeinde' },
  'refl.focus': { en: 'Next Focus', fr: 'Prochain objectif', es: 'Próximo enfoque', de: 'Nächster Fokus' },

  // Quest cards (clickable)
  'quest.q.add.title': { en: 'Add your first syllabus', fr: 'Ajoute ton premier syllabus', es: 'Añade tu primer programa', de: 'Füge deinen ersten Lehrplan hinzu' },
  'quest.q.add.sub': { en: 'Upload it in Settings', fr: 'Importe-le dans Réglages', es: 'Súbelo en Ajustes', de: 'Lade ihn in den Einstellungen hoch' },
  'quest.q.explore.title': { en: 'Explore your first World', fr: 'Explore ton premier Monde', es: 'Explora tu primer Mundo', de: 'Erkunde deine erste Welt' },
  'quest.q.explore.sub': { en: 'Open {name} and read its objectives', fr: 'Ouvre {name} et lis ses objectifs', es: 'Abre {name} y lee sus objetivos', de: 'Öffne {name} und lies die Ziele' },
  'quest.q.map.title': { en: 'Unlock a Treasure Map', fr: 'Débloque une Carte au trésor', es: 'Desbloquea un Mapa del tesoro', de: 'Schalte eine Schatzkarte frei' },
  'quest.q.map.sub': { en: 'Read (or listen to) a cheatsheet', fr: 'Lis (ou écoute) une fiche', es: 'Lee (o escucha) una chuleta', de: 'Lies (oder höre) einen Spickzettel' },
  'quest.q.talk.title': { en: 'Talk to Prof. Whaley', fr: 'Parle à Prof. Whaley', es: 'Habla con Prof. Whaley', de: 'Sprich mit Prof. Whaley' },
  'quest.q.talk.sub': { en: 'I\u2019ll show you what I can do', fr: 'Je te montre ce que je sais faire', es: 'Te muestro lo que puedo hacer', de: 'Ich zeige dir, was ich kann' },
  'quest.q.defeat.title': { en: 'Defeat the {concept}', fr: 'Vaincre {concept}', es: 'Derrota a {concept}', de: 'Besiege {concept}' },
  'quest.q.defeat.sub': { en: '5 practice problems', fr: '5 exercices d\u2019entraînement', es: '5 ejercicios de práctica', de: '5 Übungsaufgaben' },
  'quest.q.riddle.title': { en: 'Solve the {concept} Riddle', fr: 'Résous l\u2019énigme {concept}', es: 'Resuelve el enigma {concept}', de: 'Löse das {concept}-Rätsel' },
  'quest.q.riddle.sub': { en: '1 problem with Socratic questioning', fr: '1 problème avec questionnement socratique', es: '1 problema con preguntas socráticas', de: '1 Aufgabe mit sokratischem Fragen' },
  'quest.q.boss.title': { en: 'Challenge the Mock Exam Mini-Boss', fr: 'Affronte le Mini-Boss de l\u2019examen blanc', es: 'Desafía al Mini-Jefe del examen de prueba', de: 'Fordere den Mini-Boss der Probeprüfung heraus' },
  'quest.q.boss.sub': { en: '{name}', fr: '{name}', es: '{name}', de: '{name}' },
  'quest.q.reviewMap.title': { en: 'Review a Treasure Map', fr: 'Revois une Carte au trésor', es: 'Repasa un Mapa del tesoro', de: 'Wiederhole eine Schatzkarte' },
  'quest.q.reviewMap.sub': { en: 'Refresh one concept from the cheatsheet', fr: 'Rafraîchis une notion de la fiche', es: 'Refresca un concepto de la chuleta', de: 'Frische ein Konzept aus dem Spickzettel auf' },

  // Settings
  'nav.settings': { en: 'Settings', fr: 'Réglages', es: 'Ajustes', de: 'Einstellungen' },
  'settings.title': { en: '⚙️ Setup & Settings', fr: '⚙️ Installation & Réglages', es: '⚙️ Configuración', de: '⚙️ Einrichtung & Einstellungen' },
  'settings.syllabi': { en: 'Syllabi', fr: 'Syllabus', es: 'Programas', de: 'Lehrpläne' },
  'settings.upload': { en: 'Upload documents', fr: 'Importer des documents', es: 'Subir documentos', de: 'Dokumente hochladen' },
  'settings.upload.hint': { en: 'Drop a .md / .txt / .pdf file here (or pick one).', fr: 'Dépose un fichier .md / .txt / .pdf ici (ou choisis-en un).', es: 'Suelta un archivo .md / .txt / .pdf aquí (o elige uno).', de: 'Lege eine .md / .txt / .pdf Datei hier ab (oder wähle eine).' },
  'settings.upload.kind.syllabus': { en: 'Syllabus', fr: 'Syllabus', es: 'Programa', de: 'Lehrplan' },
  'settings.upload.kind.exam': { en: 'Exam', fr: 'Examen', es: 'Examen', de: 'Prüfung' },
  'settings.upload.btn': { en: 'Upload', fr: 'Importer', es: 'Subir', de: 'Hochladen' },
  'settings.sources': { en: 'Source files', fr: 'Fichiers sources', es: 'Archivos fuente', de: 'Quelldateien' },
  'settings.delete': { en: 'Delete', fr: 'Supprimer', es: 'Eliminar', de: 'Löschen' },
  'settings.delete.confirm': { en: 'Delete this syllabus and its data?', fr: 'Supprimer ce syllabus et ses données ?', es: '¿Eliminar este programa y sus datos?', de: 'Diesen Lehrplan und seine Daten löschen?' },
  'settings.model': { en: 'Edit generated model', fr: 'Éditer le modèle généré', es: 'Editar el modelo generado', de: 'Generiertes Modell bearbeiten' },
  'settings.model.hint': { en: 'Edit the competencies as JSON, then Save.', fr: 'Édite les compétences en JSON, puis Enregistrer.', es: 'Edita las competencias en JSON y guarda.', de: 'Bearbeite die Kompetenzen als JSON und speichere.' },
  'settings.model.save': { en: 'Save model', fr: 'Enregistrer le modèle', es: 'Guardar modelo', de: 'Modell speichern' },
  'settings.model.saved': { en: 'Saved ✓', fr: 'Enregistré ✓', es: 'Guardado ✓', de: 'Gespeichert ✓' },
  'settings.llm': { en: 'AI model (LLM)', fr: 'Modèle IA (LLM)', es: 'Modelo de IA (LLM)', de: 'KI-Modell (LLM)' },
  'settings.llm.base': { en: 'Base URL', fr: 'URL de base', es: 'URL base', de: 'Basis-URL' },
  'settings.llm.model': { en: 'Model', fr: 'Modèle', es: 'Modelo', de: 'Modell' },
  'settings.llm.key': { en: 'API key', fr: 'Clé API', es: 'Clave API', de: 'API-Schlüssel' },
  'settings.llm.enabled': { en: 'Enabled', fr: 'Activé', es: 'Activado', de: 'Aktiviert' },
  'settings.llm.save': { en: 'Save LLM settings', fr: 'Enregistrer les réglages LLM', es: 'Guardar ajustes de LLM', de: 'LLM-Einstellungen speichern' },
  'settings.llm.ollama': { en: 'Ollama (local)', fr: 'Ollama (local)', es: 'Ollama (local)', de: 'Ollama (lokal)' },
  'settings.llm.ollama.available': { en: 'Ollama detected', fr: 'Ollama détecté', es: 'Ollama detectado', de: 'Ollama erkannt' },
  'settings.llm.ollama.unavailable': { en: 'Ollama not detected — is it running? (ollama serve)', fr: 'Ollama non détecté — est-il lancé ? (ollama serve)', es: 'Ollama no detectado — ¿está en marcha? (ollama serve)', de: 'Ollama nicht erkannt — läuft es? (ollama serve)' },
  'settings.llm.use': { en: 'Use', fr: 'Utiliser', es: 'Usar', de: 'Verwenden' },
  'settings.empty': { en: 'No syllabi yet. Upload one below.', fr: 'Pas encore de syllabus. Importe-en un ci-dessous.', es: 'Aún no hay programas. Sube uno abajo.', de: 'Noch keine Lehrpläne. Lade unten einen hoch.' },
}

export function makeT(locale) {
  return function t(key, vars) {
    const entry = STRINGS[key]
    let s = entry ? (entry[locale] || entry.en || key) : key
    if (vars) {
      for (const [k, v] of Object.entries(vars)) {
        s = s.split(`{${k}}`).join(String(v))
      }
    }
    return s
  }
}

const I18nContext = createContext({
  locale: 'en',
  t: (k) => k,
  setLocale: () => {},
})

export const I18nProvider = I18nContext.Provider
export function useI18n() {
  return useContext(I18nContext)
}
