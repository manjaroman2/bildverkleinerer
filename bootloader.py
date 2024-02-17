from sys import platform, argv
from hashlib import sha256
from requests import get
from os import execv
from stat import S_IEXEC
from common import get_datadir
from tarfile import open as tarfile_open
from shutil import rmtree, move

archive_format = "tar.xz"
program = "bildverkleinerer"
datadir = get_datadir(program)
program_archive = (
    datadir / f"{program}_win.{archive_format}"
    if platform == "win32"
    else datadir / f"{program}_lin.{archive_format}"
)
program_exec = (
    datadir / f"{program}.exe" if platform == "win32" else datadir / f"{program}.bin"
)
program_exec_hash = datadir / f"{program_exec.name}.sha256"

for x in get("https://api.github.com/repos/manjaroman2/links/releases/latest").json()[
    "assets"
]:
    if x["name"] == program_archive.name:
        archive_link = x["browser_download_url"]
    elif x["name"] == program_exec_hash.name:
        program_exec_hash_link = x["browser_download_url"]


def dl_exec():
    print("downloading:", archive_link)
    program_archive.write_bytes(get(archive_link).content)
    with tarfile_open(program_archive, "r:xz") as f:
        f.extractall(datadir)
    program_archive.unlink()
    for x in (datadir / "dist" / program).glob("*"):
        move(x, datadir / x.name)
    rmtree((datadir / "dist"))
    program_exec.chmod(program_exec.stat().st_mode | S_IEXEC)


if not program_exec.is_file() or not program_exec.exists():
    dl_exec()
else:
    hashed = sha256()
    hashed.update(program_exec.read_bytes())
    hashed = hashed.hexdigest()
    print("local hash: ", repr(hashed))
    remote_hashed = get(program_exec_hash_link).text
    print("remote hash:", repr(remote_hashed))
    if hashed != remote_hashed:
        rmtree(datadir / "_internal")
        program_exec.unlink()
        dl_exec()
print(program_exec)
execv(program_exec, argv)
