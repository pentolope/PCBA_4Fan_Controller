# PCBA_4Fan_Controller — Four-Fan PWM/Tach Controller
## Design brief

Build a board that powers and controls four standard 4-wire 12 V PC fans. A microcontroller should generate independent PWM and read independent tach signals. Accept a single 12 V input, derive logic power locally, include sensible protection, and provide a simple host interface. Keep it compact and serviceable.

## Functional requirements

- Four channels driven and measured independently; a stalled, shorted or unplugged fan must not disturb the others.
- Duty must cover the range the 4-wire control interface defines, identically on every channel.
- Tach must read as a rate convertible to RPM; an absent or stalled fan must be distinguishable from one commanded off.

## Fan channel interface

- PWM outputs must run inside the band the 4-wire fan standard allows, sink its control-input current at a valid low, and tolerate the fan's pull-up with the logic rail unpowered.
- Tach inputs must supply their own pull-up, present a load the fan can pull low, and pass every pulse at top speed.

## Power and protection

- 12 V in is the only external supply; the logic rail comes from it on board and holds through fan inrush.
- Per-channel current must be stated, connectors and copper must carry all four at once, and fan return must not share the tach reference.
- Reverse polarity, a fan pin shorted to 12 V or ground, back-EMF, overcurrent on one channel, host hot-plug and handling ESD must leave the board and the other channels working; recovery must be documented.

## Connectors, service and test

- One connector per fan, mating a standard 4-wire PC fan plug in the standard pin order, keyed and labelled per channel.
- The host interface is one connector, needs no host power, and at least sets duty and reports tach and fault state per channel.
- Any fan must be unpluggable by hand while the others run; outline no larger than connectors and power path require.
- In-system reprogramming and test points on protected 12 V, the logic rail, ground and every PWM and tach net, board installed.

## Open choices

- MCU family and package: four independent PWM outputs at the fan drive frequency and resolution needed, four independent tach captures, the host peripheral, in-system programming.
- Logic rail voltage and regulator topology; host interface type and connector; whether fan 12 V is permanent or switched per channel; whether channel current is sensed; overcurrent shared or per channel, self-recovering or replaceable.
