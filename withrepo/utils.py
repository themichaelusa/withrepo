# Standard library
import os
from enum import Enum
from dataclasses import dataclass
from typing import Tuple, List
import shutil
import tempfile

# Local
from withrepo.resources.languages import EXT_TO_LANGUAGE_DATA
from withrepo.constants import LANGUAGE_TO_LSP_LANGUAGE_MAP


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
    provider: RepoProvider = None
    root_dir: str = ""
    root_path: str = None

    def invalid(self) -> bool:
        return not any(
            [self.user, self.repo, self.commit, self.url, self.branch, self.root_path]
        )


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


def copy_and_split_root_by_language_group(abs_root_path) -> List[LanguageGroup]:
    abs_paths, _ = get_all_paths_from_root_relative(abs_root_path)
    languages = set()

    for p in abs_paths:
        lsp_language, language, is_code = get_language_from_ext(p)
        if is_code:
            languages.add(lsp_language)
    languages = [lang for lang in languages if lang]

    copy_paths = []
    # copy the root directory into a temporary directory per language
    for _ in range(len(languages)):
        tmp_parent_dir = tempfile.mkdtemp(prefix="scope_")
        print(f"Copying {abs_root_path} to {tmp_parent_dir}")
        shutil.copytree(abs_root_path, tmp_parent_dir, dirs_exist_ok=True)
        copy_paths.append(tmp_parent_dir)

    for copy_path, language in zip(copy_paths, languages):
        for root, dirs, files in os.walk(copy_path):
            for file in files:
                if keep_file_for_language(root, file, language):
                    continue
                else:
                    # print(f"removing file: {os.path.join(root, file)}")
                    os.remove(os.path.join(root, file))

    # remove copy_paths that only have directories and no files
    nonempty_copy_paths = []
    for copy_path, language in zip(copy_paths, languages):
        files_set = set()
        for root, dirs, files in os.walk(copy_path):
            for file in files:
                files_set.add(file)
        if not files_set:
            # print(f"copy_path: {copy_path} is empty")
            shutil.rmtree(copy_path)
            continue

        # TODO: figure out if this screws up with path removal on cleanup
        child_dirs = os.listdir(copy_path)
        if len(child_dirs) == 1:
            copy_path = os.path.join(copy_path, child_dirs[0])
        nonempty_copy_paths.append(LanguageGroup(language, copy_path))

    return nonempty_copy_paths
