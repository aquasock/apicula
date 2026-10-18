"""The vendor clock-mux tables vs. what the GW5AST-138C model keeps.

TinyTang's clock inventory (2026-10-18) found that `fse_clock_pips_138()`
keeps only part of the vendor's central clock-mux tables: tile 80 keeps 807
pips over 18 destinations from 1672 `CLOCK_MUX` rows, tile 85 keeps 775 of
1259, and whole longwire (164-236) and unknown-wire (105-128) ranges are
dropped.  This test pins that delta for the 1.9.11.03 vendor data, so a later
change that un-filters or replaces an arc must update the numbers here
deliberately rather than by accident.

The golden counts are the inventory's; the vendor file is the fixture's.  The
test is skipped when no Gowin install/vendor file is available, like the rest
of the device-data tests.
"""

import pytest

from apycula import chipdb as chipdb_mod
from apycula import fse_parser, wirenames as wnames

DEVICE = "GW5AST-138C"

# ttyp -> ({wire-table id: raw rows}, kept pips, kept destinations)
GOLDEN = {
    80: ({38: 1672, 91: 119}, 807, 18),
    81: ({38: 479, 91: 35}, 275, 5),
    82: ({38: 40}, 40, 17),
    83: ({}, 0, 0),
    84: ({38: 388, 90: 40, 91: 5}, 264, 6),
    85: ({38: 1259, 90: 136, 91: 18}, 775, 18),
}


@pytest.fixture
def fse(device_file):
    path = device_file(DEVICE, "fse")
    wnames.select_wires(DEVICE)
    with open(path, "rb") as f:
        return fse_parser.read_fse(f, DEVICE)


@pytest.mark.parametrize("ttyp", sorted(GOLDEN))
def test_clock_mux_raw_and_kept_counts(fse, ttyp):
    """The model's kept pips are a subset of the vendor table, with the pinned
    counts.  A change to either side moves these numbers."""
    tables, want_pips, want_dests = GOLDEN[ttyp]
    kept = chipdb_mod.fse_clock_pips_138(fse, ttyp, DEVICE)
    assert len(kept) == want_dests, (ttyp, sorted(kept))
    assert sum(len(v) for v in kept.values()) == want_pips

    raw = fse.get(ttyp, {}).get("wire", {})
    for table, want_rows in tables.items():
        assert len(raw.get(table, [])) == want_rows, (ttyp, table)

    # Every kept destination is a destination the vendor table actually has.
    raw_dests = {
        wnames.clknames.get(destid, f"UNK{destid}")
        for rows in raw.values()
        for srcid, destid in ((r[0], r[1]) for r in rows)
    }
    assert set(kept) <= raw_dests, (ttyp, sorted(set(kept) - raw_dests))
