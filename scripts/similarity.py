#!/usr/bin/env python3
"""Multi-signal similarity detection for Claude Code skills.

Combines four signals for robust duplicate detection:
  1. TF-IDF content similarity  (lexical overlap of SKILL.md body)
  2. Frontmatter similarity     (name, description, tags, category)
  3. Structural similarity      (section headings, reference files)
  4. Name similarity            (Jaccard on hyphenated name tokens)

Zero external dependencies -- only uses Python standard library.
"""

import argparse
import json
import math
import os
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Common English stopwords plus domain-specific noise terms
STOPWORDS = frozenset({
    # Articles / determiners
    "the", "a", "an", "this", "that", "these", "those",
    # Prepositions
    "in", "on", "for", "to", "with", "of", "at", "by", "from", "up",
    "about", "into", "through", "during", "before", "after", "above",
    "below", "between", "out", "off", "over", "under",
    # Conjunctions / connectors
    "and", "or", "but", "nor", "so", "yet", "both", "either", "neither",
    "not", "if", "then", "else", "when", "where", "while", "until",
    "because", "as", "than",
    # Pronouns / misc
    "who", "what", "which", "how", "why", "here", "there", "all",
    "each", "every", "few", "more", "most", "other", "some", "such",
    "no", "only", "own", "same", "too", "very", "just", "also",
    # Verbs (common auxiliaries / light verbs)
    "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "having",
    "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "can", "shall",
    "must",
    # Domain-specific noise (appear in virtually every SKILL.md)
    "use", "used", "using", "user", "skill", "should", "claude", "code",
    "file", "files", "based", "need", "needs", "provide", "provides",
    "ensure", "follow", "following", "again", "further", "once",
})


