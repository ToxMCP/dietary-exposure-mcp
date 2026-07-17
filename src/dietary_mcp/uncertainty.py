from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import scipy
from scipy import stats

from dietary_mcp.errors import DietaryValidationError
from dietary_mcp.limits import enforce_uncertainty_draw_limit, enforce_uncertainty_iteration_limits
from dietary_mcp.models import (
    _strip_volatile,
    BuildUncertaintyIntakeAssessmentRequest,
    CensoredDataPolicy,
    HealthReferenceExceedanceSummary,
    HealthReferenceType,
    LimitationNote,
    ResidueUncertaintyDistribution,
    ResidueUncertaintyModel,
    SensitivityRankingRecord,
    Severity,
    SourceReference,
    UncertaintyAssumptionLedger,
    UncertaintyAssumptionLedgerEntry,
    UncertaintyDistributionSummary,
    UncertaintyIntakeAssessment,
    UncertaintyMetricInterval,
    UncertaintyReproducibilityRecord,
)
from dietary_mcp.runtime import DietaryRuntime, _adjusted_residue_value


_RNG_ALGORITHM = "numpy.PCG64"
_MODEL_VERSION = "uncertainty_intake_assessment_v1"
_SUMMARY_METRICS = (
    "mean",
    "p95",
    "p99",
    "p999",
    "max",
    "consumers_only_mean",
    "consumers_only_p95",
)


@dataclass(frozen=True)
class _SubjectExposureRow:
    subject_id: str
    body_weight_kg: float
    survey_weight: float | None
    consumption_by_commodity: dict[str, float]


def _fingerprint(payload: Any, prefix: str) -> str:
    # Strip volatile wall-clock timestamps (e.g. provenance ``generated_at``)
    # so reproducibility fingerprints depend only on the scientific content of
    # the inputs, not on when the assessment happened to run.
    canonical = _strip_volatile(payload)
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(encoded).hexdigest()[:12]}"


# Number of significant figures retained when quantizing stochastic
# Monte-Carlo output floats before hashing the simulation fingerprint. The
# quantum (~1e-12 relative) sits ~4 orders of magnitude above the last-ULP
# float divergence (~1e-16 relative) that macOS-ARM and Linux-x86 exhibit for
# identical draws, so it absorbs that noise and yields a platform-independent
# ``simulation_fingerprint`` while staying far tighter than the validation
# tolerances applied to the medians themselves.
_SIMULATION_FINGERPRINT_SIG_FIGS = 12


def _quantize_floats(value: Any, sig_figs: int = _SIMULATION_FINGERPRINT_SIG_FIGS) -> Any:
    """Recursively round every float in ``value`` to ``sig_figs`` significant
    figures.

    Significant figures (rather than decimal places) keep the rounding
    magnitude-relative, so it behaves identically for values spanning many
    orders of magnitude. Non-finite floats (``nan``/``inf``) and exact zeros
    are passed through unchanged. Containers are rebuilt so the result is a
    plain JSON-serialisable structure.
    """

    if isinstance(value, bool):
        # ``bool`` is a subclass of ``int``; never treat it as a float.
        return value
    if isinstance(value, float):
        if not math.isfinite(value) or value == 0.0:
            return value
        decimals = sig_figs - 1 - math.floor(math.log10(abs(value)))
        return round(value, decimals)
    if isinstance(value, dict):
        return {key: _quantize_floats(item, sig_figs) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_quantize_floats(item, sig_figs) for item in value]
    return value


def _metric_interval(values: list[float]) -> UncertaintyMetricInterval:
    if not values:
        return UncertaintyMetricInterval(median=0.0, lower95=0.0, upper95=0.0)
    return UncertaintyMetricInterval(
        median=float(np.quantile(values, 0.50)),
        lower95=float(np.quantile(values, 0.025)),
        upper95=float(np.quantile(values, 0.975)),
    )


