from __future__ import annotations

from pathlib import Path

from dietary_mcp.assets import runtime_asset_root
from dietary_mcp.errors import DietaryRegistryError


DOC_MAP = {
    "operator-guide": "docs/operator_guide.md",
    "trade-risk-review": "docs/trade_risk_review.md",
    "provenance-policy": "docs/provenance_policy.md",
    "dietary-boundary-guide": "docs/dietary_boundary_guide.md",
    "population-profile-guide": "docs/population_profile_guide.md",
    "acute-vs-chronic-guide": "docs/acute_vs_chronic_guide.md",
    "suite-integration-guide": "docs/suite_integration.md",
    "validation-framework": "docs/validation_framework.md",
    "release-readiness": "docs/release_readiness.md",
    "adapter-spi": "docs/adapter_spi.md",
    "adapter-harness-inputs": "docs/adapter_harness_inputs.md",
    "adapter-input-templates": "docs/adapter_input_templates.md",
    "adapter-import-walkthroughs": "docs/adapter_import_walkthroughs.md",
    "confidentiality-bundles": "docs/confidentiality_bundles.md",
    "food-vocabulary-crosswalk": "docs/food_vocabulary_crosswalk.md",
    "occurrence-evidence-registry": "docs/occurrence_evidence_registry.md",
    "analytical-method-evidence-registry": "docs/analytical_method_evidence_registry.md",
    "contaminant-monitoring-import": "docs/contaminant_monitoring_import.md",
    "contaminant-monitoring-interpretation": "docs/contaminant_monitoring_interpretation.md",
    "contaminant-monitoring-signoff": "docs/contaminant_monitoring_signoff.md",
    "contaminant-monitoring-review-dossier": "docs/contaminant_monitoring_review_dossier.md",
    "scientific-follow-up-queue-bundle": "docs/scientific_follow_up_queue_bundle.md",
    "scientific-follow-up-review-board": "docs/scientific_follow_up_review_board.md",
    "scientific-follow-up-owner-handoff": "docs/scientific_follow_up_owner_handoff.md",
    "scientific-follow-up-owner-remediation": "docs/scientific_follow_up_owner_remediation.md",
    "scientific-follow-up-owner-signoff": "docs/scientific_follow_up_owner_signoff.md",
    "scientific-follow-up-owner-signoff-dossier": "docs/scientific_follow_up_owner_signoff_dossier.md",
    "metals-occurrence-registry": "docs/metals_occurrence_registry.md",
    "metals-review-focus-registry": "docs/metals_review_focus_registry.md",
    "metals-monitoring-interpretation": "docs/metals_monitoring_interpretation.md",
    "metals-monitoring-signoff": "docs/metals_monitoring_signoff.md",
    "metals-monitoring-review-dossier": "docs/metals_monitoring_review_dossier.md",
    "interoperability-preview": "docs/interoperability_preview.md",
    "interoperability-readiness": "docs/interoperability_readiness.md",
    "interoperability-remediation": "docs/interoperability_remediation.md",
    "interoperability-signoff": "docs/interoperability_signoff.md",
    "applicability-limits": "docs/applicability_limits.md",
    "extension-hooks": "docs/extension_hooks.md",
    "regulatory-seed-data": "docs/regulatory_seed_data.md",
    "regulatory-governance": "docs/regulatory_governance.md",
    "regulatory-source-databases": "docs/regulatory_source_databases.md",
    "reporting-profiles-registry": "docs/reporting_profiles_registry.md",
}


def read_doc(repo_root: Path, doc_name: str) -> str:
    try:
        relative_path = DOC_MAP[doc_name]
    except KeyError as exc:
        raise DietaryRegistryError(
            code="unknown_doc_resource",
            message=f"Unknown documentation resource: {doc_name}",
            suggestion="Use one of the documented docs:// resource names.",
        ) from exc
    candidate = repo_root / relative_path
    if candidate.exists():
        return candidate.read_text()
    return (runtime_asset_root() / relative_path).read_text()
