from __future__ import annotations

PRESETS: dict[str, str] = {
    "portrait": "Compose a clean, intentional portrait with natural facial structure, controlled lighting, realistic skin texture, and no random text.",
    "likeness": "Use the supplied identity references only to preserve likeness, proportions, and key identity cues. Do not copy artifacts, watermarks, or background clutter from the references.",
    "thumbnail": "Create a high-contrast social/YouTube thumbnail composition with one clear focal point, readable negative space, strong silhouette, and no tiny unreadable text.",
    "product": "Create a polished product/landing-page hero image with clear subject separation, premium lighting, useful empty space for layout, and no fake UI text.",
    "no-text": "Do not generate text, captions, watermarks, labels, signatures, UI fragments, or random letters inside the image.",
    "russian-text": "If text is explicitly requested, use short readable Cyrillic, clean typography, correct spelling, and avoid small decorative text.",
    "edit": "Treat the supplied edit/base image as the image to modify. When an edit/base image is selected, it is the first supplied image; subsequent images are references. Preserve its core composition and identity unless the user explicitly asks to change them.",
    "brand-style": "Follow the supplied brand/style references consistently: color palette, lighting, composition rhythm, materials, typography mood, and visual density.",
}

STYLE_RULES = """Output requirements:
- deliver a finished image, not a sketch;
- keep the main subject clear and not cropped accidentally;
- avoid extra fingers, broken eyes, duplicated faces, watermarks, logos, and random text;
- if identity references are provided, preserve the requested person/character likeness without cloning background noise;
- if style references are provided, follow the style system without copying private artifacts;
- if an edit/base image is provided, change only what the instruction asks and preserve the rest;
- make the result suitable for a human visual review before publication.
""".strip()


def available_presets() -> list[str]:
    return sorted(PRESETS)


def build_prompt(
    base_prompt: str,
    presets: list[str] | None = None,
    *,
    refs_count: int = 0,
    identity_name: str | None = None,
    style_name: str | None = None,
    style_prompt: str | None = None,
    edit_mode: bool = False,
) -> str:
    text = base_prompt.strip()
    if not text:
        raise ValueError("Prompt is empty after trimming whitespace.")
    parts = [text]
    if edit_mode and "edit" not in (presets or []):
        parts.append(PRESETS["edit"])
    for preset in presets or []:
        if preset not in PRESETS:
            raise ValueError(f"Unknown preset: {preset}. Available: {', '.join(available_presets())}")
        parts.append(PRESETS[preset])
    if identity_name:
        parts.append(f"Saved identity pack selected: {identity_name}. Use its references for likeness only when the request says the person should appear.")
    if style_name:
        parts.append(f"Saved style pack selected: {style_name}. Keep the generated image aligned with that style system.")
    if style_prompt:
        parts.append(f"Style system: {style_prompt.strip()}")
    if refs_count:
        parts.append(f"Reference images supplied: {refs_count}. Use them only for the requested likeness/style/composition/edit guidance.")
    parts.append(STYLE_RULES)
    return "\n\n".join(parts)
