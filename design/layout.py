"""The board: outline, placement, pours and silkscreen, from the design source.

Board coordinates run x right and y UP from the lower-left corner, which is
the frame every dimension in this module is stated in. KiCad's own y runs
down, so the mapping is applied once, here.

The arrangement follows the current rather than the schematic. Field wiring
enters at the bottom-left corner and the four fan connectors sit along the
same edge, so the supply path is short and the return path is shorter. Each
channel's power parts stand directly above its own connector, in one column
that no other channel's copper crosses. The controller and everything
referenced to the signal ground sit above all four columns, and the two
ground systems meet at one component that straddles the line between them.
"""
from __future__ import annotations

import json
import math
import os
import sys

from . import ksym, netlist

_TOOLKIT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tooling", "PCBA_AutoDesignAndTest")
if _TOOLKIT not in sys.path:
    sys.path.insert(0, _TOOLKIT)

from pcbqa import headless  # noqa: E402

headless.suppress_blocking_ui()

import pcbnew  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOARD_PATH = os.path.join(REPO_ROOT, netlist.PROJECT_NAME + ".kicad_pcb")
PLACEMENT_PATH = os.path.join(REPO_ROOT, "constraints", "placement.json")

FOOTPRINT_SEARCH_PATHS = (
    os.path.join(REPO_ROOT, "library"),
    "/usr/share/kicad/footprints",
)

ORIGIN_MM = (30.0, 100.0)

BOARD_W_MM = 104.0
BOARD_H_MM = 66.0

#: Fan connector centres. The pitch is set by a hand, not by the copper: a
#: plug is 10.16 wide and has to be gripped and pulled while its neighbours
#: keep running, so the gap between adjacent bodies is what the pitch is for.
CHANNEL_CENTRES_MM = (34.0, 52.0, 70.0, 88.0)
FAN_HEADER_Y_MM = 5.0

#: The supply terminal shares the connector edge so the input current and the
#: fan return never leave the bottom of the board.
INPUT_TERMINAL_MM = (14.0, 10.0)

#: The protected rail. The conductor is the generated track at RAIL_TRACK_Y;
#: the pour over the same band is copper the fill can add where it fits, and
#: is allowed to lose islands, because a fill that a router cuts into pieces
#: is not what the channels are fed through. The rectangle that feeds it from
#: the blocking device is a pour, because the whole board's current passes
#: through it.
POWER_BUS_Y_MM = (31.5, 35.0)
RAIL_TRACK_Y_MM = 34.0
RAIL_TRACK_WIDTH_MM = 1.5
INPUT_POUR_MM = (10.0, 8.0, 13.0, 27.0)
FEEDER_POUR_MM = (3.0, 22.0, 7.0, 35.0)

#: Where the power return stops and the signal reference starts. The gap is
#: bridged by one component and nothing else.
#: The gap is as narrow as the clearance rule allows and the link's own pads
#: require: each pad has to overlap the pour it bonds to, and stand clear of
#: the one it must not.
GROUND_SPLIT_Y_MM = 36.3
GROUND_SPLIT_GAP_MM = 0.6

#: A clear vertical lane on the far side of every channel column. The
#: channel's own supply runs down it, generated rather than searched: it is
#: the only conductor the whole channel current passes through, and the layer
#: a router would take it to is the one the fan return pours on.
CHANNEL_LANE_DX_MM = 7.5
CHANNEL_LANE_RETURN_Y_MM = 2.5

#: Channel rows, bottom-up: fan-facing test points, the interface passives,
#: the clamps, the drivers, the gate network, and the power path.
CHANNEL_ROWS_MM = {
    "probe": 10.2,
    "interface": 13.0,
    "clamp": 16.5,
    "driver": 20.0,
    "gate": 24.5,
    "power": 30.0,
}

EDGE_WIDTH_MM = 0.1
TRACK_WIDTH_MM = 0.25
#: Width of the generated per-channel supply and of the taps onto the rail.
#: Sized for one channel's rating, not for the board's: the rail conductor
#: carries all four and is wider.
POWER_TRACK_WIDTH_MM = 0.6
CLEARANCE_MM = 0.15
EDGE_CLEARANCE_MM = 0.3
VIA_DIAMETER_MM = 0.6
VIA_DRILL_MM = 0.3
ZONE_INSET_MM = 0.5
STITCH_TRACK_WIDTH_MM = 0.4
STITCH_GAP_MM = 0.35

