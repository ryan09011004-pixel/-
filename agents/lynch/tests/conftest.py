"""scripts/ 폴더를 임포트 경로에 추가하고 `scripts_path` 가짜 모듈로 ROOT를 노출한다."""
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.modules["scripts_path"] = types.SimpleNamespace(ROOT=ROOT)
