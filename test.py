
from withrepo import repo

with repo("microsoft", "multilspy") as r:
    print(r.root)
    for dir, file in r.tree:
        print(dir, file)


    print("-" * 100)

    for dir, file in r.tree:
        print(dir, file)