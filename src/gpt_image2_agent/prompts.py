from __future__ import annotations

PRESETS: dict[str, str] = {
    "portrait": "Compose a clean, intentional portrait with natural facial structure, controlled lighting, realistic skin texture, and no random text.",
    "likeness": "Use the supplied reference image only to preserve likeness, proportions, and key identity cues. Do not copy artifacts, watermarks, or background clutter from the reference.",
    "thumbnail": "Create a high-contrast social/YouTube thumbnail composition with one clear focal point, readable negative space, strong silhouette, and no tiny unreadable text.",
    "product": "Create a polished product/landing-page hero image with clear subject separation, premium lighting, useful empty space for layout, and no fake UI text.",
    "no-text": "Do not generate text, captions, watermarks, labels, signatures, UI fragments, or random letters inside the image.",
    "russian-text": "If text is explicitly requested, use short readable Cyrillic, clean typography, correct spelling, and avoid small decorative text.",
}

STYLE_RULES = """Output requirements:
- deliver a finished image, not a sketch;
- keep the main subject clear and not cropped accidentally;
- avoid extra fingers, broken eyes, duplicated faces, watermarks, logos, and random text;
- if references are provided, preserve the requested identity/style while changing only what the prompt asks;
- make the result suitable for a human visual review before publication.
""".strip()


def available_presets() -> list[str]:
    return sorted(PRESETS)


def build_prompt(base_prompt: str, presets: list[str] | None = None, *, refs_count: int = 0) -> str:
    text = base_prompt.strip()
    if not text:
        raise ValueError("Prompt is empty after trimming whitespace.")
    parts = [text]
    for preset in presets or []:
        if preset not in PRESETS:
            raise ValueError(f"Unknown preset: {preset}. Available: {', '.join(available_presets())}")
        parts.append(PRESETS[preset])
    if refs_count:
        parts.append(f"Reference images supplied: {refs_count}. Use them only for the requested likeness/style/composition guidance.")
    parts.append(STYLE_RULES)
    return "\n\n".join(parts)