MOUNTING_HOLES_MM = {
    "H1": (4.0, 4.0),
    "H2": (101.0, 4.0),
    "H3": (4.0, 62.0),
    "H4": (101.0, 62.0),
}

#: Parts a placement search may not move, and why.
#:
#: The connectors and the fasteners are the board's mechanical contract. The
#: test points are the board's service contract. The resettable fuses stand in
#: the supply band because that is where they meet the pour that feeds them.
#: The link between the two ground systems is the one component whose position
#: IS the topology it creates.
LOCKED_PREFIXES = ("J", "H", "TP", "F")
LOCKED_REFERENCES = tuple(sorted(
    [reference for reference in netlist.PARTS
     if reference[0] in ("J", "H", "F") and reference[1:].isdigit()]
    + [reference for reference in netlist.PARTS
       if reference.startswith("TP")]
    + [netlist.GROUND_STAR_REFERENCE]))


def _channel_seed(channel, centre):
    """Every part of one channel, as offsets from its connector centre.

    The offsets are set by the courtyards, not by taste: a 0603 land is 3.06
    wide including its courtyard, so the passive rows step by 3.3, and a row
    steps by the tallest courtyard standing in it.
    """
    rows = CHANNEL_ROWS_MM
    return {
        # power path: the pour feeds the fuse, the fuse feeds the switch,
        # the switch feeds the connector, and the clamp sits across the
        # connector's own supply pin
        "F%d" % channel: (centre - 6.0, rows["power"] + 1.0, 270.0),
        "Q%d" % (channel + 1): (centre - 1.0, rows["power"], 0.0),
        "D%d" % (channel + 1): (centre + 3.0, rows["power"], 90.0),
        # gate network for the high-side switch and its enable
        "R%d" % (channel + 1): (centre - 6.6, rows["gate"], 0.0),
        "R%d" % (channel + 5): (centre - 3.3, rows["gate"], 0.0),
        "Q%d" % (channel + 5): (centre + 0.5, rows["gate"], 0.0),
        "R%d" % (channel + 9): (centre + 4.0, rows["gate"], 0.0),
        # the control driver and the channel's sense divider
        "R%d" % (channel + 17): (centre - 6.6, rows["driver"], 0.0),
        "R%d" % (channel + 13): (centre - 3.3, rows["driver"], 0.0),
        "Q%d" % (channel + 9): (centre + 0.5, rows["driver"], 0.0),
        "R%d" % (channel + 37): (centre + 4.0, rows["driver"], 0.0),
        # the clamps that face the connector. The sense clamp and the sense
        # filter are not here: they belong at the receiver, and the receiver
        # is referenced to the other ground.
        "D%d" % (channel + 10): (centre - 3.0, rows["clamp"], 0.0),
        "D%d" % (channel + 14): (centre + 3.0, rows["clamp"], 0.0),
        # the interface passives, and the sense divider's upper leg
        "R%d" % (channel + 21): (centre - 6.0, rows["interface"], 0.0),
        "R%d" % (channel + 25): (centre - 3.0, rows["interface"], 0.0),
        "R%d" % (channel + 29): (centre, rows["interface"], 0.0),
        "R%d" % (channel + 33): (centre + 3.0, rows["interface"], 180.0),
        # probes on the two nets that leave for the fan
        "TP%d" % (channel + 4): (centre - 5.0, rows["probe"], 0.0),
        "TP%d" % (channel + 8): (centre + 5.0, rows["probe"], 0.0),
        # the connector itself
        "J%d" % (channel + 1): (centre, FAN_HEADER_Y_MM, 0.0),
    }


