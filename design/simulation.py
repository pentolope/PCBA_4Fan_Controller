"""Circuit scenarios, and what each one is allowed to establish.

Four questions the schematic can answer before any copper exists.

  * The logic supply is fed through a diode from the same rail the fans are,
    so four fans taking the standard's start-up surge at once is the load
    case that could pull it under. The reservoir behind that diode is what
    is being asked about.
  * The control output has to reach a valid low inside its on-time against
    whatever capacitance the fan cable and the clamp add - the standard
    states the level and the sink current, and nothing else about the
    network the level has to appear across.
  * The sense input has to resolve every pulse at the top rotation rate the
    board claims, through a two-pole network the requirement report can only
    bound by hand.
  * With nothing driving either gate, the channel must be off and its fan at
    full speed, which is the state the standard defines for a fan that sees
    no control signal.

The elements are resistors, capacitors and ideal sources, because that is
what the scenario contract accepts; every device that is not one of those is
a declared stand-in, and each stand-in says what it replaces.

One question is deliberately absent. The hold-up reservoir rides through a
collapse of the fan supply because a diode stops it discharging backwards,
and a linear network cannot represent a device whose whole contribution is
that it blocks. That claim stays where it can be stated honestly - in the
requirement report, as arithmetic over the reservoir and its load.
"""
from __future__ import annotations

import json
import os
import sys

from . import netlist, rules

REPO_ROOT = rules.REPO_ROOT
SIM_DIR = os.path.join(REPO_ROOT, "sim")

#: How long the rail is watched after the four channels are switched on.
INRUSH_WINDOW_S = 20.0e-3

#: How many control and sense periods each edge scenario runs for.
EDGE_PERIODS = 3

#: The released control level the fan must see, as a fraction of the level
#: its own pull-up presents. A design target, not a standard figure: the
#: standard defines the low level and says nothing about the high one.
CONTROL_HIGH_FRACTION = 0.9


def _parameters():
    return rules.load_parameters()


def _sum_capacitance(*nets, derate=True):
    """Every capacitor on the named nets, at the low end of its tolerance.

    Low, because every question these scenarios ask is about a rail falling
    or an edge arriving late, and less capacitance answers both worse.
    """
    parameters = _parameters()
    total = 0.0
    for net in nets:
        for pin_ref in netlist.NETS[net]:
            reference = pin_ref.split(".", 1)[0]
            if not reference.startswith("C"):
                continue
            value = rules._capacitance_farads(reference)
            if derate:
                tolerance = parameters["parts"][netlist.PARTS[reference][
                    "mpn"]]["capacitor"]["tolerance"]["value"]
                value *= 1.0 - tolerance
            total += value
    return total


def _ideal(records):
    return {name: {"stands_in_for": detail,
                   "accepted_for_design_decision": True}
            for name, detail in records.items()}


def _measurement(name, kind, node, op=None, value=None, knowledge=None):
    record = {"name": name, "kind": kind, "node": node}
    if op is not None:
        record["assertion"] = {"op": op, "value": value}
    if knowledge is not None:
        record["knowledge"] = knowledge
    return record


def _pulse(v1, v2, period_s, delay_s=None):
    delay = period_s / 20.0 if delay_s is None else delay_s
    return {"v1": v1, "v2": v2, "delay_s": delay,
            "rise_s": period_s / 1.0e6, "fall_s": period_s / 1.0e6,
            "width_s": period_s / 2.0, "period_s": period_s}


# ---------------------------------------------------------------------------

