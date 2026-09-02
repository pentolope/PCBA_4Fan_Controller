"""Board-level electrical checks, stated as claims with their evidence.

Every number here comes from `components/parameters.json` (which cites the
frozen document it was read from), from the 4-wire fan specification, or from
the netlist. Nothing is asserted that a document, a component value or a
measurement does not support, and a quantity that cannot be established is
reported as UNKNOWN rather than assumed.
"""
from __future__ import annotations

import json
import os
import sys

from . import libraries, netlist

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARAMETERS_PATH = os.path.join(REPO_ROOT, "components", "parameters.json")
CATALOG_PATH = os.path.join(REPO_ROOT, "components", "jlcpcb.json")
TOOLKIT_ROOT = os.path.join(REPO_ROOT, "tooling", "PCBA_AutoDesignAndTest")
FOOTPRINT_ROOT = "/usr/share/kicad/footprints"
LOCAL_FOOTPRINT_ROOT = os.path.join(REPO_ROOT, "library")

if TOOLKIT_ROOT not in sys.path:
    sys.path.insert(0, TOOLKIT_ROOT)

from pcbqa import claim  # noqa: E402

DIRECT = "direct"
ASSUMED = "assumed"
DERIVED = "derived"

EVIDENCE_CLASSES = {
    DIRECT: "datasheet-behavioral",
    ASSUMED: "assumed-behavioral",
    DERIVED: "design-source",
}

BRIEF = "BRIEF.md"
FAN_SPEC = "fan_4wire_intel"


