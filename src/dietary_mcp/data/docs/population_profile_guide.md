# Population Profile Guide

Consumption profiles are governed defaults, not hidden runtime constants.

Each profile must make these semantics explicit:

- population group
- region
- source profile or survey basis
- body-weight context
- acute applicability
- chronic applicability
- commodity coverage
- limitations and known gaps

The bundled illustrative screening set currently covers:

- `adult_general`
- `child_1_6`
- `adolescent_11_17`
- `older_adult_65_plus`
- `pregnant_adult`

across thirteen canonical commodity codes:

- `apples`
- `oranges`
- `spinach`
- `tomatoes`
- `potatoes`
- `rice`
- `wheat`
- `milk`
- `chicken`
- `salmon`
- `eggs`
- `oats`
- `beans_and_pulses`

New profile packs should be added through the registry, not hard-coded in tools.