def logic_rail_inrush_scenario(parameters):
    """Four fans taking the standard's start-up surge at the same instant.

    The supply is placed at the board's input terminal, because that is where
    the declared input range is measured; the field wiring is the
    integrator's budget and appears in the fault-current claim, not here. So
    what this scenario adds over the arithmetic is the dynamics: how far the
    reservoir behind the hold-up diode actually moves while the surge lands.
    """
    supply = rules.Supply(parameters)
    surge_a = (netlist.CHANNEL_COUNT
               * netlist.FAN_SPEC_STARTUP_CURRENT_MAX_A
               + supply.logic_current_max_a)
    return {
        "name": "logic_rail_on_simultaneous_fan_inrush",
        "description": "every channel takes the 4-wire standard's maximum "
                       "start-up current at once, and the reservoir that "
                       "feeds the logic regulator is watched",
        "elements": [
            {"kind": "vsource_dc", "name": "SRC", "nodes": ["src", "0"],
             "value": supply.input_min_v},
            {"kind": "resistor", "name": "RBLOCK", "nodes": ["src", "rail"],
             "value": supply.blocking_rds_ohm},
            {"kind": "capacitor", "name": "CBULK", "nodes": ["rail", "0"],
             "value": _sum_capacitance("V12P")},
            {"kind": "resistor", "name": "RFANS", "nodes": ["rail", "sink"],
             "value": supply.protected_min_v / surge_a},
            {"kind": "vsource_pulse", "name": "START", "nodes": ["sink", "0"],
             "pulse": _pulse(supply.input_min_v, 0.0, 2 * INRUSH_WINDOW_S,
                             delay_s=INRUSH_WINDOW_S / 20.0)},
            {"kind": "resistor", "name": "RDIODE", "nodes": ["rail", "hold"],
             "value": (supply.holdup_diode_drop_v
                       / supply.logic_current_max_a)},
            {"kind": "capacitor", "name": "CHOLD", "nodes": ["hold", "0"],
             "value": _sum_capacitance("VHOLD")},
            {"kind": "resistor", "name": "RLOGIC", "nodes": ["hold", "0"],
             "value": supply.hold_up_min_v / supply.logic_current_max_a},
        ],
        "analyses": [{"kind": "tran", "step_s": INRUSH_WINDOW_S / 2000.0,
                      "stop_s": INRUSH_WINDOW_S}],
        "measurements": [
            _measurement("regulator_input_minimum", "tran_min_voltage",
                         "hold", ">=", supply.regulator_floor_v),
            _measurement("protected_rail_minimum", "tran_min_voltage",
                         "rail"),
        ],
        "assumptions": _ideal({
            "SRC": "the external supply at the low end of the range the "
                   "board declares at its own terminal, as an ideal source "
                   "with no output impedance of its own",
            "RBLOCK": "the reverse-blocking device as its on-resistance at "
                      "the gate drive the whole rail gives it",
            "CBULK": "every capacitance on the protected rail as one ideal "
                     "capacitor at the low end of its tolerance, with no "
                     "ESR, no ESL and no DC bias derating",
            "RFANS": "all four fans drawing the standard's maximum start-up "
                     "current at once, as one resistance sized at the rail "
                     "the channels are designed to deliver",
            "START": "the instant every channel is enabled together, as an "
                     "ideal switch with no on-resistance; firmware that "
                     "staggers the starts sees less than this",
            "RDIODE": "the hold-up diode as the resistance that drops its "
                      "datasheet forward voltage at the logic load, which "
                      "overstates the drop at every smaller current and "
                      "cannot represent the blocking it also does",
            "CHOLD": "the hold-up reservoir at the low end of its tolerance",
            "RLOGIC": "the regulator and everything behind it as a fixed "
                      "resistance drawing the bounded logic current",
        }),
    }


def control_edge_scenario(parameters):
    """The control output driving the fan's pull-up through the cable.

    The standard fixes the low level and the current the fan's pull-up can
    source, and says nothing about the capacitance between them. This asks
    whether the level still arrives inside the on-time once the cable and the
    clamp are in the network.
    """
    supply = rules.Supply(parameters)
    driver = rules._spec(parameters, "Q10")["fet"]
    series_max_ohm = rules._resistor_ohms("R22") * (
        1.0 + rules._resistor_tolerance(parameters, "R22"))
    period_s = 1.0 / netlist.PWM_TARGET_FREQUENCY_HZ
    pull_up_ohm = (netlist.PWM_OPEN_CIRCUIT_MAX_V
                   / netlist.PWM_SINK_REQUIRED_A)
    del supply
    return {
        "name": "control_edge_into_the_fan_pull_up",
        "description": "one control output at the standard's target "
                       "frequency, against the strongest pull-up the "
                       "standard permits a fan to present and the "
                       "capacitance the cable and the clamp add",
        "elements": [
            {"kind": "vsource_dc", "name": "FANPULL", "nodes": ["pull", "0"],
             "value": netlist.PWM_OPEN_CIRCUIT_MAX_V},
            {"kind": "resistor", "name": "RFAN", "nodes": ["pull", "fan"],
             "value": pull_up_ohm},
            {"kind": "capacitor", "name": "CFAN", "nodes": ["fan", "0"],
             "value": (netlist.TACH_CABLE_CAPACITANCE_F
                       + netlist.TACH_CLAMP_CAPACITANCE_F)},
            {"kind": "resistor", "name": "RSERIES", "nodes": ["fan", "drain"],
             "value": series_max_ohm},
            {"kind": "resistor", "name": "RDSON", "nodes": ["drain", "sw"],
             "value": driver["rds_on_ohm"]["2.5"]["value"]},
            {"kind": "vsource_pulse", "name": "DRIVE", "nodes": ["sw", "0"],
             "pulse": _pulse(netlist.PWM_OPEN_CIRCUIT_MAX_V, 0.0, period_s)},
        ],
        "analyses": [{"kind": "tran", "step_s": period_s / 2000.0,
                      "stop_s": EDGE_PERIODS * period_s}],
        "measurements": [
            _measurement("control_low_level", "tran_min_voltage", "fan",
                         "<=", netlist.PWM_OUTPUT_LOW_MAX_V),
            _measurement("control_high_level", "tran_max_voltage", "fan",
                         ">=", (CONTROL_HIGH_FRACTION
                                * netlist.PWM_OPEN_CIRCUIT_MAX_V)),
        ],
        "assumptions": _ideal({
            "FANPULL": "the fan's internal pull-up supply at the highest "
                       "open-circuit level the standard permits",
            "RFAN": "the fan's internal pull-up at the strongest the "
                    "standard permits, which is the value that sources its "
                    "stated maximum current into a short; the standard sets "
                    "no lower bound on that current, so a fan with a weaker "
                    "pull-up releases the line more slowly than this",
            "CFAN": "the fan cable and the clamp as one capacitance to the "
                    "reference, both declared budgets rather than "
                    "measurements",
            "RSERIES": "the control output's series element at the high end "
                       "of its tolerance",
            "RDSON": "the open-drain driver as its on-resistance at the "
                     "2.5 V gate the datasheet characterises, below the "
                     "logic rail that actually drives it",
            "DRIVE": "the controller's compare output as an ideal switch at "
                     "the standard's target frequency and half duty",
        }),
    }


