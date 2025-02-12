
from withrepo import repo


# Basic usage
with repo("microsoft", "multilspy") as r:
   print(r)

    # for dir, file in r.tree:
    #     print(dir, file)

    # print("-" * 100)

    # for dir, file in r.tree:
    #     print(dir, file)

# Usage with a specific commit
with repo("shobrook", "openlimit", commit="62e53478b98c1c3824d70895da9ef9eca87c43d8") as r:
    print(r)

# Usage with a specific branch
with repo("microsoft", "multilspy", branch="codeql") as r:
    print(r)
    # for dir, file in r.tree():
    #     print(dir, file)