#: The supply path and the logic island, left to right along one row, then
#: the controller and the two host-facing headers.
SHARED_PLACEMENT = {
    # below the ground split: everything whose return current is fan current
    "J1": INPUT_TERMINAL_MM + (0.0,),
    "Q1": (8.0, 24.0, 0.0),
    "R1": (8.0, 29.0, 0.0),
    "TP1": (5.0, RAIL_TRACK_Y_MM, 0.0),
    "C1": (16.0, 30.0, 0.0),
    "D1": (16.0, 24.0, 0.0),
    "C2": (23.0, 30.0, 270.0),
    "TP4": (43.0, 8.0, 0.0),
    # the one link between the two ground systems, straddling the gap
    "R45": (49.0, GROUND_SPLIT_Y_MM, 270.0),
    # above it: the reservoir, the regulator and everything it feeds
    "D6": (8.0, 39.5, 270.0),
    "C3": (8.0, 48.0, 0.0),
    "C4": (15.0, 48.0, 0.0),
    "U2": (20.0, 48.0, 0.0),
    "C5": (25.0, 48.0, 0.0),
    "C6": (29.0, 48.0, 0.0),
    "R44": (32.5, 48.0, 0.0),
    "D24": (36.0, 48.0, 0.0),
    "TP2": (24.0, 43.0, 0.0),
    "TP3": (28.0, 43.0, 0.0),
    "R42": (42.0, 35.6, 90.0),
    "R43": (42.0, 39.5, 0.0),
    "U1": (58.0, 46.0, 0.0),
    "C7": (51.0, 48.0, 90.0),
    "C8": (51.0, 44.0, 90.0),
    # the sense filters and their clamps, at the receiver rather than at the
    # connector: both return to the signal ground, and the signal ground does
    # not reach the connector edge
    "C9": (44.0, 54.0, 0.0),
    "C10": (48.0, 54.0, 0.0),
    "C11": (52.0, 54.0, 0.0),
    "C12": (56.0, 54.0, 0.0),
    "D7": (43.0, 57.5, 0.0),
    "D8": (48.5, 57.5, 0.0),
    "D9": (54.0, 57.5, 0.0),
    "D10": (59.5, 57.5, 0.0),
    # A vertical pin header puts pad 1 at its origin and the rest below it,
    # so each header is placed by its first pin and its series elements sit
    # on the row of the pin they belong to.
    "J7": (72.0, 60.0, 0.0),
    "R48": (68.0, 54.92, 0.0),
    "R49": (68.0, 52.38, 0.0),
    "D21": (65.0, 54.92, 0.0),
    "D22": (65.0, 52.38, 0.0),
    "D23": (65.0, 49.84, 0.0),
    "J6": (80.0, 60.0, 0.0),
    "R46": (84.0, 57.46, 0.0),
    "R47": (84.0, 54.92, 0.0),
    "D19": (87.5, 57.46, 0.0),
    "D20": (87.5, 54.92, 0.0),
}


def to_board(x_mm, y_mm):
    return (ORIGIN_MM[0] + x_mm, ORIGIN_MM[1] - y_mm)


def _point(x_mm, y_mm):
    bx, by = to_board(x_mm, y_mm)
    return pcbnew.VECTOR2I(pcbnew.FromMM(bx), pcbnew.FromMM(by))


def accepted_placement():
    """The placement a search accepted, if one has been recorded.

    Absent, the seed below is the placement. Present, it replaces the seed
    for every part that is not locked - a locked part is locked in the board
    file and the search cannot have moved it, so accepting one from this file
    would be accepting a value that never came from a search.
    """
    if not os.path.isfile(PLACEMENT_PATH):
        return {}
    with open(PLACEMENT_PATH, encoding="utf-8") as handle:
        document = json.load(handle)
    return {reference: tuple(pose)
            for reference, pose in document["placement"].items()
            if reference not in LOCKED_REFERENCES}


def seed_placement():
    placed = dict(SHARED_PLACEMENT)
    for reference, (x, y) in MOUNTING_HOLES_MM.items():
        placed[reference] = (x, y, 0.0)
    for index, centre in enumerate(CHANNEL_CENTRES_MM):
        placed.update(_channel_seed(index + 1, centre))
    return placed


def fixed_placements():
    placed = seed_placement()
    for reference, pose in accepted_placement().items():
        if reference not in placed:
            raise KeyError("accepted placement names an unknown part: "
                           + reference)
        placed[reference] = pose
    missing = sorted(reference for reference, part in netlist.PARTS.items()
                     if part["footprint"] and reference not in placed)
    if missing:
        raise KeyError("no placement for " + ", ".join(missing))
    return placed


