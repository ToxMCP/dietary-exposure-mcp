from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "output" / "review" / "dietary_mcp_scientific_deep_review_concat.txt"
PROFILE_NAME = "scientific_deep_review_v1"


@dataclass(frozen=True)
class Candidate:
    path: str
    category: str


class TokenCounter:
    def __init__(self) -> None:
        self.mode = "approx_char_div_4"
        self._encoder = None
        try:
            import tiktoken  # type: ignore

            self._encoder = tiktoken.get_encoding("cl100k_base")
            self.mode = "cl100k_base"
        except Exception:
            self._encoder = None

    def count(self, text: str) -> int:
        if self._encoder is not None:
            return len(self._encoder.encode(text))
        return math.ceil(len(text) / 4)


PRIMARY_CANDIDATES: list[Candidate] = [
    Candidate("src/dietary_mcp/runtime.py", "src"),
    Candidate("src/dietary_mcp/models.py", "src"),
    Candidate("src/dietary_mcp/defaults.py", "src"),
    Candidate("src/dietary_mcp/integrations.py", "src"),
    Candidate("src/dietary_mcp/release_artifacts.py", "src"),
    Candidate("src/dietary_mcp/readiness.py", "src"),
    Candidate("tests/test_runtime.py", "tests"),
    Candidate("docs/scientific_hardening_tracker.md", "docs"),
    Candidate("defaults/v1/core_defaults.json", "defaults"),
    Candidate("defaults/v1/food_vocabulary_crosswalk.json", "defaults"),
    Candidate("defaults/v1/composition_recipes.json", "defaults"),
    Candidate("defaults/v1/source_catalog.json", "defaults"),
    Candidate("defaults/v1/substance_synonyms.json", "defaults"),
    Candidate("src/dietary_mcp/source_database.py", "src"),
    Candidate("src/dietary_mcp/scientific_ledger.py", "src"),
    Candidate("src/dietary_mcp/provenance.py", "src"),
    Candidate("src/dietary_mcp/contaminant_monitoring_checks.py", "src"),
    Candidate("src/dietary_mcp/contaminant_monitoring_signoff.py", "src"),
    Candidate("src/dietary_mcp/contaminant_monitoring_review_dossier.py", "src"),
    Candidate("src/dietary_mcp/metals_monitoring_signoff.py", "src"),
    Candidate("src/dietary_mcp/metals_monitoring_review_dossier.py", "src"),
    Candidate("src/dietary_mcp/reference_validation.py", "src"),
    Candidate("src/dietary_mcp/source_database_validation.py", "src"),
    Candidate("src/dietary_mcp/probabilistic_intake_summary_validation.py", "src"),
    Candidate("src/dietary_mcp/survey_distribution_summary_validation.py", "src"),
    Candidate("src/dietary_mcp/readiness_validation.py", "src"),
    Candidate("src/dietary_mcp/contaminant_monitoring_validation.py", "src"),
    Candidate("src/dietary_mcp/contaminant_monitoring_bundle_validation.py", "src"),
    Candidate("src/dietary_mcp/contaminant_monitoring_signoff_validation.py", "src"),
    Candidate("src/dietary_mcp/contaminant_monitoring_review_dossier_validation.py", "src"),
    Candidate("src/dietary_mcp/metals_monitoring_validation.py", "src"),
    Candidate("src/dietary_mcp/metals_monitoring_signoff_validation.py", "src"),
    Candidate("src/dietary_mcp/metals_monitoring_review_dossier_validation.py", "src"),
    Candidate("defaults/v1/reference_values.json", "defaults"),
    Candidate("defaults/v1/mrl_enforcement.json", "defaults"),
    Candidate("defaults/v1/consumption_profiles.json", "defaults"),
    Candidate("defaults/v1/consumption_datasets.json", "defaults"),
    Candidate("defaults/v1/commodity_taxonomy.json", "defaults"),
    Candidate("defaults/v1/method_registry.json", "defaults"),
    Candidate("defaults/v1/legal_authorities.json", "defaults"),
    Candidate("defaults/v1/reporting_profiles.json", "defaults"),
    Candidate("defaults/v1/occurrence_evidence_registry.json", "defaults"),
    Candidate("defaults/v1/analytical_method_evidence_registry.json", "defaults"),
    Candidate("defaults/v1/metals_occurrence_registry.json", "defaults"),
    Candidate("defaults/v1/metals_review_focus_registry.json", "defaults"),
    Candidate("defaults/v1/emerging_contaminants.json", "defaults"),
    Candidate("defaults/v1/regulatory_readiness_profiles.json", "defaults"),
    Candidate("defaults/v1/model_governance.json", "defaults"),
    Candidate("tests/test_core_math.py", "tests"),
    Candidate("tests/test_defaults.py", "tests"),
    Candidate("tests/test_integrations.py", "tests"),
    Candidate("tests/test_source_database_validation.py", "tests"),
    Candidate("docs/operator_guide.md", "docs"),
    Candidate("docs/regulatory_source_databases.md", "docs"),
    Candidate("docs/validation_framework.md", "docs"),
    Candidate("docs/regulatory_governance.md", "docs"),
    Candidate("docs/dietary_boundary_guide.md", "docs"),
    Candidate("docs/applicability_limits.md", "docs"),
    Candidate("docs/acute_vs_chronic_guide.md", "docs"),
    Candidate("docs/occurrence_evidence_registry.md", "docs"),
    Candidate("docs/analytical_method_evidence_registry.md", "docs"),
    Candidate("docs/metals_occurrence_registry.md", "docs"),
    Candidate("docs/contaminant_monitoring_import.md", "docs"),
    Candidate("docs/contaminant_monitoring_interpretation.md", "docs"),
    Candidate("docs/contaminant_monitoring_signoff.md", "docs"),
    Candidate("docs/contaminant_monitoring_review_dossier.md", "docs"),
    Candidate("docs/metals_monitoring_interpretation.md", "docs"),
    Candidate("docs/metals_monitoring_signoff.md", "docs"),
    Candidate("docs/metals_monitoring_review_dossier.md", "docs"),
]


