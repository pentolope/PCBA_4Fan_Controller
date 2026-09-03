# Toolkit requests from board 04 (QuadFanController)

What this board needed from `PCBA_AutoDesignAndTest` and did not get, what it
had to build for itself that every other board will have to build again, and
what it still cannot establish about its own reliability.

Written after taking the board to a release-ready state: 22 applicable gates
pass, 177 requirement claims stand at 176 PASS and 1 UNKNOWN, `release-check`
reports RELEASE READY. Everything below is therefore a request about the *next*
board as much as this one.

**Every request here is board-agnostic by construction.** Board 04 appears only
as evidence — what it measured, what it cost, what it could not answer. Nothing
asks the toolkit to learn anything about fans, four channels, or this netlist.
Where a board must supply something specific, the request says so and names the
declaration, not the value.

I surveyed `pcbqa/` before writing this. Section E lists what already exists and
must not be rebuilt; several things I expected to ask for are already there.

---

## A. Blockers hit while building this board

These cost real time on board 04 and will cost it again unchanged. They are
ordered by how much they cost.

### A1. The router grades the board against a floor it lowers itself

**Problem.** `KiCadRoutingTools` carries its own fab-capability floor —
`py_router/fab_tiers.py` gives a two-layer `standard` board 0.127 mm clearance
and 0.127 mm track width — and individual routing steps escalate *below* the
nominal `--clearance` to fit tight geometry. `py_router/clearance_ledger.py`
records the tightest value any step used, and its own docstring states where
that value goes: into `fix_project_for_output`, which rewrites the sibling
`.kicad_pro` DRC floor so the board is subsequently graded at the relaxed
value.

This board declares 0.15 mm and is graded at 0.15 mm. Every clearance violation
I chased for several routing cycles — 37 in one candidate, 42 in another, all
between 0.116 mm and 0.144 mm — was copper that is legal at 0.127 and illegal
at 0.15. Nothing in the flow said so. The router reported success; the summary
field `min_clearance_used: 0.127` was the only trace, and it is not surfaced by
any gate.

Passing `--fab-overrides` with the board's declared constraints fixed it
completely: the accepted candidate then reported `min_clearance_used: 0.3`, the
full nominal, and the violations disappeared at the source rather than being
patched afterwards.

**Request.** The toolkit's routing entry point should own this:

1. derive the router's fab-floor override file from the board's declared
   constraints (the same values `DRC.CONSTRAINT_FLOOR` already checks) and pass
   it on every invocation, so the router cannot emit copper the checker will
   reject;
2. read back the router's reported minimum clearance and **refuse the
   candidate** when it is below the board's declared clearance, naming both
   numbers;
3. detect that a router invocation rewrote the project's DRC floor and treat it
   as a finding, not as housekeeping. A tool lowering the threshold a later gate
   reads is check-weakening arriving through the back door, and the board author
   currently has to know it happens to defend against it.

**Done when** a board whose declared clearance is tighter than the router's tier
floor either routes at its declared clearance or fails with a message naming the
two floors — and no board-owned code has to know that `fab_tiers.py` exists.

### A2. The router is not deterministic, and the candidate search is board-owned

**Problem.** The same placed board, the same ordering, the same options,
re-run: 0 errors, then 44, then 64. Attempts 1 and 2 reproduced exactly while
attempt 3 did not, so this is not a seeded search the caller can pin.

That makes routing a search whose acceptance must be repeated, and every board
must therefore own: attempt loop, ordering list, per-attempt staging, the
acceptance predicate, retry-on-rejection, and the provenance record of what was
tried. `design/route.py` on this board is ~300 lines of exactly that, and
`routing_record.py` validates the record it produces but does not produce it.

**Request.** A toolkit-owned candidate search: the board declares the router
options, the orderings, the attempt budget and the acceptance predicate (as a
set of counters that must be zero — this board uses errors, warnings,
unconnected, schematic parity); the toolkit runs the attempts, stages each one,
applies the declared transforms, measures, promotes the first accepted candidate
into the authoritative board and emits the record `routing_record.validate`
already knows how to check. It should also report the accept rate across
attempts, because that number is the honest measure of how reproducible a
board's routing is.

