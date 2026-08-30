# Sources — Four-Fan PWM/Tach Controller

The evidence this board's design will have to cite. **Classes of document, not
documents:** the specific parts are not chosen yet, so naming a datasheet here
would be choosing one.

A number that reaches the board carries its provenance: source, document id or
URL, retrieval date, units, and the condition it applies under. A number without
that is not evidence, and no live network lookup may change a validation or
release result.

| Kind of source | What the design needs from it |
|---|---|
| 4-wire PC fan interface documentation (the de-facto standard plus representative fan datasheets) | Establishes PWM input frequency range and drive requirements, tach output type and pulses per revolution, and pin order — none of which the brief states but all of which the design depends on. |
| Candidate microcontroller datasheet: timer/PWM channel count, capture inputs, I/O ratings, package thermal data | Must substantiate four independent PWM outputs and four usable capture or interrupt inputs on routable pins for whichever generation approach is chosen, plus absolute maximum ratings for any tach interface. |
| Voltage regulator datasheet and application notes for the conversion topology chosen for the local logic supply | Needed for input range at 12 V, dropout or efficiency, load capability, and thermal derating that supports any junction-temperature claim. |
| Fan current and startup-surge data for the assumed fan class | The brief names no fan, so the 12 V distribution, connection current ratings, and any fuse must be sized against a cited current figure rather than an invented one. |
| Protection device datasheets for whatever devices are selected | Any claim about reverse-polarity, overcurrent, transient, or electrostatic-discharge behaviour must trace to clamping, trip, or rating parameters of a real part. |
| Datasheets for the parts chosen to terminate the fan, 12 V input, and host connections | Per-contact current rating, pitch, keying, retention, and mating cycles feed both the current budget and the compactness and serviceability arguments. |
| Conductor sizing and spacing references (IPC-2221 / IPC-2152 class) | Trace width for the fan current at a stated temperature rise, and clearance between the 12 V net and logic nets, need an external basis. |
| Fabricator capability page for the layer count actually chosen | Minimum trace and space, available copper weights, drill and annular ring limits bound what the routing plan can actually claim. |
| Assembly-house part availability and basic/extended part listings | Supports part selection and placement cost decisions with evidence rather than preference. |
| Electrostatic-discharge and transient immunity standards | Required only if the design states an immunity level for its user-accessible connections; any stated level must name the standard and test level. |
| Shared PCBA_AutoDesignAndTest toolkit documentation | Defines the expected repository layout, configuration schema, and test hooks this repo must consume without adding board-specific logic to the toolkit. |

## Recording a source, once one is chosen

Replace the class with the actual document — manufacturer, part number, revision
and date — and state the fact taken from it, in the units the document uses.
Keep the class row: it says why the document was needed.

JLCPCB-wide process limits are **not** recorded here. They live in the toolkit's
`profiles/jlcpcb/`, with their own provenance; this board records only its own
tighter targets and its own selected options. A limit copied into two places is
a rival threshold, and the toolkit has a gate that says so.
