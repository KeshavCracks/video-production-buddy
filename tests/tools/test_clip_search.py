from __future__ import annotations

import jsonschema

from tools.video.clip_search import ClipSearch


def test_clip_search_stats_success_payload_matches_output_schema(
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    corpus_dir = "projects/demo/corpus"
    tool = ClipSearch()

    output_properties = tool.output_schema["properties"]
    assert {
        "operation",
        "corpus_dir",
        "corpus_size",
        "rows",
        "per_source",
        "per_kind",
        "mean_motion_score",
        "mean_duration",
    } <= set(output_properties)

    result = tool.execute({"operation": "stats", "corpus_dir": corpus_dir})

    assert result.success is True
    assert result.data["corpus_dir"] == corpus_dir
    jsonschema.validate(instance=result.data, schema=tool.output_schema)


def test_clip_search_requires_project_corpus_dir_before_loading(
    monkeypatch,
    tmp_path,
):
    import lib.corpus as corpus_module

    corpus_dir = tmp_path / "corpus"
    load_calls: list[str] = []

    class ForbiddenCorpus:
        def __init__(self, *args, **kwargs):
            load_calls.append("__init__")
            raise AssertionError("corpus must not be loaded for invalid corpus_dir")

    monkeypatch.setattr(corpus_module, "Corpus", ForbiddenCorpus)

    result = ClipSearch().execute(
        {
            "operation": "stats",
            "corpus_dir": str(corpus_dir),
        }
    )

    assert not result.success
    assert "corpus_dir" in (result.error or "")
    assert "projects/<project-name>/corpus" in (result.error or "")
    assert load_calls == []
    assert not corpus_dir.exists()
