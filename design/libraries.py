from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIBRARY_NAME = "QuadFanController"
SYMBOL_LIB_PATH = os.path.join(REPO_ROOT, "library",
                               LIBRARY_NAME + ".kicad_sym")
FOOTPRINT_DIR = os.path.join(REPO_ROOT, "library", LIBRARY_NAME + ".pretty")
SYM_LIB_TABLE = os.path.join(REPO_ROOT, "sym-lib-table")
FP_LIB_TABLE = os.path.join(REPO_ROOT, "fp-lib-table")

SYMBOL_LIB_VERSION = "20251024"
FOOTPRINT_VERSION = "20260206"
GENERATOR = "quad-fan-controller-design-source"

# Holtek HT75Rxx-1 Rev. 1.01, pin diagram: SOT89 is GND, VIN, VOUT on pins
# 1, 2, 3. The regulator output is the only power source on the logic rail,
# so it is declared power_out and the rail carries no separate power flag.
LDO_SYMBOL_NAME = "HT75Rxx-1"
LDO_PINS = [("2", "VIN", "power_in", "left"),
            ("3", "VOUT", "power_out", "right"),
            ("1", "GND", "power_in", "bottom")]
LDO_DATASHEET = ("https://datasheet.lcsc.com/datasheet/pdf/"
                 "59abfa7ca0c1b0cd081d8e8f60c28ed0.pdf")

# AO4407A Rev3, SOIC-8 top view: source on pins 1-3, gate on pin 4, drain on
# pins 5-8. Every package terminal is drawn, so the schematic and the land
# pattern agree pad for pad rather than through a "connect the rest" note.
PFET_SYMBOL_NAME = "AO4407A"
PFET_SOURCE_PINS = ("1", "2", "3")
PFET_GATE_PIN = "4"
PFET_DRAIN_PINS = ("5", "6", "7", "8")
PFET_DATASHEET = ("https://datasheet.lcsc.com/datasheet/pdf/"
                  "6bf17916e7274c4fb32122c6ec48f2db.pdf")

TVS_SYMBOL_NAME = "TPD1E10B06"
TVS_DATASHEET = "https://www.ti.com/lit/ds/symlink/tpd1e10b06.pdf"

# The 4-wire fan interface, named on the symbol so a wrong connection is
# visible in the schematic rather than only in a table. Pin order is fixed by
# the 4-wire fan specification, table 1.
FAN_SYMBOL_NAME = "FanHeader_1x04"
FAN_SYMBOL_PINS = [("1", "GND"), ("2", "+12V"), ("3", "SENSE"),
                   ("4", "CONTROL")]

TERMINAL_SYMBOLS = {"ScrewTerminal_1x02": ["1", "2"]}
TERMINAL_FOOTPRINT_FILTER = "TerminalBlock*"

# TI DPY0002A, drawing 4224561/C (SLLSEB1G): land pattern 2x (0.3) wide by
# 2x (0.5) tall on (0.7) centres; package outline 1.1/0.9 by 0.7/0.5.
X1SON_FOOTPRINT_NAME = "TI_X1SON-2_1.0x0.6mm_P0.65mm"
X1SON_PAD_SIZE_MM = (0.30, 0.50)
X1SON_PAD_PITCH_MM = 0.70
X1SON_BODY_MM = (1.10, 0.70)
X1SON_COURTYARD_MARGIN_MM = 0.15

# Cixi Kefa KF128-5.08 drawing rev A (2021-03-13): PCB layout is two
# 1.40 +0.10/-0.00 holes on 5.08 +/-0.03 centres; body 10.70 deep with the
# pin row 5.40 from the wire-entry face; height 14.10.
KF128_FOOTPRINT_NAME = "TerminalBlock_KF128-5.08_1x02_P5.08mm"
KF128_PITCH_MM = 5.08
KF128_DRILL_MM = 1.40
KF128_PAD_DIAMETER_MM = 2.60
KF128_BODY_DEPTH_MM = 10.70
KF128_PIN_TO_ENTRY_FACE_MM = 5.40
KF128_COURTYARD_MARGIN_MM = 0.25