def _footprint_dir(footprint):
    library, _, name = footprint.partition(":")
    for base in FOOTPRINT_SEARCH_PATHS:
        candidate = os.path.join(base, library + ".pretty")
        if os.path.isfile(os.path.join(candidate, name + ".kicad_mod")):
            return candidate, name
    raise FileNotFoundError(footprint)


_PIN_NAMES = {}


def _pin_name(lib_id, number):
    if lib_id not in _PIN_NAMES:
        library = ksym.Library(netlist.SYMBOL_LIBRARY_PATHS)
        _PIN_NAMES[lib_id] = {
            key: pins[0].name for key, pins in library.pins(lib_id).items()}
    return _PIN_NAMES[lib_id].get(number, "")


def _floating_net(board, reference, number):
    lib_id = netlist.PARTS[reference]["lib_id"]
    name = "unconnected-(%s-%s-Pad%s)" % (
        reference, _pin_name(lib_id, number).replace("/", "{slash}"), number)
    existing = board.GetNetInfo().GetNetItem(name)
    if existing is not None and existing.GetNetCode() != 0:
        return existing
    net = pcbnew.NETINFO_ITEM(board, name)
    board.Add(net)
    return net


def _load(board, reference, part, x, y, rotation, pin_net, nets):
    library_dir, name = _footprint_dir(part["footprint"])
    footprint = pcbnew.FootprintLoad(library_dir, name)
    if footprint is None:
        raise RuntimeError("could not load " + part["footprint"])
    library = part["footprint"].partition(":")[0]
    footprint.SetFPID(pcbnew.LIB_ID(library, name))
    footprint.SetPosition(_point(x, y))
    footprint.SetOrientationDegrees(rotation)
    footprint.SetReference(reference)
    footprint.SetValue(part["value"])
    footprint.Reference().SetLayer(pcbnew.F_Fab)
    footprint.Value().SetLayer(pcbnew.F_Fab)
    for key, value in (("MPN", part["mpn"]), ("LCSC", part["lcsc"]),
                       ("Manufacturer", part["manufacturer"])):
        if not value:
            continue
        footprint.SetField(key, value)
        for field in footprint.GetFields():
            if field.GetName() == key:
                field.SetLayer(pcbnew.F_Fab)
                field.SetVisible(False)
    if not part["in_bom"]:
        footprint.SetExcludedFromBOM(True)
    if reference in LOCKED_REFERENCES:
        footprint.SetLocked(True)
    for pad in footprint.Pads():
        number = pad.GetNumber()
        if not number:
            continue
        net_name = pin_net.get("%s.%s" % (reference, number))
        if net_name:
            pad.SetNet(nets[net_name])
        else:
            pad.SetNet(_floating_net(board, reference, number))
    board.Add(footprint)
    return footprint


def _nets(board):
    created = {}
    for name in sorted(netlist.NETS):
        net = pcbnew.NETINFO_ITEM(board, name)
        board.Add(net)
        created[name] = net
    return created


def _design_settings(board):
    board.SetCopperLayerCount(2)
    settings = board.GetDesignSettings()
    settings.m_TrackMinWidth = pcbnew.FromMM(0.15)
    settings.m_ViasMinSize = pcbnew.FromMM(0.45)
    settings.m_MinThroughDrill = pcbnew.FromMM(0.25)
    settings.m_CopperEdgeClearance = pcbnew.FromMM(EDGE_CLEARANCE_MM)
    settings.m_HoleClearance = pcbnew.FromMM(0.25)
    settings.m_HoleToHoleMin = pcbnew.FromMM(0.25)
    settings.m_ViasMinAnnularWidth = pcbnew.FromMM(0.1)
    settings.m_MinClearance = pcbnew.FromMM(CLEARANCE_MM)
    default_class = settings.m_NetSettings.GetDefaultNetclass()
    default_class.SetClearance(pcbnew.FromMM(CLEARANCE_MM))
    default_class.SetTrackWidth(pcbnew.FromMM(TRACK_WIDTH_MM))
    default_class.SetViaDiameter(pcbnew.FromMM(VIA_DIAMETER_MM))
    default_class.SetViaDrill(pcbnew.FromMM(VIA_DRILL_MM))


