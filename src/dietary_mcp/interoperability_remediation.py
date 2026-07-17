from __future__ import annotations

import json
from pathlib import Path

from dietary_mcp.assets import runtime_asset_root
from dietary_mcp.errors import DietaryRegistryError
from dietary_mcp.models import (
    ExportInteroperabilityRemediationBundleRequest,
    InteroperabilityRemediationActionRecord,
    InteroperabilityRemediationBundle,
    InteroperabilityRemediationItem,
    ReviewResourceReference,
)


def _validation_root(repo_root: Path) -> Path:
    candidate = repo_root / "validation" / "v1"
    if candidate.exists():
        return candidate
    return runtime_asset_root() / "validation" / "v1"


def read_interoperability_remediation_actions(repo_root: Path) -> dict:
    return json.loads((_validation_root(repo_root) / "interoperability_remediation_actions.json").read_text())


def get_interoperability_remediation_action_record(repo_root: Path, action_id: str) -> dict:
    payload = read_interoperability_remediation_actions(repo_root)
    for item in payload["actions"]:
        if item["actionId"] == action_id:
            return item
    raise DietaryRegistryError(
        code="unknown_interoperability_remediation_action",
        message=f"Unknown interoperability remediation action: {action_id}",
        suggestion="Use an action listed in interoperability-remediation://catalog.",
    )


def _action_by_rule_id(repo_root: Path) -> dict[str, dict]:
    payload = read_interoperability_remediation_actions(repo_root)
    return {item["ruleId"]: item for item in payload["actions"]}


def export_interoperability_remediation_bundle(
    repo_root: Path,
    request: ExportInteroperabilityRemediationBundleRequest,
) -> InteroperabilityRemediationBundle:
    assessment = request.assessment
    preview = request.preview
    catalog_by_rule = _action_by_rule_id(repo_root)

    action_items: list[InteroperabilityRemediationItem] = []
    referenced_resources: dict[tuple[str, str], ReviewResourceReference] = {}

    def add_resource(role: str, uri: str, description: str) -> None:
        key = (role, uri)
        if key in referenced_resources:
            return
        referenced_resources[key] = ReviewResourceReference(
            role=role,
            uri=uri,
            description=description,
        )

    add_resource(
        "remediation_catalog",
        "interoperability-remediation://catalog",
        "Governed remediation catalog for interoperability readiness outcomes.",
    )
    add_resource(
        "interoperability_readiness_profile",
        f"interoperability-readiness://profile/{assessment.target_profile.profile_id}",
        "Governed interoperability readiness profile used for this assessment.",
    )
    add_resource(
        "interoperability_preview_profile",
        preview.profile_resource_uri,
        "Governed staged preview profile used to construct the interoperability preview.",
    )
    add_resource(
        "interoperability_readiness_docs",
        "docs://interoperability-readiness",
        "Operator guide for interoperability readiness semantics and exchange gates.",
    )
    add_resource(
        "interoperability_remediation_docs",
        "docs://interoperability-remediation",
        "Operator guide for governed interoperability remediation bundles.",
    )
    add_resource(
        "interoperability_remediation_validation",
        "validation://interoperability-remediation-actions",
        "Governed remediation action catalog keyed to interoperability readiness rule ids.",
    )

    triggered_rules = assessment.blocking_rules + assessment.warning_rules
    for rule in triggered_rules:
        action_record = catalog_by_rule.get(rule.rule_id)
        if action_record is None:
            action = InteroperabilityRemediationActionRecord(
                action_id=f"generic_{rule.rule_id}",
                rule_id=rule.rule_id,
                title=f"Address {rule.rule_id}",
                action_type="generic_review",
                summary="Review the triggered interoperability rule and resolve the underlying issue before advancing the gate.",
                recommended_steps=[
                    "Inspect the triggered rule details and linked readiness profile.",
                    "Review the staged preview, dossier, and governance records referenced by the assessment.",
                    "Regenerate the preview and readiness assessment after corrective actions.",
                ],
                documentation_uris=["docs://interoperability-readiness"],
                resource_uris=["validation://interoperability-rules"],
            )
        else:
            action = InteroperabilityRemediationActionRecord.model_validate(action_record)

        item = InteroperabilityRemediationItem(
            action_id=action.action_id,
            rule_id=rule.rule_id,
            title=action.title,
            action_type=action.action_type,
            priority=rule.status,
            blocking=rule.blocking or rule.status.value == "fail",
            summary=action.summary,
            recommended_steps=action.recommended_steps,
            documentation_uris=action.documentation_uris,
            resource_uris=action.resource_uris,
            trigger_message=rule.message,
            trigger_note=rule.note,
        )
        action_items.append(item)
        for uri in action.documentation_uris:
            add_resource("documentation", uri, f"Documentation linked from remediation action {action.action_id}.")
        for uri in action.resource_uris:
            add_resource("remediation_resource", uri, f"Resource linked from remediation action {action.action_id}.")

    notes = [
        "Remediation bundle is derived from the interoperability readiness assessment and does not change the underlying dossier or preview.",
        "Recommended actions are governed catalog entries keyed to triggered rule ids.",
        "This bundle does not imply that all listed actions are sufficient for submission-capable XML generation.",
    ]
    if assessment.overall_status.value == "fail":
        notes.append("At least one blocking remediation action remains before the selected exchange gate can be reconsidered.")

    return InteroperabilityRemediationBundle(
        overall_status=assessment.overall_status,
        target_profile=assessment.target_profile,
        source_preview_profile_id=assessment.source_preview_profile_id,
        source_dossier_id=preview.source_dossier_id,
        linked_dossier_readiness_profile=assessment.linked_dossier_readiness_profile,
        linked_dossier_readiness_status=assessment.linked_dossier_readiness_status,
        action_items=action_items,
        blocking_action_count=sum(1 for item in action_items if item.blocking),
        warning_action_count=sum(1 for item in action_items if not item.blocking),
        recommended_sequence=[item.action_id for item in action_items],
        catalog_resource_uri="interoperability-remediation://catalog",
        documentation_resource_uri="docs://interoperability-remediation",
        referenced_resources=list(referenced_resources.values()),
        notes=notes,
    )
