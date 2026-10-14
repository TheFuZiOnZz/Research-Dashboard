
from pathlib import Path
import json
import os
import re

ROOT = Path.cwd()
EXCLUDED = {
    ".git", ".github", ".obsidian", "_site", "_includes",
    "_layouts", "_sass", "_data", "_plugins", "node_modules",
}
EXTENSIONS = {".md", ".markdown"}


def sort_key(value):
    return (value.casefold(), value)


def find_pages():
    result = []

    for current, dirs, files in os.walk(ROOT):
        dirs[:] = sorted(
            (
                d for d in dirs
                if not d.startswith((".", "_"))
                and d not in EXCLUDED
            ),
            key=sort_key,
        )

        folder = Path(current)

        for name in files:
            path = folder / name
            if path.suffix.lower() in EXTENSIONS:
                result.append(path)

    return result


def read_front_matter(path):
    text = path.read_text(encoding="utf-8")
    match = re.match(
        r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)",
        text,
        re.DOTALL,
    )

    if match:
        return match.group(1).splitlines(), text[match.end():]

    return [], text


def write_metadata(path, title, parent, order, has_children=False):
    lines, body = read_front_matter(path)

    # Keep unrelated metadata; replace only generated navigation fields.
    managed = {"title", "parent", "nav_order", "has_children"}
    lines = [
        line for line in lines
        if not re.match(
            r"^(title|parent|nav_order|has_children):(?:\s|$)",
            line,
        )
    ]

    lines.append(f"title: {json.dumps(title, ensure_ascii=False)}")

    if parent:
        lines.append(f"parent: {json.dumps(parent, ensure_ascii=False)}")

    lines.append(f"nav_order: {order}")

    if has_children:
        lines.append("has_children: true")

    path.write_text(
        "---\n" + "\n".join(lines) + "\n---\n\n" + body.lstrip("\n"),
        encoding="utf-8",
    )


pages = find_pages()

# Find every directory containing Markdown pages and all its ancestors.
folders = set()
for page in pages:
    folder = page.parent
    while folder != ROOT:
        folders.add(folder)
        folder = folder.parent

# Reuse existing index pages or create temporary ones in the build checkout.
folder_indexes = {}
for folder in sorted(folders, key=lambda p: (len(p.parts), str(p).casefold())):
    index = next(
        (
            p for p in folder.iterdir()
            if p.is_file()
            and p.name.casefold() in {"index.md", "index.markdown"}
        ),
        None,
    )

    if index is None:
        index = folder / "index.md"
        index.write_text(f"# {folder.name}\n", encoding="utf-8")
        pages.append(index)

    folder_indexes[folder] = index

# Each folder page is the parent for the Markdown pages directly inside it.
for directory in [ROOT] + sorted(
    folders, key=lambda p: (len(p.parts), str(p).casefold())
):
    entries = []

    for page in pages:
        if page.parent != directory:
            continue

        if page in folder_indexes.values():
            continue

        entries.append((page.stem, page, False))

    for child_folder, index in folder_indexes.items():
        if child_folder.parent == directory:
            entries.append((child_folder.name, index, True))

    entries.sort(key=lambda item: sort_key(item[0]))

    for order, (label, page, is_folder) in enumerate(entries, start=1):
        parent = directory.name if directory != ROOT else None

        write_metadata(
            page=page,
            title=label,
            parent=parent,
            order=order,
            has_children=is_folder,
        )

print(f"Prepared sidebar navigation for {len(pages)} Markdown pages.")
