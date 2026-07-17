from __future__ import annotations

import os

from dietary_mcp.errors import DietaryValidationError
from dietary_mcp.models import (
    MAX_CSV_TEXT_LENGTH,
    MAX_PROBABILISTIC_ITERATIONS,
    MAX_RAW_SURVEY_RECORDS,
    MAX_RESIDUE_RECORDS,
    MAX_TARGET_JURISDICTIONS,
    MAX_UNCERTAINTY_INNER_ITERATIONS,
    MAX_UNCERTAINTY_OUTER_ITERATIONS,
)


DEFAULT_MAX_RAW_SURVEY_RECORDS = 10_000
DEFAULT_MAX_RESIDUE_RECORDS = 500
DEFAULT_MAX_CSV_BYTES = 1_000_000
DEFAULT_MAX_PROBABILISTIC_ITERATIONS = 100_000
DEFAULT_MAX_PROBABILISTIC_DRAWS = 2_000_000
DEFAULT_MAX_TARGET_JURISDICTIONS = 50
DEFAULT_MAX_UNCERTAINTY_OUTER_ITERATIONS = 1_000
DEFAULT_MAX_UNCERTAINTY_INNER_ITERATIONS = 1_000
DEFAULT_MAX_UNCERTAINTY_DRAWS = 2_000_000

ENV_MAX_RAW_SURVEY_RECORDS = "DIETARY_MCP_MAX_RAW_SURVEY_RECORDS"
ENV_MAX_RESIDUE_RECORDS = "DIETARY_MCP_MAX_RESIDUE_RECORDS"
ENV_MAX_CSV_BYTES = "DIETARY_MCP_MAX_CSV_BYTES"
ENV_MAX_PROBABILISTIC_ITERATIONS = "DIETARY_MCP_MAX_PROBABILISTIC_ITERATIONS"
ENV_MAX_PROBABILISTIC_DRAWS = "DIETARY_MCP_MAX_PROBABILISTIC_DRAWS"
ENV_MAX_TARGET_JURISDICTIONS = "DIETARY_MCP_MAX_TARGET_JURISDICTIONS"
ENV_MAX_UNCERTAINTY_OUTER_ITERATIONS = "DIETARY_MCP_MAX_UNCERTAINTY_OUTER_ITERATIONS"
ENV_MAX_UNCERTAINTY_INNER_ITERATIONS = "DIETARY_MCP_MAX_UNCERTAINTY_INNER_ITERATIONS"
ENV_MAX_UNCERTAINTY_DRAWS = "DIETARY_MCP_MAX_UNCERTAINTY_DRAWS"

HARD_MAX_PROBABILISTIC_DRAWS = MAX_PROBABILISTIC_ITERATIONS * MAX_RAW_SURVEY_RECORDS
HARD_MAX_UNCERTAINTY_DRAWS = (
    MAX_UNCERTAINTY_OUTER_ITERATIONS * MAX_UNCERTAINTY_INNER_ITERATIONS * MAX_RAW_SURVEY_RECORDS
)


def _configured_limit(env_name: str, default: int, hard_ceiling: int) -> int:
    raw_value = os.getenv(env_name)
    if raw_value is None:
        return default
    try:
        parsed = int(raw_value)
    except ValueError:
        return default
    if parsed < 1:
        return default
    return min(parsed, hard_ceiling)


def _raise_limit_error(
    *,
    label: str,
    observed: int,
    runtime_limit: int,
    hard_ceiling: int,
    env_name: str,
    metric: str,
    code: str = "input_limit_exceeded",
) -> None:
    raise DietaryValidationError(
        code=code,
        message=f"{label} contains {observed} {metric}, which exceeds the runtime limit of {runtime_limit}.",
        suggestion=(
            f"Reduce the request size or raise {env_name} up to the hard ceiling of {hard_ceiling} "
            "after confirming the workload is intentional."
        ),
        details={
            "label": label,
            "observed": observed,
            "runtimeLimit": runtime_limit,
            "hardCeiling": hard_ceiling,
            "envVar": env_name,
            "metric": metric,
        },
    )


def enforce_raw_survey_record_limit(count: int) -> None:
    runtime_limit = _configured_limit(
        ENV_MAX_RAW_SURVEY_RECORDS,
        DEFAULT_MAX_RAW_SURVEY_RECORDS,
        MAX_RAW_SURVEY_RECORDS,
    )
    if count > runtime_limit:
        _raise_limit_error(
            label="raw survey dataset",
            observed=count,
            runtime_limit=runtime_limit,
            hard_ceiling=MAX_RAW_SURVEY_RECORDS,
            env_name=ENV_MAX_RAW_SURVEY_RECORDS,
            metric="records",
        )


def enforce_residue_record_limit(count: int) -> None:
    runtime_limit = _configured_limit(
        ENV_MAX_RESIDUE_RECORDS,
        DEFAULT_MAX_RESIDUE_RECORDS,
        MAX_RESIDUE_RECORDS,
    )
    if count > runtime_limit:
        _raise_limit_error(
            label="residue evidence",
            observed=count,
            runtime_limit=runtime_limit,
            hard_ceiling=MAX_RESIDUE_RECORDS,
            env_name=ENV_MAX_RESIDUE_RECORDS,
            metric="records",
        )