def _add_outline(board):
    corners = [(0.0, 0.0), (BOARD_W_MM, 0.0), (BOARD_W_MM, BOARD_H_MM),
               (0.0, BOARD_H_MM)]
    closed = corners + [corners[0]]
    for start, end in zip(closed, closed[1:]):
        shape = pcbnew.PCB_SHAPE(board)
        shape.SetShape(pcbnew.SHAPE_T_SEGMENT)
        shape.SetStart(_point(*start))
        shape.SetEnd(_point(*end))
        shape.SetLayer(pcbnew.Edge_Cuts)
        shape.SetWidth(pcbnew.FromMM(EDGE_WIDTH_MM))
        board.Add(shape)


def _rectangle_zone(board, corners, layers):
    zone = pcbnew.ZONE(board)
    layer_set = pcbnew.LSET()
    for layer in layers:
        layer_set.addLayer(layer)
    zone.SetLayerSet(layer_set)
    outline = zone.Outline()
    outline.NewOutline()
    for x, y in corners:
        bx, by = to_board(x, y)
        outline.Append(pcbnew.FromMM(bx), pcbnew.FromMM(by))
    return zone


def _pour(board, net, corners, layers, priority=0):
    zone = _rectangle_zone(board, corners, layers)
    zone.SetNet(net)
    zone.SetAssignedPriority(priority)
    zone.SetLocalClearance(pcbnew.FromMM(CLEARANCE_MM))
    zone.SetMinThickness(pcbnew.FromMM(0.2))
    zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    zone.SetThermalReliefGap(pcbnew.FromMM(0.3))
    zone.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.4))
    board.Add(zone)
    return zone


def ground_bands_mm():
    """The two ground pours, as the y bands they occupy.

    The power return covers the connector edge and every channel column; the
    signal reference covers the controller island. Neither reaches the other,
    and the gap between them is where the link stands.
    """
    half_gap = GROUND_SPLIT_GAP_MM / 2.0
    return {
        netlist.POWER_GROUND_NET: (ZONE_INSET_MM,
                                   GROUND_SPLIT_Y_MM - half_gap),
        netlist.SIGNAL_GROUND_NET: (GROUND_SPLIT_Y_MM + half_gap,
                                    BOARD_H_MM - ZONE_INSET_MM),
    }


def protected_rail_outline():
    """The protected rail as one polygon: a spine with one leg down to the
    blocking device. One zone rather than two, because two that touch are two
    zones a design rule has to reason about.
    """
    low, high = POWER_BUS_Y_MM
    right = CHANNEL_CENTRES_MM[-1] + 9.0
    x0, y0, x1, _ = FEEDER_POUR_MM
    return [(x0, y0), (x1, y0), (x1, low), (right, low), (right, high),
            (x0, high)]


def _add_pours(board, nets):
    for name, (low, high) in ground_bands_mm().items():
        _pour(board, nets[name],
              [(ZONE_INSET_MM, low), (BOARD_W_MM - ZONE_INSET_MM, low),
               (BOARD_W_MM - ZONE_INSET_MM, high), (ZONE_INSET_MM, high)],
              (pcbnew.B_Cu,))
    x0, y0, x1, y1 = INPUT_POUR_MM
    _pour(board, nets["V12IN"],
          [(x0, y0), (x1, y0), (x1, y1), (x0, y1)],
          (pcbnew.F_Cu,), priority=1)
    rail = _pour(board, nets["V12P"], protected_rail_outline(),
                 (pcbnew.F_Cu,), priority=1)
    rail.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)


def _add_track(board, start, end, layer, net, width_mm):
    track = pcbnew.PCB_TRACK(board)
    track.SetStart(start)
    track.SetEnd(end)
    track.SetLayer(layer)
    track.SetNet(net)
    track.SetWidth(pcbnew.FromMM(width_mm))
    board.Add(track)
    return track


