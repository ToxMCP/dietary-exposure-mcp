import json
from pathlib import Path

import pytest

from dietary_mcp.contracts import generate_contract_artifacts
from dietary_mcp.dry_runs import build_validation_dossier, run_downstream_dry_runs
from dietary_mcp.release_artifacts import build_release_reports, write_release_reports


@pytest.mark.slow
@pytest.mark.contract
def test_release_reports_are_built_and_written(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    package_dist_dir = tmp_path / "dist"
    package_dist_dir.mkdir()
    package_artifact = package_dist_dir / "dietary_mcp-0.1.0-py3-none-any.whl"
    package_artifact.write_bytes(b"deterministic-test-wheel")
    generate_contract_artifacts(repo_root)
    reports = build_release_reports(repo_root, package_dist_dir=package_dist_dir)
    assert reports["metadata-report"]["schemaCount"] >= 1
    assert reports["metadata-report"]["adapterTemplateCount"] >= 2
    assert reports["metadata-report"]["adapterWalkthroughCount"] >= 2
    assert "efsa_primo_adapter" in reports["metadata-report"]["supportedModelFamilies"]
    assert "adapter_review_dossier" in reports["metadata-report"]["supportedWorkflows"]
    assert "review_dossier_readiness" in reports["metadata-report"]["supportedWorkflows"]
    assert "scientific_follow_up_queue_bundle" in reports["metadata-report"]["supportedWorkflows"]
    assert "scientific_follow_up_review_board" in reports["metadata-report"]["supportedWorkflows"]
    assert "scientific_follow_up_owner_handoff_packet" in reports["metadata-report"]["supportedWorkflows"]
    assert "scientific_follow_up_owner_remediation_packet" in reports["metadata-report"]["supportedWorkflows"]
    assert "scientific_follow_up_owner_signoff_packet" in reports["metadata-report"]["supportedWorkflows"]
    assert "scientific_follow_up_owner_signoff_dossier" in reports["metadata-report"]["supportedWorkflows"]
    assert "reference_value_lookup" in reports["metadata-report"]["supportedWorkflows"]
    assert "trade_risk_review_bundle" in reports["metadata-report"]["supportedWorkflows"]
    assert "trade_risk_review_dossier" in reports["metadata-report"]["supportedWorkflows"]
    assert "uncertainty_intake_assessment" in reports["metadata-report"]["supportedWorkflows"]
    assert "contaminant_legal_limit_lookup" in reports["metadata-report"]["supportedWorkflows"]
    assert "method_support_lookup" in reports["metadata-report"]["supportedWorkflows"]
    assert "consumption_dataset_support_lookup" in reports["metadata-report"]["supportedWorkflows"]
    assert "reporting_profile_lookup" in reports["metadata-report"]["supportedWorkflows"]
    assert "occurrence_evidence_lookup" in reports["metadata-report"]["supportedWorkflows"]
    assert "analytical_method_evidence_lookup" in reports["metadata-report"]["supportedWorkflows"]
    assert "contaminant_monitoring_import_check" in reports["metadata-report"]["supportedWorkflows"]
    assert "contaminant_monitoring_interpretation_bundle" in reports["metadata-report"]["supportedWorkflows"]
    assert "contaminant_monitoring_signoff_packet" in reports["metadata-report"]["supportedWorkflows"]
    assert "contaminant_monitoring_review_dossier" in reports["metadata-report"]["supportedWorkflows"]
    assert "metals_occurrence_lookup" in reports["metadata-report"]["supportedWorkflows"]
    assert "metals_review_focus_lookup" in reports["metadata-report"]["supportedWorkflows"]
    assert "metals_monitoring_interpretation_bundle" in reports["metadata-report"]["supportedWorkflows"]
    assert "metals_monitoring_signoff_packet" in reports["metadata-report"]["supportedWorkflows"]
    assert "metals_monitoring_review_dossier" in reports["metadata-report"]["supportedWorkflows"]
    assert "sanitised_public_review_dossier" in reports["metadata-report"]["supportedWorkflows"]
    assert "interoperability_preview" in reports["metadata-report"]["supportedWorkflows"]
    assert "interoperability_readiness_assessment" in reports["metadata-report"]["supportedWorkflows"]
    assert "interoperability_remediation_bundle" in reports["metadata-report"]["supportedWorkflows"]
    assert "interoperability_signoff_packet" in reports["metadata-report"]["supportedWorkflows"]
    assert "adapterTemplateManifest" in reports["metadata-report"]["artifactHashes"]
    assert "referenceValuesManifest" in reports["metadata-report"]["artifactHashes"]
    assert "mrlEnforcementManifest" in reports["metadata-report"]["artifactHashes"]
    assert "contaminantLegalLimitsManifest" in reports["metadata-report"]["artifactHashes"]
    assert "consumptionDatasetsManifest" in reports["metadata-report"]["artifactHashes"]
    assert "methodRegistryManifest" in reports["metadata-report"]["artifactHashes"]
    assert "legalAuthoritiesManifest" in reports["metadata-report"]["artifactHashes"]
    assert "reportingProfilesManifest" in reports["metadata-report"]["artifactHashes"]
    assert "occurrenceEvidenceManifest" in reports["metadata-report"]["artifactHashes"]
    assert "analyticalMethodEvidenceManifest" in reports["metadata-report"]["artifactHashes"]
    assert "metalsOccurrenceManifest" in reports["metadata-report"]["artifactHashes"]
    assert "metalsReviewFocusManifest" in reports["metadata-report"]["artifactHashes"]
    assert "emergingContaminantsManifest" in reports["metadata-report"]["artifactHashes"]
    assert "jurisdictionCoverageManifest" in reports["metadata-report"]["artifactHashes"]
    assert "modelGovernanceManifest" in reports["metadata-report"]["artifactHashes"]
    assert "foodVocabularyCrosswalkManifest" in reports["metadata-report"]["artifactHashes"]
    assert "interoperabilityProfilesManifest" in reports["metadata-report"]["artifactHashes"]
    assert "interoperabilityReadinessProfilesManifest" in reports["metadata-report"]["artifactHashes"]
    assert "interoperabilityRulesManifest" in reports["metadata-report"]["artifactHashes"]
    assert "interoperabilityRemediationActionsManifest" in reports["metadata-report"]["artifactHashes"]
    assert "readinessProfilesManifest" in reports["metadata-report"]["artifactHashes"]
    assert "regulatoryRulesManifest" in reports["metadata-report"]["artifactHashes"]
    assert "sanitisationRulesManifest" in reports["metadata-report"]["artifactHashes"]
    assert reports["metadata-report"]["modelGovernanceFamilyCount"] >= 4
    assert reports["metadata-report"]["referenceValueRecordCount"] >= 31
    assert reports["metadata-report"]["contaminantLegalLimitRecordCount"] >= 20
    assert reports["metadata-report"]["consumptionDatasetCount"] >= 6
    assert reports["metadata-report"]["consumptionProfileCount"] >= 21
    assert reports["metadata-report"]["methodRegistryCount"] >= 35
    assert reports["metadata-report"]["legalAuthorityCount"] >= 4
    assert reports["metadata-report"]["reportingProfileCount"] >= 5
    assert reports["metadata-report"]["occurrenceEvidenceRecordCount"] >= 15
    assert reports["metadata-report"]["analyticalMethodEvidenceRecordCount"] >= 15
    assert reports["metadata-report"]["metalsOccurrenceRecordCount"] >= 4
    assert reports["metadata-report"]["metalsReviewFocusRecordCount"] >= 4
    assert reports["metadata-report"]["emergingContaminantFamilyCount"] >= 2
    assert reports["metadata-report"]["jurisdictionCoverageRecordCount"] >= 39
    assert reports["metadata-report"]["foodVocabularyCommodityCount"] >= 10
    assert reports["metadata-report"]["processedCommodityMappingCount"] >= 4
    assert reports["metadata-report"]["commodityCount"] >= 10
    assert reports["metadata-report"]["interoperabilityProfileCount"] >= 1
    assert reports["metadata-report"]["interoperabilityReadinessProfileCount"] >= 3
    assert reports["metadata-report"]["readinessProfileCount"] >= 3
    assert reports["metadata-report"]["interoperabilityRuleCount"] >= 1
    assert reports["metadata-report"]["interoperabilityRemediationActionCount"] >= 1
    assert reports["metadata-report"]["regulatoryRuleCount"] >= 1
    assert reports["metadata-report"]["sanitisationRuleCount"] >= 1
    assert reports["metadata-report"]["referenceCaseCount"] >= 10
    assert reports["readiness-report"]["gates"]
    assert reports["metadata-report"]["packageArtifacts"] == [
        {
            "name": package_artifact.name,
            "sizeBytes": package_artifact.stat().st_size,
            "sha256": "464541d3ae137e11343d989848f6a65be240a2576672b7781d463d239bb806ae",
        }
    ]

    written = write_release_reports(
        repo_root,
        package_dist_dir=package_dist_dir,
        output_dir=tmp_path / "release-reports",
    )
    for path in written.values():
        assert path.exists()
        payload = json.loads(path.read_text())
        assert payload["version"] == "0.1.0"
    downstream = json.loads(written["downstream-dry-runs"].read_text())
    validation_dossier = json.loads(written["validation-dossier"].read_text())
    assert downstream["status"] == "pass"
    assert validation_dossier["status"] == "draft_ready"


def test_validation_manifest_exists() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    manifest = json.loads((repo_root / "validation" / "v1" / "manifest.json").read_text())
    assert {item["name"] for item in manifest["artifacts"]} == {
        "benchmark_cases",
        "dietary_reference_cases",
        "commodity_mapping_gap_report",
        "adapter_normalization_cases",
        "food_vocabulary_cases",
        "regulatory_rules",
        "source_database_cases",
        "survey_distribution_summary_cases",
        "probabilistic_intake_summary_cases",
        "uncertainty_intake_assessment_cases",
        "censored_residue_policy_cases",
        "uncertainty_sensitivity_cases",
        "health_reference_exceedance_cases",
        "uncertainty_reproducibility_cases",
        "contaminant_monitoring_check_cases",
        "contaminant_monitoring_bundle_cases",
        "contaminant_monitoring_signoff_cases",
        "contaminant_monitoring_review_dossier_cases",
        "metals_monitoring_bundle_cases",
        "metals_monitoring_signoff_cases",
        "metals_monitoring_review_dossier_cases",
        "interoperability_profiles",
        "interoperability_preview_cases",
        "interoperability_readiness_profiles",
        "interoperability_rules",
        "interoperability_readiness_cases",
        "interoperability_remediation_actions",
        "interoperability_remediation_cases",
        "interoperability_signoff_cases",
        "sanitisation_rules",
        "review_dossier_readiness_cases",
        "scientific_follow_up_queue_bundle_cases",
        "scientific_follow_up_review_board_cases",
        "scientific_follow_up_owner_handoff_cases",
        "scientific_follow_up_owner_remediation_cases",
        "scientific_follow_up_owner_signoff_cases",
        "scientific_follow_up_owner_signoff_dossier_cases",
        "sanitised_public_review_cases",
    }


def test_release_readiness_requires_all_validation_suites_ok(monkeypatch) -> None:
    from dietary_mcp import release_artifacts

    repo_root = Path(__file__).resolve().parents[1]
    release_artifacts._RELEASE_REPORT_CACHE.clear()

    validation_summary = {
        "status": "review_required",
        "suiteCount": 1,
        "caseCount": 1,
        "failedCaseCount": 1,
        "suites": {
            "probabilistic_intake_summary": {
                "status": "review_required",
                "caseCount": 1,
                "failedCaseCount": 1,
            }
        },
        "failures": [
            {
                "suite": "probabilistic_intake_summary",
                "name": "injected_failure",
                "status": "review_required",
            }
        ],
    }

    def fake_validate_generated_artifacts(repo_root: Path) -> dict:
        return {
            "schemas": [{"name": "dietaryIntakeSummary.v1", "status": "ok"}],
            "examples": [{"name": "dietaryIntakeSummary.v1.json", "status": "ok"}],
            "probabilistic_intake_summary": [
                {"name": "injected_failure", "status": "review_required"}
            ],
            "status": "review_required",
            "suiteSummary": validation_summary,
        }

    monkeypatch.setattr(
        release_artifacts,
        "validate_generated_artifacts",
        fake_validate_generated_artifacts,
    )
    reports = release_artifacts.build_release_reports(repo_root, skip_examples=True)
    gate_status = {
        gate["id"]: gate["status"] for gate in reports["readiness-report"]["gates"]
    }

    assert reports["readiness-report"]["status"] == "review_required"
    assert gate_status["all_validation_suites_ok"] == "review_required"
    assert reports["readiness-report"]["validationSummary"]["status"] == "review_required"
    assert reports["readiness-report"]["validationSummary"]["failures"] == validation_summary["failures"]


@pytest.mark.slow
@pytest.mark.integration
def test_dry_runs_and_validation_dossier_build() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    dry_runs = run_downstream_dry_runs(repo_root)
    validation_dossier = build_validation_dossier(repo_root)
    assert dry_runs["pbpkDryRun"]["status"] == "pass"
    assert dry_runs["toxclawDryRun"]["status"] == "pass"
    assert dry_runs["adapterDryRuns"]["efsaPrimoHarness"]["status"] == "pass"
    assert dry_runs["adapterDryRuns"]["epaDeemHarness"]["status"] == "pass"
    assert validation_dossier["adapterNormalizationCaseCount"] >= 2
    assert validation_dossier["adapterNormalizationStatus"] == "ok"
    assert validation_dossier["foodVocabularyCaseCount"] >= 3
    assert validation_dossier["foodVocabularyStatus"] == "ok"
    assert validation_dossier["sourceDatabaseCaseCount"] >= 10
    assert validation_dossier["sourceDatabaseStatus"] == "ok"
    assert validation_dossier["contaminantMonitoringCheckCaseCount"] >= 3
    assert validation_dossier["contaminantMonitoringCheckStatus"] == "ok"
    assert validation_dossier["contaminantMonitoringBundleCaseCount"] >= 2
    assert validation_dossier["contaminantMonitoringBundleStatus"] == "ok"
    assert validation_dossier["contaminantMonitoringSignoffCaseCount"] >= 3
    assert validation_dossier["contaminantMonitoringSignoffStatus"] == "ok"
    assert validation_dossier["contaminantMonitoringReviewDossierCaseCount"] >= 3
    assert validation_dossier["contaminantMonitoringReviewDossierStatus"] == "ok"
    assert validation_dossier["metalsMonitoringBundleCaseCount"] >= 2
    assert validation_dossier["metalsMonitoringBundleStatus"] == "ok"
    assert validation_dossier["metalsMonitoringSignoffCaseCount"] >= 3
    assert validation_dossier["metalsMonitoringSignoffStatus"] == "ok"
    assert validation_dossier["metalsMonitoringReviewDossierCaseCount"] >= 3
    assert validation_dossier["metalsMonitoringReviewDossierStatus"] == "ok"
    assert validation_dossier["interoperabilityPreviewCaseCount"] >= 2
    assert validation_dossier["interoperabilityPreviewStatus"] == "ok"
    assert validation_dossier["interoperabilityReadinessCaseCount"] >= 4
    assert validation_dossier["interoperabilityReadinessStatus"] == "ok"
    assert validation_dossier["interoperabilityRemediationCaseCount"] >= 3
    assert validation_dossier["interoperabilityRemediationStatus"] == "ok"
    assert validation_dossier["interoperabilitySignoffCaseCount"] >= 3
    assert validation_dossier["interoperabilitySignoffStatus"] == "ok"
    assert validation_dossier["reviewDossierReadinessCaseCount"] >= 3
    assert validation_dossier["reviewDossierReadinessStatus"] == "ok"
    assert validation_dossier["scientificFollowUpQueueBundleCaseCount"] >= 3
    assert validation_dossier["scientificFollowUpQueueBundleStatus"] == "ok"
    assert validation_dossier["scientificFollowUpReviewBoardCaseCount"] >= 3
    assert validation_dossier["scientificFollowUpReviewBoardStatus"] == "ok"
    assert validation_dossier["scientificFollowUpOwnerHandoffCaseCount"] >= 3
    assert validation_dossier["scientificFollowUpOwnerHandoffStatus"] == "ok"
    assert validation_dossier["scientificFollowUpOwnerRemediationCaseCount"] >= 3
    assert validation_dossier["scientificFollowUpOwnerRemediationStatus"] == "ok"
    assert validation_dossier["scientificFollowUpOwnerSignoffCaseCount"] >= 3
    assert validation_dossier["scientificFollowUpOwnerSignoffStatus"] == "ok"
    assert validation_dossier["scientificFollowUpOwnerSignoffDossierCaseCount"] >= 3
    assert validation_dossier["scientificFollowUpOwnerSignoffDossierStatus"] == "ok"
    assert validation_dossier["sanitisedPublicReviewCaseCount"] >= 2
    assert validation_dossier["sanitisedPublicReviewStatus"] == "ok"
    assert validation_dossier["surveyDistributionSummaryCaseCount"] >= 1
    assert validation_dossier["surveyDistributionSummaryStatus"] == "ok"
    assert validation_dossier["probabilisticIntakeSummaryCaseCount"] >= 4
    assert validation_dossier["probabilisticIntakeSummaryStatus"] == "ok"
    assert validation_dossier["uncertaintyIntakeAssessmentCaseCount"] >= 4
    assert validation_dossier["uncertaintyIntakeAssessmentStatus"] == "ok"
    assert validation_dossier["censoredResiduePolicyCaseCount"] >= 1
    assert validation_dossier["censoredResiduePolicyStatus"] == "ok"
    assert validation_dossier["uncertaintySensitivityCaseCount"] >= 1
    assert validation_dossier["uncertaintySensitivityStatus"] == "ok"
    assert validation_dossier["healthReferenceExceedanceCaseCount"] >= 3
    assert validation_dossier["healthReferenceExceedanceStatus"] == "ok"
    assert validation_dossier["uncertaintyReproducibilityCaseCount"] >= 1
    assert validation_dossier["uncertaintyReproducibilityStatus"] == "ok"
    assert validation_dossier["benchmarkCaseCount"] >= 10
    assert validation_dossier["referenceCaseCount"] >= 10
    assert validation_dossier["referenceCaseStatus"] == "ok"
    assert set(validation_dossier["populationCoverage"]) >= {
        "adult_general",
        "child_1_6",
        "adolescent_11_17",
        "older_adult_65_plus",
    }
