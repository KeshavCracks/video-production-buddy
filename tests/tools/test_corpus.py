from __future__ import annotations

import json
import math

import numpy as np
import pytest

from lib.corpus import EMBED_DIM, ClipRecord, Corpus


def _record(clip_id: str) -> ClipRecord:
    return ClipRecord(
        clip_id=clip_id,
        source="test",
        source_id=clip_id,
        source_url=f"https://example.test/{clip_id}",
        local_path=f"clips/{clip_id}.mp4",
    )


def _vector(first_value: float = 1.0) -> np.ndarray:
    vector = np.zeros(EMBED_DIM, dtype=np.float32)
    vector[0] = first_value
    return vector


def test_corpus_load_maps_clip_ids_to_record_rows_when_index_contains_blank_lines(
    tmp_path,
):
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    rows = [_record("clip_a"), _record("clip_b")]
    with open(corpus_dir / "index.jsonl", "w", encoding="utf-8") as f:
        f.write(json.dumps(rows[0].__dict__) + "\n")
        f.write("\n")
        f.write(json.dumps(rows[1].__dict__) + "\n")
    np.save(corpus_dir / "embeddings.npy", np.zeros((2, EMBED_DIM), dtype=np.float32))
    np.save(corpus_dir / "tag_embeddings.npy", np.zeros((2, EMBED_DIM), dtype=np.float32))

    corpus = Corpus(corpus_dir)
    corpus.load()

    assert corpus.get("clip_a").clip_id == "clip_a"
    assert corpus.get("clip_b").clip_id == "clip_b"


def test_corpus_load_normalizes_single_vector_embedding_banks(tmp_path):
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    row = _record("clip_a")
    with open(corpus_dir / "index.jsonl", "w", encoding="utf-8") as f:
        f.write(json.dumps(row.__dict__) + "\n")
    vector = _vector()
    np.save(corpus_dir / "embeddings.npy", vector)
    np.save(corpus_dir / "tag_embeddings.npy", vector)

    corpus = Corpus(corpus_dir)
    corpus.load()

    assert corpus.clip_embeddings.shape == (1, EMBED_DIM)
    assert corpus.tag_embeddings.shape == (1, EMBED_DIM)
    results = corpus.rank_by_text(vector, k=1)
    assert [(record.clip_id, score) for record, score in results] == [("clip_a", 1.0)]