def _summarize_draws(exposures: np.ndarray) -> dict[str, float]:
    consumers = exposures[exposures > 0.0]
    return {
        "mean": float(np.mean(exposures)) if exposures.size else 0.0,
        "p95": float(np.quantile(exposures, 0.95)) if exposures.size else 0.0,
        "p99": float(np.quantile(exposures, 0.99)) if exposures.size else 0.0,
        "p999": float(np.quantile(exposures, 0.999)) if exposures.size else 0.0,
        "max": float(np.max(exposures)) if exposures.size else 0.0,
        "consumers_only_mean": float(np.mean(consumers)) if consumers.size else 0.0,
        "consumers_only_p95": float(np.quantile(consumers, 0.95)) if consumers.size else 0.0,
    }


def _summary_from_outer_metrics(outer_metrics: list[dict[str, float]]) -> UncertaintyDistributionSummary:
    by_metric = {
        metric: [outer_result[metric] for outer_result in outer_metrics]
        for metric in _SUMMARY_METRICS
    }
    return UncertaintyDistributionSummary(
        mean=_metric_interval(by_metric["mean"]),
        percentile95=_metric_interval(by_metric["p95"]),
        percentile99=_metric_interval(by_metric["p99"]),
        percentile999=_metric_interval(by_metric["p999"]),
        max=_metric_interval(by_metric["max"]),
        consumersOnlyMean=_metric_interval(by_metric["consumers_only_mean"]),
        consumersOnlyPercentile95=_metric_interval(by_metric["consumers_only_p95"]),
    )


def _subject_rows(request: BuildUncertaintyIntakeAssessmentRequest) -> list[_SubjectExposureRow]:
    rows: dict[str, _SubjectExposureRow] = {}
    for record in request.dataset.records:
        row = rows.get(record.subject_id)
        if row is None:
            row = _SubjectExposureRow(
                subject_id=record.subject_id,
                body_weight_kg=record.body_weight_kg,
                survey_weight=record.survey_weight,
                consumption_by_commodity={},
            )
            rows[record.subject_id] = row
        row.consumption_by_commodity[record.commodity_code] = (
            row.consumption_by_commodity.get(record.commodity_code, 0.0)
            + record.consumption_kg_per_day
        )
    return list(rows.values())


def _residue_profile_lookup(request: BuildUncertaintyIntakeAssessmentRequest) -> dict[str, float]:
    return {
        record.commodity.commodity_code: _adjusted_residue_value(record)
        for record in request.residue_profile.records
    }


def _censored_substitution_value(
    model: ResidueUncertaintyModel,
    policy: CensoredDataPolicy,
) -> float:
    lod = model.lod_mg_per_kg or 0.0
    loq = model.loq_mg_per_kg if model.loq_mg_per_kg is not None else lod
    if policy == CensoredDataPolicy.LOWER_BOUND_ZERO:
        return 0.0
    if policy == CensoredDataPolicy.MIDDLE_BOUND_HALF_LOD_LOQ:
        return (loq if loq > 0.0 else lod) / 2.0
    if policy == CensoredDataPolicy.UPPER_BOUND_LOD_LOQ:
        return loq
    return (loq if loq > 0.0 else lod) / 2.0


