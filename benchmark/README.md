# Benchmark entry — board 4 of 32

[metadata.json](metadata.json) is the supplied catalogue entry for this board,
preserved byte for byte from the seed pack. It is the same record that appears
in `boards_index.json` in
[PCBA_AutoDesignAndTest_Bench](https://github.com/pentolope/PCBA_AutoDesignAndTest_Bench), and the two must agree.

| | |
|---|---|
| Repository | `PCBA_4Fan_Controller` |
| Board id | `quad_fan_controller` |
| Category | mixed-power-digital |
| Difficulty | 2 / 5 |
| Brief detail | 1 / 5 |
| Likely layer count | 2 |
| Primary stressors | PWM/tach routing, 12V distribution, connector density, power thermal |

`difficulty` is how hard the board is. `detail` is how much of it the brief
states — and a low `detail` is not a low bar. A detail-1 brief leaves the
architecture open on purpose, and an agent that fills the silence with invented
user requirements has failed the board more thoroughly than one that designs it
badly.

This is a mixed-power-digital board at difficulty 2/5 with a detail 1/5 brief — a modest circuit whose difficulty lies in the interface between a 12 V power path and low-voltage digital control on a likely 2-layer stackup. The named stressors are PWM/tach routing, 12V distribution, connector density, and power thermal: four fan connections plus the 12 V input and the host interface all have to land on a board the brief asks to keep "compact", whatever connector scheme is chosen, while eight switching and feedback signals route alongside the fan current path. Because the brief specifies function but no parts, voltages, currents, or geometry, it primarily tests whether an agent can carry a thin brief forward with documented engineering decisions instead of back-filling invented user requirements.

## What goes here

Compact results only: metrics, verdicts, and the commit each was measured at.
The evidence for a result is the artefact the toolkit recomputes, not a summary
of it.

Routing search output, candidate pools, build trees and field-solver dumps do
**not** go here. They are ignored by [.gitignore](../.gitignore) and are
regenerated from what is committed. Thirty-two repositories share one benchmark
clone; weight here is paid thirty-two times.

## Protocol

The attempt protocol is defined once, in the umbrella repository, so that
thirty-two boards cannot drift into thirty-two protocols. See
[PCBA_AutoDesignAndTest_Bench/BENCHMARK.md](https://github.com/pentolope/PCBA_AutoDesignAndTest_Bench/blob/main/BENCHMARK.md).
