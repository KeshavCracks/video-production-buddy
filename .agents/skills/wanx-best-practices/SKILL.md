---
name: wanx-best-practices
description: "Wanxiang/Bailian image generation guidance for WanxImage prompts, negative_prompt usage, styles, sizes, editing, and multi-image references."
metadata:
  provider: bailian
  family: wanxiang
  version: "1.0.0"
---

# Wanx Best Practices

Use this skill before calling OpenMontage `WanxImage`, the Bailian/Wanxiang
image tool. This guidance is provider-specific to Wanxiang image models and
must not be replaced with FLUX-only rules.

## When To Use

- Generating still images with `wan2.7-image-pro`, turbo variants, or other
  Wanxiang image models exposed by `WanxImage`.
- Editing an existing image with natural-language instructions.
- Using one or more reference images to preserve product, character, or style
  consistency across a production set.
- Creating Chinese visual styles such as ink, watercolor, flat illustration,
  anime, portrait, photography, film, or product-packshot looks.

## Prompt Structure

Write direct, visual prompts:

```
[subject/product] + [scene/action] + [style] + [camera/framing] +
[lighting] + [color/material details] + [composition constraints]
```

For physical products, anchor exact geometry and visible brand details in the
positive prompt, then use a reference image when product fidelity matters.
Text-only prompts are not enough for recognizable hardware, packaging, logos,
or UI.

## Negative Prompts

Wanxiang supports `negative_prompt`; use it when the scene has clear failure
modes. Keep it concise and specific.

Good `negative_prompt` examples:

```
extra fingers, distorted logo, wrong product shape, unreadable text,
low resolution, watermark, duplicate object, melted edges
```

Do not copy FLUX guidance that says negative prompts are unsupported. For
WanxImage, `negative_prompt` is part of the tool contract and should be used
when it reduces predictable artifacts.

## Model And Parameter Notes

- Use `wan2.7-image-pro` for higher-quality image generation or editing when
  cost and latency are acceptable.
- Use lower-cost/turbo variants only for drafts, bulk exploration, or cases
  where small artifacts are acceptable.
- Use explicit supported sizes from the tool contract, such as `1024*1024`,
  `1920*1080`, `1080*1920`, or other WanxImage-supported `width*height`
  values.
- Use `style` only when it matches the brief. Prefer explicit prompt language
  for brand-sensitive output instead of relying only on a preset.
- Use `seed` when a production needs repeatable variations.

## Editing And References

For image editing, state what must change and what must remain unchanged:

```
Change the background to a moonlit studio surface. Keep the phone shape,
camera island, logo placement, color, and reflections unchanged.
```

For multi-image references, assign each reference a role in the prompt:

- Product reference: preserve geometry, material, color, and branding.
- Style reference: borrow lighting, palette, texture, or illustration style.
- Pose/layout reference: borrow composition only, not identity.

## Quality Checks

Before accepting Wanxiang output, inspect for:

- Product or logo drift.
- Extra objects, duplicate limbs, or warped hands.
- Text artifacts and unreadable labels.
- Aspect-ratio mismatch against the deliverable.
- Watermarks or provider artifacts.

If any brand-critical geometry is wrong, retry with a clearer prompt and the
reference image rather than explaining the product in prose alone.