def load_parameters():
    with open(PARAMETERS_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_catalog():
    with open(CATALOG_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _mpn(reference):
    return netlist.PARTS[reference]["mpn"]


def _spec(parameters, reference):
    return parameters["parts"][_mpn(reference)]


def _evidence(basis, documents, assumptions=(), omissions=()):
    provenance = {"source": "components/parameters.json",
                  "documents": sorted(set(documents))}
    return claim.evidence(
        "device_electrical", EVIDENCE_CLASSES.get(basis, "design-source"),
        provenance, assumptions=list(assumptions),
        omitted_contributions=list(omissions))


def _requirement(name, op, value, source=BRIEF):
    return claim.requirement(name, source, {"op": op, "value": value})


#: How the requirement's operator turns a conservatively computed number into
#: the knowledge shape it actually supports. A worst case evaluated against a
#: floor is a lower bound on the real quantity; against a ceiling it is an
#: upper bound. Nothing that omits a contribution or rests on a premise is
#: ever allowed to call itself exact.
_BOUND_FOR_OPERATOR = {">=": claim.LOWER_BOUND, ">": claim.LOWER_BOUND,
                       "<=": claim.UPPER_BOUND, "<": claim.UPPER_BOUND}


def _claim(identity, units, significance, value, basis, documents,
           requirement, knowledge=None, scope_level="net",
           assumptions=(), omissions=()):
    if value is None:
        return claim.claim(
            scope_level, identity, units, claim.UNKNOWN, {},
            _evidence(basis, documents, assumptions, omissions),
            significance, None, requirement)
    if knowledge is None:
        if basis == ASSUMED or omissions:
            knowledge = _BOUND_FOR_OPERATOR.get(
                requirement["assertion"]["op"], claim.APPROXIMATE)
        else:
            knowledge = claim.EXACT
    basis_record = None
    if knowledge != claim.EXACT:
        basis_record = claim.knowledge_basis(
            basis, "datasheet_limit" if basis == DIRECT else basis)
    return claim.claim(
        scope_level, identity, units, knowledge, {"value": value},
        _evidence(basis, documents, assumptions, omissions),
        significance, basis_record, requirement)


def _structural(identity, significance, violations, requirement_name,
                documents=(), basis=DERIVED, assumptions=(), omissions=()):
    """A count of violations: zero is the only acceptable answer."""
    return _claim(identity, "violations", significance, float(len(violations)),
                  basis, documents, _requirement(requirement_name, "<=", 0.0),
                  scope_level="board", assumptions=assumptions,
                  omissions=omissions)


def _resistor_ohms(reference):
    value = netlist.PARTS[reference]["value"]
    if value.endswith("k"):
        return float(value[:-1]) * 1e3
    if value.endswith("R"):
        return float(value[:-1])
    raise ValueError("resistor %s carries the unparsable value %r"
                     % (reference, value))


def _capacitance_farads(reference):
    value = netlist.PARTS[reference]["value"]
    if value.endswith("uF"):
        return float(value[:-2]) * 1e-6
    if value.endswith("nF"):
        return float(value[:-2]) * 1e-9
    raise ValueError("capacitor %s carries the unparsable value %r"
                     % (reference, value))


def _resistor_tolerance(parameters, reference):
    spec = _spec(parameters, reference)["resistor"]
    entry = spec.get("tolerance")
    return 0.0 if entry is None else entry["value"]


def _channel_reference(prefix, channel, offset=0):
    return "%s%d" % (prefix, channel + offset)


# ---------------------------------------------------------------------------
# the supply model every rail and fan claim is built on

class Supply:
    """Worst-case rail voltages and currents, from parameters and values.

    Currents are upper bounds and drops are computed at the highest current
    and the highest resistance the datasheet and the tolerance permit, so no
    downstream figure is optimistic. The input range is the one declared at
    the board's terminal: the field wiring is the integrator's budget and
    appears only where a fault current is being bounded.
    """

    def __init__(self, parameters):
        self.parameters = parameters
        self.documents = {"stm32g030_st", "ht75rxx_holtek", "ao4407a_aos",
                          "ao3401a_aos", "pptc_jk_msmd200_jinrui",
                          "b5819w_jscj", "res_0603_uniroyal"}

        mcu = _spec(parameters, "U1")
        ldo = _spec(parameters, "U2")["regulator"]
        blocking = _spec(parameters, "Q1")["fet"]
        switch = _spec(parameters, "Q2")["fet"]
        fuse = _spec(parameters, "F1")["resettable_fuse"]
        holdup_diode = _spec(parameters, "D6")["diode"]

        self.input_min_v = netlist.INPUT_SUPPLY["min_v"]
        self.input_max_v = netlist.INPUT_SUPPLY["max_v"]
        self.channel_current_a = netlist.CHANNEL_CURRENT_RATING_A

        self.logic_rail_v = ldo["output_voltage_v"]["value"]
        tolerance = ldo["output_tolerance"]["value"]
        self.logic_rail_min_v = self.logic_rail_v * (1.0 - tolerance)
        self.logic_rail_max_v = self.logic_rail_v * (1.0 + tolerance)

        # Logic-side load, bounded rather than typical: the regulator's own
        # quiescent draw, the MCU at its stated maximum, every sense pull-up
        # held low at once, and the indicator taken as the whole rail across
        # its series resistor so no forward-voltage figure is needed.
        pull_up_min_ohm = _resistor_ohms("R26") * (
            1.0 - _resistor_tolerance(parameters, "R26"))
        self.tach_pull_up_current_a = self.logic_rail_max_v / pull_up_min_ohm
        indicator_min_ohm = _resistor_ohms("R44") * (
            1.0 - _resistor_tolerance(parameters, "R44"))
        self.indicator_current_max_a = self.logic_rail_max_v / indicator_min_ohm
        self.mcu_current_max_a = mcu["supply_current_max_a"]["value"]
        self.ldo_quiescent_a = ldo and _spec(
            parameters, "U2")["supply_current_max_a"]["value"]
        self.logic_current_max_a = (
            self.mcu_current_max_a + self.ldo_quiescent_a
            + netlist.CHANNEL_COUNT * self.tach_pull_up_current_a
            + self.indicator_current_max_a)

        # The blocking device runs with the whole rail across its gate, so the
        # -10 V on-resistance applies over the entire declared input range.
        self.blocking_rds_ohm = blocking["rds_on_ohm"]["-10"]["value"]
        self.total_input_current_a = (
            netlist.CHANNEL_COUNT * self.channel_current_a
            + self.logic_current_max_a)
        self.blocking_drop_max_v = (self.total_input_current_a
                                    * self.blocking_rds_ohm)
        self.protected_min_v = self.input_min_v - self.blocking_drop_max_v
        self.protected_max_v = self.input_max_v

        # The channel switch is driven from a divider off the protected rail,
        # so its gate sits near half of it and the -4.5 V on-resistance is the
        # figure that applies, not the -10 V one.
        self.switch_gate_v = self.protected_min_v * _resistor_ohms("R2") / (
            _resistor_ohms("R2") + _resistor_ohms("R6"))
        self.switch_gate_max_v = self.protected_max_v * _resistor_ohms("R2") / (
            _resistor_ohms("R2") + _resistor_ohms("R6"))
        self.switch_rds_ohm = switch["rds_on_ohm"]["-4.5"]["value"]
        self.fuse_resistance_max_ohm = fuse["resistance_max_ohm"]["value"]
        self.fuse_resistance_min_ohm = fuse["resistance_min_ohm"]["value"]

        self.channel_drop_max_v = self.channel_current_a * (
            self.fuse_resistance_max_ohm + self.switch_rds_ohm
            + netlist.BOARD_COPPER_BUDGET_OHM)
        self.fan_supply_min_v = self.protected_min_v - self.channel_drop_max_v
        self.fan_supply_max_v = self.protected_max_v

        # The hold-up reservoir sits behind a diode, so a collapse of the fan
        # bus cannot pull it down. Its floor is what the regulator needs to
        # keep regulating.
        self.holdup_diode_drop_v = holdup_diode[
            "forward_voltage_max_v"]["1"]["value"]
        self.hold_up_min_v = self.protected_min_v - self.holdup_diode_drop_v
        self.regulator_floor_v = (self.logic_rail_max_v
                                  + ldo["dropout_bound_v"]["value"])
        self.hold_up_farads = _capacitance_farads(
            netlist.HOLD_UP_BULK_REFERENCES[0]) * (
            1.0 - _spec(parameters, netlist.HOLD_UP_BULK_REFERENCES[0])[
                "capacitor"]["tolerance"]["value"])


# ---------------------------------------------------------------------------
# fan supply

def evaluate_fan_supply(parameters):
    """Every fan sees a supply inside the window its standard requires."""
    supply = Supply(parameters)
    documents = ("ao4407a_aos", "ao3401a_aos", "pptc_jk_msmd200_jinrui")
    results = []
    for channel in range(1, netlist.CHANNEL_COUNT + 1):
        net = "FAN%d_12V" % channel
        results.append({
            "id": "fan_supply_above_standard_minimum",
            "identity": net,
            "measured_v": supply.fan_supply_min_v,
            "claim": _claim(
                net, "V", "interface_compliance", supply.fan_supply_min_v,
                DIRECT, documents,
                _requirement("above_fan_standard_minimum", ">=",
                             netlist.FAN_SUPPLY["min_v"], FAN_SPEC),
                assumptions=(
                    "every channel carries its full rated current at once, "
                    "which is the worst case for the shared blocking device",
                    "board copper between the terminal and a fan connector is "
                    "the declared budget, not a measurement",),
                omissions=(
                    "the fan cable's own resistance is outside the board and "
                    "is not included",)),
        })
        results.append({
            "id": "fan_supply_below_standard_maximum",
            "identity": net,
            "measured_v": supply.fan_supply_max_v,
            "claim": _claim(
                net, "V", "interface_compliance", supply.fan_supply_max_v,
                DERIVED, documents,
                _requirement("below_fan_standard_maximum", "<=",
                             netlist.FAN_SUPPLY["max_v"], FAN_SPEC),
                assumptions=(
                    "the board has no series element that raises a voltage, "
                    "so the highest a fan pin can reach is the highest the "
                    "input terminal is declared for",)),
        })
    return results


# ---------------------------------------------------------------------------
# per-channel protection

def evaluate_channel_protection(parameters):
    supply = Supply(parameters)
    fuse = _spec(parameters, "F1")["resettable_fuse"]
    hold = fuse["hold_current_a"]
    ambient = "%d" % int(netlist.AMBIENT_MAX_C)
    if ambient not in hold:
        raise KeyError("no hold current is tabulated at %s C" % ambient)
    hold_current_a = hold[ambient]["value"]
    results = []
    for channel in range(1, netlist.CHANNEL_COUNT + 1):
        reference = "F%d" % channel
        results.append({
            "id": "channel_fuse_holds_the_rated_current",
            "identity": reference,
            "measured_a": hold_current_a,
            "claim": _claim(
                reference, "A", "protection", hold_current_a, DIRECT,
                ("pptc_jk_msmd200_jinrui",),
                _requirement("holds_the_channel_rating", ">=",
                             netlist.CHANNEL_CURRENT_RATING_A),
                scope_level="group",
                assumptions=(
                    "the fuse is at the board's declared maximum ambient of "
                    "%g C, read from the datasheet's derating table rather "
                    "than interpolated" % netlist.AMBIENT_MAX_C,),
                omissions=(
                    "self-heating of neighbouring parts is not included; the "
                    "datasheet asks that no heat source sit beside the fuse "
                    "and that is a placement constraint, not a number here",)),
        })
        results.append({
            "id": "channel_fuse_passes_the_standard_start_up_surge",
            "identity": reference,
            "measured_a": netlist.FAN_SPEC_STARTUP_CURRENT_MAX_A,
            "claim": _claim(
                reference, "A", "protection",
                netlist.FAN_SPEC_STARTUP_CURRENT_MAX_A, DIRECT,
                ("pptc_jk_msmd200_jinrui",),
                _requirement("below_the_always_trip_current", "<=",
                             fuse["trip_current_a"]["value"], FAN_SPEC),
                scope_level="group",
                assumptions=(
                    "below the always-trip current the device may or may not "
                    "trip; the standard permits the surge for one second and "
                    "the datasheet's guaranteed trip time at twice this "
                    "current is longer than that",),
                omissions=(
                    "the time-current curve is typical, so the surge is shown "
                    "to be below the always-trip current rather than shown "
                    "not to trip",)),
        })
    # A bolted short downstream of one fuse, limited by the declared field
    # wiring and by the least resistance the path can have.
    fault_path_ohm = (netlist.INPUT_PATH_BUDGET_OHM
                      + supply.blocking_rds_ohm
                      + supply.fuse_resistance_min_ohm
                      + supply.switch_rds_ohm
                      + netlist.BOARD_COPPER_BUDGET_OHM)
    fault_current_a = supply.input_max_v / fault_path_ohm
    results.append({
        "id": "channel_short_current_within_the_fuse_rating",
        "identity": "F1",
        "measured_a": fault_current_a,
        "claim": _claim(
            "F1", "A", "protection", fault_current_a, DIRECT,
            ("pptc_jk_msmd200_jinrui", "ao4407a_aos", "ao3401a_aos"),
            _requirement("within_the_fuse_maximum_fault_current", "<=",
                         _spec(parameters, "F1")["resettable_fuse"][
                             "fault_current_max_a"]["value"]),
            scope_level="group",
            assumptions=(
                "the supply and its wiring present the declared %g ohm; a "
                "stiffer source raises the fault current"
                % netlist.INPUT_PATH_BUDGET_OHM,
                "the fuse is at its minimum resistance, which is the worst "
                "case for fault current",)),
    })
    return results


# ---------------------------------------------------------------------------
# the channel switch

def evaluate_channel_switch(parameters):
    supply = Supply(parameters)
    switch = _spec(parameters, "Q2")["fet"]
    driver = _spec(parameters, "Q6")["fet"]
    mcu = _spec(parameters, "U1")
    characterised_v = min(abs(float(key))
                          for key in switch["rds_on_ohm"])
    results = []
    for channel in range(1, netlist.CHANNEL_COUNT + 1):
        net = "CH%d_PG" % channel
        results.append({
            "id": "channel_switch_fully_on_at_its_gate_drive",
            "identity": net,
            "measured_v": supply.switch_gate_v,
            "claim": _claim(
                net, "V", "gate_drive", supply.switch_gate_v, DIRECT,
                ("ao3401a_aos", "res_0603_uniroyal"),
                _requirement("at_or_above_a_characterised_drive", ">=",
                             characterised_v),
                assumptions=(
                    "the gate divider is at its nominal ratio; both resistors "
                    "are the same value and the same tolerance, so tolerance "
                    "moves the ratio far less than it moves either value",)),
        })
        results.append({
            "id": "channel_switch_gate_within_its_rating",
            "identity": net,
            "measured_v": supply.switch_gate_max_v,
            "claim": _claim(
                net, "V", "absolute_maximum", supply.switch_gate_max_v, DIRECT,
                ("ao3401a_aos",),
                _requirement("within_the_gate_source_rating", "<=",
                             switch["vgs_max_v"]["value"])),
        })
        # With the enable pin floating, the driver's own drain leakage is the
        # only current in the gate divider, so the switch sees almost nothing.
        leakage_a = driver["drain_leakage_max_a"]["value"]
        residual_v = abs(leakage_a) * _resistor_ohms("R6")
        results.append({
            "id": "channel_off_when_the_enable_pin_does_not_drive",
            "identity": net,
            "measured_v": residual_v,
            "claim": _claim(
                net, "V", "safe_state", residual_v, DIRECT,
                ("ao3400a_aos", "ao3401a_aos"),
                _requirement("below_the_switch_threshold", "<=",
                             abs(switch["vgs_threshold_min_v"]["value"])),
                assumptions=(
                    "the worst case is the enable device at its maximum "
                    "drain leakage, which is stronger than the pull-down the "
                    "MCU pin sees while it is an input",)),
        })
        enable_net = "CH%d_EN" % channel
        pull_down_v = (mcu["input_leakage_max_a"]["value"]
                       * _resistor_ohms("R10"))
        results.append({
            "id": "enable_pin_defined_before_firmware_drives_it",
            "identity": enable_net,
            "measured_v": pull_down_v,
            "claim": _claim(
                enable_net, "V", "safe_state", pull_down_v, DIRECT,
                ("stm32g030_st", "ao3400a_aos"),
                _requirement("below_the_enable_device_threshold", "<=",
                             driver["vgs_threshold_min_v"]["value"])),
        })
    return results


# ---------------------------------------------------------------------------
# the control output

def evaluate_control_output(parameters):
    """The open-drain control output, against the standard's own numbers."""
    supply = Supply(parameters)
    driver = _spec(parameters, "Q10")["fet"]
    clamp = _spec(parameters, "D11")["tvs"]
    series_max_ohm = _resistor_ohms("R22") * (
        1.0 + _resistor_tolerance(parameters, "R22"))
    rds_ohm = driver["rds_on_ohm"]["2.5"]["value"]
    results = []
    for name, current in (("required", netlist.PWM_SINK_REQUIRED_A),
                          ("recommended", netlist.PWM_SINK_RECOMMENDED_A)):
        low_v = current * (series_max_ohm + rds_ohm)
        for channel in range(1, netlist.CHANNEL_COUNT + 1):
            net = "FAN%d_PWM" % channel
            results.append({
                "id": "control_low_level_at_the_%s_sink_current" % name,
                "identity": net,
                "measured_v": low_v,
                "claim": _claim(
                    net, "V", "interface_compliance", low_v, DIRECT,
                    ("ao3400a_aos", "res_0603_uniroyal"),
                    _requirement("within_the_standard_low_level", "<=",
                                 netlist.PWM_OUTPUT_LOW_MAX_V, FAN_SPEC),
                    assumptions=(
                        "the driver's on-resistance is taken at the 2.5 V "
                        "gate the datasheet characterises, which is below "
                        "the logic rail that actually drives it",),
                    omissions=(
                        "the connector's own ground pin sits above the "
                        "signal reference by the fan return drop, which "
                        "lowers the level the fan measures; ignoring it is "
                        "the conservative direction",)),
            })
    leakage_a = (driver["drain_leakage_max_a"]["value"]
                 + clamp["leakage_max_a"]["value"])
    for channel in range(1, netlist.CHANNEL_COUNT + 1):
        net = "FAN%d_PWM" % channel
        results.append({
            "id": "control_output_tolerates_the_fan_pull_up_unpowered",
            "identity": net,
            "measured_v": netlist.PWM_OPEN_CIRCUIT_MAX_V,
            "claim": _claim(
                net, "V", "absolute_maximum", netlist.PWM_OPEN_CIRCUIT_MAX_V,
                DIRECT, ("ao3400a_aos", "smf16a_jingdao"),
                _requirement("within_the_driver_drain_rating", "<=",
                             driver["vds_max_v"]["value"], FAN_SPEC),
                assumptions=(
                    "with the logic rail down the driver's gate is held at "
                    "the reference by its pull-down, so the drain simply "
                    "stands off the fan's pull-up",)),
        })
        results.append({
            "id": "control_output_leakage_with_the_board_unpowered",
            "identity": net,
            "measured_a": leakage_a,
            "claim": _claim(
                net, "A", "interface_compliance", leakage_a, DIRECT,
                ("ao3400a_aos", "smf16a_jingdao"),
                _requirement("far_below_the_fan_pull_up_current", "<=",
                             netlist.PWM_SINK_REQUIRED_A / 10.0, FAN_SPEC),
                assumptions=(
                    "the standard sets no leakage limit for the controller "
                    "end, so the board is checked against a tenth of the "
                    "current the fan's pull-up sources",)),
        })
    return results


def evaluate_control_topology(parameters):
    """The standard forbids a pull on the controller's control trace."""
    pin_net = netlist.pin_to_net()
    violations = []
    for channel in range(1, netlist.CHANNEL_COUNT + 1):
        net = "FAN%d_PWM" % channel
        for pin_ref in netlist.NETS[net]:
            reference = pin_ref.split(".")[0]
            part = netlist.PARTS[reference]
            if part["lib_id"] != "Device:R":
                continue
            # a resistor is a pull only if its far end sits on a rail
            far_pins = [p for p in ("%s.1" % reference, "%s.2" % reference)
                        if p != pin_ref]
            for far in far_pins:
                if pin_net.get(far) in netlist.POWER_NETS:
                    violations.append((net, reference, pin_net[far]))
    return [{
        "id": "control_trace_carries_no_pull_up_or_pull_down",
        "identity": "control_nets",
        "measured_c": float(len(violations)),
        "claim": _structural(
            "control_nets", "interface_compliance", violations,
            "no_resistive_pull_on_a_control_trace",
            documents=(FAN_SPEC,),
            assumptions=(
                "the clamp on each control net is a suppressor, not a pull: "
                "its stand-off is above the fan's open-circuit level and its "
                "leakage is checked separately",)),
    }]


def evaluate_control_short_to_supply(parameters):
    """A control pin shorted to the fan supply must not spread."""
    supply = Supply(parameters)
    driver = _spec(parameters, "Q10")["fet"]
    series_min_ohm = _resistor_ohms("R22") * (
        1.0 - _resistor_tolerance(parameters, "R22"))
    fault_current_a = supply.protected_max_v / series_min_ohm
    series_power_w = fault_current_a ** 2 * series_min_ohm
    rated_w = _spec(parameters, "R22")["resistor"]["power_max_w"]["value"]
    results = [{
        "id": "control_short_to_supply_stays_within_the_driver_rating",
        "identity": "PWM1_D",
        "measured_a": fault_current_a,
        "claim": _claim(
            "PWM1_D", "A", "fault_containment", fault_current_a, DIRECT,
            ("ao3400a_aos", "res_0603_uniroyal"),
            _requirement("within_the_driver_continuous_drain_current", "<=",
                         driver["id_max_a_70c"]["value"]),
            assumptions=(
                "the driver is on when the short appears, which is the worst "
                "case; with it off the series element carries nothing",)),
    }, {
        "id": "control_short_to_supply_opens_the_series_element",
        "identity": "R22",
        "measured_w": series_power_w,
        "claim": _claim(
            "R22", "W", "fault_containment", series_power_w, DIRECT,
            ("res_0603_uniroyal",),
            _requirement("above_the_series_element_rating", ">=", rated_w),
            scope_level="group",
            assumptions=(
                "the series element is the sacrificial one by design: it "
                "carries many times its rated power while the driver carries "
                "less than a twentieth of its own, so the fault ends with one "
                "0603 resistor open and the channel's fan at full speed, "
                "which is the state the standard defines for no control "
                "signal",),
            omissions=(
                "how long the element takes to open is not established here; "
                "the claim is that it, and not the driver, is the part the "
                "fault overloads",)),
    }]
    return results


# ---------------------------------------------------------------------------
# control timing

def evaluate_control_timing(parameters):
    oscillator = _spec(parameters, "U1")["oscillator"]
    low_hz = (oscillator["hsi16_min_hz"]["value"]
              * (1.0 + oscillator["temperature_drift_min"]["value"])
              * (1.0 + oscillator["supply_drift_min"]["value"]))
    high_hz = (oscillator["hsi16_max_hz"]["value"]
               * (1.0 + oscillator["temperature_drift_max"]["value"])
               * (1.0 + oscillator["supply_drift_max"]["value"]))
    pwm_low_hz = low_hz / netlist.PWM_PERIOD_COUNTS
    pwm_high_hz = high_hz / netlist.PWM_PERIOD_COUNTS
    assumptions = (
        "the divider is the one the board declares (%d counts); the board "
        "cannot make firmware use it, so what is established here is that "
        "the on-chip oscillator reaches the band with it and needs no crystal"
        % netlist.PWM_PERIOD_COUNTS,)
    results = [{
        "id": "control_frequency_above_the_standard_minimum",
        "identity": "PWM1",
        "measured_hz": pwm_low_hz,
        "claim": _claim(
            "PWM1", "Hz", "interface_compliance", pwm_low_hz, DIRECT,
            ("stm32g030_st",),
            _requirement("above_the_standard_minimum", ">=",
                         netlist.PWM_FREQUENCY_BAND_HZ["min"], FAN_SPEC),
            assumptions=assumptions),
    }, {
        "id": "control_frequency_below_the_standard_maximum",
        "identity": "PWM1",
        "measured_hz": pwm_high_hz,
        "claim": _claim(
            "PWM1", "Hz", "interface_compliance", pwm_high_hz, DIRECT,
            ("stm32g030_st",),
            _requirement("below_the_standard_maximum", "<=",
                         netlist.PWM_FREQUENCY_BAND_HZ["max"], FAN_SPEC),
            assumptions=assumptions),
    }, {
        "id": "control_duty_resolution_meets_the_board_target",
        "identity": "PWM1",
        "measured_c": float(netlist.PWM_PERIOD_COUNTS),
        "claim": _claim(
            "PWM1", "steps", "interface_compliance",
            float(netlist.PWM_PERIOD_COUNTS), DERIVED, ("stm32g030_st",),
            _requirement("at_or_above_the_declared_resolution", ">=",
                         float(netlist.PWM_RESOLUTION_STEPS_TARGET))),
    }]
    timers = {function.split("_")[0]
              for function in netlist.CHANNEL_PWM_FUNCTIONS}
    results.append({
        "id": "every_channel_drives_from_one_counter",
        "identity": "control_nets",
        "measured_c": float(len(timers) - 1),
        "claim": _structural(
            "control_nets", "interface_compliance",
            sorted(timers)[1:], "one_timer_for_every_control_output",
            documents=("stm32g030_st",),
            assumptions=(
                "compare channels of one timer share its counter, prescaler "
                "and period, so equal frequency and equal duty resolution on "
                "every channel follow from the pin choice",)),
    })
    return results


# ---------------------------------------------------------------------------
# the sense input

def evaluate_sense_input(parameters):
    supply = Supply(parameters)
    mcu = _spec(parameters, "U1")
    clamp = _spec(parameters, "D7")["diode"]
    pull_up_ohm = _resistor_ohms("R26")
    series_ohm = _resistor_ohms("R30")
    tolerance = _resistor_tolerance(parameters, "R26")
    vil_max = (mcu["digital_inputs"]["vil_max"]["fraction_of_supply"]["value"]
               * supply.logic_rail_min_v)
    vih_min = (mcu["digital_inputs"]["vih_min"]["fraction_of_supply"]["value"]
               * supply.logic_rail_min_v)
    high_level_v = supply.logic_rail_min_v - (
        mcu["input_leakage_max_a"]["value"] * pull_up_ohm * (1.0 + tolerance))
    results = []
    for channel in range(1, netlist.CHANNEL_COUNT + 1):
        fan_net = "FAN%d_TACH" % channel
        mcu_net = "TACH%d" % channel
        results.append({
            "id": "sense_pull_up_load_within_the_declared_fan_capability",
            "identity": fan_net,
            "measured_a": supply.tach_pull_up_current_a,
            "claim": _claim(
                fan_net, "A", "interface_compliance",
                supply.tach_pull_up_current_a, ASSUMED,
                ("res_0603_uniroyal", "ht75rxx_holtek"),
                _requirement("within_the_declared_fan_sink", "<=",
                             netlist.TACH_ASSUMED_SINK_A),
                assumptions=(
                    "the standard states no sink current for the fan's open "
                    "collector, so the board declares one and the pull-up is "
                    "checked against it; a fan that cannot sink it will not "
                    "read correctly and the declaration is revisable",)),
        })
        results.append({
            "id": "sense_low_level_below_the_receiver_threshold",
            "identity": mcu_net,
            "measured_v": netlist.TACH_ASSUMED_LOW_LEVEL_V,
            "claim": _claim(
                mcu_net, "V", "interface_compliance",
                netlist.TACH_ASSUMED_LOW_LEVEL_V, ASSUMED,
                ("stm32g030_st",),
                _requirement("below_the_receiver_low_threshold", "<=",
                             vil_max),
                assumptions=(
                    "the fan's output low level is declared, not stated by "
                    "the standard",
                    "no current flows in the series element while the "
                    "receiver is an input, so the level at the pin is the "
                    "level at the connector",)),
        })
        results.append({
            "id": "sense_high_level_above_the_receiver_threshold",
            "identity": mcu_net,
            "measured_v": high_level_v,
            "claim": _claim(
                mcu_net, "V", "interface_compliance", high_level_v, DIRECT,
                ("stm32g030_st", "res_0603_uniroyal"),
                _requirement("above_the_receiver_high_threshold", ">=",
                             vih_min)),
        })
    # Rise time to the receiver's threshold, against the shortest half period
    # the board is required to resolve.
    pull_up_max_ohm = pull_up_ohm * (1.0 + tolerance)
    series_max_ohm = series_ohm * (
        1.0 + _resistor_tolerance(parameters, "R30"))
    node_farads = (netlist.TACH_CLAMP_CAPACITANCE_F
                   + netlist.TACH_CABLE_CAPACITANCE_F)
    receiver_farads = (
        _capacitance_farads("C9")
        * (1.0 + _spec(parameters, "C9")["capacitor"]["tolerance"]["value"])
        + mcu["pin_capacitance_f"]["value"])
    time_constant_s = (pull_up_max_ohm * (node_farads + receiver_farads)
                       + series_max_ohm * receiver_farads)
    threshold_fraction = mcu["digital_inputs"]["vih_min"][
        "fraction_of_supply"]["value"]
    import math
    rise_s = time_constant_s * math.log(1.0 / (1.0 - threshold_fraction))
    half_period_s = 30.0 / (netlist.TACH_MAX_RPM
                            * netlist.TACH_PULSES_PER_REVOLUTION)
    results.append({
        "id": "sense_edge_reaches_the_threshold_inside_a_half_period",
        "identity": "TACH1",
        "measured_s": rise_s,
        "claim": _claim(
            "TACH1", "s", "interface_compliance", rise_s, ASSUMED,
            ("stm32g030_st", "res_0603_uniroyal", "mlcc_yageo_cc0603"),
            _requirement("within_the_declared_fraction_of_a_half_period",
                         "<=",
                         half_period_s
                         * netlist.TACH_RISE_FRACTION_OF_HALF_PERIOD),
            assumptions=(
                "the clamp's datasheet states no junction capacitance and the "
                "cable is not part of the board, so both are declared "
                "budgets",
                "the network is treated as one time constant that adds both "
                "stages, which overstates the rise rather than understating "
                "it",)),
    })
    # A sense pin shorted to the fan supply must not push more into the
    # receiver than the datasheet allows.
    series_min_ohm = series_ohm * (
        1.0 - _resistor_tolerance(parameters, "R30"))
    clamped_v = supply.logic_rail_max_v + clamp[
        "forward_voltage_max_v"]["1"]["value"]
    injection_a = (netlist.INPUT_SURVIVAL_MAX_V - clamped_v) / series_min_ohm
    results.append({
        "id": "sense_short_to_supply_within_the_receiver_injection_limit",
        "identity": "TACH1",
        "measured_a": injection_a,
        "claim": _claim(
            "TACH1", "A", "fault_containment", injection_a, DIRECT,
            ("stm32g030_st", "b5819w_jscj", "res_0603_uniroyal"),
            _requirement("within_the_pin_injection_limit", "<=",
                         mcu["injection_current_max_a"]["value"]),
            assumptions=(
                "evaluated at the highest steady input the board is required "
                "to survive, not merely at the top of its operating range",
                "the clamp's forward drop is taken at 1 A, far above the "
                "current here, which overstates the clamped level and so the "
                "current through the series element",)),
    })
    return results


def evaluate_injection_policy(parameters):
    """No conductor that leaves the board reaches a pin that tolerates no
    negative injection, except where the board itself bounds the excursion."""
    pin_net = netlist.pin_to_net()
    entering = set(netlist.entering_conductors())
    violations = []
    for pin, name in sorted(netlist.MCU_NO_NEGATIVE_INJECTION_PINS.items()):
        net = pin_net.get("U1.%s" % pin)
        if net is None:
            continue
        if net in entering:
            violations.append((pin, name, net))
    return [{
        "id": "no_leaving_conductor_reaches_a_zero_injection_pin",
        "identity": "U1",
        "measured_c": float(len(violations)),
        "claim": _structural(
            "U1", "absolute_maximum", violations,
            "no_direct_path_from_a_connector_to_a_zero_injection_pin",
            documents=("stm32g030_st",),
            assumptions=(
                "the programming pin the part fixes at a zero-injection pin "
                "is reached only through a series element and a clamp at the "
                "connector, so a sustained negative level cannot stand on it",
                "the sense dividers cannot take their pins below the input "
                "voltage minimum, because the fan supply itself is clamped "
                "one Schottky drop below the reference",)),
    }]


# ---------------------------------------------------------------------------
# rails

def evaluate_rails(parameters):
    supply = Supply(parameters)
    ldo = _spec(parameters, "U2")["regulator"]
    mcu = _spec(parameters, "U1")
    results = [{
        "id": "regulator_input_within_its_rating",
        "identity": "VHOLD",
        "measured_v": supply.protected_max_v,
        "claim": _claim(
            "VHOLD", "V", "absolute_maximum", supply.protected_max_v, DIRECT,
            ("ht75rxx_holtek",),
            _requirement("within_the_regulator_input_rating", "<=",
                         ldo["input_voltage_max_v"]["value"])),
    }, {
        "id": "logic_rail_within_the_controller_supply_range",
        "identity": "+3V3",
        "measured_v": supply.logic_rail_max_v,
        "claim": _claim(
            "+3V3", "V", "absolute_maximum", supply.logic_rail_max_v, DIRECT,
            ("ht75rxx_holtek", "stm32g030_st"),
            _requirement("within_the_controller_supply_maximum", "<=",
                         mcu["supply"]["max_v"]["value"])),
    }, {
        "id": "logic_rail_above_the_controller_supply_minimum",
        "identity": "+3V3",
        "measured_v": supply.logic_rail_min_v,
        "claim": _claim(
            "+3V3", "V", "rail_margin", supply.logic_rail_min_v, DIRECT,
            ("ht75rxx_holtek", "stm32g030_st"),
            _requirement("above_the_controller_supply_minimum", ">=",
                         mcu["supply"]["min_v"]["value"])),
    }]
    # Fan inrush: the standard lets every fan take its start-up surge at once.
    inrush_a = (netlist.CHANNEL_COUNT * netlist.FAN_SPEC_STARTUP_CURRENT_MAX_A
                + supply.logic_current_max_a)
    inrush_rail_v = (supply.input_min_v
                     - inrush_a * supply.blocking_rds_ohm
                     - supply.holdup_diode_drop_v)
    results.append({
        "id": "logic_rail_holds_through_fan_inrush",
        "identity": "VHOLD",
        "measured_v": inrush_rail_v,
        "claim": _claim(
            "VHOLD", "V", "rail_margin", inrush_rail_v, DIRECT,
            ("ao4407a_aos", "b5819w_jscj", "ht75rxx_holtek"),
            _requirement("above_the_regulator_floor", ">=",
                         supply.regulator_floor_v, FAN_SPEC),
            assumptions=(
                "all four channels take the standard's maximum start-up "
                "current at the same instant, which is the worst case and is "
                "what firmware would avoid by staggering",
                "the regulator's dropout at this load is a declared bound: "
                "the datasheet states dropout only at 1 mA",)),
    })
    hold_up_s = (supply.hold_up_farads
                 * (supply.hold_up_min_v - supply.regulator_floor_v)
                 / supply.logic_current_max_a)
    results.append({
        "id": "logic_rail_rides_through_a_fan_supply_collapse",
        "identity": "VHOLD",
        "measured_s": hold_up_s,
        "claim": _claim(
            "VHOLD", "s", "rail_margin", hold_up_s, DIRECT,
            ("elcap_knscha_rvt", "ht75rxx_holtek", "b5819w_jscj",
             "stm32g030_st"),
            _requirement("at_or_above_the_declared_hold_up", ">=",
                         netlist.HOLD_UP_TARGET_S),
            assumptions=(
                "the reservoir is at the low end of its tolerance and the "
                "logic load is at its bounded maximum throughout",
                "the load is treated as constant although the pull-ups and "
                "the indicator fall with the rail, which understates the "
                "time",),
            omissions=(
                "the fuse's guaranteed clearing time is longer than this, so "
                "a collapse that lasts is not ridden through: the controller "
                "restarts and re-establishes the channels, and that is the "
                "documented recovery rather than an uninterrupted one",)),
    })
    dissipation_w = ((supply.protected_max_v - supply.holdup_diode_drop_v
                      - supply.logic_rail_min_v)
                     * supply.logic_current_max_a)
    thermal = _spec(parameters, "U2")["thermal"]
    junction_c = (netlist.AMBIENT_MAX_C
                  + dissipation_w * thermal["rthja_c_per_w"]["value"])
    results.append({
        "id": "regulator_junction_within_its_rating",
        "identity": "U2",
        "measured_c": junction_c,
        "claim": _claim(
            "U2", "degC", "thermal", junction_c, DIRECT,
            ("ht75rxx_holtek",),
            _requirement("within_the_regulator_junction_maximum", "<=",
                         thermal["tj_max_c"]["value"]),
            scope_level="group",
            assumptions=(
                "the package's junction-to-ambient figure applies at the "
                "board's declared maximum ambient",),
            omissions=(
                "the datasheet's thermal resistance is for its own test "
                "board; the copper this board gives the tab is a layout "
                "quantity and is not yet measured",)),
    })
    return results


# ---------------------------------------------------------------------------
# reverse polarity

def evaluate_reverse_polarity(parameters):
    supply = Supply(parameters)
    blocking = _spec(parameters, "Q1")["fet"]
    clamp = _spec(parameters, "D1")["tvs"]
    results = [{
        "id": "blocking_device_stands_off_a_reversed_input",
        "identity": "V12IN",
        "measured_v": netlist.INPUT_SURVIVAL_MAX_V,
        "claim": _claim(
            "V12IN", "V", "absolute_maximum", netlist.INPUT_SURVIVAL_MAX_V,
            DIRECT, ("ao4407a_aos",),
            _requirement("within_the_blocking_drain_source_rating", "<=",
                         abs(blocking["vds_max_v"]["value"])),
            assumptions=(
                "with the input reversed the device's gate sits at the "
                "terminal that is now positive, so it is off and the whole "
                "reversed input stands across it",)),
    }, {
        "id": "blocking_device_gate_within_its_rating",
        "identity": "PFET_G",
        "measured_v": supply.protected_max_v,
        "claim": _claim(
            "PFET_G", "V", "absolute_maximum", supply.protected_max_v, DIRECT,
            ("ao4407a_aos",),
            _requirement("within_the_gate_source_rating", "<=",
                         blocking["vgs_max_v"]["value"])),
    }, {
        "id": "input_clamp_stands_off_the_operating_maximum",
        "identity": "V12P",
        "measured_v": supply.protected_max_v,
        "claim": _claim(
            "V12P", "V", "protection", supply.protected_max_v, DIRECT,
            ("smaj_littelfuse",),
            _requirement("below_the_clamp_stand_off", "<=",
                         clamp["reverse_standoff_v"]["value"])),
    }, {
        "id": "blocking_device_dissipation_within_its_rating",
        "identity": "Q1",
        "measured_w": (supply.total_input_current_a ** 2
                       * supply.blocking_rds_ohm),
        "claim": _claim(
            "Q1", "W", "thermal",
            supply.total_input_current_a ** 2 * supply.blocking_rds_ohm,
            DIRECT, ("ao4407a_aos",),
            _requirement("within_the_steady_state_power_rating", "<=",
                         blocking["power_max_w_70c"]["value"]),
            scope_level="group",
            omissions=(
                "the package's power rating is quoted on the datasheet's own "
                "test board; the copper this board gives the drain is a "
                "layout quantity and is not yet measured",)),
    }]
    return results


# ---------------------------------------------------------------------------
# dissipation

def _resistor_worst_case_w(parameters, reference, supply):
    """The highest power each resistor sees in normal operation."""
    ohm = _resistor_ohms(reference)
    tolerance = _resistor_tolerance(parameters, reference)
    minimum_ohm = ohm * (1.0 - tolerance) if ohm else 0.0
    logic = supply.logic_rail_max_v
    protected = supply.protected_max_v
    if reference == "R1":
        return protected ** 2 / (ohm * (1.0 - tolerance))
    if reference == netlist.GROUND_STAR_REFERENCE:
        resistance = _spec(parameters, reference)["resistor"][
            "resistance_max_ohm"]["value"]
        return supply.logic_current_max_a ** 2 * resistance
    index = int(reference[1:])
    if 2 <= index <= 9:                       # switch gate divider
        return (protected / 2.0) ** 2 / minimum_ohm
    if 10 <= index <= 13 or 18 <= index <= 21:  # gate pull-downs
        return logic ** 2 / minimum_ohm
    if 14 <= index <= 17:                     # gate series, capacitive load
        return 0.0
    if 22 <= index <= 25:                     # control series element
        return netlist.PWM_SINK_RECOMMENDED_A ** 2 * ohm * (1.0 + tolerance)
    if 26 <= index <= 29:                     # sense pull-up
        return logic ** 2 / minimum_ohm
    if 30 <= index <= 33:                     # sense series element
        return logic ** 2 / minimum_ohm
    if 34 <= index <= 37 or reference == "R42":   # divider, upper
        top = _resistor_ohms(reference)
        bottom = _resistor_ohms("R%d" % (index + 4)) if index <= 37 else \
            _resistor_ohms("R43")
        return (protected * top / (top + bottom)) ** 2 / minimum_ohm
    if 38 <= index <= 41 or reference == "R43":   # divider, lower
        bottom = _resistor_ohms(reference)
        top = _resistor_ohms("R%d" % (index - 4)) if index <= 41 else \
            _resistor_ohms("R42")
        return (protected * bottom / (top + bottom)) ** 2 / minimum_ohm
    if reference == "R44":                    # indicator series element
        return logic ** 2 / minimum_ohm
    if 46 <= index <= 49:                     # host and programming series
        return logic ** 2 / minimum_ohm
    raise ValueError("no dissipation model for " + reference)


def evaluate_dissipation(parameters):
    supply = Supply(parameters)
    results = []
    for reference in sorted(netlist.PARTS,
                            key=lambda r: (r[0], int(r[1:]) if r[1:].isdigit()
                                           else 0)):
        if not reference.startswith("R"):
            continue
        rated_w = _spec(parameters, reference)["resistor"][
            "power_max_w"]["value"]
        power_w = _resistor_worst_case_w(parameters, reference, supply)
        results.append({
            "id": "resistor_dissipation_within_its_rating",
            "identity": reference,
            "measured_w": power_w,
            "claim": _claim(
                reference, "W", "thermal", power_w, DERIVED,
                ("res_0603_uniroyal",),
                _requirement("within_the_element_power_rating", "<=", rated_w),
                scope_level="group",
                assumptions=(
                    "normal operation; a fault that overloads an element "
                    "deliberately is evaluated by its own claim",)),
        })
    led = _spec(parameters, "D24")["led"]
    current_a = ((supply.logic_rail_max_v
                  - led["forward_voltage_min_v"]["value"])
                 / (_resistor_ohms("R44")
                    * (1.0 - _resistor_tolerance(parameters, "R44"))))
    results.append({
        "id": "indicator_current_within_its_rating",
        "identity": "D24",
        "measured_a": current_a,
        "claim": _claim(
            "D24", "A", "thermal", current_a, DIRECT,
            ("kt0603r_kento", "res_0603_uniroyal"),
            _requirement("within_the_indicator_forward_current", "<=",
                         led["forward_current_max_a"]["value"]),
            scope_level="group"),
    })
    return results


# ---------------------------------------------------------------------------
# protection coverage

def evaluate_esd_coverage(parameters):
    """Every conductor entering the board is clamped, or exempt with a reason."""
    pin_net = netlist.pin_to_net()
    clamps = {}
    for reference, part in netlist.PARTS.items():
        if part["lib_id"] not in ("Device:D_TVS",
                                  "%s:TPD1E10B06" % netlist.LIBRARY_NAME):
            continue
        for pin in ("%s.1" % reference, "%s.2" % reference):
            net = pin_net.get(pin)
            if net is not None:
                clamps.setdefault(net, []).append(reference)
    unclamped = []
    for net in sorted(netlist.entering_conductors()):
        if net in clamps or net in netlist.ESD_EXEMPT:
            continue
        unclamped.append(net)
    results = [{
        "id": "every_entering_conductor_is_clamped_or_exempt",
        "identity": "connectors",
        "measured_c": float(len(unclamped)),
        "claim": _structural(
            "connectors", "protection", unclamped,
            "no_unclamped_conductor_enters_the_board",
            documents=("tpd1e10b06_ti", "smf16a_jingdao",
                       "smaj_littelfuse")),
    }]
    # A clamp must stand off the highest level its own net reaches, or it
    # conducts in normal operation.
    levels = _net_levels(parameters)
    over = []
    for net, references in sorted(clamps.items()):
        level = levels.get(net)
        if level is None:
            continue
        for reference in references:
            spec = _spec(parameters, reference)
            standoff = (spec.get("tvs", {}).get("reverse_standoff_v")
                        or spec.get("reverse_standoff_v"))
            if standoff is None:
                continue
            if level > standoff["value"]:
                over.append((net, reference, level, standoff["value"]))
    results.append({
        "id": "every_clamp_stands_off_its_own_net",
        "identity": "clamps",
        "measured_c": float(len(over)),
        "claim": _structural(
            "clamps", "protection", over,
            "no_clamp_conducts_in_normal_operation",
            documents=("tpd1e10b06_ti", "smf16a_jingdao",
                       "smaj_littelfuse")),
    })
    return results


def _net_levels(parameters):
    """The highest steady voltage each net reaches in normal operation."""
    supply = Supply(parameters)
    levels = {
        "V12IN": supply.input_max_v,
        "V12P": supply.protected_max_v,
        "VHOLD": supply.protected_max_v,
        "+3V3": supply.logic_rail_max_v,
        "GND": 0.0,
        "PGND": 0.0,
        "PFET_G": supply.protected_max_v,
        "V12P_SENSE": supply.protected_max_v * _resistor_ohms("R43") / (
            _resistor_ohms("R42") + _resistor_ohms("R43")),
        "HOST_TX": supply.logic_rail_max_v,
        "HOST_RX": supply.logic_rail_max_v,
        "UART_TX": supply.logic_rail_max_v,
        "UART_RX": supply.logic_rail_max_v,
        "SWD_DIO": supply.logic_rail_max_v,
        "SWD_CLK": supply.logic_rail_max_v,
        "SWDIO": supply.logic_rail_max_v,
        "SWCLK": supply.logic_rail_max_v,
        "NRST": supply.logic_rail_max_v,
        "PWR_LED_A": supply.logic_rail_max_v,
    }
    for channel in range(1, netlist.CHANNEL_COUNT + 1):
        levels["CH%d_FUSED" % channel] = supply.protected_max_v
        levels["CH%d_PG" % channel] = supply.protected_max_v
        levels["CH%d_GD" % channel] = supply.protected_max_v
        levels["CH%d_EN" % channel] = supply.logic_rail_max_v
        levels["FAN%d_12V" % channel] = supply.fan_supply_max_v
        levels["CH%d_SENSE" % channel] = (
            supply.fan_supply_max_v * _resistor_ohms("R38")
            / (_resistor_ohms("R34") + _resistor_ohms("R38")))
        levels["PWM%d" % channel] = supply.logic_rail_max_v
        levels["PWM%d_G" % channel] = supply.logic_rail_max_v
        levels["PWM%d_D" % channel] = netlist.PWM_OPEN_CIRCUIT_MAX_V
        levels["FAN%d_PWM" % channel] = netlist.PWM_OPEN_CIRCUIT_MAX_V
        levels["FAN%d_TACH" % channel] = supply.logic_rail_max_v
        levels["TACH%d" % channel] = supply.logic_rail_max_v
    return levels


def evaluate_absolute_maximum(parameters):
    """No device pin sees more than its datasheet permits."""
    levels = _net_levels(parameters)
    pin_net = netlist.pin_to_net()
    mcu = _spec(parameters, "U1")
    limit_v = mcu["input_voltage_max_v"]["value"]
    over = []
    for pin, net in sorted(pin_net.items()):
        if not pin.startswith("U1."):
            continue
        level = levels.get(net)
        if level is None:
            over.append((pin, net, None))
        elif level > limit_v:
            over.append((pin, net, level))
    return [{
        "id": "no_controller_pin_exceeds_its_input_rating",
        "identity": "U1",
        "measured_c": float(len(over)),
        "claim": _structural(
            "U1", "absolute_maximum", over,
            "every_controller_pin_within_its_input_rating",
            documents=("stm32g030_st",)),
    }]


# ---------------------------------------------------------------------------
# structure

def evaluate_ground_topology(parameters):
    """The two ground systems meet at one declared component and nowhere else."""
    pin_net = netlist.pin_to_net()
    bridges = []
    for reference in sorted(netlist.PARTS):
        pins = [pin for pin in pin_net if pin.startswith(reference + ".")]
        nets = {pin_net[pin] for pin in pins}
        if {netlist.POWER_GROUND_NET, netlist.SIGNAL_GROUND_NET} <= nets:
            if reference != netlist.GROUND_STAR_REFERENCE:
                bridges.append(reference)
    star_pins = {pin_net.get("%s.1" % netlist.GROUND_STAR_REFERENCE),
                 pin_net.get("%s.2" % netlist.GROUND_STAR_REFERENCE)}
    if star_pins != {netlist.POWER_GROUND_NET, netlist.SIGNAL_GROUND_NET}:
        bridges.append(netlist.GROUND_STAR_REFERENCE)
    return [{
        "id": "fan_return_and_sense_reference_meet_at_one_point",
        "identity": "PGND",
        "measured_c": float(len(bridges)),
        "claim": _structural(
            "PGND", "topology", bridges,
            "one_deliberate_link_between_the_ground_systems",
            omissions=(
                "the copper each system covers, and therefore the drop the "
                "fan return actually puts into the sense reference, is a "
                "layout quantity and is not established here",)),
    }]


def evaluate_connector_contract(parameters):
    """Each fan connector carries the standard's own pin order."""
    pin_net = netlist.pin_to_net()
    wrong = []
    for channel in range(1, netlist.CHANNEL_COUNT + 1):
        reference = "J%d" % (channel + 1)
        expected = {
            netlist.FAN_CONNECTOR_PINS["GND"]: netlist.POWER_GROUND_NET,
            netlist.FAN_CONNECTOR_PINS["12V"]: "FAN%d_12V" % channel,
            netlist.FAN_CONNECTOR_PINS["SENSE"]: "FAN%d_TACH" % channel,
            netlist.FAN_CONNECTOR_PINS["CONTROL"]: "FAN%d_PWM" % channel,
        }
        for pin, net in sorted(expected.items()):
            found = pin_net.get("%s.%d" % (reference, pin))
            if found != net:
                wrong.append((reference, pin, net, found))
    results = [{
        "id": "fan_connectors_carry_the_standard_pin_order",
        "identity": "fan_connectors",
        "measured_c": float(len(wrong)),
        "claim": _structural(
            "fan_connectors", "interface_compliance", wrong,
            "every_fan_pin_carries_its_standard_function",
            documents=(FAN_SPEC,)),
    }]
    contact_a = _spec(parameters, "J2")["contact_current_max_a"]["value"]
    results.append({
        "id": "fan_connector_contact_carries_the_channel_rating",
        "identity": "J2",
        "measured_a": netlist.CHANNEL_CURRENT_RATING_A,
        "claim": _claim(
            "J2", "A", "interface_compliance",
            netlist.CHANNEL_CURRENT_RATING_A, DIRECT,
            ("fanheader_2510_cax",),
            _requirement("within_the_contact_current_rating", "<=",
                         contact_a),
            scope_level="group"),
    })
    input_a = _spec(parameters, "J1")["contact_current_max_a"]["value"]
    total_a = netlist.CHANNEL_COUNT * netlist.CHANNEL_CURRENT_RATING_A
    results.append({
        "id": "input_terminal_carries_every_channel_at_once",
        "identity": "J1",
        "measured_a": total_a,
        "claim": _claim(
            "J1", "A", "interface_compliance", total_a, DIRECT,
            ("kf128_cixikefa",),
            _requirement("within_the_terminal_current_rating", "<=", input_a),
            scope_level="group"),
    })
    results.append({
        "id": "fan_connector_mates_a_standard_fan_plug",
        "identity": "J2",
        "measured_c": None,
        "claim": _claim(
            "J2", "mates", "interface_compliance", None, ASSUMED,
            (FAN_SPEC, "fanheader_2510_cax"),
            _requirement("mates_a_conforming_fan_housing", ">=", 1.0,
                         FAN_SPEC),
            scope_level="group",
            omissions=(
                "the standard names particular housings and their mating "
                "headers and permits equivalents; the header's own drawing "
                "claims no equivalence to any of them, so mating is not "
                "established from the frozen documents and needs a fan plug "
                "and a built board",)),
    })
    return results


def evaluate_probe_access(parameters):
    pin_net = netlist.pin_to_net()
    probed = {pin_net[pin] for pin in pin_net
              if netlist.PARTS[pin.split(".")[0]]["lib_id"]
              == "Connector:TestPoint"}
    missing = [net for net in netlist.PROBE_REQUIRED_NETS
               if net not in probed]
    return [{
        "id": "every_required_net_reaches_a_probe",
        "identity": "test_points",
        "measured_c": float(len(missing)),
        "claim": _structural("test_points", "serviceability", missing,
                             "no_required_net_without_a_probe"),
    }]


def _footprint_pad_count(footprint):
    library, _, name = footprint.partition(":")
    for root in (LOCAL_FOOTPRINT_ROOT, FOOTPRINT_ROOT):
        path = os.path.join(root, library + ".pretty", name + ".kicad_mod")
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as handle:
                text = handle.read()
            numbers = set()
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith('(pad "'):
                    numbers.add(stripped.split('"')[1])
            return len(numbers)
    return None


def evaluate_package_correspondence(parameters):
    """Symbol pins, land-pattern pads and the package drawing agree."""
    from . import ksym
    library = ksym.Library(netlist.SYMBOL_LIBRARY_PATHS)
    mismatches = []
    for reference, part in sorted(netlist.PARTS.items()):
        if not part["in_bom"]:
            continue
        spec = parameters["parts"][part["mpn"]]
        declared = spec.get("land_pattern", {}).get("pad_count")
        if declared is None:
            continue
        symbol_pins = len(library.pins(part["lib_id"]))
        pads = _footprint_pad_count(part["footprint"])
        if symbol_pins != declared or pads != declared:
            mismatches.append((reference, declared, symbol_pins, pads))
    results = [{
        "id": "symbol_pins_and_land_pattern_pads_match_the_drawing",
        "identity": "library",
        "measured_c": float(len(mismatches)),
        "claim": _structural(
            "library", "package_correspondence", mismatches,
            "every_declared_terminal_count_agrees"),
    }]
    contested = [pin for pin in netlist.MCU_CONTESTED_PINS
                 if "U1.%s" % pin not in netlist.NO_CONNECT]
    results.append({
        "id": "contested_package_pins_carry_nothing",
        "identity": "U1",
        "measured_c": float(len(contested)),
        "claim": _structural(
            "U1", "package_correspondence", contested,
            "no_design_dependence_on_a_contested_pin",
            documents=("stm32g030_st",),
            assumptions=(
                "the datasheet's package pinout names two pins the shipped "
                "symbol calls no-connect; the disagreement is unresolved, so "
                "both are left unconnected and nothing depends on which "
                "source is right",)),
    })
    return results


def evaluate_supply_availability(parameters):
    catalog = load_catalog()["parts"]
    counts = {}
    for part in netlist.PARTS.values():
        if part["in_bom"]:
            counts[part["lcsc"]] = counts.get(part["lcsc"], 0) + 1
    results = []
    for code in sorted(counts):
        entry = catalog[code]
        boards = entry["stock"] // counts[code]
        results.append({
            "id": "catalogue_stock_covers_the_planned_build",
            "identity": code,
            "measured_c": float(boards),
            "claim": _claim(
                code, "boards", "supply", float(boards), DIRECT,
                ("components/jlcpcb.json",),
                _requirement("at_or_above_the_planned_build", ">=",
                             float(netlist.PLANNED_BUILD_QUANTITY)),
                scope_level="group",
                assumptions=(
                    "the catalogue reading is frozen; stock moves and this "
                    "is the figure the design was accepted against",)),
        })
    return results


def evaluate_assembly(parameters):
    through_hole = sorted(
        reference for reference, part in netlist.PARTS.items()
        if part["in_bom"] and _footprint_is_through_hole(part["footprint"]))
    declared = netlist.ASSEMBLY_POLICY["through_hole_soldered_parts"]
    return [{
        "id": "through_hole_population_matches_the_declared_process",
        "identity": "assembly",
        "measured_c": float(len(through_hole)),
        "claim": _claim(
            "assembly", "parts", "manufacturability",
            float(len(through_hole)), DERIVED, (),
            _requirement("equals_the_declared_through_hole_count", "<=",
                         float(declared)),
            scope_level="board",
            omissions=(
                "which side each part sits on is a layout property and is "
                "not established from the netlist",)),
    }]


def _footprint_is_through_hole(footprint):
    library, _, name = footprint.partition(":")
    for root in (LOCAL_FOOTPRINT_ROOT, FOOTPRINT_ROOT):
        path = os.path.join(root, library + ".pretty", name + ".kicad_mod")
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as handle:
                return "thru_hole" in handle.read()
    raise ValueError("no footprint file for " + footprint)


# ---------------------------------------------------------------------------

PRODUCERS = (
    evaluate_fan_supply,
    evaluate_channel_protection,
    evaluate_channel_switch,
    evaluate_control_output,
    evaluate_control_topology,
    evaluate_control_short_to_supply,
    evaluate_control_timing,
    evaluate_sense_input,
    evaluate_injection_policy,
    evaluate_rails,
    evaluate_reverse_polarity,
    evaluate_dissipation,
    evaluate_esd_coverage,
    evaluate_absolute_maximum,
    evaluate_ground_topology,
    evaluate_connector_contract,
    evaluate_probe_access,
    evaluate_package_correspondence,
    evaluate_supply_availability,
    evaluate_assembly,
)


def evaluate_all():
    parameters = load_parameters()
    results = []
    for producer in PRODUCERS:
        results.extend(producer(parameters))
    for result in results:
        result["verdict"] = claim.verdict(result["claim"])
    return results


REPORT_PATH = os.path.join(REPO_ROOT, "generated", "requirements.json")


def write_report():
    """The whole claim set, as an artifact rather than a console report.

    Each entry carries what was measured, the evidence class it rests on, the
    documents behind it, the assumptions it was evaluated under and the
    verdict - so a later reader can see not only that the board passed but
    what "passed" was allowed to mean.
    """
    evaluated = evaluate_all()
    document = {
        "kind": "board-requirement-evidence",
        "summary": summarise(evaluated),
        "results": [
            {"id": result["id"], "identity": result["identity"],
             "claim": result["claim"], "verdict": result["verdict"]}
            for result in sorted(evaluated,
                                 key=lambda item: (item["id"],
                                                   item["identity"]))],
    }
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(document, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return REPORT_PATH


def summarise(results):
    counts = {}
    for result in results:
        counts[result["verdict"]["result"]] = counts.get(
            result["verdict"]["result"], 0) + 1
    return counts


if __name__ == "__main__":
    evaluated = evaluate_all()
    write_report()
    for result in sorted(evaluated, key=lambda item: (
            item["verdict"]["result"], item["id"], item["identity"])):
        value = result["claim"]["quantity"].get("value")
        rendered = "-" if value is None else "%.6g" % value
        sys.stdout.write("%-8s %-56s %-16s %12s %s\n" % (
            result["verdict"]["result"], result["id"], result["identity"],
            rendered, result["claim"]["units"]))
    sys.stdout.write("\n" + json.dumps(summarise(evaluated), sort_keys=True)
                     + "\n")
