"""The GW5AST-138C clock bridge keeps only the paths measured to clock.

TinyNES core-log entry 14 (the HDMI pixel clock from a RIGHTSIDE[4] CLKDIV,
HCLK escape wire 111, over 16 placement seeds and a Gowin IDE 1.9.11.03
build of the same clock decoded with gowin_unpack) found that flip-flops on
branches fed through `(27, 94) SPINE17 <= CBRIDGEOUT_BOTTOM0` or
`(27, 94) SPINE18 <= CBRIDGEOUT_BOTTOM2` never clock, that the clock entering
at `(54, 93) SPINE9` reaches nothing, and that entering at `(54, 88) SPINE18`
and leaving through `SPINE26 <= CBRIDGEOUT_BOTTOM2` clocks every flip-flop.
`SPINE25 <= CBRIDGEOUT_BOTTOM0` was on the silent AE350 route of core-log
entry 5. This file holds the chipdb to those measurements.
"""

from pathlib import Path

import pytest

from apycula import chipdb as chipdb_mod

DEVICE = "GW5AST-138C"
HCLK_WIRES = [f"UNK{n}" for n in range(105, 113)]
CENTRE = [(54, 88), (54, 93)]
DEAD = {
    (27, 94): [("SPINE17", "CBRIDGEOUT_BOTTOM0"), ("SPINE18", "CBRIDGEOUT_BOTTOM2")],
    (81, 94): [("SPINE17", "CBRIDGEOUT_BOTTOM0"), ("SPINE18", "CBRIDGEOUT_BOTTOM2")],
    (27, 96): [("SPINE25", "CBRIDGEOUT_BOTTOM0")],
    (81, 96): [("SPINE25", "CBRIDGEOUT_BOTTOM0")],
}
GOOD = {(27, 96): ("SPINE26", "CBRIDGEOUT_BOTTOM2"), (81, 96): ("SPINE26", "CBRIDGEOUT_BOTTOM2")}


@pytest.fixture(scope="module")
def db():
    path = Path(__file__).resolve().parent.parent / "apycula" / f"{DEVICE}.msgpack.xz"
    if not path.is_file():
        pytest.skip(f"{path} is absent; run `make apycula/{DEVICE}.msgpack.xz`")
    return chipdb_mod.load_chipdb(path)


def clock_pips(db, row, col):
    return db.tiles[db.grid[row][col]].clock_pips


@pytest.mark.parametrize("wire", HCLK_WIRES)
def test_hclk_wire_enters_only_at_bottom_spine18(db, wire):
    entries = sorted((rc, dest) for rc in CENTRE
                     for dest, srcs in clock_pips(db, *rc).items()
                     if dest.startswith("SPINE") and wire in srcs)
    assert entries == [((54, 88), "SPINE18")]


@pytest.mark.parametrize("cell", sorted(DEAD))
def test_dead_bridge_pips_absent(db, cell):
    pips = clock_pips(db, *cell)
    for dest, src in DEAD[cell]:
        assert src not in pips.get(dest, {}), f"{cell} {dest} <= {src}"


@pytest.mark.parametrize("cell", sorted(GOOD))
def test_measured_bridge_pip_present(db, cell):
    dest, src = GOOD[cell]
    assert src in clock_pips(db, *cell).get(dest, {})


def test_top_pll_still_enters_through_top(db):
    """Core-log entry 5's rule for PLL_R[0] CLKOUT0 is unchanged."""
    bottom = [d for d, s in clock_pips(db, 54, 88).items()
              if d.startswith("SPINE") and "TRPLL0CLK0" in s]
    top = [d for d, s in clock_pips(db, 54, 93).items()
           if d.startswith("SPINE") and "TRPLL0CLK0" in s]
    assert bottom == [] and top
