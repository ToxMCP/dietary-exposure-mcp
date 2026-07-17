from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from dietary_mcp.assets import runtime_asset_root
from dietary_mcp.errors import DietaryRegistryError
from dietary_mcp.models import (
    AnalyticalMethodEvidenceRecord,
    ConsumptionDatasetRecord,
    CommodityReference,
    ContaminantLegalLimitRecord,
    DocumentStatus,
    EmergingContaminantRecord,
    FoodVocabularyCrosswalkRecord,
    JurisdictionCoverageRecord,
    LegalAuthorityRecord,
    MetalsOccurrenceRecord,
    MetalsReviewFocusRecord,
    ModelGovernanceRecord,
    MrlEnforcementRecord,
    CompositionRecipeRecord,
    MethodRegistryRecord,
    IntakeWindowSemantic,
    OccurrenceEvidenceRecord,
    ProcessedCommodityMappingRecord,
    ProcessingFactorApplicabilityRecord,
    QualityFlag,
    ReferenceValueRecord,
    ReportingProfileRecord,
    RegulatoryReadinessProfile,
    RegulatoryRole,
    RegulatorySourceRecord,
    Severity,
    SourceClassification,
    SourceOriginTag,
    SourceReference,
)
from dietary_mcp.package_metadata import DEFAULTS_VERSION


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# Module-level cache for expensive MRL enforcement loads across multiple
# DefaultsRegistry instances (e.g. during test runs).
_MRL_REGISTRY_CACHE: dict[Path, dict[str, Any]] = {}
_YEAR_PATTERN = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
_SOURCE_CURRENCY_REVIEW_AGE_YEARS = 5
_OFFICIAL_PRIMARY_WAVE1_PROFILE = "official_primary_wave1"
_OFFICIAL_PRIMARY_WAVE2_PROFILE = "official_primary_wave2"
_OFFICIAL_PRIMARY_PROFILES = {
    _OFFICIAL_PRIMARY_WAVE1_PROFILE,
    _OFFICIAL_PRIMARY_WAVE2_PROFILE,
}


@dataclass(frozen=True)
class CommodityResolution:
    commodity: CommodityReference
    source_classification: SourceClassification
    quality_flags: list[QualityFlag]


@dataclass(frozen=True)
class SourceCurrencyAssessment:
    reference_date: date
    data_period: str | None
    historical_data_period: bool
    data_period_end_year: int | None
    historical_source_ids: tuple[str, ...]
    current_context_source_ids: tuple[str, ...]
    notes: tuple[str, ...]
    review_required: bool


def _extract_years(value: str | None) -> list[int]:
    if not value:
        return []
    return sorted({int(match.group(0)) for match in _YEAR_PATTERN.finditer(value)})


