import json, os, tempfile
from pathlib import Path
from .settings import settings

HALT_FILE = Path(settings.STATE_DIR) / "HALTED"
RUNTIME   = Path(settings.STATE_DIR) / "runtime.json"

def atomic_write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent)
    with os.fdopen(fd, "w") as f:
        f.write(data); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)

def is_halted() -> bool:
    return HALT_FILE.exists()

def halt() -> None:
    atomic_write(HALT_FILE, "halted")

def resume() -> None:
    if HALT_FILE.exists():
        HALT_FILE.unlink()

def set_runtime(**kw) -> None:
    cur = {}
    if RUNTIME.exists():
        cur = json.loads(RUNTIME.read_text())
    cur.update(kw)
    atomic_write(RUNTIME, json.dumps(cur, default=str, indent=2))

def get_runtime() -> dict:
    return json.loads(RUNTIME.read_text()) if RUNTIME.exists() else {}