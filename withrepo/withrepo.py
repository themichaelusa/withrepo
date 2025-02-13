# Standard library
import os
import shutil
import contextlib
from typing import Iterator, Tuple, List, Union

# Local
from withrepo.utils import RepoArguments, LanguageGroup, RepoProvider
from withrepo.download import (
    parse_repo_arguments_into_download_url,
    download_and_extract_archive,
)
from withrepo.utils import get_language_from_ext


class RepoFile:
    def __init__(self, abs_path: str, relative_path: str):
        self.abs_path = abs_path
        self.relative_path = relative_path
        self._contents = None
        _, language, is_code = get_language_from_ext(abs_path)
        self.language = language
        self.is_code = is_code

    def contents(self) -> str:
        if self._contents is None:
            with open(self.abs_path, "r") as f:
                self._contents = f.read()
        return self._contents

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
        self.path = path
        self.url = url
        self.user = args.user
        self.repo = args.repo
        self.commit = args.commit
        self.branch = args.branch
        self.repo_url = args.url
        self.provider = args.provider
        self.lang_groups = lang_groups
        self.languages = list({lang_group.language for lang_group in lang_groups})

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
        self, multilang: bool = False
    ) -> Union[Iterator[Tuple[str, str]], Iterator[Tuple[str, str, str]]]:
        """
        Returns a tree of the repository.
        If multilang is True, the tree will be split by language group.
        """
        if not multilang:
            for root, _, files in os.walk(self.path, topdown=True):
                # Yield full paths relative to the input directory
                for file in files:
                    relpath = os.path.relpath(os.path.join(root, file), self.path)
                    abspath = os.path.abspath(os.path.join(root, file))
                    yield RepoFile(abspath, relpath)
        else:
            for lang_group in self.lang_groups:
                for root, _, files in os.walk(lang_group.path, topdown=True):
                    # Yield full paths relative to the input directory with the language
                    for file in files:
                        relpath = os.path.relpath(
                            os.path.join(root, file), lang_group.path
                        )
                        abspath = os.path.abspath(os.path.join(root, file))
                        yield RepoFile(abspath, relpath)


@contextlib.contextmanager
def repo(
    user: str, repo: str, commit: str = "", branch: str = "", url: str = "", provider: RepoProvider = RepoProvider.GITHUB
) -> Iterator[RepoContext]:
    """
    TODO
    """
    args = RepoArguments(user=user, repo=repo, commit=commit, branch=branch, url=url, provider=provider)
    repo_zip_url = parse_repo_arguments_into_download_url(args)
    source_directory_path, lang_groups = download_and_extract_archive(repo_zip_url)
    yield RepoContext(source_directory_path, repo_zip_url, args, lang_groups)

    # cleanup the source directory and the group directories
    if os.path.exists(source_directory_path):
        shutil.rmtree(source_directory_path)
    for lang_group in lang_groups:
        if os.path.exists(lang_group.path):
            shutil.rmtree(lang_group.path)
