from __future__ import annotations

import os

CHANNEL_COUNT = 4

PROJECT_NAME = "quad_fan_controller"

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SYMBOL_LIBRARY_PATHS = (
    os.path.join(_REPO_ROOT, "library"),
    "/usr/share/kicad/symbols",
)

LIBRARY_NAME = "QuadFanController"

#: Fan connector function -> connector pin, from the 4-wire fan specification
#: table 1. The order is the whole point of the connector: a plug that mates
#: mechanically but not in this order destroys the fan.
FAN_CONNECTOR_PINS = {"GND": 1, "12V": 2, "SENSE": 3, "CONTROL": 4}

#: MCU pin each channel signal lands on, in channel order. LQFP-32 pin numbers
#: from DS12991 figure 4; the peripheral each one carries is in
#: CHANNEL_PWM_FUNCTIONS / CHANNEL_TACH_FUNCTIONS below.
CHANNEL_PWM_PINS = ("13", "14", "15", "16")
CHANNEL_TACH_PINS = ("18", "27", "30", "22")
CHANNEL_ENABLE_PINS = ("17", "28", "29", "32")
CHANNEL_SENSE_PINS = ("7", "11", "23", "31")

#: The four PWM outputs are four compare channels of one timer, and the four
#: tach inputs are four capture channels of another, so each group shares a
#: counter, a prescaler and a period: equal frequency and equal resolution on
#: every channel is a property of the pin choice, not of the firmware.
CHANNEL_PWM_FUNCTIONS = ("TIM3_CH1", "TIM3_CH2", "TIM3_CH3", "TIM3_CH4")
CHANNEL_TACH_FUNCTIONS = ("TIM1_CH1", "TIM1_CH2", "TIM1_CH3", "TIM1_CH4")

#: ADC channel behind each sense divider, and behind the input-rail divider.
CHANNEL_SENSE_FUNCTIONS = ("ADC_IN0", "ADC_IN4", "ADC_IN16", "ADC_IN11")
RAIL_SENSE_FUNCTION = "ADC_IN1"
RAIL_SENSE_PIN = "8"

#: Pins the datasheet's injection-susceptibility table says tolerate no
#: negative injection at all. A conductor that leaves the board may be driven
#: below the reference, so no such conductor reaches one of these.
MCU_NO_NEGATIVE_INJECTION_PINS = {
    "8": "PA1", "12": "PA5", "24": "PA13", "16": "PB1", "17": "PB2",
    "32": "PB8",
}

#: Pins the LQFP-32 brings out that this board does not use. Pins 19 and 21
#: are the two the datasheet pinout calls PA9 and PA10 and the KiCad symbol
#: calls NC: the contradiction is unresolved, so the design does not depend on
#: either reading.
MCU_UNUSED_PINS = ("1", "2", "3", "12", "19", "20", "21", "26")

#: The two package pins whose identity the sources disagree about, and what
#: each source says. Recorded so the disagreement is visible rather than
#: silently resolved in favour of whichever was read last.
MCU_CONTESTED_PINS = {
    "19": {"datasheet": "PA9", "symbol": "NC/PA9"},
    "21": {"datasheet": "PA10", "symbol": "NC/PA10"},
}


def _part(lib_id, footprint, value, mpn=None, manufacturer=None, lcsc=None,
          datasheet="", in_bom=True, on_board=True):
    return {
        "lib_id": lib_id,
        "footprint": footprint,
        "value": value,
        "mpn": mpn,
        "manufacturer": manufacturer,
        "lcsc": lcsc,
        "datasheet": datasheet,
        "in_bom": in_bom,
        "on_board": on_board,
    }


def _resistor(value, lcsc, mpn):
    return _part("Device:R", "Resistor_SMD:R_0603_1608Metric", value,
                 mpn, "UNI-ROYAL(Uniroyal Elec)", lcsc)


def _capacitor(value, footprint, lcsc, mpn, manufacturer,
               lib_id="Device:C"):
    return _part(lib_id, footprint, value, mpn, manufacturer, lcsc)


#: Resistor values used on this board, and the catalogue part behind each.
RESISTOR_PARTS = {
    "0R": ("C21189", "0603WAF0000T5E"),
    "47R": ("C23182", "0603WAF470JT5E"),
    "100R": ("C22775", "0603WAF1000T5E"),
    "1.5k": ("C22843", "0603WAF1501T5E"),
    "2.2k": ("C4190", "0603WAF2201T5E"),
    "4.7k": ("C23162", "0603WAF4701T5E"),
    "470R": ("C23179", "0603WAF4700T5E"),
    "10k": ("C25804", "0603WAF1002T5E"),
    "33k": ("C4216", "0603WAF3302T5E"),
    "100k": ("C25803", "0603WAF1003T5E"),
}

