"""What changes when the GW5AST-138C's DDR3 PHY runs on real signals.

Every earlier DDR3 measurement tied the serializers' `RESET` low and clocked
the `DDRDLL` from the global network.  The PHY bring-up (TinyVCMI
`fpga/ddr3_phy_bringup`) drives `RESET` from logic and clocks the DLL from
the memory clock's HCLK lane, as the hardware-proven controller does, and
Gowin EDA 1.9.11.03 configures both differently (MEASURED 2026-10-24):

* a serializer on a routed `RESET` has no reset multiplexer on its own half,
  so the table's absence fuse is set;
* a `DDRDLL` whose clock also drives a `CLKDIV` at `LEFTSIDE[4+n]` takes it
  from HCLK block-2 lane n, `DLL0` features 21 and `4-n`, in place of feature
  5, which is `CLKIN` from the port tile's `CLK0`.

The reset tests need no chipdb; the DLL tests read the built database.
"""
import os

import pytest

from apycula import chipdb, gowin_pack

DEVICE = "GW5AST-138C"
GND, SIGNAL = 2, 77


class _Pnr:
    def is_constant_net(self, wire):
        return wire == GND


class _Device(gowin_pack.GW5AST_138C):
    def __init__(self):
        self.pnr = _Pnr()


def _bel(typ, reset):
    cell = gowin_pack.CellDesc(name='ser', typ=typ, parms={}, attrs={},
                               connections={'RESET': [reset]} if reset else {})
    return gowin_pack.BelDesc(0, 77, 'A', cell)


def _lsr(attr_vals):
    return {av.attr: av.val for av in attr_vals}


@pytest.mark.parametrize("reset", [GND, None])
def test_a_constant_reset_keeps_both_multiplexers_at_zero(reset):
    for mux in ('LSROMUX_0', 'LSRIMUX_0'):
        assert _lsr(_Device()._lsr_attrs(_bel('OSER8_MEM', reset), mux)) == \
            {'LSRIMUX_0': '0', 'LSROMUX_0': '0'}


def test_a_routed_reset_drops_the_output_multiplexer_of_an_output():
    assert _lsr(_Device()._lsr_attrs(_bel('OSER8_MEM', SIGNAL), 'LSROMUX_0')) == \
        {'LSRIMUX_0': '0'}


def test_a_routed_reset_drops_the_input_multiplexer_of_an_input():
    assert _lsr(_Device()._lsr_attrs(_bel('IDES8_MEM', SIGNAL), 'LSRIMUX_0')) == \
        {'LSROMUX_0': '0'}


@pytest.fixture(scope="module")
def real_db():
    path = os.path.join(os.path.dirname(chipdb.__file__), f"{DEVICE}.msgpack.xz")
    if not os.path.exists(path):
        pytest.skip(f"{DEVICE}.msgpack.xz absent; run apycula.chipdb_builder")
    return chipdb.load_chipdb(path)


class _Dll(gowin_pack.GW5AST_138C):
    def __init__(self, db, src, context=True):
        class _ChipDB:
            pass
        self.chipdb = _ChipDB()
        self.chipdb.db = db
        self.chipdb.rows = len(db.grid)
        self.chipdb.get_ttyp = lambda x, y: db.grid[y][x]
        self.ddr_context = context
        self._ddrdll_clkin_src = src


def _dll_bel(db):
    cell = gowin_pack.CellDesc(name='dll', typ='DDRDLL', attrs={}, connections={},
                               parms={'CODESCAL': '111', 'SCAL_EN': 'FALSE',
                                      'DIV_SEL': '0', 'DLL_FORCE': 'FALSE'})
    return gowin_pack.BelDesc(1, len(db.grid) - 1, 'DDRDLL', cell)


def _features(db, src, context=True):
    dev = _Dll(db, src, context)
    (fuses,) = dev.get_DDRDLL_fuses(_dll_bel(db))
    table = db.shortval[db.grid[len(db.grid) - 1][0]]['DLL0']
    bits = set(fuses.bits)
    return {k[0] for k, v in table.items()
            if len(k) == 2 and k[1] == 0 and v and set(v) <= bits}


@pytest.mark.parametrize("src", ['CLK0', None])
def test_a_dll_on_clk0_takes_feature_5(real_db, src):
    feats = _features(real_db, src)
    assert {5, 12, 17, 18, 19} <= feats
    assert not feats & {1, 2, 3, 4, 21}


@pytest.mark.parametrize("lane", [0, 1, 2, 3])
def test_a_dll_on_an_hclk_lane_takes_feature_21_and_its_lane(real_db, lane):
    feats = _features(real_db, f'HCLK2{lane}')
    assert {21, 4 - lane, 12, 17, 18, 19} <= feats
    assert 5 not in feats
    assert not feats & ({1, 2, 3, 4} - {4 - lane})


def test_a_dll_clock_from_anywhere_else_is_refused(real_db):
    with pytest.raises(gowin_pack.PackRefused, match="neither CLK0 nor"):
        _features(real_db, 'HCLK00')


def test_outside_a_context_the_lane_is_still_written(real_db):
    feats = _features(real_db, 'HCLK20', context=False)
    assert {21, 4} <= feats
    assert 5 not in feats
