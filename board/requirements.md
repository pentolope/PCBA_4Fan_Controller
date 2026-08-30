# Requirements — Four-Fan PWM/Tach Controller

Two lists. The difference between them is the whole point of this file.

A **fixed requirement** is something [BRIEF.md](../BRIEF.md) asks for. Each one
below quotes the brief text that substantiates it; if a statement cannot be
quoted, it is not a requirement here. An **open decision** is a choice the brief
deliberately left to whoever designs this board.

> Missing details are design freedom, not permission to fabricate unstated user
> requirements.

Promoting a decision into a requirement is the failure this file exists to
prevent. Record a choice under the decision it answers, with the reasoning that
made it — never by adding it to the list above.

Bound to `BRIEF.md` SHA-256 `531862b585105d510d5cae2a7e9f812644b966f14cebd01fc22d28720cdb2ca3`.

## Fixed by the brief

### REQ-01 — The board shall power and control four standard 4-wire 12 V PC fans.

Brief text:

> Build a board that powers and controls four standard 4-wire 12 V PC fans.

### REQ-02 — A microcontroller on the board shall generate PWM for each fan independently (four independent PWM outputs).

Brief text:

> A microcontroller should generate independent PWM and read independent tach signals.

### REQ-03 — The microcontroller shall read the tach signal of each fan independently (four independent tach inputs).

Brief text:

> generate independent PWM and read independent tach signals

### REQ-04 — The board shall accept a single 12 V input. The brief fixes one 12 V input; it does not state that this input is the board's only source of energy, so whether anything else (for example the host connection) also supplies power is a decision for the design agent to make and record.

Brief text:

> Accept a single 12 V input, derive logic power locally

### REQ-05 — Logic power shall be derived locally on the board rather than supplied externally.

Brief text:

> Accept a single 12 V input, derive logic power locally

### REQ-06 — The design shall include protection. The brief qualifies it only as "sensible" and names no fault modes or devices, so the scope and means of protection must be chosen and justified by the design agent.

Brief text:

> derive logic power locally, include sensible protection

### REQ-07 — The board shall provide a host interface, and that interface shall be simple.

Brief text:

> include sensible protection, and provide a simple host interface.

### REQ-08 — The board shall be compact. No dimension is stated, so the design agent must define and record what compact means for this board.

Brief text:

> and provide a simple host interface. Keep it compact and serviceable.

### REQ-09 — The board shall be serviceable. No mechanism is stated, so the design agent must define and record what serviceability means for this board.

Brief text:

> Keep it compact and serviceable.

### REQ-10 — Stated requirements are authoritative; where the brief is open, the design agent shall make and document reasonable engineering decisions and shall not invent hidden user requirements.

Brief text:

> Treat stated requirements as authoritative; where the brief leaves choices open, make and document reasonable engineering decisions rather than inventing hidden user requirements.

### REQ-11 — This repository shall remain a consumer of the shared PCBA_AutoDesignAndTest toolkit; board-specific logic shall not be pushed into the toolkit.

Brief text:

> The repository should remain a consumer of the shared `PCBA_AutoDesignAndTest` toolkit rather than accumulating board-specific logic in the toolkit.

## Open — the design agent decides

### OPEN-01 — Microcontroller selection: family, package, pin count, clock source, memory, and programming/debug interface.

The brief says only "A microcontroller" and names no device, vendor, or architecture.

*Decision:* **not yet made.**

### OPEN-02 — Logic rail voltage and the conversion topology used to derive it from 12 V (linear versus switching, and the resulting quiescent and thermal behaviour).

The brief requires that logic power be derived locally but states no rail voltage, no load current, and no conversion method.

*Decision:* **not yet made.**

### OPEN-03 — Host interface protocol, physical layer, physical connection, addressing/command model, and whether any isolation is provided.

The brief asks only for "a simple host interface" and defines neither the bus nor what simple means here.

*Decision:* **not yet made.**

### OPEN-04 — PWM generation approach: frequency, duty resolution, whether hardware timer channels or software generation is used, and how the drive level is matched to the fan PWM input.

The brief requires independent PWM but fixes no frequency, resolution, or drive characteristic; those follow from the fan interface convention and the chosen MCU, not from the brief.

*Decision:* **not yet made.**

### OPEN-05 — Tach input conditioning: interface to the fan's tach output, any level translation or filtering, protection of the MCU input, and whether edges are captured by interrupt, timer capture, or polling.

The brief requires independent tach reading but says nothing about signal levels, pull-up arrangement, or capture method.

*Decision:* **not yet made.**

### OPEN-06 — Scope and means of protection: which fault modes are covered (for example reverse input polarity, overcurrent, input transients, electrostatic discharge at exposed connections, fan stall or shorted fan output) and by what circuit means each is handled.

The brief asks for "sensible protection" without enumerating fault modes, protection devices, or any immunity level to be met.

*Decision:* **not yet made.**

### OPEN-07 — Whether the 12 V feed to each fan is individually switched, fused, or current-limited, or whether all four fans share one common unswitched 12 V rail.