def _sample_residue_values(
    *,
    rng: np.random.Generator,
    models_by_commodity: dict[str, ResidueUncertaintyModel],
    fallback_residues: dict[str, float],
    inner_iteration_count: int,
    policy: CensoredDataPolicy,
) -> tuple[dict[str, np.ndarray], dict[str, float]]:
    values: dict[str, np.ndarray] = {}
    sensitivity_inputs: dict[str, float] = {}
    for commodity_code, fallback in fallback_residues.items():
        model = models_by_commodity.get(commodity_code)
        input_name = f"residue.{commodity_code}"
        if model is None:
            draw = np.full(inner_iteration_count, fallback)
            sensitivity_inputs[input_name] = float(np.mean(draw))
        elif model.distribution == ResidueUncertaintyDistribution.POINT:
            point = model.point_mg_per_kg if model.point_mg_per_kg is not None else fallback
            draw = np.full(inner_iteration_count, point)
            sensitivity_inputs[input_name] = float(np.mean(draw))
        elif model.distribution == ResidueUncertaintyDistribution.EMPIRICAL:
            empirical = np.array(model.empirical_values_mg_per_kg, dtype=float)
            draw = rng.choice(empirical, size=inner_iteration_count, replace=True)
            sensitivity_inputs[input_name] = float(np.mean(draw))
        elif model.distribution == ResidueUncertaintyDistribution.UNIFORM:
            draw = rng.uniform(model.min_mg_per_kg, model.max_mg_per_kg, size=inner_iteration_count)
            sensitivity_inputs[input_name] = float(np.mean(draw))
        elif model.distribution == ResidueUncertaintyDistribution.TRIANGULAR:
            draw = rng.triangular(
                model.min_mg_per_kg,
                model.mode_mg_per_kg,
                model.max_mg_per_kg,
                size=inner_iteration_count,
            )
            sensitivity_inputs[input_name] = float(np.mean(draw))
        elif model.distribution == ResidueUncertaintyDistribution.LOGNORMAL:
            draw = rng.lognormal(
                mean=float(np.log(model.geometric_mean_mg_per_kg)),
                sigma=float(np.log(model.geometric_sd)),
                size=inner_iteration_count,
            )
            sensitivity_inputs[input_name] = float(np.mean(draw))
        else:
            substitution = _censored_substitution_value(model, policy)
            if policy in {
                CensoredDataPolicy.LOWER_BOUND_ZERO,
                CensoredDataPolicy.MIDDLE_BOUND_HALF_LOD_LOQ,
                CensoredDataPolicy.UPPER_BOUND_LOD_LOQ,
            }:
                draw = np.full(inner_iteration_count, substitution)
            else:
                draw = rng.lognormal(
                    mean=float(np.log(model.geometric_mean_mg_per_kg)),
                    sigma=float(np.log(model.geometric_sd)),
                    size=inner_iteration_count,
                )
                draw = np.minimum(draw, substitution)
            sensitivity_inputs[input_name] = float(np.mean(draw))
        processing_cv = model.processing_factor_cv if model is not None else None
        if processing_cv and processing_cv > 0.0:
            multiplier = rng.lognormal(
                mean=-0.5 * processing_cv**2,
                sigma=processing_cv,
                size=inner_iteration_count,
            )
            draw = draw * multiplier
            sensitivity_inputs[f"processing_factor.{commodity_code}"] = float(np.mean(multiplier))
        values[commodity_code] = np.clip(draw, 0.0, None)
    return values, sensitivity_inputs


def _simulate_policy(
    *,
    request: BuildUncertaintyIntakeAssessmentRequest,
    subject_rows: list[_SubjectExposureRow],
    fallback_residues: dict[str, float],
    models_by_commodity: dict[str, ResidueUncertaintyModel],
    policy: CensoredDataPolicy,
) -> tuple[list[dict[str, float]], list[float], dict[str, list[float]]]:
    rng = np.random.Generator(np.random.PCG64(request.random_seed))
    weights = np.array([row.survey_weight or 1.0 for row in subject_rows], dtype=float)
    weights = weights / np.sum(weights)
    outer_metrics: list[dict[str, float]] = []
    outer_exceedance: list[float] = []
    sensitivity_inputs: dict[str, list[float]] = {}

    for _ in range(request.outer_iteration_count):
        subject_indices = rng.choice(
            len(subject_rows),
            size=request.inner_iteration_count,
            replace=True,
            p=weights,
        )
        residue_draws, sampled_inputs = _sample_residue_values(
            rng=rng,
            models_by_commodity=models_by_commodity,
            fallback_residues=fallback_residues,
            inner_iteration_count=request.inner_iteration_count,
            policy=policy,
        )
        exposures = np.zeros(request.inner_iteration_count, dtype=float)
        for draw_index, subject_index in enumerate(subject_indices):
            row = subject_rows[int(subject_index)]
            mass = 0.0
            for commodity_code, consumption_kg_per_day in row.consumption_by_commodity.items():
                if commodity_code in residue_draws:
                    mass += consumption_kg_per_day * residue_draws[commodity_code][draw_index]
            exposures[draw_index] = mass / row.body_weight_kg if row.body_weight_kg > 0.0 else 0.0

        metrics = _summarize_draws(exposures)
        outer_metrics.append(metrics)
        for name, value in sampled_inputs.items():
            sensitivity_inputs.setdefault(name, []).append(value)

        if request.health_reference is not None:
            reference_value = request.health_reference.value
            if request.health_reference.reference_type in {
                HealthReferenceType.BMDL,
                HealthReferenceType.MOE_REFERENCE_POINT,
            }:
                outer_exceedance.append(float(np.mean(reference_value / np.maximum(exposures, 1e-18))))
            else:
                outer_exceedance.append(float(np.mean(exposures > reference_value)))
    return outer_metrics, outer_exceedance, sensitivity_inputs


