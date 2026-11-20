"""Collect dependency notices for the offline Windows distribution."""
from importlib import metadata
from pathlib import Path
import shutil
import sys

target = Path("dist/EthoState/licenses")
target.mkdir(parents=True, exist_ok=True)
shutil.copy2("LICENSE", target/"EthoState.txt")
python_license = Path(sys.base_prefix)/"LICENSE.txt"
if python_license.exists():
    shutil.copy2(python_license, target/"Python.txt")
for dist in metadata.distributions():
    for item in dist.files or []:
        if ".." in item.parts:
            continue
        if item.name.lower().startswith(("license", "copying", "notice", "copyright")):
            src = Path(dist.locate_file(item))
            if src.is_file():
                dest = target / dist.metadata["Name"] / item
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)

