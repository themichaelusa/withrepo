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

# Local
from withrepo.utils import RepoArguments, RepoProvider
# from withrepo.utils import copy_and_split_root_by_language_group

# Third party
import httpx

# constants
PROVIDER_TO_URL_MAP = {
    RepoProvider.GITHUB: "https://github.com",
    RepoProvider.GITLAB: "https://gitlab.com",
    RepoProvider.BITBUCKET: "https://bitbucket.org",
}

def download_and_extract_archive(url: str, archive_type: str = "zip") -> str:
    """
    Downloads the archive from the given URL having format {archive_type} and extracts it to the given {target_path}
    """
    if not url:
        raise Exception(f"withrepo.download_file(): URL is empty")
    try:
        extract_directory = tempfile.mkdtemp(prefix="scope_")
        fd, tmp_file_name = tempfile.mkstemp(prefix="scope_")

        # Download the archive
        client = httpx.Client(follow_redirects=True)
        with client.stream("GET", url, timeout=60.0) as response:
            if response.status_code != 200:
                error_text = response.read().decode()  # Read the response content first
                raise httpx.RequestError(
                    f"Error downloading file '{url}': {response.status_code} {error_text}"
                )
            with os.fdopen(fd, "wb") as f:
                for chunk in response.iter_raw():
                    f.write(chunk)

        # Extract the archive
        if archive_type in ["zip", "tar", "gztar", "bztar", "xztar"]:
            shutil.unpack_archive(tmp_file_name, extract_directory, archive_type)
            os.remove(tmp_file_name)
        else:
            raise Exception(f"download_and_extract_archive(): Unsupported archive type '{archive_type}'")
        return extract_directory
    except Exception as exc:
        raise Exception(
            f"Error extracting archive '{tmp_file_name}' obtained from '{url}': {exc}"
        ) from exc

def parse_repo_arguments_into_download_url(args: RepoArguments) -> str:
    if args.invalid():
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