def _health_reference_summary(
    request: BuildUncertaintyIntakeAssessmentRequest,
    outer_metrics: list[dict[str, float]],
    outer_health_values: list[float],
) -> HealthReferenceExceedanceSummary | None:
    if request.health_reference is None:
        return None
    reference = request.health_reference
    if reference.reference_type in {HealthReferenceType.BMDL, HealthReferenceType.MOE_REFERENCE_POINT}:
        return HealthReferenceExceedanceSummary(
            referenceType=reference.reference_type,
            referenceValue=reference.value,
            referenceUnit=reference.unit,
            exceedanceProbability=UncertaintyMetricInterval(median=0.0, lower95=0.0, upper95=0.0),
            marginOfExposure=_metric_interval(outer_health_values),
        )
    if reference.reference_type == HealthReferenceType.ARFD:
        high_percentile_ratio_values = [
            outer_result["p95"] / reference.value
            for outer_result in outer_metrics
        ]
        return HealthReferenceExceedanceSummary(
            referenceType=reference.reference_type,
            referenceValue=reference.value,
            referenceUnit=reference.unit,
            exceedanceProbability=_metric_interval(outer_health_values),
            highPercentileMetric="p95",
            highPercentileExposureRatio=_metric_interval(high_percentile_ratio_values),
        )
    percent_values = [
        100.0 * outer_result["mean"] / reference.value
        for outer_result in outer_metrics
    ]
    return HealthReferenceExceedanceSummary(
        referenceType=reference.reference_type,
        referenceValue=reference.value,
        referenceUnit=reference.unit,
        exceedanceProbability=_metric_interval(outer_health_values),
        percentOfReference=_metric_interval(percent_values),
    )


def _sensitivity_ranking(
    sensitivity_inputs: dict[str, list[float]],
    outer_metrics: list[dict[str, float]],
) -> list[SensitivityRankingRecord]:
    target = [item["mean"] for item in outer_metrics]
    records = []
    for input_name, values in sensitivity_inputs.items():
        if len(set(values)) < 2 or len(set(target)) < 2:
            continue
        correlation = stats.spearmanr(values, target).correlation
        if correlation is None or not np.isfinite(correlation):
            continue
        records.append(
            SensitivityRankingRecord(
                inputName=input_name,
                metric="mean",
                rankCorrelation=float(correlation),
            )
        )
    return sorted(records, key=lambda item: abs(item.rank_correlation), reverse=True)[:10]