The brief requires that the board power the fans but does not state per-channel power control, fusing, or current limiting.

*Decision:* **not yet made.**

### OPEN-08 — The 12 V current budget: assumed per-fan steady-state and startup current, total input current, and therefore conductor widths, connector current ratings, and any fuse rating.

The brief names no fan wattage, model, or current, so every current figure in the design is an assumption the agent must state and justify, not a given.

*Decision:* **not yet made.**

### OPEN-09 — How the four fans attach to the board: connector series or termination style, pitch, orientation, keying, and pin order convention for the 4-wire interface.

The brief says the fans are "standard 4-wire 12 V PC fans" but names no connector part number, type, pitch, or footprint.

*Decision:* **not yet made.**

### OPEN-10 — How the 12 V input arrives at the board — termination style, part selection, and its mating and retention scheme.

The brief states a single 12 V input but does not specify how that input arrives at the board.

*Decision:* **not yet made.**

### OPEN-11 — Board outline, dimensions, mounting hole pattern, edge placement of the external connections, and any keep-out or enclosure constraint.

"Compact" is unquantified and the brief gives no mechanical envelope, mounting scheme, or enclosure.

*Decision:* **not yet made.**

### OPEN-12 — Concrete realisation of serviceability: test points, silkscreen labelling and channel identification, accessibility and orientation of the external connections, replaceable versus resettable protection, and debug/programming access.

The brief asks for a serviceable board but defines no serviceability features or acceptance criteria.

*Decision:* **not yet made.**

### OPEN-13 — Stackup: final layer count, copper weight, and the plane or pour strategy for the 12 V and return paths.

The layer count comes from benchmark metadata as a likely value, not from the brief; no copper weight or plane arrangement is stated anywhere.

*Decision:* **not yet made.**

### OPEN-14 — Control policy: whether fan speed is commanded entirely by the host, partly or wholly by on-board logic, and what the board does at power-up or when the host is absent or silent.

The brief describes the control hardware but is silent on control behaviour, defaults, and fail-safe response.

*Decision:* **not yet made.**

### OPEN-15 — Local indicators, status LEDs, user controls, and any on-board sensing input.

The brief mentions none of these; adding them is a design choice, and assuming a temperature input or local setpoint control would be inventing a requirement.

*Decision:* **not yet made.**

### OPEN-16 — Whether firmware is a deliverable of this repository, and if so its architecture and its boundary with the shared toolkit.

The brief requires a microcontroller but never states firmware scope, while the benchmark intent only constrains what may go into the shared toolkit.

*Decision:* **not yet made.**

### OPEN-17 — Whether any source other than the 12 V input contributes power to the board — for example a host connection or a programming/bring-up link that carries power — and how the board behaves when such a source is present or absent.

The brief fixes a single 12 V input and requires logic power to be derived locally, but never states that the 12 V input is the board's only source of energy.

*Decision:* **not yet made.**

## Where a decision gets recorded

1. Answer it under its `OPEN-nn` heading above, with the reasoning and the
   evidence that made the choice.
2. Set `chosen` and `rationale` on the matching entry in
   [requirements.json](requirements.json).
3. Cite the datasheet or standard in [docs/sources.md](../docs/sources.md).

A choice recorded this way stays visibly a choice. That is what lets a later
reader tell this board's engineering apart from its brief.

## Where this board is most likely to be faked

Places where a design run would be tempted to assert something it cannot
substantiate:

- Part invention: the brief names no microcontroller, regulator, or connector. The most likely failure is silently adopting a familiar MCU or a familiar fan connector as if the brief specified it, instead of recording it as a justified choice.
- Fabricated current budget: no fan wattage or current appears in the brief or metadata. Every trace width, fuse rating, contact rating, and thermal claim rests on an assumed per-fan current that must be written down as an assumption with a source.
- Stressors treated as solutions: "power thermal" and "connector density" are problems to analyse. Claiming a copper pour area, a heatsink, or a specific connector layout as if the brief called for it converts a stressor into a fabricated requirement.
- Unsupported protection claims: "sensible protection" is the entire text. Statements like ESD-protected or reverse-polarity-safe are unsubstantiated without a named fault-mode list and device datasheet parameters.
- Fan interface parameters asserted rather than cited: PWM frequency, PWM drive level, tach pull-up arrangement, and pulses per revolution come from the 4-wire fan convention and fan datasheets, not from this brief.
- Layer count treated as fixed: 2 is the benchmark metadata's likely value, not a brief requirement. Both presenting it as mandated and silently moving to four layers without recording why are failure modes.
- Mechanical and environmental back-fill: "compact and serviceable" is unquantified, and the brief says nothing about where the board sits or what airflow reaches it. Inventing a board size, enclosure, mounting pattern, or a self-cooled in-airflow thermal environment and then designing to it as a given would corrupt the problem.
- Supply architecture over-read: the brief fixes a single 12 V input and local logic derivation, but does not declare that input the board's only energy source. Both asserting that as a requirement and quietly drawing power from the host link without recording it are failure modes.
