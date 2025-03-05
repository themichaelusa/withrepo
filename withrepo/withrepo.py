# Standard library
import os
import shutil
import contextlib
from typing import Iterator, List, Union, Dict
from collections import defaultdict

# Local
from withrepo.utils import RepoArguments, LanguageGroup, RepoProvider
from withrepo.download import (
    parse_repo_arguments_into_download_url,
    download_and_extract_archive,
)
from withrepo.utils import get_language_from_ext


class RepoFile:
    def __init__(self, abs_path: str, relative_path: str, preload: bool = False):
        self.abs_path: str = abs_path
        self.relative_path: str = relative_path
        self._contents: str = None
        if preload:
            self.contents()
        _, language, is_code = get_language_from_ext(abs_path)
        self.language: str = language
        self.is_code: bool = is_code

    def contents(self) -> str:
        try:
            if self._contents is None:
                with open(self.abs_path, "r") as f:
                    self._contents = f.read()
            return self._contents
        except Exception:
            print(f"RepoFile::contents() Error reading file {self.abs_path}")
            return ""

    def __len__(self) -> int:
        return len(self.contents().split("\n"))

    def __str__(self) -> str:
        return f"""RepoFile(
            relative_path={self.relative_path},
            language={self.language},
            is_code={self.is_code},
            num_lines={len(self)}
        )"""

    def __iter__(self) -> Iterator[str]:
        return iter(self.contents().split("\n"))


class RepoContext:
    def __init__(
        self, path: str, url: str, args: RepoArguments, lang_groups: List[LanguageGroup]
    ):
        """Stores the context for a withrepo test."""
        self.path: str = path
        self.url: str = url
        self.user: str = args.user
        self.repo: str = args.repo
        self.commit: str = args.commit
        self.branch: str = args.branch
        self.repo_url: str = args.url
        self.provider: RepoProvider = args.provider
        self.lang_groups: List[LanguageGroup] = lang_groups
        self.languages: List[str] = list(
            {lang_group.language for lang_group in lang_groups}
        )

        self.files: List[RepoFile] = []
        self.lang_trees: Dict[str, List[RepoFile]] = {}

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

    def tree(
        self, multilang: bool = False, store: bool = False
    ) -> Union[List[RepoFile], Dict[str, List[RepoFile]]]:
        """
        Returns a tree of the repository.
        If multilang is False, returns a list of RepoFiles.
        If multilang is True, returns a dict mapping languages to lists of RepoFiles.
        """
        if not multilang:
            files = []
            for root, _, files_list in os.walk(self.path, topdown=True):
                # Collect full paths relative to the input directory
                for file in files_list:
                    relpath = os.path.relpath(os.path.join(root, file), self.path)
                    abspath = os.path.abspath(os.path.join(root, file))
                    files.append(RepoFile(abspath, relpath, preload=store))
            if store:
                self.files = files
            return files
        else:
            lang_trees = defaultdict(list)
            for lang_group in self.lang_groups:
                lang_tree = list(os.walk(lang_group.path, topdown=True))
                tree_files_and_root = [(root, files) for root, _, files in lang_tree]
                for root, files in tree_files_and_root:
                    for file in files:
                        relpath = os.path.relpath(
                            os.path.join(root, file), lang_group.path
                        )
                        abspath = os.path.abspath(os.path.join(root, file))
                        lang_trees[lang_group.language].append(
                            RepoFile(abspath, relpath, preload=store)
                        )
            if store:
                self.lang_trees = lang_trees
            return lang_trees

    def cleanup(self, log: bool = False):
        if log:
            print(f"RepoContext::cleanup() Cleaning up {self.path}")
            print(f"RepoContext::cleanup() Cleaning up {self.lang_groups}")
        # cleanup the source directory and the group directories
        if os.path.exists(self.path):
            shutil.rmtree(self.path)
        for lang_group in self.lang_groups:
            if os.path.exists(lang_group.path):
                shutil.rmtree(lang_group.path)


@contextlib.contextmanager
def repo(
    user: str,
    repo: str,
    commit: str = "",
    branch: str = "",
    url: str = "",
    provider: RepoProvider = RepoProvider.GITHUB,
    cleanup_callback: bool = False,
    log: bool = False,
) -> Iterator[RepoContext]:
    """
    TODO
    """
    args = RepoArguments(
        user=user, repo=repo, commit=commit, branch=branch, url=url, provider=provider
    )
    repo_zip_url = parse_repo_arguments_into_download_url(args)
    source_directory_path, lang_groups = download_and_extract_archive(repo_zip_url)
    repo_ctx = RepoContext(source_directory_path, repo_zip_url, args, lang_groups)
    yield repo_ctx

    if not cleanup_callback:
        repo_ctx.cleanup(log=log)
