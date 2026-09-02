from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from design import (build, cost, evidence, ksym, libraries,  # noqa: E402
                    netlist, rules)


class DesignSource(unittest.TestCase):
    def test_pin_assignment_is_unique(self):
        mapping = netlist.pin_to_net()
        self.assertEqual(len(mapping),
                         sum(len(pins) for pins in netlist.NETS.values()))

    def test_every_symbol_pin_is_connected_or_declared_no_connect(self):
        library = ksym.Library(netlist.SYMBOL_LIBRARY_PATHS)
        mapping = netlist.pin_to_net()
        declared = set(netlist.NO_CONNECT)
        unresolved = []
        for reference, part in netlist.PARTS.items():
            for number in library.pins(part["lib_id"]):
                pin_ref = "%s.%s" % (reference, number)
                if pin_ref not in mapping and pin_ref not in declared:
                    unresolved.append(pin_ref)
        self.assertEqual(unresolved, [])

    def test_declared_pins_exist_on_the_symbol(self):
        library = ksym.Library(netlist.SYMBOL_LIBRARY_PATHS)
        missing = []
        for pin_ref in list(netlist.pin_to_net()) + list(netlist.NO_CONNECT):
            reference, _, number = pin_ref.partition(".")
            lib_id = netlist.PARTS[reference]["lib_id"]
            if number not in library.pins(lib_id):
                missing.append(pin_ref)
        self.assertEqual(missing, [])

    def test_the_library_holds_nothing_the_design_source_does_not_write(self):
        produced = set(libraries.artifacts())
        present = set()
        for root, _, names in os.walk(libraries.FOOTPRINT_DIR):
            for name in names:
                present.add(os.path.join(root, name))
        present.add(libraries.SYMBOL_LIB_PATH)
        self.assertEqual(sorted(present - produced), [])

    def test_the_committed_design_files_are_the_generated_ones(self):
        with open(build.schematic_path(), "r", encoding="utf-8") as handle:
            self.assertEqual(handle.read(), build.generate_schematic_text())
        for path, text in libraries.artifacts().items():
            with open(path, "r", encoding="utf-8") as handle:
                self.assertEqual(handle.read(), text, path)


class ChannelTopology(unittest.TestCase):
    def setUp(self):
        self.mapping = netlist.pin_to_net()

    def test_every_channel_has_its_own_switch_driver_fuse_and_connector(self):
        for channel in range(1, netlist.CHANNEL_COUNT + 1):
            for prefix, offset in (("Q", 1), ("Q", 5), ("Q", 9), ("F", 0),
                                   ("J", 1)):
                reference = "%s%d" % (prefix, channel + offset)
                self.assertIn(reference, netlist.PARTS, reference)

    def test_a_channel_reaches_no_other_channel(self):
        for channel in range(1, netlist.CHANNEL_COUNT + 1):
            own = {"FAN%d_12V" % channel, "FAN%d_PWM" % channel,
                   "FAN%d_TACH" % channel, "CH%d_FUSED" % channel,
                   "CH%d_PG" % channel, "CH%d_GD" % channel,
                   "CH%d_EN" % channel, "CH%d_SENSE" % channel,
                   "PWM%d" % channel, "PWM%d_G" % channel,
                   "PWM%d_D" % channel, "TACH%d" % channel}
            references = {pin.split(".")[0] for net in own
                          for pin in netlist.NETS[net]}
            for other in range(1, netlist.CHANNEL_COUNT + 1):
                if other == channel:
                    continue
                foreign = {pin.split(".")[0]
                           for pin in netlist.NETS["FAN%d_12V" % other]}
                shared = references & foreign
                self.assertEqual(shared - {"J%d" % (other + 1)}, set())

    def test_the_fan_connectors_carry_the_standard_pin_order(self):
        for channel in range(1, netlist.CHANNEL_COUNT + 1):
            reference = "J%d" % (channel + 1)
            expected = {
                netlist.FAN_CONNECTOR_PINS["GND"]: netlist.POWER_GROUND_NET,
                netlist.FAN_CONNECTOR_PINS["12V"]: "FAN%d_12V" % channel,
                netlist.FAN_CONNECTOR_PINS["SENSE"]: "FAN%d_TACH" % channel,
                netlist.FAN_CONNECTOR_PINS["CONTROL"]: "FAN%d_PWM" % channel,
            }
            for pin, net in expected.items():
                self.assertEqual(
                    self.mapping["%s.%d" % (reference, pin)], net)

    def test_the_control_and_sense_pins_are_distinct_and_on_the_controller(self):
        for pins in (netlist.CHANNEL_PWM_PINS, netlist.CHANNEL_TACH_PINS,
                     netlist.CHANNEL_ENABLE_PINS, netlist.CHANNEL_SENSE_PINS):
            self.assertEqual(len(set(pins)), netlist.CHANNEL_COUNT)
        used = (set(netlist.CHANNEL_PWM_PINS)
                | set(netlist.CHANNEL_TACH_PINS)
                | set(netlist.CHANNEL_ENABLE_PINS)
                | set(netlist.CHANNEL_SENSE_PINS)
                | {netlist.RAIL_SENSE_PIN})
        self.assertEqual(len(used),
                         4 * netlist.CHANNEL_COUNT + 1)
        self.assertFalse(used & set(netlist.MCU_UNUSED_PINS))

    def test_each_control_and_sense_group_shares_one_timer(self):
        for functions in (netlist.CHANNEL_PWM_FUNCTIONS,
                          netlist.CHANNEL_TACH_FUNCTIONS):
            timers = {function.split("_")[0] for function in functions}
            self.assertEqual(len(timers), 1, functions)
            self.assertEqual(len(set(functions)), netlist.CHANNEL_COUNT)


