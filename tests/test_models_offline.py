from __future__ import annotations

import pytest

from gpt_image25_agent.models import BACKGROUNDS, DEFAULT_IMAGE_MODEL, IMAGE_MODELS, OUTPUT_FORMATS, QUALITIES, SIZES, resolve_size, validate_image_options


def validate(**options):
    validate_image_options(**{
        "image_model": DEFAULT_IMAGE_MODEL, "quality": "medium", "size": "1024x1024",
        "background": "opaque", **options,
    })


def test_model_registry_is_explicit_and_25_only():
    assert IMAGE_MODELS == ("gpt-image-2.5-sunburst", "gpt-image-2.5-flare")
    assert DEFAULT_IMAGE_MODEL == IMAGE_MODELS[0]


@pytest.mark.parametrize("image_model", IMAGE_MODELS)
@pytest.mark.parametrize("quality", QUALITIES)
def test_25_models_accept_all_quality_levels(image_model, quality):
    validate(image_model=image_model, quality=quality)


@pytest.mark.parametrize("quality", QUALITIES)
def test_legacy_is_rejected_at_every_quality(quality):
    with pytest.raises(ValueError, match="Unsupported image model"):
        validate(image_model="gpt-image-2", quality=quality)


@pytest.mark.parametrize("image_model", [
    "gpt-image-1", "gpt-image-2.5", "gpt-image-2.5-sunburst-2026-09-08", "gpt-image-2.5-flare-2026-09-08",
])
def test_only_supported_aliases_are_runnable(image_model):
    with pytest.raises(ValueError, match="Unsupported image model"):
        validate(image_model=image_model)


@pytest.mark.parametrize("background", BACKGROUNDS)
def test_supported_backgrounds(background):
    validate(background=background)


@pytest.mark.parametrize("output_format", OUTPUT_FORMATS)
def test_supported_formats_with_default_compression(output_format):
    validate(output_format=output_format)


@pytest.mark.parametrize("output_format", ["png", "webp"])
def test_alpha_formats_allow_transparency(output_format):
    validate(output_format=output_format, background="transparent")


def test_jpeg_cannot_request_transparency_even_with_auto_size():
    with pytest.raises(ValueError, match="Transparent backgrounds require PNG or WebP"):
        validate(output_format="jpeg", background="transparent", size="auto")


@pytest.mark.parametrize("output_format", ["jpeg", "webp"])
@pytest.mark.parametrize("output_compression", [0, 50, 100])
def test_compression_accepts_integer_boundaries(output_format, output_compression):
    validate(output_format=output_format, output_compression=output_compression)


@pytest.mark.parametrize("output_compression", [-1, 101, True, False, 50.0, 50.5, "50"])
def test_invalid_compression_is_rejected(output_compression):
    with pytest.raises(ValueError, match="integer between 0 and 100"):
        validate(output_format="webp", output_compression=output_compression)


def test_compression_is_rejected_for_png_even_with_auto_size():
    with pytest.raises(ValueError, match="only for JPEG or WebP"):
        validate(output_compression=100, size="auto")


@pytest.mark.parametrize("size", [
    "auto", *SIZES.values(), "1024x640", "640x1024", "3840x2160", "2160x3840", "3072x1024", "1024x3072",
])
def test_supported_sizes_including_boundaries(size):
    validate(size=size)


@pytest.mark.parametrize("size,message", [
    ("", "WIDTHxHEIGHT"), ("AUTO", "WIDTHxHEIGHT"), ("1024X1024", "WIDTHxHEIGHT"),
    ("1024 x 1024", "WIDTHxHEIGHT"), ("-1024x1024", "WIDTHxHEIGHT"),
    ("1024.0x1024", "WIDTHxHEIGHT"), ("0x1024", "positive multiples"),
    ("1023x1024", "positive multiples"), ("1024x1023", "positive multiples"),
    ("3856x1024", "at most 3840"), ("1024x3856", "at most 3840"),
    ("3072x1008", "aspect ratio"), ("1008x3072", "aspect ratio"),
    ("1024x624", "between 655360 and 8294400"),
    ("3840x2176", "between 655360 and 8294400"),
])
def test_invalid_sizes_are_explained(size, message):
    with pytest.raises(ValueError, match=message):
        validate(size=size)


@pytest.mark.parametrize("options,message", [
    ({"image_model": "gpt-image-unknown"}, "Unsupported image model"),
    ({"quality": "ultra"}, "Unsupported quality"),
    ({"background": "blue"}, "Unsupported background"),
    ({"output_format": "jpg"}, "Unsupported output format"),
    ({"output_format": "gif"}, "Unsupported output format"),
])
def test_unknown_options_are_rejected(options, message):
    with pytest.raises(ValueError, match=message):
        validate(**options)


@pytest.mark.parametrize("aspect,size", SIZES.items())
def test_resolve_aspect_preset(aspect, size):
    assert resolve_size(aspect, None) == size


def test_explicit_size_wins_over_aspect():
    assert resolve_size("portrait", "2048x1024") == "2048x1024"
    assert resolve_size("unused", "auto") == "auto"


def test_unknown_aspect_without_size_is_rejected():
    with pytest.raises(ValueError, match="Unsupported aspect"):
        resolve_size("panorama", None)
