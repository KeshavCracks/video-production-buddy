from __future__ import annotations

import sys
import types
from pathlib import Path

import jsonschema
import pytest

from lib.corpus import Corpus
from tools.video.corpus_builder import CorpusBuilder, _save_as_jpeg
from tools.video.stock_sources import safe_clip_file_name
from tools.video.stock_sources.base import Candidate


class _NoCache:
    def try_link(self, clip_id: str, out_path: Path) -> bool:
        return False

    def ingest(self, *args, **kwargs) -> bool:
        return True


class _PartialFailureSource:
    name = "partial"

    def download(self, candidate: Candidate, out_path: Path) -> Path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"x" * 2048)
        raise OSError("interrupted download")


class _EmptySource:
    name = "empty"

    def is_available(self) -> bool:
        return True

    def search(self, query: str, filters) -> list[Candidate]:
        return []


class _FakeCache:
    def stats(self) -> dict[str, object]:
        return {"entries": 0, "bytes": 0}


def test_corpus_builder_success_payload_matches_output_schema(
    monkeypatch,
    tmp_path,
):
    import tools.video.clip_cache as clip_cache
    import tools.video.stock_sources as stock_sources

    monkeypatch.chdir(tmp_path)
    source = _EmptySource()
    monkeypatch.setattr(stock_sources, "all_sources", lambda: [source])
    monkeypatch.setattr(stock_sources, "available_sources", lambda: [source])
    monkeypatch.setattr(
        stock_sources,
        "source_summary",
        lambda: {
            "configured": 1,
            "total": 1,
            "available_source_names": [source.name],
            "unavailable_source_names": [],
        },
    )
    monkeypatch.setattr(clip_cache, "get_default_cache", lambda: _FakeCache())

    tool = CorpusBuilder()
    output_properties = tool.output_schema["properties"]
    assert {
        "corpus_dir",
        "queries_run",
        "candidates_seen",
        "clips_added",
        "clips_skipped_existing",
        "clips_failed",
        "per_source_counts",
        "added_ids",
        "total_corpus_size",
        "requested_sources",
        "resolved_sources",
        "source_provider_summary",
        "cache_hits",
        "cache_misses",
        "cache_bytes_saved",
        "cache_stats",
        "errors",
    } <= set(output_properties)

    result = tool.execute(
        {
            "corpus_dir": "projects/demo/corpus",
            "queries": [{"query": "rain at night"}],
            "sources": [source.name],
        }
    )

    assert result.success is True
    assert result.data["corpus_dir"] == "projects/demo/corpus"
    assert result.data["clips_added"] == 0
    jsonschema.validate(instance=result.data, schema=tool.output_schema)


def test_corpus_builder_removes_partial_file_when_download_fails(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "cv2", types.SimpleNamespace())
    corpus = Corpus(tmp_path / "corpus")
    candidate = Candidate(
        source="partial",
        source_id="clip_1",
        source_url="https://example.test/landing",
        download_url="https://example.test/clip.mp4",
        kind="video",
    )

    with pytest.raises(OSError, match="interrupted download"):
        CorpusBuilder()._process_candidate(
            cand=candidate,
            src=_PartialFailureSource(),
            corp=corpus,
            query="test",
            thumbs_per_video=1,
            cache=_NoCache(),
            run_cache_stats={"hits": 0, "misses": 0, "bytes_saved": 0},
        )

    final_path = corpus.clips_dir / safe_clip_file_name(candidate.clip_id, ".mp4")
    assert not final_path.exists()


def test_save_as_jpeg_reports_failed_cv2_write(monkeypatch, tmp_path):
    fake_cv2 = types.SimpleNamespace(
        IMWRITE_JPEG_QUALITY=1,
        imread=lambda path: object(),
        imwrite=lambda path, image, params: False,
    )
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2)

    assert not _save_as_jpeg(tmp_path / "input.png", tmp_path / "thumb.jpg")


def test_corpus_builder_requires_project_corpus_dir_before_source_lookup(
    monkeypatch, tmp_path
):
    import tools.video.stock_sources as stock_sources

    corpus_dir = tmp_path / "corpus"
    lookup_calls: list[str] = []

    def fail_available_sources():
        lookup_calls.append("available_sources")
        raise AssertionError("stock sources should not be resolved for invalid corpus_dir")

    monkeypatch.setattr(stock_sources, "available_sources", fail_available_sources)

    result = CorpusBuilder().execute(
        {
            "corpus_dir": str(corpus_dir),
            "queries": [{"query": "rain at night"}],
        }
    )

    assert not result.success
    assert "corpus_dir" in (result.error or "")
    assert "projects/<project-name>/corpus" in (result.error or "")
    assert lookup_calls == []
    assert not corpus_dir.exists()


def test_corpus_builder_idempotency_key_includes_population_inputs():
    tool = CorpusBuilder()
    base = {
        "corpus_dir": "projects/demo/corpus",
        "queries": [{"query": "city skyline", "kind": "video", "per_source": 5}],
        "sources": ["pexels"],
        "filters": {"orientation": "landscape"},
        "max_new_clips": 10,
        "skip_existing": True,
        "thumbs_per_video": 5,
    }
    variants = [
        {"queries": [{"query": "forest trail", "kind": "video", "per_source": 5}]},
        {"sources": ["archive_org"]},
        {"filters": {"orientation": "portrait"}},
        {"max_new_clips": 20},
        {"skip_existing": False},
        {"thumbs_per_video": 8},
    ]

    base_key = tool.idempotency_key(base)
    for variant in variants:
        assert tool.idempotency_key({**base, **variant}) != base_key