def test_corpus_load_preserves_rows_when_tag_embedding_bank_is_missing(tmp_path):
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    rows = [_record("clip_a"), _record("clip_b")]
    with open(corpus_dir / "index.jsonl", "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row.__dict__) + "\n")
    clip_vectors = np.zeros((2, EMBED_DIM), dtype=np.float32)
    clip_vectors[0, 0] = 1.0
    clip_vectors[1, 1] = 1.0
    np.save(corpus_dir / "embeddings.npy", clip_vectors)

    corpus = Corpus(corpus_dir)
    corpus.load()

    assert [record.clip_id for record in corpus.records] == ["clip_a", "clip_b"]
    assert corpus.clip_embeddings.shape == (2, EMBED_DIM)
    assert corpus.tag_embeddings.shape == (2, EMBED_DIM)
    assert np.all(corpus.tag_embeddings == 0.0)
    results = corpus.rank_by_text(clip_vectors[0], k=1)
    assert [record.clip_id for record, _score in results] == ["clip_a"]
    assert np.isclose(results[0][1], 0.7)


def test_corpus_load_skips_non_finite_rows_without_shifting_embeddings(tmp_path):
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    row_a = _record("clip_a")
    row_b = _record("clip_b")
    with open(corpus_dir / "index.jsonl", "w", encoding="utf-8") as f:
        f.write("not json\n")
        f.write(json.dumps(row_a.__dict__) + "\n")
        f.write(
            '{"clip_id": "bad_1", "source": "test", "source_id": "bad_1", '
            '"source_url": "https://example.test/bad_1", '
            '"local_path": "clips/bad_1.mp4", "duration": NaN}\n'
        )
        f.write(json.dumps(row_b.__dict__) + "\n")

    clip_vectors = np.zeros((4, EMBED_DIM), dtype=np.float32)
    clip_vectors[0, 0] = 0.25
    clip_vectors[1, 1] = 1.0
    clip_vectors[2, 2] = 1.0
    clip_vectors[3, 3] = 1.0
    tag_vectors = np.zeros((4, EMBED_DIM), dtype=np.float32)
    tag_vectors[0, 10] = 0.25
    tag_vectors[1, 11] = 1.0
    tag_vectors[2, 12] = 1.0
    tag_vectors[3, 13] = 1.0
    np.save(corpus_dir / "embeddings.npy", clip_vectors)
    np.save(corpus_dir / "tag_embeddings.npy", tag_vectors)

    corpus = Corpus(corpus_dir)
    corpus.load()

    assert [record.clip_id for record in corpus.records] == ["clip_a", "clip_b"]
    assert corpus.clip_embeddings.shape == (2, EMBED_DIM)
    assert corpus.tag_embeddings.shape == (2, EMBED_DIM)
    assert np.array_equal(corpus.clip_embeddings[0], clip_vectors[1])
    assert np.array_equal(corpus.clip_embeddings[1], clip_vectors[3])
    assert np.array_equal(corpus.tag_embeddings[0], tag_vectors[1])
    assert np.array_equal(corpus.tag_embeddings[1], tag_vectors[3])


def test_corpus_load_skips_non_strict_json_rows_without_shifting_embeddings(
    tmp_path,
):
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    bad_row = _record("clip_bad")
    good_row = _record("clip_good")
    with open(corpus_dir / "index.jsonl", "w", encoding="utf-8") as f:
        f.write(
            json.dumps(bad_row.__dict__)[:-1]
            + ', "ignored_future_field": NaN}\n'
        )
        f.write(json.dumps(good_row.__dict__) + "\n")

    clip_vectors = np.zeros((2, EMBED_DIM), dtype=np.float32)
    clip_vectors[0, 0] = 1.0
    clip_vectors[1, 1] = 1.0
    tag_vectors = np.zeros((2, EMBED_DIM), dtype=np.float32)
    tag_vectors[0, 10] = 1.0
    tag_vectors[1, 11] = 1.0
    np.save(corpus_dir / "embeddings.npy", clip_vectors)
    np.save(corpus_dir / "tag_embeddings.npy", tag_vectors)

    corpus = Corpus(corpus_dir)
    corpus.load()

    assert [record.clip_id for record in corpus.records] == ["clip_good"]
    assert np.array_equal(corpus.clip_embeddings[0], clip_vectors[1])
    assert np.array_equal(corpus.tag_embeddings[0], tag_vectors[1])


def test_corpus_load_drops_non_finite_visual_embeddings_and_zeroes_bad_tag_rows(
    tmp_path,
):
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    rows = [_record("clip_a"), _record("clip_bad"), _record("clip_c")]
    with open(corpus_dir / "index.jsonl", "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row.__dict__) + "\n")

    clip_vectors = np.zeros((3, EMBED_DIM), dtype=np.float32)
    clip_vectors[0, 0] = 1.0
    clip_vectors[1, 1] = np.nan
    clip_vectors[2, 2] = 1.0
    tag_vectors = np.zeros((3, EMBED_DIM), dtype=np.float32)
    tag_vectors[0, 10] = 1.0
    tag_vectors[1, 11] = 1.0
    tag_vectors[2, 12] = np.inf
    np.save(corpus_dir / "embeddings.npy", clip_vectors)
    np.save(corpus_dir / "tag_embeddings.npy", tag_vectors)

    corpus = Corpus(corpus_dir)
    corpus.load()

    assert [record.clip_id for record in corpus.records] == ["clip_a", "clip_c"]
    assert corpus.clip_embeddings.shape == (2, EMBED_DIM)
    assert corpus.tag_embeddings.shape == (2, EMBED_DIM)
    assert np.all(np.isfinite(corpus.clip_embeddings))
    assert np.all(np.isfinite(corpus.tag_embeddings))
    assert np.array_equal(corpus.clip_embeddings[0], clip_vectors[0])
    assert np.array_equal(corpus.clip_embeddings[1], clip_vectors[2])
    assert np.array_equal(corpus.tag_embeddings[0], tag_vectors[0])
    assert np.array_equal(corpus.tag_embeddings[1], np.zeros(EMBED_DIM, dtype=np.float32))

    results = corpus.rank_by_text(clip_vectors[0], k=2)
    assert [record.clip_id for record, score in results if math.isfinite(score)] == [
        "clip_a",
        "clip_c",
    ]


def test_corpus_load_treats_corrupt_embedding_files_as_empty_banks(tmp_path):
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    row = _record("clip_a")
    with open(corpus_dir / "index.jsonl", "w", encoding="utf-8") as f:
        f.write(json.dumps(row.__dict__) + "\n")
    (corpus_dir / "embeddings.npy").write_bytes(b"not a numpy file")
    (corpus_dir / "tag_embeddings.npy").write_bytes(b"not a numpy file")

    corpus = Corpus(corpus_dir)
    corpus.load()

    assert len(corpus) == 0
    assert corpus.clip_embeddings.shape == (0, EMBED_DIM)
    assert corpus.tag_embeddings.shape == (0, EMBED_DIM)


def test_corpus_save_failure_preserves_previous_persisted_embedding_banks(
    tmp_path, monkeypatch
):
    corpus_dir = tmp_path / "corpus"
    corpus = Corpus(corpus_dir)
    corpus.add(_record("clip_a"), _vector(), _vector())
    corpus.save()

    corpus.add(_record("clip_b"), _vector(0.5), _vector(0.5))

    def corrupting_save(path, arr):
        path.write_bytes(b"partial numpy output")
        raise OSError("simulated interrupted save")

    monkeypatch.setattr("lib.corpus.np.save", corrupting_save)

    try:
        corpus.save()
    except OSError:
        pass

    reloaded = Corpus(corpus_dir)
    reloaded.load()
    assert [record.clip_id for record in reloaded.records] == ["clip_a"]
    assert reloaded.clip_embeddings.shape == (1, EMBED_DIM)
    assert reloaded.tag_embeddings.shape == (1, EMBED_DIM)


def test_corpus_save_rejects_non_finite_record_before_writing_files(tmp_path):
    corpus = Corpus(tmp_path / "corpus")
    bad_record = _record("clip_bad")
    bad_record.duration = math.nan
    corpus.add(bad_record, _vector(), _vector())

    with pytest.raises(ValueError, match="strict JSON"):
        corpus.save()

    assert not corpus.index_path.exists()
    assert not corpus.embed_path.exists()
    assert not corpus.tag_embed_path.exists()


def test_corpus_save_rejects_misaligned_embedding_banks_before_writing_files(tmp_path):
    corpus = Corpus(tmp_path / "corpus")
    corpus.add(_record("clip_a"), _vector(), _vector())
    corpus.clip_embeddings = np.zeros((0, EMBED_DIM), dtype=np.float32)

    with pytest.raises(ValueError, match="align"):
        corpus.save()

    assert not corpus.index_path.exists()
    assert not corpus.embed_path.exists()
    assert not corpus.tag_embed_path.exists()


def test_corpus_save_rejects_non_finite_embedding_banks_without_replacing_previous_files(
    tmp_path,
):
    corpus_dir = tmp_path / "corpus"
    corpus = Corpus(corpus_dir)
    corpus.add(_record("clip_a"), _vector(), _vector())
    corpus.save()
    original_index = corpus.index_path.read_bytes()
    original_embeddings = corpus.embed_path.read_bytes()
    original_tag_embeddings = corpus.tag_embed_path.read_bytes()

    corpus.clip_embeddings[0, 10] = np.nan

    with pytest.raises(ValueError, match="finite"):
        corpus.save()

    assert corpus.index_path.read_bytes() == original_index
    assert corpus.embed_path.read_bytes() == original_embeddings
    assert corpus.tag_embed_path.read_bytes() == original_tag_embeddings


def test_corpus_add_rejects_non_finite_clip_embedding_before_mutation(tmp_path):
    corpus = Corpus(tmp_path / "corpus")
    clip_embedding = _vector()
    clip_embedding[10] = np.nan

    with pytest.raises(ValueError, match="finite"):
        corpus.add(_record("clip_bad"), clip_embedding, _vector())

    assert len(corpus) == 0
    assert corpus.get("clip_bad") is None
    assert corpus.clip_embeddings.shape == (0, EMBED_DIM)
    assert corpus.tag_embeddings.shape == (0, EMBED_DIM)


def test_corpus_add_rejects_non_finite_tag_embedding_before_mutation(tmp_path):
    corpus = Corpus(tmp_path / "corpus")
    tag_embedding = _vector()
    tag_embedding[10] = np.inf

    with pytest.raises(ValueError, match="finite"):
        corpus.add(_record("clip_bad"), _vector(), tag_embedding)

    assert len(corpus) == 0
    assert corpus.get("clip_bad") is None
    assert corpus.clip_embeddings.shape == (0, EMBED_DIM)
    assert corpus.tag_embeddings.shape == (0, EMBED_DIM)


def test_corpus_diversify_drops_duplicate_candidate_ids(tmp_path):
    corpus = Corpus(tmp_path / "corpus")
    vec_a = _vector()
    vec_b = np.zeros(EMBED_DIM, dtype=np.float32)
    vec_b[1] = 1.0
    corpus.add(_record("clip_a"), vec_a, vec_a)
    corpus.add(_record("clip_b"), vec_b, vec_b)

    kept = corpus.diversify(["clip_a", "clip_a", "clip_b"], n=2)

    assert kept == ["clip_a", "clip_b"]


def test_corpus_diversify_respects_zero_requested_count(tmp_path):
    corpus = Corpus(tmp_path / "corpus")
    corpus.add(_record("clip_a"), _vector(), _vector())

    assert corpus.diversify(["clip_a"], n=0) == []
