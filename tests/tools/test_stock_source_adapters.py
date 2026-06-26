import hashlib
import re
from pathlib import Path

from tools.video.stock_sources import (
    SearchFilters,
    absolute_url,
    all_sources,
    safe_clip_file_name,
)
from tools.video.stock_sources.coverr import CoverrSource
from tools.video.stock_sources.loc import LibraryOfCongressSource
from tools.video.stock_sources.nara import NARASource
from tools.video.stock_sources.nasa import _sanitize_source_id
from tools.video.stock_sources.unsplash import _build_download_url, _orientation_for_unsplash
from tools.video.stock_sources.videvo import VidevoSource
from tools.video.stock_sources.wikimedia import (
    _build_search_queries,
    _kind_from_mime,
    _meta_value,
)


SOURCE_DIR = Path(__file__).resolve().parents[2] / "tools" / "video" / "stock_sources"


def test_stock_source_autodiscovery_keeps_adapters_visible():
    names = {source.name for source in all_sources()}

    assert {"wikimedia", "unsplash", "nasa", "nara"}.issubset(names)


def test_stock_source_adapters_use_process_stable_ids():
    offenders = []
    for path in SOURCE_DIR.glob("*.py"):
        if path.name == "__init__.py":
            continue
        if re.search(r"\bhash\s*\(", path.read_text(encoding="utf-8")):
            offenders.append(path.name)

    assert offenders == []


def test_stock_source_adapters_do_not_stringify_missing_provider_ids():
    pattern = re.compile(r"source_id=str\([^)]*\.get\([\"']id[\"']")
    offenders = []
    for path in SOURCE_DIR.glob("*.py"):
        if path.name == "__init__.py":
            continue
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if pattern.search(line):
                offenders.append(f"{path.name}:{line_number}:{line.strip()}")

    assert offenders == []


def test_stock_source_adapters_do_not_concatenate_relative_urls():
    pattern = re.compile(r'f"[^"]*\{(?:href|download_url|thumb|url|image_url)\}[^"]*"')
    offenders = []
    for path in SOURCE_DIR.glob("*.py"):
        if path.name == "__init__.py":
            continue
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if pattern.search(line):
                offenders.append(f"{path.name}:{line_number}:{line.strip()}")

    assert offenders == []


def test_absolute_url_resolves_relative_paths_without_leading_slash():
    assert absolute_url("https://example.test", "media/clip.mp4") == (
        "https://example.test/media/clip.mp4"
    )
    assert absolute_url("https://example.test/root", "media/clip.mp4") == (
        "https://example.test/root/media/clip.mp4"
    )


def test_safe_clip_file_name_bounds_names_and_sanitizes_extensions():
    clip_id = "pexels_" + ("a" * 300)
    file_name = safe_clip_file_name(clip_id, "../../escape.mp4")

    assert len(file_name) <= 120
    assert "/" not in file_name
    assert "\\" not in file_name
    assert file_name.endswith(".mp4")
    assert f"-{hashlib.sha256(clip_id.encode('utf-8')).hexdigest()[:12]}" in file_name


def test_safe_clip_file_name_bounds_directory_names_without_extension():
    clip_id = "archive_org_" + ("b" * 300)
    directory_name = safe_clip_file_name(clip_id, "")

    assert len(directory_name) <= 120
    assert directory_name.endswith(hashlib.sha256(clip_id.encode("utf-8")).hexdigest()[:12])


def test_nasa_sanitized_source_ids_keep_long_ids_unique():
    shared_prefix = "Mission " + ("A" * 140)

    first = _sanitize_source_id(f"{shared_prefix} alpha")
    second = _sanitize_source_id(f"{shared_prefix} beta")

    assert first != second
    assert len(first) <= 120
    assert len(second) <= 120


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_coverr_search_falls_back_to_stable_ids_when_api_ids_are_missing(monkeypatch):
    import requests

    monkeypatch.setattr(
        requests,
        "get",
        lambda *args, **kwargs: _FakeResponse(
            {
                "hits": [
                    {"urls": {"mp4_720": "https://cdn.test/a.mp4"}},
                    {"urls": {"mp4_720": "https://cdn.test/b.mp4"}},
                ]
            }
        ),
    )

    candidates = CoverrSource().search("city", SearchFilters(kind="video"))

    source_ids = [candidate.source_id for candidate in candidates]
    assert len(source_ids) == 2
    assert len(set(source_ids)) == 2
    assert all(source_id for source_id in source_ids)


def test_videvo_search_falls_back_to_stable_ids_when_api_ids_are_missing(monkeypatch):
    import requests

    monkeypatch.setenv("VIDEVO_API_KEY", "test-key")
    monkeypatch.setattr(
        requests,
        "get",
        lambda *args, **kwargs: _FakeResponse(
            {
                "data": [
                    {"download_url": "https://cdn.test/a.mp4"},
                    {"download_url": "https://cdn.test/b.mp4"},
                ]
            }
        ),
    )

    candidates = VidevoSource().search("city", SearchFilters(kind="video"))

    source_ids = [candidate.source_id for candidate in candidates]
    assert len(source_ids) == 2
    assert len(set(source_ids)) == 2
    assert all(source_id for source_id in source_ids)


def test_nara_and_loc_extract_media_urls_with_query_strings():
    nara_item = {
        "naId": "123",
        "objects": [{"url": "https://catalog.test/a.mp4?download=1", "mimeType": ""}],
    }
    loc_item = {
        "id": "/item/test/",
        "resources": [{"files": [[{"url": "/media/test.mp4?download=1", "mimetype": ""}]]}],
    }

    nara_candidates = NARASource()._extract_candidates(
        nara_item, kind="video", filters=SearchFilters(kind="video")
    )
    loc_candidates = LibraryOfCongressSource()._extract_candidates(
        loc_item, kind="video", filters=SearchFilters(kind="video")
    )

    assert [candidate.download_url for candidate in nara_candidates] == [
        "https://catalog.test/a.mp4?download=1"
    ]
    assert [candidate.download_url for candidate in loc_candidates] == [
        "https://www.loc.gov/media/test.mp4?download=1"
    ]


def test_wikimedia_search_query_respects_kind_and_fallback_tokens():
    video_cascade = _build_search_queries("rain city", "video")
    image_cascade = _build_search_queries("rain city", "image")
    fallback_cascade = _build_search_queries("1950s family watching television", "video")

    assert video_cascade[0][1].startswith("filetype:video")
    assert image_cascade[0][1].startswith("filetype:image")
    assert [label for label, _ in fallback_cascade] == ["full", "top2_or", "single_best"]
    assert fallback_cascade[1][1] == "filetype:video television watching"


def test_wikimedia_and_unsplash_helpers_normalize_external_metadata():
    assert _kind_from_mime("video/webm", "File:foo.webm") == "video"
    assert _kind_from_mime("image/jpeg", "File:foo.jpg") == "image"
    assert _meta_value({"Artist": {"value": "<a href='/wiki/User:Test'>Test User</a>"}}, "Artist") == "Test User"
    assert _orientation_for_unsplash("square") == "squarish"

    url = _build_download_url("https://images.unsplash.com/photo-123?ixid=abc", 1920)
    assert "ixid=abc" in url
    assert "w=1920" in url
    assert "fm=jpg" in url
