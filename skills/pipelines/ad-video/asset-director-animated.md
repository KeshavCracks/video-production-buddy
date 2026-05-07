# Asset Director — Animated Mode Supplement

## Dynamic Scenes Policy (MANDATORY — all ad-video productions)

**Every moment must be visually dynamic.** Static images with pan/zoom (ken-burns, zoom-in, zoom-out, parallax) are PROHIBITED for the following beat types:

| Beat | PROHIBITED | USE INSTEAD |
|------|-----------|-------------|
| Hook / chaos (B1) | `anime_scene` + any camera motion on a still image | `notification_scene` — spring-animated icon grid, badge counters, banner cascade |
| Product reveal (B3, B4) | `anime_scene` + ken-burns on a UI screenshot | `dashboard_scene` — sidebar spring-in, task cards, toast notification |
| CTA / brand (B5) | `hero_title` or `text_card` on a static background | `brand_card` — letter-spring wordmark, underline draw, tagline fade, CTA, pulse |

`anime_scene` is **only permitted** when all three conditions hold:
1. The scene requires a real photographic or AI-generated image (lifestyle, environment, texture)
2. It is paired with a `particles` effect (not bare camera motion alone)
3. The beat is NOT hook, product-reveal, or CTA

Any scene plan that routes hook / product / CTA beats to `anime_scene` must be corrected before assets are generated. Use the dynamic cut types above — they are built into the Remotion composer and require no image assets.

## Visual Asset Generation

For each scene in `scene_plan.scenes[]` where `motion_required: false`:

No external image generation needed for text-based scenes (`text_card`, `stat_reveal`, `cta_hold`). These are rendered from data by Remotion using the playbook's typography and color tokens.

For scenes requiring visual backgrounds (`motion_loop`, `split_screen`, `logo_reveal`, `product_demo`):

### Image Generation (Flux or DALL-E)

Prompt structure:
```
{playbook.asset_generation.image_prompt_prefix}
{scene.description} — flat vector illustration style, bold colors
Primary color: {playbook.visual_language.color_palette.primary[0]}
Accent: {playbook.visual_language.color_palette.accent[0]}
Background: {playbook.visual_language.color_palette.background}
{playbook.asset_generation.image_negative_prompt} [negative]
```

Output: `assets/scene_{id}_bg.png`, 1920×1080

### Video Generation (motion_required: true)

For `motion_loop` and `product_demo` scenes:

Provider: Wan 2.7 (Bailian/DashScope) — primary
Fallback: Kling

Prompt structure:
```
{scene.description}
style: motion graphics, flat animation, bold colors
duration: {scene.duration_seconds}s
{playbook.asset_generation.image_negative_prompt} [negative]
```

Output: `assets/scene_{id}_video.mp4`, 1920×1080, duration ≥ scene.duration_seconds

### Style Consistency

After generating each image/video:
- Check that primary color `#1A1A2E` or `#E94560` (accent) appears in frame
- Check that background is dark (luminance < 0.3 on average)
- If mismatch: regenerate with stronger color directive in prompt
- Store passing style token in `EP_STATE.style_anchors`:
  ```
  EP_STATE.style_anchors["animated_palette_confirmed"] = true
  EP_STATE.style_anchors["first_bg_seed"] = "{seed or prompt hash}"
  ```

## Remotion-Specific Asset Notes

Remotion renders text cards, stat reveals, and CTA holds from data — no pre-generated images needed.

Pass to compose director via `asset_manifest.remotion_data`:
```json
{
  "text_cards": [
    {"scene_id": "scene-1", "text": "45 minutes. Gone.", "font_weight": 900, "entrance": "scale-up-bounce"}
  ],
  "stat_reveals": [
    {"scene_id": "scene-2", "value": "4 HRS", "label": "wasted every week", "animation": "count-up"}
  ],
  "cta_data": {
    "scene_id": "scene-7",
    "cta_text": "Start free at flowcut.io",
    "brand_name": "Flowcut",
    "url": "flowcut.io"
  }
}
```