def enforce_csv_byte_limit(csv_text: str) -> None:
    observed = len(csv_text.encode("utf-8"))
    runtime_limit = _configured_limit(
        ENV_MAX_CSV_BYTES,
        DEFAULT_MAX_CSV_BYTES,
        MAX_CSV_TEXT_LENGTH,
    )
    if observed > runtime_limit:
        _raise_limit_error(
            label="CSV payload",
            observed=observed,
            runtime_limit=runtime_limit,
            hard_ceiling=MAX_CSV_TEXT_LENGTH,
            env_name=ENV_MAX_CSV_BYTES,
            metric="bytes",
        )


def enforce_probabilistic_iteration_limit(count: int) -> None:
    runtime_limit = _configured_limit(
        ENV_MAX_PROBABILISTIC_ITERATIONS,
        DEFAULT_MAX_PROBABILISTIC_ITERATIONS,
        MAX_PROBABILISTIC_ITERATIONS,
    )
    if count > runtime_limit:
        _raise_limit_error(
            label="probabilistic intake summary",
            observed=count,
            runtime_limit=runtime_limit,
            hard_ceiling=MAX_PROBABILISTIC_ITERATIONS,
            env_name=ENV_MAX_PROBABILISTIC_ITERATIONS,
            metric="iterations",
        )


def enforce_probabilistic_draw_limit(iteration_count: int, total_subjects: int) -> None:
    observed = iteration_count * total_subjects
    runtime_limit = _configured_limit(
        ENV_MAX_PROBABILISTIC_DRAWS,
        DEFAULT_MAX_PROBABILISTIC_DRAWS,
        HARD_MAX_PROBABILISTIC_DRAWS,
    )
    if observed > runtime_limit:
        _raise_limit_error(
            label="probabilistic intake summary",
            observed=observed,
            runtime_limit=runtime_limit,
            hard_ceiling=HARD_MAX_PROBABILISTIC_DRAWS,
            env_name=ENV_MAX_PROBABILISTIC_DRAWS,
            metric="bootstrap draws",
            code="probabilistic_draw_limit_exceeded",
        )


def enforce_target_jurisdiction_limit(count: int) -> None:
    runtime_limit = _configured_limit(
        ENV_MAX_TARGET_JURISDICTIONS,
        DEFAULT_MAX_TARGET_JURISDICTIONS,
        MAX_TARGET_JURISDICTIONS,
    )
    if count > runtime_limit:
        _raise_limit_error(
            label="target jurisdictions",
            observed=count,
            runtime_limit=runtime_limit,
            hard_ceiling=MAX_TARGET_JURISDICTIONS,
            env_name=ENV_MAX_TARGET_JURISDICTIONS,
            metric="jurisdictions",
        )


def enforce_uncertainty_iteration_limits(outer_iteration_count: int, inner_iteration_count: int) -> None:
    outer_runtime_limit = _configured_limit(
        ENV_MAX_UNCERTAINTY_OUTER_ITERATIONS,
        DEFAULT_MAX_UNCERTAINTY_OUTER_ITERATIONS,
        MAX_UNCERTAINTY_OUTER_ITERATIONS,
    )
    if outer_iteration_count > outer_runtime_limit:
        _raise_limit_error(
            label="uncertainty intake assessment",
            observed=outer_iteration_count,
            runtime_limit=outer_runtime_limit,
            hard_ceiling=MAX_UNCERTAINTY_OUTER_ITERATIONS,
            env_name=ENV_MAX_UNCERTAINTY_OUTER_ITERATIONS,
            metric="outer iterations",
        )

    inner_runtime_limit = _configured_limit(
        ENV_MAX_UNCERTAINTY_INNER_ITERATIONS,
        DEFAULT_MAX_UNCERTAINTY_INNER_ITERATIONS,
        MAX_UNCERTAINTY_INNER_ITERATIONS,
    )
    if inner_iteration_count > inner_runtime_limit:
        _raise_limit_error(
            label="uncertainty intake assessment",
            observed=inner_iteration_count,
            runtime_limit=inner_runtime_limit,
            hard_ceiling=MAX_UNCERTAINTY_INNER_ITERATIONS,
            env_name=ENV_MAX_UNCERTAINTY_INNER_ITERATIONS,
            metric="inner iterations",
        )


def enforce_uncertainty_draw_limit(
    outer_iteration_count: int,
    inner_iteration_count: int,
    total_subjects: int,
) -> None:
    observed = outer_iteration_count * inner_iteration_count * max(total_subjects, 1)
    runtime_limit = _configured_limit(
        ENV_MAX_UNCERTAINTY_DRAWS,
        DEFAULT_MAX_UNCERTAINTY_DRAWS,
        HARD_MAX_UNCERTAINTY_DRAWS,
    )
    if observed > runtime_limit:
        _raise_limit_error(
            label="uncertainty intake assessment",
            observed=observed,
            runtime_limit=runtime_limit,
            hard_ceiling=HARD_MAX_UNCERTAINTY_DRAWS,
            env_name=ENV_MAX_UNCERTAINTY_DRAWS,
            metric="two-dimensional simulation draws",
            code="uncertainty_draw_limit_exceeded",
        )
