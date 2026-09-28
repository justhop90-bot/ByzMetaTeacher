# Player knowledge matrix (replaces provisional 42% with per-domain measurement)
Columns: community-knowledge | native-support | compiler | strategic-rep | execution-rep | verification.
Tokens: OK / PARTIAL / MISSING.

| domain | community | native | compiler | strategic | execution | verification |
|---|---|---|---|---|---|---|
| economy opening (housing/dropsite) | OK | OK | OK | PARTIAL | OK | PARTIAL |
| age transitions + escrow | OK | PARTIAL | PARTIAL | PARTIAL | PARTIAL | NO |
| farm/dropsite/boom/sustain | OK | PARTIAL | PARTIAL | PARTIAL | PARTIAL | NO |
| construction + retry | OK | OK | OK (PR86 unmerged) | OK | OK | PARTIAL |
| production + queue | OK | PARTIAL | PARTIAL | PARTIAL | PARTIAL | NO |
| research + prereq | OK | PARTIAL | PARTIAL | OK | PARTIAL | NO |
| military composition/counters | PARTIAL | PARTIAL | MISSING | MISSING | PARTIAL | NO |
| scouting/lure (DUC) | OK | OK-structure | MISSING (emission) | MISSING | MISSING | NO |
| attack control/posture/TSA | OK | PARTIAL | MISSING | MISSING | MISSING | NO |
| resource control/escrow/starvation | OK | PARTIAL | MISSING | PARTIAL | PARTIAL | NO |
| adaptation/recovery | PARTIAL | PARTIAL | PARTIAL | PARTIAL | PARTIAL | NO |
| map conditions/loads | OK | OK | OK | PARTIAL | OK | PARTIAL |
| civ data (Byzantine) | PARTIAL | OK | PARTIAL | OK | PARTIAL | PARTIAL |
| civ data (broad) | MISSING | OK | MISSING | MISSING | MISSING | NO |
| late game/exhaustion | PARTIAL | PARTIAL | MISSING | MISSING | MISSING | NO |

Reading: knowledge exists for ~11/15 domains; compilable execution exists for ~5/15.
The player gap = DUC emission + attack lifecycle + escrow lowering + strategy synthesis.
Next measurable milestone: Tier-1 economy/production/research player fully compilable
(construction merged + SN/timer alloc + escrow-claim + queue model), then military tier.