# Jingdao SMF series (SOD-123FL), "The recommended mounting pad size":
# two 1.2 x 1.2 pads with a 2.0 gap, so 3.2 between centres. Body D is
# 2.6-2.9 long and E is 1.7-1.9 wide.
SOD123FL_FOOTPRINT_NAME = "D_SOD-123FL_1.2x1.2mm_P3.2mm"
SOD123FL_PAD_SIZE_MM = (1.20, 1.20)
SOD123FL_PAD_PITCH_MM = 3.20
SOD123FL_BODY_MM = (2.90, 1.90)
SOD123FL_COURTYARD_MARGIN_MM = 0.25

# JinRui JK-mSMD series, "Recommended pad layout": two 1.78 x 3.20 pads with
# a 3.20 gap. Body A is 4.37-4.73 long and B is 3.07-3.41 wide, from the
# JK-mSMD200 dimension table. The name says PTC because that is what the part
# is, and because the resettable-fuse symbol will only accept a land pattern
# that says so.
PTC_FOOTPRINT_NAME = "PTC_1812_Jinrui_JK-mSMD"
PTC_PAD_SIZE_MM = (1.78, 3.20)
PTC_PAD_GAP_MM = 3.20
PTC_BODY_MM = (4.73, 3.41)
PTC_COURTYARD_MARGIN_MM = 0.25

# 2510 wire-to-board specification PB131 version 17, right-angle header: pins
# are 0.62 square on 2.54 centres, the moulding is 10.16 long for four
# circuits, it stands 2.00 off the board and reaches 3.40 in front of and
# 2.40 behind the pin row. The drawing states no recommended land pattern, so
# the hole and the annulus below are this board's choice: 1.00 clears the
# 0.877 diagonal of the pin, and the annulus is the same 0.4 ring the other
# through-hole parts on this board use.
FAN_FOOTPRINT_NAME = "FanHeader_2510_1x04_P2.54mm_Horizontal"
FAN_PITCH_MM = 2.54
FAN_DRILL_MM = 1.00
FAN_PAD_DIAMETER_MM = 1.80
FAN_BODY_LENGTH_MM = 10.16
FAN_PIN_TO_FRONT_FACE_MM = 3.40
FAN_PIN_TO_BACK_FACE_MM = 2.40
FAN_COURTYARD_MARGIN_MM = 0.25
FAN_POSITIONS = 4


def _effects():
    return ("\n\t\t\t\t(effects\n\t\t\t\t\t(font\n"
            "\t\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t\t)\n\t\t\t\t)")


def _symbol_property(key, value, index, hide):
    hidden = "\n\t\t\t(hide yes)" if hide else ""
    return ('\t\t(property "%s" "%s"\n\t\t\t(at 0 %.2f 0)%s\n'
            '\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n'
            '\t\t\t\t)\n\t\t\t)\n\t\t)\n'
            % (key, value, 17.78 - 2.54 * index, hidden))


def _pin_text(kind, x, y, angle, name, number):
    return ('\t\t\t(pin %s line\n\t\t\t\t(at %.2f %.2f %d)\n'
            '\t\t\t\t(length 2.54)\n'
            '\t\t\t\t(name "%s"%s\n\t\t\t\t)\n'
            '\t\t\t\t(number "%s"%s\n\t\t\t\t)\n\t\t\t)'
            % (kind, x, y, angle, name, _effects(), number, _effects()))


def _rectangle(half_x, half_y):
    return ['\t\t\t(rectangle',
            '\t\t\t\t(start %.2f %.2f)' % (-half_x, half_y),
            '\t\t\t\t(end %.2f %.2f)' % (half_x, -half_y),
            '\t\t\t\t(stroke\n\t\t\t\t\t(width 0.254)\n'
            '\t\t\t\t\t(type default)\n\t\t\t\t)',
            '\t\t\t\t(fill\n\t\t\t\t\t(type background)\n\t\t\t\t)',
            '\t\t\t)']


