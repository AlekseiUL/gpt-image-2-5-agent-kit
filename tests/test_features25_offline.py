from __future__ import annotations

import json
from pathlib import Path

from PIL import Image
import pytest

from gpt_image25_agent import cli, library, prompts


def image_file(path, *, alpha=255, size=(12, 8)):
    Image.new('RGBA', size, (20, 40, 60, alpha)).save(path)
    return path


def deny_live(**kwargs):
    pytest.fail('Invalid or planned requests must never read auth or call the backend')


def test_roles_preservation_exact_copy_survive_saved_packs_and_edit(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, 'read_token', deny_live)
    monkeypatch.setattr(cli, 'generate_image', deny_live)
    base = image_file(tmp_path / 'base.png')
    identity = image_file(tmp_path / 'identity.png')
    style = image_file(tmp_path / 'style.png')
    logo = image_file(tmp_path / 'logo.png')
    mask = image_file(tmp_path / 'mask.png', alpha=0)
    library.save_identity(tmp_path, 'person', [identity])
    library.save_style(tmp_path, 'brand', refs=[style])
    code = cli.main(['--edit-image', str(base), '--mask', str(mask), '--identity', 'person', '--style', 'brand',
                     '--ref', str(logo), '--ref-role', 'logo', '--edit', 'Replace title with «ЧАСТЬ 4: Новый путь»',
                     '--preserve', 'person, lighting, framing', '--preset', 'russian-text', '--root', str(tmp_path), '--json'])
    assert code == 0
    result = json.loads(capsys.readouterr().out)
    assert result['receipt']['reference_roles'] == ['edit_base', 'identity', 'style', 'logo']
    assert 'Image 1 [edit_base]' in result['final_prompt'] and 'Image 4 [logo]' in result['final_prompt']
    assert 'ЧАСТЬ 4: Новый путь' in result['final_prompt']
    assert 'person, lighting, framing' in result['final_prompt']
    assert result['receipt']['mask']['path'] == str(mask)
    assert not Path(result['receipt']['output_path']).exists()


@pytest.mark.parametrize('args', [
    ['--preserve', 'lighting'], ['--mask', 'missing.png'], ['--action', 'edit'],
    ['--preset', 'edit'], ['--ref-role', 'identity'],
    ['--preset', 'no-text', '--preset', 'russian-text'],
    ['--timeout', '0'], ['--timeout', 'nan'], ['--timeout', 'inf'],
    ['--output-format', 'jpeg', '--background', 'transparent'],
    ['--output-format', 'png', '--output-compression', '80'],
    ['--output-format', 'webp', '--output-compression', '101'],
])
def test_invalid_feature_combinations_fail_before_auth(args, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, 'read_token', deny_live)
    monkeypatch.setattr(cli, 'generate_image', deny_live)
    assert cli.main(['A sketch', '--root', str(tmp_path), '--live', '--json', *args]) == 2
    assert not json.loads(capsys.readouterr().out)['success']
    assert not (tmp_path / 'generated').exists()


def test_saved_style_cannot_introduce_conflicting_text_presets(tmp_path, monkeypatch, capsys):
    library.save_style(tmp_path, 'words', presets=['russian-text'])
    monkeypatch.setattr(cli, 'read_token', deny_live)
    assert cli.main(['A sketch', '--root', str(tmp_path), '--style', 'words', '--preset', 'no-text', '--live', '--json']) == 2
    assert 'cannot be combined' in capsys.readouterr().out
    with pytest.raises(ValueError, match='cannot be combined'):
        library.save_style(tmp_path, 'bad', presets=['no-text', 'russian-text'])
    assert not library.style_dir(tmp_path, 'bad').exists()


def test_requested_sketch_logo_and_long_copy_are_not_contradicted():
    copy = 'Первый шаг: сделайте систему понятной для всей команды'
    prompt = prompts.build_prompt('A pencil sketch with our requested logo and title: ' + copy, ['portrait', 'russian-text'])
    assert copy in prompt
    for outdated_rule in ['not a sketch', 'avoid extra fingers, broken eyes, duplicated faces, watermarks, logos', 'short readable Cyrillic', 'no random text']:
        assert outdated_rule not in prompt


@pytest.mark.parametrize('fmt,suffix', [('png','.png'), ('jpeg','.jpg'), ('webp','.webp')])
def test_cli_format_receipt_matches_real_saved_output(fmt, suffix, tmp_path, monkeypatch, capsys):
    seen = {}
    monkeypatch.setattr(cli, 'read_token', lambda **kw: 'synthetic-token')
    def generate(**kwargs):
        seen.update(kwargs)
        kwargs['out'].parent.mkdir(parents=True, exist_ok=True)
        Image.new('RGB', (13, 9), (10, 20, 30)).save(kwargs['out'], format=kwargs['output_format'])
        return kwargs['out']
    monkeypatch.setattr(cli, 'generate_image', generate)
    out = tmp_path / 'output' / ('image' + suffix)
    args = ['A sketch', '--root', str(tmp_path), '--out', str(out), '--output-format', fmt, '--live', '--json']
    if fmt != 'png':
        args += ['--output-compression', '85']
    assert cli.main(args) == 0
    receipt = json.loads(capsys.readouterr().out)['receipt']
    assert receipt['output_format'] == seen['output_format'] == fmt
    assert receipt['output_compression'] == seen['output_compression'] == (None if fmt == 'png' else 85)
    assert receipt['actual_output']['width'] == 13 and receipt['actual_output']['height'] == 9
    assert receipt['actual_output']['format'] == fmt
    assert receipt['actual_output']['bytes'] == out.stat().st_size
    assert len(receipt['actual_output']['sha256']) == 64


def test_bad_receipt_path_does_not_spend_quota(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, 'read_token', deny_live)
    monkeypatch.setattr(cli, 'generate_image', deny_live)
    assert cli.main(['A sketch', '--root', str(tmp_path), '--receipt', str(tmp_path / 'bad.txt'), '--live', '--json']) == 2
    assert 'receipt path' in capsys.readouterr().out
    assert not (tmp_path / 'generated').exists()


def test_python_edit_prompt_assigns_base_role_without_explicit_roles():
    text = prompts.build_prompt("Replace the background", edit_mode=True, refs_count=2)
    assert "Image 1 [edit_base]" in text and "Image 2 [general]" in text
    assert "Image 1 [general]" not in text
    with pytest.raises(ValueError, match="base image"):
        prompts.build_prompt("Replace the background", edit_mode=True)
