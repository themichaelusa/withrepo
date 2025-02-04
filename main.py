"""
Attribution:
    create_test_context():
        https://github.com/microsoft/multilspy/blob/main/tests/test_utils.py
    read_file(), download_file(), download_and_extract_archive():
        https://github.com/microsoft/multilspy/blob/main/src/multilspy/multilspy_utils.py

    Original authors:
        Lakshya A Agrawal

    License:
        MIT
"""

# Standard library
import os
import gzip
import pathlib
import contextlib
import shutil
from typing import Iterator, Callable
from uuid import uuid4
from dataclasses import dataclass

# Third party
import requests

# Constants
HOME_DIR = os.path.expanduser("~")
WITH_REPO_DIR = str(pathlib.Path(HOME_DIR, ".withrepo"))


def read_file(file_path: str) -> str:
    """
    Reads the file at the given path and returns the contents as a string.
    """
    encodings = ["utf-8-sig", "utf-16"]
    try:
        for encoding in encodings:
            try:
                with open(file_path, "r", encoding=encoding) as inp_file:
                    return inp_file.read()
            except UnicodeError:
                continue
    except Exception:
        raise Exception("File read failed.") from None
    raise Exception(f"File read '{file_path}' failed: Unsupported encoding.") from None


def download_file(url: str, target_path: str) -> None:
    """
    Downloads the file from the given URL to the given {target_path}
    """
    try:
        response = requests.get(url, stream=True, timeout=60)
        if response.status_code != 200:
            raise Exception(
                f"Error downloading file '{url}': {response.status_code} {response.text}"
            )
        with open(target_path, "wb") as f:
            shutil.copyfileobj(response.raw, f)
    except Exception:
        raise Exception("Error downoading file.") from None


def download_and_extract_archive(url: str, target_path: str, archive_type: str) -> None:
    """
    Downloads the archive from the given URL having format {archive_type} and extracts it to the given {target_path}
    """
    try:
        tmp_files = []
        # tmp_file_name = str(
        #     pathlib.PurePath(os.path.expanduser("~"), "scope_tmp", uuid4().hex)
        # )
        tmp_file_name = str(
            pathlib.PurePath(HOME_DIR, "withrepo_tmp", uuid4().hex)
        )
        tmp_files.append(tmp_file_name)
        os.makedirs(os.path.dirname(tmp_file_name), exist_ok=True)
        download_file(url, tmp_file_name)
        if archive_type in ["zip", "tar", "gztar", "bztar", "xztar"]:
            assert os.path.isdir(target_path)
            shutil.unpack_archive(tmp_file_name, target_path, archive_type)
        elif archive_type == "zip.gz":
            assert os.path.isdir(target_path)
            tmp_file_name_ungzipped = tmp_file_name + ".zip"
            tmp_files.append(tmp_file_name_ungzipped)
            with (
                gzip.open(tmp_file_name, "rb") as f_in,
                open(tmp_file_name_ungzipped, "wb") as f_out,
            ):
                shutil.copyfileobj(f_in, f_out)
            shutil.unpack_archive(tmp_file_name_ungzipped, target_path, "zip")
        elif archive_type == "gz":
            with (
                gzip.open(tmp_file_name, "rb") as f_in,
                open(target_path, "wb") as f_out,
            ):
                shutil.copyfileobj(f_in, f_out)
        else:
            raise Exception(f"Unknown archive type '{archive_type}' for extraction")
    except Exception as exc:
        raise Exception(
            f"Error extracting archive '{tmp_file_name}' obtained from '{url}': {exc}"
        ) from exc
    finally:
        for tmp_file_name in tmp_files:
            if os.path.exists(tmp_file_name):
                pathlib.Path.unlink(pathlib.Path(tmp_file_name))


@dataclass
class WithRepoContext:
    """Stores the context for a withrepo test."""
    root: str
    tree: Iterator[tuple[str, str]]

# @contextlib.contextmanager
# def repo_context(params: dict) -> Iterator[ScopeContext]:
#     """
#     Creates a test context for the given parameters.
#     """

#     user_home_dir = os.path.expanduser("~")
#     scope_home_directory = str(pathlib.Path(user_home_dir, ".scope"))
#     temp_extract_directory = str(pathlib.Path(scope_home_directory, uuid4().hex))
#     try:
#         os.makedirs(temp_extract_directory, exist_ok=False)
#         assert params["repo_url"].endswith("/")
#         repo_zip_url = params["repo_url"] + f"archive/{params['repo_commit']}.zip"
#         download_and_extract_archive(repo_zip_url, temp_extract_directory, "zip")
#         dir_contents = os.listdir(temp_extract_directory)
#         assert len(dir_contents) == 1
#         source_directory_path = str(
#             pathlib.Path(temp_extract_directory, dir_contents[0])
#         )
#         yield ScopeContext(source_directory_path)
#     finally:
#         if os.path.exists(temp_extract_directory):
#             shutil.rmtree(temp_extract_directory)


def cleanup(directory: str) -> None:
    if os.path.exists(directory):
        shutil.rmtree(directory)

def tree(directory: str) -> Iterator[tuple[str, str]]:
    for root, dirs, files in os.walk(directory, topdown=True):
        # Yield full paths relative to the input directory
        for file in files:
            yield (root, os.path.relpath(os.path.join(root, file), directory))

def repo_to_dir(url : str) -> str:
    temp_extract_directory = str(pathlib.Path(WITH_REPO_DIR, uuid4().hex))
    try:
        os.makedirs(temp_extract_directory, exist_ok=False)
        # assert url.endswith("/")
        download_and_extract_archive(url, temp_extract_directory, "zip")
        dir_contents = os.listdir(temp_extract_directory)
        assert len(dir_contents) == 1
        source_directory_path = str(
            pathlib.Path(temp_extract_directory, dir_contents[0])
        )
        return source_directory_path
    except Exception as e:
        raise Exception(f"Error extracting archive '{url}': {e}") from e

@contextlib.contextmanager
def repo_from_url(url: str = "", commit: str = "") -> Iterator[WithRepoContext]:
    if not commit:
        repo_zip_url = f"{url}/archive/HEAD.zip"
    else:
        repo_zip_url = url + f"archive/{commit}.zip"
    try:
        source_directory_path = repo_to_dir(repo_zip_url)
        tree_list = list(tree(source_directory_path))
        yield WithRepoContext(source_directory_path, tree_list)
    finally:
        cleanup(source_directory_path)

@contextlib.contextmanager
def repo(user: str, repo: str, commit: str = "") -> Iterator[WithRepoContext]:
    if not commit:
        repo_zip_url = f"https://github.com/{user}/{repo}/archive/HEAD.zip"
    else:
        repo_zip_url = f"https://github.com/{user}/{repo}/archive/{commit}.zip"
    try:
        source_directory_path = repo_to_dir(repo_zip_url)
        tree_list = list(tree(source_directory_path))
        yield WithRepoContext(source_directory_path, tree_list)
    finally:
        cleanup(source_directory_path)
