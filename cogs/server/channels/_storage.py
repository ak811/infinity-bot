# cogs/server/channels/_storage.py
import json, asyncio
from pathlib import Path
from .archive_config import DATA_DIR

ROOT = Path(DATA_DIR) if DATA_DIR else Path(__file__).parent
ROOT.mkdir(parents=True, exist_ok=True)

ACTIVITY_PATH = ROOT / "_data_archiver_activity.json"
POSITIONS_PATH = ROOT / "_data_archiver_positions.json"

async def _io(func, *a, **k): return await asyncio.to_thread(func, *a, **k)

def _load(path: Path) -> dict:
    if not path.exists(): return {}
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return {}

def _save(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

async def load_activity() -> dict: return await _io(_load, ACTIVITY_PATH)
async def save_activity(data: dict) -> None: await _io(_save, ACTIVITY_PATH, data)
async def load_positions() -> dict: return await _io(_load, POSITIONS_PATH)
async def save_positions(data: dict) -> None: await _io(_save, POSITIONS_PATH, data)