class GroundTopology(unittest.TestCase):
    def test_the_two_ground_systems_meet_only_at_the_star_link(self):
        mapping = netlist.pin_to_net()
        both = {netlist.POWER_GROUND_NET, netlist.SIGNAL_GROUND_NET}
        for reference in netlist.PARTS:
            nets = {net for pin, net in mapping.items()
                    if pin.split(".")[0] == reference}
            if both <= nets:
                self.assertEqual(reference, netlist.GROUND_STAR_REFERENCE)

    def test_the_star_link_joins_exactly_the_two_ground_systems(self):
        mapping = netlist.pin_to_net()
        reference = netlist.GROUND_STAR_REFERENCE
        self.assertEqual(
            {mapping["%s.1" % reference], mapping["%s.2" % reference]},
            {netlist.POWER_GROUND_NET, netlist.SIGNAL_GROUND_NET})

    def test_every_fan_return_lands_on_the_power_ground(self):
        mapping = netlist.pin_to_net()
        for channel in range(1, netlist.CHANNEL_COUNT + 1):
            pin = "J%d.%d" % (channel + 1, netlist.FAN_CONNECTOR_PINS["GND"])
            self.assertEqual(mapping[pin], netlist.POWER_GROUND_NET)

    def test_the_controller_references_the_signal_ground(self):
        mapping = netlist.pin_to_net()
        self.assertEqual(mapping["U1.5"], netlist.SIGNAL_GROUND_NET)


class ControlInterface(unittest.TestCase):
    def test_no_resistive_pull_sits_on_a_control_trace(self):
        parameters = rules.load_parameters()
        for result in rules.evaluate_control_topology(parameters):
            self.assertEqual(result["claim"]["quantity"]["value"], 0.0)

    def test_the_control_driver_is_an_open_drain_device(self):
        for channel in range(1, netlist.CHANNEL_COUNT + 1):
            driver = netlist.PARTS["Q%d" % (channel + 9)]
            self.assertEqual(driver["mpn"], "AO3400A")
            mapping = netlist.pin_to_net()
            self.assertEqual(mapping["Q%d.2" % (channel + 9)],
                             netlist.SIGNAL_GROUND_NET)

    def test_the_declared_divider_reaches_the_standard_band(self):
        parameters = rules.load_parameters()
        results = {result["id"]: result
                   for result in rules.evaluate_control_timing(parameters)}
        low = results["control_frequency_above_the_standard_minimum"]
        high = results["control_frequency_below_the_standard_maximum"]
        self.assertGreaterEqual(low["measured_hz"],
                                netlist.PWM_FREQUENCY_BAND_HZ["min"])
        self.assertLessEqual(high["measured_hz"],
                             netlist.PWM_FREQUENCY_BAND_HZ["max"])