def _add_via(board, position, net):
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(position)
    via.SetWidth(pcbnew.F_Cu, pcbnew.FromMM(VIA_DIAMETER_MM))
    via.SetDrill(pcbnew.FromMM(VIA_DRILL_MM))
    via.SetNet(net)
    via.SetViaType(pcbnew.VIATYPE_THROUGH)
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    board.Add(via)
    return via


def _obstacles(board):
    """Every pad and via, as a centre and a radius the stitch must clear."""
    found = []
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            size = pad.GetSize()
            found.append((pad.GetPosition(),
                          max(size.x, size.y) / 2.0, pad.GetNetCode()))
    for item in board.GetTracks():
        if item.Type() == pcbnew.PCB_VIA_T:
            found.append((item.GetPosition(),
                          item.GetWidth(pcbnew.F_Cu) / 2.0,
                          item.GetNetCode()))
    return found


def _stitch(board, footprint, pad, net, band):
    """Drop a via just outside a surface pad and bond it to its pour.

    The direction is searched rather than assumed: on a board where a passive
    row steps by little more than its own courtyard, the obvious direction is
    often occupied, and a via that lands on a neighbour's mask opening is a
    bridge, not a connection.
    """
    position = pad.GetPosition()
    size = pad.GetSize()
    angle = math.radians(footprint.GetOrientationDegrees())
    along = (math.cos(angle), math.sin(angle))
    across = (-math.sin(angle), math.cos(angle))
    half_along = pcbnew.ToMM(size.x) / 2.0
    half_across = pcbnew.ToMM(size.y) / 2.0
    keep_out = pcbnew.FromMM(VIA_DIAMETER_MM / 2.0 + CLEARANCE_MM)
    obstacles = _obstacles(board)
    low, high = band
    candidates = []
    for axis, half in ((across, half_across), (along, half_along)):
        reach = half + VIA_DIAMETER_MM / 2.0 + STITCH_GAP_MM
        for sign in (1.0, -1.0):
            for extra in (0.0, 0.6, 1.2):
                candidates.append((axis[0] * sign * (reach + extra),
                                   axis[1] * sign * (reach + extra)))
    for dx, dy in candidates:
        centre = pcbnew.VECTOR2I(int(position.x + pcbnew.FromMM(dx)),
                                 int(position.y + pcbnew.FromMM(dy)))
        y_mm = ORIGIN_MM[1] - pcbnew.ToMM(centre.y)
        if not low + VIA_DIAMETER_MM / 2.0 <= y_mm <= high - VIA_DIAMETER_MM / 2.0:
            continue
        clear = True
        for point, radius, net_code in obstacles:
            if net_code == net.GetNetCode():
                continue
            distance = math.hypot(centre.x - point.x, centre.y - point.y)
            if distance < radius + keep_out:
                clear = False
                break
        if not clear:
            continue
        _add_via(board, centre, net)
        _add_track(board, position, centre, pcbnew.F_Cu, net,
                   STITCH_TRACK_WIDTH_MM)
        return centre
    raise RuntimeError(
        "no clear stitch position for %s pad %s"
        % (footprint.GetReference(), pad.GetNumber()))


def _stitch_grounds(board, footprints, nets):
    """Every surface pad on a ground reaches its pour through its own via.

    The two grounds are pours on the back layer, so a pad that exists only on
    the front is not on them until something takes it there. Doing it here
    rather than leaving it to the router keeps which ground a pad joins a
    property of the pad's net, not of a search.
    """
    bands = ground_bands_mm()
    for reference, footprint in sorted(footprints.items()):
        for pad in footprint.Pads():
            name = pad.GetNetname()
            if name not in bands:
                continue
            if pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                continue
            _stitch(board, footprint, pad, nets[name], bands[name])


#: Pads on the protected rail that no pour reaches, and the y each one is
#: taken to. Each is a short vertical drop onto the rail's own pour, which is
#: the only copper on this board whose route is not a search result.
#: Pads on the protected rail that the rail conductor does not itself pass
#: through, and the pad each one is taken from. Every one is a straight climb
#: with nothing of another net between it and the rail.
RAIL_TAPS = (("D1", "1"), ("C2", "1"), ("D6", "2"))


