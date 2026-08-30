# PCBA_4Fan_Controller — Four-Fan PWM/Tach Controller

**Benchmark ID:** 04  
**Difficulty:** 2/5  
**Brief detail:** 1/5  
**Category:** mixed-power-digital  
**Likely layer count:** 2  
**Primary stressors:** PWM/tach routing, 12V distribution, connector density, power thermal

## Design brief

Build a board that powers and controls four standard 4-wire 12 V PC fans. A microcontroller should generate independent PWM and read independent tach signals. Accept a single 12 V input, derive logic power locally, include sensible protection, and provide a simple host interface. Keep it compact and serviceable.

## Benchmark intent

This brief is intentionally one member of a heterogeneous PCBA-autodesign benchmark. Treat stated requirements as authoritative; where the brief leaves choices open, make and document reasonable engineering decisions rather than inventing hidden user requirements. The repository should remain a consumer of the shared `PCBA_AutoDesignAndTest` toolkit rather than accumulating board-specific logic in the toolkit.
