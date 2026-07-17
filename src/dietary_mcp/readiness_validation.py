from __future__ import annotations

import json
from pathlib import Path

from dietary_mcp.assets import runtime_asset_root
from dietary_mcp.models import (
    AssessReviewDossierReadinessRequest,
    CheckAdapterImportRequest,
    CheckContaminantMonitoringImportRequest,
    CompareAdapterImportToWalkthroughRequest,
    ContaminantFamily,
    ContaminantMonitoringSignoffDecisionInput,
    DietaryCommodityResidueInput,
    ExportAdapterReviewBundleRequest,
    ExportContaminantMonitoringInterpretationBundleRequest,
    ExportContaminantMonitoringSignoffPacketRequest,
    ExportMetalsMonitoringInterpretationBundleRequest,
    ExportMetalsMonitoringSignoffPacketRequest,
    ExportVersionPinnedAdapterReviewDossierRequest,
    ExportVersionPinnedContaminantMonitoringReviewDossierRequest,
    ExportVersionPinnedMetalsMonitoringReviewDossierRequest,
    IntakeWindowSemantic,
    InteroperabilityActionDecisionStatus,
    LookupMetalsOccurrenceRequest,
    LookupMetalsReviewFocusRequest,
    MetalsMonitoringSignoffDecisionInput,
    ModelFamily,
    ResidueSourceType,
    ScenarioClass,
)
from dietary_mcp.runtime import DietaryRuntime, get_cached_dietary_runtime


def _validation_root(repo_root: Path) -> Path:
    candidate = repo_root / "validation" / "v1"
    if candidate.exists():
        return candidate
    return runtime_asset_root() / "validation" / "v1"


def _build_adapter_example_dossier(runtime: DietaryRuntime, scenario: str):
    if scenario == "efsa_primo":
        check_result = runtime.check_adapter_import(
            CheckAdapterImportRequest(
                model_family=ModelFamily.EFSA_PRIMO_ADAPTER,
                population_group="child_1_6",
                intake_window=IntakeWindowSemantic.ACUTE,
                scenario_class=ScenarioClass.BOUNDED_ACUTE,
                chemical_identity={"preferredName": "Example", "casrn": "100-00-0"},
                residue_records=[
                    DietaryCommodityResidueInput(
                        commodity_code="apples",
                        residue_concentration_mg_per_kg=0.18,
                        lower_bound_mg_per_kg=0.12,
                        upper_bound_mg_per_kg=0.24,
                        source_type=ResidueSourceType.MONITORING,
                    ),
                    DietaryCommodityResidueInput(
                        commodity_code="milk",
                        residue_concentration_mg_per_kg=0.03,
                        source_type=ResidueSourceType.CURATED_DEFAULT,
                    ),
                ],
                external_engine_version="3.1-harness",
                declared_total_intake_mg_per_kg_bw_per_day=0.00416,
                declared_lower_bound_mg_per_kg_bw_per_day=0.00304,
                declared_upper_bound_mg_per_kg_bw_per_day=0.00528,
                csv_text=(
                    "commodity,iesti_mgkgbwday,hr_mgkg,consumption_kg_day,pf,lb_mgkgbwday,ub_mgkgbwday\n"
                    "apple,0.00336,0.18,0.28,1.0,0.00224,0.00448\n"
                    "whole_milk,0.0008,0.03,0.4,1.0,0.0008,0.0008\n"
                ),
            )
        )
        comparison = runtime.compare_adapter_import_to_walkthrough(
            CompareAdapterImportToWalkthroughRequest(
                check_result=check_result,
                walkthrough_name="efsa_primo_tabular_alias_case",
            )
        )
    elif scenario == "epa_deem":
        check_result = runtime.check_adapter_import(
            CheckAdapterImportRequest(
                model_family=ModelFamily.EPA_DEEM_ADAPTER,
                population_group="adult_general",
                intake_window=IntakeWindowSemantic.CHRONIC,
                scenario_class=ScenarioClass.POINT_ESTIMATE,
                chemical_identity={"preferredName": "Example", "casrn": "100-00-0"},
                residue_records=[
                    DietaryCommodityResidueInput(
                        commodity_code="apples",
                        residue_concentration_mg_per_kg=0.18,
                        source_type=ResidueSourceType.MONITORING,
                    ),
                    DietaryCommodityResidueInput(
                        commodity_code="milk",
                        residue_concentration_mg_per_kg=0.03,
                        source_type=ResidueSourceType.CURATED_DEFAULT,
                    ),
                ],
                external_engine_version="4.02-harness",
                declared_total_intake_mg_per_kg_bw_per_day=0.0005571428571428571,
                csv_text=(
                    "food,exposure_mg_per_kg_bw_per_day,stmr_mgkg,food_consumption_kg_per_day,processing_factor\n"
                    "apples_raw,0.0004628571428571429,0.18,0.18,1.0\n"
                    "cow_milk,0.00009428571428571429,0.03,0.22,1.0\n"
                ),
            )
        )
        comparison = runtime.compare_adapter_import_to_walkthrough(
            CompareAdapterImportToWalkthroughRequest(
                check_result=check_result,
                walkthrough_name="epa_deem_csv_alias_case",
            )
        )
    else:
        raise ValueError(f"Unknown adapter readiness validation scenario: {scenario}")

    bundle = runtime.export_adapter_review_bundle(
        ExportAdapterReviewBundleRequest(
            check_result=check_result,
            comparison_result=comparison,
        )
    )
    return runtime.export_version_pinned_adapter_review_dossier(
        ExportVersionPinnedAdapterReviewDossierRequest(review_bundle=bundle)
    )