class Evidence(unittest.TestCase):
    def test_the_frozen_documents_are_intact_and_all_referenced(self):
        self.assertEqual(evidence.verify(), [])

    def test_the_committed_index_is_the_computed_one(self):
        self.assertEqual(evidence.load_index(), evidence.compute_index())

    def test_every_parameter_names_a_frozen_document(self):
        known = set(evidence.load_index()["documents"])
        unknown = set()

        def walk(node):
            if isinstance(node, dict):
                document = node.get("document")
                if isinstance(document, str) and document not in known:
                    unknown.add(document)
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        walk(rules.load_parameters()["parts"])
        self.assertEqual(sorted(unknown), [])

    def test_every_bom_part_has_frozen_parameters_and_a_catalogue_entry(self):
        parameters = rules.load_parameters()["parts"]
        catalog = rules.load_catalog()["parts"]
        for reference, part in netlist.PARTS.items():
            if not part["in_bom"]:
                continue
            self.assertIn(part["mpn"], parameters, reference)
            self.assertIn(part["lcsc"], catalog, reference)

    def test_the_catalogue_holds_no_part_the_board_does_not_use(self):
        used = {part["lcsc"] for part in netlist.PARTS.values()
                if part["in_bom"]}
        self.assertEqual(sorted(set(rules.load_catalog()["parts"]) - used), [])


class Requirements(unittest.TestCase):
    def setUp(self):
        self.results = rules.evaluate_all()

    def test_no_board_rule_fails(self):
        failed = sorted(result["id"] for result in self.results
                        if result["verdict"]["result"] == "FAIL")
        self.assertEqual(failed, [])

    def test_the_only_unresolved_claim_is_the_one_that_needs_a_fan_plug(self):
        unknown = sorted({result["id"] for result in self.results
                          if result["verdict"]["result"] == "UNKNOWN"})
        self.assertEqual(unknown, ["fan_connector_mates_a_standard_fan_plug"])

    def test_the_committed_requirement_evidence_is_current(self):
        with open(rules.REPORT_PATH, "r", encoding="utf-8") as handle:
            committed = json.load(handle)
        rules.write_report()
        with open(rules.REPORT_PATH, "r", encoding="utf-8") as handle:
            self.assertEqual(committed, json.load(handle))

    def test_every_probe_required_net_exists(self):
        for net in netlist.PROBE_REQUIRED_NETS:
            self.assertIn(net, netlist.NETS)

    def test_every_entering_conductor_is_clamped_or_exempt(self):
        parameters = rules.load_parameters()
        for result in rules.evaluate_esd_coverage(parameters):
            self.assertEqual(result["claim"]["quantity"]["value"], 0.0)

    def test_no_conductor_reaches_a_zero_injection_pin(self):
        parameters = rules.load_parameters()
        for result in rules.evaluate_injection_policy(parameters):
            self.assertEqual(result["claim"]["quantity"]["value"], 0.0)

    def test_the_contested_package_pins_carry_nothing(self):
        for pin in netlist.MCU_CONTESTED_PINS:
            self.assertIn("U1.%s" % pin, netlist.NO_CONNECT)


class Supply(unittest.TestCase):
    def test_stock_covers_the_planned_build(self):
        limits = cost.stock_limited_boards()
        self.assertGreaterEqual(min(limits.values()),
                                netlist.PLANNED_BUILD_QUANTITY)

    def test_every_bom_line_prices(self):
        report = cost.bom_cost(netlist.PLANNED_BUILD_QUANTITY)
        self.assertGreater(report["per_board_usd"], 0.0)
        self.assertEqual(len(report["lines"]), len(cost.line_items()))


class StaticVerification(unittest.TestCase):
    def test_the_schematic_passes_erc(self):
        report = os.path.join(REPO_ROOT, "out", "erc_test.json")
        os.makedirs(os.path.dirname(report), exist_ok=True)
        completed = subprocess.run(
            ["kicad-cli", "sch", "erc", "--output", report, "--format",
             "json", "--severity-error", "--severity-warning",
             "--exit-code-violations", build.schematic_path()],
            capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stdout)
        with open(report, "r", encoding="utf-8") as handle:
            document = json.load(handle)
        violations = [violation for sheet in document.get("sheets", [])
                      for violation in sheet.get("violations", [])]
        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