#: Where every resistor goes. The index is the reference number; channel
#: blocks are laid out as four consecutive numbers so the layout can group
#: them without a second table.
_RESISTOR_VALUES = {1: "100k", 42: "33k", 43: "10k", 44: "1.5k", 45: "0R",
                    46: "2.2k", 47: "2.2k", 48: "470R", 49: "470R"}
for _base, _value in ((2, "100k"), (6, "100k"), (10, "100k"), (14, "100R"),
                      (18, "100k"), (22, "47R"), (26, "4.7k"), (30, "4.7k"),
                      (34, "33k"), (38, "10k")):
    for _offset in range(CHANNEL_COUNT):
        _RESISTOR_VALUES[_base + _offset] = _value


def _parts():
    parts = {
        "U1": _part(
            "MCU_ST_STM32G0:STM32G030K8Tx",
            "Package_QFP:LQFP-32_7x7mm_P0.8mm",
            "STM32G030K8T6", "STM32G030K8T6TR", "STMicroelectronics",
            "C724044"),
        "U2": _part(
            "%s:HT75Rxx-1" % LIBRARY_NAME,
            "Package_TO_SOT_SMD:SOT-89-3",
            "HT75R33-1A", "HT75R33-1A", "Holtek Semiconductor", "C53223865"),
        "Q1": _part(
            "%s:AO4407A" % LIBRARY_NAME,
            "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
            "AO4407A", "AO4407A", "Alpha & Omega Semiconductor", "C16072"),
        "D1": _part(
            "Device:D_TVS", "Diode_SMD:D_SMA",
            "SMAJ16A", "SMAJ16A", "Littelfuse", "C74561"),
        "D6": _part(
            "Device:D_Schottky", "Diode_SMD:D_SOD-123",
            "B5819W", "B5819W SL", "Jiangsu Changjing Elec", "C8598"),
        "D24": _part(
            "Device:LED", "LED_SMD:LED_0603_1608Metric",
            "KT-0603R", "KT-0603R", "Hubei KENTO Elec", "C2286"),
        "J1": _part(
            "%s:ScrewTerminal_1x02" % LIBRARY_NAME,
            "%s:TerminalBlock_KF128-5.08_1x02_P5.08mm" % LIBRARY_NAME,
            "KF128-5.08-2P-AA", "KF128-5.08-2P-AA", "Cixi Kefa Elec",
            "C474952"),
        "J6": _part(
            "Connector_Generic:Conn_01x03",
            "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
            "KH-2.54PH180-1X3P-L11.5", "KH-2.54PH180-1X3P-L11.5",
            "Shenzhen Kinghelm Elec", "C2932698"),
        "J7": _part(
            "Connector_Generic:Conn_01x05",
            "Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical",
            "KH-2.54PH180-1X5P-L11.5", "KH-2.54PH180-1X5P-L11.5",
            "Shenzhen Kinghelm Elec", "C2932699"),
        "C1": _capacitor(
            "100uF", "Capacitor_SMD:CP_Elec_6.3x7.7", "C2836443",
            "RVT100UF25V67RV0011", "KNSCHA", "Device:C_Polarized"),
        "C3": _capacitor(
            "100uF", "Capacitor_SMD:CP_Elec_6.3x7.7", "C2836443",
            "RVT100UF25V67RV0011", "KNSCHA", "Device:C_Polarized"),
        "C5": _capacitor(
            "10uF", "Capacitor_SMD:C_0805_2012Metric", "C15850",
            "CL21A106KAYNNNE", "Samsung Electro-Mechanics"),
    }
    for index in (2, 4, 6, 7, 8):
        parts["C%d" % index] = _capacitor(
            "100nF", "Capacitor_SMD:C_0603_1608Metric", "C14663",
            "CC0603KRX7R9BB104", "YAGEO")
    for channel in range(1, CHANNEL_COUNT + 1):
        parts["Q%d" % (channel + 1)] = _part(
            "Transistor_FET:AO3401A", "Package_TO_SOT_SMD:SOT-23",
            "AO3401A", "AO3401A", "Alpha & Omega Semiconductor", "C15127")
        for offset in (5, 9):
            parts["Q%d" % (channel + offset)] = _part(
                "Transistor_FET:AO3400A", "Package_TO_SOT_SMD:SOT-23",
                "AO3400A", "AO3400A", "Alpha & Omega Semiconductor", "C20917")
        parts["F%d" % channel] = _part(
            "Device:Polyfuse", "%s:PTC_1812_Jinrui_JK-mSMD" % LIBRARY_NAME,
            "JK-MSMD200-24V", "JK-MSMD200-24V",
            "Jinrui Electronic Material", "C561584")
        for offset in (1, 6):
            parts["D%d" % (channel + offset)] = _part(
                "Device:D_Schottky", "Diode_SMD:D_SOD-123",
                "B5819W", "B5819W SL", "Jiangsu Changjing Elec", "C8598")
        for offset in (10, 14):
            parts["D%d" % (channel + offset)] = _part(
                "Device:D_TVS", "%s:D_SOD-123FL_1.2x1.2mm_P3.2mm" % LIBRARY_NAME,
                "SMF16A", "SMF16A", "Shandong Jingdao Microelectronics",
                "C353308")
        parts["C%d" % (channel + 8)] = _capacitor(
            "1nF", "Capacitor_SMD:C_0603_1608Metric", "C100040",
            "CC0603KRX7R9BB102", "YAGEO")
        parts["J%d" % (channel + 1)] = _part(
            "%s:FanHeader_1x04" % LIBRARY_NAME,
            "%s:FanHeader_2510_1x04_P2.54mm_Horizontal" % LIBRARY_NAME,
            "KF2510-4AGW-GW", "KF2510-4AGW-GW", "CAX", "C722747")
    for index in range(19, 24):
        parts["D%d" % index] = _part(
            "%s:TPD1E10B06" % LIBRARY_NAME,
            "%s:TI_X1SON-2_1.0x0.6mm_P0.65mm" % LIBRARY_NAME,
            "TPD1E10B06DPYR", "TPD1E10B06DPYR", "Texas Instruments", "C48260")
    for index, value in sorted(_RESISTOR_VALUES.items()):
        lcsc, mpn = RESISTOR_PARTS[value]
        parts["R%d" % index] = _resistor(value, lcsc, mpn)
    for index in range(1, 13):
        parts["TP%d" % index] = _part(
            "Connector:TestPoint", "TestPoint:TestPoint_Pad_D1.0mm",
            "TestPoint", in_bom=False)
    for index in range(1, 5):
        parts["H%d" % index] = _part(
            "Mechanical:MountingHole",
            "MountingHole:MountingHole_3.2mm_M3",
            "MountingHole_M3", in_bom=False)
    for index in range(1, 6):
        parts["#FLG%d" % index] = _part(
            "power:PWR_FLAG", "", "PWR_FLAG", in_bom=False, on_board=False)
    return parts


