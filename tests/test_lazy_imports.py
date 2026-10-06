import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _run(code: str) -> subprocess.CompletedProcess:
    """Run `code` in a fresh interpreter, with this checkout importable"""
    return subprocess.run(
        [sys.executable, '-c', code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_plain_import_loads_none_of_the_lazy_modules():
    result = _run(
        'import sys, juturna\n'
        'loaded = [m for m in ("juturna.nodes", "juturna.hub",'
        ' "juturna.remotizer", "grpc") if m in sys.modules]\n'
        'print(",".join(loaded))'
    )

    assert result.returncode == 0, f'import failed: {result.stderr}'
    assert result.stdout.strip() == '', (
        f'plain import loaded {result.stdout.strip()}'
    )


@pytest.mark.parametrize('name', ['nodes', 'hub'])
def test_attribute_access_imports_the_module(name):
    result = _run(
        'import sys, juturna\n'
        f'module = juturna.{name}\n'
        f'print(module is sys.modules["juturna.{name}"])\n'
        f'print(juturna.{name} is module)'
    )

    assert result.returncode == 0, f'access failed: {result.stderr}'
    assert result.stdout.split() == ['True', 'True'], (
        f'unexpected output: {result.stdout}'
    )


def test_remotizer_is_imported_on_access():
    pytest.importorskip('grpc')

    result = _run(
        'import sys, juturna\n'
        'juturna.remotizer\n'
        'print("juturna.remotizer" in sys.modules)'
    )

    assert result.returncode == 0, f'access failed: {result.stderr}'
    assert result.stdout.strip() == 'True', (
        f'remotizer not imported: {result.stdout}'
    )


def test_unknown_attribute_raises_attribute_error():
    result = _run(
        'import juturna\n'
        'try:\n'
        '    juturna.does_not_exist\n'
        'except AttributeError as e:\n'
        '    print(e)'
    )

    assert result.returncode == 0, f'unexpected failure: {result.stderr}'
    assert 'does_not_exist' in result.stdout, (
        f'unexpected message: {result.stdout}'
    )
