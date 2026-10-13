"""Every `AE350_SOC` bus port carries the vendor's own port timing.

The vendor `.tm` has no group for the hard SoC, so without one nextpnr treats
the block's ports as untimed, and a bus path to the block may then cross the
die without the router knowing that it must arrive within the bus clock. The
`ae350` group comes from `apycula/ae350_138c_timing.py`: setup, hold and
clock-to-out measured from the Gowin 1.9.11.03 timing report for the block on
a GW5AST-LV138PG484AC1/I0, one figure per bus port, applied to every bit.

These tests hold the group against the block's own port map: every ROM, DDR
and EXTS bus bit the chipdb exposes is timed, every pin an arc names exists
on the block, and every arc is clocked by one of the block's bus clocks.
"""

from pathlib import Path

import pytest

from apycula import chipdb as chipdb_mod
from apycula.ae350_138c_timing import ae350_timing_group

DEVICE = "GW5AST-138C"
ANCHOR = (0, 159)
BUS_PREFIXES = ("ROM_H", "DDR_H", "EXTS_H")
BUS_CLOCKS = {"AHB_CLK", "APB_CLK", "DDR_CLK"}


@pytest.fixture(scope="module")
def db():
    path = Path(__file__).resolve().parent.parent / "apycula" / f"{DEVICE}.msgpack.xz"
    if not path.is_file():
        pytest.skip(f"{path} is absent; run `make apycula/{DEVICE}.msgpack.xz`")
    return chipdb_mod.load_chipdb(str(path))


def split(group):
    return [(name.split(":"), value) for name, value in group.items()]


def test_group_is_in_every_speed_grade(db):
    for speed, groups in db.timing.items():
        assert groups.get("ae350") == ae350_timing_group(), speed


def test_every_bus_bit_is_timed(db):
    block = db.extra_func[ANCHOR]["ae350"]
    group = ae350_timing_group()
    ins = {b for (kind, _, b), _ in split(group) if kind == "setup_hold"}
    outs = {b for (kind, _, b), _ in split(group) if kind == "clock_out"}
    assert ins == {p for p in block["ins"] if p.startswith(BUS_PREFIXES)}
    assert outs == {p for p in block["outs"] if p.startswith(BUS_PREFIXES)}


def test_arcs_name_real_pins_and_bus_clocks(db):
    block = db.extra_func[ANCHOR]["ae350"]
    for (kind, a, b), value in split(ae350_timing_group()):
        assert len(value) == 2, (kind, a, b)
        if kind == "comb":
            assert a in block["ins"] and b in block["outs"], (a, b)
            assert 0 <= value[0] <= value[1]
        else:
            assert kind in ("setup_hold", "clock_out"), kind
            assert a in BUS_CLOCKS and a in block["ins"], (kind, a, b)
            assert b in (block["ins"] if kind == "setup_hold" else block["outs"])
            if kind == "clock_out":
                assert 0 < value[0] <= value[1], (a, b, value)