PARTS = _parts()


def _nets():
    #: Power return for the fan current: the input terminal, the bulk, and
    #: every fan connector's ground pin. It reaches the signal reference only
    #: through R45.
    power_ground = [
        "J1.2", "R1.2", "D1.2", "C1.2", "C2.2", "R45.2", "TP4.1", "#FLG4.1",
    ]
    #: Signal reference for the MCU, the tach thresholds and the PWM drivers.
    signal_ground = [
        "U1.5", "U2.1", "C3.2", "C4.2", "C5.2", "C6.2", "C7.2", "C8.2",
        "R43.2", "D24.1", "J6.1", "J7.1", "R45.1", "TP3.1", "#FLG5.1",
    ]
    input_rail = ["J1.1", "Q1.5", "Q1.6", "Q1.7", "Q1.8", "#FLG1.1"]
    protected_rail = [
        "Q1.1", "Q1.2", "Q1.3", "D1.1", "C1.1", "C2.1", "D6.2", "R42.1",
        "TP1.1", "#FLG2.1",
    ]
    hold_up_rail = ["D6.1", "C3.1", "C4.1", "U2.2", "#FLG3.1"]
    logic_rail = [
        "U2.3", "C5.1", "C6.1", "C7.1", "U1.4", "R44.1", "J7.2", "TP2.1",
    ]
    for index in range(19, 24):
        signal_ground.append("D%d.1" % index)
    for channel in range(1, CHANNEL_COUNT + 1):
        protected_rail.append("F%d.1" % channel)
        power_ground.append("J%d.%d" % (channel + 1,
                                        FAN_CONNECTOR_PINS["GND"]))
        power_ground.append("D%d.2" % (channel + 1))
        power_ground.append("D%d.2" % (channel + 10))
        power_ground.append("D%d.2" % (channel + 14))
        # Everything in a channel returns to the power ground, including
        # the control driver's source: the level the fan measures is between
        # its own control pin and its own ground pin, and both of those are
        # the connector's, not the controller's. Only the sense filter is on
        # the signal ground, because it sits at the receiver.
        power_ground.append("Q%d.2" % (channel + 5))
        power_ground.append("Q%d.2" % (channel + 9))
        power_ground.append("R%d.2" % (channel + 9))
        power_ground.append("R%d.2" % (channel + 17))
        power_ground.append("R%d.2" % (channel + 37))
        signal_ground.append("C%d.2" % (channel + 8))
        logic_rail.append("R%d.2" % (channel + 25))
        logic_rail.append("D%d.1" % (channel + 6))

    nets = {
        "PGND": power_ground,
        "GND": signal_ground,
        "V12IN": input_rail,
        "V12P": protected_rail,
        "VHOLD": hold_up_rail,
        "+3V3": logic_rail,
        "PFET_G": ["Q1.4", "R1.1"],
        "V12P_SENSE": ["R42.2", "R43.1", "U1." + RAIL_SENSE_PIN],
        "HOST_TX": ["J6.2", "D19.2", "R46.1"],
        "UART_TX": ["R46.2", "U1.9"],
        "HOST_RX": ["J6.3", "D20.2", "R47.1"],
        "UART_RX": ["R47.2", "U1.10"],
        "SWD_DIO": ["J7.3", "D21.2", "R48.1"],
        "SWDIO": ["R48.2", "U1.24"],
        "SWD_CLK": ["J7.4", "D22.2", "R49.1"],
        "SWCLK": ["R49.2", "U1.25"],
        "NRST": ["U1.6", "J7.5", "C8.1", "D23.2"],
        "PWR_LED_A": ["R44.2", "D24.2"],
    }
    for channel in range(1, CHANNEL_COUNT + 1):
        index = channel - 1
        connector = "J%d" % (channel + 1)
        nets["CH%d_FUSED" % channel] = [
            "F%d.2" % channel, "Q%d.2" % (channel + 1),
            "R%d.2" % (channel + 1)]
        nets["CH%d_PG" % channel] = [
            "Q%d.1" % (channel + 1), "R%d.1" % (channel + 1),
            "R%d.1" % (channel + 5)]
        nets["CH%d_GD" % channel] = [
            "R%d.2" % (channel + 5), "Q%d.3" % (channel + 5)]
        nets["CH%d_EN" % channel] = [
            "U1.%s" % CHANNEL_ENABLE_PINS[index], "Q%d.1" % (channel + 5),
            "R%d.1" % (channel + 9)]
        nets["FAN%d_12V" % channel] = [
            "Q%d.3" % (channel + 1), "D%d.1" % (channel + 1),
            "%s.%d" % (connector, FAN_CONNECTOR_PINS["12V"]),
            "R%d.1" % (channel + 33)]
        nets["CH%d_SENSE" % channel] = [
            "R%d.2" % (channel + 33), "R%d.1" % (channel + 37),
            "U1.%s" % CHANNEL_SENSE_PINS[index]]
        nets["PWM%d" % channel] = [
            "U1.%s" % CHANNEL_PWM_PINS[index], "R%d.1" % (channel + 13)]
        nets["PWM%d_G" % channel] = [
            "R%d.2" % (channel + 13), "R%d.1" % (channel + 17),
            "Q%d.1" % (channel + 9)]
        nets["PWM%d_D" % channel] = [
            "Q%d.3" % (channel + 9), "R%d.1" % (channel + 21)]
        nets["FAN%d_PWM" % channel] = [
            "R%d.2" % (channel + 21),
            "%s.%d" % (connector, FAN_CONNECTOR_PINS["CONTROL"]),
            "D%d.1" % (channel + 10), "TP%d.1" % (channel + 4)]
        nets["FAN%d_TACH" % channel] = [
            "%s.%d" % (connector, FAN_CONNECTOR_PINS["SENSE"]),
            "R%d.1" % (channel + 25), "R%d.1" % (channel + 29),
            "D%d.1" % (channel + 14), "TP%d.1" % (channel + 8)]
        nets["TACH%d" % channel] = [
            "R%d.2" % (channel + 29), "C%d.1" % (channel + 8),
            "D%d.2" % (channel + 6), "U1.%s" % CHANNEL_TACH_PINS[index]]
    return nets


