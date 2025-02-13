# Standard library
import os
from enum import Enum
from dataclasses import dataclass
from typing import Tuple

# Local
from withrepo.resources import EXT_TO_LANGUAGE_DATA
from withrepo.constants import (
    LANGUAGE_TO_LSP_LANGUAGE_MAP,
)


# General utils
def flatten(xss):
    return [x for xs in xss for x in xs]


def is_file_empty(path):
    return os.stat(path).st_size == 0


# Dtos for downloads
class RepoProvider(Enum):
    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"


@dataclass
class RepoArguments:
    user: str = ""
    repo: str = ""
    commit: str = ""
    url: str = ""
    branch: str = ""
    provider: RepoProvider = RepoProvider.GITHUB

    def invalid(self) -> bool:
        return not any([self.user, self.repo, self.commit, self.url, self.branch])


@dataclass
class LanguageGroup:
    language: str
    path: str
    # files: List[str]


# Codebase segmentation utils
def get_all_paths_from_root_relative(root_path):
    abs_paths, rel_paths = [], []
    for root, dirs, files in os.walk(root_path):
        for file in files:
            abs_path = os.path.join(root, file)
            relpath = os.path.relpath(abs_path, root_path)
            abs_paths.append(abs_path)
            rel_paths.append(relpath)
    return abs_paths, rel_paths


def get_language_from_ext(path) -> Tuple[str, str, bool]:
    root, ext = os.path.splitext(path)
    language_info = EXT_TO_LANGUAGE_DATA.get(ext, {})
    is_code = language_info.get("is_code", False)
    language = language_info.get("language_mode", None)
    lsp_language = LANGUAGE_TO_LSP_LANGUAGE_MAP.get(language, None)
    return lsp_language, language, is_code


def keep_file_for_language(root, file, language):
    file_language, _, is_code = get_language_from_ext(file)
    if file_language == language and is_code:
        return True
    return False
    # match language:
    #     case "javascript" | "typescript":
    #         if file.endswith("config.json") or file.endswith("package.json"):
    #             print("CallGraphBuilder :: keeping file: ", os.path.join(root, file))
    #             return True
    #     case _:
    #         return False
