import os

EXCLUDE = {
    "venv",
    ".venv",
    "env",
    "__pycache__",
    ".git"
}

def print_tree(path, prefix=""):
    items = sorted(os.listdir(path))

    items = [i for i in items if i not in EXCLUDE]

    for i, item in enumerate(items):
        full_path = os.path.join(path, item)

        connector = "└── " if i == len(items)-1 else "├── "

        print(prefix + connector + item)

        if os.path.isdir(full_path):
            extension = "    " if i == len(items)-1 else "│   "
            print_tree(full_path, prefix + extension)

print_tree(".")