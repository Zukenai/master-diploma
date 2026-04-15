from __future__ import annotations

import html
import json
import re
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from app.config.settings import AppConfig


def _fetch_openalex_work(openalex_id: str, email: str) -> dict[str, object]:
    url = f"https://api.openalex.org/works/{openalex_id}?mailto={email}"
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        path = Path(tmp.name)
    try:
        completed = subprocess.run(
            ["curl", "-sL", "--retry", "4", "--retry-all-errors", "-o", str(path), url],
            check=True,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"curl failed for {openalex_id}")
        return json.loads(path.read_text(encoding="utf-8"))
    finally:
        path.unlink(missing_ok=True)


def _reconstruct_abstract(abstract_inverted_index: dict[str, list[int]] | None) -> str:
    if not abstract_inverted_index:
        return ""
    tokens_by_position: dict[int, str] = {}
    for token, positions in abstract_inverted_index.items():
        for position in positions:
            tokens_by_position[position] = token
    ordered = [tokens_by_position[idx] for idx in sorted(tokens_by_position)]
    return " ".join(ordered).replace(" ,", ",").replace(" .", ".").strip()


def _sentence_claims(text: str) -> list[str]:
    sentences = [segment.strip() for segment in re.split(r"(?<=[.!?])\s+", text) if segment.strip()]
    return sentences[:2]


def _normalize_work(manifest_entry: dict[str, object], work: dict[str, object]) -> dict[str, object]:
    abstract = _reconstruct_abstract(work.get("abstract_inverted_index"))
    keywords = [
        item["display_name"]
        for item in (work.get("keywords") or [])[:5]
        if item.get("display_name")
    ]
    if not keywords:
        keywords = [
            item["display_name"]
            for item in (work.get("topics") or [])[:5]
            if item.get("display_name")
        ]
    primary_location = work.get("primary_location") or {}
    source = primary_location.get("source") or {}
    return {
        "paper_id": manifest_entry["paper_id"],
        "title": html.unescape(work.get("title") or work.get("display_name") or ""),
        "abstract": abstract,
        "keywords": keywords,
        "claims": _sentence_claims(abstract),
        "year": work.get("publication_year") or 0,
        "venue": source.get("display_name") or work.get("type") or "unknown",
    }


def acquire_curated_corpus(config: AppConfig, contact_email: str = "zukenaib@gmail.com") -> dict[str, object]:
    manifest = json.loads(config.paths.curated_manifest_path.read_text(encoding="utf-8"))
    selected_records: list[dict[str, object]] = []
    provenance_records: list[dict[str, object]] = []
    raw_snapshot: list[dict[str, object]] = []

    for entry in manifest["selected_works"]:
        work = _fetch_openalex_work(entry["openalex_id"], contact_email)
        raw_snapshot.append(work)
        selected_records.append(_normalize_work(entry, work))
        provenance_records.append(
            {
                "paper_id": entry["paper_id"],
                "openalex_id": entry["openalex_id"],
                "title_query": entry["title_query"],
                "selection_reason": entry["selection_reason"],
                "doi": work.get("doi"),
                "title": html.unescape(work.get("title") or work.get("display_name") or ""),
                "publication_year": work.get("publication_year"),
                "venue": ((work.get("primary_location") or {}).get("source") or {}).get("display_name"),
                "abstract_available": bool(work.get("abstract_inverted_index")),
            }
        )

    config.paths.curated_snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    config.paths.curated_provenance_path.parent.mkdir(parents=True, exist_ok=True)
    config.paths.curated_raw_corpus_path.parent.mkdir(parents=True, exist_ok=True)

    config.paths.curated_snapshot_path.write_text(
        json.dumps(raw_snapshot, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    config.paths.curated_raw_corpus_path.write_text(
        json.dumps(selected_records, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    config.paths.curated_provenance_path.write_text(
        json.dumps(
            {
                "source": "OpenAlex",
                "source_url": "https://api.openalex.org",
                "acquired_at_utc": datetime.now(UTC).isoformat(),
                "selection_queries": manifest["selection_queries"],
                "selection_logic": manifest["selection_logic"],
                "limitations": manifest["limitations"],
                "records": provenance_records,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return {
        "record_count": len(selected_records),
        "raw_corpus_path": str(config.paths.curated_raw_corpus_path),
        "snapshot_path": str(config.paths.curated_snapshot_path),
        "provenance_path": str(config.paths.curated_provenance_path),
    }
