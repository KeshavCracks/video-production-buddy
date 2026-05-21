"""Curated advertising knowledge retrieval for the ad-video pipeline.

This module is deliberately local and deterministic by default. It gives the
agent a professional producer knowledge layer without turning OpenMontage into
an opaque Python orchestrator: directors still decide how to apply guidance,
while this code loads cards, validates their contract, and ranks likely matches.
"""

from __future__ import annotations

import json
import hashlib
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Iterable

import jsonschema


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CARD_DIR = ROOT / "knowledge" / "ad-video"
CARD_SCHEMA_PATH = ROOT / "schemas" / "knowledge" / "ad_video_knowledge_card.schema.json"
DEFAULT_TOP_K = 6

EmbeddingScorer = Callable[[list[dict[str, Any]], str], list[float]]


def _load_card_schema() -> dict[str, Any]:
    with open(CARD_SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def _content_hash(card: dict[str, Any]) -> str:
    payload = {key: value for key, value in card.items() if key != "content_hash"}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def load_ad_knowledge_cards(card_dir: Path | str | None = None) -> list[dict[str, Any]]:
    """Load and schema-validate curated ad-video knowledge cards."""
    directory = Path(card_dir) if card_dir is not None else DEFAULT_CARD_DIR
    schema = _load_card_schema()
    cards: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for path in sorted(directory.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            card = json.load(f)
        jsonschema.validate(instance=card, schema=schema)
        expected_hash = _content_hash(card)
        if card.get("content_hash") != expected_hash:
            raise ValueError(
                f"ad knowledge card {path.name} content_hash mismatch: "
                f"expected {expected_hash}, got {card.get('content_hash')}"
            )

        card_id = card["card_id"]
        if card_id in seen_ids:
            raise ValueError(f"Duplicate ad knowledge card_id: {card_id}")
        seen_ids.add(card_id)
        cards.append(card)

    if not cards:
        raise ValueError(f"No ad knowledge cards found in {directory}")
    return cards


def _tokens(value: Any) -> list[str]:
    return re.findall(r"[a-z0-9]+", str(value or "").lower())


def _flatten_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _flatten_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _flatten_strings(item)
    elif value is not None:
        yield str(value)


def _card_text(card: dict[str, Any]) -> str:
    fields = [
        card.get("card_id", ""),
        card.get("domain", ""),
        card.get("summary", ""),
        " ".join(card.get("principles", [])),
        " ".join(card.get("apply_when", [])),
        " ".join(card.get("avoid_when", [])),
        " ".join(card.get("downstream_targets", [])),
        " ".join(card.get("keywords", [])),
    ]
    return " ".join(fields)


def _query_text(inputs: dict[str, Any]) -> str:
    parts = []
    for key in (
        "product_category",
        "platform",
        "audience",
        "objectives",
        "validation_targets",
        "brief",
        "product",
    ):
        parts.extend(_flatten_strings(inputs.get(key)))
    return " ".join(parts)


def _target_terms(inputs: dict[str, Any]) -> set[str]:
    terms: set[str] = set()
    for value in inputs.get("validation_targets", []) or []:
        normalized = str(value).strip().lower().replace("-", "_").replace(" ", "_")
        if normalized:
            terms.add(normalized)
            terms.update(_tokens(normalized))
    for value in inputs.get("objectives", []) or []:
        terms.update(_tokens(value))
    terms.update(_tokens(inputs.get("platform")))
    return terms


def _bm25_scores(cards: list[dict[str, Any]], query: str, inputs: dict[str, Any]) -> list[float]:
    query_terms = _tokens(query)
    if not query_terms:
        return [0.0 for _ in cards]

    docs = [_tokens(_card_text(card)) for card in cards]
    avg_len = sum(len(doc) for doc in docs) / max(len(docs), 1)
    doc_freq: Counter[str] = Counter()
    for doc in docs:
        doc_freq.update(set(doc))

    targets = _target_terms(inputs)
    scores: list[float] = []
    k1 = 1.2
    b = 0.75
    for card, doc in zip(cards, docs):
        tf = Counter(doc)
        doc_len = max(len(doc), 1)
        score = 0.0
        for term in query_terms:
            if tf[term] == 0:
                continue
            idf = math.log((len(cards) - doc_freq[term] + 0.5) / (doc_freq[term] + 0.5) + 1.0)
            denom = tf[term] + k1 * (1 - b + b * doc_len / max(avg_len, 1))
            score += idf * (tf[term] * (k1 + 1)) / denom

        domain = str(card.get("domain") or "").lower()
        downstream = {str(item).lower() for item in card.get("downstream_targets", [])}
        keywords = {str(item).lower() for item in card.get("keywords", [])}
        if domain in targets:
            score += 2.0
        if downstream.intersection(targets):
            score += 0.75
        if any(token in " ".join(keywords) for token in targets):
            score += 0.5
        scores.append(score)
    return scores


def _normalize_ranked(cards: list[dict[str, Any]], scores: list[float], top_k: int) -> list[dict[str, Any]]:
    paired = [
        (card, score)
        for card, score in zip(cards, scores)
        if score > 0
    ]
    paired.sort(key=lambda item: (-item[1], item[0]["card_id"]))
    if not paired:
        paired = [(card, 1.0) for card in cards[:top_k]]

    max_score = max(score for _, score in paired) or 1.0
    out: list[dict[str, Any]] = []
    for card, score in paired[:top_k]:
        out.append(
            {
                "card_id": card["card_id"],
                "domain": card["domain"],
                "source_ref": f"knowledge_alignment:{card['card_id']}",
                "summary": card["summary"],
                "relevance_score": round(max(0.01, min(score / max_score, 1.0)), 3),
                "why_relevant": _why_relevant(card),
                "downstream_targets": card["downstream_targets"],
            }
        )
    return out


def _why_relevant(card: dict[str, Any]) -> str:
    apply_when = card.get("apply_when") or []
    if apply_when:
        return apply_when[0]
    return card["summary"]


def _recommendations(cards_by_id: dict[str, dict[str, Any]], retrieved: list[dict[str, Any]]) -> list[dict[str, Any]]:
    recommendations: list[dict[str, Any]] = []
    for item in retrieved:
        card = cards_by_id[item["card_id"]]
        recommendations.append(
            {
                "card_id": card["card_id"],
                "target": card["downstream_targets"][0],
                "recommendation": card["principles"][0],
                "confidence": "producer-doctrine",
            }
        )
    return recommendations


def _contraindications(cards_by_id: dict[str, dict[str, Any]], retrieved: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in retrieved:
        card = cards_by_id[item["card_id"]]
        out.append(
            {
                "card_id": card["card_id"],
                "avoid_when": card["avoid_when"][0],
                "reason": "Apply only when the brief and truth contract allow it.",
            }
        )
    return out


def _gaps(inputs: dict[str, Any], retrieved: list[dict[str, Any]]) -> list[str]:
    retrieved_domains = {item["domain"] for item in retrieved}
    gaps: list[str] = []
    for target in inputs.get("validation_targets", []) or []:
        normalized = str(target).strip().lower().replace("-", "_").replace(" ", "_")
        if normalized and normalized not in retrieved_domains:
            gaps.append(f"No direct curated card matched validation target: {normalized}")
    return gaps


def retrieve_ad_knowledge(
    inputs: dict[str, Any],
    *,
    cards: list[dict[str, Any]] | None = None,
    embedding_scorer: EmbeddingScorer | None = None,
) -> dict[str, Any]:
    """Retrieve professional ad-video knowledge for the current brief.

    `backend="auto"` and `backend="bm25"` use deterministic lexical scoring.
    `backend="embedding"` or `backend="hybrid"` can use an injected scorer in
    future providers; without one they deliberately fall back to BM25 with an
    explicit warning so the pipeline remains local and testable.
    """
    cards = list(cards) if cards is not None else load_ad_knowledge_cards()
    cards_by_id = {card["card_id"]: card for card in cards}
    backend = str(inputs.get("backend") or "auto").lower()
    top_k = int(inputs.get("top_k") or DEFAULT_TOP_K)
    query = _query_text(inputs)
    warnings: list[str] = []

    if backend in {"embedding", "hybrid"} and embedding_scorer is not None:
        raw_scores = embedding_scorer(cards, query)
        backend_used = "embedding" if backend == "embedding" else "hybrid"
    else:
        if backend in {"embedding", "hybrid"}:
            warnings.append("Embedding backend is not configured; fell back to deterministic BM25 retrieval.")
        raw_scores = _bm25_scores(cards, query, inputs)
        backend_used = "bm25"

    retrieved = _normalize_ranked(cards, raw_scores, top_k)
    return {
        "retrieval_backend": backend_used,
        "warnings": warnings,
        "cards_used": retrieved,
        "application_recommendations": _recommendations(cards_by_id, retrieved),
        "contraindications": _contraindications(cards_by_id, retrieved),
        "gaps": _gaps(inputs, retrieved),
    }