NETS = _nets()

NO_CONNECT = tuple("U1.%s" % pin for pin in MCU_UNUSED_PINS)


#: What the board's silkscreen declares and every rail claim is evaluated
#: over. The lower bound is not the fan standard's 12 V -5%: the board's own
#: series drop has to come out of the supply's budget, so a supply at 11.4 V
#: cannot deliver 11.4 V at the fan. The upper bound is the fan standard's,
#: because the board passes the input through.
INPUT_SUPPLY = {"min_v": 11.9, "max_v": 12.6}

#: Measured at the board's input terminal, not at the supply: the resistance
#: of the field wiring is the integrator's budget, not the board's.
#:
#: The highest steady input the board is required to survive undamaged. Set
#: by the input clamp's stand-off voltage, above which it starts to conduct.
INPUT_SURVIVAL_MAX_V = 16.0

RAILS = {
    "V12IN": dict(INPUT_SUPPLY),
    "V12P": dict(INPUT_SUPPLY),
    "VHOLD": dict(INPUT_SUPPLY),
    "GND": {"min_v": 0.0, "max_v": 0.0},
    "PGND": {"min_v": 0.0, "max_v": 0.0},
}

#: Every net the board treats as a supply. The logic rail's limits are the
#: regulator's own and are not restated here; what this tuple is for is the
#: question "is this net a rail?", which the control-trace check asks.
POWER_NETS = tuple(RAILS) + ("+3V3",)