class DefaultsRegistry:
    def __init__(self, repo_root: Path) -> None:
        asset_root = repo_root if (repo_root / "defaults" / DEFAULTS_VERSION / "core_defaults.json").exists() else runtime_asset_root()
        self.repo_root = asset_root
        self.defaults_root = asset_root / "defaults"
        self.version_root = self.defaults_root / DEFAULTS_VERSION
        self.extensions_root = self.defaults_root / "extensions" / DEFAULTS_VERSION
        self.core_defaults = _load_json(self.version_root / "core_defaults.json")
        self.commodity_taxonomy = _load_json(self.version_root / "commodity_taxonomy.json")
        self.consumption_profiles = self._load_consumption_profile_packs()
        self.source_catalog = self._load_source_catalog()
        self.reference_values = self._load_reference_values()
        self.method_registry = self._load_method_registry()
        self.consumption_datasets = self._load_consumption_datasets()
        self.legal_authorities = self._load_legal_authorities()
        self.reporting_profiles = self._load_reporting_profiles()
        self.metals_occurrence_registry = self._load_metals_occurrence_registry()
        self.metals_review_focus_registry = self._load_metals_review_focus_registry()
        self.occurrence_evidence_registry = self._load_occurrence_evidence_registry()
        self.analytical_method_evidence_registry = self._load_analytical_method_evidence_registry()
        self.model_governance = self._load_model_governance()
        self.regulatory_readiness_profiles = self._load_regulatory_readiness_profiles()
        self.emerging_contaminants = self._load_emerging_contaminants()
        self._apply_extensions()
        self.food_vocabulary_crosswalk = self._load_food_vocabulary_crosswalk()
        self.contaminant_legal_limits = self._load_contaminant_legal_limits_registry()
        self._verify_manifest()
        self.mrl_enforcement_registry = self._load_mrl_enforcement_registry()
        self._mrl_index: dict[tuple[str, str, str], dict[str, Any]] = {}
        self._mrl_by_sc_index: dict[tuple[str, str], list[dict[str, Any]]] = {}
        self._mrl_by_record_id_index: dict[str, dict[str, Any]] = {}
        self._build_mrl_index()
        self.jurisdiction_coverage_registry = self._load_jurisdiction_coverage_registry()
        self.composition_recipes_registry = self._load_composition_recipes_registry()
        self.substance_synonyms = self._load_substance_synonyms()

    def _verify_manifest(self) -> None:
        logger = logging.getLogger("dietary_mcp.defaults")
        if os.environ.get("DIETARY_MCP_SKIP_DEFAULTS_VERIFICATION") == "1":
            logger.warning("Skipping defaults manifest verification due to DIETARY_MCP_SKIP_DEFAULTS_VERIFICATION=1")
            return

        manifest_path = self.defaults_root / "manifest.json"
        if not manifest_path.exists():
            raise DietaryRegistryError(
                code="missing_defaults_manifest",
                message="Defaults manifest is missing.",
                suggestion="Run the manifest generation command or restore defaults/manifest.json.",
            )

        manifest = _load_json(manifest_path)
        expected_files: dict[str, str] = {
            entry["path"]: entry["sha256"] for entry in manifest.get("files", [])
        }
        observed_files: set[str] = set()

        for relative_path, expected_sha256 in expected_files.items():
            file_path = self.repo_root / relative_path
            if not file_path.exists():
                raise DietaryRegistryError(
                    code="missing_defaults_file",
                    message=f"Defaults file listed in manifest is missing: {relative_path}",
                    suggestion="Restore the missing file or regenerate the manifest.",
                )
            observed_sha256 = _sha256(file_path)
            if observed_sha256 != expected_sha256:
                raise DietaryRegistryError(
                    code="defaults_integrity_mismatch",
                    message=f"Defaults file hash mismatch for {relative_path}: expected {expected_sha256}, got {observed_sha256}.",
                    suggestion="If you intentionally modified defaults, set DIETARY_MCP_SKIP_DEFAULTS_VERIFICATION=1.",
                )
            observed_files.add(relative_path)

        logger.debug("Defaults manifest verification passed for %d files.", len(observed_files))

        # Detect extra files in version_root and extensions_root that are not in manifest
        for path in sorted(self.version_root.glob("*.json")):
            relative = path.relative_to(self.repo_root).as_posix()
            if relative not in observed_files:
                raise DietaryRegistryError(
                    code="untracked_defaults_file",
                    message=f"Untracked defaults file: {relative}",
                    suggestion="Add the file to the manifest or remove it.",
                )

        if self.extensions_root.exists():
            for path in sorted(self.extensions_root.rglob("*.json")):
                relative = path.relative_to(self.repo_root).as_posix()
                if relative not in observed_files:
                    raise DietaryRegistryError(
                        code="untracked_defaults_extension_file",
                        message=f"Untracked defaults extension file: {relative}",
                        suggestion="Add the file to the manifest or remove it.",
                    )

    def _load_consumption_profile_packs(self) -> dict[str, Any]:
        merged = {"defaultsVersion": DEFAULTS_VERSION, "profiles": []}
        seen_profile_ids: set[str] = set()
        pack_paths = sorted(self.version_root.glob("consumption_profiles*.json"))
        if not pack_paths:
            raise DietaryRegistryError(
                code="missing_consumption_profile_pack",
                message="No consumption-profile packs were found in the defaults directory.",
                suggestion="Add at least one defaults/v1/consumption_profiles*.json pack.",
            )

        for path in pack_paths:
            payload = _load_json(path)
            kind = payload.get("kind")
            if kind not in (None, "consumption_profiles"):
                raise DietaryRegistryError(
                    code="invalid_consumption_profile_pack_kind",
                    message=f"Consumption-profile pack {path.name} has an invalid kind field.",
                    suggestion="Use kind='consumption_profiles' or omit kind for base defaults packs.",
                )
            profiles = payload.get("profiles")
            if not isinstance(profiles, list):
                raise DietaryRegistryError(
                    code="invalid_consumption_profile_pack",
                    message=f"Consumption-profile pack {path.name} must define a profiles list.",
                    suggestion="Publish consumption-profile packs with a top-level profiles array.",
                )
            for profile in profiles:
                profile_id = profile["profileId"]
                if profile_id in seen_profile_ids:
                    raise DietaryRegistryError(
                        code="duplicate_consumption_profile_pack_entry",
                        message=f"Consumption-profile pack duplicates existing id {profile_id}.",
                        suggestion="Assign unique profile ids across defaults/v1 consumption-profile packs.",
                    )
                seen_profile_ids.add(profile_id)
                merged["profiles"].append(profile)
        return merged

    def _load_source_catalog(self) -> dict[str, Any]:
        merged = {"defaultsVersion": DEFAULTS_VERSION, "sources": []}
        seen_source_ids: set[str] = set()
        for path in sorted(self.version_root.glob("source_catalog*.json")):
            payload = _load_json(path)
            kind = payload.get("kind")
            validation_profile = payload.get("validationProfile")
            if kind not in (None, "source_catalog"):
                raise DietaryRegistryError(
                    code="invalid_source_catalog_pack_kind",
                    message=f"Source catalog pack {path.name} has an invalid kind field.",
                    suggestion="Use kind='source_catalog' or omit kind for base source catalogs.",
                )
            sources = payload.get("sources")
            if not isinstance(sources, list):
                raise DietaryRegistryError(
                    code="invalid_source_catalog_pack",
                    message=f"Source catalog pack {path.name} must define a sources list.",
                    suggestion="Publish source catalogs with a top-level sources array.",
                )
            for source in sources:
                source_id = source["sourceId"]
                if source_id in seen_source_ids:
                    raise DietaryRegistryError(
                        code="duplicate_source_catalog_entry",
                        message=f"Source catalog pack duplicates existing source id {source_id}.",
                        suggestion="Assign unique source ids across defaults/v1 source catalogs.",
                    )
                seen_source_ids.add(source_id)
                normalized_source = dict(source)
                normalized_source.setdefault("originTag", self._infer_source_origin_tag(normalized_source))
                validated_source = RegulatorySourceRecord.model_validate(normalized_source).model_dump(
                    mode="json",
                    by_alias=True,
                )
                if validation_profile in _OFFICIAL_PRIMARY_PROFILES:
                    self._validate_wave1_source_record(path, validated_source)
                merged["sources"].append(validated_source)
        return merged

    def _infer_source_origin_tag(self, source: dict[str, Any]) -> str:
        explicit = source.get("originTag")
        if explicit:
            return str(explicit)

        note_text = " ".join([source.get("title", "")] + list(source.get("notes", []))).lower()
        kind = str(source.get("kind", "")).strip().lower()
        organization = str(source.get("organization", "")).strip().lower()

        if any(
            marker in note_text
            for marker in (
                "illustrative",
                "placeholder",
                "workflow-hardening",
                "not an externally governed",
                "not official",
                "provisional crosswalk",
            )
        ):
            return SourceOriginTag.ILLUSTRATIVE_PLACEHOLDER.value
        if kind.startswith("official_") and organization not in {"dietary mcp", "project internal", "internal"}:
            return SourceOriginTag.OFFICIAL_REGULATORY.value
        if kind.startswith("curated_"):
            return SourceOriginTag.CURATED_DERIVED.value
        if organization in {"dietary mcp", "project internal", "internal"}:
            return SourceOriginTag.INTERNAL_OPERATIONAL.value
        return SourceOriginTag.CURATED_DERIVED.value

    def _known_source_ids(self) -> set[str]:
        return {item["sourceId"] for item in self.source_catalog["sources"]}

    def _is_official_final_source(self, source_id: str) -> bool:
        record = self._source_catalog_record_or_none(source_id)
        if record is None:
            return False
        return (
            record.get("originTag") == SourceOriginTag.OFFICIAL_REGULATORY.value
            and record.get("documentStatus") == DocumentStatus.FINAL_CURRENT.value
        )

    def _validate_wave1_source_record(self, path: Path, source: dict[str, Any]) -> None:
        if source.get("originTag") != SourceOriginTag.OFFICIAL_REGULATORY.value:
            raise DietaryRegistryError(
                code="invalid_wave1_source_origin",
                message=(
                    f"Wave-1 source record {source['sourceId']} in {path.name} must resolve to official regulatory provenance."
                ),
                suggestion="Use only official primary-source records in official_primary_wave1 packs.",
            )
        if source.get("documentStatus") != DocumentStatus.FINAL_CURRENT.value:
            raise DietaryRegistryError(
                code="invalid_wave1_source_status",
                message=(
                    f"Wave-1 source record {source['sourceId']} in {path.name} must be final/current, not "
                    f"{source.get('documentStatus')}."
                ),
                suggestion="Use only final/current primary-source records in official_primary_wave1 packs.",
            )

    def _validate_wave1_reference_record(self, path: Path, record: dict[str, Any]) -> None:
        if record.get("effectiveDate") is None:
            raise DietaryRegistryError(
                code="missing_wave1_reference_value_effective_date",
                message=f"Wave-1 reference-value record {record['recordId']} in {path.name} must publish an effectiveDate.",
                suggestion="Populate effectiveDate for official wave-1 reference-value records.",
            )
        if record.get("documentStatus") != DocumentStatus.FINAL_CURRENT.value:
            raise DietaryRegistryError(
                code="invalid_wave1_reference_value_status",
                message=(
                    f"Wave-1 reference-value record {record['recordId']} in {path.name} must be final/current, "
                    f"not {record.get('documentStatus')}."
                ),
                suggestion="Use only final/current primary-source reference values in official_primary_wave1 packs.",
            )
        non_official_sources = [source_id for source_id in record["sourceIds"] if not self._is_official_final_source(source_id)]
        if non_official_sources:
            raise DietaryRegistryError(
                code="invalid_wave1_reference_value_source",
                message=(
                    f"Wave-1 reference-value record {record['recordId']} in {path.name} references non-official "
                    f"or non-final sources: {non_official_sources}."
                ),
                suggestion="Reference only official final/current source ids in official_primary_wave1 packs.",
            )

    def _validate_wave1_legal_authority_record(self, path: Path, record: dict[str, Any]) -> None:
        if record.get("documentStatus") != DocumentStatus.FINAL_CURRENT.value:
            raise DietaryRegistryError(
                code="invalid_wave1_legal_authority_status",
                message=(
                    f"Wave-1 legal-authority record {record['authorityId']} in {path.name} must be final/current, "
                    f"not {record.get('documentStatus')}."
                ),
                suggestion="Use only final/current legal anchors in official_primary_wave1 packs.",
            )
        if not self._is_official_final_source(record["sourceId"]):
            raise DietaryRegistryError(
                code="invalid_wave1_legal_authority_source",
                message=(
                    f"Wave-1 legal-authority record {record['authorityId']} in {path.name} must reference an "
                    "official final/current source."
                ),
                suggestion="Reference only official final/current source ids in official_primary_wave1 packs.",
            )

    def _validate_wave1_mrl_record(self, path: Path, record: dict[str, Any]) -> None:
        if record.get("effectiveDate") is None:
            raise DietaryRegistryError(
                code="missing_wave1_mrl_effective_date",
                message=f"Wave-1 MRL record {record['recordId']} in {path.name} must publish an effectiveDate.",
                suggestion="Populate effectiveDate for official wave-1 MRL records.",
            )
        non_official_sources = [source_id for source_id in record["sourceIds"] if not self._is_official_final_source(source_id)]
        if non_official_sources:
            raise DietaryRegistryError(
                code="invalid_wave1_mrl_source",
                message=(
                    f"Wave-1 MRL record {record['recordId']} in {path.name} references non-official or non-final "
                    f"sources: {non_official_sources}."
                ),
                suggestion="Reference only official final/current source ids in official_primary_wave1 packs.",
            )

    def _validate_official_primary_contaminant_legal_limit_record(self, path: Path, record: dict[str, Any]) -> None:
        if record.get("effectiveDate") is None:
            raise DietaryRegistryError(
                code="missing_official_primary_contaminant_legal_limit_effective_date",
                message=(
                    f"Official-primary contaminant legal-limit record {record['recordId']} in {path.name} "
                    "must publish an effectiveDate."
                ),
                suggestion="Populate effectiveDate for official primary-source contaminant legal-limit records.",
            )
        if record.get("documentStatus") != DocumentStatus.FINAL_CURRENT.value:
            raise DietaryRegistryError(
                code="invalid_official_primary_contaminant_legal_limit_status",
                message=(
                    f"Official-primary contaminant legal-limit record {record['recordId']} in {path.name} "
                    f"must be final/current, not {record.get('documentStatus')}."
                ),
                suggestion="Use only final/current official primary-source contaminant legal-limit records.",
            )
        non_official_sources = [
            source_id for source_id in record["sourceIds"] if not self._is_official_final_source(source_id)
        ]
        if non_official_sources:
            raise DietaryRegistryError(
                code="invalid_official_primary_contaminant_legal_limit_source",
                message=(
                    f"Official-primary contaminant legal-limit record {record['recordId']} in {path.name} "
                    f"references non-official or non-final sources: {non_official_sources}."
                ),
                suggestion="Reference only official final/current source ids in official primary-source legal-limit packs.",
            )

    def _load_reference_values(self) -> dict[str, Any]:
        merged = {"defaultsVersion": DEFAULTS_VERSION, "records": []}
        seen_record_ids: set[str] = set()
        known_sources = self._known_source_ids()
        for path in sorted(self.version_root.glob("reference_values*.json")):
            payload = _load_json(path)
            kind = payload.get("kind")
            validation_profile = payload.get("validationProfile")
            if kind not in (None, "reference_values"):
                raise DietaryRegistryError(
                    code="invalid_reference_values_pack_kind",
                    message=f"Reference-values pack {path.name} has an invalid kind field.",
                    suggestion="Use kind='reference_values' or omit kind for base reference-values packs.",
                )
            records = payload.get("records")
            if not isinstance(records, list):
                raise DietaryRegistryError(
                    code="invalid_reference_values_pack",
                    message=f"Reference-values pack {path.name} must define a records list.",
                    suggestion="Publish reference-values packs with a top-level records array.",
                )
            for item in records:
                record = ReferenceValueRecord.model_validate(item).model_dump(mode="json", by_alias=True)
                record_id = record["recordId"]
                if record_id in seen_record_ids:
                    raise DietaryRegistryError(
                        code="duplicate_reference_value_entry",
                        message=f"Reference-values pack duplicates existing record id {record_id}.",
                        suggestion="Assign one reference-value record per record id.",
                    )
                unknown_sources = [source_id for source_id in record["sourceIds"] if source_id not in known_sources]
                if unknown_sources:
                    raise DietaryRegistryError(
                        code="unknown_reference_value_source",
                        message=f"Reference-value record {record_id} references unknown sources: {unknown_sources}.",
                        suggestion="Reference source ids that exist in defaults/v1/source_catalog*.json.",
                    )
                for field_name in ("primarySourceId", "databaseSourceId"):
                    field_value = record.get(field_name)
                    if field_value is not None and field_value not in record["sourceIds"]:
                        raise DietaryRegistryError(
                            code="reference_value_source_mismatch",
                            message=(
                                f"Reference-value record {record_id} publishes {field_name}={field_value} "
                                "outside sourceIds."
                            ),
                            suggestion="Keep primarySourceId/databaseSourceId aligned with the record sourceIds list.",
                        )
                if validation_profile in _OFFICIAL_PRIMARY_PROFILES:
                    self._validate_wave1_reference_record(path, record)
                seen_record_ids.add(record_id)
                merged["records"].append(record)
        if not merged["records"]:
            raise DietaryRegistryError(
                code="missing_reference_values_pack",
                message="No reference-values packs were found in the defaults directory.",
                suggestion="Add defaults/v1/reference_values.json.",
            )
        return merged

    def _load_consumption_datasets(self) -> dict[str, Any]:
        merged = {"defaultsVersion": DEFAULTS_VERSION, "datasets": []}
        seen_dataset_ids: set[str] = set()
        known_sources = self._known_source_ids()
        known_method_ids = {item["methodId"] for item in self.method_registry["methods"]}
        for path in sorted(self.version_root.glob("consumption_datasets*.json")):
            payload = _load_json(path)
            kind = payload.get("kind")
            if kind not in (None, "consumption_datasets"):
                raise DietaryRegistryError(
                    code="invalid_consumption_datasets_pack_kind",
                    message=f"Consumption-datasets pack {path.name} has an invalid kind field.",
                    suggestion="Use kind='consumption_datasets' or omit kind for base dataset registry packs.",
                )
            datasets = payload.get("datasets")
            if not isinstance(datasets, list):
                raise DietaryRegistryError(
                    code="invalid_consumption_datasets_pack",
                    message=f"Consumption-datasets pack {path.name} must define a datasets list.",
                    suggestion="Publish dataset registry packs with a top-level datasets array.",
                )
            for item in datasets:
                record = ConsumptionDatasetRecord.model_validate(item).model_dump(mode="json", by_alias=True)
                dataset_id = record["datasetId"]
                if dataset_id in seen_dataset_ids:
                    raise DietaryRegistryError(
                        code="duplicate_consumption_dataset_entry",
                        message=f"Consumption-datasets pack duplicates existing dataset id {dataset_id}.",
                        suggestion="Assign one dataset registry record per dataset id.",
                    )
                unknown_sources = [source_id for source_id in record["sourceIds"] if source_id not in known_sources]
                if unknown_sources:
                    raise DietaryRegistryError(
                        code="unknown_consumption_dataset_source",
                        message=f"Consumption dataset {dataset_id} references unknown sources: {unknown_sources}.",
                        suggestion="Reference source ids that exist in defaults/v1/source_catalog*.json.",
                    )
                unknown_methods = [method_id for method_id in record["methodIds"] if method_id not in known_method_ids]
                if unknown_methods:
                    raise DietaryRegistryError(
                        code="unknown_consumption_dataset_method",
                        message=f"Consumption dataset {dataset_id} references unknown methods: {unknown_methods}.",
                        suggestion="Reference method ids that exist in defaults/v1/method_registry.json.",
                    )
                seen_dataset_ids.add(dataset_id)
                merged["datasets"].append(record)
        if not merged["datasets"]:
            raise DietaryRegistryError(
                code="missing_consumption_datasets_pack",
                message="No consumption-datasets packs were found in the defaults directory.",
                suggestion="Add defaults/v1/consumption_datasets.json.",
            )
        return merged

    def _load_method_registry(self) -> dict[str, Any]:
        merged = {"defaultsVersion": DEFAULTS_VERSION, "methods": []}
        seen_method_ids: set[str] = set()
        known_sources = self._known_source_ids()
        for path in sorted(self.version_root.glob("method_registry*.json")):
            payload = _load_json(path)
            kind = payload.get("kind")
            if kind not in (None, "method_registry"):
                raise DietaryRegistryError(
                    code="invalid_method_registry_pack_kind",
                    message=f"Method-registry pack {path.name} has an invalid kind field.",
                    suggestion="Use kind='method_registry' or omit kind for base method registry packs.",
                )
            methods = payload.get("methods")
            if not isinstance(methods, list):
                raise DietaryRegistryError(
                    code="invalid_method_registry_pack",
                    message=f"Method-registry pack {path.name} must define a methods list.",
                    suggestion="Publish method registry packs with a top-level methods array.",
                )
            for item in methods:
                record = MethodRegistryRecord.model_validate(item).model_dump(mode="json", by_alias=True)
                method_id = record["methodId"]
                if method_id in seen_method_ids:
                    raise DietaryRegistryError(
                        code="duplicate_method_registry_entry",
                        message=f"Method-registry pack duplicates existing method id {method_id}.",
                        suggestion="Assign one method registry record per method id.",
                    )
                unknown_sources = [source_id for source_id in record["sourceIds"] if source_id not in known_sources]
                if unknown_sources:
                    raise DietaryRegistryError(
                        code="unknown_method_registry_source",
                        message=f"Method registry record {method_id} references unknown sources: {unknown_sources}.",
                        suggestion="Reference source ids that exist in defaults/v1/source_catalog*.json.",
                    )
                seen_method_ids.add(method_id)
                merged["methods"].append(record)
        if not merged["methods"]:
            raise DietaryRegistryError(
                code="missing_method_registry_pack",
                message="No method-registry packs were found in the defaults directory.",
                suggestion="Add defaults/v1/method_registry.json.",
            )
        return merged

    def _load_legal_authorities(self) -> dict[str, Any]:
        merged = {"defaultsVersion": DEFAULTS_VERSION, "authorities": []}
        seen_authority_ids: set[str] = set()
        known_sources = self._known_source_ids()
        for path in sorted(self.version_root.glob("legal_authorities*.json")):
            payload = _load_json(path)
            kind = payload.get("kind")
            validation_profile = payload.get("validationProfile")
            if kind not in (None, "legal_authorities"):
                raise DietaryRegistryError(
                    code="invalid_legal_authorities_pack_kind",
                    message=f"Legal-authorities pack {path.name} has an invalid kind field.",
                    suggestion="Use kind='legal_authorities' or omit kind for base legal-authorities packs.",
                )
            authorities = payload.get("authorities")
            if not isinstance(authorities, list):
                raise DietaryRegistryError(
                    code="invalid_legal_authorities_pack",
                    message=f"Legal-authorities pack {path.name} must define an authorities list.",
                    suggestion="Publish legal-authorities packs with a top-level authorities array.",
                )
            for item in authorities:
                record = LegalAuthorityRecord.model_validate(item).model_dump(mode="json", by_alias=True)
                authority_id = record["authorityId"]
                if authority_id in seen_authority_ids:
                    raise DietaryRegistryError(
                        code="duplicate_legal_authority_entry",
                        message=f"Legal-authorities pack duplicates existing authority id {authority_id}.",
                        suggestion="Assign one legal authority record per authority id.",
                    )
                if record["sourceId"] not in known_sources:
                    raise DietaryRegistryError(
                        code="unknown_legal_authority_source",
                        message=f"Legal authority {authority_id} references unknown source {record['sourceId']}.",
                        suggestion="Reference source ids that exist in defaults/v1/source_catalog*.json.",
                    )
                if validation_profile in _OFFICIAL_PRIMARY_PROFILES:
                    self._validate_wave1_legal_authority_record(path, record)
                seen_authority_ids.add(authority_id)
                merged["authorities"].append(record)
        if not merged["authorities"]:
            raise DietaryRegistryError(
                code="missing_legal_authorities_pack",
                message="No legal-authorities packs were found in the defaults directory.",
                suggestion="Add defaults/v1/legal_authorities.json.",
            )
        return merged

    def _load_reporting_profiles(self) -> dict[str, Any]:
        merged = {"defaultsVersion": DEFAULTS_VERSION, "profiles": []}
        seen_profile_ids: set[str] = set()
        known_sources = self._known_source_ids()
        known_legal_authority_ids = {item["authorityId"] for item in self.legal_authorities["authorities"]}
        known_reference_value_ids = {item["recordId"] for item in self.reference_values["records"]}
        for path in sorted(self.version_root.glob("reporting_profiles*.json")):
            payload = _load_json(path)
            kind = payload.get("kind")
            if kind not in (None, "reporting_profiles"):
                raise DietaryRegistryError(
                    code="invalid_reporting_profiles_pack_kind",
                    message=f"Reporting-profiles pack {path.name} has an invalid kind field.",
                    suggestion="Use kind='reporting_profiles' or omit kind for base reporting-profiles packs.",
                )
            profiles = payload.get("profiles")
            if not isinstance(profiles, list):
                raise DietaryRegistryError(
                    code="invalid_reporting_profiles_pack",
                    message=f"Reporting-profiles pack {path.name} must define a profiles list.",
                    suggestion="Publish reporting-profiles packs with a top-level profiles array.",
                )
            for item in profiles:
                record = ReportingProfileRecord.model_validate(item).model_dump(mode="json", by_alias=True)
                profile_id = record["profileId"]
                if profile_id in seen_profile_ids:
                    raise DietaryRegistryError(
                        code="duplicate_reporting_profile_entry",
                        message=f"Reporting-profiles pack duplicates existing profile id {profile_id}.",
                        suggestion="Assign one reporting-profile record per profile id.",
                    )
                unknown_sources = [source_id for source_id in record["sourceIds"] if source_id not in known_sources]
                if unknown_sources:
                    raise DietaryRegistryError(
                        code="unknown_reporting_profile_source",
                        message=f"Reporting profile {profile_id} references unknown sources: {unknown_sources}.",
                        suggestion="Reference source ids that exist in defaults/v1/source_catalog*.json.",
                    )
                unknown_legal_authorities = [
                    authority_id
                    for authority_id in record["legalAuthorityIds"]
                    if authority_id not in known_legal_authority_ids
                ]
                if unknown_legal_authorities:
                    raise DietaryRegistryError(
                        code="unknown_reporting_profile_legal_authority",
                        message=(
                            f"Reporting profile {profile_id} references unknown legal authorities: "
                            f"{unknown_legal_authorities}."
                        ),
                        suggestion="Reference legal-authority ids that exist in defaults/v1/legal_authorities.json.",
                    )
                unknown_reference_values = [
                    reference_value_id
                    for reference_value_id in record["referenceValueRecordIds"]
                    if reference_value_id not in known_reference_value_ids
                ]
                if unknown_reference_values:
                    raise DietaryRegistryError(
                        code="unknown_reporting_profile_reference_value",
                        message=(
                            f"Reporting profile {profile_id} references unknown reference values: "
                            f"{unknown_reference_values}."
                        ),
                        suggestion="Reference record ids that exist in defaults/v1/reference_values.json.",
                    )
                unknown_profile_refs = [
                    other_profile_id
                    for other_profile_id in record["notSubstitutableForProfileIds"]
                    if other_profile_id not in seen_profile_ids
                ]
                if unknown_profile_refs:
                    raise DietaryRegistryError(
                        code="unknown_reporting_profile_reference",
                        message=(
                            f"Reporting profile {profile_id} references unknown prior reporting profiles: "
                            f"{unknown_profile_refs}."
                        ),
                        suggestion="List non-substitutable profile ids after the referenced profile is declared.",
                    )
                seen_profile_ids.add(profile_id)
                merged["profiles"].append(record)
        if not merged["profiles"]:
            raise DietaryRegistryError(
                code="missing_reporting_profiles_pack",
                message="No reporting-profiles packs were found in the defaults directory.",
                suggestion="Add defaults/v1/reporting_profiles.json.",
            )
        return merged

    def _load_metals_occurrence_registry(self) -> dict[str, Any]:
        merged = {"defaultsVersion": DEFAULTS_VERSION, "records": []}
        seen_record_ids: set[str] = set()
        known_sources = self._known_source_ids()
        known_method_ids = {item["methodId"] for item in self.method_registry["methods"]}
        known_dataset_ids = {item["datasetId"] for item in self.consumption_datasets["datasets"]}
        known_legal_authority_ids = {item["authorityId"] for item in self.legal_authorities["authorities"]}
        known_reference_value_ids = {item["recordId"] for item in self.reference_values["records"]}
        for path in sorted(self.version_root.glob("metals_occurrence_registry*.json")):
            payload = _load_json(path)
            kind = payload.get("kind")
            if kind not in (None, "metals_occurrence_registry"):
                raise DietaryRegistryError(
                    code="invalid_metals_occurrence_registry_pack_kind",
                    message=f"Metals-occurrence registry pack {path.name} has an invalid kind field.",
                    suggestion="Use kind='metals_occurrence_registry' or omit kind for the base pack.",
                )
            records = payload.get("records")
            if not isinstance(records, list):
                raise DietaryRegistryError(
                    code="invalid_metals_occurrence_registry_pack",
                    message=f"Metals-occurrence registry pack {path.name} must define a records list.",
                    suggestion="Publish metals-occurrence registry packs with a top-level records array.",
                )
            for item in records:
                record = MetalsOccurrenceRecord.model_validate(item).model_dump(mode="json", by_alias=True)
                record_id = record["recordId"]
                if record_id in seen_record_ids:
                    raise DietaryRegistryError(
                        code="duplicate_metals_occurrence_record",
                        message=f"Metals-occurrence registry duplicates existing record id {record_id}.",
                        suggestion="Assign one metals-occurrence registry record per record id.",
                    )
                unknown_sources = [source_id for source_id in record["sourceIds"] if source_id not in known_sources]
                if unknown_sources:
                    raise DietaryRegistryError(
                        code="unknown_metals_occurrence_source",
                        message=f"Metals-occurrence record {record_id} references unknown sources: {unknown_sources}.",
                        suggestion="Reference source ids that exist in defaults/v1/source_catalog*.json.",
                    )
                unknown_methods = [method_id for method_id in record["methodIds"] if method_id not in known_method_ids]
                if unknown_methods:
                    raise DietaryRegistryError(
                        code="unknown_metals_occurrence_method",
                        message=f"Metals-occurrence record {record_id} references unknown methods: {unknown_methods}.",
                        suggestion="Reference method ids that exist in defaults/v1/method_registry.json.",
                    )
                unknown_legal_authorities = [
                    authority_id for authority_id in record["legalAuthorityIds"] if authority_id not in known_legal_authority_ids
                ]
                if unknown_legal_authorities:
                    raise DietaryRegistryError(
                        code="unknown_metals_occurrence_legal_authority",
                        message=(
                            f"Metals-occurrence record {record_id} references unknown legal authorities: "
                            f"{unknown_legal_authorities}."
                        ),
                        suggestion="Reference legal-authority ids that exist in defaults/v1/legal_authorities.json.",
                    )
                unknown_datasets = [dataset_id for dataset_id in record["datasetIds"] if dataset_id not in known_dataset_ids]
                if unknown_datasets:
                    raise DietaryRegistryError(
                        code="unknown_metals_occurrence_dataset",
                        message=f"Metals-occurrence record {record_id} references unknown datasets: {unknown_datasets}.",
                        suggestion="Reference dataset ids that exist in defaults/v1/consumption_datasets.json.",
                    )
                unknown_reference_values = [
                    reference_value_id
                    for reference_value_id in record["referenceValueRecordIds"]
                    if reference_value_id not in known_reference_value_ids
                ]
                if unknown_reference_values:
                    raise DietaryRegistryError(
                        code="unknown_metals_occurrence_reference_value",
                        message=(
                            f"Metals-occurrence record {record_id} references unknown reference values: "
                            f"{unknown_reference_values}."
                        ),
                        suggestion="Reference value ids that exist in defaults/v1/reference_values.json.",
                    )
                seen_record_ids.add(record_id)
                merged["records"].append(record)
        if not merged["records"]:
            raise DietaryRegistryError(
                code="missing_metals_occurrence_registry_pack",
                message="No metals-occurrence registry packs were found in the defaults directory.",
                suggestion="Add defaults/v1/metals_occurrence_registry.json.",
            )
        return merged

    def _load_metals_review_focus_registry(self) -> dict[str, Any]:
        merged = {"defaultsVersion": DEFAULTS_VERSION, "records": []}
        seen_focus_ids: set[str] = set()
        known_sources = self._known_source_ids()
        known_method_ids = {item["methodId"] for item in self.method_registry["methods"]}
        known_dataset_ids = {item["datasetId"] for item in self.consumption_datasets["datasets"]}
        known_legal_authority_ids = {item["authorityId"] for item in self.legal_authorities["authorities"]}
        known_reference_value_ids = {item["recordId"] for item in self.reference_values["records"]}
        known_occurrence_record_ids = {item["recordId"] for item in self.metals_occurrence_registry["records"]}
        for path in sorted(self.version_root.glob("metals_review_focus_registry*.json")):
            payload = _load_json(path)
            kind = payload.get("kind")
            if kind not in (None, "metals_review_focus_registry"):
                raise DietaryRegistryError(
                    code="invalid_metals_review_focus_registry_pack_kind",
                    message=f"Metals-review-focus registry pack {path.name} has an invalid kind field.",
                    suggestion="Use kind='metals_review_focus_registry' or omit kind for the base pack.",
                )
            records = payload.get("records")
            if not isinstance(records, list):
                raise DietaryRegistryError(
                    code="invalid_metals_review_focus_registry_pack",
                    message=f"Metals-review-focus registry pack {path.name} must define a records list.",
                    suggestion="Publish metals-review-focus registry packs with a top-level records array.",
                )
            for item in records:
                record = MetalsReviewFocusRecord.model_validate(item).model_dump(mode="json", by_alias=True)
                focus_id = record["focusId"]
                if focus_id in seen_focus_ids:
                    raise DietaryRegistryError(
                        code="duplicate_metals_review_focus_record",
                        message=f"Metals-review-focus registry duplicates existing focus id {focus_id}.",
                        suggestion="Assign one metals-review-focus registry record per focus id.",
                    )
                unknown_sources = [source_id for source_id in record["sourceIds"] if source_id not in known_sources]
                if unknown_sources:
                    raise DietaryRegistryError(
                        code="unknown_metals_review_focus_source",
                        message=(
                            f"Metals-review-focus record {focus_id} references unknown sources: {unknown_sources}."
                        ),
                        suggestion="Reference source ids that exist in defaults/v1/source_catalog*.json.",
                    )
                unknown_methods = [method_id for method_id in record["methodIds"] if method_id not in known_method_ids]
                if unknown_methods:
                    raise DietaryRegistryError(
                        code="unknown_metals_review_focus_method",
                        message=(
                            f"Metals-review-focus record {focus_id} references unknown methods: {unknown_methods}."
                        ),
                        suggestion="Reference method ids that exist in defaults/v1/method_registry.json.",
                    )
                unknown_legal_authorities = [
                    authority_id for authority_id in record["legalAuthorityIds"] if authority_id not in known_legal_authority_ids
                ]
                if unknown_legal_authorities:
                    raise DietaryRegistryError(
                        code="unknown_metals_review_focus_legal_authority",
                        message=(
                            f"Metals-review-focus record {focus_id} references unknown legal authorities: "
                            f"{unknown_legal_authorities}."
                        ),
                        suggestion="Reference legal-authority ids that exist in defaults/v1/legal_authorities.json.",
                    )
                unknown_datasets = [dataset_id for dataset_id in record["datasetIds"] if dataset_id not in known_dataset_ids]
                if unknown_datasets:
                    raise DietaryRegistryError(
                        code="unknown_metals_review_focus_dataset",
                        message=f"Metals-review-focus record {focus_id} references unknown datasets: {unknown_datasets}.",
                        suggestion="Reference dataset ids that exist in defaults/v1/consumption_datasets.json.",
                    )
                unknown_reference_values = [
                    reference_value_id
                    for reference_value_id in record["referenceValueRecordIds"]
                    if reference_value_id not in known_reference_value_ids
                ]
                if unknown_reference_values:
                    raise DietaryRegistryError(
                        code="unknown_metals_review_focus_reference_value",
                        message=(
                            f"Metals-review-focus record {focus_id} references unknown reference values: "
                            f"{unknown_reference_values}."
                        ),
                        suggestion="Reference value ids that exist in defaults/v1/reference_values.json.",
                    )
                unknown_occurrence_records = [
                    occurrence_record_id
                    for occurrence_record_id in record["linkedOccurrenceRecordIds"]
                    if occurrence_record_id not in known_occurrence_record_ids
                ]
                if unknown_occurrence_records:
                    raise DietaryRegistryError(
                        code="unknown_metals_review_focus_occurrence_record",
                        message=(
                            f"Metals-review-focus record {focus_id} references unknown metals-occurrence records: "
                            f"{unknown_occurrence_records}."
                        ),
                        suggestion="Reference record ids that exist in defaults/v1/metals_occurrence_registry.json.",
                    )
                seen_focus_ids.add(focus_id)
                merged["records"].append(record)
        if not merged["records"]:
            raise DietaryRegistryError(
                code="missing_metals_review_focus_registry_pack",
                message="No metals-review-focus registry packs were found in the defaults directory.",
                suggestion="Add defaults/v1/metals_review_focus_registry.json.",
            )
        return merged

    def _load_occurrence_evidence_registry(self) -> dict[str, Any]:
        merged = {"defaultsVersion": DEFAULTS_VERSION, "records": []}
        seen_record_ids: set[str] = set()
        known_sources = self._known_source_ids()
        known_occurrence_record_ids = {item["recordId"] for item in self.metals_occurrence_registry["records"]}
        known_dataset_ids = {item["datasetId"] for item in self.consumption_datasets["datasets"]}
        known_legal_authority_ids = {item["authorityId"] for item in self.legal_authorities["authorities"]}
        known_reference_value_ids = {item["recordId"] for item in self.reference_values["records"]}
        known_focus_ids = {item["focusId"] for item in self.metals_review_focus_registry["records"]}
        known_reporting_profile_ids = {item["profileId"] for item in self.reporting_profiles["profiles"]}
        for path in sorted(self.version_root.glob("occurrence_evidence_registry*.json")):
            payload = _load_json(path)
            kind = payload.get("kind")
            if kind not in (None, "occurrence_evidence_registry"):
                raise DietaryRegistryError(
                    code="invalid_occurrence_evidence_registry_pack_kind",
                    message=f"Occurrence-evidence registry pack {path.name} has an invalid kind field.",
                    suggestion="Use kind='occurrence_evidence_registry' or omit kind for the base pack.",
                )
            records = payload.get("records")
            if not isinstance(records, list):
                raise DietaryRegistryError(
                    code="invalid_occurrence_evidence_registry_pack",
                    message=f"Occurrence-evidence registry pack {path.name} must define a records list.",
                    suggestion="Publish occurrence-evidence registry packs with a top-level records array.",
                )
            for item in records:
                record = OccurrenceEvidenceRecord.model_validate(item).model_dump(mode="json", by_alias=True)
                record_id = record["recordId"]
                if record_id in seen_record_ids:
                    raise DietaryRegistryError(
                        code="duplicate_occurrence_evidence_record",
                        message=f"Occurrence-evidence registry duplicates existing record id {record_id}.",
                        suggestion="Assign one occurrence-evidence record per record id.",
                    )
                unknown_sources = [source_id for source_id in record["sourceIds"] if source_id not in known_sources]
                if unknown_sources:
                    raise DietaryRegistryError(
                        code="unknown_occurrence_evidence_source",
                        message=f"Occurrence-evidence record {record_id} references unknown sources: {unknown_sources}.",
                        suggestion="Reference source ids that exist in defaults/v1/source_catalog*.json.",
                    )
                unknown_occurrence_records = [
                    occurrence_record_id
                    for occurrence_record_id in record["occurrenceRecordIds"]
                    if occurrence_record_id not in known_occurrence_record_ids
                ]
                if unknown_occurrence_records:
                    raise DietaryRegistryError(
                        code="unknown_occurrence_evidence_occurrence_record",
                        message=(
                            f"Occurrence-evidence record {record_id} references unknown metals-occurrence records: "
                            f"{unknown_occurrence_records}."
                        ),
                        suggestion="Reference record ids that exist in defaults/v1/metals_occurrence_registry.json.",
                    )
                unknown_datasets = [dataset_id for dataset_id in record["datasetIds"] if dataset_id not in known_dataset_ids]
                if unknown_datasets:
                    raise DietaryRegistryError(
                        code="unknown_occurrence_evidence_dataset",
                        message=f"Occurrence-evidence record {record_id} references unknown datasets: {unknown_datasets}.",
                        suggestion="Reference dataset ids that exist in defaults/v1/consumption_datasets.json.",
                    )
                unknown_legal_authorities = [
                    authority_id for authority_id in record["legalAuthorityIds"] if authority_id not in known_legal_authority_ids
                ]
                if unknown_legal_authorities:
                    raise DietaryRegistryError(
                        code="unknown_occurrence_evidence_legal_authority",
                        message=(
                            f"Occurrence-evidence record {record_id} references unknown legal authorities: "
                            f"{unknown_legal_authorities}."
                        ),
                        suggestion="Reference legal-authority ids that exist in defaults/v1/legal_authorities.json.",
                    )
                unknown_reference_values = [
                    reference_value_id
                    for reference_value_id in record["referenceValueRecordIds"]
                    if reference_value_id not in known_reference_value_ids
                ]
                if unknown_reference_values:
                    raise DietaryRegistryError(
                        code="unknown_occurrence_evidence_reference_value",
                        message=(
                            f"Occurrence-evidence record {record_id} references unknown reference values: "
                            f"{unknown_reference_values}."
                        ),
                        suggestion="Reference value ids that exist in defaults/v1/reference_values.json.",
                    )
                unknown_focus_ids = [
                    focus_id for focus_id in record["linkedReviewFocusIds"] if focus_id not in known_focus_ids
                ]
                if unknown_focus_ids:
                    raise DietaryRegistryError(
                        code="unknown_occurrence_evidence_review_focus",
                        message=(
                            f"Occurrence-evidence record {record_id} references unknown metals-review-focus ids: "
                            f"{unknown_focus_ids}."
                        ),
                        suggestion="Reference focus ids that exist in defaults/v1/metals_review_focus_registry.json.",
                    )
                unknown_reporting_profiles = [
                    profile_id
                    for profile_id in record["reportingProfileIds"]
                    if profile_id not in known_reporting_profile_ids
                ]
                if unknown_reporting_profiles:
                    raise DietaryRegistryError(
                        code="unknown_occurrence_evidence_reporting_profile",
                        message=(
                            f"Occurrence-evidence record {record_id} references unknown reporting profiles: "
                            f"{unknown_reporting_profiles}."
                        ),
                        suggestion="Reference reporting profile ids that exist in defaults/v1/reporting_profiles.json.",
                    )
                seen_record_ids.add(record_id)
                merged["records"].append(record)
        if not merged["records"]:
            raise DietaryRegistryError(
                code="missing_occurrence_evidence_registry_pack",
                message="No occurrence-evidence registry packs were found in the defaults directory.",
                suggestion="Add defaults/v1/occurrence_evidence_registry.json.",
            )
        return merged

    def _load_analytical_method_evidence_registry(self) -> dict[str, Any]:
        merged = {"defaultsVersion": DEFAULTS_VERSION, "records": []}
        seen_record_ids: set[str] = set()
        known_sources = self._known_source_ids()
        known_method_ids = {item["methodId"] for item in self.method_registry["methods"]}
        known_legal_authority_ids = {item["authorityId"] for item in self.legal_authorities["authorities"]}
        known_reporting_profile_ids = {item["profileId"] for item in self.reporting_profiles["profiles"]}
        for path in sorted(self.version_root.glob("analytical_method_evidence_registry*.json")):
            payload = _load_json(path)
            kind = payload.get("kind")
            if kind not in (None, "analytical_method_evidence_registry"):
                raise DietaryRegistryError(
                    code="invalid_analytical_method_evidence_registry_pack_kind",
                    message=f"Analytical-method-evidence registry pack {path.name} has an invalid kind field.",
                    suggestion="Use kind='analytical_method_evidence_registry' or omit kind for the base pack.",
                )
            records = payload.get("records")
            if not isinstance(records, list):
                raise DietaryRegistryError(
                    code="invalid_analytical_method_evidence_registry_pack",
                    message=f"Analytical-method-evidence registry pack {path.name} must define a records list.",
                    suggestion="Publish analytical-method-evidence registry packs with a top-level records array.",
                )
            for item in records:
                record = AnalyticalMethodEvidenceRecord.model_validate(item).model_dump(mode="json", by_alias=True)
                record_id = record["recordId"]
                if record_id in seen_record_ids:
                    raise DietaryRegistryError(
                        code="duplicate_analytical_method_evidence_record",
                        message=f"Analytical-method-evidence registry duplicates existing record id {record_id}.",
                        suggestion="Assign one analytical-method-evidence record per record id.",
                    )
                unknown_sources = [source_id for source_id in record["sourceIds"] if source_id not in known_sources]
                if unknown_sources:
                    raise DietaryRegistryError(
                        code="unknown_analytical_method_evidence_source",
                        message=(
                            f"Analytical-method-evidence record {record_id} references unknown sources: "
                            f"{unknown_sources}."
                        ),
                        suggestion="Reference source ids that exist in defaults/v1/source_catalog*.json.",
                    )
                unknown_methods = [method_id for method_id in record["methodIds"] if method_id not in known_method_ids]
                if unknown_methods:
                    raise DietaryRegistryError(
                        code="unknown_analytical_method_evidence_method",
                        message=(
                            f"Analytical-method-evidence record {record_id} references unknown methods: "
                            f"{unknown_methods}."
                        ),
                        suggestion="Reference method ids that exist in defaults/v1/method_registry.json.",
                    )
                unknown_legal_authorities = [
                    authority_id for authority_id in record["legalAuthorityIds"] if authority_id not in known_legal_authority_ids
                ]
                if unknown_legal_authorities:
                    raise DietaryRegistryError(
                        code="unknown_analytical_method_evidence_legal_authority",
                        message=(
                            f"Analytical-method-evidence record {record_id} references unknown legal authorities: "
                            f"{unknown_legal_authorities}."
                        ),
                        suggestion="Reference legal-authority ids that exist in defaults/v1/legal_authorities.json.",
                    )
                unknown_reporting_profiles = [
                    profile_id
                    for profile_id in record["reportingProfileIds"]
                    if profile_id not in known_reporting_profile_ids
                ]
                if unknown_reporting_profiles:
                    raise DietaryRegistryError(
                        code="unknown_analytical_method_evidence_reporting_profile",
                        message=(
                            f"Analytical-method-evidence record {record_id} references unknown reporting profiles: "
                            f"{unknown_reporting_profiles}."
                        ),
                        suggestion="Reference reporting profile ids that exist in defaults/v1/reporting_profiles.json.",
                    )
                seen_record_ids.add(record_id)
                merged["records"].append(record)
        if not merged["records"]:
            raise DietaryRegistryError(
                code="missing_analytical_method_evidence_registry_pack",
                message="No analytical-method-evidence registry packs were found in the defaults directory.",
                suggestion="Add defaults/v1/analytical_method_evidence_registry.json.",
            )
        return merged

    def _load_emerging_contaminants(self) -> dict[str, Any]:
        merged = {"defaultsVersion": DEFAULTS_VERSION, "families": []}
        seen_family_ids: set[str] = set()
        known_sources = self._known_source_ids()
        known_method_ids = {item["methodId"] for item in self.method_registry["methods"]}
        known_profile_ids = {item["profileId"] for item in self.regulatory_readiness_profiles["profiles"]} if hasattr(self, "regulatory_readiness_profiles") else set()
        for path in sorted(self.version_root.glob("emerging_contaminants*.json")):
            payload = _load_json(path)
            kind = payload.get("kind")
            if kind not in (None, "emerging_contaminants"):
                raise DietaryRegistryError(
                    code="invalid_emerging_contaminants_pack_kind",
                    message=f"Emerging-contaminants pack {path.name} has an invalid kind field.",
                    suggestion="Use kind='emerging_contaminants' or omit kind for base emerging-contaminants packs.",
                )
            families = payload.get("families")
            if not isinstance(families, list):
                raise DietaryRegistryError(
                    code="invalid_emerging_contaminants_pack",
                    message=f"Emerging-contaminants pack {path.name} must define a families list.",
                    suggestion="Publish emerging-contaminants packs with a top-level families array.",
                )
            for item in families:
                record = EmergingContaminantRecord.model_validate(item).model_dump(mode="json", by_alias=True)
                family_id = record["familyId"]
                if family_id in seen_family_ids:
                    raise DietaryRegistryError(
                        code="duplicate_emerging_contaminant_entry",
                        message=f"Emerging-contaminants pack duplicates existing family id {family_id}.",
                        suggestion="Assign one emerging-contaminant record per family id.",
                    )
                unknown_sources = [source_id for source_id in record["sourceIds"] if source_id not in known_sources]
                if unknown_sources:
                    raise DietaryRegistryError(
                        code="unknown_emerging_contaminant_source",
                        message=f"Emerging contaminant record {family_id} references unknown sources: {unknown_sources}.",
                        suggestion="Reference source ids that exist in defaults/v1/source_catalog*.json.",
                    )
                unknown_methods = [method_id for method_id in record["methodIds"] if method_id not in known_method_ids]
                if unknown_methods:
                    raise DietaryRegistryError(
                        code="unknown_emerging_contaminant_method",
                        message=f"Emerging contaminant record {family_id} references unknown methods: {unknown_methods}.",
                        suggestion="Reference method ids that exist in defaults/v1/method_registry.json.",
                    )
                unknown_profiles = [
                    profile_id
                    for profile_id in record["defaultReadinessProfileIds"] + record["hardFailureProfiles"]
                    if profile_id not in known_profile_ids
                ]
                if unknown_profiles:
                    raise DietaryRegistryError(
                        code="unknown_emerging_contaminant_profile",
                        message=f"Emerging contaminant record {family_id} references unknown readiness profiles: {unknown_profiles}.",
                        suggestion="Reference readiness profile ids that exist in defaults/v1/regulatory_readiness_profiles.json.",
                    )
                seen_family_ids.add(family_id)
                merged["families"].append(record)
        if not merged["families"]:
            raise DietaryRegistryError(
                code="missing_emerging_contaminants_pack",
                message="No emerging-contaminants packs were found in the defaults directory.",
                suggestion="Add defaults/v1/emerging_contaminants.json.",
            )
        return merged

    def _load_model_governance(self) -> dict[str, Any]:
        merged = {"defaultsVersion": DEFAULTS_VERSION, "families": []}
        seen_families: set[str] = set()
        for path in sorted(self.version_root.glob("model_governance*.json")):
            payload = _load_json(path)
            kind = payload.get("kind")
            if kind not in (None, "model_governance"):
                raise DietaryRegistryError(
                    code="invalid_model_governance_pack_kind",
                    message=f"Model governance pack {path.name} has an invalid kind field.",
                    suggestion="Use kind='model_governance' or omit kind for base governance packs.",
                )
            families = payload.get("families")
            if not isinstance(families, list):
                raise DietaryRegistryError(
                    code="invalid_model_governance_pack",
                    message=f"Model governance pack {path.name} must define a families list.",
                    suggestion="Publish model governance packs with a top-level families array.",
                )
            for family in families:
                record = ModelGovernanceRecord.model_validate(family).model_dump(mode="json", by_alias=True)
                family_id = record["modelFamily"]
                if family_id in seen_families:
                    raise DietaryRegistryError(
                        code="duplicate_model_governance_entry",
                        message=f"Model governance pack duplicates existing model family {family_id}.",
                        suggestion="Assign one governance record per model family.",
                    )
                unknown_sources = [
                    source_id
                    for source_id in record["sourceIds"]
                    if source_id not in {item["sourceId"] for item in self.source_catalog["sources"]}
                ]
                if unknown_sources:
                    raise DietaryRegistryError(
                        code="unknown_model_governance_source",
                        message=f"Model governance record {family_id} references unknown sources: {unknown_sources}.",
                        suggestion="Reference source ids that exist in defaults/v1/source_catalog*.json.",
                    )
                seen_families.add(family_id)
                merged["families"].append(record)
        if not merged["families"]:
            raise DietaryRegistryError(
                code="missing_model_governance_pack",
                message="No model governance packs were found in the defaults directory.",
                suggestion="Add defaults/v1/model_governance.json.",
            )
        return merged

    def _load_regulatory_readiness_profiles(self) -> dict[str, Any]:
        merged = {"defaultsVersion": DEFAULTS_VERSION, "profiles": []}
        seen_profile_ids: set[str] = set()
        for path in sorted(self.version_root.glob("regulatory_readiness_profiles*.json")):
            payload = _load_json(path)
            kind = payload.get("kind")
            if kind not in (None, "regulatory_readiness_profiles"):
                raise DietaryRegistryError(
                    code="invalid_regulatory_readiness_profiles_pack_kind",
                    message=f"Regulatory readiness profiles pack {path.name} has an invalid kind field.",
                    suggestion="Use kind='regulatory_readiness_profiles' or omit kind for base readiness profile packs.",
                )
            profiles = payload.get("profiles")
            if not isinstance(profiles, list):
                raise DietaryRegistryError(
                    code="invalid_regulatory_readiness_profiles_pack",
                    message=f"Regulatory readiness profiles pack {path.name} must define a profiles list.",
                    suggestion="Publish readiness profile packs with a top-level profiles array.",
                )
            for profile in profiles:
                record = RegulatoryReadinessProfile.model_validate(profile).model_dump(mode="json", by_alias=True)
                profile_id = record["profileId"]
                if profile_id in seen_profile_ids:
                    raise DietaryRegistryError(
                        code="duplicate_regulatory_readiness_profile_entry",
                        message=f"Regulatory readiness profiles duplicate existing id {profile_id}.",
                        suggestion="Assign one readiness profile record per profile id.",
                    )
                seen_profile_ids.add(profile_id)
                merged["profiles"].append(record)
        if not merged["profiles"]:
            raise DietaryRegistryError(
                code="missing_regulatory_readiness_profiles_pack",
                message="No regulatory readiness profile packs were found in the defaults directory.",
                suggestion="Add defaults/v1/regulatory_readiness_profiles.json.",
            )
        return merged

    def _load_food_vocabulary_crosswalk(self) -> dict[str, Any]:
        path = self.version_root / "food_vocabulary_crosswalk.json"
        if not path.exists():
            raise DietaryRegistryError(
                code="missing_food_vocabulary_crosswalk_pack",
                message="No food vocabulary crosswalk pack was found in the defaults directory.",
                suggestion="Add defaults/v1/food_vocabulary_crosswalk.json.",
            )
        payload = _load_json(path)
        if payload.get("kind") not in (None, "food_vocabulary_crosswalk"):
            raise DietaryRegistryError(
                code="invalid_food_vocabulary_crosswalk_pack_kind",
                message="Food vocabulary crosswalk pack has an invalid kind field.",
                suggestion="Use kind='food_vocabulary_crosswalk' or omit kind for the base pack.",
            )

        known_commodities = {item["commodityCode"] for item in self.commodity_taxonomy["commodities"]}
        known_sources = {item["sourceId"] for item in self.source_catalog["sources"]}

        commodity_mappings = []
        seen_commodity_codes: set[str] = set()
        for item in payload.get("commodityMappings", []):
            record = FoodVocabularyCrosswalkRecord.model_validate(item).model_dump(mode="json", by_alias=True)
            if record["commodityCode"] in seen_commodity_codes:
                raise DietaryRegistryError(
                    code="duplicate_food_vocabulary_mapping_entry",
                    message=f"Food vocabulary crosswalk duplicates commodity code {record['commodityCode']}.",
                    suggestion="Publish one food vocabulary mapping per canonical commodity code.",
                )
            if record["commodityCode"] not in known_commodities:
                raise DietaryRegistryError(
                    code="unknown_food_vocabulary_mapping_commodity",
                    message=f"Food vocabulary crosswalk references unknown commodity {record['commodityCode']}.",
                    suggestion="Use commodity codes that exist in defaults/v1/commodity_taxonomy.json.",
                )
            if record["sourceId"] not in known_sources:
                raise DietaryRegistryError(
                    code="unknown_food_vocabulary_mapping_source",
                    message=f"Food vocabulary crosswalk references unknown source {record['sourceId']}.",
                    suggestion="Reference a source id listed in defaults/v1/source_catalog.json.",
                )
            seen_commodity_codes.add(record["commodityCode"])
            commodity_mappings.append(record)

        processed_mappings = []
        seen_processed_codes: set[str] = set()
        seen_processed_aliases: dict[str, str] = {}
        for item in payload.get("processedCommodityMappings", []):
            record = ProcessedCommodityMappingRecord.model_validate(item).model_dump(mode="json", by_alias=True)
            if record["processedCommodityCode"] in seen_processed_codes:
                raise DietaryRegistryError(
                    code="duplicate_processed_commodity_mapping_entry",
                    message=(
                        f"Food vocabulary crosswalk duplicates processed commodity code "
                        f"{record['processedCommodityCode']}."
                    ),
                    suggestion="Publish one processed mapping per processed commodity code.",
                )
            if record["rawCommodityCode"] not in known_commodities:
                raise DietaryRegistryError(
                    code="unknown_processed_mapping_raw_commodity",
                    message=(
                        f"Processed commodity mapping references unknown raw commodity "
                        f"{record['rawCommodityCode']}."
                    ),
                    suggestion="Use raw commodity codes that exist in defaults/v1/commodity_taxonomy.json.",
                )
            if record["sourceId"] not in known_sources:
                raise DietaryRegistryError(
                    code="unknown_processed_mapping_source",
                    message=f"Processed commodity mapping references unknown source {record['sourceId']}.",
                    suggestion="Reference a source id listed in defaults/v1/source_catalog.json.",
                )
            normalized_inputs = {
                record["processedCommodityCode"].strip().lower(),
                *{alias.strip().lower() for alias in record.get("aliases", [])},
            }
            for normalized_input in normalized_inputs:
                existing = seen_processed_aliases.get(normalized_input)
                if existing is not None:
                    raise DietaryRegistryError(
                        code="ambiguous_processed_mapping_input",
                        message=(
                            f"Processed commodity input `{normalized_input}` maps to both {existing} and "
                            f"{record['processedCommodityCode']}."
                        ),
                        suggestion="Keep processed commodity codes and aliases unique across the crosswalk.",
                    )
                seen_processed_aliases[normalized_input] = record["processedCommodityCode"]
            seen_processed_codes.add(record["processedCommodityCode"])
            processed_mappings.append(record)

        applicability_records = []
        for item in payload.get("processingFactorApplicability", []):
            record = ProcessingFactorApplicabilityRecord.model_validate(item).model_dump(mode="json", by_alias=True)
            if record["rawCommodityCode"] not in known_commodities:
                raise DietaryRegistryError(
                    code="unknown_processing_factor_applicability_raw_commodity",
                    message=(
                        f"Processing-factor applicability references unknown raw commodity "
                        f"{record['rawCommodityCode']}."
                    ),
                    suggestion="Use raw commodity codes that exist in defaults/v1/commodity_taxonomy.json.",
                )
            if record["processedCommodityCode"] not in seen_processed_codes:
                raise DietaryRegistryError(
                    code="unknown_processing_factor_applicability_processed_commodity",
                    message=(
                        f"Processing-factor applicability references unknown processed commodity "
                        f"{record['processedCommodityCode']}."
                    ),
                    suggestion="Reference a processed commodity published in the same food vocabulary crosswalk pack.",
                )
            if record["sourceId"] not in known_sources:
                raise DietaryRegistryError(
                    code="unknown_processing_factor_applicability_source",
                    message=(
                        f"Processing-factor applicability references unknown source {record['sourceId']}."
                    ),
                    suggestion="Reference a source id listed in defaults/v1/source_catalog.json.",
                )
            applicability_records.append(record)

        return {
            "defaultsVersion": payload.get("defaultsVersion", DEFAULTS_VERSION),
            "kind": "food_vocabulary_crosswalk",
            "taxonomyId": payload.get("taxonomyId", self.taxonomy_id()),
            "commodityMappings": commodity_mappings,
            "processedCommodityMappings": processed_mappings,
            "processingFactorApplicability": applicability_records,
        }

    def _iter_extension_files(self, category: str) -> list[Path]:
        category_root = self.extensions_root / category
        if not category_root.exists():
            return []
        return sorted(category_root.glob("*.json"))

    def _load_mrl_enforcement_registry(self) -> dict[str, Any]:
        cache_key = self.version_root.resolve()
        if cache_key in _MRL_REGISTRY_CACHE:
            return _MRL_REGISTRY_CACHE[cache_key]

        merged = {"defaultsVersion": DEFAULTS_VERSION, "records": []}
        seen_record_ids: set[str] = set()
        known_sources = self._known_source_ids()
        for path in sorted(self.version_root.glob("mrl_enforcement*.json")):
            payload = _load_json(path)
            kind = payload.get("kind")
            validation_profile = payload.get("validationProfile")
            if kind not in (None, "mrl_enforcement"):
                raise DietaryRegistryError(
                    code="invalid_mrl_enforcement_pack_kind",
                    message=f"MRL enforcement pack {path.name} has an invalid kind field.",
                    suggestion="Use kind='mrl_enforcement' or omit kind.",
                )
            records = payload.get("records")
            if not isinstance(records, list):
                raise DietaryRegistryError(
                    code="invalid_mrl_enforcement_pack",
                    message=f"MRL enforcement pack {path.name} must define a records list.",
                    suggestion="Publish MRL enforcement packs with a top-level records array.",
                )
            for item in records:
                record = MrlEnforcementRecord.model_validate(item).model_dump(mode="json", by_alias=True)
                record_id = record["recordId"]
                if record_id in seen_record_ids:
                    raise DietaryRegistryError(
                        code="duplicate_mrl_enforcement_entry",
                        message=f"MRL enforcement pack duplicates existing record id {record_id}.",
                        suggestion="Assign one MRL enforcement record per record id.",
                    )
                seen_record_ids.add(record_id)
                unknown_sources = [source_id for source_id in record["sourceIds"] if source_id not in known_sources]
                if unknown_sources:
                    raise DietaryRegistryError(
                        code="unknown_mrl_source",
                        message=f"MRL enforcement record {record_id} references unknown sources: {unknown_sources}.",
                        suggestion="Reference source ids that exist in defaults/v1/source_catalog*.json.",
                    )
                if validation_profile in _OFFICIAL_PRIMARY_PROFILES:
                    self._validate_wave1_mrl_record(path, record)
                merged["records"].append(record)
        _MRL_REGISTRY_CACHE[cache_key] = merged
        return merged

    def _load_contaminant_legal_limits_registry(self) -> dict[str, Any]:
        merged = {"defaultsVersion": DEFAULTS_VERSION, "records": []}
        seen_record_ids: set[str] = set()
        known_sources = self._known_source_ids()
        known_legal_authorities = {item["authorityId"] for item in self.legal_authorities["authorities"]}
        for path in sorted(self.version_root.glob("contaminant_legal_limits*.json")):
            payload = _load_json(path)
            kind = payload.get("kind")
            validation_profile = payload.get("validationProfile")
            if kind not in (None, "contaminant_legal_limits"):
                raise DietaryRegistryError(
                    code="invalid_contaminant_legal_limits_pack_kind",
                    message=f"Contaminant legal-limits pack {path.name} has an invalid kind field.",
                    suggestion="Use kind='contaminant_legal_limits' or omit kind.",
                )
            records = payload.get("records")
            if not isinstance(records, list):
                raise DietaryRegistryError(
                    code="invalid_contaminant_legal_limits_pack",
                    message=f"Contaminant legal-limits pack {path.name} must define a records list.",
                    suggestion="Publish contaminant legal-limits packs with a top-level records array.",
                )
            for item in records:
                record = ContaminantLegalLimitRecord.model_validate(item).model_dump(mode="json", by_alias=True)
                record_id = record["recordId"]
                if record_id in seen_record_ids:
                    raise DietaryRegistryError(
                        code="duplicate_contaminant_legal_limit_record",
                        message=f"Contaminant legal-limits pack duplicates existing record id {record_id}.",
                        suggestion="Assign one contaminant legal-limit record per record id.",
                    )
                unknown_sources = [source_id for source_id in record["sourceIds"] if source_id not in known_sources]
                if unknown_sources:
                    raise DietaryRegistryError(
                        code="unknown_contaminant_legal_limit_source",
                        message=(
                            f"Contaminant legal-limit record {record_id} references unknown sources: "
                            f"{unknown_sources}."
                        ),
                        suggestion="Reference source ids that exist in defaults/v1/source_catalog*.json.",
                    )
                if record["legalAuthorityId"] not in known_legal_authorities:
                    raise DietaryRegistryError(
                        code="unknown_contaminant_legal_limit_legal_authority",
                        message=(
                            f"Contaminant legal-limit record {record_id} references unknown legal authority "
                            f"{record['legalAuthorityId']}."
                        ),
                        suggestion="Reference legal-authority ids that exist in defaults/v1/legal_authorities*.json.",
                    )
                for commodity_code in record["commodityCodes"]:
                    try:
                        self.get_food_vocabulary_mapping_record(commodity_code)
                    except DietaryRegistryError as exc:
                        raise DietaryRegistryError(
                            code="unknown_contaminant_legal_limit_commodity_code",
                            message=(
                                f"Contaminant legal-limit record {record_id} references unknown commodity code "
                                f"{commodity_code}."
                            ),
                            suggestion="Reference commodity codes published in the food-vocabulary manifest.",
                        ) from exc
                if validation_profile in _OFFICIAL_PRIMARY_PROFILES:
                    self._validate_official_primary_contaminant_legal_limit_record(path, record)
                seen_record_ids.add(record_id)
                merged["records"].append(record)
        return merged

    def _load_jurisdiction_coverage_registry(self) -> dict[str, Any]:
        merged = {"defaultsVersion": DEFAULTS_VERSION, "records": []}
        seen_record_ids: set[str] = set()
        known_sources = self._known_source_ids()
        known_legal_authorities = {item["authorityId"] for item in self.legal_authorities["authorities"]}
        known_reference_values = {item["recordId"] for item in self.reference_values["records"]}
        known_enforcement_records = {item["recordId"] for item in self.mrl_enforcement_registry["records"]}
        known_legal_limit_records = {item["recordId"] for item in self.contaminant_legal_limits["records"]}

        for path in sorted(self.version_root.glob("jurisdiction_coverage*.json")):
            payload = _load_json(path)
            kind = payload.get("kind")
            if kind not in (None, "jurisdiction_coverage"):
                raise DietaryRegistryError(
                    code="invalid_jurisdiction_coverage_pack_kind",
                    message=f"Jurisdiction-coverage pack {path.name} has an invalid kind field.",
                    suggestion="Use kind='jurisdiction_coverage' or omit kind.",
                )
            records = payload.get("records")
            if not isinstance(records, list):
                raise DietaryRegistryError(
                    code="invalid_jurisdiction_coverage_pack",
                    message=f"Jurisdiction-coverage pack {path.name} must define a records list.",
                    suggestion="Publish jurisdiction-coverage packs with a top-level records array.",
                )
            for item in records:
                record = JurisdictionCoverageRecord.model_validate(item).model_dump(mode="json", by_alias=True)
                record_id = record["coverageId"]
                if record_id in seen_record_ids:
                    raise DietaryRegistryError(
                        code="duplicate_jurisdiction_coverage_entry",
                        message=f"Jurisdiction-coverage pack duplicates existing record id {record_id}.",
                        suggestion="Assign one jurisdiction-coverage record per coverage id.",
                    )
                unknown_sources = [
                    source_id for source_id in record["officialSourceIds"] if source_id not in known_sources
                ]
                if unknown_sources:
                    raise DietaryRegistryError(
                        code="unknown_jurisdiction_coverage_source",
                        message=(
                            f"Jurisdiction-coverage record {record_id} references unknown source ids: {unknown_sources}."
                        ),
                        suggestion="Reference source ids that exist in defaults/v1/source_catalog*.json.",
                    )
                unknown_authorities = [
                    authority_id
                    for authority_id in record["legalAuthorityIds"]
                    if authority_id not in known_legal_authorities
                ]
                if unknown_authorities:
                    raise DietaryRegistryError(
                        code="unknown_jurisdiction_coverage_legal_authority",
                        message=(
                            f"Jurisdiction-coverage record {record_id} references unknown legal authority ids: "
                            f"{unknown_authorities}."
                        ),
                        suggestion="Reference legal authority ids that exist in defaults/v1/legal_authorities*.json.",
                    )
                unknown_reference_values = [
                    reference_id
                    for reference_id in record["referenceValueRecordIds"]
                    if reference_id not in known_reference_values
                ]
                if unknown_reference_values:
                    raise DietaryRegistryError(
                        code="unknown_jurisdiction_coverage_reference_value",
                        message=(
                            f"Jurisdiction-coverage record {record_id} references unknown reference-value ids: "
                            f"{unknown_reference_values}."
                        ),
                        suggestion="Reference record ids that exist in defaults/v1/reference_values*.json.",
                    )
                unknown_enforcement_records = [
                    enforcement_id
                    for enforcement_id in record["enforcementRecordIds"]
                    if enforcement_id not in known_enforcement_records
                ]
                if unknown_enforcement_records:
                    raise DietaryRegistryError(
                        code="unknown_jurisdiction_coverage_enforcement_record",
                        message=(
                            f"Jurisdiction-coverage record {record_id} references unknown enforcement record ids: "
                            f"{unknown_enforcement_records}."
                        ),
                        suggestion="Reference record ids that exist in defaults/v1/mrl_enforcement*.json.",
                    )
                unknown_legal_limit_records = [
                    legal_limit_id
                    for legal_limit_id in record["legalLimitRecordIds"]
                    if legal_limit_id not in known_legal_limit_records
                ]
                if unknown_legal_limit_records:
                    raise DietaryRegistryError(
                        code="unknown_jurisdiction_coverage_legal_limit_record",
                        message=(
                            f"Jurisdiction-coverage record {record_id} references unknown legal-limit record ids: "
                            f"{unknown_legal_limit_records}."
                        ),
                        suggestion="Reference record ids that exist in defaults/v1/contaminant_legal_limits*.json.",
                    )
                seen_record_ids.add(record_id)
                merged["records"].append(record)

        return merged

    def _load_substance_synonyms(self) -> dict[str, list[str]]:
        """Load substance synonym mappings and return a dict of canonical_key -> synonyms."""
        canonical_to_synonyms: dict[str, list[str]] = {}
        synonym_to_canonical: dict[str, str] = {}
        for path in sorted(self.version_root.glob("substance_synonyms*.json")):
            payload = _load_json(path)
            kind = payload.get("kind")
            if kind not in (None, "substance_synonyms"):
                raise DietaryRegistryError(
                    code="invalid_substance_synonyms_pack_kind",
                    message=f"Substance synonyms pack {path.name} has an invalid kind field.",
                    suggestion="Use kind='substance_synonyms' or omit kind.",
                )
            for entry in payload.get("entries", []):
                canonical = entry["canonicalKey"].lower()
                synonyms = [s.lower() for s in entry.get("synonyms", [])]
                for synonym in synonyms:
                    existing = synonym_to_canonical.get(synonym)
                    if existing is not None and existing != canonical:
                        raise DietaryRegistryError(
                            code="duplicate_substance_synonym",
                            message=(
                                f"Substance synonym `{synonym}` is assigned to both {existing} and {canonical}."
                            ),
                            suggestion="Keep synonym aliases unique across substance_synonyms packs.",
                        )
                    synonym_to_canonical[synonym] = canonical
                canonical_to_synonyms.setdefault(canonical, []).extend(synonyms)
        return canonical_to_synonyms

    def resolve_substance_key(self, name: str) -> str | None:
        """Resolve a substance name to its canonical key using exact match or synonym lookup."""
        normalized = name.lower()
        # Exact match against a canonical key
        if normalized in self.substance_synonyms:
            return normalized
        # Exact match against a known synonym
        for canonical, synonyms in self.substance_synonyms.items():
            if normalized in synonyms:
                return canonical
        return None

    def _load_composition_recipes_registry(self) -> dict[str, Any]:
        merged = {"defaultsVersion": DEFAULTS_VERSION, "records": []}
        seen_record_ids: set[str] = set()
        known_sources = self._known_source_ids()
        known_commodities = {item["commodityCode"] for item in self.commodity_taxonomy["commodities"]}
        for path in sorted(self.version_root.glob("composition_recipes*.json")):
            payload = _load_json(path)
            kind = payload.get("kind")
            if kind not in (None, "composition_recipes"):
                raise DietaryRegistryError(
                    code="invalid_composition_recipes_pack_kind",
                    message=f"Composition recipes pack {path.name} has an invalid kind field.",
                    suggestion="Use kind='composition_recipes' or omit kind.",
                )
            records = payload.get("records")
            if not isinstance(records, list):
                raise DietaryRegistryError(
                    code="invalid_composition_recipes_pack",
                    message=f"Composition recipes pack {path.name} must define a records list.",
                    suggestion="Publish composition recipes packs with a top-level records array.",
                )
            for item in records:
                record = CompositionRecipeRecord.model_validate(item).model_dump(mode="json", by_alias=True)
                record_id = record["recipeId"]
                if record_id in seen_record_ids:
                    raise DietaryRegistryError(
                        code="duplicate_composition_recipes_entry",
                        message=f"Composition recipes pack duplicates existing record id {record_id}.",
                        suggestion="Assign one composition recipes record per record id.",
                    )
                seen_record_ids.add(record_id)
                unknown_sources = [source_id for source_id in record["sourceIds"] if source_id not in known_sources]
                if unknown_sources:
                    raise DietaryRegistryError(
                        code="unknown_recipe_source",
                        message=f"Composition recipes record {record_id} references unknown sources: {unknown_sources}.",
                        suggestion="Reference source ids that exist in defaults/v1/source_catalog*.json.",
                    )
                if record["compositeCommodityCode"] not in known_commodities:
                    raise DietaryRegistryError(
                        code="unknown_recipe_composite_commodity",
                        message=(
                            f"Composition recipes record {record_id} references unknown composite commodity "
                            f"{record['compositeCommodityCode']}."
                        ),
                        suggestion="Use composite commodity codes that exist in defaults/v1/commodity_taxonomy.json.",
                    )
                unknown_components = [
                    component["commodityCode"]
                    for component in record["components"]
                    if component["commodityCode"] not in known_commodities
                ]
                if unknown_components:
                    raise DietaryRegistryError(
                        code="unknown_recipe_component_commodity",
                        message=(
                            f"Composition recipes record {record_id} references unknown component commodities: "
                            f"{sorted(set(unknown_components))}."
                        ),
                        suggestion="Use component commodity codes that exist in defaults/v1/commodity_taxonomy.json.",
                    )
                merged["records"].append(record)
        return merged

    def _apply_extensions(self) -> None:
        for path in self._iter_extension_files("commodity_taxonomy"):
            payload = _load_json(path)
            if payload.get("kind") != "commodity_taxonomy":
                raise DietaryRegistryError(
                    code="invalid_taxonomy_extension_kind",
                    message=f"Taxonomy extension {path.name} has an invalid kind field.",
                    suggestion="Use kind='commodity_taxonomy' for taxonomy extension packs.",
                )
            for entry in payload.get("commodities", []):
                if any(
                    existing["commodityCode"] == entry["commodityCode"]
                    for existing in self.commodity_taxonomy["commodities"]
                ):
                    raise DietaryRegistryError(
                        code="duplicate_taxonomy_extension_entry",
                        message=f"Commodity extension duplicates existing code {entry['commodityCode']}.",
                        suggestion="Extension packs must add new commodity codes without overriding the base pack.",
                    )
                self.commodity_taxonomy["commodities"].append(entry)

        for path in self._iter_extension_files("consumption_profiles"):
            payload = _load_json(path)
            if payload.get("kind") != "consumption_profiles":
                raise DietaryRegistryError(
                    code="invalid_profile_extension_kind",
                    message=f"Consumption-profile extension {path.name} has an invalid kind field.",
                    suggestion="Use kind='consumption_profiles' for profile extension packs.",
                )
            for profile in payload.get("profiles", []):
                if any(
                    existing["profileId"] == profile["profileId"]
                    for existing in self.consumption_profiles["profiles"]
                ):
                    raise DietaryRegistryError(
                        code="duplicate_profile_extension_entry",
                        message=f"Consumption-profile extension duplicates existing id {profile['profileId']}.",
                        suggestion="Extension packs must add new profile ids without overriding the base pack.",
                    )
                self.consumption_profiles["profiles"].append(profile)

        for path in self._iter_extension_files("reporting_profiles"):
            payload = _load_json(path)
            if payload.get("kind") != "reporting_profiles":
                raise DietaryRegistryError(
                    code="invalid_reporting_profile_extension_kind",
                    message=f"Reporting-profile extension {path.name} has an invalid kind field.",
                    suggestion="Use kind='reporting_profiles' for reporting-profile extension packs.",
                )
            known_sources = self._known_source_ids()
            known_legal_authority_ids = {item["authorityId"] for item in self.legal_authorities["authorities"]}
            known_reference_value_ids = {item["recordId"] for item in self.reference_values["records"]}
            known_profile_ids = {item["profileId"] for item in self.reporting_profiles["profiles"]}
            for item in payload.get("profiles", []):
                profile = ReportingProfileRecord.model_validate(item).model_dump(mode="json", by_alias=True)
                if any(
                    existing["profileId"] == profile["profileId"]
                    for existing in self.reporting_profiles["profiles"]
                ):
                    raise DietaryRegistryError(
                        code="duplicate_reporting_profile_extension_entry",
                        message=f"Reporting-profile extension duplicates existing id {profile['profileId']}.",
                        suggestion="Extension packs must add new profile ids without overriding the base pack.",
                    )
                unknown_sources = [
                    source_id for source_id in profile["sourceIds"] if source_id not in known_sources
                ]
                if unknown_sources:
                    raise DietaryRegistryError(
                        code="unknown_reporting_profile_extension_source",
                        message=(
                            f"Reporting-profile extension {profile['profileId']} references unknown sources: "
                            f"{unknown_sources}."
                        ),
                        suggestion="Reference source ids that exist in defaults/v1/source_catalog*.json.",
                    )
                unknown_legal_authorities = [
                    authority_id
                    for authority_id in profile["legalAuthorityIds"]
                    if authority_id not in known_legal_authority_ids
                ]
                if unknown_legal_authorities:
                    raise DietaryRegistryError(
                        code="unknown_reporting_profile_extension_legal_authority",
                        message=(
                            f"Reporting-profile extension {profile['profileId']} references unknown legal authorities: "
                            f"{unknown_legal_authorities}."
                        ),
                        suggestion="Reference legal-authority ids that exist in defaults/v1/legal_authorities.json.",
                    )
                unknown_reference_values = [
                    reference_value_id
                    for reference_value_id in profile["referenceValueRecordIds"]
                    if reference_value_id not in known_reference_value_ids
                ]
                if unknown_reference_values:
                    raise DietaryRegistryError(
                        code="unknown_reporting_profile_extension_reference_value",
                        message=(
                            f"Reporting-profile extension {profile['profileId']} references unknown reference values: "
                            f"{unknown_reference_values}."
                        ),
                        suggestion="Reference record ids that exist in defaults/v1/reference_values.json.",
                    )
                unknown_profile_refs = [
                    other_profile_id
                    for other_profile_id in profile["notSubstitutableForProfileIds"]
                    if other_profile_id not in known_profile_ids
                ]
                if unknown_profile_refs:
                    raise DietaryRegistryError(
                        code="unknown_reporting_profile_extension_reference",
                        message=(
                            f"Reporting-profile extension {profile['profileId']} references unknown profile ids: "
                            f"{unknown_profile_refs}."
                        ),
                        suggestion="Reference reporting profile ids already published in the base or earlier extension packs.",
                    )
                self.reporting_profiles["profiles"].append(profile)
                known_profile_ids.add(profile["profileId"])

    def parameter_record(self, parameter: str) -> dict[str, Any]:
        try:
            return self.core_defaults["parameters"][parameter]
        except KeyError as exc:
            raise DietaryRegistryError(
                code="missing_default_parameter",
                message=f"Unknown default parameter: {parameter}",
                suggestion="Check defaults/v1/core_defaults.json or add the missing parameter.",
            ) from exc

    def parameter_value(self, parameter: str) -> float:
        return float(self.parameter_record(parameter)["value"])

    def parameter_source_reference(self, parameter: str) -> SourceReference:
        record = self.parameter_record(parameter)
        return SourceReference(
            source_id=record["sourceId"],
            title=record["title"],
            effective_date=record.get("effectiveDate"),
            url=record.get("sourceUrl"),
            origin_tag=SourceOriginTag.INTERNAL_OPERATIONAL,
        )

    def taxonomy_source_reference(self, commodity_entry: dict[str, Any]) -> SourceReference:
        catalog_record = self._source_catalog_record_or_none(commodity_entry["sourceId"])
        if catalog_record is not None:
            return self.source_catalog_reference(commodity_entry["sourceId"])
        return SourceReference(
            source_id=commodity_entry["sourceId"],
            title=f"Commodity taxonomy entry for {commodity_entry['canonicalName']}",
            effective_date=None,
            url=commodity_entry.get("sourceUrl"),
            origin_tag=SourceOriginTag.CURATED_DERIVED,
        )

    def _base_food_vocabulary_mapping(self, commodity_code: str) -> dict[str, Any] | None:
        for item in self.food_vocabulary_crosswalk["commodityMappings"]:
            if item["commodityCode"] == commodity_code:
                return item
        return None

    def _processed_mapping_for_input(self, input_code: str) -> dict[str, Any] | None:
        normalized = input_code.strip().lower()
        for item in self.food_vocabulary_crosswalk["processedCommodityMappings"]:
            aliases = {alias.lower() for alias in item.get("aliases", [])}
            if normalized == item["processedCommodityCode"].lower() or normalized in aliases:
                return item
        return None

    def _processing_factor_applicability_for_processed(self, processed_commodity_code: str) -> dict[str, Any] | None:
        for item in self.food_vocabulary_crosswalk["processingFactorApplicability"]:
            if item["processedCommodityCode"] == processed_commodity_code:
                return item
        return None

    def _commodity_reference_from_entry(
        self,
        entry: dict[str, Any],
        input_code: str,
        *,
        source_reference: SourceReference,
        food_mapping: dict[str, Any] | None = None,
    ) -> CommodityReference:
        return CommodityReference(
            taxonomy_id=self.taxonomy_id(),
            commodity_code=entry["commodityCode"],
            canonical_name=entry["canonicalName"],
            food_group=food_mapping.get("foodGroup", entry["foodGroup"]) if food_mapping else entry["foodGroup"],
            mapping_status=entry["mappingStatus"],
            foodex2_code=food_mapping.get("foodex2Code") if food_mapping else None,
            rpc_code=food_mapping.get("rpcCode") if food_mapping else None,
            rpcd_code=food_mapping.get("rpcdCode") if food_mapping else None,
            processed_status=food_mapping.get("processedStatus") if food_mapping else None,
            mapping_confidence=food_mapping.get("mappingConfidence") if food_mapping else None,
            matched_input_code=input_code,
            source_reference=source_reference,
        )

    def taxonomy_id(self) -> str:
        return self.commodity_taxonomy["taxonomyId"]

    def list_commodity_entries(self) -> list[dict[str, Any]]:
        return list(self.commodity_taxonomy["commodities"])

    def resolve_commodity(self, input_code: str) -> CommodityResolution:
        normalized = input_code.strip().lower()
        for entry in self.list_commodity_entries():
            canonical = entry["commodityCode"].lower()
            aliases = {alias.lower() for alias in entry.get("aliases", [])}
            food_mapping = self._base_food_vocabulary_mapping(entry["commodityCode"])
            reference = self.source_catalog_reference(food_mapping["sourceId"]) if food_mapping else self.taxonomy_source_reference(entry)
            if normalized == canonical:
                return CommodityResolution(
                    commodity=self._commodity_reference_from_entry(
                        entry,
                        input_code,
                        source_reference=reference,
                        food_mapping=food_mapping,
                    ),
                    source_classification=SourceClassification.USER_INPUT,
                    quality_flags=[],
                )
            if normalized in aliases:
                quality_flags = []
                if entry["mappingStatus"] == "heuristic":
                    quality_flags.append(
                        QualityFlag(
                            code="heuristic_alias_mapping",
                            severity=Severity.WARNING,
                            message=f"Commodity alias {input_code} was matched heuristically to {entry['commodityCode']}.",
                        )
                    )
                return CommodityResolution(
                    commodity=self._commodity_reference_from_entry(
                        entry,
                        input_code,
                        source_reference=reference,
                        food_mapping=food_mapping,
                    ),
                    source_classification=SourceClassification.MAPPED,
                    quality_flags=quality_flags,
                )
        processed_mapping = self._processed_mapping_for_input(input_code)
        if processed_mapping:
            for entry in self.list_commodity_entries():
                if entry["commodityCode"] != processed_mapping["rawCommodityCode"]:
                    continue
                quality_flags = [
                    QualityFlag(
                        code="processed_derivative_mapping",
                        severity=Severity.INFO,
                        message=(
                            f"Processed commodity {input_code} was mapped to raw primary commodity "
                            f"{processed_mapping['rawCommodityCode']} with derivative metadata retained."
                        ),
                    )
                ]
                if processed_mapping["mappingConfidence"] == "heuristic":
                    quality_flags.append(
                        QualityFlag(
                            code="heuristic_processed_mapping",
                            severity=Severity.WARNING,
                            message=(
                                f"Processed commodity {input_code} was matched heuristically to "
                                f"{processed_mapping['processedCommodityCode']}."
                            ),
                        )
                    )
                return CommodityResolution(
                    commodity=self._commodity_reference_from_entry(
                        entry,
                        input_code,
                        source_reference=self.source_catalog_reference(processed_mapping["sourceId"]),
                        food_mapping=processed_mapping,
                    ),
                    source_classification=SourceClassification.MAPPED,
                    quality_flags=quality_flags,
                )
        raise DietaryRegistryError(
            code="unknown_commodity_code",
            message=f"Unsupported commodity code: {input_code}",
            suggestion="Use a commodity listed in defaults/v1/commodity_taxonomy.json.",
        )

    def default_processing_factor(self, commodity_code: str) -> tuple[float, SourceReference]:
        processed_mapping = self._processed_mapping_for_input(commodity_code)
        if processed_mapping:
            applicability = self._processing_factor_applicability_for_processed(
                processed_mapping["processedCommodityCode"]
            )
            if applicability and applicability.get("applicability") == "supported":
                factor = applicability.get("recommendedProcessingFactor")
                if factor is not None:
                    return float(factor), self.source_catalog_reference(applicability["sourceId"])
            if processed_mapping.get("defaultProcessingFactor") is not None:
                return float(processed_mapping["defaultProcessingFactor"]), self.source_catalog_reference(
                    processed_mapping["sourceId"]
                )

        resolution = self.resolve_commodity(commodity_code)
        for entry in self.list_commodity_entries():
            if entry["commodityCode"] == resolution.commodity.commodity_code:
                if entry.get("defaultProcessingFactor") is not None:
                    return float(entry["defaultProcessingFactor"]), self.taxonomy_source_reference(entry)
        return self.parameter_value("default_processing_factor"), self.parameter_source_reference(
            "default_processing_factor"
        )

    def get_consumption_profile_record(self, profile_id: str) -> dict[str, Any]:
        for profile in self.consumption_profiles["profiles"]:
            if profile["profileId"] == profile_id:
                return profile
        raise DietaryRegistryError(
            code="unknown_consumption_profile",
            message=f"Unknown consumption profile: {profile_id}",
            suggestion="Use a profile listed in the governed consumption-profile manifests.",
        )

    def select_consumption_profile_record(
        self,
        region_id: str,
        population_group: str,
        intake_window: IntakeWindowSemantic,
        preferred_profile_id: str | None = None,
    ) -> dict[str, Any]:
        profiles = self.consumption_profiles["profiles"]
        if preferred_profile_id:
            record = self.get_consumption_profile_record(preferred_profile_id)
            if record["regionId"] != region_id or record["populationGroup"] != population_group:
                raise DietaryRegistryError(
                    code="consumption_profile_scope_mismatch",
                    message="Preferred profile does not match the requested region and population group.",
                    suggestion="Choose a compatible profile or omit preferred_profile_id.",
                )
            if intake_window.value not in record["applicableWindows"]:
                raise DietaryRegistryError(
                    code="consumption_profile_window_mismatch",
                    message="Preferred profile does not support the requested intake window.",
                    suggestion="Choose a compatible intake window or profile.",
                )
            return record

        for profile in profiles:
            if (
                profile["regionId"] == region_id
                and profile["populationGroup"] == population_group
                and intake_window.value in profile["applicableWindows"]
            ):
                return profile
        raise DietaryRegistryError(
            code="missing_consumption_profile",
            message=f"No consumption profile found for {population_group} in {region_id}.",
            suggestion="Add a compatible consumption-profile pack or change the requested population/window combination.",
        )

    def profile_source_reference(self, profile: dict[str, Any]) -> SourceReference:
        catalog_record = self._source_catalog_record_or_none(profile["sourceId"])
        if catalog_record is not None:
            return self.source_catalog_reference(profile["sourceId"])
        return SourceReference(
            source_id=profile["sourceId"],
            title=profile["sourceTitle"],
            effective_date=profile.get("effectiveDate"),
            url=profile.get("sourceUrl"),
            origin_tag=SourceOriginTag.CURATED_DERIVED,
        )

    def _source_catalog_record_or_none(self, source_id: str) -> dict[str, Any] | None:
        for source in self.source_catalog["sources"]:
            if source["sourceId"] == source_id:
                return source
        return None

    def get_source_catalog_record(self, source_id: str) -> dict[str, Any]:
        record = self._source_catalog_record_or_none(source_id)
        if record is not None:
            return record
        raise DietaryRegistryError(
            code="unknown_source_catalog_record",
            message=f"Unknown source catalog record: {source_id}",
            suggestion="Use a source listed in the source-catalog manifest.",
        )

    def source_catalog_reference(self, source_id: str) -> SourceReference:
        record = self.get_source_catalog_record(source_id)
        return SourceReference(
            source_id=record["sourceId"],
            title=record["title"],
            effective_date=record.get("effectiveDate"),
            url=record.get("url"),
            origin_tag=record.get("originTag"),
        )

    def assess_source_currency(
        self,
        *,
        source_ids: list[str],
        data_period: str | None = None,
    ) -> SourceCurrencyAssessment:
        reference_date = date.today()
        historical_cutoff_year = reference_date.year - _SOURCE_CURRENCY_REVIEW_AGE_YEARS
        period_years = _extract_years(data_period)
        data_period_end_year = max(period_years) if period_years else None
        historical_data_period = (
            data_period_end_year is not None and data_period_end_year <= historical_cutoff_year
        )

        historical_source_ids: list[str] = []
        current_context_source_ids: list[str] = []
        for source_id in sorted(set(source_ids)):
            payload = self._source_catalog_record_or_none(source_id)
            if payload is None:
                continue
            record = RegulatorySourceRecord.model_validate(payload)
            if record.effective_date is None:
                continue
            if record.regulatory_role == RegulatoryRole.BINDING:
                current_context_source_ids.append(record.source_id)
                continue
            if record.effective_date.year <= historical_cutoff_year:
                historical_source_ids.append(record.source_id)
            else:
                current_context_source_ids.append(record.source_id)

        notes: list[str] = []
        if historical_data_period and data_period_end_year is not None:
            notes.append(
                f"Data period `{data_period}` ends in {data_period_end_year} and should be treated as historical relative to {reference_date.isoformat()}."
            )
        if historical_source_ids and current_context_source_ids:
            notes.append(
                "Supporting sources mix historical anchors "
                f"({', '.join(historical_source_ids)}) with newer context records ({', '.join(current_context_source_ids)}); confirm the older evidence base is still fit for the intended use."
            )
        elif historical_source_ids:
            notes.append(
                f"Supporting sources are historical as of {reference_date.isoformat()}: {', '.join(historical_source_ids)}."
            )

        return SourceCurrencyAssessment(
            reference_date=reference_date,
            data_period=data_period,
            historical_data_period=historical_data_period,
            data_period_end_year=data_period_end_year,
            historical_source_ids=tuple(historical_source_ids),
            current_context_source_ids=tuple(current_context_source_ids),
            notes=tuple(notes),
            review_required=historical_data_period or (
                bool(historical_source_ids) and not bool(current_context_source_ids)
            ),
        )

    def get_model_governance_record(self, model_family: str) -> dict[str, Any]:
        for family in self.model_governance["families"]:
            if family["modelFamily"] == model_family:
                return family
        raise DietaryRegistryError(
            code="unknown_model_governance_record",
            message=f"Unknown model governance record: {model_family}",
            suggestion="Use a model family listed in the model-governance manifest.",
        )

    def get_regulatory_readiness_profile_record(self, profile_id: str) -> dict[str, Any]:
        for profile in self.regulatory_readiness_profiles["profiles"]:
            if profile["profileId"] == profile_id:
                return profile
        raise DietaryRegistryError(
            code="unknown_regulatory_readiness_profile",
            message=f"Unknown regulatory readiness profile: {profile_id}",
            suggestion="Use a profile listed in the regulatory readiness profiles manifest.",
        )

    def list_reference_value_records(self) -> list[dict[str, Any]]:
        return list(self.reference_values["records"])

    def get_reference_value_record(self, record_id: str) -> dict[str, Any]:
        for record in self.reference_values["records"]:
            if record["recordId"] == record_id:
                return record
        raise DietaryRegistryError(
            code="unknown_reference_value_record",
            message=f"Unknown reference-value record: {record_id}",
            suggestion="Use a record listed in the reference-values manifest.",
        )

    def list_contaminant_legal_limit_records(self) -> list[dict[str, Any]]:
        return list(self.contaminant_legal_limits["records"])

    def get_contaminant_legal_limit_record(self, record_id: str) -> dict[str, Any]:
        for record in self.contaminant_legal_limits["records"]:
            if record["recordId"] == record_id:
                return record
        raise DietaryRegistryError(
            code="unknown_contaminant_legal_limit_record",
            message=f"Unknown contaminant legal-limit record: {record_id}",
            suggestion="Use a record listed in the contaminant-legal-limits manifest.",
        )

    def get_contaminant_legal_limit_records(
        self,
        *,
        jurisdiction: str | None = None,
        contaminant_family: str | None = None,
        substance_key: str | None = None,
    ) -> list[dict[str, Any]]:
        normalized_jurisdiction = jurisdiction.strip().lower() if jurisdiction is not None else None
        normalized_family = contaminant_family.strip().lower() if contaminant_family is not None else None
        normalized_substance = substance_key.strip().lower() if substance_key is not None else None
        records = []
        for item in self.contaminant_legal_limits["records"]:
            if normalized_jurisdiction and item["jurisdiction"].strip().lower() != normalized_jurisdiction:
                continue
            if normalized_family and item["contaminantFamily"].strip().lower() != normalized_family:
                continue
            if normalized_substance and item["substanceKey"].strip().lower() != normalized_substance:
                continue
            records.append(item)
        return records

    def list_consumption_dataset_records(self) -> list[dict[str, Any]]:
        return list(self.consumption_datasets["datasets"])

    def get_consumption_dataset_record(self, dataset_id: str) -> dict[str, Any]:
        for record in self.consumption_datasets["datasets"]:
            if record["datasetId"] == dataset_id:
                return record
        raise DietaryRegistryError(
            code="unknown_consumption_dataset_record",
            message=f"Unknown consumption-dataset record: {dataset_id}",
            suggestion="Use a dataset listed in the consumption-datasets manifest.",
        )

    def _build_mrl_index(self) -> None:
        for record in self.mrl_enforcement_registry.get("records", []):
            sk = record["substanceKey"].lower()
            cc = record["commodityCode"].lower()
            jc = record["jurisdiction"].lower()
            key = (sk, cc, jc)
            existing = self._mrl_index.get(key)
            if existing is not None:
                raise DietaryRegistryError(
                    code="duplicate_active_mrl_enforcement_record",
                    message=(
                        "Multiple active MRL enforcement records were found for "
                        f"{record['substanceKey']}/{record['commodityCode']}/{record['jurisdiction']}."
                    ),
                    suggestion="Keep one active MRL enforcement record per substance/commodity/jurisdiction key.",
                )
            self._mrl_index[key] = record
            self._mrl_by_record_id_index[record["recordId"]] = record
            sc_key = (sk, cc)
            self._mrl_by_sc_index.setdefault(sc_key, []).append(record)

    def get_mrl_record(self, substance_key: str, commodity_code: str, jurisdiction: str) -> dict[str, Any] | None:
        return self._mrl_index.get((substance_key.lower(), commodity_code.lower(), jurisdiction.lower()))

    def get_mrl_enforcement_record(self, record_id: str) -> dict[str, Any]:
        record = self._mrl_by_record_id_index.get(record_id)
        if record is None:
            raise DietaryRegistryError(
                code="unknown_mrl_enforcement_record",
                message=f"Unknown MRL enforcement record: {record_id}",
                suggestion="Use a record id listed in defaults/v1/mrl_enforcement*.json.",
            )
        return record

    def list_mrl_records_by_substance_commodity(self, substance_key: str, commodity_code: str) -> list[dict[str, Any]]:
        return list(self._mrl_by_sc_index.get((substance_key.lower(), commodity_code.lower()), []))

    def list_mrl_enforcement_records(self) -> list[dict[str, Any]]:
        return list(self.mrl_enforcement_registry.get("records", []))

    def list_composition_recipes_records(self) -> list[dict[str, Any]]:
        return list(self.composition_recipes_registry.get("records", []))

    def list_method_registry_records(self) -> list[dict[str, Any]]:
        return list(self.method_registry["methods"])

    def get_method_registry_record(self, method_id: str) -> dict[str, Any]:
        for record in self.method_registry["methods"]:
            if record["methodId"] == method_id:
                return record
        raise DietaryRegistryError(
            code="unknown_method_registry_record",
            message=f"Unknown method-registry record: {method_id}",
            suggestion="Use a method listed in the method-registry manifest.",
        )

    def list_legal_authority_records(self) -> list[dict[str, Any]]:
        return list(self.legal_authorities["authorities"])

    def get_legal_authority_record(self, authority_id: str) -> dict[str, Any]:
        for record in self.legal_authorities["authorities"]:
            if record["authorityId"] == authority_id:
                return record
        raise DietaryRegistryError(
            code="unknown_legal_authority_record",
                message=f"Unknown legal-authority record: {authority_id}",
                suggestion="Use a legal authority listed in the legal-authorities manifest.",
            )

    def list_reporting_profile_records(self) -> list[dict[str, Any]]:
        return list(self.reporting_profiles["profiles"])

    def get_reporting_profile_record(self, profile_id: str) -> dict[str, Any]:
        for record in self.reporting_profiles["profiles"]:
            if record["profileId"] == profile_id:
                return record
        raise DietaryRegistryError(
            code="unknown_reporting_profile_record",
            message=f"Unknown reporting profile record: {profile_id}",
            suggestion="Use a profile listed in the reporting-profiles manifest.",
        )

    def get_reporting_profile_records_for_family(self, family_id: str) -> list[dict[str, Any]]:
        records = [record for record in self.reporting_profiles["profiles"] if record["contaminantFamily"] == family_id]
        if not records:
            raise DietaryRegistryError(
                code="unknown_reporting_profile_family",
                message=f"Unknown reporting-profile family: {family_id}",
                suggestion="Use a family listed in the reporting-profiles manifest.",
            )
        return records

    def list_metals_occurrence_records(self) -> list[dict[str, Any]]:
        return list(self.metals_occurrence_registry["records"])

    def get_metals_occurrence_record(self, record_id: str) -> dict[str, Any]:
        for record in self.metals_occurrence_registry["records"]:
            if record["recordId"] == record_id:
                return record
        raise DietaryRegistryError(
            code="unknown_metals_occurrence_record",
            message=f"Unknown metals-occurrence record: {record_id}",
            suggestion="Use a record listed in the metals-occurrence manifest.",
        )

    def get_metals_occurrence_records_for_family(self, family_id: str) -> list[dict[str, Any]]:
        records = [record for record in self.metals_occurrence_registry["records"] if record["contaminantFamily"] == family_id]
        if not records:
            raise DietaryRegistryError(
                code="unknown_metals_occurrence_family",
                message=f"Unknown metals-occurrence family: {family_id}",
                suggestion="Use a family listed in the metals-occurrence manifest.",
            )
        return records

    def list_metals_review_focus_records(self) -> list[dict[str, Any]]:
        return list(self.metals_review_focus_registry["records"])

    def get_metals_review_focus_record(self, focus_id: str) -> dict[str, Any]:
        for record in self.metals_review_focus_registry["records"]:
            if record["focusId"] == focus_id:
                return record
        raise DietaryRegistryError(
            code="unknown_metals_review_focus_record",
            message=f"Unknown metals-review-focus record: {focus_id}",
            suggestion="Use a record listed in the metals-review-focus manifest.",
        )

    def get_metals_review_focus_records_for_family(self, family_id: str) -> list[dict[str, Any]]:
        records = [record for record in self.metals_review_focus_registry["records"] if record["contaminantFamily"] == family_id]
        if not records:
            raise DietaryRegistryError(
                code="unknown_metals_review_focus_family",
                message=f"Unknown metals-review-focus family: {family_id}",
                suggestion="Use a family listed in the metals-review-focus manifest.",
            )
        return records

    def list_occurrence_evidence_records(self) -> list[dict[str, Any]]:
        return list(self.occurrence_evidence_registry["records"])

    def get_occurrence_evidence_record(self, record_id: str) -> dict[str, Any]:
        for record in self.occurrence_evidence_registry["records"]:
            if record["recordId"] == record_id:
                return record
        raise DietaryRegistryError(
            code="unknown_occurrence_evidence_record",
            message=f"Unknown occurrence-evidence record: {record_id}",
            suggestion="Use a record listed in the occurrence-evidence manifest.",
        )

    def get_occurrence_evidence_records_for_family(self, family_id: str) -> list[dict[str, Any]]:
        records = [record for record in self.occurrence_evidence_registry["records"] if record["contaminantFamily"] == family_id]
        if not records:
            raise DietaryRegistryError(
                code="unknown_occurrence_evidence_family",
                message=f"Unknown occurrence-evidence family: {family_id}",
                suggestion="Use a family listed in the occurrence-evidence manifest.",
            )
        return records

    def list_analytical_method_evidence_records(self) -> list[dict[str, Any]]:
        return list(self.analytical_method_evidence_registry["records"])

    def get_analytical_method_evidence_record(self, record_id: str) -> dict[str, Any]:
        for record in self.analytical_method_evidence_registry["records"]:
            if record["recordId"] == record_id:
                return record
        raise DietaryRegistryError(
            code="unknown_analytical_method_evidence_record",
            message=f"Unknown analytical-method-evidence record: {record_id}",
            suggestion="Use a record listed in the analytical-method-evidence manifest.",
        )

    def get_analytical_method_evidence_records_for_family(self, family_id: str) -> list[dict[str, Any]]:
        records = [
            record
            for record in self.analytical_method_evidence_registry["records"]
            if record["contaminantFamily"] == family_id
        ]
        if not records:
            raise DietaryRegistryError(
                code="unknown_analytical_method_evidence_family",
                message=f"Unknown analytical-method-evidence family: {family_id}",
                suggestion="Use a family listed in the analytical-method-evidence manifest.",
            )
        return records

    def list_emerging_contaminant_records(self) -> list[dict[str, Any]]:
        return list(self.emerging_contaminants["families"])

    def get_emerging_contaminant_record(self, family_id: str) -> dict[str, Any]:
        for record in self.emerging_contaminants["families"]:
            if record["familyId"] == family_id:
                return record
        raise DietaryRegistryError(
            code="unknown_emerging_contaminant_record",
            message=f"Unknown emerging-contaminant record: {family_id}",
            suggestion="Use a family listed in the emerging-contaminants manifest.",
        )

    def build_manifest(self) -> dict[str, Any]:
        files = sorted(self.version_root.glob("*.json"))
        if self.extensions_root.exists():
            files.extend(sorted(self.extensions_root.rglob("*.json")))
        return {
            "defaultsVersion": DEFAULTS_VERSION,
            "files": [
                {
                    "path": str(path.relative_to(self.repo_root)),
                    "sha256": _sha256(path),
                    "defaultsVersion": _load_json(path).get("defaultsVersion", DEFAULTS_VERSION),
                }
                for path in files
            ],
        }

    def consumption_profiles_manifest(self) -> dict[str, Any]:
        return {
            "defaultsVersion": DEFAULTS_VERSION,
            "profiles": [
                {
                    "profileId": profile["profileId"],
                    "displayName": profile["displayName"],
                    "regionId": profile["regionId"],
                    "populationGroup": profile["populationGroup"],
                    "applicableWindows": profile["applicableWindows"],
                    "profileFamily": profile.get("profileFamily"),
                    "regulatoryBasis": profile.get("regulatoryBasis"),
                    "reviewStatus": profile.get("reviewStatus"),
                }
                for profile in self.consumption_profiles["profiles"]
            ],
        }

    def source_catalog_manifest(self) -> dict[str, Any]:
        return self.source_catalog

    def reference_values_manifest(self) -> dict[str, Any]:
        return self.reference_values

    def contaminant_legal_limits_manifest(self) -> dict[str, Any]:
        return self.contaminant_legal_limits

    def mrl_enforcement_manifest(self) -> dict[str, Any]:
        return self.mrl_enforcement_registry

    def consumption_datasets_manifest(self) -> dict[str, Any]:
        return self.consumption_datasets

    def method_registry_manifest(self) -> dict[str, Any]:
        return self.method_registry

    def legal_authorities_manifest(self) -> dict[str, Any]:
        return self.legal_authorities

    def reporting_profiles_manifest(self) -> dict[str, Any]:
        return self.reporting_profiles

    def metals_occurrence_manifest(self) -> dict[str, Any]:
        return self.metals_occurrence_registry

    def metals_review_focus_manifest(self) -> dict[str, Any]:
        return self.metals_review_focus_registry

    def occurrence_evidence_manifest(self) -> dict[str, Any]:
        return self.occurrence_evidence_registry

    def analytical_method_evidence_manifest(self) -> dict[str, Any]:
        return self.analytical_method_evidence_registry

    def emerging_contaminants_manifest(self) -> dict[str, Any]:
        return self.emerging_contaminants

    def jurisdiction_coverage_manifest(self) -> dict[str, Any]:
        return self.jurisdiction_coverage_registry

    def model_governance_manifest(self) -> dict[str, Any]:
        return self.model_governance

    def regulatory_readiness_profiles_manifest(self) -> dict[str, Any]:
        return self.regulatory_readiness_profiles

    def food_vocabulary_crosswalk_manifest(self) -> dict[str, Any]:
        return self.food_vocabulary_crosswalk

    def list_jurisdiction_coverage_records(self) -> list[dict[str, Any]]:
        return list(self.jurisdiction_coverage_registry["records"])

    def get_jurisdiction_coverage_record(self, coverage_id: str) -> dict[str, Any]:
        for item in self.jurisdiction_coverage_registry["records"]:
            if item["coverageId"] == coverage_id:
                return item
        raise DietaryRegistryError(
            code="unknown_jurisdiction_coverage_record",
            message=f"Unknown jurisdiction coverage record: {coverage_id}",
            suggestion="Use a coverage id listed in the jurisdiction-coverage manifest.",
        )

    def get_jurisdiction_coverage_records(
        self,
        *,
        jurisdiction: str | None = None,
        contaminant_family: str | None = None,
        substance_key: str | None = None,
    ) -> list[dict[str, Any]]:
        normalized_jurisdiction = jurisdiction.strip().lower() if jurisdiction is not None else None
        normalized_family = contaminant_family.strip().lower() if contaminant_family is not None else None
        normalized_substance = substance_key.strip().lower() if substance_key is not None else None
        records = []
        for item in self.jurisdiction_coverage_registry["records"]:
            if normalized_jurisdiction and item["jurisdiction"].strip().lower() != normalized_jurisdiction:
                continue
            if normalized_family and item["contaminantFamily"].strip().lower() != normalized_family:
                continue
            if normalized_substance and item["substanceKey"].strip().lower() != normalized_substance:
                continue
            records.append(item)
        return records

    def get_food_vocabulary_mapping_record(self, commodity_code: str) -> dict[str, Any]:
        normalized = self.resolve_commodity(commodity_code)
        processed_mapping = self._processed_mapping_for_input(commodity_code)
        if processed_mapping is not None:
            return processed_mapping
        mapping = self._base_food_vocabulary_mapping(normalized.commodity.commodity_code)
        if mapping is None:
            raise DietaryRegistryError(
                code="unknown_food_vocabulary_mapping_record",
                message=f"Unknown food vocabulary mapping record: {commodity_code}",
                suggestion="Use a commodity listed in the food-vocabulary manifest.",
            )
        return mapping

    def get_processed_commodity_mapping_record(self, processed_commodity_code: str) -> dict[str, Any]:
        mapping = self._processed_mapping_for_input(processed_commodity_code)
        if mapping is None:
            raise DietaryRegistryError(
                code="unknown_processed_commodity_mapping_record",
                message=f"Unknown processed commodity mapping record: {processed_commodity_code}",
                suggestion="Use a processed commodity listed in the food-vocabulary manifest.",
            )
        return mapping

    def commodity_taxonomy_manifest(self) -> dict[str, Any]:
        return {
            "defaultsVersion": DEFAULTS_VERSION,
            "taxonomyId": self.taxonomy_id(),
            "commodities": [
                {
                    "commodityCode": entry["commodityCode"],
                    "canonicalName": entry["canonicalName"],
                    "foodGroup": entry["foodGroup"],
                    "mappingStatus": entry["mappingStatus"],
                }
                for entry in self.list_commodity_entries()
            ],
        }

    def write_manifest(self) -> Path:
        manifest_path = self.defaults_root / "manifest.json"
        manifest_path.write_text(json.dumps(self.build_manifest(), indent=2) + "\n")
        return manifest_path
