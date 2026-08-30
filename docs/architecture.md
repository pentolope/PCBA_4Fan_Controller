# Architecture — Four-Fan PWM/Tach Controller

**A worksheet, not a design.** Every line below is a question this board has to
answer, and none of them is answered here. Nothing in this file is a
recommendation, and the order of the sections carries no preference.

The questions were derived from [the brief](../BRIEF.md) and from what this
board is meant to stress in the benchmark:

- PWM/tach routing
- 12V distribution
- connector density
- power thermal

Those are the places where a wrong answer shows up in copper.

Answer them in this file as the design is made, each answer carrying the
evidence that supports it, and record the corresponding choice against its
`OPEN-nn` entry in [board/requirements.md](../board/requirements.md). An answer
without evidence is a guess wearing a document's clothes — and this benchmark is
allowed to refuse an unsupported claim rather than invent one.

## Fan channel architecture and 12 V distribution

- Do all four fans share one 12 V node, or does each channel get its own switch, fuse, or current limit — and what does the requirement that the board "powers" the fans imply for that node?
- What per-fan steady-state and startup current is being assumed, and on what evidence, given that the brief names no fan?
- How does the 12 V current path enter the board, reach the four fan connections, and return, and where is the highest current density on the chosen stackup?
- What happens electrically if one fan is unplugged, stalled, or short-circuited, and does that fault reach the other three channels or the logic rail?
- How are the four fan returns arranged relative to the logic ground so tach and PWM references stay clean?

## PWM generation and drive to the fan

- Which PWM frequency and duty resolution are chosen for the fan control input, and what source justifies that frequency range for 4-wire PC fans?
- How are the four independent PWM outputs generated — hardware timer channels, software generation, or a mix — what does that approach cost in MCU resources and timing jitter, and does the chosen device offer four such outputs on routable pins?
- What voltage and drive strength does the fan PWM input require, and does the chosen logic rail meet it directly or need translation?
- What is the PWM state during MCU reset, before firmware runs, and on firmware fault — do the fans run, stop, or float?
- Is the PWM line loaded or terminated in any way, and what does that do to edge rate and to conducted noise on the 12 V rail?

## Tach capture and input conditioning

- What is the electrical nature of the fan tach output, what pull-up does it require, and to which rail is that pull-up returned?
- If the tach pull-up were referenced to 12 V, how is the MCU input protected from exceeding its absolute maximum rating?
- How many pulses per revolution are assumed, and what source establishes that for the fan class in question?
- Are the four tach inputs captured by interrupt, timer capture, or polling, and does the chosen MCU have four suitable inputs available simultaneously with four PWM outputs?
- What is the expected tach frequency range across the controllable speed range, and does the capture method resolve both ends of it?
- How is a stopped or disconnected fan distinguished from a fan running below the measurable range?

## Local logic power derivation

- What logic rail voltage is chosen, and what total load does it actually have to supply once the MCU, pull-ups, indicators, and host interface are counted?
- Linear or switching conversion from 12 V — and what power is dissipated in the regulator at that load with a 12 V input?
- What input voltage range must the converter tolerate once input transients and the protection scheme are accounted for?
- Where does the regulator sit relative to the fan connections and the 12 V path, and what is its thermal path on the chosen stackup?
- What is the power-up sequence, and how is the MCU held in a defined state until the logic rail is valid?

## Protection scope and justification

- Which fault modes is this board claiming to survive, and which is it explicitly not covering?
- Is reverse polarity on the 12 V input handled, and by what means and at what forward loss?
- What overcurrent element, if any, protects the input and the individual fan channels, and how is its rating derived from the assumed current budget?
- What transient or inductive-kickback energy can appear on the 12 V rail from four motor loads, and what absorbs it?
- Which pins are user-accessible and therefore exposed to electrostatic discharge, and what is the protection at each?
- For every protection claim, which device datasheet parameter substantiates it?

## Host interface

- Which bus and physical layer implement the "simple host interface", and what makes that choice simple in this board's context?
- What carries it physically, and does the host side also supply anything, or is the single 12 V input the board's only supply?
- What command and telemetry model does the host see, how much control and reporting is exposed to it versus handled on-board, and what justifies that scope?
- Is any isolation, series protection, or level translation needed between the host connection and the MCU?
- What is the board's behaviour when the host link is idle, disconnected, or sending nothing?

## Connector density and board outline

- How many external connections must land on the board in total, in what termination style, and what edge length does that consume at the chosen pitch?
- What board outline and dimensions result, and by what argument is that outline "compact" for this connection count?
- Are the fan connections oriented so four fan cables can be routed and dressed without fouling each other or the input and host connections?
- What mounting hole pattern is provided, and what mechanical loading do the cables impose on the board?
- Does the placement leave a routable channel for eight PWM and tach signals on the chosen layer count?

## Thermal design of the power path

- Which components dissipate meaningfully at full fan load — regulator, any pass or switching element, protection devices, connector contacts?
- What copper area and stackup does each dissipating part have, and what junction temperature does that imply at the assumed load?
- What ambient temperature and airflow condition is assumed at the board, and on what basis — where is the board taken to sit relative to the fans it drives, given the brief says nothing about its placement?
- Are any thermal claims backed by a datasheet thermal resistance figure and a stated copper area, rather than asserted?

## Routing plan on the chosen stackup

- Where does the ground return for the tach and PWM signals run relative to the fan current path, and does the chosen layer count leave a continuous return under them?
- How are the eight low-voltage control signals kept away from the switching and motor current nodes?
- What clearance is used between the 12 V net and logic nets, and what standard or fabricator rule sets it?
- What trace width carries the fan current, and what conductor-sizing reference and temperature rise produced that number?
- If two layers proves insufficient, what is the trigger for going to four, and where is that decision recorded?

## Serviceability, bring-up and test

- What must a technician be able to measure or replace in the field, and does the layout expose it?
- Which nets, if any, get test points so the 12 V rail, logic rail, each PWM output, and each tach input can be probed?
- How is a fan traced to its control channel without a schematic, and what marking or labelling scheme achieves that?
- How is the MCU programmed and re-programmed after assembly, and is that access preserved when fans are connected?
- What is the power-on test sequence that proves all four channels drive and report independently?

## Component selection record

- For each chosen part — MCU, regulator, protection devices, connectors — what requirement drove the choice, and what alternatives were rejected and why?
- Which parts are available from the intended fabrication and assembly route, and what is the evidence?
- Which selections are load-bearing for the current budget or thermal claims and would need re-checking if the assumed fan current changes?
- Where is each assumption recorded as an assumption rather than restated as a brief requirement?

## Answers still owed

All of them. See [status.md](status.md).
