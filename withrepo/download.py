"""
Attribution:
    download_and_extract_archive():
        https://github.com/microsoft/multilspy/blob/main/src/multilspy/multilspy_utils.py

    Original authors:
        Lakshya A Agrawal

    License:
        MIT
"""

# Standard library
import os
import shutil
import tempfile
from typing import List, Tuple

# Local
from withrepo.utils import (
    RepoArguments,
    RepoProvider,
    LanguageGroup,
    copy_and_split_root_by_language_group,
)

# Third party
import httpx

# CONSTANTS
CHUNK_SIZE = 2 * 1024 * 1024

PROVIDER_TO_URL_MAP = {
    RepoProvider.GITHUB: "https://github.com",
    RepoProvider.GITLAB: "https://gitlab.com",
    RepoProvider.BITBUCKET: "https://bitbucket.org",
}


def download_and_extract_archive(url: str) -> Tuple[str, List[LanguageGroup]]:
    """
    Downloads the archive from the given URL having format {archive_type} and extracts it to the given {target_path}
    """
    if not url:
        raise Exception("withrepo.download_file(): URL is empty")

    archive_type = url.split(".")[-1]
    extract_directory = tempfile.mkdtemp(prefix="scope_")
    fd, tmp_file_name = tempfile.mkstemp(prefix="scope_")
    lang_groups = []

    try:
        # Download the archive
        client = httpx.Client(follow_redirects=True, http2=True)
        with client.stream("GET", url, timeout=60.0) as response:
            if response.status_code != 200:
                error_text = response.read().decode()
                raise httpx.RequestError(
                    f"Error downloading file '{url}': {response.status_code} {error_text}"
                )
            with os.fdopen(fd, "wb") as f:
                for chunk in response.iter_raw(chunk_size=CHUNK_SIZE):
                    f.write(chunk)

        # Extract the archive
        if archive_type in {"zip", "tar", "gztar", "bztar", "xztar"}:
            shutil.unpack_archive(tmp_file_name, extract_directory, archive_type)
        else:
            raise Exception(
                f"download_and_extract_archive(): Unsupported archive type '{archive_type}'"
            )

        # Split the archive into language groups
        lang_groups.extend(copy_and_split_root_by_language_group(extract_directory))

        # TODO: figure out if this screws up with path removal on cleanup
        child_dirs = os.listdir(extract_directory)
        if len(child_dirs) == 1:
            extract_directory = os.path.join(extract_directory, child_dirs[0])
    except Exception as exc:
        raise Exception(
            f"Error extracting archive '{tmp_file_name}' obtained from '{url}': {exc}"
        ) from exc
    finally:
        if os.path.exists(tmp_file_name):
            os.remove(tmp_file_name)
        # if os.path.exists(extract_directory):
        #     shutil.rmtree(extract_directory)

    return extract_directory, lang_groups


### TODO
# GITLAB default clone
# https://gitlab.com/NTPsec/ntpsec/-/archive/master/ntpsec-master.zip

# GITLAB commit clone
# https://gitlab.com/NTPsec/ntpsec/-/archive/f282438ee3875330d82877975adbf7a096b06f73/ntpsec-f282438ee3875330d82877975adbf7a096b06f73.zip

# GITLAB branch clone
# https://gitlab.com/NTPsec/ntpsec/-/archive/mr_1415/ntpsec-mr_1415.zip


def parse_repo_arguments_into_download_url(args: RepoArguments) -> str:
    if args.invalid():
        raise Exception("Cannot parse repo() without arguments")
    provider_url = PROVIDER_TO_URL_MAP[args.provider]
    # at minimum, either url or (user, repo) must be provided
    if args.url:
        if not args.commit:
            # if args.provider == RepoProvider.GITLAB:
            #     return f"{provider_url}/{args.user}/{args.repo}/-/raw/HEAD/archive.zip"
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