def _boxed_symbol(name, reference_prefix, value, footprint, datasheet,
                  placed_pins, half_x, half_y, footprint_filter=None,
                  exclude_from_sim="no"):
    """A rectangle with pins on declared sides, one pin per package terminal."""
    lines = ['\t(symbol "%s"' % name,
             '\t\t(pin_names\n\t\t\t(offset 1.016)\n\t\t)',
             '\t\t(exclude_from_sim %s)' % exclude_from_sim,
             '\t\t(in_bom yes)',
             '\t\t(on_board yes)',
             _symbol_property("Reference", reference_prefix, 0,
                              False).rstrip("\n"),
             _symbol_property("Value", value, 1, False).rstrip("\n"),
             _symbol_property("Footprint", footprint, 2, True).rstrip("\n"),
             _symbol_property("Datasheet", datasheet, 3, True).rstrip("\n")]
    if footprint_filter is not None:
        lines.append(_symbol_property("ki_fp_filters", footprint_filter, 4,
                                      True).rstrip("\n"))
    lines.append('\t\t(symbol "%s_0_1"' % name)
    lines.extend(_rectangle(half_x, half_y))
    lines.append('\t\t)')
    lines.append('\t\t(symbol "%s_1_1"' % name)
    for number, pin_name, kind, side in placed_pins:
        lines.append(_placed_pin(number, pin_name, kind, side, placed_pins,
                                 half_x, half_y))
    lines.append('\t\t)')
    lines.append('\t)')
    return "\n".join(lines)


def _placed_pin(number, pin_name, kind, side, placed_pins, half_x, half_y):
    same_side = [entry for entry in placed_pins if entry[3] == side]
    index = same_side.index((number, pin_name, kind, side))
    span = 2.54 * (len(same_side) - 1) / 2.0
    if side == "left":
        return _pin_text(kind, -half_x - 2.54, span - 2.54 * index, 0,
                         pin_name, number)
    if side == "right":
        return _pin_text(kind, half_x + 2.54, span - 2.54 * index, 180,
                         pin_name, number)
    if side == "bottom":
        return _pin_text(kind, 2.54 * index - span, -half_y - 2.54, 90,
                         pin_name, number)
    return _pin_text(kind, 2.54 * index - span, half_y + 2.54, 270,
                     pin_name, number)


def ldo_symbol_text():
    placed = [(number, name, kind, side)
              for number, name, kind, side in LDO_PINS]
    return _boxed_symbol(
        LDO_SYMBOL_NAME, "U", LDO_SYMBOL_NAME, "Package_TO_SOT_SMD:SOT-89-3",
        LDO_DATASHEET, placed, 5.08, 3.81, footprint_filter="SOT?89*")


def pfet_symbol_text():
    placed = [(number, "S", "passive", "left") for number in PFET_SOURCE_PINS]
    placed.append((PFET_GATE_PIN, "G", "input", "bottom"))
    placed.extend((number, "D", "passive", "right")
                  for number in PFET_DRAIN_PINS)
    return _boxed_symbol(
        PFET_SYMBOL_NAME, "Q", PFET_SYMBOL_NAME,
        "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", PFET_DATASHEET, placed,
        5.08, 6.35, footprint_filter="SOIC*3.9x4.9mm*P1.27mm*")


def fan_header_symbol_text():
    placed = [(number, name, "passive", "left")
              for number, name in FAN_SYMBOL_PINS]
    return _boxed_symbol(
        FAN_SYMBOL_NAME, "J", FAN_SYMBOL_NAME,
        "%s:%s" % (LIBRARY_NAME, FAN_FOOTPRINT_NAME), "", placed, 2.54, 5.08,
        footprint_filter="FanHeader*", exclude_from_sim="yes")