**Done when** a board can obtain an accepted, recorded routing run without
owning a loop, and two runs of the same board report the same verdict even
though the router does not return the same copper.

### A3. Post-router geometry repair is board-owned and easy to get wrong

**Problem.** Router output is not directly acceptable. This board needed seven
transforms, all generic, none board-specific:

- snap a track end standing inside a same-net via's annulus onto its centre;
- pull a track end that stopped inside a same-net pad's outline onto the pad
  anchor (a 45° corner landing in the cut corner of a rounded rectangle reads as
  connected to KiCad's connectivity and as a bare end to everything else);
- drop tracks a snap collapsed to zero length;
- widen any track the router necked below the declared floor;
- restore the declared size on any via the router narrowed;
- absorb chamfer fragments a few tens of microns long into their single
  neighbour, away from pads and vias;
- prune dangling ends.

The last three are only safe under a connectivity-invariance guard: apply,
rebuild connectivity, and revert if the unconnected count rose. I wrote that
guard three times across two stages of this work.

**Request.** These transforms belong in the toolkit, each with the invariance
guard built in, each reporting what it changed so the routing record can carry
it. The board should declare which to apply and with what tolerances, not
implement them.

**Done when** a board gets router output into an acceptable state by declaring a
transform list, and the effects appear in the routing record without board-side
bookkeeping.

### A4. KiCad object identity has a trap that silently disables correct code

**Problem.** `str(track.m_Uuid)` returns a SWIG proxy repr — an address, reused
as objects are freed. On this board, **1190 tracks shared 3 distinct strings**.
Code comparing track identities that way is not merely wrong, it is wrong in the
direction that looks fine: my dangling-end prune skipped nothing, because every
track matched itself out of the neighbour scan and then held its own ends up.
The prune reported `dangling_tracks_removed: 0` for weeks of work while the
geometry gate kept reporting dangling ends, and the two facts never met.
`m_Uuid.AsString()` is the correct accessor.

**Request.** A `pcbqa` helper — `item_id(item)` — that returns the KIID string,
used by every toolkit path that compares board items, and one sentence in the
KiCad-interaction documentation stating the trap. This is three lines of code
that prevents a class of silent failure no test naturally catches, because the
broken version produces plausible output.

### A5. Saving a board rewrites the project document

**Problem.** `pcbnew.SaveBoard` rewrites the sibling `.kicad_pro` with KiCad's
own defaults, discarding the board's declared rule severities. On this board
that surfaced as `DRC.NO_SUPPRESSED_RULES` failing with five rules set to
"ignore" that the board never set to ignore. The fix — rewrite the project
document after every save — has to be remembered at every call site.

**Request.** A `pcbqa` save entry point that preserves the project document, and
which board-side layout code can use instead of `pcbnew.SaveBoard` directly.

### A6. Gate findings are not addressable

**Problem.** `ROUTE.GEOMETRY_HYGIENE` reports, for example,
`net=+3V3, layer=F.Cu, x_mm=71.8, y_mm=-42.9`. Those are KiCad-frame
coordinates with y negated, not board coordinates, and there is no item
identity. Locating each finding meant mapping the frame by hand and then
searching the board for copper near the point — several times per routing cycle,
and once with the wrong sign, which sent me looking at empty board area.

**Request.** Geometry findings should carry the board-frame coordinate *and* the
offending item's identity: net, layer, KIID, and where applicable the footprint
reference and pad number. `feedback.py` already establishes the principle — a
finding must name what failed, where, by how much, and which variables may move
— so this is asking the geometry gates to emit what that module already models.

**Done when** a finding can be resolved to the item it is about without a
coordinate-frame conversion in the reader's head.

### A7. Placement seeds need measured footprint geometry, not guesses

**Problem.** Seeding placement means knowing a footprint's courtyard extent and
where pad 1 sits after rotation. Both are empirical: rotation 90 puts pad 1
below the footprint centre and 270 above it; a vertical pin header places pad 1
at the origin and runs in −y. I discovered each by producing a board, running
DRC, reading the overlap, and adjusting — and eventually wrote a scratch script
to measure courtyard bounding boxes from the library so the constants could be
derived rather than guessed.

**Request.** A small geometry query on top of the footprint libraries:
courtyard extent, pad-1 position and pad centroid for a given footprint at a
given rotation. `geom.py` already reads pad outlines and mask openings from a
board; this is the same question asked of a library before a board exists.

### A8. `checks.<tool>.output` accepts a path that lands in the repository root

**Minor.** This board's manifest declared `"drc": {"output": "drc.json"}`; the
report landed at the repository root as an untracked file and nothing
complained. My fault, but the schema could refuse an output path that is not
inside a declared generated location.

---

## B. What the remaining stages need

Per `AUTONOMOUS_PCBA_AGENT.md`, this board has completed through §20 and §32.
§21–§26 are open. Some of what they need already exists; the gaps below are the
parts that do not.

### B1. A wired path from a board to the extraction modules that already exist

**Problem.** `extract.py`, `electrical_path.py`, `propagation.py`,
`coupling_geometry.py` and `stackup_physical.py` are present and do most of what
§21.1 asks. Board 04 uses none of them, and its `TIMING.*`, `STACK.PHYSICAL` and
`PROV.TIMING_MODELS` gates all report NOT_APPLICABLE because the manifest
declares no `timing` section. The capability exists; the route from a board to
it does not, and nothing tells a board author it is there.

**Request.** A documented opt-in: what a board declares to get Tier-1
extraction, what physical inputs it must supply as parameter records, and which
gates become applicable when it does. A worked minimal example in the toolkit's
own fixtures is worth more than prose.

**Done when** a board can obtain per-net conductor length, cross-section, DC
resistance, via inventory and reference-plane context as claims by declaring
inputs, without reading module source to discover the calling convention.

### B2. Pre-layout versus post-layout comparison (§22)

**Problem.** `simulation.required_stages` on this board is `["pre_layout"]`.
The scenario contract supports `model_instance`, and `extract.py` already offers
`interconnect_model_from_path` — a two-terminal model from a traced path — so
the primitives for substitution exist. What does not exist is the comparison the
doc actually asks for: *pre-layout model vs post-layout model*, stating which
quantity moved and by how much.

**Request.** A stage-comparison artifact and gate: given the same scenario run
in two stages, report per measurement the pre value, the post value, the change,
and whether the assertion's margin narrowed. A post-layout stage that merely
passes tells the reader nothing about what layout cost.

**Done when** a board can answer "did the routed copper change this margin, and
by how much" from an artifact rather than by diffing two reports by eye.

### B3. DC power integrity (§23) — absent

**Problem.** No module in `pcbqa` addresses IR drop, source-to-load DC
resistance over routed copper, current bottlenecks or plane spreading
resistance; a grep for the concepts returns nothing. Board 04 declares
`INPUT_PATH_BUDGET_OHM = 0.2` and `BOARD_COPPER_BUDGET_OHM = 0.03` as *budgets*
and has no way to measure what its routed rail and return actually are. It
carries 4 A through one input path and cannot state the drop.

`extract.py:path_resistance` gets close — DC resistance over an actual traversal
between two pads — but it refuses when the net carries filled zone copper, which
is precisely the case for a poured power rail and a ground return, so it does
not answer the power question.

**Request.** A DC distribution analysis: given a source pad, a set of load pads
and their currents, report the resistance and voltage drop along each path
**including plane and pour copper**, identify the narrowest point and the vias
carrying the most current, and emit claims with the model and its omissions
stated. Zone copper is the hard part and the reason this cannot be assembled
from what exists.

**Done when** a board that declares a rail's source, loads and currents receives
a measured drop it can compare against a declared budget, and a via or neck that
carries more current than the rest is named.

### B4. Thermal estimation (§24) — absent

**Problem.** No thermal capability exists. Two of this board's claims sit
exactly on the failure mode the agent doc names by hand — a junction temperature
from a generic package number whose boundary conditions do not match:

- `blocking_device_dissipation_within_its_rating` (Q1), omitting *"the package's
  power rating is quoted on the datasheet's own test board; the copper this
  board gives the drain is a layout quantity and is not yet measured"*;
- `regulator_junction_within_its_rating` (U2), omitting the same for its tab.

The copper now exists. The omissions can be closed, and cannot be closed by
anything in the toolkit.

**Request.** A copper-aware thermal estimate: pad and plane copper area attached
to a part, thermal via conductance, declared ambient and airflow as explicit
inputs, and a result **labelled an estimate** with its validity envelope stated.
It should refuse to emit a junction-temperature claim when the declared boundary
conditions fall outside the validity of the θJA it was given, rather than
quietly extrapolating — the doc asks for that refusal specifically.

**Done when** a dissipating part's claim can cite measured attached copper
instead of omitting it, and a board whose conditions do not match its
datasheet's test board is told so.

### B5. Design-for-assembly checks (§25) — absent

**Problem.** `gates/g_assembly.py` is BOM and CPL *parity* — it proves the
schematic, board and packaged files agree on what gets soldered. It is not DFA.
Nothing checks component height, insertion or mating access, side-of-board
population, paste segmentation on a thermal tab, hand-solder sets, moisture
sensitivity, or fiducials.

Board 04 is a case where access is a real constraint and is currently unchecked:
four fan headers and a screw terminal sit on the board edge, and nothing
verifies a plug can be inserted, or that a mating connector's body does not
collide with a neighbouring part.

**Request.** Assembly constraints as board-declared, toolkit-checked geometry:
height limits per region, keep-clear volumes for connector insertion and mating,
population side, and paste-mask rules. The connector contracts this board
already declares are the natural place to attach a mating envelope.

### B6. External and manual release dependencies (§25, §32)

**Problem.** Some release conditions cannot be established locally — the doc
names JLCPCB's assembly preview. Today they are either silently assumed or
recorded as prose that no gate reads.

**Request.** A manifest-declared external dependency with an acknowledgement
artifact: what must be checked outside the toolkit, by whom, and a recorded
result with a digest, so `release-check` blocks until an unacknowledged
dependency is either satisfied or explicitly declined. Recording it as an
open dependency is honest; assuming it silently is not.

### B7. Verification-method classification (§26)

**Problem.** Claims carry `evidence_class` (this board: 101
`datasheet-behavioral`, 66 `design-source`, 10 `assumed-behavioral`) and
`phenomenon` (all 177 `device_electrical`), but not the strongest verification
method available for the requirement. The doc's enumeration — STATIC, GEOMETRY,
ANALYTIC, CIRCUIT_SIM, DIGITAL_SIM, EXTRACTED, EM_SIM, THERMAL_SIM,
MANUFACTURING_CHECK, PHYSICAL_TEST, DOCUMENTATION — has no representation in
`claim.py`.

The consequence is that this board cannot say the true thing about several
requirements. Connector mating, TVS survival to a real ESD event, and the fan's
own rotor-lock behaviour are `PHYSICAL_TEST` and nothing else. Today the mating
requirement is the board's single UNKNOWN, which reads like an oversight rather
than like a correct statement that a bench test is required.

**Request.** A method field on claims, a gate that every significant requirement
names its strongest available method, and — the part that matters — a verdict
shape for "physical validation required" that is neither a FAIL nor an UNKNOWN
that looks like a gap. The doc says the agent should be rewarded for saying it;
right now there is nowhere to say it.

### B8. Board-contract export for firmware (§6.3)

**Problem.** This design determines firmware behaviour and records it only as
prose in comments: the PWM drivers are external open-drain N-FETs, so the
timer's channel polarity must be inverted; the 25 kHz target comes out as
ARR = 639 on a 16 MHz HSI; and the control gate sits at 2.664 V under the MCU's
internal pull-up before firmware runs, which constrains what the pin may be
configured to at boot. Firmware that gets any of these wrong runs the fans
backwards or full-speed. The doc's rule is not to maintain two independently
edited copies of the board contract, and today there is only prose to copy from.

**Request.** Generated machine-readable board contract: pin assignments,
voltage domains, clock sources, per-pin polarity and boot-state constraints,
derived from the netlist the board already declares. Format is the toolkit's
call; the requirement is that it is generated, not authored twice.

---

## C. Verifying this board's reliability

Three things I want and cannot get, all generic.

### C1. Flow repeatability

Given A2, "this board routes clean" is a statement about one run. The honest
claim is about the distribution: run generate → route → validate N times from
the same sources and report whether the verdict is stable and which gates ever
differ. That number belongs in the release evidence for any board whose routing
came from a non-deterministic search — which, today, is all of them.

### C2. Omission-closure report

Every claim states what it omits. Some omissions name quantities that were
unmeasurable at the stage the claim was written and are measurable now: on this
board, 8 of 177 claims omit a layout or thermal quantity that the routed board
now contains. I found that with an ad-hoc script to answer a question about what
work remained.

**Request.** A report listing every claim whose omissions name a quantity the
current stage can measure. It is the work list for post-layout verification,
it is derivable from the claim records the toolkit already owns, and it turns
"what is left to do" from a judgement call into a query.

### C3. Per-gate negative coverage

`tests/fixtures/negative/` holds one fixture, which drives 15 of the 36 gates to
FAIL. The other 21 have no fixture proving they fail when they should. A gate
that cannot be shown to bite is indistinguishable from a gate that always
passes, and the discipline this toolkit applies to boards — unknown is not pass
— applies to the checker too.

**Request.** Per-gate negative coverage, ideally by programmatic mutation of a
clean fixture: shrink a via below the annulus target, add a dangling track,
widen a fragment, break schematic parity, relax a project rule, and assert that
exactly the corresponding gate fails. Mutation is preferable to hand-built
fixtures because it stays honest as gates change.

---

## D. Constraints these requests must respect

Stated so no request above is read as licence to relax any of them:

- **Genericity.** Nothing in `pcbqa/` may know a board name. Every request above
  is phrased as a board declaration plus a toolkit behaviour.
- **Fail-closed.** A capability that cannot be evaluated reports ERROR and
  blocks. An extraction that cannot establish its inputs must refuse, not
  approximate silently.
- **Never weaken a check.** A1 is a request to *enforce* this at the router
  boundary, where a third-party tool currently lowers a threshold the toolkit
  later reads.
- **No live network in a verdict.** Anything acquired from outside is frozen
  with a digest first; B6 asks for a recorded acknowledgement, not a live query.
- **Never modify the authoritative board in place.** The candidate search in A2
  promotes a candidate; it does not edit the board being searched from.
- **Models carry provenance, applicability and omissions.** B3 and B4 in
  particular must state their model and what it leaves out — they are the two
  most tempting places to emit a bare number.

---

## E. Already present — do not rebuild

Surveyed before writing this, and deliberately not requested:

| Module | Covers |
| --- | --- |
| `extract.py` | Tier-1 geometry parasitics, parameter records with provenance, path resistance, two-terminal interconnect models |
| `electrical_path.py` | ElectricalPath across nets and through series parts, path resolution against copper |
| `propagation.py` | Analytic delay from geometry and physical stackup, with evidence ranking and via policy |
| `coupling_geometry.py` | Measured parallel-run inventory (geometry, explicitly not a crosstalk voltage) |
| `stackup_physical.py` | Physical vs structural stackup, reference geometry |
| `critical_topology.py` | Deterministic local copper at declared fabrication values |
| `placement.py`, `feedback.py` | Semantic placement constraints; structured downstream-to-placement feedback records |
| `routing_record.py` | Validation of the routing record and its agreement with the adopted board |
| `connectivity.py`, `geom.py` | Copper connectivity by geometric intersection; native pad/mask/via geometry |
| `sim/` | Scenario contract, ngspice backend, model registry, digital |
| `fabricators/` | JLCPCB catalogue, acquisition, selection, impedance, stackup export |
| `claim.py`, `closure.py` | Evidence and numeric-claim contracts; source closure identity |

The pattern across A and B is that the toolkit's *analysis* layer is strong and
its *board-facing* layer is thin: the capabilities exist but each board hand-
rolls the path to them, and the two places where a board meets an external tool
— the router, and anything outside the repository — are where it silently
inherits someone else's standards instead of its own.
