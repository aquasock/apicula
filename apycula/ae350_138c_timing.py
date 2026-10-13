# SPDX-License-Identifier: MIT
"""Measured GW5AST-138C AE350_SOC bus-port timing.

The `.tm` file carries no AE350 group, so without this table every path into
or out of the hard SoC is untimed in the open flow, and the placer is free to
stretch the ROM, DDR and EXTS bus nets past what the block can take.

MEASURED with Gowin IDE 1.9.11.03 (GW5AST-LV138PG484AC1/I0, speed C1/I0): a
vehicle SoC driving the ROM, DDR and EXTS AHB ports from fabric registers at
75 MHz was placed and routed by the vendor, and `report_timing -from/-to` on
every `cpu/*` pin gave, per port bit, the `tSu`/`tHld` the vendor charges at
an input and the `tC2Q` it charges at an output, with the clock pin the arc
hangs off. Setup paths are the slow corner, hold paths the fast one.

Values are nanoseconds, folded per port group so every bit of a group carries
the group's worst value: the largest setup and hold, and a clock-to-out window
from the fastest hold-corner to the slowest setup-corner `tC2Q`. A group the
vehicle left unconnected (marked `fallback`) takes the worst value of the
groups on the same bus and clock.

The vendor also times one combinational arc through the block, EXTS_HREADYIN
to EXTS_HSEL (0.304 ns, slow corner); its fast-corner value was not reported,
so its minimum is 0.
"""

# port group -> (width, [(clock pin, setup, hold)])
AE350_SOC_INPUT_TIMING_138C = {
    'ROM_HRDATA': (32, [('AHB_CLK', 0.073, 0.086)]),
    'ROM_HREADY': (1, [('AHB_CLK', -1.646, 0.054)]),
    'ROM_HRESP': (1, [('AHB_CLK', 0.073, 0.086)]),  # fallback
    'EXTS_HRDATA': (32, [('AHB_CLK', -0.011, 0.062)]),
    'EXTS_HREADYIN': (1, [('AHB_CLK', -1.681, 0.027), ('APB_CLK', -0.125, 0.018)]),
    'EXTS_HRESP': (1, [('AHB_CLK', -1.609, 0.033)]),
    'DDR_HRDATA': (64, [('DDR_CLK', 0.125, 0.094)]),
    'DDR_HREADY': (1, [('DDR_CLK', -1.519, -0.022)]),
    'DDR_HRESP': (1, [('DDR_CLK', -1.406, 0.027)]),
}

# port group -> (width, [(clock pin, clock-to-out min, clock-to-out max)])
AE350_SOC_OUTPUT_TIMING_138C = {
    'ROM_HADDR': (32, [('AHB_CLK', 0.340, 1.176)]),
    'ROM_HTRANS': (2, [('AHB_CLK', 0.359, 1.007)]),
    'ROM_HWRITE': (1, [('AHB_CLK', 0.340, 1.176)]),  # fallback
    'EXTS_HADDR': (32, [('AHB_CLK', 0.296, 1.080)]),
    'EXTS_HTRANS': (2, [('AHB_CLK', 0.354, 0.913)]),
    'EXTS_HSEL': (1, [('AHB_CLK', 0.274, 1.401), ('APB_CLK', 0.350, 1.859)]),
    'EXTS_HWRITE': (1, [('AHB_CLK', 0.360, 0.949)]),
    'EXTS_HWDATA': (32, [('AHB_CLK', 0.263, 1.019)]),
    'EXTS_HSIZE': (3, [('AHB_CLK', 0.263, 1.401)]),  # fallback
    'EXTS_HBURST': (3, [('AHB_CLK', 0.263, 1.401)]),  # fallback
    'EXTS_HPROT': (4, [('AHB_CLK', 0.263, 1.401)]),  # fallback
    'DDR_HADDR': (32, [('DDR_CLK', 0.281, 1.002)]),
    'DDR_HTRANS': (2, [('DDR_CLK', 0.343, 0.948)]),
    'DDR_HWRITE': (1, [('DDR_CLK', 0.354, 0.993)]),
    'DDR_HSIZE': (3, [('DDR_CLK', 0.297, 0.882)]),
    'DDR_HBURST': (3, [('DDR_CLK', 0.304, 0.863)]),
    'DDR_HPROT': (4, [('DDR_CLK', 0.328, 0.819)]),
    'DDR_HWDATA': (64, [('DDR_CLK', 0.253, 0.862)]),
}

# (from pin, to pin, min, max)
AE350_SOC_COMB_TIMING_138C = [
    ('EXTS_HREADYIN', 'EXTS_HSEL', 0.0, 0.304),
]


def ae350_timing_group():
    """The table as one `db.timing[speed]['ae350']` group, one entry per bit.

    The chipdb types a timing group as `{arc name: [float, ...]}`, so the
    arc's kind and pins are carried in its name:
      `setup_hold:CLOCK:PORT` -> [setup, hold]
      `clock_out:CLOCK:PORT`  -> [min, max]
      `comb:FROM:TO`          -> [min, max]
    """
    # A bus bit is `NAMEi`, a one-bit port plain `NAME`, as in the port map.
    def bits(name, width):
        return [f"{name}{i}" for i in range(width)] if width > 1 else [name]

    group = {}
    for name, (width, arcs) in AE350_SOC_INPUT_TIMING_138C.items():
        for port in bits(name, width):
            for clock, setup, hold in arcs:
                group[f"setup_hold:{clock}:{port}"] = [setup, hold]
    for name, (width, arcs) in AE350_SOC_OUTPUT_TIMING_138C.items():
        for port in bits(name, width):
            for clock, c2q_min, c2q_max in arcs:
                group[f"clock_out:{clock}:{port}"] = [c2q_min, c2q_max]
    for src, dst, d_min, d_max in AE350_SOC_COMB_TIMING_138C:
        group[f"comb:{src}:{dst}"] = [d_min, d_max]
    return group