def sense_edge_scenario(parameters):
    """The sense input resolving pulses at the top rate the board claims.

    The requirement report bounds this network by adding both stages into one
    time constant, which overstates the rise. Here the network is solved.
    """
    supply = rules.Supply(parameters)
    mcu = rules._spec(parameters, "U1")
    pull_up_max_ohm = rules._resistor_ohms("R26") * (
        1.0 + rules._resistor_tolerance(parameters, "R26"))
    series_max_ohm = rules._resistor_ohms("R30") * (
        1.0 + rules._resistor_tolerance(parameters, "R30"))
    filter_f = _sum_capacitance("TACH1") + mcu["pin_capacitance_f"]["value"]
    saturation_ohm = (netlist.TACH_ASSUMED_LOW_LEVEL_V
                      / supply.tach_pull_up_current_a)
    period_s = 60.0 / (netlist.TACH_MAX_RPM
                       * netlist.TACH_PULSES_PER_REVOLUTION)
    vil_max = (mcu["digital_inputs"]["vil_max"]["fraction_of_supply"]["value"]
               * supply.logic_rail_min_v)
    vih_min = (mcu["digital_inputs"]["vih_min"]["fraction_of_supply"]["value"]
               * supply.logic_rail_min_v)
    return {
        "name": "sense_edge_at_the_top_declared_rotation_rate",
        "description": "one sense input pulsed at the rate the board's "
                       "declared maximum rotation gives, through the "
                       "pull-up, the cable and clamp capacitance, the "
                       "series element and the receiver's own filter",
        "elements": [
            {"kind": "vsource_dc", "name": "RAIL", "nodes": ["rail", "0"],
             "value": supply.logic_rail_min_v},
            {"kind": "resistor", "name": "RPULLUP", "nodes": ["rail", "fan"],
             "value": pull_up_max_ohm},
            {"kind": "capacitor", "name": "CFAN", "nodes": ["fan", "0"],
             "value": (netlist.TACH_CABLE_CAPACITANCE_F
                       + netlist.TACH_CLAMP_CAPACITANCE_F)},
            {"kind": "resistor", "name": "RSERIES", "nodes": ["fan", "pin"],
             "value": series_max_ohm},
            {"kind": "capacitor", "name": "CPIN", "nodes": ["pin", "0"],
             "value": filter_f},
            {"kind": "resistor", "name": "RSAT", "nodes": ["fan", "sink"],
             "value": saturation_ohm},
            {"kind": "vsource_pulse", "name": "TACH", "nodes": ["sink", "0"],
             "pulse": _pulse(supply.logic_rail_min_v, 0.0, period_s)},
        ],
        "analyses": [{"kind": "tran", "step_s": period_s / 4000.0,
                      "stop_s": EDGE_PERIODS * period_s}],
        "measurements": [
            _measurement("receiver_high_level", "tran_max_voltage", "pin",
                         ">=", vih_min),
            _measurement("receiver_low_level", "tran_min_voltage", "pin",
                         "<=", vil_max),
        ],
        "assumptions": _ideal({
            "RAIL": "the logic rail at the low end of the regulator's stated "
                    "accuracy, which is the worst case for reaching the "
                    "receiver's high threshold",
            "RPULLUP": "the sense pull-up at the high end of its tolerance, "
                       "the value that charges the line slowest",
            "CFAN": "the fan cable and the clamp as one capacitance to the "
                    "reference, both declared budgets",
            "RSERIES": "the series element at the high end of its tolerance",
            "CPIN": "the receiver's filter at the high end of its tolerance "
                    "plus the datasheet's pin capacitance",
            "RSAT": "the fan's open-collector output as the resistance that "
                    "produces the declared output low level at the current "
                    "this pull-up sources; the standard states neither, so "
                    "both are the board's declarations",
            "TACH": "two pulses per turn at the highest rotation rate the "
                    "board claims to resolve, as an ideal switch",
        }),
    }


