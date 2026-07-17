from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dietary_mcp.assets import runtime_asset_root
from dietary_mcp.errors import DietaryRegistryError
from dietary_mcp.models import (
    ExportInteroperabilityPreviewRequest,
    InteroperabilityExportPreview,
    InteroperabilityMappedField,
    InteroperabilityProfile,
    InteroperabilitySupportLevel,
    InteroperabilityUnsupportedField,
    ReadinessStatus,
)


def _validation_root(repo_root: Path) -> Path:
    candidate = repo_root / "validation" / "v1"
    if candidate.exists():
        return candidate
    return runtime_asset_root() / "validation" / "v1"


def read_interoperability_profiles(repo_root: Path) -> dict:
    return json.loads((_validation_root(repo_root) / "interoperability_profiles.json").read_text())


def get_interoperability_profile_record(repo_root: Path, profile_id: str) -> dict[str, Any]:
    payload = read_interoperability_profiles(repo_root)
    for item in payload["profiles"]:
        if item["profileId"] == profile_id:
            return item
    raise DietaryRegistryError(
        code="unknown_interoperability_profile",
        message=f"Unknown interoperability profile: {profile_id}",
        suggestion="Use a profile listed in interoperability://manifest.",
    )


def _extract_path(payload: Any, path: str) -> Any:
    current = payload
    for segment in path.split("."):
        if isinstance(current, dict):
            if segment not in current:
                return None
            current = current[segment]
            continue
        return None
    return current


def _set_path(target: dict[str, Any], path: str, value: Any) -> None:
    current = target
    segments = path.split(".")
    for segment in segments[:-1]:
        current = current.setdefault(segment, {})
    current[segments[-1]] = value


def _is_present(value: Any) -> bool:
    return value not in (None, "", [], {})


def export_interoperability_preview(
    repo_root: Path,
    request: ExportInteroperabilityPreviewRequest,
) -> InteroperabilityExportPreview:
    profile_record = get_interoperability_profile_record(repo_root, request.target_profile)
    profile = InteroperabilityProfile.model_validate(
        {
            "profileId": profile_record["profileId"],
            "displayName": profile_record["displayName"],
            "targetFamily": profile_record["targetFamily"],
            "ohtTemplates": profile_record.get("ohtTemplates", []),
            "notes": profile_record.get("notes", []),
        }
    )
    dossier_payload = request.dossier.model_dump(mode="json")

    target_document: dict[str, Any] = {}
    mapped_fields: list[InteroperabilityMappedField] = []
    unsupported_fields: list[InteroperabilityUnsupportedField] = []
    missing_required_fields: list[str] = []

    for mapping in profile_record["mappedFields"]:
        value = _extract_path(dossier_payload, mapping["localPath"])
        present = _is_present(value)
        if present:
            _set_path(target_document, mapping["targetPath"], value)
        if mapping.get("required") and not present:
            missing_required_fields.append(mapping["localPath"])
        mapped_fields.append(
            InteroperabilityMappedField(
                local_path=mapping["localPath"],
                target_path=mapping["targetPath"],
                support_level=InteroperabilitySupportLevel(mapping["supportLevel"]),
                required=mapping.get("required", False),
                value_present=present,
                value=value if present else None,
                note=mapping.get("note"),
            )
        )

    for item in profile_record.get("unsupportedFields", []):
        value = _extract_path(dossier_payload, item["localPath"])
        present = _is_present(value)
        if not present:
            continue
        unsupported_fields.append(
            InteroperabilityUnsupportedField(
                local_path=item["localPath"],
                reason=item["reason"],
                present=present,
                observed_value=value,
                suggested_action=item.get("suggestedAction"),
            )
        )

    if missing_required_fields:
        preview_status = ReadinessStatus.FAIL
    elif unsupported_fields or any(item.support_level != InteroperabilitySupportLevel.DIRECT for item in mapped_fields):
        preview_status = ReadinessStatus.REVIEW_REQUIRED
    else:
        preview_status = ReadinessStatus.PASS

    notes = [
        "This is a validation-only OHT/IUCLID-aligned JSON preview and not an XML submission payload.",
        "Unsupported fields are reported explicitly so downstream teams can track manual review or future profile expansion.",
        "No claim of IUCLID or OECD OHT XML equivalence is implied by this preview.",
    ]
    notes.extend(profile.notes)

    return InteroperabilityExportPreview(
        preview_status=preview_status,
        target_profile=profile,
        source_dossier_id=request.dossier.dossier_id,
        bundle_profile=request.dossier.bundle_profile,
        profile_resource_uri=f"interoperability://profile/{profile.profile_id}",
        documentation_resource_uri="docs://interoperability-preview",
        target_document=target_document,
        mapped_fields=mapped_fields,
        unsupported_fields=unsupported_fields,
        missing_required_fields=missing_required_fields,
        notes=notes,
    )
