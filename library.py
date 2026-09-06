#!/usr/bin/env python3
"""
Tutor library ingestion engine.

The single source of truth for turning a folder of raw documents (Markdown,
plain text, or PDF) into:

  * an organised syllabus (one JSON per syllabus),
  * a generated cheatsheet (one Markdown per syllabus),
  * inferred practice/mock exams,
  * analysed real exams (one JSON per exam),
  * a library registry (`registry.json`) that indexes everything.

The dashboard and the `syllabus_processor` MCP server both call
:func:`sync_library` so they always agree on the state of the library.

All paths are rooted at ``CODewhale_HOME`` (default ``~/.codewhale``) so the
engine can be pointed at a scratch directory in tests.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import PyPDF2
except Exception:  # pragma: no cover - PDF support is optional
    PyPDF2 = None


# --- Paths -------------------------------------------------------------------
CW_HOME = Path(os.environ.get("CODewhale_HOME", str(Path.home() / ".codewhale")))
SYLLABI_DIR = CW_HOME / "syllabi"
EXAMS_DIR = CW_HOME / "exams"
CHEATSHEETS_DIR = CW_HOME / "cheatsheets"
PROGRESS_DIR = CW_HOME / "tutor_progress"
REGISTRY_PATH = CW_HOME / "registry.json"

# Raw source files that count as "documents the user dumped".
SOURCE_EXTENSIONS = {".md", ".txt", ".markdown", ".text", ".rst", ".pdf"}


def ensure_dirs() -> None:
    for d in (SYLLABI_DIR, EXAMS_DIR, CHEATSHEETS_DIR, PROGRESS_DIR):
        d.mkdir(parents=True, exist_ok=True)


# --- Text helpers ------------------------------------------------------------
def _strip_accents(text: str) -> str:
    text = text.lower()
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def _detect_language(text: str) -> str:
    if re.search(r"[éèêëàâäôûüîïç]", text):
        return "French"
    if re.search(r"[ñáéíóúü]", text):
        return "Spanish"
    if re.search(r"[äöüß]", text):
        return "German"
    if re.search(r"[가-힣]", text):
        return "Korean"
    if re.search(r"[一-龯]", text):
        return "Chinese"
    return "English"


def _slugify(text: str) -> str:
    s = _strip_accents(text)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "syllabus"


def _read_pdf_text(file_path: Path) -> str:
    if PyPDF2 is None:
        raise RuntimeError("PyPDF2 is not installed; cannot read PDF files")
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        return "".join(page.extract_text() or "" for page in reader.pages)


def _read_text(file_path: Path) -> str:
    if file_path.suffix.lower() == ".pdf":
        return _read_pdf_text(file_path)
    return file_path.read_text(encoding="utf-8", errors="replace")


def fingerprint(file_path: Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# --- Front matter / document splitting --------------------------------------
def _is_header(lines: List[str], i: int) -> bool:
    """Return True when lines[i] opens a YAML-ish front-matter header."""
    if i < 0 or i >= len(lines) or lines[i].strip() != "---":
        return False
    j = i + 1
    found_key = False
    while j < len(lines) and lines[j].strip() != "---":
        line = lines[j].strip()
        if not line:
            j += 1
            continue
        if re.match(r"^[\w-]+\s*:", line):
            found_key = True
        else:
            return False
        j += 1
    return found_key and j < len(lines) and lines[j].strip() == "---"


def _header_end(lines: List[str], i: int) -> int:
    j = i + 1
    while j < len(lines) and lines[j].strip() != "---":
        j += 1
    return j


def _parse_meta(lines: List[str]) -> Dict[str, str]:
    meta: Dict[str, str] = {}
    for raw in lines:
        line = raw.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip().lower()] = value.strip().strip('"').strip("'")
    return meta


def split_blocks(text: str) -> List[Dict]:
    """Split a document into one or more ``{"meta": ..., "body": ...}`` blocks.

    A block is introduced by an optional front-matter header::

        ---
        id: algebra3
        name: Algebra III
        language: French
        ---

    A file without front matter becomes a single block with empty meta. Repeating
    these headers lets one Markdown file describe several syllabi.
    """
    lines = text.split("\n")
    n = len(lines)
    idx = 0
    while idx < n and not lines[idx].strip():
        idx += 1

    first = None
    for k in range(idx, n):
        if _is_header(lines, k):
            first = k
            break

    if first is None:
        return [{"meta": {}, "body": text}]

    blocks: List[Dict] = []
    if first > idx:
        blocks.append({"meta": {}, "body": "\n".join(lines[idx:first])})

    while True:
        start = None
        for k in range(idx, n):
            if _is_header(lines, k):
                start = k
                break
        if start is None:
            break
        end = _header_end(lines, start)
        meta = _parse_meta(lines[start + 1:end])

        next_start = None
        for k in range(end + 1, n):
            if _is_header(lines, k):
                next_start = k
                break

        if next_start is None:
            blocks.append({"meta": meta, "body": "\n".join(lines[end + 1:])})
            idx = n
        else:
            blocks.append({"meta": meta, "body": "\n".join(lines[end + 1:next_start])})
            idx = next_start
    return blocks


# --- Syllabus parsing --------------------------------------------------------
def _new_concept(name: str, module: str = "") -> Dict:
    return {
        "name": name,
        "description": "",
        "prerequisites": [],
        "difficulty": 2,
        "exam_frequency": 0,
        "common_misconceptions": [],
        "related_questions": [],
        "module": module,
    }


def parse_markdown_syllabus(text: str) -> Tuple[List[Dict], List[str]]:
    concepts: List[Dict] = []
    objectives: List[str] = []
    current_module = ""
    current: Optional[Dict] = None
    seen_module = False

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("# "):
            seen_module = True
            current_module = line[2:].strip()
            continue
        if line.startswith("## "):
            seen_module = True
            title = line[3:].strip()
            current = _new_concept(title, current_module)
            concepts.append(current)
            continue
        if line.startswith("### "):
            if current is not None:
                current["related_questions"].append(line[4:].strip())
            continue
        if raw_line[:1] in (" ", "\t"):
            if not seen_module:
                objectives.append(line)
            elif current is not None:
                current["related_questions"].append(line)
            continue
        if line.startswith("-") or line.startswith("*") or line.startswith("•"):
            topic = line.lstrip("-*• \t").strip()
            if not topic:
                continue
            if not seen_module:
                objectives.append(topic)
            elif current is not None:
                current["related_questions"].append(topic)

    for c in concepts:
        if c["related_questions"]:
            c["description"] = "; ".join(c["related_questions"][:8])
    return concepts, objectives


def parse_pdf_syllabus(text: str) -> Tuple[List[Dict], List[str]]:
    concepts: List[Dict] = []
    chapter_pattern = r"(?:Chapter|Topic|Module|Unit|Section)\s+(\d+):?\s*([^\n]+)"
    chapters = re.findall(chapter_pattern, text, re.IGNORECASE)

    for i, (num, title) in enumerate(chapters):
        concepts.append({
            **_new_concept(title.strip()),
            "description": f"Chapter {num}: {title.strip()}",
            "difficulty": 1 if i < 3 else 2 if i < 6 else 3,
        })

    objective_pattern = r"(?:Learning Objective|Objective|Goal)\s*:?\s*([^\n]+)"
    objectives = [o.strip() for o in re.findall(objective_pattern, text, re.IGNORECASE)]

    if not concepts:
        sections = re.split(r"\n\s*(?=\d+\.\s|\w+\.\s)", text)
        for i, section in enumerate(sections[:10]):
            lines = section.strip().split("\n")
            if lines:
                concepts.append({
                    **_new_concept(lines[0][:50].strip()),
                    "description": lines[0][:200].strip(),
                    "difficulty": 1 if i < 3 else 2,
                })
    return concepts, objectives


def parse_source(body: str, suffix: str) -> Tuple[List[Dict], List[str]]:
    if suffix in {".md", ".txt", ".markdown", ".text", ".rst"}:
        return parse_markdown_syllabus(body)
    return parse_pdf_syllabus(body)


# --- Concept relationship helpers -------------------------------------------
_ROMAN = {
    "i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5,
    "vi": 6, "vii": 7, "viii": 8, "ix": 9, "x": 10,
}


def _family_and_level(name: str) -> Tuple[str, int]:
    norm = _strip_accents(name)
    m = re.search(r"\b(i{1,3}|iv|v|vi{0,3}|ix|x)\b\s*$", norm)
    level = _ROMAN.get(m.group(1), 0) if m else 0
    family = re.sub(r"\s+(i{1,3}|iv|v|vi{0,3}|ix|x)\s*$", "", norm).strip()
    return family, level


def infer_prerequisites(concept_names: List[str]) -> Dict[str, List[str]]:
    by_family: Dict[str, List[Tuple[int, str]]] = {}
    for name in concept_names:
        family, level = _family_and_level(name)
        if level:
            by_family.setdefault(family, []).append((level, name))

    prereqs: Dict[str, List[str]] = {}
    for entries in by_family.values():
        entries.sort(key=lambda x: x[0])
        for i in range(1, len(entries)):
            prereqs[entries[i][1]] = [entries[i - 1][1]]
    return prereqs


def topological_order(concepts: List[Dict]) -> List[Dict]:
    by_name = {c["name"]: c for c in concepts}
    in_degree = {
        c["name"]: len([p for p in c.get("prerequisites", []) if p in by_name])
        for c in concepts
    }
    dependents = {c["name"]: [] for c in concepts}
    for c in concepts:
        for p in c.get("prerequisites", []):
            if p in dependents:
                dependents[p].append(c["name"])

    queue = [c["name"] for c in concepts if in_degree[c["name"]] == 0]
    order: List[Dict] = []
    while queue:
        name = queue.pop(0)
        order.append(by_name[name])
        for dep in dependents[name]:
            in_degree[dep] -= 1
            if in_degree[dep] == 0:
                queue.append(dep)
    return order if len(order) == len(concepts) else concepts


def _dedupe_concepts(concepts: List[Dict]) -> List[Dict]:
    seen: Dict[str, Dict] = {}
    order: List[str] = []
    for c in concepts:
        key = _strip_accents(c["name"])
        if key in seen:
            existing = seen[key]
            existing["related_questions"] = list(dict.fromkeys(
                existing.get("related_questions", []) + c.get("related_questions", [])
            ))
            if c.get("description") and not existing.get("description"):
                existing["description"] = c["description"]
            continue
        seen[key] = dict(c)
        order.append(key)
    return [seen[k] for k in order]


# --- Competence model (curriculum → knowledge → observable competencies) -----

_COMPETENCE_TYPE_KEYWORDS = [
    ("connaissance", ["definir", "identifier", "nommer", "lister", "connaitre", "define", "identify", "vocabulaire", "definition", "notion", "restituer"]),
    ("comprehension", ["expliquer", "reformuler", "distinguer", "interpreter", "comprendre", "explain", "understand", "interpret", "decrire", "décrire"]),
    ("procedure", ["calculer", "executer", "appliquer", "methode", "algorithme", "procedure", "procédure", "compute", "apply", "executer", "resoudre", "résoudre", "determiner", "déterminer"]),
    ("raisonnement", ["demontrer", "justifier", "prouver", "deduire", "raisonner", "argumenter", "prove", "justify", "reason", "deduce", "démontrer", "déduire"]),
    ("application", ["appliquer", "mobiliser", "utiliser", "apply", "use", "mobilize", "reinvestir", "transfert"]),
    ("analyse", ["analyser", "comparer", "decomposer", "diagnostiquer", "analyze", "compare", "decompose", "critiquer", "evaluer", "évaluer"]),
    ("communication", ["rediger", "presenter", "communiquer", "expliquer", "write", "present", "rédiger", "présenter", "justifier"]),
    ("outil", ["coder", "programmer", "logiciel", "langage", "python", "code", "software", "tool", "instrument", "deboguer", "tester"]),
    ("synthese", ["synthetiser", "combiner", "integrer", "synthèse", "synthesize", "combine", "integrate", "croiser", "mobiliser plusieurs"]),
]

_COMPETENCE_TYPE_LABELS = {
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

_ACTION_VERBS = [
    "calculer", "résoudre", "resoudre", "démontrer", "demontrer", "justifier", "expliquer",
    "identifier", "interpréter", "interpreter", "appliquer", "analyser", "comparer", "déduire",
    "deduire", "prouver", "rédiger", "rediger", "présenter", "presenter", "coder", "programmer",
    "modéliser", "modeliser", "vérifier", "verifier", "estimer", "déterminer", "determiner",
]


def _competence_id(discipline: str, domain: str, name: str) -> str:
    return f"{_slugify(discipline)}.{_slugify(domain)}.{_slugify(name)}"


def _classify_competence_types(name: str, description: str) -> List[str]:
    hay = _strip_accents((name or "") + " " + (description or ""))
    types = []
    for ctype, kws in _COMPETENCE_TYPE_KEYWORDS:
        if any(kw in hay for kw in kws):
            types.append(ctype)
    if not types:
        types.append("comprehension")
    return types


def _action_verbs(name: str, description: str) -> List[str]:
    hay = _strip_accents((name or "") + " " + (description or ""))
    found = []
    for v in _ACTION_VERBS:
        if v in hay and v not in found:
            found.append(v)
        if len(found) >= 3:
            break
    return found


def _success_criteria(types: List[str]) -> List[str]:
    criteria = {
        "connaissance": "Restitue ou identifie la notion sans aide.",
        "comprehension": "Reformule et distingue correctement les idées clés.",
        "procedure": "Exécute les étapes de la méthode dans l'ordre attendu.",
        "raisonnement": "Justifie le choix de la méthode et la conclusion.",
        "application": "Mobilise la compétence dans une situation donnée.",
        "analyse": "Décompose, compare ou interprète les éléments pertinents.",
        "communication": "Présente et rédige une production conforme aux attentes.",
        "outil": "Utilise correctement l'outil, le langage ou l'instrument.",
        "synthese": "Combine plusieurs compétences pour produire une réponse intégrée.",
    }
    out = []
    for t in types:
        if t in criteria and criteria[t] not in out:
            out.append(criteria[t])
    out.append("Produit une réponse correcte de façon autonome.")
    return out


def _default_frequent_errors(types: List[str]) -> List[str]:
    defaults = {
        "procedure": "Oubli ou inversion d'une étape de la méthode.",
        "raisonnement": "Justification insuffisante du choix de la méthode.",
        "application": "Erreur de sélection de la formule ou de la méthode.",
        "comprehension": "Confusion entre notions proches.",
    }
    out = []
    for t in types:
        if t in defaults and defaults[t] not in out:
            out.append(defaults[t])
    return out or ["Erreur non documentée."]


def _observable_title(name: str, verbs: List[str]) -> str:
    if not verbs:
        return name
    return f"{name} — {', '.join(verbs[:2])}"


def _concept_to_competence(c: Dict, syllabus: Dict) -> Dict:
    name = c.get("name", "")
    domain = c.get("module") or "General"
    discipline = syllabus.get("discipline", "general")
    types = _classify_competence_types(name, c.get("description", ""))
    verbs = _action_verbs(name, c.get("description", ""))
    has_prereqs = bool(c.get("prerequisites"))
    return {
        "id": _competence_id(discipline, domain, name),
        "name": name,
        "intitule": _observable_title(name, verbs),
        "discipline": discipline,
        "domaine": domain,
        "type": types,
        "type_labels": [_COMPETENCE_TYPE_LABELS.get(t, t) for t in types],
        "connaissances": c.get("related_questions", [])[:6],
        "actions": verbs,
        "criteres_reussite": _success_criteria(types),
        "prerequis": list(c.get("prerequisites", [])),
        "erreurs_frequentes": list(c.get("common_misconceptions", [])) or _default_frequent_errors(types),
        "difficulte": c.get("difficulty", 2),
        "source_status": syllabus.get("source_status", "document_interne"),
        "inferred": ["type", "criteres_reussite", "erreurs_frequentes"] + (["prerequis"] if has_prereqs else []),
        "module": c.get("module", ""),
        "order": c.get("order"),
    }


def _infer_discipline(syllabus: Dict) -> str:
    counts: Dict[str, int] = {}
    for c in syllabus.get("concepts", []):
        cat = _concept_category(c)
        if cat != "general":
            counts[cat] = counts.get(cat, 0) + 1
    if not counts:
        return "general"
    top = max(counts, key=counts.get)
    return {
        "linear_algebra": "mathematiques",
        "probability": "mathematiques",
        "statistics": "mathematiques",
        "calculus_analysis": "mathematiques",
        "python_programming": "informatique",
        "economics": "economie",
    }.get(top, "general")


def _build_competence_graph(syllabus: Dict) -> Dict:
    comps = syllabus.get("competences", [])
    by_name = {c["name"]: c for c in comps if c.get("name")}
    nodes = [
        {"id": c["id"], "name": c["name"], "intitule": c.get("intitule", c["name"]),
         "type": c.get("type", []), "domaine": c.get("domaine")}
        for c in comps
    ]
    edges = []
    for c in comps:
        for p in c.get("prerequis", []):
            pc = by_name.get(p)
            if pc:
                edges.append({"source": pc["id"], "target": c["id"], "type": "prerequis", "force": "forte"})
    return {"nodes": nodes, "edges": edges}


# --- Exam parsing ------------------------------------------------------------
_CATEGORY_KEYWORDS = [
    ("linear_algebra", ["valeur propre", "diagonalis", "matrice", "determinant", "produit scalaire", "eigenvalue", "matrix"]),
    ("probability", ["variable aleatoire", "esperance", "variance", "bayes", "probabilite", "covariance", "probability", "distribution"]),
    ("statistics", ["estimateur", "estimation", "echantillon", "regression", "estimator", "hypothesis", "p-value"]),
    ("calculus_analysis", ["derivee", "integrale", "serie", "suite", "taylor", "derivative", "integral"]),
    ("python_programming", ["python", "dictionnaire", "fonction", "classe", "api", "algorithm", "dictionary", "object"]),
    ("economics", ["offre", "demande", "marche", "inflation", "gdp", "supply", "demand", "elasticite"]),
]

_STOPWORDS = {
    "the", "and", "for", "are", "was", "were", "with", "that", "this", "from", "have",
    "des", "les", "une", "est", "sont", "dans", "pour", "par", "sur", "avec", "plus",
    "que", "qui", "comme", "leur", "leurs", "notre", "votre", "entre", "mais", "donc",
}


def _word_tokens(text: str) -> set:
    words = re.findall(r"[a-z0-9]+", _strip_accents(text))
    return {w for w in words if len(w) >= 4 and w not in _STOPWORDS}


def _concept_tokens(c: Dict) -> set:
    text = " ".join([c.get("name", ""), c.get("description", "")]
                    + c.get("related_questions", [])[:8])
    return _word_tokens(text)


def _concept_category(c: Dict) -> str:
    hay = _strip_accents(c.get("name", "") + " " + c.get("description", ""))
    for category, kws in _CATEGORY_KEYWORDS:
        if any(kw in hay for kw in kws):
            return category
    return "general"


def parse_exam_questions(text: str) -> List[Dict]:
    questions: List[str] = []
    patterns = [
        r"(\d+)[\.\)]\s*([^\n]+(?:\n(?!\d+[\.\)])[^\n]+)*)",
        r"Question\s+(\d+)\s*[:\.\)]?\s*([^\n]+(?:\n(?!Question\s+\d+)[^\n]+)*)",
        r"[Qq](\d+)\s*[:\.\)]?\s*([^\n]+(?:\n(?!Q\d+)[^\n]+)*)",
        r"Exercice\s+(\d+)\s*[:\.\)]?\s*([^\n]+(?:\n(?!Exercice\s+\d+)[^\n]+)*)",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, text, re.MULTILINE):
            q_text = match[1].strip() if len(match) == 2 else match[0].strip()
            if len(q_text) > 10:
                questions.append(q_text)
    if not questions:
        for section in re.split(r"\n\s*\n", text):
            if len(section) > 50 and any(c.isdigit() for c in section[:50]):
                questions.append(section.strip())

    result = []
    for i, q in enumerate(questions, 1):
        result.append({
            "number": i,
            "text": q[:500],
            "concept": _question_concept(q),
            "difficulty": _estimate_difficulty(q),
        })
    return result


def _question_concept(text: str) -> str:
    norm = _strip_accents(text)
    for concept, kws in _CATEGORY_KEYWORDS:
        if any(kw in norm for kw in kws):
            return concept
    return "general"


def _estimate_difficulty(text: str) -> float:
    difficulty = 0.5
    length = len(text)
    if length < 50:
        difficulty -= 0.1
    elif length > 200:
        difficulty += 0.1
    technical = [
        r"\b(concept|theoretical|principle|derive|analyze|evaluate|critique)\b",
        r"\b(equation|formula|algorithm|function|variable)\b",
    ]
    difficulty += min(0.2, sum(len(re.findall(p, text.lower())) for p in technical) * 0.05)
    if "if" in text.lower() or "when" in text.lower() or "unless" in text.lower():
        difficulty += 0.1
    return max(0.0, min(1.0, difficulty))


# --- Mock exam ---------------------------------------------------------------
_MATH_WORDS = [
    "matrice", "diagonalis", "vecteur", "probabilite", "esperance", "variance",
    "derivee", "integrale", "fonction", "equation", "determinant", "estimation",
    "covariance", "matrix", "eigenvalue", "derivative", "integral", "probability",
]


def _is_mathy(concept: Dict) -> bool:
    hay = _strip_accents(concept["name"] + " " + concept.get("description", ""))
    return any(w in hay for w in _MATH_WORDS)


def build_mock_exam(syllabus: Dict, num_questions: int = 6) -> Dict:
    concepts = syllabus.get("concepts", [])
    questions: List[Dict] = []
    if not concepts:
        return {"id": f"{syllabus['id']}_mock", "syllabus_id": syllabus["id"], "questions": []}

    comp_by_name = {c["name"]: c for c in syllabus.get("competences", [])}
    discipline = syllabus.get("discipline", "general")

    n = max(1, min(num_questions, 12))
    for i in range(n):
        c = concepts[i % len(concepts)]
        name = c.get("name", "the topic")
        if _is_mathy(c):
            text = f"Compute and justify: {name}. Show your working."
            qtype = "calculation"
        else:
            text = f"Explain the key ideas of “{name}” and give a concrete example."
            qtype = "short_answer"
        cid = (comp_by_name.get(name) or {}).get("id") or _competence_id(
            discipline, _slugify(c.get("module") or "General"), name)
        diff = c.get("difficulty", 2) or 2
        questions.append({
            "number": i + 1,
            "text": text,
            "concept": name,
            "type": qtype,
            "difficulty": round(c.get("difficulty", 2) / 5, 2),
            "bloom_level": "apply" if qtype == "calculation" else "understand",
            "evaluates": [{"competence": cid, "weight": 1.0}],
            "complexity": {
                "conceptualisation": max(0, min(5, diff)),
                "execution": max(0, min(5, diff)),
                "interpretation": max(0, min(5, diff - 1)),
                "raisonnement": max(0, min(5, diff - 1)),
                "autonomie": max(0, min(5, diff - 2)),
                "transfert": max(0, min(5, diff - 3)),
                "integration": max(0, min(5, diff - 3)),
            },
            "hints": [
                {"level": 1, "content": "Reformule ce que la question demande avec tes propres mots."},
                {"level": 2, "content": "Identifie la notion et la méthode concernées avant de commencer."},
                {"level": 3, "content": "Décompose en petites étapes et vérifie chacune."},
            ],
        })

    return {
        "id": f"{syllabus['id']}_mock",
        "syllabus_id": syllabus["id"],
        "kind": "mock",
        "questions": questions,
        "concepts_tested": [c["name"] for c in concepts[:n]],
        "difficulty_distribution": {
            "easy": sum(1 for q in questions if q["difficulty"] < 0.34),
            "medium": sum(1 for q in questions if 0.34 <= q["difficulty"] <= 0.67),
            "hard": sum(1 for q in questions if q["difficulty"] > 0.67),
        },
    }


# --- Cheatsheet --------------------------------------------------------------
def write_cheatsheet(syllabus: Dict, exams: List[Dict]) -> Path:
    concepts = syllabus.get("concepts", [])
    sid = syllabus["id"]
    name = syllabus.get("name", sid)
    language = syllabus.get("language", "English")

    lines = [
        f"# 📚 {name} — Cheatsheet",
        "",
        f"**Language:** {language}",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Total Concepts:** {len(concepts)}",
        f"**Sources:** {', '.join(src.get('file', '') for src in syllabus.get('sources', [])) or '—'}",
        "",
        "---",
        "",
    ]

    path = syllabus.get("learning_path", [])
    if path:
        lines += ["## 🧭 Suggested study path", ""]
        for step in path:
            mod = f" ({step.get('module', '')})" if step.get("module") else ""
            prereqs = f" — after {', '.join(step.get('prerequisites', []))}" if step.get("prerequisites") else ""
            lines.append(f"{step['order']}. **{step['concept']}**{mod}{prereqs} — ~{step.get('estimated_minutes', 30)} min")
        lines += ["", "## 🎯 Key Concepts", ""]
    else:
        lines += ["## 🎯 Key Concepts", ""]

    for i, c in enumerate(concepts, 1):
        diff = c.get("difficulty", 1)
        emoji = "🟢" if diff <= 2 else "🟡" if diff <= 3 else "🔴"
        lines += [
            f"### {i}. {c.get('name', '')}",
            f"{emoji} Difficulty: {diff}/5",
            "",
            f"**Description:** {c.get('description', 'No description available')}",
            "",
            f"**Prerequisites:** {', '.join(c.get('prerequisites', [])) or 'None'}",
            "",
            f"**Exam Frequency:** {c.get('exam_frequency', 0)} time(s)",
            "",
        ]
        related = c.get("related_questions", [])
        if related:
            lines += ["**Topics:**"] + [f"  - {t}" for t in related[:10]] + [""]
        lines += ["---", ""]

    objectives = syllabus.get("learning_objectives", [])
    if objectives:
        lines += ["## 📖 Learning Objectives", ""]
        lines += [f"- {o}" for o in objectives] + [""]

    lines += ["## 💡 Exam Tips", ""]
    linked = [e for e in exams if e.get("syllabus_id") == sid]
    weighted = sorted(
        [c for c in concepts if c.get("exam_frequency", 0) > 0],
        key=lambda c: c.get("exam_frequency", 0),
        reverse=True,
    )[:5]
    if weighted:
        lines += ["Based on the exams linked to this syllabus, focus on:", ""]
        for c in weighted:
            lines.append(f"- **{c['name']}** (tested {c['exam_frequency']} time(s))")
    elif linked:
        counts: Dict[str, int] = {}
        for e in linked:
            for c in e.get("concepts_tested", []):
                counts[c] = counts.get(c, 0) + 1
        if counts:
            lines += ["Based on the exams linked to this syllabus, focus on:", ""]
            for concept, cnt in sorted(counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                lines.append(f"- **{concept}** (appears in {cnt} exam(s))")
        else:
            lines += ["Exam data is linked; review the concepts above."]
    else:
        lines += ["No exam data available yet. A mock exam has been inferred — use it to practice!"]
    lines += ["", "## 🧠 Mnemonic Devices", "", "*Create your own memory aids!*", ""]
    lines += ["- **Acronyms:** a word from first letters", "- **Visualization:** a mental image",
              "- **Chunking:** group information", "- **Story Method:** a connecting narrative", ""]

    cheatsheet_file = CHEATSHEETS_DIR / f"{sid}_cheatsheet.md"
    cheatsheet_file.write_text("\n".join(lines), encoding="utf-8")
    return cheatsheet_file


# --- Registry ----------------------------------------------------------------
def load_registry() -> Dict:
    if not REGISTRY_PATH.exists():
        return {"version": 1, "syllabi": {}, "exams": {}, "sources": {}}
    try:
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"version": 1, "syllabi": {}, "exams": {}, "sources": {}}


def _save_registry(registry: Dict) -> None:
    REGISTRY_PATH.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")


def _scan(dir_path: Path, kind: str) -> List[Dict]:
    results = []
    if not dir_path.exists():
        return results
    for p in sorted(dir_path.iterdir()):
        if not p.is_file() or p.name.startswith("."):
            continue
        if p.suffix.lower() not in SOURCE_EXTENSIONS:
            continue
        results.append({
            "path": p,
            "rel": str(p.relative_to(CW_HOME)),
            "name": p.name,
            "stem": p.stem,
            "suffix": p.suffix.lower(),
            "kind": kind,
            "fp": fingerprint(p),
            "mtime": int(p.stat().st_mtime),
        })
    return results


def _build_syllabi(sources: List[Dict]) -> Dict[str, Dict]:
    grouped: Dict[str, Dict] = {}
    for src in sources:
        try:
            text = _read_text(src["path"])
        except Exception as e:  # noqa: BLE001
            grouped.setdefault("_errors", {"id": "_errors", "name": "Read errors", "concepts": [],
                                          "learning_objectives": [], "sources": [], "errors": []})
            grouped["_errors"]["errors"].append(f"{src['name']}: {e}")
            continue

        blocks = split_blocks(text)
        multi = len(blocks) > 1
        for k, block in enumerate(blocks, 1):
            meta = block.get("meta", {})
            if meta.get("id"):
                sid = _slugify(meta["id"])
            elif multi:
                sid = f"{_slugify(src['stem'])}-{k}"
            else:
                sid = _slugify(src["stem"])

            concepts, objectives = parse_source(block.get("body", ""), src["suffix"])
            entry = grouped.setdefault(sid, {
                "id": sid,
                "name": meta.get("name") or src["stem"],
                "language": meta.get("language") or "auto",
                "concepts": [],
                "learning_objectives": [],
                "sources": [],
            })
            if meta.get("name"):
                entry["name"] = meta["name"]
            if meta.get("discipline"):
                entry["discipline"] = meta["discipline"]
            if meta.get("source_status"):
                entry["source_status"] = meta["source_status"]
            entry["concepts"].extend(concepts)
            entry["learning_objectives"].extend(objectives)
            entry["sources"].append({
                "file": src["name"],
                "rel": src["rel"],
                "sha256": src["fp"],
                "mtime": src["mtime"],
            })

    result: Dict[str, Dict] = {}
    for sid, s in grouped.items():
        if sid == "_errors":
            continue
        s["concepts"] = _dedupe_concepts(s["concepts"])
        prereqs = infer_prerequisites([c["name"] for c in s["concepts"]])
        for c in s["concepts"]:
            c["prerequisites"] = prereqs.get(c["name"], [])
        s["concepts"] = topological_order(s["concepts"])
        s["learning_objectives"] = list(dict.fromkeys(s["learning_objectives"]))
        if s["language"] == "auto":
            sample = " ".join(c["name"] for c in s["concepts"])
            s["language"] = _detect_language(sample)

        # Materialise the learning path + module grouping.
        ordered = s["concepts"]
        for i, c in enumerate(ordered, 1):
            c["order"] = i
            c["estimated_minutes"] = max(20, (c.get("difficulty", 2) or 2) * 15)
        s["learning_path"] = [
            {
                "order": c["order"],
                "concept": c["name"],
                "module": c.get("module", ""),
                "prerequisites": c.get("prerequisites", []),
                "estimated_minutes": c["estimated_minutes"],
            }
            for c in ordered
        ]
        modules: Dict[str, Dict] = {}
        for c in ordered:
            mod = c.get("module") or "General"
            m = modules.setdefault(mod, {"name": mod, "concepts": [], "estimated_minutes": 0})
            m["concepts"].append(c["name"])
            m["estimated_minutes"] += c["estimated_minutes"]
        s["modules"] = list(modules.values())
        s["estimated_hours"] = round(sum(c["estimated_minutes"] for c in ordered) / 60, 1)
        s.setdefault("discipline", _infer_discipline(s))
        s.setdefault("source_status", "document_interne")
        s["domaines"] = s["modules"]
        s["competences"] = [_concept_to_competence(c, s) for c in ordered]
        s["competence_graph"] = _build_competence_graph(s)
        result[sid] = s
    return result


def _build_real_exams(sources: List[Dict], syllabi: Dict[str, Dict]) -> List[Dict]:
    exams: List[Dict] = []
    category_to_sids: Dict[str, set] = {}
    for sid, s in syllabi.items():
        for c in s.get("concepts", []):
            cat = _concept_category(c)
            if cat != "general":
                category_to_sids.setdefault(cat, set()).add(sid)

    for src in sources:
        try:
            text = _read_text(src["path"])
        except Exception:  # noqa: BLE001
            continue

        blocks = split_blocks(text)
        for k, block in enumerate(blocks, 1):
            meta = block.get("meta", {})
            body = block.get("body", "")
            if meta.get("id"):
                exam_id = _slugify(meta["id"])
            elif len(blocks) > 1:
                exam_id = f"{_slugify(src['stem'])}-{k}"
            else:
                exam_id = _slugify(src["stem"])

            questions = parse_exam_questions(body)
            concepts_tested = list(dict.fromkeys(q["concept"] for q in questions))

            # Link to a syllabus: explicit front matter wins, else category/word overlap.
            syllabus_id = meta.get("syllabus_id") or ""
            if not syllabus_id:
                scores: Dict[str, int] = {}
                for q in questions:
                    cat = _question_concept(q["text"])
                    for sid in category_to_sids.get(cat, []):
                        scores[sid] = scores.get(sid, 0) + 2
                    qt = _word_tokens(q["text"])
                    for sid, s in syllabi.items():
                        for c in s.get("concepts", []):
                            if qt & _concept_tokens(c):
                                scores[sid] = scores.get(sid, 0) + 1
                syllabus_id = max(scores, key=scores.get) if scores else "unknown"

            exams.append({
                "id": exam_id,
                "syllabus_id": _slugify(syllabus_id) if syllabus_id != "unknown" else "unknown",
                "kind": "exam",
                "source": src["rel"],
                "questions": questions,
                "concepts_tested": concepts_tested,
                "difficulty_distribution": {
                    "easy": sum(1 for q in questions if q["difficulty"] < 0.34),
                    "medium": sum(1 for q in questions if 0.34 <= q["difficulty"] <= 0.67),
                    "hard": sum(1 for q in questions if q["difficulty"] > 0.67),
                },
            })
    return exams


def _apply_exam_frequency(syllabi: Dict[str, Dict], exams: List[Dict]) -> None:
    for exam in exams:
        if exam.get("kind") == "mock":
            continue
        for q in exam.get("questions", []):
            qt = _word_tokens(q.get("text", ""))
            for s in syllabi.values():
                for c in s.get("concepts", []):
                    if qt & _concept_tokens(c):
                        c["exam_frequency"] = c.get("exam_frequency", 0) + 1


def _detect_cycles(concepts: List[Dict]) -> List[str]:
    """Return readable prerequisite cycles, e.g. "A → B → A"."""
    names = {c["name"] for c in concepts}
    adj = {c["name"]: [p for p in c.get("prerequisites", []) if p in names] for c in concepts}
    WHITE, GREY, BLACK = 0, 1, 2
    color = {n: WHITE for n in names}
    cycles: List[str] = []

    def visit(n: str, stack: List[str]) -> None:
        color[n] = GREY
        stack.append(n)
        for m in adj[n]:
            if color[m] == GREY:
                idx = stack.index(m)
                cycles.append(" → ".join(stack[idx:] + [m]))
            elif color[m] == WHITE:
                visit(m, stack)
        stack.pop()
        color[n] = BLACK

    for n in names:
        if color[n] == WHITE:
            visit(n, [])
    return cycles


def validate_syllabus(s: Dict, has_exams: bool = False) -> Dict:
    """Diagnose how workable a syllabus is and flag missing elements."""
    concepts = s.get("concepts", [])
    objectives = s.get("learning_objectives", [])
    names = {c["name"] for c in concepts}
    issues: List[str] = []
    warnings: List[str] = []

    if not concepts:
        issues.append("No concepts extracted (add `## Concept` headings to the source).")
    if not objectives:
        warnings.append("No learning objectives/competencies detected.")

    broken: List[str] = []
    for c in concepts:
        for p in c.get("prerequisites", []):
            if p and p not in names:
                broken.append(f"{c['name']} → {p}")
    if broken:
        issues.append("Broken prerequisites: " + "; ".join(broken[:5]))

    cycles = _detect_cycles(concepts)
    if cycles:
        issues.append("Prerequisite cycles: " + "; ".join(cycles[:3]))

    no_desc = [c["name"] for c in concepts if not c.get("description")]
    if no_desc:
        warnings.append(f"{len(no_desc)} concept(s) have no description/topics.")

    no_module = [c["name"] for c in concepts if not c.get("module")]
    if no_module:
        warnings.append(f"{len(no_module)} concept(s) are not grouped in a module.")

    if not has_exams:
        warnings.append("No real exam linked — only an inferred mock exam.")

    # Weighted completeness score (0..1).
    score = 0.0
    if concepts:
        score += 0.25
    if concepts:
        score += 0.25 * (sum(1 for c in concepts if c.get("description")) / len(concepts))
    if objectives:
        score += 0.15
    if concepts and not broken and not cycles:
        score += 0.25
    if has_exams:
        score += 0.10

    return {
        "workable": bool(concepts and not issues),
        "score": round(score, 2),
        "issues": issues,
        "warnings": warnings,
        "counts": {
            "concepts": len(concepts),
            "with_description": sum(1 for c in concepts if c.get("description")),
            "objectives": len(objectives),
            "modules": len({c.get("module") for c in concepts if c.get("module")}),
            "broken_prerequisites": len(broken),
            "cycles": len(cycles),
        },
    }


def _syllabus_summary(s: Dict, exam_ids: List[str]) -> Dict:
    return {
        "id": s["id"],
        "name": s.get("name", s["id"]),
        "language": s.get("language", "unknown"),
        "concepts": len(s.get("concepts", [])),
        "competences": len(s.get("competences", [])),
        "discipline": s.get("discipline", "general"),
        "domaines": len(s.get("domaines", []) or s.get("modules", [])),
        "learning_objectives": len(s.get("learning_objectives", [])),
        "estimated_hours": s.get("estimated_hours", 0),
        "learning_path_steps": len(s.get("learning_path", [])),
        "modules": len(s.get("modules", [])),
        "sources": [src["file"] for src in s.get("sources", [])],
        "cheatsheet": f"cheatsheets/{s['id']}_cheatsheet.md",
        "exams": exam_ids,
        "mock_exam": f"{s['id']}_mock",
        "completeness": s.get("completeness", {}),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }


def _exam_summary(e: Dict) -> Dict:
    return {
        "id": e["id"],
        "syllabus_id": e.get("syllabus_id", "unknown"),
        "kind": e.get("kind", "exam"),
        "questions": len(e.get("questions", [])),
        "source": e.get("source"),
        "concepts_tested": e.get("concepts_tested", []),
    }


def _cleanup_stale(prev_sources: Dict, current_sources: Dict, syllabi: Dict, real_exams: List[Dict]) -> None:
    removed = [rel for rel in prev_sources if rel not in current_sources]
    for rel in removed:
        info = prev_sources.get(rel, {})
        kind = info.get("kind")
        if kind == "syllabus":
            sid = info.get("syllabus_id")
            if sid and sid not in syllabi:
                for p in (SYLLABI_DIR / f"{sid}.json", CHEATSHEETS_DIR / f"{sid}_cheatsheet.md",
                          EXAMS_DIR / f"{sid}_mock.json"):
                    if p.exists():
                        p.unlink()
        elif kind == "exam":
            exam_id = info.get("exam_id")
            if exam_id and exam_id not in {e["id"] for e in real_exams}:
                p = EXAMS_DIR / f"{exam_id}.json"
                if p.exists():
                    p.unlink()


def sync_library() -> Dict:
    """Rebuild the library from the raw documents currently on disk.

    Returns a summary dict suitable for both the dashboard API and the MCP
    ``sync_library`` tool. Idempotent: re-running produces the same artifacts.
    """
    ensure_dirs()
    prev = load_registry()

    syllabus_sources = _scan(SYLLABI_DIR, "syllabus")
    exam_sources = _scan(EXAMS_DIR, "exam")

    syllabi = _build_syllabi(syllabus_sources)
    real_exams = _build_real_exams(exam_sources, syllabi)
    _apply_exam_frequency(syllabi, real_exams)

    exam_ids_by_syllabus: Dict[str, List[str]] = {}
    for e in real_exams:
        exam_ids_by_syllabus.setdefault(e.get("syllabus_id", "unknown"), []).append(e["id"])

    for sid, s in syllabi.items():
        s["completeness"] = validate_syllabus(s, has_exams=bool(exam_ids_by_syllabus.get(sid)))

    mock_exams = [build_mock_exam(s) for s in syllabi.values()]

    # Persist organised syllabi.
    for sid, s in syllabi.items():
        (SYLLABI_DIR / f"{sid}.json").write_text(
            json.dumps(s, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    # Persist exams (real + inferred).
    for e in real_exams:
        (EXAMS_DIR / f"{e['id']}.json").write_text(
            json.dumps(e, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    for m in mock_exams:
        (EXAMS_DIR / f"{m['id']}.json").write_text(
            json.dumps(m, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    # Persist cheatsheets (after exam frequency + mock exams exist).
    all_exams = real_exams + mock_exams
    for s in syllabi.values():
        write_cheatsheet(s, all_exams)

    # Registry index + source fingerprints for change detection / cleanup.
    current_sources: Dict[str, Dict] = {}
    for src in syllabus_sources:
        # Best-effort: record which syllabus this source contributed to.
        sid = _slugify(src["stem"])
        blocks = split_blocks(_read_text(src["path"]) if src["suffix"] != ".pdf" else "")
        if len(blocks) == 1 and blocks[0].get("meta", {}).get("id"):
            sid = _slugify(blocks[0]["meta"]["id"])
        current_sources[src["rel"]] = {"kind": "syllabus", "syllabus_id": sid,
                                       "sha256": src["fp"], "mtime": src["mtime"]}
    for src in exam_sources:
        current_sources[src["rel"]] = {"kind": "exam", "exam_id": _slugify(src["stem"]),
                                       "sha256": src["fp"], "mtime": src["mtime"]}

    _cleanup_stale(prev.get("sources", {}), current_sources, syllabi, real_exams)

    registry = {
        "version": 1,
        "last_sync": datetime.now().isoformat(timespec="seconds"),
        "syllabi": {sid: _syllabus_summary(s, exam_ids_by_syllabus.get(sid, []))
                    for sid, s in syllabi.items()},
        "exams": {e["id"]: _exam_summary(e) for e in real_exams + mock_exams},
        "sources": current_sources,
    }
    _save_registry(registry)

    return {
        "syllabi": list(syllabi.keys()),
        "syllabus_count": len(syllabi),
        "exam_count": len(real_exams),
        "mock_exam_count": len(mock_exams),
        "cheatsheet_count": len(syllabi),
        "sources": len(current_sources),
        "last_sync": registry["last_sync"],
    }


def render_sync_summary(summary: Dict) -> str:
    """Human-readable summary for the MCP tool."""
    lines = [
        "✅ **Library synced**",
        "",
        f"- Syllabi organised: {summary['syllabus_count']}",
        f"- Real exams analysed: {summary['exam_count']}",
        f"- Mock exams inferred: {summary['mock_exam_count']}",
        f"- Cheatsheets generated: {summary['cheatsheet_count']}",
        f"- Source documents tracked: {summary['sources']}",
    ]
    if summary["syllabi"]:
        lines.append("")
        lines.append("**Syllabi:** " + ", ".join(summary["syllabi"]))
    return "\n".join(lines)
