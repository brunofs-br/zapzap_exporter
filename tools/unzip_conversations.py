# coding: utf-8
"""
unzip_conversations.py DIR
No diretório DIR, descompacta cada as conversas .zip para
"""
import re
import sys
import os
from pathlib import Path
import zipfile


def unzip_all(directory):
    for fullpathzip in directory.glob("*.zip"):
        fname = fullpathzip.stem.rstrip(" .")
        newdir = fullpathzip.parent / fname
        if not newdir.exists():
            try:
                zipf = zipfile.ZipFile(fullpathzip)
                newdir.mkdir(parents=True)
                zipf.extractall(path=newdir)
                zipf.close()
                fullpathzip.unlink()
            except zipfile.BadZipfile:
                print("BAD ZIP: " + os.fspath(fullpathzip))
                fullpathzip.unlink()


def remove_duplicate(directory):
    """Remove os arquivos com (1), (2), etc..."""
    files = [f for f in directory.iterdir() if f.is_file() and re.match(r'.+\([0-9]\).*', os.fspath(f))]

    for f in files:
        print(f"Removendo {f}")
        f.unlink()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Utilização: unzip_conversations.py "pasta"')
        exit(1)
    path = Path(sys.argv[-1])
    print(path)
    remove_duplicate(path)
    unzip_all(path)