def tvs_symbol_text():
    return "\n".join([
        '\t(symbol "%s"' % TVS_SYMBOL_NAME,
        '\t\t(pin_numbers\n\t\t\t(hide yes)\n\t\t)',
        '\t\t(pin_names\n\t\t\t(offset 1.016)\n\t\t\t(hide yes)\n\t\t)',
        '\t\t(exclude_from_sim no)',
        '\t\t(in_bom yes)',
        '\t\t(on_board yes)',
        _symbol_property("Reference", "D", 0, False).rstrip("\n"),
        _symbol_property("Value", TVS_SYMBOL_NAME, 1, False).rstrip("\n"),
        _symbol_property("Footprint", "%s:%s" % (LIBRARY_NAME,
                                                 X1SON_FOOTPRINT_NAME),
                         2, True).rstrip("\n"),
        _symbol_property("Datasheet", TVS_DATASHEET, 3, True).rstrip("\n"),
        _symbol_property("ki_fp_filters", X1SON_FOOTPRINT_NAME, 4,
                         True).rstrip("\n"),
        '\t\t(symbol "%s_0_1"' % TVS_SYMBOL_NAME,
        '\t\t\t(rectangle',
        '\t\t\t\t(start -1.27 1.27)',
        '\t\t\t\t(end 1.27 -1.27)',
        '\t\t\t\t(stroke\n\t\t\t\t\t(width 0.254)\n'
        '\t\t\t\t\t(type default)\n\t\t\t\t)',
        '\t\t\t\t(fill\n\t\t\t\t\t(type background)\n\t\t\t\t)',
        '\t\t\t)',
        '\t\t)',
        '\t\t(symbol "%s_1_1"' % TVS_SYMBOL_NAME,
        _pin_text("passive", 0.0, -3.81, 90, "A1", "1"),
        _pin_text("passive", 0.0, 3.81, 270, "A2", "2"),
        '\t\t)',
        '\t)',
    ])


def terminal_symbol_text(name, pin_names):
    half = 2.54 * (len(pin_names) - 1) / 2.0
    lines = ['\t(symbol "%s"' % name,
             '\t\t(pin_names\n\t\t\t(offset 1.016)\n\t\t)',
             '\t\t(exclude_from_sim yes)',
             '\t\t(in_bom yes)',
             '\t\t(on_board yes)',
             _symbol_property("Reference", "J", 0, False).rstrip("\n"),
             _symbol_property("Value", name, 1, False).rstrip("\n"),
             _symbol_property("Footprint", "", 2, True).rstrip("\n"),
             _symbol_property("Datasheet", "", 3, True).rstrip("\n"),
             _symbol_property("ki_fp_filters", TERMINAL_FOOTPRINT_FILTER, 4,
                              True).rstrip("\n"),
             '\t\t(symbol "%s_0_1"' % name]
    lines.extend(_rectangle(2.54, half + 2.54))
    lines.append('\t\t)')
    lines.append('\t\t(symbol "%s_1_1"' % name)
    for index, pin_name in enumerate(pin_names):
        y = half - 2.54 * index
        lines.append(_pin_text("passive", -5.08, y, 0, pin_name,
                               str(index + 1)))
    lines.append('\t\t)')
    lines.append('\t)')
    return "\n".join(lines)


def symbol_library_text():
    body = [ldo_symbol_text(), pfet_symbol_text(), fan_header_symbol_text(),
            tvs_symbol_text()]
    for name in sorted(TERMINAL_SYMBOLS):
        body.append(terminal_symbol_text(name, TERMINAL_SYMBOLS[name]))
    return "\n".join([
        '(kicad_symbol_lib',
        '\t(version %s)' % SYMBOL_LIB_VERSION,
        '\t(generator "%s")' % GENERATOR,
        '\t(generator_version "10.0")',
    ] + body + [')']) + "\n"