def build_uncertainty_intake_assessment(
    runtime: DietaryRuntime,
    request: BuildUncertaintyIntakeAssessmentRequest,
) -> UncertaintyIntakeAssessment:
    enforce_uncertainty_iteration_limits(request.outer_iteration_count, request.inner_iteration_count)
    subject_rows = _subject_rows(request)
    if not subject_rows:
        raise DietaryValidationError(
            code="empty_uncertainty_dataset",
            message="Cannot run uncertainty intake assessment on an empty survey dataset.",
            suggestion="Provide at least one mapped survey subject before running the uncertainty assessment.",
        )
    enforce_uncertainty_draw_limit(
        request.outer_iteration_count,
        request.inner_iteration_count,
        len(subject_rows),
    )

    fallback_residues = _residue_profile_lookup(request)
    models_by_commodity = {
        model.commodity_code: model
        for model in request.residue_uncertainty_models
    }
    unsupported_models = sorted(set(models_by_commodity) - set(fallback_residues))
    if unsupported_models:
        raise DietaryValidationError(
            code="uncertainty_model_without_residue_record",
            message=f"Residue uncertainty models were supplied without residue records: {unsupported_models}.",
            suggestion="Provide uncertainty models only for commodities present in the residue profile.",
            details={"commodityCodes": unsupported_models},
        )

    weighted_sampling = any(row.survey_weight is not None for row in subject_rows)
    ledger_entries = [
        UncertaintyAssumptionLedgerEntry(
            code="two_dimensional_monte_carlo",
            severity=Severity.INFO,
            category="method",
            message="Assessment separates outer uncertainty draws from inner population-variability draws.",
            conservative=None,
        ),
        UncertaintyAssumptionLedgerEntry(
            code="regulatory_acceptance_not_implied",
            severity=Severity.WARNING,
            category="scope",
            message="Transparent regulatory-style modelling does not imply official regulator acceptance.",
            conservative=None,
        ),
    ]
    if weighted_sampling:
        ledger_entries.append(
            UncertaintyAssumptionLedgerEntry(
                code="survey_weighted_sampling",
                severity=Severity.INFO,
                category="survey_design",
                message="Subjects were resampled with normalized survey weights where provided.",
                conservative=None,
            )
        )
    else:
        ledger_entries.append(
            UncertaintyAssumptionLedgerEntry(
                code="unweighted_empirical_sampling",
                severity=Severity.WARNING,
                category="survey_design",
                message="No survey weights were supplied; subjects were resampled uniformly.",
                conservative=None,
            )
        )

    policy_sequence = (
        [
            CensoredDataPolicy.LOWER_BOUND_ZERO,
            CensoredDataPolicy.MIDDLE_BOUND_HALF_LOD_LOQ,
            CensoredDataPolicy.UPPER_BOUND_LOD_LOQ,
        ]
        if request.censored_data_policy == CensoredDataPolicy.THREE_BOUND_SENSITIVITY
        else [request.censored_data_policy]
    )
    if request.censored_data_policy == CensoredDataPolicy.THREE_BOUND_SENSITIVITY:
        ledger_entries.append(
            UncertaintyAssumptionLedgerEntry(
                code="three_bound_censored_sensitivity",
                severity=Severity.INFO,
                category="censored_data",
                message="Censored residues were evaluated as lower, middle, and upper bound scenarios.",
                conservative=True,
            )
        )

    policy_outputs: dict[CensoredDataPolicy, tuple[list[dict[str, float]], list[float], dict[str, list[float]]]] = {}
    for policy in policy_sequence:
        policy_outputs[policy] = _simulate_policy(
            request=request,
            subject_rows=subject_rows,
            fallback_residues=fallback_residues,
            models_by_commodity=models_by_commodity,
            policy=policy,
        )

    primary_policy = (
        CensoredDataPolicy.MIDDLE_BOUND_HALF_LOD_LOQ
        if request.censored_data_policy == CensoredDataPolicy.THREE_BOUND_SENSITIVITY
        else request.censored_data_policy
    )
    primary_outer_metrics, primary_health_values, primary_sensitivity_inputs = policy_outputs[primary_policy]
    distribution_summary = _summary_from_outer_metrics(primary_outer_metrics)
    censored_policy_summaries = {
        policy.value: _summary_from_outer_metrics(outer_metrics)
        for policy, (outer_metrics, _, _) in policy_outputs.items()
        if request.censored_data_policy == CensoredDataPolicy.THREE_BOUND_SENSITIVITY
    }

    health_reference_exceedance = _health_reference_summary(
        request,
        primary_outer_metrics,
        primary_health_values,
    )
    sensitivity_ranking = _sensitivity_ranking(primary_sensitivity_inputs, primary_outer_metrics)

    model_fingerprint = _fingerprint(
        {
            "version": _MODEL_VERSION,
            "residueUncertaintyModels": [
                model.model_dump(mode="json", by_alias=True)
                for model in request.residue_uncertainty_models
            ],
            "censoredDataPolicy": request.censored_data_policy.value,
            "healthReference": (
                request.health_reference.model_dump(mode="json", by_alias=True)
                if request.health_reference
                else None
            ),
        },
        "model",
    )
    input_fingerprint = _fingerprint(
        {
            "dataset": request.dataset.model_dump(mode="json", by_alias=True),
            "residueProfile": request.residue_profile.model_dump(mode="json", by_alias=True),
        },
        "input",
    )
    simulation_fingerprint = _fingerprint(
        {
            "randomSeed": request.random_seed,
            "outerIterationCount": request.outer_iteration_count,
            "innerIterationCount": request.inner_iteration_count,
            # Quantize the stochastic Monte-Carlo summary floats before hashing
            # so the simulation fingerprint is stable across platforms whose
            # floating-point results differ only in the last ULP (e.g.
            # macOS-ARM vs Linux-x86). The medians remain validated against the
            # case tolerances separately; this only stabilises the exact-match
            # fingerprint.
            "summary": _quantize_floats(
                distribution_summary.model_dump(mode="json", by_alias=True)
            ),
        },
        "simulation",
    )

    source_references = [
        SourceReference(
            source_id=f"dietary.dataset.{request.dataset.dataset_id}",
            title=f"Raw Survey Dataset: {request.dataset.dataset_id}",
        )
    ]
    if request.residue_profile.provenance and request.residue_profile.provenance.source_references:
        source_references.extend(request.residue_profile.provenance.source_references)

    return UncertaintyIntakeAssessment(
        datasetId=request.dataset.dataset_id,
        populationGroup=request.dataset.population_group,
        chemicalIdentity=request.residue_profile.chemical_identity,
        assessmentMode=request.assessment_mode,
        outerIterationCount=request.outer_iteration_count,
        innerIterationCount=request.inner_iteration_count,
        totalSubjects=len(subject_rows),
        weightedSampling=weighted_sampling,
        censoredDataPolicy=request.censored_data_policy,
        distributionSummary=distribution_summary,
        censoredPolicySummaries=censored_policy_summaries,
        healthReferenceExceedance=health_reference_exceedance,
        sensitivityRanking=sensitivity_ranking,
        uncertaintyAssumptionLedger=UncertaintyAssumptionLedger(entries=ledger_entries),
        reproducibility=UncertaintyReproducibilityRecord(
            randomSeed=request.random_seed,
            rngAlgorithm=_RNG_ALGORITHM,
            modelFingerprint=model_fingerprint,
            inputFingerprint=input_fingerprint,
            simulationFingerprint=simulation_fingerprint,
            numpyVersion=np.__version__,
            scipyVersion=scipy.__version__,
        ),
        qualityFlags=request.dataset.quality_flags + request.residue_profile.quality_flags,
        limitations=request.dataset.limitations
        + request.residue_profile.limitations
        + [
            LimitationNote(
                code="regulatory_style_uncertainty_assessment",
                message=(
                    "This tool provides transparent two-dimensional Monte Carlo review support; "
                    "it does not claim official equivalence to PRIMo, DEEM, DietEx, or regulator acceptance."
                ),
            )
        ],
        provenance=runtime.provenance.bundle(source_references),
    )
