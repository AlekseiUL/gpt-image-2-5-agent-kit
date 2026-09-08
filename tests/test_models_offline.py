from __future__ import annotations

import pytest

from gpt_image2_agent.models import BACKGROUNDS, DEFAULT_IMAGE_MODEL, IMAGE_MODELS, QUALITIES, SIZES, resolve_size, validate_image_options


def validate(**options):
    validate_image_options(**{
        "image_model": DEFAULT_IMAGE_MODEL, "quality": "medium", "size": "1024x1024",
        "background": "opaque", **options,
    })


def test_model_registry_is_explicit_and_legacy_is_available():
    assert IMAGE_MODELS == ("gpt-image-2.5-sunburst", "gpt-image-2.5-flare", "gpt-image-2")
    assert DEFAULT_IMAGE_MODEL == IMAGE_MODELS[0]


@pytest.mark.parametrize("image_model", IMAGE_MODELS[:2])
@pytest.mark.parametrize("quality", QUALITIES)
def test_25_models_accept_all_quality_levels(image_model, quality):
    validate(image_model=image_model, quality=quality)


@pytest.mark.parametrize("quality", ["low", "medium", "high", "auto"])
def test_legacy_accepts_supported_quality_levels(quality):
    validate(image_model="gpt-image-2", quality=quality)


@pytest.mark.parametrize("quality", ["xhigh", "max"])
def test_legacy_rejects_25_quality_levels(quality):
    with pytest.raises(ValueError, match="requires a GPT Image 2.5 model"):
        validate(image_model="gpt-image-2", quality=quality)


@pytest.mark.parametrize("background", BACKGROUNDS)
def test_supported_backgrounds(background):
    validate(background=background)


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