def _outline(layer, half_x, half_y, thickness, start_y=None, end_y=None):
    top = half_y if start_y is None else start_y
    bottom = -half_y if end_y is None else end_y
    return ('\t(fp_rect\n\t\t(start %.3f %.3f)\n\t\t(end %.3f %.3f)\n'
            '\t\t(stroke\n\t\t\t(width %.2f)\n\t\t\t(type default)\n\t\t)\n'
            '\t\t(fill none)\n\t\t(layer "%s")\n\t)'
            % (-half_x, top, half_x, bottom, thickness, layer))


def _footprint_header(name, descr, tags, attr, ref_y, value_y, size,
                      thickness, uid):
    return [
        '(footprint "%s"' % name,
        '\t(version %s)' % FOOTPRINT_VERSION,
        '\t(generator "%s")' % GENERATOR,
        '\t(generator_version "10.0")',
        '\t(layer "F.Cu")',
        '\t(descr "%s")' % descr,
        '\t(tags "%s")' % tags,
        '\t(attr %s)' % attr,
        '\t(property "Reference" "REF**"\n\t\t(at 0 %.2f 0)\n'
        '\t\t(layer "F.SilkS")\n\t\t(uuid "00000000-0000-0000-0000-'
        '0000000000%02d")\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size %.1f %.1f)'
        '\n\t\t\t\t(thickness %.2f)\n\t\t\t)\n\t\t)\n\t)'
        % (ref_y, uid, size, size, thickness),
        '\t(property "Value" "%s"\n\t\t(at 0 %.2f 0)\n'
        '\t\t(layer "F.Fab")\n\t\t(uuid "00000000-0000-0000-0000-'
        '0000000000%02d")\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size %.1f %.1f)'
        '\n\t\t\t\t(thickness %.2f)\n\t\t\t)\n\t\t)\n\t)'
        % (name, value_y, uid + 1, size, size, thickness),
    ]


def x1son_footprint_text():
    width, height = X1SON_PAD_SIZE_MM
    offset = X1SON_PAD_PITCH_MM / 2.0
    body_x, body_y = (value / 2.0 for value in X1SON_BODY_MM)
    court_x = body_x + X1SON_COURTYARD_MARGIN_MM
    court_y = body_y + X1SON_COURTYARD_MARGIN_MM
    pads = []
    for number, sign in (("1", -1.0), ("2", 1.0)):
        pads.append(
            '\t(pad "%s" smd roundrect\n\t\t(at %.3f 0)\n'
            '\t\t(size %.3f %.3f)\n\t\t(layers "F.Cu" "F.Paste" "F.Mask")\n'
            '\t\t(roundrect_rratio 0.1667)\n\t)'
            % (number, sign * offset, width, height))
    outline = [_outline("F.CrtYd", court_x, court_y, 0.05),
               _outline("F.Fab", body_x, body_y, 0.1)]
    return "\n".join(_footprint_header(
        X1SON_FOOTPRINT_NAME,
        "TI DPY0002A land pattern, SLLSEB1G drawing 4224561/C",
        "X1SON DPY TVS", "smd", -1.2, 1.2, 0.6, 0.1, 1)
        + outline + pads + [')']) + "\n"


