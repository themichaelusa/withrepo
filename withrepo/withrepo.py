# Standard library
import os
import shutil
import contextlib
from typing import Iterator, Tuple, List, Union

# Local
from withrepo.utils import copy_and_split_root_by_language_group, RepoArguments
from withrepo.download import parse_repo_arguments_into_download_url, download_and_extract_archive


class RepoContext:
    def __init__(self, path: str, url: str, args: RepoArguments, lang_groups: List[Tuple[str, str]]):
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
    
    def tree(self, multilang: bool = False) -> Union[Iterator[Tuple[str, str]], Iterator[Tuple[str, str, str]]]:
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

@contextlib.contextmanager
def repo(user: str, repo: str, commit: str = "", branch: str = "", url: str = "") -> Iterator[RepoContext]:
    """
    TODO
    """
    args = RepoArguments(user=user, repo=repo, commit=commit, branch=branch, url=url)
    repo_zip_url = parse_repo_arguments_into_download_url(args)
    source_directory_path = download_and_extract_archive(repo_zip_url)

    lang_groups = copy_and_split_root_by_language_group(source_directory_path)
    yield RepoContext(
        source_directory_path, repo_zip_url, args, lang_groups
    )

    # cleanup the source directory and the group directories
    group_dirs = [dir for dir, _ in lang_groups]
    if os.path.exists(source_directory_path):
        shutil.rmtree(source_directory_path)
    for group_dir in group_dirs:
        if os.path.exists(group_dir):
            shutil.rmtree(group_dir)
