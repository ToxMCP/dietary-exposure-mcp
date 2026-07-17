from __future__ import annotations

from datetime import UTC, datetime

from dietary_mcp.defaults import DefaultsRegistry
from dietary_mcp.models import (
    DietaryAssumptionRecord,
    QualityFlag,
    Severity,
    SourceClassification,
    SourceReference,
    ProvenanceBundle,
)
from dietary_mcp.package_metadata import ALGORITHM_VERSION, DEFAULTS_VERSION, SCHEMA_VERSION


class ProvenanceBuilder:
    def __init__(self, defaults_registry: DefaultsRegistry) -> None:
        self.defaults_registry = defaults_registry

    def bundle(self, source_references: list[SourceReference] | None = None) -> ProvenanceBundle:
        return ProvenanceBundle(
            schema_version=SCHEMA_VERSION,
            defaults_version=DEFAULTS_VERSION,
            algorithm_version=ALGORITHM_VERSION,
            generated_at=datetime.now(UTC),
            source_references=source_references or [],
        )

    def curated_default(self, parameter: str, rationale: str) -> DietaryAssumptionRecord:
        source_reference = self.defaults_registry.parameter_source_reference(parameter)
        parameter_record = self.defaults_registry.parameter_record(parameter)
        return DietaryAssumptionRecord(
            parameter=parameter,
            value=float(parameter_record["value"]),
            unit=parameter_record["unit"],
            source_classification=SourceClassification.CURATED_DEFAULT,
            rationale=rationale,
            source_reference=source_reference,
        )

    def user_input(
        self,
        parameter: str,
        value: float | str,
        unit: str | None,
        rationale: str,
        source_reference: SourceReference | None = None,
    ) -> DietaryAssumptionRecord:
        return DietaryAssumptionRecord(
            parameter=parameter,
            value=value,
            unit=unit,
            source_classification=SourceClassification.USER_INPUT,
            rationale=rationale,
            source_reference=source_reference,
        )

    def mapped(
        self,
        parameter: str,
        value: float | str,
        unit: str | None,
        rationale: str,
        source_reference: SourceReference | None = None,
        warning: str | None = None,
    ) -> DietaryAssumptionRecord:
        quality_flags = []
        if warning:
            quality_flags.append(
                QualityFlag(
                    code="mapped_value",
                    severity=Severity.WARNING,
                    message=warning,
                )
            )
        return DietaryAssumptionRecord(
            parameter=parameter,
            value=value,
            unit=unit,
            source_classification=SourceClassification.MAPPED,
            rationale=rationale,
            source_reference=source_reference,
            quality_flags=quality_flags,
        )

    def derived(self, parameter: str, value: float | str, unit: str | None, rationale: str) -> DietaryAssumptionRecord:
        return DietaryAssumptionRecord(
            parameter=parameter,
            value=value,
            unit=unit,
            source_classification=SourceClassification.DERIVED,
            rationale=rationale,
        )

    def heuristic(
        self,
        parameter: str,
        value: float | str,
        unit: str | None,
        rationale: str,
        warning: str,
    ) -> DietaryAssumptionRecord:
        return DietaryAssumptionRecord(
            parameter=parameter,
            value=value,
            unit=unit,
            source_classification=SourceClassification.HEURISTIC,
            rationale=rationale,
            quality_flags=[
                QualityFlag(
                    code="heuristic_input",
                    severity=Severity.WARNING,
                    message=warning,
                )
            ],
        )