def _build_mercury_contaminant_dossier(runtime: DietaryRuntime):
    check_result = runtime.check_contaminant_monitoring_import(
        CheckContaminantMonitoringImportRequest(
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
            jurisdiction="eu",
            dataset_id="efsa.comprehensive_food_consumption_db.mercury_support",
            csv_text=(
                "food,contaminant,result,unit,loq,recovery_percent,measurement_uncertainty_percent,sampling_year\n"
                "swordfish,methylmercury,0.72,mg/kg,0.01,94,12,2025\n"
                "bluefin_tuna,methylmercury,0.55,mg/kg,0.01,92,11,2025\n"
            ),
        )
    )
    interpretation_bundle = runtime.export_contaminant_monitoring_interpretation_bundle(
        ExportContaminantMonitoringInterpretationBundleRequest(check_result=check_result)
    )
    signoff_packet = runtime.export_contaminant_monitoring_signoff_packet(
        ExportContaminantMonitoringSignoffPacketRequest(
            interpretation_bundle=interpretation_bundle,
            reviewer_id="validation.contaminant.reviewer",
            reviewer_role="scientific_reviewer",
            decisions=[
                ContaminantMonitoringSignoffDecisionInput(
                    action_id="review_header_resolution_and_quality_flags",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Header alias resolution and quality flags were reviewed.",
                    supporting_uris=["docs://contaminant-monitoring-import"],
                ),
                ContaminantMonitoringSignoffDecisionInput(
                    action_id="review_occurrence_evidence_context",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Occurrence evidence context was reviewed.",
                    supporting_uris=["docs://occurrence-evidence-registry"],
                ),
                ContaminantMonitoringSignoffDecisionInput(
                    action_id="review_analytical_method_context",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Analytical-method context was reviewed.",
                    supporting_uris=["docs://analytical-method-evidence-registry"],
                ),
                ContaminantMonitoringSignoffDecisionInput(
                    action_id="review_linked_focus_records",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Linked review-focus records were reviewed.",
                    supporting_uris=["docs://contaminant-monitoring-interpretation"],
                ),
                ContaminantMonitoringSignoffDecisionInput(
                    action_id="review_governance_links",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Governance links were reviewed.",
                    supporting_uris=["docs://regulatory-source-databases"],
                ),
            ],
        )
    )
    return runtime.export_version_pinned_contaminant_monitoring_review_dossier(
        ExportVersionPinnedContaminantMonitoringReviewDossierRequest(
            interpretation_bundle=interpretation_bundle,
            signoff_packet=signoff_packet,
        )
    )


def _build_mercury_metals_dossier(runtime: DietaryRuntime):
    occurrence_result = runtime.lookup_metals_occurrence(
        LookupMetalsOccurrenceRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
        )
    )
    review_focus_result = runtime.lookup_metals_review_focus(
        LookupMetalsReviewFocusRequest(
            jurisdiction="eu",
            contaminant_family=ContaminantFamily.MERCURY_FOOD_CONTAMINANTS,
        )
    )
    interpretation_bundle = runtime.export_metals_monitoring_interpretation_bundle(
        ExportMetalsMonitoringInterpretationBundleRequest(
            occurrence_result=occurrence_result,
            review_focus_result=review_focus_result,
        )
    )
    signoff_packet = runtime.export_metals_monitoring_signoff_packet(
        ExportMetalsMonitoringSignoffPacketRequest(
            interpretation_bundle=interpretation_bundle,
            reviewer_id="validation.metals.reviewer",
            reviewer_role="scientific_reviewer",
            decisions=[
                MetalsMonitoringSignoffDecisionInput(
                    action_id="review_occurrence_context",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Occurrence context reviewed.",
                    supporting_uris=["docs://metals-occurrence-registry"],
                ),
                MetalsMonitoringSignoffDecisionInput(
                    action_id="review_priority_food_groups",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Priority foods reviewed.",
                    supporting_uris=["docs://metals-monitoring-interpretation"],
                ),
                MetalsMonitoringSignoffDecisionInput(
                    action_id="review_sensitive_populations",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Sensitive populations reviewed.",
                    supporting_uris=["docs://metals-review-focus-registry"],
                ),
                MetalsMonitoringSignoffDecisionInput(
                    action_id="review_commodity_focus_prompts",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Commodity prompts reviewed.",
                    supporting_uris=["docs://metals-review-focus-registry"],
                ),
                MetalsMonitoringSignoffDecisionInput(
                    action_id="review_governance_links",
                    decision_status=InteroperabilityActionDecisionStatus.COMPLETED,
                    rationale="Governance links reviewed.",
                    supporting_uris=["docs://regulatory-source-databases"],
                ),
            ],
        )
    )
    return runtime.export_version_pinned_metals_monitoring_review_dossier(
        ExportVersionPinnedMetalsMonitoringReviewDossierRequest(
            interpretation_bundle=interpretation_bundle,
            signoff_packet=signoff_packet,
        )
    )


