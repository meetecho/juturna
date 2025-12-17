import argparse
import pathlib


def _is_file_ok(file_path: str) -> str:
    if not pathlib.Path(file_path).exists():
        raise argparse.ArgumentTypeError(f'{file_path} does not exists')

    if not pathlib.Path(file_path).is_file():
        raise argparse.ArgumentTypeError(f'{file_path} is not a file')

    return file_path


def _is_dir_ok(dir_path: str) -> str:
    if not pathlib.Path(dir_path).exists():
        raise argparse.ArgumentTypeError(f'{dir_path} does not exists')

    if not pathlib.Path(dir_path).is_dir():
        raise argparse.ArgumentTypeError(f'{dir_path} is not a file')

    return dir_path
