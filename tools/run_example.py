"""Run a code example and save its real output.

Usage: uv run python tools/run_example.py posts/NN-slug/code/example.py

Writes <example>.out.txt next to the script (stdout + stderr) and exits with
the example's own exit code, so a failing example is never silently published.
"""
import subprocess
import sys
from pathlib import Path


def main() -> int:
    script = Path(sys.argv[1]).resolve()
    result = subprocess.run(
        [sys.executable, script.name], cwd=script.parent,
        capture_output=True, text=True, timeout=300,
    )
    output = result.stdout + result.stderr
    script.with_suffix(".out.txt").write_text(output)
    print(output, end="")
    print(f"[exit code {result.returncode}]", file=sys.stderr)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
