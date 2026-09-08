"""Shared image-model options and validation for local planning and requests."""

from __future__ import annotations

import re

DEFAULT_IMAGE_MODEL = "gpt-image-2.5-sunburst"
IMAGE_MODELS = (DEFAULT_IMAGE_MODEL, "gpt-image-2.5-flare")
QUALITIES = ("low", "medium", "high", "xhigh", "max", "auto")
SIZES = {"landscape": "1536x1024", "square": "1024x1024", "portrait": "1024x1536"}
BACKGROUNDS = ("opaque", "transparent", "auto")
OUTPUT_FORMATS = ("png", "jpeg", "webp")


def resolve_size(aspect: str, size: str | None) -> str:
    """Use an explicit size when supplied, otherwise resolve the aspect preset."""
    if size is not None:
        return size
    if aspect not in SIZES:
        raise ValueError(f"Unsupported aspect: {aspect}. Choose from {', '.join(SIZES)}.")
    return SIZES[aspect]


def validate_image_options(
    *, image_model: str, quality: str, size: str, background: str,
    output_format: str = "png", output_compression: int | None = None,
) -> None:
    """Reject unsupported combinations before reading references or using the network."""
    if image_model not in IMAGE_MODELS:
        raise ValueError(f"Unsupported image model: {image_model}. Choose from {', '.join(IMAGE_MODELS)}.")
    if quality not in QUALITIES:
        raise ValueError(f"Unsupported quality: {quality}. Choose from {', '.join(QUALITIES)}.")
    if background not in BACKGROUNDS:
        raise ValueError(f"Unsupported background: {background}. Choose from {', '.join(BACKGROUNDS)}.")
    if output_format not in OUTPUT_FORMATS:
        raise ValueError(f"Unsupported output format: {output_format}. Choose from {', '.join(OUTPUT_FORMATS)}.")
    if background == "transparent" and output_format == "jpeg":
        raise ValueError("Transparent backgrounds require PNG or WebP output.")
    if output_compression is not None:
        if type(output_compression) is not int or not 0 <= output_compression <= 100:
            raise ValueError("Output compression must be an integer between 0 and 100.")
        if output_format not in {"jpeg", "webp"}:
            raise ValueError("Output compression is supported only for JPEG or WebP output.")
    if size == "auto":
        return
    if not re.fullmatch(r"[0-9]+x[0-9]+", size):
        raise ValueError("Size must be 'auto' or WIDTHxHEIGHT, for example 1536x1024.")
    width, height = (int(edge) for edge in size.split("x"))
    if width <= 0 or height <= 0 or width % 16 or height % 16:
        raise ValueError("Size width and height must be positive multiples of 16.")
    if max(width, height) > 3840:
        raise ValueError("Size width and height must be at most 3840 pixels.")
    if max(width, height) > 3 * min(width, height):
        raise ValueError("Size aspect ratio must be at most 3:1 in either orientation.")
    if not 655360 <= width * height <= 8294400:
        raise ValueError("Size must contain between 655360 and 8294400 pixels.")
