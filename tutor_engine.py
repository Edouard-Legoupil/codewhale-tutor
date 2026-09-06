#!/usr/bin/env python3
"""
Pédagogical engine ("moteur pédagogique") for the adaptive AI tutor.

This module is deliberately separate from the curriculum/ingestion layer
(``library.py``). It implements the decision-making side of the model described
in ``approche_modelisation_tutorat_ia.md``:

  * mastery is an **inferred state** (not a syllabus property);
  * an error is **diagnosed by its nature**, not just marked wrong;
  * scaffolding is **progressive and minimal**;
  * the next task is **chosen adaptively**, never "just the next exercise".

It only consumes generic dicts, so it can be driven by the dashboard API, the
MCP tools, or the Codewhale agent directly.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional

# --- Vocabulary (machine keys are stable; labels are for display) ------------

COMPETENCE_TYPES = [
    "connaissance", "comprehension", "procedure", "raisonnement", "application",
    "analyse", "communication", "outil", "synthese",
]

COMPETENCE_TYPE_LABELS = {
    "connaissance": "Connaissance",
    "comprehension": "Compréhension",
    "procedure": "Procédure",
    "raisonnement": "Raisonnement",
    "application": "Application",
    "analyse": "Analyse",
    "communication": "Communication",
    "outil": "Outil",
    "synthese": "Synthèse",
}

# Five inferred mastery states (see §9.1 of the reference document).
MASTERY_STATES = [
    "non_aborde", "en_cours", "acquis_avec_aide", "acquis", "maitrise",
]

MASTERY_STATE_LABELS = {
    "non_aborde": "Non abordé",
    "en_cours": "En cours",
    "acquis_avec_aide": "Acquis avec aide",
    "acquis": "Acquis",
    "maitrise": "Maîtrisé",
}

DIFFICULTY_DIMENSIONS = [
    "conceptualisation", "execution", "interpretation", "raisonnement",
    "autonomie", "transfert", "integration",
]

SOURCE_STATUSES = ["officiel", "institutionnel", "document_interne", "infere", "a_verifier"]

# Each diagnostic error type maps to a tutoring action (§10 of the reference).
ERROR_TYPES = {
    "knowledge": {
        "label": "Erreur de connaissance",
        "action": "Rappeler ou reconstruire la notion, puis vérifier immédiatement par une micro-question.",
    },
    "representation": {
        "label": "Erreur de représentation",
        "action": "Faire expliciter la correspondance entre les représentations (texte → formule → graphique…).",
    },
    "procedure": {
        "label": "Erreur de procédure",
        "action": "Faire verbaliser les étapes de la méthode, puis refaire une tâche analogue.",
    },
    "execution": {
        "label": "Erreur d'exécution / calcul",
        "action": "Faire localiser l'étape fautive avant de fournir la correction.",
    },
    "interpretation": {
        "label": "Erreur d'interprétation",
        "action": "Faire reformuler la consigne et identifier explicitement les informations utiles.",
    },
    "reasoning": {
        "label": "Erreur de raisonnement",
        "action": "Demander pourquoi la méthode, la propriété ou la décision a été choisie.",
    },
    "strategy": {
        "label": "Erreur de stratégie",
        "action": "Comparer les stratégies possibles et leurs conditions d'utilisation.",
    },
    "transfer": {
        "label": "Difficulté de transfert",
        "action": "Revenir à la structure commune, expliciter l'analogie, puis réessayer dans le contexte nouveau.",
    },
    "communication": {
        "label": "Erreur de communication",
        "action": "Distinguer le contenu intellectuel de la qualité de la présentation et entraîner la forme attendue.",
    },
}

# --- Mastery inference -------------------------------------------------------


def mastery_state(score: Optional[float], evidence: Optional[Dict] = None) -> str:
    """Map a 0..1 score and observed evidence to one of the five states.

    Mastery is *inferred* from observations, so evidence can upgrade or downgrade
    the raw score (a high score reached only with help is not "mastered").
    """
    ev = evidence or {}
    n_success = int(ev.get("successful_tasks", 0))
    n_indep = int(ev.get("independent_successes", 0))
    n_guided = int(ev.get("guided_successes", 0))
    n_transfer = int(ev.get("transfer_successes", 0))
    n_fail = int(ev.get("unsuccessful_tasks", 0))

    if score is None:
        return "non_aborde"

    if score >= 0.9 and (n_transfer > 0 or n_indep >= 3):
        return "maitrise"
    if score >= 0.7 and n_indep >= 1:
        return "acquis"
    if score >= 0.7 and n_guided >= 1:
        return "acquis_avec_aide"
    if score >= 0.4:
        return "en_cours"
    if n_success == 0 and n_fail == 0:
        return "non_aborde"
    return "en_cours"


def build_evidence(attempts: Optional[List[Dict]]) -> Dict:
    """Derive evidence counters from a list of recorded attempts."""
    evidence = {
        "successful_tasks": 0,
        "unsuccessful_tasks": 0,
        "independent_successes": 0,
        "guided_successes": 0,
        "transfer_successes": 0,
        "attempts": 0,
    }
    for a in attempts or []:
        evidence["attempts"] += 1
        correct = bool(a.get("correct"))
        if correct:
            evidence["successful_tasks"] += 1
            support = a.get("support") or a.get("autonomy", "independent")
            if support in ("independent", "autonomous"):
                evidence["independent_successes"] += 1
            elif support in ("guided", "prompted"):
                evidence["guided_successes"] += 1
            if a.get("transfer"):
                evidence["transfer_successes"] += 1
        else:
            evidence["unsuccessful_tasks"] += 1
    return evidence


# --- Error diagnosis ---------------------------------------------------------

_KNOWLEDGE_MARKERS = [
    "je ne sais pas", "i don't know", "aucune idee", "aucune idée", "no idea",
    "je ne connais pas", "jamais vu", "never seen", "?", "je ne comprends pas",
]
_PROCEDURE_MARKERS = [
    "methode", "méthode", "etape", "étape", "formule", "procedure", "procédure",
    "steps", "method", "ordre", "j'ai oublié", "forgot",
]
_INTERPRETATION_MARKERS = [
    "j'ai compris", "j'ai interpreté", "interprété", "signifie", "veut dire",
    "i understood", "i read", "d'après", "selon", "the question says",
]
_REASONING_MARKERS = [
    "donc", "parce que", "puisque", "ainsi", "because", "therefore", "so",
    "why", "pourquoi", "je pense que", "je crois que", "i think",
]
_TRANSFER_MARKERS = [
    "contexte", "situation", "appliquer", "transfer", "analogie", "new",
    "nouveau", "généraliser", "generalize",
]
_COMMUNICATION_MARKERS = [
    "rediger", "rédiger", "presenter", "présenter", "justifier", "expliquer",
    "write", "conclusion", "synthese", "synthèse",
]


def _strip_accents(text: str) -> str:
    import unicodedata
    return "".join(
        c for c in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(c) != "Mn"
    )


def diagnose_error(question: str, response: str, correct: Optional[bool] = None,
                   analysis: Optional[Dict] = None) -> Dict:
    """Classify the *nature* of an error and recommend a tutoring action."""
    q = _strip_accents(question or "")
    r = _strip_accents(response or "")

    types: List[str] = []
    if not r.strip() or any(m in r for m in _KNOWLEDGE_MARKERS):
        types.append("knowledge")
    if any(m in r for m in _INTERPRETATION_MARKERS) and (correct is False or correct is None):
        types.append("interpretation")
    if any(m in r for m in _PROCEDURE_MARKERS):
        types.append("procedure")
    if any(m in r for m in _TRANSFER_MARKERS):
        types.append("transfer")
    if any(m in r for m in _COMMUNICATION_MARKERS) and correct is False:
        types.append("communication")
    if any(m in r for m in _REASONING_MARKERS):
        types.append("reasoning")

    # If the answer is wrong but the reasoning markers are absent, prefer a
    # reasoning/procedure default over "knowledge" (which is reserved for blank /
    # explicit "I don't know").
    if correct is False and not types:
        types.append("reasoning")
    if correct is False and "procedure" not in types and "knowledge" not in types and len(response.split()) > 8:
        types.append("execution")

    if not types:
        types.append("reasoning")

    primary = types[0]
    severity = "blocking" if "knowledge" in types else ("significant" if len(types) > 1 else "minor")
    info = ERROR_TYPES.get(primary, ERROR_TYPES["reasoning"])

    return {
        "primary": primary,
        "types": types,
        "severity": severity,
        "confidence": (analysis or {}).get("confidence", 50),
        "label": info["label"],
        "action": info["action"],
        "independence": "unable" if "knowledge" in types else ("prompted" if "procedure" in types else "autonomous"),
    }


# --- Scaffolding -------------------------------------------------------------

def scaffold(levels: int = 3) -> List[Dict]:
    """Progressive, minimal help ladder (see §12 of the reference)."""
    ladder = [
        {"level": 1, "type": "indice_minimal", "content": "Indice minimal : que peut-on déjà récupérer de l'énoncé ?"},
        {"level": 2, "type": "question_guidee", "content": "Question guidée : quelle étape te semble la plus incertaine, et pourquoi ?"},
        {"level": 3, "type": "rappel_cible", "content": "Rappel ciblé : reviens à la définition ou à la méthode avant de recalculer."},
        {"level": 4, "type": "exemple_analogue", "content": "Exemple analogue : voici un cas plus simple — retrouve la structure commune."},
        {"level": 5, "type": "demonstration_partielle", "content": "Démonstration partielle : je fais la première étape, tu continues."},
        {"level": 6, "type": "demonstration_complete", "content": "Démonstration complète : je montre, puis tu refais seul."},
    ]
    return ladder[:levels]


# --- Adaptive next-action policy --------------------------------------------

_STATE_ACTION = {
    "non_aborde": {
        "action": "introduce",
        "label": "Introduire et diagnostiquer",
        "support_level": "moyen",
        "task_types": ["reconnaitre", "question_courte"],
    },
    "en_cours": {
        "action": "guided_task",
        "label": "Proposer une tâche guidée",
        "support_level": "fort",
        "task_types": ["appliquer", "exercice_direct"],
    },
    "acquis_avec_aide": {
        "action": "reduce_support",
        "label": "Réduire progressivement l'étayage",
        "support_level": "moyen",
        "task_types": ["appliquer", "interpreter"],
    },
    "acquis": {
        "action": "increase_difficulty",
        "label": "Augmenter la variation ou la complexité",
        "support_level": "faible",
        "task_types": ["resoudre", "probleme"],
    },
    "maitrise": {
        "action": "transfer_or_synthesis",
        "label": "Proposer un transfert ou une synthèse",
        "support_level": "faible",
        "task_types": ["transferer", "synthetiser"],
    },
}


def _blocking_prerequisite(target_id: str, competences: List[Dict], learner: Dict) -> Optional[Dict]:
    """Return the least-mastered prerequisite of ``target_id``, if any."""
    by_id = {c.get("id", c.get("name")): c for c in competences}
    target = by_id.get(target_id)
    if not target:
        return None
    blocked = []
    for pid in target.get("prerequisites", []) or []:
        state = (learner.get(pid) or {}).get("status", "non_aborde")
        if state in ("non_aborde", "en_cours"):
            blocked.append(pid)
    if not blocked:
        return None
    # Prefer the prerequisite that is furthest from mastered.
    order = {s: i for i, s in enumerate(MASTERY_STATES)}
    blocked.sort(key=lambda pid: order.get((learner.get(pid) or {}).get("status", "non_aborde"), 0))
    return by_id.get(blocked[0])


def next_action(competences: List[Dict], learner: Dict,
                graph: Optional[Dict] = None) -> Dict:
    """Choose the next pedagogical action (decision algorithm, §18).

    ``competences`` should be topologically ordered (prerequisites first).
    ``learner`` maps competence id → ``{"status": str, "score": float}``.
    """
    if not competences:
        return {"action": "none", "reason": "Aucune compétence modélisée."}

    # 1. A not-yet-mastered prerequisite blocks its dependents.
    for c in competences:
        cid = c.get("id", c.get("name"))
        state = (learner.get(cid) or {}).get("status", "non_aborde")
        if state in ("maitrise", "acquis"):
            continue
        blocker = _blocking_prerequisite(cid, competences, learner)
        if blocker:
            bid = blocker.get("id", blocker.get("name"))
            bstate = (learner.get(bid) or {}).get("status", "non_aborde")
            plan = _STATE_ACTION.get(bstate, _STATE_ACTION["non_aborde"])
            return {
                "action": "review_prerequisite",
                "target_competence": bid,
                "title": blocker.get("title") or blocker.get("name"),
                "reason": f"Prérequis bloquant pour « {c.get('title') or c.get('name')} ».",
                "support_level": plan["support_level"],
                "suggested_task_types": plan["task_types"],
                "label": "Revenir au prérequis bloquant",
            }

    # 2. Otherwise advance the first non-mastered competence in order.
    for c in competences:
        cid = c.get("id", c.get("name"))
        state = (learner.get(cid) or {}).get("status", "non_aborde")
        if state in ("maitrise",):
            continue
        plan = _STATE_ACTION.get(state, _STATE_ACTION["non_aborde"])
        return {
            "action": plan["action"],
            "target_competence": cid,
            "title": c.get("title") or c.get("name"),
            "reason": f"État actuel : {MASTERY_STATE_LABELS.get(state, state)}.",
            "support_level": plan["support_level"],
            "suggested_task_types": plan["task_types"],
            "label": plan["label"],
        }

    return {
        "action": "synthesis",
        "target_competence": None,
        "title": "Synthèse générale",
        "reason": "Toutes les compétences sont maîtrisées.",
        "support_level": "faible",
        "suggested_task_types": ["synthetiser", "transferer"],
        "label": "Proposer une synthèse ou un transfert",
    }


def build_learner_state(progress_data: Dict) -> Dict:
    """Derive a per-competence learner state from a raw progress file.

    Compatible with the schema written by ``tracking_hook`` (concept_mastery as
    a 0..1 dict) as well as the richer schema (per-concept evidence).
    """
    concept_mastery = progress_data.get("concept_mastery", {}) or {}
    attempts_by_concept: Dict[str, List[Dict]] = {}
    for a in progress_data.get("attempts", []) or []:
        attempts_by_concept.setdefault(a.get("concept", "general"), []).append(a)

    state: Dict[str, Dict] = {}
    for concept, score in concept_mastery.items():
        evidence = build_evidence(attempts_by_concept.get(concept, []))
        status = mastery_state(float(score) if score is not None else None, evidence)
        observed_errors: Dict[str, int] = {}
        for a in attempts_by_concept.get(concept, []):
            et = a.get("error_type")
            if et:
                observed_errors[et] = observed_errors.get(et, 0) + 1
        state[concept] = {
            "status": status,
            "status_label": MASTERY_STATE_LABELS[status],
            "score": float(score) if score is not None else None,
            "evidence": evidence,
            "observed_errors": sorted(observed_errors.items(), key=lambda x: -x[1]),
        }
    return state


# --- Hybrid (rule + LLM) layer ----------------------------------------------

_LANG_NAMES = {"en": "English", "fr": "French", "es": "Spanish", "de": "German", "it": "Italian", "pt": "Portuguese"}


def _toml_get(text: str, key: str) -> Optional[str]:
    m = re.search(rf'^\s*{re.escape(key)}\s*=\s*"([^"]*)"', text, re.MULTILINE)
    return m.group(1) if m else None


def _read_codewhale_config() -> Dict:
    """Best-effort reuse of the Codewhale provider config (~/.codewhale)."""
    home = Path.home()
    cfg_path = home / ".codewhale" / "config.toml"
    secrets_path = home / ".codewhale" / "secrets" / "secrets.json"
    base_url, model, api_key = None, None, None
    try:
        text = cfg_path.read_text(encoding="utf-8")
        base_url = _toml_get(text, "base_url")
        model = _toml_get(text, "default_text_model")
    except OSError:
        pass
    try:
        data = json.loads(secrets_path.read_text(encoding="utf-8"))
        entries = data.get("entries", {}) or {}
        api_key = entries.get("deepseek") or (next(iter(entries.values())) if entries else None)
    except (OSError, json.JSONDecodeError, StopIteration):
        pass
    return {"base_url": base_url, "model": model, "api_key": api_key}


LLM_CONFIG_PATH = Path.home() / ".codewhale" / "tutor_llm.json"


def read_llm_config_file() -> Dict:
    try:
        return json.loads(LLM_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def write_llm_config_file(config: Dict) -> None:
    LLM_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LLM_CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


def load_llm_config() -> Dict:
    """Resolve an LLM endpoint: env vars → ~/.codewhale/tutor_llm.json → Codewhale config.

    The frontend Settings page writes ``tutor_llm.json``, so the user can switch
    between providers (DeepSeek, Ollama, any OpenAI-compatible server) at runtime.
    """
    env = os.environ
    if env.get("TUTOR_LLM_DISABLE") in ("1", "true", "yes"):
        return {"enabled": False}

    base = (env.get("TUTOR_LLM_BASE_URL") or env.get("OPENAI_BASE_URL")
            or env.get("OLLAMA_BASE_URL") or env.get("OLLAMA_HOST"))
    key = env.get("TUTOR_LLM_API_KEY") or env.get("OPENAI_API_KEY") or env.get("ANTHROPIC_API_KEY")
    model = env.get("TUTOR_LLM_MODEL") or env.get("OPENAI_MODEL")

    file_cfg = read_llm_config_file()
    base = base or file_cfg.get("base_url")
    model = model or file_cfg.get("model")
    key = key or file_cfg.get("api_key")
    file_disabled = file_cfg.get("enabled") is False

    cfg = _read_codewhale_config()
    if cfg:
        base = base or cfg.get("base_url")
        model = model or cfg.get("model")
        key = key or cfg.get("api_key")

    # Default DeepSeek base URL when a key exists but no URL is set.
    if key and not base:
        base = "https://api.deepseek.com/beta"

    if base and not base.startswith(("http://", "https://")):
        base = "http://" + base  # e.g. plain `localhost:11434` for Ollama

    return {
        "base_url": base,
        "api_key": key,
        "model": model,
        "timeout": float(env.get("TUTOR_LLM_TIMEOUT", "30") or 30),
        "enabled": bool(base and model) and not file_disabled,
    }


def _http_post_json(url: str, payload: Dict, headers: Dict, timeout: float) -> Dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    return json.loads(body)


class LlmClient:
    """Minimal OpenAI-compatible chat client (works with DeepSeek, OpenAI, Ollama…)."""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or load_llm_config()
        self.enabled = bool(self.config.get("enabled"))
        self.base_url = (self.config.get("base_url") or "").rstrip("/")
        self.api_key = self.config.get("api_key")
        self.model = self.config.get("model")
        self.timeout = float(self.config.get("timeout", 30) or 30)

    def chat(self, system: str, user: str, temperature: float = 0.4, max_tokens: int = 800) -> Optional[str]:
        if not self.enabled:
            return None
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        try:
            data = _http_post_json(self.base_url + "/chat/completions", payload, headers, self.timeout)
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, json.JSONDecodeError, KeyError):
            return None
        choices = data.get("choices") or []
        if not choices:
            return None
        return (choices[0].get("message") or {}).get("content")


_LLM: Optional[LlmClient] = None


def get_llm() -> LlmClient:
    global _LLM
    if _LLM is None:
        try:
            _LLM = LlmClient()
        except Exception:  # noqa: BLE001
            _LLM = LlmClient({"enabled": False})
    return _LLM


def reset_llm() -> None:
    """Drop the cached client so new settings take effect on the next call."""
    global _LLM
    _LLM = None


def _http_get_json(url: str, timeout: float) -> Dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    return json.loads(body)


def list_ollama_models(base_url: Optional[str] = None) -> Dict:
    """Probe a local Ollama instance and list its models (best effort)."""
    host = (base_url or os.environ.get("OLLAMA_HOST") or "http://localhost:11434").rstrip("/")
    if not host.startswith(("http://", "https://")):
        host = "http://" + host
    try:
        data = _http_get_json(host + "/api/tags", timeout=2.0)
        models = [m.get("name") for m in (data.get("models") or []) if m.get("name")]
        return {
            "available": True,
            "tags_base_url": host,
            "openai_base_url": host + "/v1",
            "models": models,
        }
    except Exception:  # noqa: BLE001
        return {"available": False, "tags_base_url": host, "openai_base_url": host + "/v1", "models": []}


# --- Rule-based coach (deterministic fallback, localised) --------------------

_RULE_TEXT = {
    "greet": {
        "en": "Ahoy there, knowledge seeker! 🐋 I'm Prof. Whaley. Ask me for your quests, weaknesses, a quiz, a review, or just tell me what you want to learn.",
        "fr": "Ahoy, explorateur du savoir ! 🐋 Je suis Prof. Whaley. Demande-moi tes quêtes, tes points faibles, un quiz, une révision — ou dis-moi ce que tu veux apprendre.",
        "es": "¡Ahoy, buscador de conocimiento! 🐋 Soy Prof. Whaley. Pídeme tus misiones, tus puntos débiles, un test, un repaso — o cuéntame qué quieres aprender.",
        "de": "Ahoi, Wissenssuchender! 🐋 Ich bin Prof. Whaley. Frag mich nach deinen Quests, Schwächen, einem Quiz oder einer Wiederholung.",
    },
    "help": {
        "en": "I can help with: \"quests\", \"weaknesses\", \"quiz me\", \"review\", \"cheatsheet\", \"exam/gauntlet\", \"how am I doing?\", or a mood like \"I feel stressed\".",
        "fr": "Je peux t'aider avec : « quêtes », « points faibles », « quiz », « révision », « fiche », « examen », « où j'en suis ? », ou une humeur comme « je suis stressé ».",
        "es": "Puedo ayudarte con: « misiones », « debilidades », « test », « repaso », « chuleta », « examen », « ¿cómo voy? », o un estado como « estoy estresado ».",
        "de": "Ich helfe mit: „Quests“, „Schwächen“, „Quiz“, „Wiederholung“, „Spickzettel“, „Prüfung“, „Wie stehe ich?“, oder Stimmung wie „Ich bin gestresst“.",
    },
    "no_data": {
        "en": "Drop your syllabi into ~/.codewhale/syllabi and press Sync, then I'll have plenty for you.",
        "fr": "Dépose tes syllabus dans ~/.codewhale/syllabi puis synchronise — j'aurai alors de quoi t'aider.",
        "es": "Coloca tus programas en ~/.codewhale/syllabi y sincroniza; entonces tendré mucho para ti.",
        "de": "Lege deine Lehrpläne in ~/.codewhale/syllabi ab und synchronisiere — dann habe ich viel für dich.",
    },
    "mood": {
        "en": "How are you feeling today — 😩 stressed, 😴 tired, ⚡ energetic, or 🤔 curious? I'll tune the session to match.",
        "fr": "Comment te sens-tu aujourd'hui — 😩 stressé, 😴 fatigué, ⚡ énergique ou 🤔 curieux ? J'adapte la séance.",
        "es": "¿Cómo te sientes hoy — 😩 estresado, 😴 cansado, ⚡ enérgico o 🤔 curioso? Adaptaré la sesión.",
        "de": "Wie fühlst du dich heute — 😩 gestresst, 😴 müde, ⚡ energiegeladen oder 🤔 neugierig? Ich passe die Sitzung an.",
    },
}


def _L(locale: str, key: str) -> str:
    d = _RULE_TEXT.get(key, {})
    return d.get(locale) or d.get("en") or ""


def rule_reply(message: str, context: Dict) -> str:
    """Deterministic, localised coach used whenever no LLM is available."""
    locale = (context or {}).get("locale") or "en"
    t = (message or "").strip().lower()
    weaknesses = (context or {}).get("weaknesses") or []
    next_action = (context or {}).get("next_action") or {}
    syllabi = (context or {}).get("syllabi") or []
    exam_count = (context or {}).get("exam_count") or 0

    if not t or re.search(r"(^|\s)(hi|hello|hey|salut|bonjour|hola|yo)\b", t):
        if not syllabi and not weaknesses:
            return _L(locale, "greet") + "\n\n" + _L(locale, "no_data")
        return _L(locale, "greet")

    if re.search(r"help|aide|command|what can|start", t):
        return _L(locale, "help")

    if re.search(r"quest|mission|daily|today|aujourd", t):
        if next_action:
            return f"🎯 {next_action.get('label')} — {next_action.get('title')}. {next_action.get('reason')}"
        return _L(locale, "no_data")

    if re.search(r"weak|faible|difficult|struggle|galer|bloque|radar", t):
        if weaknesses:
            return "🧭 " + " · ".join(weaknesses[:5])
        return "🎉 " + _L(locale, "greet")

    if re.search(r"review|révis|revis|spaced|memory|rappel", t):
        return "📖 " + _L(locale, "help")

    if re.search(r"exam|test|mock|gauntlet|contrôle|controle|brevet|boss", t):
        return f"⚔️ {exam_count} " + _L(locale, "no_data")

    if re.search(r"cheatsheet|fich|triche|summary|résumé|resume|map|scroll", t):
        return "🗺️ " + _L(locale, "no_data")

    if re.search(r"quiz|question|interro|practice|entraîne|entraine|exercice|problème|probleme", t):
        return "🎲 " + _L(locale, "help")

    if re.search(r"feeling|mood|stress|tired|fatigu|épuis|epuis|energ|curious|curieux|anxie", t):
        return _L(locale, "mood")

    if re.search(r"progress|level|niveau|xp|avanc|how am i|doing|master", t):
        if next_action:
            return f"🎯 {next_action.get('label')} — {next_action.get('title')}. {next_action.get('reason')}"
        return _L(locale, "greet")

    # Default: Socratic nudge toward the recommended next action.
    if next_action:
        if locale == "fr":
            return f"{next_action.get('label')} : « {next_action.get('title')} ». {next_action.get('reason')}\n\nQu'est-ce que tu comprends déjà, et où est-ce que ça devient flou ?"
        return f"{next_action.get('label')} on « {next_action.get('title')} ». {next_action.get('reason')}\n\nWhat do you already understand, and where does it get foggy?"
    return _L(locale, "greet")


def _system_prompt(context: Dict) -> str:
    persona = (context or {}).get("persona") or {}
    strict = float(persona.get("strict", 0.5))
    humor = float(persona.get("humor", 0.4))
    locale = (context or {}).get("locale") or "en"
    lang = _LANG_NAMES.get(locale, "English")
    lines = [
        "You are Prof. Whaley, a Socratic, metacognitive tutor.",
        f"Strictness: {strict:.2f} (0 = gentle cheerleader, 1 = demanding drill sergeant).",
        f"Humor: {humor:.2f} (0 = dead serious, 1 = playful jester).",
        f"Always answer in {lang}.",
        "Never reveal the final answer. Ask guiding questions, praise effort, and adapt to the learner's state.",
    ]
    weaknesses = (context or {}).get("weaknesses") or []
    if weaknesses:
        lines.append("Known weaknesses: " + ", ".join(weaknesses[:5]) + ".")
    next_action = (context or {}).get("next_action") or {}
    if next_action:
        lines.append(f"Recommended next action: {next_action.get('label')} on « {next_action.get('title')} » — {next_action.get('reason')}")
    lines.append("Keep replies concise (2-5 sentences) unless the learner asks for a detailed explanation.")
    return "\n".join(lines)


def tutor_reply(message: str, context: Dict, llm: Optional[LlmClient] = None) -> Dict:
    """Hybrid tutor reply: LLM when available, deterministic rules otherwise."""
    client = llm or get_llm()
    if client and client.enabled:
        try:
            text = client.chat(_system_prompt(context), message or "")
            if text and text.strip():
                return {"reply": text.strip(), "source": "llm"}
        except Exception:  # noqa: BLE001
            pass
    return {"reply": rule_reply(message, context), "source": "rules"}


def generate_activity(competence: Dict, state: Optional[Dict] = None,
                      llm: Optional[LlmClient] = None) -> Dict:
    """Hybrid task generator: LLM drafts the task when possible, rules otherwise.

    Returns a task dict with ``evaluates``, ``hints`` and a text — always valid
    even with no LLM, so the learner can keep training offline.
    """
    title = competence.get("intitule") or competence.get("name", "the topic")
    cid = competence.get("id", "unknown")
    status = (state or {}).get("status", "non_aborde")

    base = {
        "competence": cid,
        "title": title,
        "evaluates": [{"competence": cid, "weight": 1.0}],
        "hints": scaffold(3),
    }

    client = llm or get_llm()
    if client and client.enabled:
        try:
            prompt = (
                f"Create ONE short practice task (2-4 lines) for the competence: {title}.\n"
                f"Learner mastery state: {status}.\n"
                "Make it observable and appropriate to that state, and give 3 progressive hints. "
                "Return only the task text."
            )
            text = client.chat("You generate short, well-scoped learning tasks.", prompt, temperature=0.5)
            if text and text.strip():
                base["text"] = text.strip()
                base["generator"] = "llm"
                return base
        except Exception:  # noqa: BLE001
            pass

    base["text"] = f"Reformule puis résous un exercice sur « {title} » en explicitant ta démarche."
    base["generator"] = "rules"
    return base
