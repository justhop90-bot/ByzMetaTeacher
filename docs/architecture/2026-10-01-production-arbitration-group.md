# Production Arbitration Group Contract

The strategy layer normally maps each StrategicDemandSpec to its own production arbitration owner through `StrategicBinding.strategic_id`.

Some strategic packages are intentionally multiple demands inside one higher-level execution domain. Those demands may set `StrategicDemandSpec.production_arbitration_group`, which is copied into `StrategicBinding` and takes precedence for `TRAIN_ARBITRATION` claim ownership.

This is compiler policy only. It does not merge strategic identities, targets, witnesses, lifecycle state, or package arbitration. It only allows compatible execution claims to share the existing production arbitration contract.

The Byzantine counter layer uses the `defense` production group. Threat arbitration still decides which counter package is active; production arbitration only prevents mutually compatible defense trains from producing false RES-006 owner conflicts.