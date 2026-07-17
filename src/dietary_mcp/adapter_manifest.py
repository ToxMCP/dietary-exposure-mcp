from __future__ import annotations

from dietary_mcp.defaults import DefaultsRegistry
from dietary_mcp.models import ModelFamily, ScenarioClass
from dietary_mcp.package_metadata import VERSION


def build_adapter_manifest(defaults: DefaultsRegistry) -> dict:
    source_ids_by_family = {
        ModelFamily.REFERENCE_DIETARY: [],
        ModelFamily.ADAPTER_STUB: [],
        ModelFamily.EFSA_PRIMO_ADAPTER: [
            "efsa.primo",
            "efsa.default_body_weights.2012",
        ],
        ModelFamily.EPA_DEEM_ADAPTER: ["epa.deem.fcid.4_02"],
    }
    family_metadata = {
        ModelFamily.REFERENCE_DIETARY: {
            "label": "Native deterministic dietary kernel",
            "status": "native",
            "notes": [
                "Implements the auditable first-party Dietary MCP calculator.",
                "Supports deterministic point-estimate and bounded acute/chronic summaries.",
            ],
        },
        ModelFamily.ADAPTER_STUB: {
            "label": "Generic adapter compatibility stub",
            "status": "synthetic_harness",
            "notes": [
                "Compatibility-only family for exercising extension hooks without a named external engine.",
                "Reuses the native deterministic kernel and is not model-equivalent to an external engine.",
            ],
        },
        ModelFamily.EFSA_PRIMO_ADAPTER: {
            "label": "EFSA PRIMo-aligned harness",
            "status": "synthetic_harness",
            "notes": [
                "Normalizes PRIMo-aligned workflows through the public Dietary MCP contracts.",
                "Current v0.1 harness reuses the native deterministic kernel and is not a claim of official PRIMo equivalence.",
            ],
        },
        ModelFamily.EPA_DEEM_ADAPTER: {
            "label": "EPA DEEM-aligned harness",
            "status": "synthetic_harness",
            "notes": [
                "Normalizes DEEM-aligned workflows through the public Dietary MCP contracts.",
                "Current v0.1 harness reuses the native deterministic kernel and is not a claim of official DEEM equivalence.",
            ],
        },
    }

    families = []
    for family in ModelFamily:
        metadata = family_metadata[family]
        source_descriptors = []
        for source_id in source_ids_by_family[family]:
            record = defaults.get_source_catalog_record(source_id)
            source_descriptors.append(
                {
                    "sourceId": record["sourceId"],
                    "title": record["title"],
                    "organization": record.get("organization"),
                    "url": record.get("url"),
                }
            )
        families.append(
            {
                "modelFamily": family.value,
                "label": metadata["label"],
                "status": metadata["status"],
                "normalizerMode": (
                    "native_runtime"
                    if family == ModelFamily.REFERENCE_DIETARY
                    else "synthetic_external_summary_v1"
                ),
                "supportedInputModes": (
                    ["validated_scenario"]
                    if family == ModelFamily.REFERENCE_DIETARY
                    else ["validated_payload", "tabular_rows_v1", "csv_v1"]
                ),
                "supportsScenarioClasses": [item.value for item in ScenarioClass],
                "notes": metadata["notes"],
                "sourceDescriptors": source_descriptors,
            }
        )

    return {
        "version": VERSION,
        "families": families,
        "deferredCapabilities": [
            "Official external-engine execution and equivalence claims.",
            "Hidden probabilistic population distributions.",
            "Direct ingestion of proprietary survey packs without explicit normalization and provenance controls.",
        ],
    }
