from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from dietary_mcp.models import DietaryIntakeScenarioDefinition, DietaryIntakeSummary, ModelFamily, ScenarioClass


@dataclass(frozen=True)
class PluginKey:
    scenario_class: ScenarioClass
    model_family: ModelFamily


class DietaryPlugin(Protocol):
    key: PluginKey
    limitations: list[str]

    def run(self, scenario: DietaryIntakeScenarioDefinition) -> DietaryIntakeSummary: ...
