from __future__ import annotations

PRESETS: dict[str, str] = {
    "portrait": "Compose an intentional portrait with clear facial structure and controlled lighting. For a photographic brief retain natural skin texture; honor the requested medium and crop.",
    "likeness": "Use identity references to preserve the requested person's distinguishing features and proportions. Do not copy background clutter or blend different identities.",
    "thumbnail": "Create one clear focal point with strong contrast, readable hierarchy and text at a scale appropriate to the requested export.",
    "product": "Keep the requested product recognizable, with clear subject separation, task-appropriate lighting and useful space for the requested layout.",
    "no-text": "Do not include lettering, captions, labels, logos, UI text or watermarks in this no-text image.",
    "russian-text": "Render supplied Cyrillic copy verbatim, preserving language, spelling, case, punctuation and line breaks. Do not translate, shorten, paraphrase, duplicate or add text. Follow the specified placement, typography and contrast.",
    "edit": "Edit the first supplied image. Apply only the requested changes; preserve all other content, identity, composition, lighting, texture and lettering unless explicitly changed. Other images are scoped references, not replacement bases.",
    "brand-style": "Use the requested brand palette, materials, lighting, typography direction and visual density consistently.",
}
REFERENCE_ROLES = {
    "edit_base": "Base image to modify. Preserve everything outside the requested changes.",
    "identity": "Identity anchor for the requested subject; do not copy pose, clothing or background unless asked, or blend different people.",
    "style": "Use the requested palette, materials, lighting and visual density; do not copy people, scenery or lettering unless asked.",
    "logo": "Preserve the requested mark's shape, proportions, colors and exact lettering; place or restyle it only as requested.",
    "layout": "Use the requested spatial arrangement and scale; do not inherit identities, text or style automatically.",
    "general": "Use only for its stated purpose in the request; do not infer an identity, style or edit-base role.",
}
STYLE_RULES = """Task-specific output requirements:
- honor the requested medium, finish and framing, including sketches or deliberate crops;
- preserve literal requested text without translation, abbreviation or extra characters;
- include requested logos and lettering, and avoid unrequested additions;
- use each numbered reference only for its assigned role;
- task-specific requirements take precedence over preset and style defaults.
""".strip()


def available_presets() -> list[str]:
    return sorted(PRESETS)


def validate_presets(presets: list[str]) -> list[str]:
    for preset in presets:
        if preset not in PRESETS:
            raise ValueError(f"Unknown preset: {preset}. Available: {', '.join(available_presets())}")
    if "no-text" in presets and "russian-text" in presets:
        raise ValueError("no-text and russian-text presets cannot be combined.")
    return list(dict.fromkeys(presets))


def build_prompt(
    base_prompt: str,
    presets: list[str] | None = None,
    *,
    refs_count: int = 0,
    identity_name: str | None = None,
    style_name: str | None = None,
    style_prompt: str | None = None,
    edit_mode: bool = False,
    reference_roles: list[str] | None = None,
    preserve: list[str] | None = None,
) -> str:
    text = base_prompt.strip()
    if not text:
        raise ValueError("Prompt is empty after trimming whitespace.")
    selected = validate_presets(presets or [])
    if (preserve or "edit" in selected) and not edit_mode:
        raise ValueError("--preserve and the edit preset require --edit-image.")
    if edit_mode and refs_count < 1:
        raise ValueError("An edit prompt requires at least one base image.")
    default_roles = (["edit_base"] + ["general"] * (refs_count - 1)) if edit_mode else ["general"] * refs_count
    roles = reference_roles if reference_roles is not None else default_roles
    if len(roles) != refs_count or any(role not in REFERENCE_ROLES for role in roles):
        raise ValueError("Reference roles must match the number of supplied images and use supported roles.")
    if reference_roles is not None and ((edit_mode and roles[:1] != ["edit_base"]) or (not edit_mode and "edit_base" in roles) or roles.count("edit_base") > 1):
        raise ValueError("The edit base must be the first image and have the only edit_base role.")
    parts = [text]
    if edit_mode and "edit" not in selected:
        parts.append(PRESETS["edit"])
    parts.extend(PRESETS[preset] for preset in selected)
    if identity_name:
        parts.append(f"Saved identity pack: {identity_name}. Use only for the requested person/context.")
    if style_name:
        parts.append(f"Saved style pack: {style_name}.")
    if style_prompt:
        parts.append(f"Style system: {style_prompt.strip()}")
    if refs_count:
        parts.append("Reference roles in attachment order:\n" + "\n".join(f"Image {i} [{role}]: {REFERENCE_ROLES[role]}" for i, role in enumerate(roles, 1)))
    if preserve:
        if any(not item.strip() for item in preserve):
            raise ValueError("Preserve instructions must not be empty.")
        parts.append("Preserve unchanged:\n" + "\n".join(f"- {item.strip()}" for item in preserve))
    parts.append(STYLE_RULES)
    return "\n\n".join(parts)
