from pathlib import Path

from dietary_mcp.benchmarks import run_benchmarks


def test_benchmarks_pass() -> None:
    results = run_benchmarks(Path(__file__).resolve().parents[1])
    assert results["status"] == "ok"
