"""Build the handoff ZIP from the current code, docs, examples, and saved runs."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "Option1_Student1_Foundation.zip"
ROOT_FILES = (
    ".gitignore",
    ".python-version",
    "main.py",
    "gui.py",
    "start_gui.bat",
    "README.md",
    "INTEGRATION.md",
    "DEVIN_HANDOFF.md",
    "STUDENT1_WALKTHROUGH.md",
)
FOLDERS = ("cfg_toolkit", "examples", "tests", "tools", "sample_runs")
FILE_TYPES = (".py", ".json", ".txt", ".cfg", ".grammar", ".png")


def collect_files():
    """Keep the package list here so adding a folder or file type is straightforward."""
    files = [ROOT / name for name in ROOT_FILES]
    for directory in FOLDERS:
        for path in (ROOT / directory).rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            if path.suffix in FILE_TYPES:
                files.append(path)
    for path in files:
        if not path.is_file():
            raise RuntimeError("Missing handoff file: {}".format(path))
    return sorted(files)


def main():
    files = collect_files()
    with ZipFile(str(ARCHIVE), "w", compression=ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(str(path), path.relative_to(ROOT).as_posix())
    with ZipFile(str(ARCHIVE)) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("handoff ZIP failed validation")
    print("Built {} ({} files)".format(ARCHIVE.name, len(files)))


if __name__ == "__main__":
    main()
