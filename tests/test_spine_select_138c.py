"""GW5AST-138C spine select ports hold VSS (TinyTang core-log entry 94)."""

import types

from apycula import chipdb


def _select_wires():
    dev = types.SimpleNamespace(rows=110)
    chipdb.fse_create_spine_select_wires(dev, 'GW5AST-138C')
    return dev.spine_select_wires


def test_spine19_select_is_the_vendor_vss_tie():
    # Gowin IDE 1.9.11.03 drives exactly these ports from VSS for SPINE19.
    wires = _select_wires()
    assert wires['top']['SPINE19'] == [(27, 94, 'CLK0', 0), (27, 94, 'CLK1', 0)]
    assert wires['bottom']['SPINE19'] == [(81, 94, 'CLK0', 0), (81, 94, 'CLK1', 0)]


def test_no_select_port_asks_for_vcc():
    # A CLK port has no VCC row in the .fse, so a 1 here routes to a fuseless
    # pip and leaves the port unprogrammed.
    for half in _select_wires().values():
        for ports in half.values():
            assert all(vcc_gnd == 0 for *_, vcc_gnd in ports)