OVERFLOW_CANDIDATES = [
    "defaults/v1/consumption_profiles_who_gems_public.json",
    "src/dietary_mcp/scientific_follow_up_bundle.py",
    "src/dietary_mcp/interoperability_readiness.py",
]


def render_section(candidate: Candidate, text: str) -> str:
    body = text.rstrip()
    if candidate.path.endswith(".json"):
        body = json.dumps(json.loads(body), separators=(",", ":"), ensure_ascii=True)
    return (
        f"\n\n===== BEGIN FILE: {candidate.path} =====\n"
        f"{body}\n"
        f"===== END FILE: {candidate.path} =====\n"
    )


def build_header(
    *,
    counter: TokenCounter,
    max_tokens: int,
    included: list[Candidate],
    body_tokens: int,
) -> str:
    category_counts = Counter(candidate.category for candidate in included)
    return (
        "Dietary MCP scientific deep review bundle\n"
        f"Profile: {PROFILE_NAME}\n"
        f"Generated: {datetime.now(timezone.utc).isoformat()}\n"
        f"Token budget: {max_tokens}\n"
        f"Tokenizer: {counter.mode}\n"
        f"Estimated tokens used: {body_tokens}\n"
        f"Included files: {len(included)} "
        f"(src={category_counts.get('src', 0)}, "
        f"defaults={category_counts.get('defaults', 0)}, "
        f"tests={category_counts.get('tests', 0)}, "
        f"docs={category_counts.get('docs', 0)})\n"
        "Focus: scientific runtime, governed defaults, validation modules, "
        "robustness tests, hardening tracker, and core governance docs.\n"
        "Overflow if more budget is available: "
        + ", ".join(OVERFLOW_CANDIDATES)
        + "\n"
    )


def select_candidates(counter: TokenCounter, max_tokens: int) -> tuple[list[Candidate], list[str], int]:
    included: list[Candidate] = []
    sections: list[str] = []

    for candidate in PRIMARY_CANDIDATES:
        file_path = ROOT / candidate.path
        text = file_path.read_text(encoding="utf-8")
        section = render_section(candidate, text)
        included.append(candidate)
        sections.append(section)

    while included:
        body = "".join(sections)
        header = build_header(counter=counter, max_tokens=max_tokens, included=included, body_tokens=0)
        final_text = header + body
        total_tokens = counter.count(final_text)
        if total_tokens <= max_tokens:
            final_header = build_header(
                counter=counter,
                max_tokens=max_tokens,
                included=included,
                body_tokens=total_tokens,
            )
            final_text = final_header + body
            return included, sections, counter.count(final_text)

        included.pop()
        sections.pop()

    raise RuntimeError("Unable to fit even the highest-priority file set inside the requested budget.")


def write_bundle(output_path: Path, max_tokens: int) -> tuple[int, int]:
    counter = TokenCounter()
    included, sections, final_tokens = select_candidates(counter, max_tokens=max_tokens)
    header = build_header(
        counter=counter,
        max_tokens=max_tokens,
        included=included,
        body_tokens=final_tokens,
    )
    final_text = header + "".join(sections)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(final_text, encoding="utf-8")
    return len(included), counter.count(final_text)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a token-budgeted deep-review concat bundle.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path to the output text file.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=200000,
        help="Maximum token budget for the generated bundle.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    included_count, estimated_tokens = write_bundle(args.output, max_tokens=args.max_tokens)
    print(f"Wrote {args.output}")
    print(f"Included files: {included_count}")
    print(f"Estimated tokens: {estimated_tokens}")


if __name__ == "__main__":
    main()
