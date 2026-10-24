"""A declared DDR3 context admits only its manifest's balls, exactly as stated.

`gowin_pack --ddr3-context MANIFEST` is the one way a design may configure a
pad on the GW5AST-138C's DDR3 banks 6 and 7 (`D20c`, `D54`, PR #423).  The
manifest is a board fact -- which balls the board's DDR3 uses -- and the
packer holds every listed pad to the hardware-proven controller's
constraints (TinyVCMI TOOL-013): `SSTL15` on a single ball and `SSTL15D` on a
listed pair, `BANK_VCCIO=1.5`, `PULL_MODE=NONE`, `DRIVE=8` on an output and no
drive on an input, and no other IO attribute.  These tests pin each refusal.

The admission tests need no chipdb; the manifest-loading tests read the
built `apycula/GW5AST-138C.msgpack.xz` and skip without it.
"""
import json
import os

import pytest

from apycula import chipdb, gowin_pack

SETTINGS = {'BANK_VCCIO': '1.5', 'PULL_MODE': 'NONE', 'DRIVE': '8'}
GOOD = {'IO_TYPE': 'SSTL15', 'BANK_VCCIO': '1.5', 'PULLMODE': 'NONE', 'DRIVE': '8'}


class _Device(gowin_pack.GW5AST_138C):
    """The DDR3-context admission alone, with no chipdb load behind it."""

    class _ChipDB:
        db = object()

    def __init__(self, balls):
        self.banked = []
        self.chipdb = self._ChipDB()
        self.ddr_context = True
        self.ddr3_balls = balls
        self.ddr3_settings = dict(SETTINGS)

    def get_bel_bank(self, bel):
        return 6

    def add_io_to_bank_base(self, bel):
        self.banked.append(bel)


@pytest.fixture(autouse=True)
def _named_pad(monkeypatch):
    monkeypatch.setattr(chipdb, 'loc2pin_name', lambda db, row, col: 'IOL78')
    monkeypatch.setattr(gowin_pack.Device, 'add_io_to_bank',
                        _Device.add_io_to_bank_base, raising=True)


def _bel(attrs, idx='A', output=True, parms=None, typ='IOBUF'):
    cell = gowin_pack.CellDesc(name='pad', typ=typ, parms=parms or {}, attrs=attrs,
                               connections={})
    return gowin_pack.IoBelDesc(0, 77, idx, cell, {'IS_OUTPUT': 1} if output else {})


SINGLE = {'IOL78A': {'pin': 'Y4', 'site': 'IOL78A', 'bank': 6, 'io_type': 'SSTL15'}}
PAIR = {'IOL78A': {'pin': 'Y3', 'site': 'IOL78A', 'bank': 6, 'io_type': 'SSTL15D',
                   'half': 'P', 'pair': 'AA3'},
        'IOL78B': {'pin': 'AA3', 'site': 'IOL78B', 'bank': 6, 'io_type': 'SSTL15D',
                   'half': 'N', 'pair': 'Y3'}}


def test_a_listed_ball_at_the_proven_settings_is_admitted():
    dev = _Device(SINGLE)
    dev.add_io_to_bank(_bel(dict(GOOD)))
    assert len(dev.banked) == 1


def test_an_input_is_admitted_without_drive():
    dev = _Device(SINGLE)
    dev.add_io_to_bank(_bel({k: v for k, v in GOOD.items() if k != 'DRIVE'},
                            output=False, typ='IBUF'))
    assert len(dev.banked) == 1


@pytest.mark.parametrize('attrs, why', [
    (dict(GOOD, IO_TYPE='LVCMOS33'), 'LVCMOS33'),
    ({k: v for k, v in GOOD.items() if k != 'IO_TYPE'}, 'without an IO_TYPE'),
    (dict(GOOD, BANK_VCCIO='3.3'), 'admits exactly'),
    (dict(GOOD, PULLMODE='UP'), 'admits exactly'),
    (dict(GOOD, DRIVE='12'), 'admits exactly'),
    ({k: v for k, v in GOOD.items() if k != 'DRIVE'}, 'admits exactly'),
    (dict(GOOD, OPENDRAIN='ON'), 'OPENDRAIN'),
])
def test_anything_but_the_proven_settings_is_refused(attrs, why):
    dev = _Device(SINGLE)
    with pytest.raises(gowin_pack.PackRefused, match=why):
        dev.add_io_to_bank(_bel(attrs))
    assert dev.banked == []


def test_drive_on_an_input_is_refused():
    dev = _Device(SINGLE)
    with pytest.raises(gowin_pack.PackRefused, match='admits exactly'):
        dev.add_io_to_bank(_bel(dict(GOOD), output=False, typ='IBUF'))


def test_a_ball_the_manifest_does_not_list_is_refused():
    dev = _Device({'IOL80A': dict(SINGLE['IOL78A'], site='IOL80A')})
    with pytest.raises(gowin_pack.PackRefused, match='not a ball of the declared DDR3 manifest'):
        dev.add_io_to_bank(_bel(dict(GOOD)))


