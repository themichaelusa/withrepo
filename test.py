
from main import repo

with repo("microsoft", "multilspy") as r:
    print(r.root)