def tokenize(text: str) -> List[str]:
    """Extract meaningful tokens from markdown text.

    Strips markdown formatting, lowercases, splits on word boundaries,
    and removes stopwords and short tokens.

    Args:
        text: Raw markdown text content.

    Returns:
        List of cleaned, lowercased tokens.
    """
    # Remove fenced code blocks (``` ... ```)
    text = re.sub(r"```[\s\S]*?```", " ", text)
    # Remove inline code (`...`)
    text = re.sub(r"`[^`]*`", " ", text)
    # Remove URLs
    text = re.sub(r"https?://\S+", " ", text)
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Remove markdown headers (#)
    text = re.sub(r"#+\s*", " ", text)
    # Remove bold / italic markers
    text = re.sub(r"\*{1,3}", " ", text)
    # Lowercase
    text = text.lower()
    # Split on non-alphanumeric characters
    tokens = re.split(r"[^a-z0-9]+", text)
    # Filter short tokens and stopwords
    return [t for t in tokens if len(t) >= 3 and t not in STOPWORDS]


def compute_tf(tokens: List[str]) -> Dict[str, float]:
    """Compute term frequency for a token list.

    Args:
        tokens: List of tokens from a single document.

    Returns:
        Mapping of term to its normalised frequency.
    """
    counts = Counter(tokens)
    total = len(tokens)
    if total == 0:
        return {}
    return {term: count / total for term, count in counts.items()}


def compute_idf(all_docs_tokens: List[List[str]]) -> Dict[str, float]:
    """Compute inverse document frequency across a corpus.

    Args:
        all_docs_tokens: List of token lists, one per document.

    Returns:
        Mapping of term to its IDF value.
    """
    total_docs = len(all_docs_tokens)
    doc_freq: Dict[str, int] = {}
    for tokens in all_docs_tokens:
        unique_terms = set(tokens)
        for term in unique_terms:
            doc_freq[term] = doc_freq.get(term, 0) + 1

    return {
        term: math.log(total_docs / (1 + df))
        for term, df in doc_freq.items()
    }


def compute_tfidf(tf: Dict[str, float], idf: Dict[str, float]) -> Dict[str, float]:
    """Compute TF-IDF vector from term frequency and IDF mappings.

    Args:
        tf: Term frequency dict for a single document.
        idf: Inverse document frequency dict for the corpus.

    Returns:
        TF-IDF weighted vector as a dict.
    """
    return {term: freq * idf.get(term, 0.0) for term, freq in tf.items()}


def cosine_similarity(vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
    """Compute cosine similarity between two sparse vectors.

    Args:
        vec_a: First TF-IDF vector.
        vec_b: Second TF-IDF vector.

    Returns:
        Cosine similarity in [0, 1]. Returns 0.0 when either vector is zero.
    """
    common = set(vec_a) & set(vec_b)
    dot = sum(vec_a[t] * vec_b[t] for t in common)

    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)



# ---------------------------------------------------------------------------
# Signal 2: Frontmatter similarity
# ---------------------------------------------------------------------------

def extract_frontmatter(text: str) -> Dict[str, str]:
    """Extract YAML frontmatter fields from a SKILL.md file.

    Args:
        text: Raw SKILL.md content.

    Returns:
        Dict of frontmatter key-value pairs (all values as strings).
    """
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    fm: Dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip()
    return fm


def frontmatter_similarity(fm_a: Dict[str, str], fm_b: Dict[str, str]) -> float:
    """Score similarity between two frontmatter dicts.

    Compares description (tokenized Jaccard), tags, and category fields.

    Args:
        fm_a: Frontmatter of skill A.
        fm_b: Frontmatter of skill B.

    Returns:
        Weighted similarity score in [0, 1].
    """
    scores: List[float] = []

    # Description similarity (tokenized Jaccard)
    desc_a = set(re.split(r"\W+", fm_a.get("description", "").lower())) - {""}
    desc_b = set(re.split(r"\W+", fm_b.get("description", "").lower())) - {""}
    if desc_a or desc_b:
        inter = desc_a & desc_b
        union = desc_a | desc_b
        scores.append(len(inter) / len(union) if union else 0.0)

    # Category match (exact)
    cat_a = fm_a.get("category", "").lower().strip()
    cat_b = fm_b.get("category", "").lower().strip()
    if cat_a and cat_b:
        scores.append(1.0 if cat_a == cat_b else 0.0)

    # Tags overlap (Jaccard)
    tags_a = {t.strip().lower() for t in fm_a.get("tags", "").split(",") if t.strip()}
    tags_b = {t.strip().lower() for t in fm_b.get("tags", "").split(",") if t.strip()}
    if tags_a or tags_b:
        inter = tags_a & tags_b
        union = tags_a | tags_b
        scores.append(len(inter) / len(union) if union else 0.0)

    return sum(scores) / len(scores) if scores else 0.0


# ---------------------------------------------------------------------------
# Signal 3: Structural similarity
# ---------------------------------------------------------------------------

def extract_headings(text: str) -> List[str]:
    """Extract markdown section headings from text.

    Args:
        text: Raw markdown content.

    Returns:
        List of lowercased heading strings.
    """
    return [m.group(1).strip().lower() for m in re.finditer(r"^#{1,4}\s+(.+)$", text, re.MULTILINE)]


def list_references(skill_dir: Path) -> List[str]:
    """List filenames in a skill's references/ directory.

    Args:
        skill_dir: Path to the skill directory.

    Returns:
        Sorted list of filenames.
    """
    refs_dir = skill_dir / "references"
    if not refs_dir.is_dir():
        return []
    return sorted(f.name for f in refs_dir.iterdir() if f.is_file())


def structural_similarity(
    headings_a: List[str],
    headings_b: List[str],
    refs_a: List[str],
    refs_b: List[str],
) -> float:
    """Compute structural similarity between two skills.

    Combines heading overlap (Jaccard) and reference file overlap.

    Args:
        headings_a: Section headings of skill A.
        headings_b: Section headings of skill B.
        refs_a: Reference filenames of skill A.
        refs_b: Reference filenames of skill B.

    Returns:
        Similarity score in [0, 1].
    """
    scores: List[float] = []

    # Heading overlap
    set_a, set_b = set(headings_a), set(headings_b)
    if set_a or set_b:
        union = set_a | set_b
        scores.append(len(set_a & set_b) / len(union) if union else 0.0)

    # Reference file overlap
    ra, rb = set(refs_a), set(refs_b)
    if ra or rb:
        union = ra | rb
        scores.append(len(ra & rb) / len(union) if union else 0.0)

    return sum(scores) / len(scores) if scores else 0.0


# ---------------------------------------------------------------------------
# Signal 4: Name similarity
# ---------------------------------------------------------------------------

def name_similarity(name_a: str, name_b: str) -> float:
    """Jaccard similarity on hyphen-tokenized skill names.

    Args:
        name_a: First skill name (kebab-case).
        name_b: Second skill name (kebab-case).

    Returns:
        Jaccard similarity in [0, 1].
    """
    tokens_a = set(name_a.lower().split("-"))
    tokens_b = set(name_b.lower().split("-"))
    union = tokens_a | tokens_b
    if not union:
        return 0.0
    return len(tokens_a & tokens_b) / len(union)


# ---------------------------------------------------------------------------
# Composite scoring
# ---------------------------------------------------------------------------

# Weights for the composite score.  Content (TF-IDF) is still the
# strongest signal, but the other three signals correct for vocabulary
# mismatch and structural similarity that pure bag-of-words misses.
WEIGHT_CONTENT = 0.45
WEIGHT_FRONTMATTER = 0.20
WEIGHT_STRUCTURE = 0.15
WEIGHT_NAME = 0.20


@dataclass
class SimilarityResult:
    """Detailed similarity result between two skills."""

    skill_a: str
    skill_b: str
    composite: float
    content: float
    frontmatter: float
    structure: float
    name: float


def _similarity_label(score: float) -> str:
    """Map a similarity score to a human-readable status label.

    Args:
        score: Composite similarity score.

    Returns:
        Status string.
    """
    if score >= 0.9:
        return "Near Identical"
    if score >= 0.7:
        return "Likely Duplicate"
    if score >= 0.5:
        return "Possible Match"
    return "Low"


def find_similar_skills(
    skills_dir: str,
    threshold: float = 0.5,
) -> List[SimilarityResult]:
    """Detect similar skills using multi-signal composite scoring.

    Combines four signals:
      1. TF-IDF content similarity (weight 0.45)
      2. Frontmatter similarity   (weight 0.20)
      3. Structural similarity    (weight 0.15)
      4. Name similarity          (weight 0.20)

    Args:
        skills_dir: Root directory containing skill sub-directories.
        threshold: Minimum composite score to include a pair.

    Returns:
        List of :class:`SimilarityResult` sorted by composite score descending.
    """
    skills_path = Path(skills_dir).expanduser().resolve()
    if not skills_path.is_dir():
        raise FileNotFoundError(f"Skills directory not found: {skills_path}")

    # Discover SKILL.md files
    skill_docs: Dict[str, str] = {}
    skill_dirs: Dict[str, Path] = {}
    for entry in sorted(skills_path.iterdir()):
        skill_md = entry / "SKILL.md"
        if entry.is_dir() and skill_md.is_file():
            skill_docs[entry.name] = skill_md.read_text(encoding="utf-8")
            skill_dirs[entry.name] = entry

    if len(skill_docs) < 2:
        return []

    names = list(skill_docs.keys())

    # --- Signal 1: TF-IDF ---
    all_tokens = [tokenize(skill_docs[n]) for n in names]
    idf = compute_idf(all_tokens)
    tfidf_vecs = [compute_tfidf(compute_tf(t), idf) for t in all_tokens]

    # --- Signal 2: Frontmatter ---
    frontmatters = {n: extract_frontmatter(skill_docs[n]) for n in names}

    # --- Signal 3: Structure ---
    headings = {n: extract_headings(skill_docs[n]) for n in names}
    refs = {n: list_references(skill_dirs[n]) for n in names}

    # Pairwise comparison
    results: List[SimilarityResult] = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            s_content = cosine_similarity(tfidf_vecs[i], tfidf_vecs[j])
            s_fm = frontmatter_similarity(frontmatters[names[i]], frontmatters[names[j]])
            s_struct = structural_similarity(
                headings[names[i]], headings[names[j]],
                refs[names[i]], refs[names[j]],
            )
            s_name = name_similarity(names[i], names[j])

            composite = (
                WEIGHT_CONTENT * s_content
                + WEIGHT_FRONTMATTER * s_fm
                + WEIGHT_STRUCTURE * s_struct
                + WEIGHT_NAME * s_name
            )

            if composite >= threshold:
                results.append(SimilarityResult(
                    skill_a=names[i],
                    skill_b=names[j],
                    composite=composite,
                    content=s_content,
                    frontmatter=s_fm,
                    structure=s_struct,
                    name=s_name,
                ))

    results.sort(key=lambda r: r.composite, reverse=True)
    return results


def _format_table(results: List[SimilarityResult], top: int, detailed: bool = False) -> str:
    """Render results as a formatted ASCII table.

    Args:
        results: Similarity results from :func:`find_similar_skills`.
        top: Maximum number of rows to display (0 = unlimited).
        detailed: If True, show per-signal breakdown columns.

    Returns:
        Formatted table string.
    """
    display = results[:top] if top > 0 else results

    if not display:
        return "No similar skill pairs found above the threshold."

    col_skill = max(
        max((len(r.skill_a) for r in display), default=10),
        max((len(r.skill_b) for r in display), default=10),
        10,
    )

    if detailed:
        header = (
            f"{'Score':<7}| {'Status':<17}| {'Skill A':<{col_skill}} | "
            f"{'Skill B':<{col_skill}} | {'Content':>7} {'FM':>5} "
            f"{'Struct':>6} {'Name':>5}"
        )
        sep = "-" * len(header)
        lines = ["Similarity Report (Multi-Signal)", "=" * 32, header, sep]
        for r in display:
            label = _similarity_label(r.composite)
            lines.append(
                f"{r.composite:<7.2f}| {label:<17}| {r.skill_a:<{col_skill}} | "
                f"{r.skill_b:<{col_skill}} | {r.content:>7.2f} {r.frontmatter:>5.2f} "
                f"{r.structure:>6.2f} {r.name:>5.2f}"
            )
    else:
        header = (
            f"{'Score':<7}| {'Status':<17}| "
            f"{'Skill A':<{col_skill}} | {'Skill B':<{col_skill}}"
        )
        sep = (
            f"{'-' * 7}|{'-' * 18}|"
            f"{'-' * (col_skill + 2)}|{'-' * (col_skill + 1)}"
        )
        lines = ["Similarity Report (Multi-Signal)", "=" * 32, header, sep]
        for r in display:
            label = _similarity_label(r.composite)
            lines.append(
                f"{r.composite:<7.2f}| {label:<17}| "
                f"{r.skill_a:<{col_skill}} | {r.skill_b:<{col_skill}}"
            )

    lines.append("")
    lines.append(
        f"Weights: content={WEIGHT_CONTENT} frontmatter={WEIGHT_FRONTMATTER} "
        f"structure={WEIGHT_STRUCTURE} name={WEIGHT_NAME}"
    )
    return "\n".join(lines)


def _format_json(results: List[SimilarityResult], top: int) -> str:
    """Render results as a JSON string.

    Args:
        results: Similarity results from :func:`find_similar_skills`.
        top: Maximum number of entries (0 = unlimited).

    Returns:
        Pretty-printed JSON string.
    """
    display = results[:top] if top > 0 else results
    payload = [
        {
            "skill_a": r.skill_a,
            "skill_b": r.skill_b,
            "composite": round(r.composite, 4),
            "content": round(r.content, 4),
            "frontmatter": round(r.frontmatter, 4),
            "structure": round(r.structure, 4),
            "name": round(r.name, 4),
            "status": _similarity_label(r.composite),
        }
        for r in display
    ]
    return json.dumps(payload, indent=2)


def main() -> None:
    """CLI entry point for the similarity scanner."""
    parser = argparse.ArgumentParser(
        description="Detect duplicate / similar Claude Code skills via multi-signal analysis.",
    )
    parser.add_argument(
        "--skills-dir",
        default=os.path.expanduser("~/.claude/skills"),
        help="Root directory containing skill sub-directories (default: ~/.claude/skills)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Minimum composite score to report (default: 0.5)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=0,
        help="Show only the top N pairs (default: 0 = all)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output results as JSON instead of a table",
    )
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show per-signal breakdown (content, frontmatter, structure, name)",
    )

    args = parser.parse_args()

    results = find_similar_skills(args.skills_dir, threshold=args.threshold)

    if args.output_json:
        print(_format_json(results, args.top))
    else:
        print(_format_table(results, args.top, detailed=args.detailed))


if __name__ == "__main__":
    main()