def safe_state_scenario(parameters):
    """Both gates with nothing driving them, and one firmware sensitivity.

    The asserted case is the one the hardware guarantees: after reset every
    port is a floating input, so the only current in the gate divider is the
    receiver's own leakage. The third branch asks what the control gate would
    reach if firmware enabled an internal pull-up at the strongest the
    datasheet permits. It carries no assertion because no requirement says
    firmware must not, and it is measured because the number is the reason it
    must not.
    """
    supply = rules.Supply(parameters)
    mcu = rules._spec(parameters, "U1")
    driver = rules._spec(parameters, "Q10")["fet"]
    leakage_ohm = (supply.logic_rail_max_v
                   / mcu["input_leakage_max_a"]["value"])
    threshold_v = driver["vgs_threshold_min_v"]["value"]
    return {
        "name": "gates_held_off_with_nothing_driving_them",
        "description": "the control driver's gate and the channel enable's "
                       "gate in the state a controller that has not started "
                       "leaves them, and the control gate again against an "
                       "internal pull-up",
        "elements": [
            {"kind": "vsource_dc", "name": "RAIL", "nodes": ["rail", "0"],
             "value": supply.logic_rail_max_v},
            {"kind": "resistor", "name": "RLEAKC", "nodes": ["rail", "cpin"],
             "value": leakage_ohm},
            {"kind": "resistor", "name": "RSERIESC", "nodes": ["cpin", "cgate"],
             "value": rules._resistor_ohms("R14")},
            {"kind": "resistor", "name": "RPULLDOWNC", "nodes": ["cgate", "0"],
             "value": rules._resistor_ohms("R18")},
            {"kind": "resistor", "name": "RLEAKE", "nodes": ["rail", "egate"],
             "value": leakage_ohm},
            {"kind": "resistor", "name": "RPULLDOWNE", "nodes": ["egate", "0"],
             "value": rules._resistor_ohms("R10")},
            {"kind": "resistor", "name": "RPULLUP", "nodes": ["rail", "ppin"],
             "value": mcu["pull_resistor_ohm"]["min"]["value"]},
            {"kind": "resistor", "name": "RSERIESP", "nodes": ["ppin", "pgate"],
             "value": rules._resistor_ohms("R14")},
            {"kind": "resistor", "name": "RPULLDOWNP", "nodes": ["pgate", "0"],
             "value": rules._resistor_ohms("R18")},
        ],
        "analyses": [{"kind": "op"}],
        "measurements": [
            _measurement("control_gate_voltage", "op_voltage", "cgate",
                         "<=", threshold_v),
            _measurement("enable_gate_voltage", "op_voltage", "egate",
                         "<=", threshold_v),
            _measurement("control_gate_voltage_under_an_internal_pull_up",
                         "op_voltage", "pgate"),
        ],
        "assumptions": _ideal({
            "RAIL": "the logic rail at the top of the regulator's stated "
                    "accuracy",
            "RLEAKC": "the controller pin's own input leakage at the "
                      "datasheet maximum, as the resistance that sources it "
                      "from the rail",
            "RSERIESC": "the control gate's series element at its nominal "
                        "value",
            "RPULLDOWNC": "the control gate's pull-down at its nominal value",
            "RLEAKE": "the enable pin's input leakage, as above",
            "RPULLDOWNE": "the enable gate's pull-down at its nominal value",
            "RPULLUP": "an internal pull-up at the lowest resistance the "
                       "datasheet permits, which is not the reset state: "
                       "after reset every port is a floating input",
            "RSERIESP": "the control gate's series element, again",
            "RPULLDOWNP": "the control gate's pull-down, again",
        }),
    }


SCENARIOS = (
    ("pre_layout_logic_rail_inrush.json", logic_rail_inrush_scenario),
    ("pre_layout_control_edge.json", control_edge_scenario),
    ("pre_layout_sense_edge.json", sense_edge_scenario),
    ("pre_layout_safe_state.json", safe_state_scenario),
)


def documents():
    parameters = _parameters()
    return {name: builder(parameters) for name, builder in SCENARIOS}


def _write(path, document):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(document, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return path


def write():
    return [_write(os.path.join(SIM_DIR, name), document)
            for name, document in sorted(documents().items())]


if __name__ == "__main__":
    for path in write():
        sys.stdout.write(path + "\n")
