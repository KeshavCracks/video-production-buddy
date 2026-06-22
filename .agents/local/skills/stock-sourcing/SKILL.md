---
name: stock-sourcing
description: Use when sourcing stock images or video clips from Pexels or Pixabay APIs, including query construction, download behavior, licensing metadata, and asset-pipeline integration.
---

# Stock Sourcing

Use this skill for stock media tools and stock-source adapter workflows:

- `pexels_image`
- `pixabay_image`
- `pexels_video`
- `pixabay_video`
- `direct_clip_search`
- `corpus_builder`

`direct_clip_search` and `corpus_builder` route through the shared
`tools/video/stock_sources/` adapter family. That family can include Pexels,
Pixabay, Unsplash, NASA, Archive.org, Wikimedia, NARA, Library of Congress,
Mixkit, Coverr, Videvo, NOAA, ESA, JAXA, Pond5 public domain, and Dareful,
depending on local configuration and provider availability.

## Provider Setup

Pexels requires `PEXELS_API_KEY`. Send it as the raw `Authorization` header
value, not as a bearer token.

Pixabay requires `PIXABAY_API_KEY`. Send it as the `key` query parameter.

These are network/API or hybrid tools. Do not offer them as fully offline paths
unless the requested source is an already-populated local project corpus.

## Query Rules

Use short concrete search phrases. Prefer nouns, setting, activity, and mood
over sentence-like prompts.

For stock video, include duration constraints when the scene length is known.
This avoids downloading clips that are much longer than the edit needs.

For visual consistency, choose provider filters from the project playbook:

- orientation or aspect ratio
- color or palette cues
- category
- media type, such as photo, illustration, vector, film, or animation
- safe search or editor selection flags

## Provider Choice

Use Pexels when the project needs curated real-world photography, high-quality
B-roll, strong orientation filtering, or 4K-capable stock video.

Use Pixabay when the project needs category filtering, illustrations, vectors,
animation clips, or higher request-rate tolerance.

Use public-domain/government/archive adapters when provenance, historical
footage, scientific imagery, or license clarity matters more than commercial
stock polish.

Use `direct_clip_search` when a shot list already exists and the goal is fast
download plus thumbnail inspection. Use `corpus_builder` when the project needs
a reusable local corpus with thumbnails, CLIP embeddings, and query-time
retrieval through `clip_search`.

If exact composition, product identity, brand text, or novel visual structure is
required, use generated-image or generated-video providers instead of stock.

## Download Rules

Always download selected assets immediately into the explicit `output_path`,
`output_dir`, or `corpus_dir` requested by the tool. Do not persist provider CDN
URLs as durable artifacts. Provider URLs can expire, and result ordering can
change.

Write project-scoped outputs under the path family required by the tool:

- generated or acquired media: `projects/<project-name>/assets/...` or
  `projects/<project-name>/renders/...`
- corpora: `projects/<project-name>/corpus/...`
- thumbnails and sidecars: inside the selected project-scoped output directory

## Metadata Rules

Preserve provider metadata in the tool result and downstream asset manifest:

- provider name
- source page URL
- author or photographer name when returned
- provider media id
- license label
- downloaded file path

Pexels and Pixabay allow broad free commercial use, but do not imply creator,
person, brand, or venue endorsement from stock footage alone.
