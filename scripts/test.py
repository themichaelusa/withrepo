from withrepo import repo, File

# Basic usage
# with repo("microsoft", "multilspy") as r:
#    print(r)

# Usage with a specific commit
# with repo("shobrook", "openlimit", commit="62e53478b98c1c3824d70895da9ef9eca87c43d8") as r:
#     print(r)
#     print(os.listdir(r.path))

# Usage with a specific branch
with repo("microsoft", "multilspy", branch="codeql") as r:
    # for lg in r.lang_groups:
    #     print(lg)
    for t in r.tree(multilang=True):
        print(t)

# Usage with gitlab
# with repo("NTPsec", "ntpsec", provider=RepoProvider.GITLAB) as r:
#     # for lg in r.lang_groups:
#     #     print(lg)
#     for t in r.tree(multilang=True):
#         print(t)