def _route_rail(board, footprints, nets):
    """The protected rail as copper, not as fill.

    One track along the band through every fuse's supply pad, and one climb
    from each pad the track does not pass through. A pour can be cut into
    islands by a router; a track cannot, because the router routes around
    copper that is already there.
    """
    # The rail runs from the probe that carries it to the last channel's
    # fuse, so neither end is a track end standing on nothing: the probe sits
    # on the rail's own line, which is why it is placed where it is.
    left = SHARED_PLACEMENT["TP1"][0]
    right = CHANNEL_CENTRES_MM[-1] - 6.0
    _add_track(board, _point(left, RAIL_TRACK_Y_MM),
               _point(right, RAIL_TRACK_Y_MM), pcbnew.F_Cu, nets["V12P"],
               RAIL_TRACK_WIDTH_MM)
    for index, centre in enumerate(CHANNEL_CENTRES_MM):
        _route_channel_supply(board, footprints, nets, index + 1, centre)
    for reference, number in RAIL_TAPS:
        footprint = footprints[reference]
        pad = next(p for p in footprint.Pads() if p.GetNumber() == number)
        start = pad.GetPosition()
        end = pcbnew.VECTOR2I(
            start.x, pcbnew.FromMM(ORIGIN_MM[1] - RAIL_TRACK_Y_MM))
        _add_track(board, start, end, pcbnew.F_Cu, nets["V12P"],
                   POWER_TRACK_WIDTH_MM)


def _route_channel_supply(board, footprints, nets, channel, centre):
    """One channel's supply, from its switch to its own connector pin.

    Down the lane and along below the connector, so the two signals that
    leave the same connector cross nothing on their way up. Generated rather
    than routed, because the requirement is the topology - one layer, no via
    - and a search has no freedom left inside it.
    """
    net = nets["FAN%d_12V" % channel]
    switch = footprints["Q%d" % (channel + 1)]
    connector = footprints["J%d" % (channel + 1)]
    drain = next(pad for pad in switch.Pads() if pad.GetNumber() == "3")
    supply = next(pad for pad in connector.Pads()
                  if pad.GetNumber() == str(netlist.FAN_CONNECTOR_PINS["12V"]))
    lane_x = centre + CHANNEL_LANE_DX_MM
    start = drain.GetPosition()
    end = supply.GetPosition()
    corner_y = pcbnew.FromMM(ORIGIN_MM[1] - CHANNEL_LANE_RETURN_Y_MM)
    lane = pcbnew.VECTOR2I(pcbnew.FromMM(ORIGIN_MM[0] + lane_x), start.y)
    points = [start, lane,
              pcbnew.VECTOR2I(lane.x, corner_y),
              pcbnew.VECTOR2I(end.x, corner_y), end]
    for first, second in zip(points, points[1:]):
        _add_track(board, first, second, pcbnew.F_Cu, net,
                   POWER_TRACK_WIDTH_MM)
    # The clamp across the connector's supply pin and the upper leg of the
    # sense divider are on the same net; each reaches the lane straight out
    # to the side, which is why the divider faces the way it does.
    for reference, number in (("D%d" % (channel + 1), "1"),
                              ("R%d" % (channel + 33), "1")):
        pad = next(p for p in footprints[reference].Pads()
                   if p.GetNumber() == number)
        at = pad.GetPosition()
        _add_track(board, at, pcbnew.VECTOR2I(lane.x, at.y), pcbnew.F_Cu,
                   net, POWER_TRACK_WIDTH_MM)


def fill_zones(board):
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    return board


def build(with_copper=True):
    """The board.

    `with_copper=False` produces the same placement with no pours: the
    placement search refuses a board that already carries copper, because
    moving a footprint would leave its copper behind. Everything conductive
    is generated from the accepted poses afterwards, so the two forms cannot
    disagree about where a part is.
    """
    board = pcbnew.CreateEmptyBoard()
    _design_settings(board)
    nets = _nets(board)
    pin_net = netlist.pin_to_net()

    footprints = {}
    placed = fixed_placements()
    for reference, (x, y, rotation) in sorted(placed.items()):
        part = netlist.PARTS[reference]
        if not part["footprint"]:
            continue
        footprints[reference] = _load(
            board, reference, part, x, y, rotation, pin_net, nets)

    _add_outline(board)
    if with_copper:
        _add_pours(board, nets)
        _stitch_grounds(board, footprints, nets)
        _route_rail(board, footprints, nets)
    _add_silkscreen(board, footprints)
    return board, footprints


