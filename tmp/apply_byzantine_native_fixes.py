from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text(encoding="utf-8")

# Native parser bindings required for symbolic c:/g:/s: arguments.
block = """\n; Native parser bindings for symbolic unit/building/status/SN identifiers.
(defconst monk 125)
(defconst town-center 109)
(defconst castle 82)
(defconst keep 235)
(defconst bombard-tower 236)
(defconst guard-tower 234)
(defconst watch-tower 79)
(defconst outpost 598)
(defconst scout-cavalry-line 448)
(defconst lumber-camp 562)
(defconst mining-camp 584)
(defconst stable 101)
(defconst archery-range 87)
(defconst barracks 12)
(defconst siege-workshop 49)
(defconst status-resource 3)
(defconst list-active 0)
(defconst status-ready 2)
(defconst villager-class 904)
(defconst object-data-id 0)
(defconst object-data-dropsite 14)
(defconst ri-man-at-arms 222)
(defconst sn-intelligent-gathering 142)
(defconst sn-retask-gather-amount 148)
(defconst sn-livestock-to-town-center 263)
(defconst sn-wild-animal-exploration 300)
(defconst sn-maximum-hunt-drop-distance 235)
(defconst sn-maximum-food-drop-distance 234)
(defconst sn-preferred-mill-placement 253)
(defconst sn-boar-lure-destination 295)
(defconst sn-maximum-wood-drop-distance 233)
(defconst sn-object-repair-level 246)
(defconst sn-enable-boar-hunting 244)
(defconst sn-minimum-boar-lure-group-size 252)
(defconst sn-minimum-boar-hunt-group-size 204)
(defconst sn-minimum-number-hunters 245)
(defconst sn-cap-civilian-explorers 3)
(defconst sn-percent-civilian-explorers 0)
(defconst sn-focus-player-number 251)
(defconst sn-stone-gatherer-percentage 119)
(defconst sn-defer-dropsite-update 273)
(defconst sn-allow-adjacent-dropsites 272)
(defconst sn-dropsite-separation-distance 248)
(defconst sn-mill-max-distance 87)
"""
needle = "(defconst wheelbarrow 213)\n"
if block.strip() not in s:
    if s.count(needle) != 1:
        raise SystemExit("wheelbarrow anchor missing")
    s = s.replace(needle, needle + block, 1)

for phase in ("21", "22"):
    old = f"""(defrule
    (goal byzantine-scout-phase {phase})
    (up-compare-goal 384 > 0)
=>
    (up-full-reset-search)
    (up-modify-sn sn-focus-player-number g:= byzantine-scout-focus-player)"""
    new = f"""(defrule
    (goal byzantine-scout-phase {phase})
    (up-compare-goal 384 > 0)
=>
    (up-modify-sn sn-focus-player-number g:= byzantine-scout-focus-player)"""
    if old not in s:
        raise SystemExit(f"phase {phase} reset pattern missing")
    s = s.replace(old, new, 1)

old = """(defrule
    (or
        (goal byzantine-scout-phase 1)
        (or
            (goal byzantine-scout-phase 2)
            (or
                (goal byzantine-scout-phase 3)
                (or
                    (goal byzantine-scout-phase 4)
                    (or
                        (goal byzantine-scout-phase 5)
                        (or
                            (goal byzantine-scout-phase 6)
                            (or
                                (goal byzantine-scout-phase 7)
                                (or
                                    (goal byzantine-scout-phase 8)
                                    (or
                                        (goal byzantine-scout-phase 9)
                                        (or
                                            (goal byzantine-scout-phase 15)
                                            (or
                                                (goal byzantine-scout-phase 16)
                                                (or
                                                    (goal byzantine-scout-phase 17)
                                                    (or
                                                        (goal byzantine-scout-phase 18)
                                                        (or
                                                            (goal byzantine-scout-phase 20)
                                                            (or
                                                                (goal byzantine-scout-phase 21)
                                                                (goal byzantine-scout-phase 22)
                                                            )
                                                        )
                                                    )
                                                )
                                            )
                                        )
                                    )
                                )
                            )
                        )
                    )
                )
            )
        )
    )
    (not (unit-type-count scout-cavalry-line >= 1))
=>
    (set-goal byzantine-scout-phase 0)
    (disable-timer byzantine-scout-intel-timer)
)"""
new = """(defrule
    (up-compare-goal byzantine-scout-phase > 0)
    (not (unit-type-count scout-cavalry-line >= 1))
=>
    (set-goal byzantine-scout-phase 0)
    (disable-timer byzantine-scout-intel-timer)
)"""
if old not in s:
    raise SystemExit("scout recovery pattern missing")
s = s.replace(old, new, 1)

old = """            (and
                (building-type-count-total town-center >= 2)
                (not (building-type-count-total town-center >= 3))
                (building-type-count farm < bt-imperial-farm-target-2tc)
            )"""
new = """            (and
                (building-type-count-total town-center >= 2)
                (and
                    (not (building-type-count-total town-center >= 3))
                    (building-type-count farm < bt-imperial-farm-target-2tc)
                )
            )"""
if old not in s:
    raise SystemExit("farm arity pattern missing")
s = s.replace(old, new, 1)

old = """    (goal byzantine-siege-scale byzantine-siege-scale-fortified)
    (goal demand-imperial-bombard-floor 0)
    (unit-type-count-total bombard-cannon"""
new = """    (goal byzantine-siege-scale byzantine-siege-scale-fortified)
    (unit-type-count-total bombard-cannon"""
if old not in s:
    raise SystemExit("bombard duplicate pattern missing")
s = s.replace(old, new, 1)

old = """    (wood-amount > 5000)
    (goal demand-economy-farm-boom-imperial 0)
    (or"""
new = """    (wood-amount > 5000)
    (or"""
if old not in s:
    raise SystemExit("farm duplicate pattern missing")
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
