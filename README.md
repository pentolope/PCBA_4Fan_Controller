# Four-Fan PWM/Tach Controller

Board that powers and controls four standard 4-wire 12 V PC fans, with a microcontroller giving independent PWM and tach per fan from a single 12 V input.

This repository holds the design problem for a four-channel PC fan controller. The brief fixes the function and almost nothing else: four standard 4-wire 12 V PC fans are powered and controlled from the board, a microcontroller generates independent PWM and reads independent tach signals, the board accepts a single 12 V input and derives its logic power locally, protection is required, and a simple host interface is to be provided. It also asks that the board be kept compact and serviceable, without stating any dimension, outline, or mounting scheme.

At brief detail 1/5, everything below that statement of function is left to the design agent: microcontroller family, logic rail voltage and regulator topology, host interface protocol and physical connection, how the fans and the 12 V input attach to the board, per-fan current budget, what "sensible protection" concretely covers, board outline, and stackup. Those choices belong in the design record as decisions with rationale, not as requirements attributed to the brief.

> **This board has not been designed.** There is no schematic, no layout and no
> part selection here — only the brief, a reading of the brief, and the
> scaffolding a design run needs. That is the intended state of this repository,
> not a gap in it.

## What the brief fixes, and what it leaves open

The brief pins down 11 requirements and deliberately leaves
17 decisions to whoever designs the board. The `Source` column says
which is which: `brief` is quoted from [BRIEF.md](BRIEF.md), `metadata` comes
from the benchmark catalogue, and `open` means the brief does not fix it.

| Aspect | Value | Source |
|---|---|---|
| Fan channels | Four standard 4-wire 12 V PC fans, powered and controlled by the board | brief |
| Fan control signals | Independent PWM per fan (four independent PWM outputs) | brief |
| Fan feedback signals | Independent tach read per fan (four independent tach inputs) | brief |
| Control element | A microcontroller performs PWM generation and tach reading; no family, package, or vendor named | brief |
| Power input | A single 12 V input, accepted by the board; the brief fixes one 12 V input and says nothing about whether anything else (for example the host link) also supplies power | brief |
| Logic power | Derived locally on the board rather than supplied externally; rail voltage and conversion method not stated | brief |
| Protection | Protection is required; the brief says only "sensible" and names no fault modes or devices | brief |
| Host interface | A simple host interface is to be provided; protocol, physical layer, and physical connection not specified | brief |
| Mechanical intent | Compact and serviceable; no dimensions, outline, mounting pattern, or enclosure stated | brief |
| Likely layer count | 2 | metadata |
| Category / difficulty / brief detail | mixed-power-digital; difficulty 2/5; detail 1/5 | metadata |
| Primary stressors | PWM/tach routing, 12V distribution, connector density, power thermal | metadata |
| Microcontroller, regulator, and connector selection | Not fixed by the brief — design agent's choice, to be justified in the design record | open |
| Board outline, stackup, and 12 V current budget | Not fixed by the brief — design agent's choice; no size, copper weight, or per-fan current is stated | open |
| Whether any supply other than the 12 V input exists | Not fixed by the brief — one 12 V input is fixed and logic power must be derived locally, but the brief does not say whether the host connection or a programming/bring-up link may also carry power; the design agent decides and records this | open |

The full split, with the verbatim brief text substantiating every fixed
requirement, is in [board/requirements.md](board/requirements.md) and
machine-readably in [board/requirements.json](board/requirements.json).

**Missing details are design freedom, not permission to fabricate unstated user
requirements.** A choice the brief left open is recorded as a decision, with its
reasoning — never promoted into a requirement.

## Benchmark position

| | |
|---|---|
| Benchmark id | 4 of 32 |
| Category | mixed-power-digital |
| Difficulty | 2 / 5 |
| Brief detail | 1 / 5 |
| Likely layer count | 2 |
| Primary stressors | PWM/tach routing, 12V distribution, connector density, power thermal |

This is a mixed-power-digital board at difficulty 2/5 with a detail 1/5 brief — a modest circuit whose difficulty lies in the interface between a 12 V power path and low-voltage digital control on a likely 2-layer stackup. The named stressors are PWM/tach routing, 12V distribution, connector density, and power thermal: four fan connections plus the 12 V input and the host interface all have to land on a board the brief asks to keep "compact", whatever connector scheme is chosen, while eight switching and feedback signals route alongside the fan current path. Because the brief specifies function but no parts, voltages, currents, or geometry, it primarily tests whether an agent can carry a thin brief forward with documented engineering decisions instead of back-filling invented user requirements.

This repository is one of thirty-two. The suite, the protocol and the results
live in [PCBA_AutoDesignAndTest_Bench](https://github.com/pentolope/PCBA_AutoDesignAndTest_Bench).

## Repository layout

| Path | Contents |
|---|---|
| `BRIEF.md` | the supplied brief — authoritative, preserved byte for byte, never edited |
| `board/requirements.md` | what the brief fixes, what it leaves open, and where decisions get recorded |
| `board/requirements.json` | the same split, machine-readable, each fixed requirement bound to brief text |
| `board/manifest.template.json` | the toolkit's minimum manifest, pre-filled for this board |
| `board/toolchain.json` | where this board's build finds KiCad and the router |
| `benchmark/metadata.json` | the supplied catalogue entry — category, difficulty, detail, stressors |
| `docs/architecture.md` | the decisions this board must make, as questions, unanswered |
| `docs/sources.md` | the classes of evidence the design will have to cite |
| `docs/status.md` | what exists, what does not, and what is deliberately absent |
| `candidates/` | disposable search output, ignored by Git |
| `.claude/skills/` | the claim-audit and accountability-review skills [CLAUDE.md](CLAUDE.md) requires before a push |
| `tooling/PCBA_AutoDesignAndTest` | the shared verification/routing/release toolkit, as a pinned submodule |

## Getting the repository

The toolkit is a submodule and carries KiCad Routing Tools as a submodule of its
own, so clone recursively:

```bash
git clone --recursive https://github.com/pentolope/PCBA_4Fan_Controller.git
```

```bash
git submodule update --init --recursive
```

## Designing the board

Generic verification, routing and release logic is **not** written here. It is
consumed from `tooling/PCBA_AutoDesignAndTest`, which is board-agnostic by
construction and must stay that way; this repository owns the board and nothing
else. Start from
[the toolkit's onboarding guide](tooling/PCBA_AutoDesignAndTest/examples/onboarding.md),
and see [CLAUDE.md](CLAUDE.md) for the rules a design run works under.

```bash
python3 tooling/PCBA_AutoDesignAndTest/run.py preflight
```

## Brief integrity

`BRIEF.md` SHA-256 `531862b585105d510d5cae2a7e9f812644b966f14cebd01fc22d28720cdb2ca3`

Every quotation in `board/requirements.json` is bound to those exact bytes. If
the brief ever changes, the bindings are stale by construction — which is the
point of recording the digest.
