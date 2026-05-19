# Asset Director — Cinematic Mode Supplement

## Visual Asset Generation

For each scene in `scene_plan.scenes[]`:

### Still Image Generation (hero_shot, detail_close, text_overlay, stat_lower_third)

Provider: Flux (preferred) or DALL-E

Prompt structure:
```
{playbook.asset_generation.image_prompt_prefix}
{scene.description}
shot type: {scene shot type from scene_plan}
lighting: cinematic, {motivated direction}
color grade: {aligned to playbook primary palette}
{playbook.asset_generation.image_negative_prompt} [negative]
```

Output: `assets/scene_{id}_img.jpg`, 1920×1080, JPEG quality 95

### Reference-Aware Branching (run BEFORE picking a video tool)

**Brand-fidelity rule:** Wan 2.6 / 2.7 t2v cannot reliably render specific product geometry (lens count, button placement, brand-mark colors) from prose alone. For ANY scene where the advertised product or brand-mandatory element is visible, branch:

```python
scene_shows_product = scene.get("product_reference_required") is True
product_ref = product_identity_reference  # loaded from artifacts/product_identity_reference.json

if scene_shows_product and product_ref["source_type"] in {"user_provided", "generated", "external_url"}:
    if product_ref["approval_status"] != "approved":
        raise RuntimeError(
            f"Scene {scene['id']} is product-visible, but product_identity_reference "
            "is not approved. Stop before generation and request user approval."
        )
    # PREFERRED: provider identity/reference-to-video if supported. Otherwise
    # generate a scene keyframe constrained by product_ref, then animate it via
    # image_to_video and record conditioning_mode=scene_keyframe_to_video.
    operation = "image_to_video"
    image_path = product_ref.get("selected_reference_image_path") or product_ref.get("selected_reference_url")
elif scene_shows_product and product_ref["source_type"] == "risk_accepted":
    if not product_ref.get("risk_waiver", {}).get("user_approved"):
        raise RuntimeError(
            f"Scene {scene['id']} is product-visible, but the fidelity-risk waiver "
            "is not user-approved. Stop before text-only generation."
        )
    # Text-only is allowed only under this explicit waiver. Record
    # conditioning_mode=text_only_waived in asset_manifest.
    operation = "text_to_video"
else:
    # No product in frame — text-to-video is fine for environmental / lifestyle-only scenes.
    operation = "text_to_video"
```

After each product-visible generated asset, record
`asset_manifest.assets[].product_identity_conditioning` with the approved reference id/path,
conditioning mode, generation tool/model, and fidelity verdict from the visual sanity check.

**Rationale:** without an approved Product Identity Reference, the agent is gambling that Wan happens to generate a phone shape similar to the actual product. For brand-paying advertisers, this is unacceptable risk. The `reference_assets/` convention remains the preferred source when the user has real product photography, but the approved `product_identity_reference` artifact is the contract downstream stages inspect.

### Video Generation (lifestyle_moment, environment_wide)

Provider: Wan 2.7 (Bailian/DashScope) — primary
Fallback: Kling

Prompt structure for **text_to_video** (no product in frame):
```
{scene.description}
cinematic quality, {shot type} shot
camera movement: {slow push-in | static | slow pan} depending on scene
duration: {scene.duration_seconds}s, 24fps
aspect_ratio: {primary aspect ratio from production_bible.deliverables.primary}
{playbook.asset_generation.image_negative_prompt} [negative]
```

Prompt structure for **image_to_video** (product visible, reference image available):
```
{scene.description}
preserve the device geometry and brand markings from the reference image
cinematic quality, {shot type} shot
camera movement: {slow push-in | static | slow pan} depending on scene
duration: {scene.duration_seconds}s, 24fps
aspect_ratio: {primary aspect ratio from production_bible.deliverables.primary}
{playbook.asset_generation.image_negative_prompt} [negative]
```

Output: `assets/scene_{id}_video.mp4`, dimensions matching aspect_ratio (1080×1920 for 9:16, 1920×1080 for 16:9)

**Aspect ratio:** ALWAYS pass `aspect_ratio` to the wan_video_api tool. Do NOT pass `resolution` for non-landscape output (the wan2.6-t2v `resolution` preset forces landscape; pass `aspect_ratio: "9:16"` or `aspect_ratio: "16:9"` instead).

### Brand Landing Frame

For `brand_landing` scene:
1. If brand logo file exists in confirmed reference_files: use it directly
2. If no logo: generate a clean text logo using playbook typography
   - Background: `playbook.visual_language.color_palette.background` (#0D0D0D)
   - Brand name: `playbook.typography.headings` (Inter 800, #F5F5F5)
   - Accent line: `playbook.visual_language.color_palette.accent[0]` (#E94560)

Output: `assets/brand_landing.jpg`, 1920×1080

### Style Consistency

After generating first image, record the visual treatment as a style anchor:
```
EP_STATE.style_anchors["cinematic_lighting"] = "{direction from first successful image}"
EP_STATE.style_anchors["cinematic_color_grade"] = "{grade description}"
EP_STATE.style_anchors["cinematic_first_prompt"] = "{first image prompt}"
```

For all subsequent images: include `EP_STATE.style_anchors["cinematic_lighting"]` explicitly in every prompt.

Consistency check: visually compare each generated image/frame for:
- Consistent color temperature (warm or cool, not mixed)
- Consistent lighting direction
- Consistent depth of field treatment

If inconsistency detected: regenerate with explicit anchor-matching prompt addition.
