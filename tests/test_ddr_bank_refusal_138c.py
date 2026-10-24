"""No design outside a DDR context configures a bank 6/7 pad (`D20c`, `D54`).

Banks 6 and 7 of the GW5AST-138C are the DDR3 banks.  PR #423's class of
defect -- a pull or drive configuration written onto an unfused bank -- is a
live thermal hazard there, so the rule has to hold at every layer that can
reach a pad, and it has to be about the **ball**: keying it on `IO_TYPE`
admits `SSTL15`, which is precisely the standard DDR3 uses.
"""
import pytest

from apycula import chipdb, gowin_pack


def _io_bel(x, y, idx='A'):
    cell = gowin_pack.CellDesc(name='dq', typ='IOBUF', parms={}, attrs={},
                               connections={})
    return gowin_pack.IoBelDesc(x, y, idx, cell)


class _Device(gowin_pack.GW5AST_138C):
    """The packer's DDR-bank rule alone, with no chipdb load behind it."""

    class _ChipDB:
        db = object()

    def __init__(self, bank):
        self._bank = bank
        self.banked = []
        self.chipdb = self._ChipDB()

    def get_bel_bank(self, bel):
        return self._bank

    def add_io_to_bank_base(self, bel):
        self.banked.append(bel)


@pytest.fixture(autouse=True)
def _named_pad(monkeypatch):
    monkeypatch.setattr(chipdb, 'loc2pin_name', lambda db, row, col: 'IOR55')
    monkeypatch.setattr(gowin_pack.Device, 'add_io_to_bank',
                        _Device.add_io_to_bank_base, raising=True)


@pytest.mark.parametrize('bank', [6, 7])
def test_a_pad_on_a_ddr_bank_is_refused_by_name(bank):
    dev = _Device(bank)
    with pytest.raises(gowin_pack.PackRefused) as excinfo:
        dev.add_io_to_bank(_io_bel(184, 55))
    message = str(excinfo.value)
    assert f'bank {bank}' in message
    assert 'IOR55A' in message
    assert dev.banked == []


def test_the_refusal_does_not_depend_on_the_io_standard():
    """The cell carries no `IO_TYPE` at all and is still refused."""
    dev = _Device(6)
    bel = _io_bel(184, 55)
    assert 'IO_TYPE' not in bel.cell.attrs
    with pytest.raises(gowin_pack.PackRefused):
        dev.add_io_to_bank(bel)


@pytest.mark.parametrize('bank', [0, 1, 2, 3, 4, 5])
def test_a_pad_on_every_other_bank_still_packs(bank):
    dev = _Device(bank)
    dev.add_io_to_bank(_io_bel(52, 108))
    assert len(dev.banked) == 1


def test_a_declared_ddr_context_lifts_the_refusal_for_a_manifest_ball():
    """Phase 5b owns these banks and says so with a ball manifest
    (`--ddr3-context`); nothing in Phase 3 sets it.  The rules a declared
    ball must then meet are in `test_ddr3_context_138c.py`."""
    assert gowin_pack.GW5AST_138C.ddr_context is False
    dev = _Device(6)
    dev.ddr_context = True
    dev.ddr3_balls = {'IOR55A': {'pin': 'X1', 'site': 'IOR55A', 'bank': 6,
                                 'io_type': 'SSTL15'}}
    dev.ddr3_settings = {'BANK_VCCIO': '1.5', 'PULL_MODE': 'NONE', 'DRIVE': '8'}
    cell = gowin_pack.CellDesc(name='dq', typ='IOBUF', parms={},
                               attrs={'IO_TYPE': 'SSTL15', 'BANK_VCCIO': '1.5',
                                      'PULLMODE': 'NONE', 'DRIVE': '8'},
                               connections={})
    dev.add_io_to_bank(gowin_pack.IoBelDesc(184, 55, 'A', cell, {'IS_OUTPUT': 1}))
    assert len(dev.banked) == 1


def test_a_declared_ddr_context_without_a_manifest_is_refused():
    dev = _Device(6)
    dev.ddr_context = True
    with pytest.raises(gowin_pack.PackRefused, match="no ball manifest"):
        dev.add_io_to_bank(_io_bel(184, 55))
    assert dev.banked == []