#: Fan supply window the 4-wire specification requires at the fan, and the
#: currents it permits a conforming fan to draw.
FAN_SUPPLY = {"min_v": 11.4, "max_v": 12.6}
FAN_SPEC_STEADY_CURRENT_MAX_A = 1.5
FAN_SPEC_STARTUP_CURRENT_MAX_A = 2.2
FAN_SPEC_STARTUP_SECONDS = 1.0

#: What this board is rated to deliver per channel. Lower than the standard's
#: ceiling: the choice buys hold-current margin in the resettable fuse and
#: keeps the series drop inside the fan supply window.
CHANNEL_CURRENT_RATING_A = 1.0

#: Tach behaviour the specification does not state. It says the fan's sense
#: output is open collector and that the motherboard pulls it up to as much
#: as 12.6 V, but it states no sink current and no output low level, so the
#: board declares the two it depends on and they stay revisable.
TACH_ASSUMED_SINK_A = 0.0025
TACH_ASSUMED_LOW_LEVEL_V = 0.4

#: A budget, not a measurement: capacitance of the fan cable on a sense line,
#: and of the clamp, whose datasheet states no junction capacitance.
TACH_CABLE_CAPACITANCE_F = 150.0e-12
TACH_CLAMP_CAPACITANCE_F = 1.5e-9

#: How much of the shortest half period the sense edge may take to reach the
#: receiver's high threshold. A design target, not a standard figure.
TACH_RISE_FRACTION_OF_HALF_PERIOD = 0.2

#: The 4-wire control signal, as the specification defines it for the
#: controller end of the link.
PWM_TARGET_FREQUENCY_HZ = 25000.0
PWM_FREQUENCY_BAND_HZ = {"min": 21000.0, "max": 28000.0}
PWM_SINK_REQUIRED_A = 0.005
PWM_SINK_RECOMMENDED_A = 0.008
PWM_OUTPUT_LOW_MAX_V = 0.8
PWM_OPEN_CIRCUIT_MAX_V = 5.25

#: Tach output of a conforming fan: open collector, two pulses per turn.
TACH_PULSES_PER_REVOLUTION = 2

#: A design target, not a fan-standard figure: the highest rotation rate the
#: tach front end is required to resolve. No PC fan approaches it; it exists
#: so "passes every pulse at top speed" is a number a check can evaluate.
TACH_MAX_RPM = 60000.0

#: Timer arrangement the PWM frequency claim is evaluated against. The board
#: cannot make firmware use these, but it can establish that its clock source
#: reaches the required band with them.
PWM_TIMER_CLOCK_HZ = 16.0e6
PWM_PERIOD_COUNTS = 640

#: A budget, not a measurement: resistance of the supply and its wiring up to
#: the input terminal.
INPUT_PATH_BUDGET_OHM = 0.2

#: A budget, not a measurement: board copper between the input terminal and a
#: fan connector, before layout exists to measure it.
BOARD_COPPER_BUDGET_OHM = 0.03

