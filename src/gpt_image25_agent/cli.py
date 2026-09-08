from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from .auth import AuthError, read_token
from .client import CODEX_BASE_URL, DEFAULT_HOST_MODEL, ClientError, generate_image
from .models import BACKGROUNDS, DEFAULT_IMAGE_MODEL, IMAGE_MODELS, QUALITIES, SIZES, OUTPUT_FORMATS, resolve_size, validate_image_options
from .files import PolicyError, default_root, read_prompt, resolve_output_path, validate_refs, validate_mask
from .library import list_library, load_identity_refs, load_style, save_identity, save_style
from .prompts import REFERENCE_ROLES, available_presets, build_prompt
from .receipts import build_receipt, write_receipt, validate_receipt_path, actual_output_metadata
from .redaction import sanitize_error_text
from .review import build_review_markdown


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Agent-safe GPT Image 2.5 prompt/reference toolkit")
    parser.add_argument("prompt", nargs="?", help="Image request. Use --prompt-file for long prompts.")
    parser.add_argument("--prompt-file", type=Path, help="Read UTF-8 prompt from a text file")
    parser.add_argument("--preset", action="append", choices=available_presets(), default=[], help="Prompt preset; repeatable")
    parser.add_argument("--ref", action="append", type=Path, default=[], help="One-shot reference image path; repeatable")
    parser.add_argument("--ref-role", action="append", choices=sorted(set(REFERENCE_ROLES) - {"edit_base"}), default=[], help="Role for each explicit --ref in attachment order; supply one per ref")
    parser.add_argument("--preserve", action="append", default=[], help="Invariant to preserve in an edit; repeatable, requires --edit-image")
    parser.add_argument("--mask", type=Path, help="PNG alpha mask for a PNG edit base; same dimensions; transparent areas are editable")
    parser.add_argument("--identity", help="Use a saved identity pack created with --add-identity")
    parser.add_argument("--style", help="Use a saved style pack created with --add-style")
    parser.add_argument("--edit-image", type=Path, help="Base image to modify while preserving requested parts")
    parser.add_argument("--edit", help="Edit instruction. Equivalent to using prompt with --edit-image, but clearer for agents")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Safe root for outputs, refs, prompt files, library and receipts by default")
    parser.add_argument("--out", type=Path, help="Output image path matching --output-format")
    parser.add_argument("--receipt", type=Path, help="Optional JSON receipt path. In dry-run this is the only intentional write.")
    parser.add_argument("--quality", choices=sorted(QUALITIES), default="medium")
    parser.add_argument("--image-model", choices=IMAGE_MODELS, default=DEFAULT_IMAGE_MODEL, help="Image tool model; Sunburst by default, Flare for faster everyday generation")
    parser.add_argument("--aspect", choices=sorted(SIZES), default="landscape")
    parser.add_argument("--size", help="Image size: auto or WIDTHxHEIGHT (multiples of 16). Overrides --aspect.")
    parser.add_argument("--background", choices=BACKGROUNDS, default="opaque", help="Output background; transparency requires PNG or WebP")
    parser.add_argument("--output-format", choices=OUTPUT_FORMATS, default="png")
    parser.add_argument("--output-compression", type=int, help="JPEG/WebP compression, 0-100; omit for PNG")
    parser.add_argument("--action", choices=["auto", "generate", "edit"], help="Force generation or editing; edit requires --edit-image")
    parser.add_argument("--host-model", default=DEFAULT_HOST_MODEL)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--json", action="store_true", help="Print compact JSON result")
    parser.add_argument("--review-markdown", action="store_true", help="Print a human-readable Markdown review plan instead of JSON/plain output")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print plan without auth/network/output write. This is the default unless --live is passed. May write --receipt if requested.")
    parser.add_argument("--live", action="store_true", help="Actually call backend and write the verified image")
    parser.add_argument("--overwrite", action="store_true", help="Allow replacing existing output")
    parser.add_argument("--include-prompt-in-receipt", action="store_true", help="Store full final prompt in receipt. Default stores only hash.")
    parser.add_argument("--auth-provider", choices=["env", "file", "command"], default="env")
    parser.add_argument("--token-env", default="CHATGPT_CODEX_ACCESS_TOKEN")
    parser.add_argument("--token-file", type=Path)
    parser.add_argument("--token-command", help="Trusted local command argv string; executed without shell")
    parser.add_argument("--allow-output-outside-root", action="store_true")
    parser.add_argument("--allow-ref-outside-root", action="store_true")
    parser.add_argument("--allow-prompt-file-outside-root", action="store_true")
    parser.add_argument("--allow-receipt-outside-root", action="store_true")

    parser.add_argument("--add-identity", metavar="NAME", help="Create a local saved identity pack from --ref images, then exit")
    parser.add_argument("--identity-notes", default="", help="Optional notes stored with --add-identity")
    parser.add_argument("--add-style", metavar="NAME", help="Create a local saved style pack from --style-prompt/--style-preset/--ref, then exit")
    parser.add_argument("--style-prompt", default="", help="Style-system text for --add-style or one-shot generation")
    parser.add_argument("--style-preset", action="append", choices=available_presets(), default=[], help="Preset stored in --add-style; repeatable")
    parser.add_argument("--list-library", action="store_true", help="List saved identities/styles, then exit")
    return parser.parse_args(argv)


