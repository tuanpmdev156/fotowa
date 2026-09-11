r"""Chạy cả hai kiểm tra tĩnh - gõ một lệnh là xong.

    .venv\Scripts\python.exe scripts\check.py

- `pytest --setup-plan`: giải toàn bộ fixture mà không mở browser, bắt lỗi sai tên
  fixture - thứ duy nhất type checker không thấy được (fixture khớp theo chuỗi lúc
  runtime).
- `pyright`: bắt sai kiểu và sai tên method/attribute. Cùng engine với Pylance nên
  kết quả khớp y với squiggle trong VSCode.
- `ruff check`: bắt lỗi style/PEP 8, import sai thứ tự, biến và import chết - những
  thứ pyright không quan tâm. Chỉ báo lỗi, không tự sửa; thêm `--fix` khi muốn ruff
  sửa hộ phần an toàn (xem `ruff.toml`).

Exit code khác 0 nếu bất kỳ bước nào thất bại; chạy hết cả ba bước để báo cáo đầy
đủ thay vì dừng ở bước đầu.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable

STEPS = [
    ("fixtures", [PYTHON, "-m", "pytest", "--setup-plan", "-q"]),
    ("types", [PYTHON, "-m", "pyright"]),
    ("lint", [PYTHON, "-m", "ruff", "check", "."]),
]


def main() -> int:
    failed: list[str] = []

    for name, cmd in STEPS:
        print(f"\n=== {name}: {' '.join(cmd[1:])} ===", flush=True)
        if subprocess.run(cmd, cwd=ROOT).returncode != 0:
            failed.append(name)

    print()
    if failed:
        print(f"FAILED: {', '.join(failed)}", file=sys.stderr)
        return 1

    print("All checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
