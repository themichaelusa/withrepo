# import pytest

from withrepo import repo


def test_basic():
    """
    Test the basic functionality of withrepo
    """
    commit = "ae77eb7d41f537ce1e68f78031f4b7197ddf29f4"
    with repo("shobrook", "openlimit", commit) as r:
        for t in r.tree(multilang=True):
            print(t)