# ---------------------------------------------------------------------------
# silkscreen

SILK_LAYER = pcbnew.F_SilkS
SILK_TEXT_MM = 1.2
SILK_THICKNESS_MM = 0.2
CHANNEL_LABEL_Y_MM = 7.0
#: One letter per connector function, for the pin-order marking. The board is
#: marked with the order because a plug that mates the wrong way round is the
#: one mistake the connector itself cannot prevent.
FAN_PIN_MARKS = {"GND": "G", "12V": "V", "SENSE": "S", "CONTROL": "C"}
PIN_LABEL_OFFSET_MM = 2.2
RATING_Y_MM = 63.5
PROBE_LABEL_OFFSET_MM = -1.6


def _text(board, value, x, y, size_mm=SILK_TEXT_MM, layer=None):
    item = pcbnew.PCB_TEXT(board)
    item.SetText(value)
    item.SetPosition(_point(x, y))
    item.SetLayer(SILK_LAYER if layer is None else layer)
    item.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(size_mm),
                                     pcbnew.FromMM(size_mm)))
    item.SetTextThickness(pcbnew.FromMM(SILK_THICKNESS_MM))
    item.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
    item.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
    board.Add(item)
    return item


def rating_text():
    """What the board is marked with, from what it claims, not from taste."""
    return "12V IN %.1f-%.1fV  %.1fA/CH  %dCH" % (
        netlist.INPUT_SUPPLY["min_v"], netlist.INPUT_SUPPLY["max_v"],
        netlist.CHANNEL_CURRENT_RATING_A, netlist.CHANNEL_COUNT)


def probe_labels():
    """Which probe carries which net, from the netlist rather than a list."""
    pin_net = netlist.pin_to_net()
    return {reference: pin_net["%s.1" % reference]
            for reference in netlist.PARTS if reference.startswith("TP")}


def _add_silkscreen(board, footprints):
    _text(board, rating_text(), BOARD_W_MM / 2.0, RATING_Y_MM)
    assert set(FAN_PIN_MARKS) == set(netlist.FAN_CONNECTOR_PINS)
    order = " ".join(
        "%d%s" % (pin, FAN_PIN_MARKS[function])
        for function, pin in sorted(netlist.FAN_CONNECTOR_PINS.items(),
                                    key=lambda item: item[1]))
    for index, centre in enumerate(CHANNEL_CENTRES_MM):
        _text(board, "FAN%d %s" % (index + 1, order), centre,
              CHANNEL_LABEL_Y_MM, size_mm=0.9)
    placed = fixed_placements()
    for reference, net in sorted(probe_labels().items()):
        x, y, _ = placed[reference]
        _text(board, net, x, y + PROBE_LABEL_OFFSET_MM, size_mm=0.8)
    for reference, label, dx, dy in (("J1", "12V IN", 0.0, -4.6),
                                     ("J6", "HOST", 3.0, 1.8),
                                     ("J7", "SWD", -3.5, 1.8)):
        x, y, _ = placed[reference]
        _text(board, label, x + dx, y + dy, size_mm=1.0)


def write(path=None):
    """Write the board, then rewrite the project it belongs to.

    Saving a board rewrites the project file beside it with KiCad's own
    defaults, which is how five rule severities this board declares as
    warnings became ignores. The project is therefore regenerated from the
    design source afterwards, every time, rather than left as whatever the
    save left behind.
    """
    from . import build as _build
    board, _ = build()
    fill_zones(board)
    target = BOARD_PATH if path is None else path
    pcbnew.SaveBoard(target, board)
    if path is None:
        _build.write_project()
    return target


def write_placement_board(path):
    board, _ = build(with_copper=False)
    pcbnew.SaveBoard(path, board)
    return path


if __name__ == "__main__":
    sys.stdout.write(write() + "\n")
