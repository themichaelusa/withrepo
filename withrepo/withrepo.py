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
from enum import Enum
from typing import Iterator, Callable, Optional, Tuple, Union
from uuid import uuid4
from dataclasses import dataclass

# Local
from withrepo.utils import copy_and_split_root_by_language_group

# Third party
import requests

# Constants
HOME_DIR = os.path.expanduser("~")
WITH_REPO_DIR = str(pathlib.Path(HOME_DIR, ".withrepo"))

# Dtos
class RepoProvider(Enum):
    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"

PROVIDER_TO_URL_MAP = {
    RepoProvider.GITHUB: "https://github.com",
    RepoProvider.GITLAB: "https://gitlab.com",
    RepoProvider.BITBUCKET: "https://bitbucket.org",
}

@dataclass
class RepoArguments:
    user: str = ""
    repo: str = ""
    commit: str = ""
    url: str = ""
    branch: str = ""
    provider: RepoProvider = RepoProvider.GITHUB

    def all_empty(self) -> bool:
        return not any([self.user, self.repo, self.commit, self.url, self.branch])


class RepoContext:
    def __init__(self, path: str, url: str, args: RepoArguments, lang_groups: list[tuple[str, str]]):
        """Stores the context for a withrepo test."""
        self.path = path
        self.url = url
        self.user = args.user
        self.repo = args.repo
        self.commit = args.commit
        self.branch = args.branch
        self.repo_url = args.url
        self.provider = args.provider
        self.lang_groups = lang_groups
        self.languages = list({language for _, language in lang_groups})

    def __str__(self):
        return f"""RepoContext(
            url={self.url},
            user={self.user},
            repo={self.repo},
            commit={self.commit},
            branch={self.branch},
            provider={self.provider},
            languages={self.languages},
            path={self.path}
        )"""
    
    def tree(self, multilang: bool = False) -> Union[Iterator[tuple[str, str]], Iterator[tuple[str, str, str]]]:
        """
        Returns a tree of the repository.
        If multilang is True, the tree will be split by language group.
        """
        if not multilang:
            for root, dirs, files in os.walk(self.path, topdown=True):
                # Yield full paths relative to the input directory
                for file in files:
                    yield (root, os.path.relpath(os.path.join(root, file), self.path))
        else:
            for root_dir, language in self.lang_groups:
                for root, dirs, files in os.walk(root_dir, topdown=True):
                    # Yield full paths relative to the input directory with the language
                    for file in files:
                        yield (root, os.path.relpath(os.path.join(root, file), root_dir), language)

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


def cleanup(directory: str, root_dirs: list[str]) -> None:
    if os.path.exists(directory):
        shutil.rmtree(directory)
    for root_dir in root_dirs:
        if os.path.exists(root_dir):
            shutil.rmtree(root_dir)

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

def parse_repo_arguments_to_download_url(args: RepoArguments) -> str:
    if args.all_empty():
        raise Exception("Cannot parse repo() without arguments")
    provider_url = PROVIDER_TO_URL_MAP[args.provider]
    # at minimum, either url or (user, repo) must be provided
    if args.url:
        if not args.commit:
            return f"{args.url}/archive/HEAD.zip"
        else:
            return f"{args.url}/archive/{args.commit}.zip"
    elif args.user and args.repo:
        if args.branch:
            return f"{provider_url}/{args.user}/{args.repo}/archive/{args.branch}.zip"
        elif args.commit:
            return f"{provider_url}/{args.user}/{args.repo}/archive/{args.commit}.zip"
        else:
            return f"{provider_url}/{args.user}/{args.repo}/archive/HEAD.zip"
    else:
        raise Exception("Cannot parse repo() with given arguments")

@contextlib.contextmanager
def repo(user: str, repo: str, commit: str = "", branch: str = "", url: str = "") -> Iterator[RepoContext]:
    """
    TODO
    """
    args = RepoArguments(user=user, repo=repo, commit=commit, branch=branch, url=url)
    repo_zip_url = parse_repo_arguments_to_download_url(args)
    source_directory_path = repo_to_dir(repo_zip_url)
    lang_groups = copy_and_split_root_by_language_group(source_directory_path)
    yield RepoContext(
        source_directory_path, repo_zip_url, args, lang_groups
    )
    group_dirs = [dir for dir, _ in lang_groups]
    cleanup(source_directory_path, group_dirs)
