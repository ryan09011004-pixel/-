"""다섯 에이전트를 한 번에 점검한다: 인용·사례 원문 대조, 에이전트별 테스트, 공통 테스트. 모델 호출·비용 없음.

사용: python check_all.py   (각 에이전트의 corpus/가 없으면 원문 대조는 건너뛴다고 표시)
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
AGENTS = ["buffett", "graham", "lynch", "dalio", "soros"]


def run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip().splitlines()[-1] if (p.stdout + p.stderr).strip() else ""


def main() -> int:
    failed = 0
    for a in AGENTS:
        d = ROOT / a
        if (d / "corpus" / "txt").exists():
            rc, last = run([sys.executable, "scripts/verify_quotes.py"], d)
        else:
            rc, last = 0, "원문 없음(건너뜀)"
        print(f"{a:8s} 원문대조: {'OK' if rc == 0 else 'FAIL'} {last}")
        failed += rc != 0
        rc, last = run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], d)
        print(f"{a:8s} 테스트  : {'OK' if rc == 0 else 'FAIL'} {last}")
        failed += rc != 0
    rc, last = run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "common/tests"], ROOT)
    print(f"{'common':8s} 테스트  : {'OK' if rc == 0 else 'FAIL'} {last}")
    failed += rc != 0
    print("모두 통과" if not failed else f"실패 {failed}건")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
