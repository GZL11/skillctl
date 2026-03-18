"""TF-IDF + cosine similarity for detecting duplicate/similar Claude Code skills.

Reads SKILL.md files from skill directories, computes TF-IDF vectors,
and reports pairs of skills that exceed a similarity threshold.

Zero external dependencies -- only uses Python standard library.
"""

import argparse
import json
import math
import os
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

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


def _similarity_label(score: float) -> str:
    """Map a similarity score to a human-readable status label.

    Args:
        score: Cosine similarity score.

    Returns:
        Status string.
    """
    if score >= 0.9:
        return "Near Identical"
    if score >= 0.7:
        return "Likely Duplicate"
    return "Possible Match"


def find_similar_skills(
    skills_dir: str,
    threshold: float = 0.5,
) -> List[Tuple[str, str, float]]:
    """Detect similar skills by comparing their SKILL.md content.

    Walks *skills_dir*, reads every ``SKILL.md``, builds a TF-IDF model
    over the corpus, and returns all pairs whose cosine similarity
    exceeds *threshold*.

    Args:
        skills_dir: Root directory containing skill sub-directories.
        threshold: Minimum cosine similarity to include a pair.

    Returns:
        List of ``(skill_a, skill_b, score)`` tuples sorted by score
        descending.
    """
    skills_path = Path(skills_dir).expanduser().resolve()
    if not skills_path.is_dir():
        raise FileNotFoundError(f"Skills directory not found: {skills_path}")

    # Discover SKILL.md files
    skill_docs: Dict[str, str] = {}
    for entry in sorted(skills_path.iterdir()):
        skill_md = entry / "SKILL.md"
        if entry.is_dir() and skill_md.is_file():
            skill_docs[entry.name] = skill_md.read_text(encoding="utf-8")

    if len(skill_docs) < 2:
        return []

    # Tokenize
    names = list(skill_docs.keys())
    all_tokens = [tokenize(skill_docs[name]) for name in names]

    # Build IDF
    idf = compute_idf(all_tokens)

    # Build TF-IDF vectors
    tfidf_vecs = [compute_tfidf(compute_tf(tokens), idf) for tokens in all_tokens]

    # Pairwise comparison
    results: List[Tuple[str, str, float]] = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            score = cosine_similarity(tfidf_vecs[i], tfidf_vecs[j])
            if score >= threshold:
                results.append((names[i], names[j], score))

    results.sort(key=lambda x: x[2], reverse=True)
    return results


def _format_table(results: List[Tuple[str, str, float]], top: int) -> str:
    """Render results as a formatted ASCII table.

    Args:
        results: Similarity results from :func:`find_similar_skills`.
        top: Maximum number of rows to display (0 = unlimited).

    Returns:
        Formatted table string.
    """
    display = results[:top] if top > 0 else results

    if not display:
        return "No similar skill pairs found above the threshold."

    # Column widths
    col_score = 7
    col_status = 17
    col_skill = max(
        max((len(a) for a, _, _ in display), default=10),
        max((len(b) for _, b, _ in display), default=10),
        10,
    )

    header = (
        f"{'Score':<{col_score}}| {'Status':<{col_status}}| "
        f"{'Skill A':<{col_skill}} | {'Skill B':<{col_skill}}"
    )
    sep = (
        f"{'-' * col_score}|{'-' * (col_status + 1)}|"
        f"{'-' * (col_skill + 2)}|{'-' * (col_skill + 1)}"
    )

    lines = ["Similarity Report", "=================", header, sep]
    for skill_a, skill_b, score in display:
        label = _similarity_label(score)
        lines.append(
            f"{score:<{col_score}.2f}| {label:<{col_status}}| "
            f"{skill_a:<{col_skill}} | {skill_b:<{col_skill}}"
        )

    return "\n".join(lines)


def _format_json(results: List[Tuple[str, str, float]], top: int) -> str:
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
            "skill_a": a,
            "skill_b": b,
            "score": round(s, 4),
            "status": _similarity_label(s),
        }
        for a, b, s in display
    ]
    return json.dumps(payload, indent=2)


def main() -> None:
    """CLI entry point for the similarity scanner."""
    parser = argparse.ArgumentParser(
        description="Detect duplicate / similar Claude Code skills via TF-IDF.",
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
        help="Minimum cosine similarity to report (default: 0.5)",
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

    args = parser.parse_args()

    results = find_similar_skills(args.skills_dir, threshold=args.threshold)

    if args.output_json:
        print(_format_json(results, args.top))
    else:
        print(_format_table(results, args.top))


if __name__ == "__main__":
    main()