def _build_example_dossier(runtime: DietaryRuntime, scenario: str):
    if scenario in {"efsa_primo", "epa_deem"}:
        return _build_adapter_example_dossier(runtime, scenario)
    if scenario == "mercury_contaminant":
        return _build_mercury_contaminant_dossier(runtime)
    if scenario == "mercury_metals":
        return _build_mercury_metals_dossier(runtime)
    raise ValueError(f"Unknown readiness validation scenario: {scenario}")


def run_review_dossier_readiness_cases(repo_root: Path) -> dict:
    cases_payload = json.loads((_validation_root(repo_root) / "review_dossier_readiness_cases.json").read_text())
    runtime = get_cached_dietary_runtime(repo_root)
    results = []
    for case in cases_payload["cases"]:
        dossier = _build_example_dossier(runtime, case["scenario"])
        if case.get("extraDossierNotes"):
            dossier = dossier.model_copy(update={"notes": dossier.notes + case["extraDossierNotes"]})
        assessment = runtime.assess_review_dossier_readiness(
            AssessReviewDossierReadinessRequest(
                dossier=dossier,
                target_profile=case["targetProfile"],
            )
        )
        blocking_rule_ids = sorted(item.rule_id for item in assessment.blocking_rules)
        warning_rule_ids = sorted(item.rule_id for item in assessment.warning_rules)
        scientific_follow_up_action_ids = sorted(item.action_id for item in assessment.scientific_follow_up_items)
        observed_scientific_follow_up_queues = {
            "openActionIds": sorted(assessment.scientific_follow_up_queues.open_action_ids),
            "pendingActionIds": sorted(assessment.scientific_follow_up_queues.pending_action_ids),
            "acknowledgedActionIds": sorted(assessment.scientific_follow_up_queues.acknowledged_action_ids),
            "completedActionIds": sorted(assessment.scientific_follow_up_queues.completed_action_ids),
            "waivedActionIds": sorted(assessment.scientific_follow_up_queues.waived_action_ids),
            "escalatedActionIds": sorted(assessment.scientific_follow_up_queues.escalated_action_ids),
        }
        expected_blocking = sorted(case.get("expectedBlockingRuleIds", []))
        expected_warning = sorted(case.get("expectedWarningRuleIds", []))
        expected_scientific_follow_up = sorted(case.get("expectedScientificFollowUpActionIds", []))
        expected_scientific_follow_up_queues = {
            "openActionIds": sorted(case.get("expectedScientificFollowUpQueues", {}).get("openActionIds", [])),
            "pendingActionIds": sorted(case.get("expectedScientificFollowUpQueues", {}).get("pendingActionIds", [])),
            "acknowledgedActionIds": sorted(
                case.get("expectedScientificFollowUpQueues", {}).get("acknowledgedActionIds", [])
            ),
            "completedActionIds": sorted(case.get("expectedScientificFollowUpQueues", {}).get("completedActionIds", [])),
            "waivedActionIds": sorted(case.get("expectedScientificFollowUpQueues", {}).get("waivedActionIds", [])),
            "escalatedActionIds": sorted(case.get("expectedScientificFollowUpQueues", {}).get("escalatedActionIds", [])),
        }
        status = (
            "ok"
            if assessment.overall_status.value == case["expectedOverallStatus"]
            and blocking_rule_ids == expected_blocking
            and warning_rule_ids == expected_warning
            and scientific_follow_up_action_ids == expected_scientific_follow_up
            and observed_scientific_follow_up_queues == expected_scientific_follow_up_queues
            else "mismatch"
        )
        results.append(
            {
                "name": case["name"],
                "status": status,
                "expectedOverallStatus": case["expectedOverallStatus"],
                "observedOverallStatus": assessment.overall_status.value,
                "expectedBlockingRuleIds": expected_blocking,
                "observedBlockingRuleIds": blocking_rule_ids,
                "expectedWarningRuleIds": expected_warning,
                "observedWarningRuleIds": warning_rule_ids,
                "expectedScientificFollowUpActionIds": expected_scientific_follow_up,
                "observedScientificFollowUpActionIds": scientific_follow_up_action_ids,
                "expectedScientificFollowUpQueues": expected_scientific_follow_up_queues,
                "observedScientificFollowUpQueues": observed_scientific_follow_up_queues,
            }
        )
    overall_status = "ok" if all(item["status"] == "ok" for item in results) else "review_required"
    return {"status": overall_status, "cases": results}