def emit(obj: dict, *, as_json: bool) -> None:
    print(json.dumps(obj, ensure_ascii=False) if as_json else json.dumps(obj, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = default_root(args.root)
    dry_run = args.dry_run or not args.live
    try:
        if not math.isfinite(args.timeout) or args.timeout <= 0:
            raise PolicyError("--timeout must be a positive finite number.")
        if args.json and args.review_markdown:
            raise PolicyError("Pass either --json or --review-markdown, not both.")
        if args.list_library:
            emit({"success": True, "library": list_library(root)}, as_json=args.json)
            return 0
        if args.add_identity:
            manifest = save_identity(root, args.add_identity, args.ref, notes=args.identity_notes, allow_ref_outside=args.allow_ref_outside_root)
            emit({"success": True, "created": "identity", "manifest": manifest}, as_json=args.json)
            return 0
        if args.add_style:
            manifest = save_style(root, args.add_style, prompt=args.style_prompt, presets=args.style_preset, refs=args.ref, allow_ref_outside=args.allow_ref_outside_root)
            emit({"success": True, "created": "style", "manifest": manifest}, as_json=args.json)
            return 0

        if args.edit and (args.prompt or args.prompt_file):
            raise PolicyError("Pass either --edit or a normal prompt/--prompt-file, not both.")
        if args.edit and not args.edit_image:
            raise PolicyError("--edit requires --edit-image with the base image to modify.")
        if (args.preserve or args.mask or args.action == "edit") and not args.edit_image:
            raise PolicyError("--preserve, --mask and action edit require --edit-image.")
        if args.edit_image and args.action == "generate":
            raise PolicyError("An edit base cannot be combined with action generate.")
        if args.ref_role and len(args.ref_role) != len(args.ref):
            raise PolicyError("Supply one --ref-role per explicit --ref.")
        size = resolve_size(args.aspect, args.size)
        validate_image_options(image_model=args.image_model, quality=args.quality, size=size, background=args.background, output_format=args.output_format, output_compression=args.output_compression)
        aspect = ("auto" if size == "auto" else "custom") if args.size is not None else args.aspect
        action = args.action or ("edit" if args.edit_image else "auto")
        if args.mask and action != "edit":
            raise PolicyError("A mask requires action edit.")
        prompt_source = args.edit or args.prompt
        raw_prompt = read_prompt(prompt_source, args.prompt_file, root=root, allow_prompt_file_outside=args.allow_prompt_file_outside_root)
        refs = validate_refs(args.ref, root=root, allow_outside=args.allow_ref_outside_root)
        identity_refs: list[Path] = []
        style_refs: list[Path] = []
        style_prompt = args.style_prompt.strip()
        style_presets: list[str] = []
        if args.identity:
            identity_refs = load_identity_refs(root, args.identity)
        if args.style:
            saved_style_prompt, style_presets, style_refs = load_style(root, args.style)
            style_prompt = "\n\n".join(p for p in [saved_style_prompt, style_prompt] if p)
        edit_refs: list[Path] = []
        if args.edit_image:
            edit_refs = validate_refs([args.edit_image], root=root, allow_outside=args.allow_ref_outside_root)
        all_refs = validate_refs(edit_refs + identity_refs + style_refs + refs, root=root, allow_outside=args.allow_ref_outside_root)
        reference_roles = (["edit_base"] * len(edit_refs) + ["identity"] * len(identity_refs) + ["style"] * len(style_refs) + (args.ref_role or ["general"] * len(refs)))
        mask = validate_mask(args.mask, edit_refs[0], root=root, allow_outside=args.allow_ref_outside_root) if args.mask else None
        presets = list(dict.fromkeys([*args.preset, *style_presets]))
        final_prompt = build_prompt(
            raw_prompt,
            presets,
            refs_count=len(all_refs),
            identity_name=args.identity,
            style_name=args.style,
            style_prompt=style_prompt or None,
            edit_mode=bool(args.edit_image),
            reference_roles=reference_roles,
            preserve=args.preserve,
        )
        out = resolve_output_path(args.out, raw_prompt, root=root, allow_outside=args.allow_output_outside_root, overwrite=args.overwrite, create_parent=False, output_format=args.output_format)
        if args.receipt:
            validate_receipt_path(args.receipt, root=root, allow_outside=args.allow_receipt_outside_root)
        receipt = build_receipt(status="planned" if dry_run else "pending", dry_run=dry_run, backend=CODEX_BASE_URL, host_model=args.host_model, image_model=args.image_model, quality=args.quality, aspect=aspect, size=size, background=args.background, action=action, out=out, prompt=final_prompt, refs=all_refs, include_prompt=args.include_prompt_in_receipt, output_format=args.output_format, output_compression=args.output_compression, reference_roles=reference_roles, mask=mask)
        receipt["identity"] = args.identity
        receipt["style"] = args.style
        receipt["edit_image"] = str(args.edit_image) if args.edit_image else None
        if dry_run:
            result = {"success": True, "dry_run": True, "would_call": CODEX_BASE_URL + "/responses", "final_prompt": final_prompt, "refs_count": len(all_refs), "receipt": receipt}
            if args.receipt:
                write_receipt(args.receipt, receipt, root=root, allow_outside=args.allow_receipt_outside_root)
                result["receipt_path"] = str(args.receipt)
            if args.review_markdown:
                print(build_review_markdown(
                    dry_run=True,
                    backend=CODEX_BASE_URL,
                    image_model=args.image_model,
                    host_model=args.host_model,
                    final_prompt=final_prompt,
                    quality=args.quality,
                    aspect=aspect,
                    size=size,
                    background=args.background,
                    action=action,
                    output_format=args.output_format,
                    output_compression=args.output_compression,
                    mask=mask,
                    reference_roles=reference_roles,
                    out=out,
                    refs=all_refs,
                    identity=args.identity,
                    style=args.style,
                    edit_image=args.edit_image,
                    receipt_path=args.receipt,
                ), end="")
            else:
                emit(result, as_json=args.json)
            return 0
        token = read_token(provider=args.auth_provider, token_env=args.token_env, token_file=args.token_file, token_command=args.token_command)
        generated = generate_image(prompt=final_prompt, refs=all_refs, out=out, token=token, host_model=args.host_model, image_model=args.image_model, quality=args.quality, aspect=args.aspect, size=size, background=args.background, action=action, timeout=args.timeout, overwrite=args.overwrite, output_format=args.output_format, output_compression=args.output_compression, mask=mask)
        receipt["status"] = "success"
        receipt["actual_output"] = actual_output_metadata(generated)
        result = {"success": True, "dry_run": False, "image": str(generated), "receipt": receipt}
        if args.receipt:
            write_receipt(args.receipt, receipt, root=root, allow_outside=args.allow_receipt_outside_root)
            result["receipt_path"] = str(args.receipt)
        if args.review_markdown:
            print(build_review_markdown(
                dry_run=False,
                backend=CODEX_BASE_URL,
                image_model=args.image_model,
                host_model=args.host_model,
                final_prompt=final_prompt,
                quality=args.quality,
                aspect=aspect,
                size=size,
                background=args.background,
                action=action,
                output_format=args.output_format,
                output_compression=args.output_compression,
                mask=mask,
                reference_roles=reference_roles,
                out=generated,
                refs=all_refs,
                identity=args.identity,
                style=args.style,
                edit_image=args.edit_image,
                receipt_path=args.receipt,
            ), end="")
        else:
            emit(result, as_json=args.json)
        return 0
    except (PolicyError, AuthError, ClientError, ValueError, OSError) as exc:
        err = sanitize_error_text(exc)
        emit({"success": False, "error": err, "error_class": type(exc).__name__}, as_json=args.json)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