def sod123fl_footprint_text():
    width, height = SOD123FL_PAD_SIZE_MM
    offset = SOD123FL_PAD_PITCH_MM / 2.0
    body_x, body_y = (value / 2.0 for value in SOD123FL_BODY_MM)
    court_x = offset + width / 2.0 + SOD123FL_COURTYARD_MARGIN_MM
    court_y = body_y + SOD123FL_COURTYARD_MARGIN_MM
    pads = []
    for number, sign in (("1", -1.0), ("2", 1.0)):
        pads.append(
            '\t(pad "%s" smd roundrect\n\t\t(at %.3f 0)\n'
            '\t\t(size %.3f %.3f)\n\t\t(layers "F.Cu" "F.Paste" "F.Mask")\n'
            '\t\t(roundrect_rratio 0.25)\n\t)'
            % (number, sign * offset, width, height))
    marker = (
        '\t(fp_line\n\t\t(start %.3f %.3f)\n\t\t(end %.3f %.3f)\n'
        '\t\t(stroke\n\t\t\t(width 0.12)\n\t\t\t(type default)\n\t\t)\n'
        '\t\t(layer "F.SilkS")\n\t)'
        % (-court_x, -court_y, -court_x, court_y))
    outline = [_outline("F.CrtYd", court_x, court_y, 0.05),
               _outline("F.Fab", body_x, body_y, 0.1)]
    return "\n".join(_footprint_header(
        SOD123FL_FOOTPRINT_NAME,
        "SOD-123FL land pattern, Jingdao SMF series recommended mounting pad",
        "SOD-123FL TVS diode", "smd", -1.8, 1.8, 0.8, 0.12, 21)
        + outline + [marker] + pads + [')']) + "\n"


def ptc_footprint_text():
    width, height = PTC_PAD_SIZE_MM
    offset = (PTC_PAD_GAP_MM + width) / 2.0
    body_x, body_y = (value / 2.0 for value in PTC_BODY_MM)
    court_x = offset + width / 2.0 + PTC_COURTYARD_MARGIN_MM
    court_y = max(height / 2.0, body_y) + PTC_COURTYARD_MARGIN_MM
    pads = []
    for number, sign in (("1", -1.0), ("2", 1.0)):
        pads.append(
            '\t(pad "%s" smd roundrect\n\t\t(at %.3f 0)\n'
            '\t\t(size %.3f %.3f)\n\t\t(layers "F.Cu" "F.Paste" "F.Mask")\n'
            '\t\t(roundrect_rratio 0.25)\n\t)'
            % (number, sign * offset, width, height))
    outline = [_outline("F.CrtYd", court_x, court_y, 0.05),
               _outline("F.Fab", body_x, body_y, 0.1)]
    return "\n".join(_footprint_header(
        PTC_FOOTPRINT_NAME,
        "JinRui JK-mSMD 1812 resettable fuse, recommended pad layout "
        "from the JK-mSMD series specification",
        "PTC polyfuse resettable fuse 1812", "smd", -2.4, 2.4, 0.8, 0.12, 41)
        + outline + pads + [')']) + "\n"


def kf128_footprint_text():
    """Land pattern for the 12 V input terminal.

    The drawing dimensions the hole diameter and the pitch, so those are
    datasheet values; the annulus is this board's choice. The body is drawn
    with the wire-entry face toward -Y, which is how the layout places it so
    that field wiring leaves the board rather than crossing it.
    """
    half_pitch = KF128_PITCH_MM / 2.0
    front = -KF128_PIN_TO_ENTRY_FACE_MM
    back = KF128_BODY_DEPTH_MM - KF128_PIN_TO_ENTRY_FACE_MM
    half_width = KF128_PITCH_MM  # (P x 5.08) overall for two poles
    margin = KF128_COURTYARD_MARGIN_MM
    pads = []
    for number, sign in (("1", -1.0), ("2", 1.0)):
        pads.append(
            '\t(pad "%s" thru_hole %s\n\t\t(at %.3f 0)\n'
            '\t\t(size %.3f %.3f)\n\t\t(drill %.3f)\n'
            '\t\t(layers "*.Cu" "*.Mask")\n\t)'
            % (number, "rect" if number == "1" else "circle",
               sign * half_pitch, KF128_PAD_DIAMETER_MM,
               KF128_PAD_DIAMETER_MM, KF128_DRILL_MM))
    outline = [
        _outline("F.CrtYd", half_width + margin, 0, 0.05,
                 start_y=back + margin, end_y=front - margin),
        _outline("F.Fab", half_width, 0, 0.1, start_y=back, end_y=front),
    ]
    return "\n".join(_footprint_header(
        KF128_FOOTPRINT_NAME,
        "Cixi Kefa KF128-5.08 2-pole screw terminal, PCB layout from drawing "
        "KF128-5.08 rev A",
        "terminal block screw 5.08mm", "through_hole",
        front - 1.2, back + 1.2, 1.0, 0.15, 11)
        + outline + pads + [')']) + "\n"