#: Nets that must reach a probe with the board installed, from the brief's
#: bring-up requirement.
PROBE_REQUIRED_NETS = ("V12P", "+3V3", "GND", "PGND") + tuple(
    "FAN%d_%s" % (channel, node)
    for channel in range(1, CHANNEL_COUNT + 1)
    for node in ("PWM", "TACH"))

#: A design target, not a standard figure: how long the logic rail must ride
#: through a collapse of the fan supply.
HOLD_UP_TARGET_S = 0.050

#: A design target: the smallest number of duty steps the control output must
#: offer across the band.
PWM_RESOLUTION_STEPS_TARGET = 256

#: The highest ambient the board's per-channel current rating is claimed at.
AMBIENT_MAX_C = 60.0

#: Series element feeding the hold-up reservoir, and the reservoir itself.
HOLD_UP_DIODE_REFERENCE = "D6"
HOLD_UP_BULK_REFERENCES = ("C3",)
INPUT_BULK_REFERENCES = ("C1", "C2")
LOGIC_BULK_REFERENCES = ("C5", "C6", "C7")

#: The one deliberate connection between the two ground systems.
GROUND_STAR_REFERENCE = "R45"
POWER_GROUND_NET = "PGND"
SIGNAL_GROUND_NET = "GND"

#: The build this board is costed and supplied for. A stock reading below
#: this is a finding, not a footnote.
PLANNED_BUILD_QUANTITY = 50

#: What the assembler has to do beyond one reflow of the front side. Only
#: what a check reads is declared here.
ASSEMBLY_POLICY = {
    "placement_sides": 1,
    # the supply terminal, one fan header per channel, the host header and
    # the programming header
    "through_hole_soldered_parts": 1 + CHANNEL_COUNT + 2,
}

CONNECTOR_FUNCTION_NETS = {
    "J1": {"V12IN": "V12IN", "PGND": "PGND"},
    "J6": {"GND": "GND", "HOST_TX": "HOST_TX", "HOST_RX": "HOST_RX"},
    "J7": {"GND": "GND", "+3V3": "+3V3", "SWD_DIO": "SWD_DIO",
           "SWD_CLK": "SWD_CLK", "NRST": "NRST"},
}
for _channel in range(1, CHANNEL_COUNT + 1):
    CONNECTOR_FUNCTION_NETS["J%d" % (_channel + 1)] = {
        "GND": "PGND",
        "12V": "FAN%d_12V" % _channel,
        "SENSE": "FAN%d_TACH" % _channel,
        "CONTROL": "FAN%d_PWM" % _channel,
    }

#: A conductor that needs no clamp of its own, and why.
ESD_EXEMPT = {
    "PGND": "the reference the clamps divert into",
    "GND": "the reference the clamps divert into",
    "V12IN": "clamped by the input suppressor through the reverse-blocking "
             "device's body diode, which conducts in exactly the direction a "
             "positive surge arrives",
    "+3V3": "a regulated rail with bulk capacitance behind a regulator whose "
            "input is on the far side of the hold-up diode",
    "FAN1_12V": "clamped both ways by construction: below ground by the "
                "channel's Schottky and above the protected rail by the "
                "switch's body diode into the input bulk",
}
for _channel in range(2, CHANNEL_COUNT + 1):
    ESD_EXEMPT["FAN%d_12V" % _channel] = ESD_EXEMPT["FAN1_12V"]


def entering_conductors():
    """Every conductor that enters the board, and the connector it enters by.

    Each one has to survive ESD and a hot connection, so each one either
    carries a clamp or appears in ESD_EXEMPT with a reason.
    """
    entering = {}
    for reference, functions in CONNECTOR_FUNCTION_NETS.items():
        for net in functions.values():
            entering.setdefault(net, []).append(reference)
    return {net: sorted(refs) for net, refs in entering.items()}


def pin_to_net():
    mapping = {}
    for net_name, pin_refs in NETS.items():
        for pin_ref in pin_refs:
            if pin_ref in mapping:
                raise ValueError(
                    "pin %s assigned to both %s and %s"
                    % (pin_ref, mapping[pin_ref], net_name))
            mapping[pin_ref] = net_name
    for pin_ref in NO_CONNECT:
        if pin_ref in mapping:
            raise ValueError(
                "pin %s is both no-connect and on net %s"
                % (pin_ref, mapping[pin_ref]))
    return mapping