def test_a_listed_pair_ball_used_single_ended_is_refused():
    dev = _Device(PAIR)
    with pytest.raises(gowin_pack.PackRefused, match='admits it only as SSTL15D'):
        dev.add_io_to_bank(_bel(dict(GOOD)))


def test_a_single_ball_used_as_a_pair_half_is_refused():
    dev = _Device(SINGLE)
    with pytest.raises(gowin_pack.PackRefused, match='pair half'):
        dev.add_io_to_bank(_bel(dict(GOOD), parms={'DIFF': 'P', 'DIFF_TYPE': 'ELVDS_IOBUF'},
                                typ='ELVDS_IOBUF'))


def test_a_pair_is_admitted_on_its_listed_halves():
    dev = _Device(PAIR)
    dev.add_io_to_bank(_bel(dict(GOOD, IO_TYPE='SSTL15D'),
                            parms={'DIFF': 'P', 'DIFF_TYPE': 'ELVDS_IOBUF'}, typ='ELVDS_IOBUF'))
    dev.add_io_to_bank(_bel({'IO_TYPE': 'SSTL15D'}, idx='B',
                            parms={'DIFF': 'N', 'DIFF_TYPE': 'ELVDS_IOBUF'}, typ='ELVDS_IOBUF'))
    assert len(dev.banked) == 2


def test_a_pair_on_swapped_halves_is_refused():
    dev = _Device(PAIR)
    with pytest.raises(gowin_pack.PackRefused, match='pair half'):
        dev.add_io_to_bank(_bel(dict(GOOD, IO_TYPE='SSTL15D'),
                                parms={'DIFF': 'N', 'DIFF_TYPE': 'ELVDS_IOBUF'}, typ='ELVDS_IOBUF'))


# -- the manifest itself, checked against the die ------------------------

DEVICE = "GW5AST-138C"


@pytest.fixture(scope="module")
def real_db():
    path = os.path.join(os.path.dirname(chipdb.__file__), f"{DEVICE}.msgpack.xz")
    if not os.path.exists(path):
        pytest.skip(f"{DEVICE}.msgpack.xz absent; run apycula.chipdb_builder")
    return chipdb.load_chipdb(path)


class _Loader(gowin_pack.GW5AST_138C):
    def __init__(self, db):
        class _ChipDB:
            pass
        self.chipdb = _ChipDB()
        self.chipdb.db = db


def _manifest(tmp_path, balls, **head):
    doc = {"device": DEVICE, "package": "PBGA484A", "settings": dict(SETTINGS),
           "balls": balls}
    doc.update(head)
    path = tmp_path / "ddr3_balls.json"
    path.write_text(json.dumps(doc))
    return str(path)


GOOD_BALLS = [
    {"pin": "Y4", "site": "IOL78A", "bank": 6, "port": "ddr_dq[0]", "io_type": "SSTL15"},
    {"pin": "Y3", "site": "IOL69A", "bank": 6, "port": "ddr_dqs[0]", "io_type": "SSTL15D",
     "half": "P", "pair": "AA3"},
    {"pin": "AA3", "site": "IOL69B", "bank": 6, "port": "ddr_dqs[0]", "io_type": "SSTL15D",
     "half": "N", "pair": "Y3"},
    {"pin": "M1", "site": "IOL35A", "bank": 7, "port": "ddr_addr[0]", "io_type": "SSTL15"},
]


def test_a_good_manifest_loads(real_db, tmp_path):
    balls, settings = _Loader(real_db)._load_ddr3_manifest(_manifest(tmp_path, GOOD_BALLS))
    assert set(balls) == {"IOL78A", "IOL69A", "IOL69B", "IOL35A"}
    assert settings == SETTINGS


@pytest.mark.parametrize('change, why', [
    (lambda b: b[0].update(site="IOL79A"), "is not IO site"),
    (lambda b: b.append({"pin": "V22", "site": "IOB103A", "bank": 6, "io_type": "SSTL15"}),
     "is not IO site|not on the bank"),
    (lambda b: b[0].update(io_type="SSTL15D"), "single ball must be SSTL15"),
    (lambda b: b[0].update(io_type="LVCMOS33"), "single ball must be SSTL15"),
    (lambda b: b[2].update(pair="Y4"), "pair is not the other half"),
    (lambda b: b.append(dict(b[0])), "listed twice"),
    (lambda b: b[3].update(bank=6), "not on the bank"),
])
def test_a_bad_manifest_is_refused(real_db, tmp_path, change, why):
    balls = [dict(b) for b in GOOD_BALLS]
    change(balls)
    with pytest.raises(gowin_pack.PackRefused, match=why):
        _Loader(real_db)._load_ddr3_manifest(_manifest(tmp_path, balls))


@pytest.mark.parametrize('head, why', [
    ({"device": "GW5A-25A"}, "not the GW5AST-138C"),
    ({"package": "XYZ"}, "not in this chipdb"),
    ({"settings": dict(SETTINGS, DRIVE="12")}, "not the proven"),
])
def test_a_manifest_for_another_part_or_setting_is_refused(real_db, tmp_path, head, why):
    with pytest.raises(gowin_pack.PackRefused, match=why):
        _Loader(real_db)._load_ddr3_manifest(_manifest(tmp_path, GOOD_BALLS, **head))