def fan_header_footprint_text():
    """Land pattern for one fan connector.

    Pin 1 is square so the pin-1 end is identifiable on the assembled board,
    which is what makes the standard pin order checkable by inspection.
    """
    span = FAN_PITCH_MM * (FAN_POSITIONS - 1)
    front = -FAN_PIN_TO_FRONT_FACE_MM
    back = FAN_PIN_TO_BACK_FACE_MM
    half_body = FAN_BODY_LENGTH_MM / 2.0
    margin = FAN_COURTYARD_MARGIN_MM
    pads = []
    for index in range(FAN_POSITIONS):
        number = str(index + 1)
        pads.append(
            '\t(pad "%s" thru_hole %s\n\t\t(at %.3f 0)\n'
            '\t\t(size %.3f %.3f)\n\t\t(drill %.3f)\n'
            '\t\t(layers "*.Cu" "*.Mask")\n\t)'
            % (number, "rect" if index == 0 else "circle",
               FAN_PITCH_MM * index - span / 2.0,
               FAN_PAD_DIAMETER_MM, FAN_PAD_DIAMETER_MM, FAN_DRILL_MM))
    outline = [
        _outline("F.CrtYd", half_body + margin, 0, 0.05,
                 start_y=back + margin, end_y=front - margin),
        _outline("F.Fab", half_body, 0, 0.1, start_y=back, end_y=front),
    ]
    return "\n".join(_footprint_header(
        FAN_FOOTPRINT_NAME,
        "2510 right-angle 4-circuit header, body from specification PB131 "
        "version 17; hole and annulus chosen by this board",
        "fan header 2510 2.54mm right angle", "through_hole",
        front - 1.2, back + 1.2, 1.0, 0.15, 31)
        + outline + pads + [')']) + "\n"


def sym_lib_table_text():
    return ('(sym_lib_table\n\t(version 7)\n'
            '\t(lib (name "%s")(type "KiCad")'
            '(uri "${KIPRJMOD}/library/%s.kicad_sym")(options "")(descr ""))\n)\n'
            % (LIBRARY_NAME, LIBRARY_NAME))


def fp_lib_table_text():
    return ('(fp_lib_table\n\t(version 7)\n'
            '\t(lib (name "%s")(type "KiCad")'
            '(uri "${KIPRJMOD}/library/%s.pretty")(options "")(descr ""))\n)\n'
            % (LIBRARY_NAME, LIBRARY_NAME))


def artifacts():
    return {
        SYMBOL_LIB_PATH: symbol_library_text(),
        os.path.join(FOOTPRINT_DIR, X1SON_FOOTPRINT_NAME + ".kicad_mod"):
            x1son_footprint_text(),
        os.path.join(FOOTPRINT_DIR, SOD123FL_FOOTPRINT_NAME + ".kicad_mod"):
            sod123fl_footprint_text(),
        os.path.join(FOOTPRINT_DIR, PTC_FOOTPRINT_NAME + ".kicad_mod"):
            ptc_footprint_text(),
        os.path.join(FOOTPRINT_DIR, KF128_FOOTPRINT_NAME + ".kicad_mod"):
            kf128_footprint_text(),
        os.path.join(FOOTPRINT_DIR, FAN_FOOTPRINT_NAME + ".kicad_mod"):
            fan_header_footprint_text(),
        SYM_LIB_TABLE: sym_lib_table_text(),
        FP_LIB_TABLE: fp_lib_table_text(),
    }


def write():
    os.makedirs(FOOTPRINT_DIR, exist_ok=True)
    written = []
    for path, text in artifacts().items():
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        written.append(path)
    return sorted(written)


if __name__ == "__main__":
    for path in write():
        sys.stdout.write(path + "\n")
