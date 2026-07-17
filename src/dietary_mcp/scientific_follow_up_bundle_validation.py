from __future__ import annotations

import json
from pathlib import Path

from dietary_mcp.assets import runtime_asset_root
from dietary_mcp.models import (
    AssessReviewDossierReadinessRequest,
    ExportScientificFollowUpQueueBundleRequest,
)
from dietary_mcp.readiness_validation import _build_example_dossier
from dietary_mcp.runtime import get_cached_dietary_runtime


def _validation_root(repo_root: Path) -> Path:
    candidate = repo_root / "validation" / "v1"
    if candidate.exists():
        return candidate
    return runtime_asset_root() / "validation" / "v1"


def run_scientific_follow_up_queue_bundle_cases(repo_root: Path) -> dict:
    cases_payload = json.loads((_validation_root(repo_root) / "scientific_follow_up_queue_bundle_cases.json").read_text())
    runtime = get_cached_dietary_runtime(repo_root)
    results = []

    for case in cases_payload["cases"]:
        dossier = _build_example_dossier(runtime, case["scenario"])
        assessment = runtime.assess_review_dossier_readiness(
            AssessReviewDossierReadinessRequest(
                dossier=dossier,
                target_profile=case["targetProfile"],
            )
        )
        bundle = runtime.export_scientific_follow_up_queue_bundle(
            ExportScientificFollowUpQueueBundleRequest(
                dossier=dossier,
                assessment=assessment,
                bundle_note=case.get("bundleNote"),
            )
        )

        observed_action_ids = [item.action_id for item in bundle.action_items]
        observed_queue_labels_by_action = {
            item.action_id: [label.value for label in item.queue_labels]
            for item in bundle.action_items
        }
        status = (
            "ok"
            if bundle.overall_status.value == case["expectedOverallStatus"]
            and bundle.source_workflow == case["expectedSourceWorkflow"]
            and observed_action_ids == case["expectedActionIds"]
            and observed_queue_labels_by_action == case.get(
                "expectedQueueLabelsByAction",
                observed_queue_labels_by_action,
            )
            and bundle.recommended_sequence == case.get("expectedRecommendedSequence", bundle.recommended_sequence)
            else "mismatch"
        )
        results.append(
            {
                "name": case["name"],
                "status": status,
                "expectedOverallStatus": case["expectedOverallStatus"],
                "observedOverallStatus": bundle.overall_status.value,
                "expectedSourceWorkflow": case["expectedSourceWorkflow"],
                "observedSourceWorkflow": bundle.source_workflow,
                "expectedActionIds": case["expectedActionIds"],
                "observedActionIds": observed_action_ids,
                "expectedQueueLabelsByAction": case.get("expectedQueueLabelsByAction", {}),
                "observedQueueLabelsByAction": observed_queue_labels_by_action,
                "expectedRecommendedSequence": case.get("expectedRecommendedSequence", []),
                "observedRecommendedSequence": bundle.recommended_sequence,
            }
        )

    overall_status = "ok" if all(item["status"] == "ok" for item in results) else "review_required"
    return {"status": overall_status, "cases": results}
