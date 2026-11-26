import os
import re
import gdsfactory as gf

# Initialize standard gdsfactory layout environment
gf.gpdk.PDK.activate()

# ==============================================================================
# 1. SKY130 LAYER DEFINITIONS
# ==============================================================================
LAYER_NWELL    = (64, 20)
LAYER_DIFF     = (65, 20)
LAYER_TAP      = (65, 44)
LAYER_POLY     = (66, 20)
LAYER_NSDM     = (93, 44)
LAYER_PSDM     = (94, 20)
LAYER_LICON    = (66, 44)
LAYER_LI       = (67, 20)
LAYER_MCON     = (67, 44)
LAYER_MET1     = (68, 20)
LAYER_VIA1     = (68, 44)
LAYER_MET2     = (69, 20)
LAYER_VIA2     = (69, 44)
LAYER_MET3     = (70, 20)
LAYER_VIA3     = (70, 44)
LAYER_MET4     = (71, 20)
LAYER_MET4_PIN = (71, 16)
LAYER_MET4_LBL = (71, 5)
LAYER_PR_BND   = (235, 4)

TILE_W, TILE_H = 161.00, 225.76


# ==============================================================================
# 2. PARSE OFFICIAL TINY TAPEOUT 1x2 ANALOG TEMPLATE DEF
# ==============================================================================
def load_template_pins() -> dict:
    """Reads exact pin boxes, directions, and USE types from tt_analog_1x2.def."""
    candidate_paths = [
        "tt_analog_1x2.def",
        "tt/tech/sky130A/def/analog/tt_analog_1x2.def",
        "../tech/sky130A/def/analog/tt_analog_1x2.def",
    ]
    def_path = next((p for p in candidate_paths if os.path.exists(p)), None)
    if not def_path:
        raise FileNotFoundError(
            "Could not find tt_analog_1x2.def. Ensure it is in the repository root."
        )

    with open(def_path, "r") as f:
        text = f.read()

    units_match = re.search(r"UNITS\s+DISTANCE\s+MICRONS\s+(\d+)\s*;", text)
    dbu = float(units_match.group(1)) if units_match else 1000.0

    pins_block_match = re.search(r"PINS\s+\d+\s*;(.*?)END\s+PINS", text, re.DOTALL)
    if not pins_block_match:
        raise ValueError(f"No PINS section found in {def_path}")

    pins = {}
    entries = re.split(r"\n\s*-\s+", "\n" + pins_block_match.group(1).strip())
    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue
        name = entry.split()[0]

        dir_m = re.search(r"\+\s*DIRECTION\s+(\S+)", entry)
        use_m = re.search(r"\+\s*USE\s+(\S+)", entry)
        layer_m = re.search(
            r"\+\s*LAYER\s+(\S+)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)",
            entry,
        )
        placed_m = re.search(
            r"\+\s*(?:PLACED|FIXED)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s*(\S+)",
            entry,
        )
        if not (layer_m and placed_m):
            continue

        layer_name = layer_m.group(1)
        lx1, ly1, lx2, ly2 = map(float, layer_m.groups()[1:])
        px, py = float(placed_m.group(1)), float(placed_m.group(2))
        orient = placed_m.group(3)

        if orient == "N":
            x1, y1, x2, y2 = px + lx1, py + ly1, px + lx2, py + ly2
        elif orient == "S":
            x1, y1, x2, y2 = px - lx2, py - ly2, px - lx1, py - ly1
        elif orient == "FN":
            x1, y1, x2, y2 = px - lx2, py + ly1, px - lx1, py + ly2
        elif orient == "FS":
            x1, y1, x2, y2 = px + lx1, py - ly2, px + lx2, py - ly1
        elif orient == "E":
            x1, y1, x2, y2 = px + ly1, py - lx2, px + ly2, py - lx1
        elif orient == "W":
            x1, y1, x2, y2 = px - ly2, py + lx1, px - ly1, py + lx2
        elif orient == "FE":
            x1, y1, x2, y2 = px + ly1, py + lx1, px + ly2, py + lx2
        elif orient == "FW":
            x1, y1, x2, y2 = px - ly2, py - lx2, px - ly1, py - lx1
        else:
            x1, y1, x2, y2 = px + lx1, py + ly1, px + lx2, py + ly2

        xmin, xmax = min(x1, x2) / dbu, max(x1, x2) / dbu
        ymin, ymax = min(y1, y2) / dbu, max(y1, y2) / dbu

        default_use = "ANALOG" if name.startswith("ua[") else "SIGNAL"
        pins[name] = {
            "bbox": (xmin, ymin, xmax, ymax),
            "cx": (xmin + xmax) / 2.0,
            "cy": (ymin + ymax) / 2.0,
            "w": xmax - xmin,
            "h": ymax - ymin,
            "layer": layer_name,
            "direction": dir_m.group(1) if dir_m else "INOUT",
            "use": use_m.group(1) if use_m else default_use,
        }

    # Inject VPWR and VGND met4 stripes since tt_analog_1x2.def omits power pins
    if "VPWR" not in pins:
        pins["VPWR"] = {
            "bbox": (2.0, 10.0, 4.0, TILE_H - 10.0),
            "cx": 3.0,
            "cy": TILE_H / 2.0,
            "w": 2.0,
            "h": TILE_H - 20.0,
            "layer": "met4",
            "direction": "INOUT",
            "use": "POWER",
        }
    if "VGND" not in pins:
        pins["VGND"] = {
            "bbox": (TILE_W - 4.0, 10.0, TILE_W - 2.0, TILE_H - 10.0),
            "cx": TILE_W - 3.0,
            "cy": TILE_H / 2.0,
            "w": 2.0,
            "h": TILE_H - 20.0,
            "layer": "met4",
            "direction": "INOUT",
            "use": "GROUND",
        }

    return pins


TEMPLATE_PINS = load_template_pins()

# ==============================================================================
# 3. NATIVE DEVICE GENERATORS
# ==============================================================================
@gf.cell
def create_mosfet(w: float, l: float, nf: int, dev_type: str) -> gf.Component:
    """Draws a DRC-clean parameterizable Sky130 MOSFET with LICON & MCON."""
    c = gf.Component()
    sd_pitch = 0.42
    diff_len = nf * l + (nf + 1) * sd_pitch

    # Active & Implants
    c << gf.components.rectangle(size=(diff_len, w), layer=LAYER_DIFF)
    imp = c << gf.components.rectangle(
        size=(diff_len + 0.26, w + 0.26),
        layer=LAYER_NSDM if dev_type == "nfet" else LAYER_PSDM,
    )
    imp.move((-0.13, -0.13))

    # Poly Fingers
    for i in range(nf):
        px = sd_pitch + i * (l + sd_pitch)
        poly = c << gf.components.rectangle(size=(l, w + 0.4), layer=LAYER_POLY)
        poly.move((px, -0.2))

    # Source/Drain Contacts (LICON -> LI -> MCON -> MET1)
    n_contacts = max(1, int((w - 0.12) // 0.36))
    span_y = (n_contacts - 1) * 0.36
    y_start = (w - span_y) / 2.0 - 0.085

    for i in range(nf + 1):
        cx = i * (l + sd_pitch) + sd_pitch / 2.0
        li = c << gf.components.rectangle(size=(0.17, w), layer=LAYER_LI)
        li.move((cx - 0.085, 0))
        m1 = c << gf.components.rectangle(size=(0.30, w + 0.16), layer=LAYER_MET1)
        m1.move((cx - 0.15, -0.08))

        for k in range(n_contacts):
            cy = y_start + k * 0.36
            lic = c << gf.components.rectangle(size=(0.17, 0.17), layer=LAYER_LICON)
            lic.move((cx - 0.085, cy))
            mc = c << gf.components.rectangle(size=(0.17, 0.17), layer=LAYER_MCON)
            mc.move((cx - 0.085, cy))

    return c


@gf.cell
def create_mimcap(w: float, l: float) -> gf.Component:
    """Draws an overlapping Met3/Met4 capacitor."""
    c = gf.Component()
    c << gf.components.rectangle(size=(w, l), layer=LAYER_MET3)
    top = c << gf.components.rectangle(size=(w - 2.0, l - 2.0), layer=LAYER_MET4)
    top.move((1.0, 1.0))
    return c


# ==============================================================================
# 4. PRIMITIVE HELPER FUNCTIONS (VIAS, ROUTING, GUARD RINGS)
# ==============================================================================
def add_via_stack(
    comp: gf.Component,
    x: float,
    y: float,
    bottom_met: int,
    top_met: int,
    cols: int = 2,
    rows: int = 2,
):
    # Sky130 DRC-clean via sizes, pitches, and >= 0.10 um enclosures
    via_specs = {
        1: (LAYER_MET1, LAYER_VIA1, LAYER_MET2, 0.15, 0.36, 0.10),
        2: (LAYER_MET2, LAYER_VIA2, LAYER_MET3, 0.20, 0.42, 0.10),
        3: (LAYER_MET3, LAYER_VIA3, LAYER_MET4, 0.20, 0.42, 0.10),
    }
    for level in range(bottom_met, top_met):
        bot_l, via_l, top_l, vw, pitch, enc = via_specs[level]
        pad_w = (cols - 1) * pitch + vw + 2 * enc
        pad_h = (rows - 1) * pitch + vw + 2 * enc
        for layer in (bot_l, top_l):
            pad = comp << gf.components.rectangle(size=(pad_w, pad_h), layer=layer)
            pad.move((x - pad_w / 2.0, y - pad_h / 2.0))
        for c_idx in range(cols):
            for r_idx in range(rows):
                vx = x - ((cols - 1) * pitch) / 2.0 + c_idx * pitch - vw / 2.0
                vy = y - ((rows - 1) * pitch) / 2.0 + r_idx * pitch - vw / 2.0
                v = comp << gf.components.rectangle(size=(vw, vw), layer=via_l)
                v.move((vx, vy))


def route_manhattan(comp: gf.Component, pts: list, width: float, layer: tuple):
    for i in range(len(pts) - 1):
        x1, y1 = pts[i]
        x2, y2 = pts[i + 1]
        if abs(x1 - x2) > 1e-6 and abs(y1 - y2) > 1e-6:
            route_manhattan(comp, [(x1, y1), (x2, y1), (x2, y2)], width, layer)
            return
        xmin, xmax = min(x1, x2) - width / 2.0, max(x1, x2) + width / 2.0
        ymin, ymax = min(y1, y2) - width / 2.0, max(y1, y2) + width / 2.0
        seg = comp << gf.components.rectangle(
            size=(xmax - xmin, ymax - ymin), layer=layer
        )
        seg.move((xmin, ymin))


def add_guard_ring(
    comp: gf.Component, x0: float, y0: float, w: float, h: float, ring_type: str
):
    bar_w = 0.8
    imp = LAYER_PSDM if ring_type == "ptap" else LAYER_NSDM
    bars = [
        (x0, y0, w, bar_w, True),
        (x0, y0 + h - bar_w, w, bar_w, True),
        (x0, y0, bar_w, h, False),
        (x0 + w - bar_w, y0, bar_w, h, False),
    ]
    for sx, sy, sw, sh, is_horiz in bars:
        for lyr in (LAYER_TAP, LAYER_LI, LAYER_MET1):
            r = comp << gf.components.rectangle(size=(sw, sh), layer=lyr)
            r.move((sx, sy))
        im = comp << gf.components.rectangle(size=(sw + 0.26, sh + 0.26), layer=imp)
        im.move((sx - 0.13, sy - 0.13))

        # Populate LICON & MCON cuts along the guard ring
        if is_horiz:
            n_cuts = int((sw - 1.6) // 0.50)
            for k in range(n_cuts):
                cx = sx + 0.8 + k * 0.50
                cy = sy + (sh - 0.17) / 2.0
                for cl in (LAYER_LICON, LAYER_MCON):
                    cut = comp << gf.components.rectangle(size=(0.17, 0.17), layer=cl)
                    cut.move((cx, cy))
        else:
            n_cuts = int((sh - 1.6) // 0.50)
            for k in range(n_cuts):
                cx = sx + (sw - 0.17) / 2.0
                cy = sy + 0.8 + k * 0.50
                for cl in (LAYER_LICON, LAYER_MCON):
                    cut = comp << gf.components.rectangle(size=(0.17, 0.17), layer=cl)
                    cut.move((cx, cy))


def build_common_centroid_array(
    comp: gf.Component,
    dev_type: str,
    w_finger: float,
    l: float,
    origin: tuple,
    pitch: float = 4.0,
):
    x0, y0 = origin
    pattern = ["DUM_L", "A", "B", "B", "A", "DUM_R"]
    terminals = {"A": {"S": [], "G": [], "D": []}, "B": {"S": [], "G": [], "D": []}}

    for idx, role in enumerate(pattern):
        mos = create_mosfet(w=w_finger, l=l, nf=1, dev_type=dev_type)
        ref = comp << mos
        ref.move((x0 + idx * pitch, y0))

        cx, cy = (ref.xmin + ref.xmax) / 2.0, (ref.ymin + ref.ymax) / 2.0
        # Exact contact centers (sd_pitch / 2.0 = 0.21 from diff edge)
        s_pos = (ref.xmin + 0.21, cy)
        g_pos = (cx, ref.ymax - 0.15)
        d_pos = (ref.xmax - 0.21, cy)

        if role in terminals:
            terminals[role]["S"].append(s_pos)
            terminals[role]["G"].append(g_pos)
            terminals[role]["D"].append(d_pos)

    return terminals


# ==============================================================================
# 5. MAIN TOP-LEVEL CELL (No @gf.cell so name stays exact)
# ==============================================================================
def tt_um_Zero_Drift_Opamp() -> gf.Component:
    c = gf.Component("tt_um_Zero_Drift_Opamp")

    # PR Boundary
    c.add_polygon(
        [(0, 0), (TILE_W, 0), (TILE_W, TILE_H), (0, TILE_H)], layer=LAYER_PR_BND
    )

    # Place ALL 53 Official Tiny Tapeout Template Pins (met4, met4.pin, met4.label)
    for pin_name, info in TEMPLATE_PINS.items():
        xmin, ymin, xmax, ymax = info["bbox"]
        rect_pts = [(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax)]
        c.add_polygon(rect_pts, layer=LAYER_MET4)
        c.add_polygon(rect_pts, layer=LAYER_MET4_PIN)
        c.add_label(text=pin_name, position=(info["cx"], info["cy"]), layer=LAYER_MET4_LBL)

    pwr_name = "VDPWR" if "VDPWR" in TEMPLATE_PINS else "VPWR"
    vpwr_x = TEMPLATE_PINS[pwr_name]["cx"]
    vgnd_x = TEMPLATE_PINS["VGND"]["cx"]

    # Place Core Silicon Devices
    sw_refs = []
    for i in range(4):
        sw = c << create_mosfet(w=1.0, l=0.15, nf=2, dev_type="nfet")
        sw.move((28.0 + i * 16.0, 22.0))
        sw_refs.append(sw)

    mbias = c << create_mosfet(w=2.5, l=1.0, nf=2, dev_type="nfet")
    mbias.move((98.0, 22.0))
    mtail = c << create_mosfet(w=2.5, l=1.0, nf=2, dev_type="nfet")
    mtail.move((116.0, 22.0))

    diff_terms = build_common_centroid_array(c, "nfet", 2.5, 1.0, origin=(34.0, 48.0))
    add_guard_ring(c, x0=22.0, y0=17.0, w=118.0, h=42.0, ring_type="ptap")
    route_manhattan(c, [(140.0, 38.0), (vgnd_x, 38.0)], 1.2, LAYER_MET1)
    add_via_stack(c, x=vgnd_x, y=38.0, bottom_met=1, top_met=4, cols=2, rows=3)

    # Single unified NWELL enclosing the entire PFET + ntap region (fixes all 5 FEOL nwell spacing errors)
    nw = c << gf.components.rectangle(size=(119.0, 21.0), layer=LAYER_NWELL)
    nw.move((21.5, 67.5))

    mirror_terms = build_common_centroid_array(c, "pfet", 2.5, 1.0, origin=(34.0, 74.0))
    m5 = c << create_mosfet(w=2.5, l=0.5, nf=8, dev_type="pfet")
    m5.move((88.0, 74.0))

    add_guard_ring(c, x0=22.0, y0=68.0, w=118.0, h=20.0, ring_type="ntap")
    route_manhattan(c, [(vpwr_x, 78.0), (22.0, 78.0)], 1.2, LAYER_MET1)
    add_via_stack(c, x=vpwr_x, y=78.0, bottom_met=1, top_met=4, cols=2, rows=3)

    cmiller = c << create_mimcap(w=32.0, l=32.0)
    cmiller.move((60.0, 112.0))

    # Signal Routing Core (aligned to exact contact centers to avoid met1 spacing errors)
    mtail_cx = (mtail.xmin + mtail.xmax) / 2.0
    for dev in ("A", "B"):
        for sx, sy in diff_terms[dev]["S"]:
            route_manhattan(c, [(sx, sy), (sx, 44.5)], 0.30, LAYER_MET1)
    route_manhattan(
        c, [(38.21, 44.5), (mtail_cx, 44.5), (mtail_cx, 23.25)], 0.30, LAYER_MET1
    )

    # Connect ua[0] (INP) to input switch 0 (horizontal track at y=4.0)
    ua0 = TEMPLATE_PINS["ua[0]"]
    sw0_x, sw0_y = sw_refs[0].xmin + 0.21, sw_refs[0].ymin + 0.50
    add_via_stack(c, x=sw0_x, y=sw0_y, bottom_met=1, top_met=4, cols=1, rows=2)
    route_manhattan(
        c,
        [(sw0_x, sw0_y), (sw0_x, 4.0), (ua0["cx"], 4.0), (ua0["cx"], ua0["cy"])],
        0.85,
        LAYER_MET4,
    )

    # Connect ua[1] (INN) to input switch 1 (horizontal track at y=6.0)
    ua1 = TEMPLATE_PINS["ua[1]"]
    sw1_x, sw1_y = sw_refs[1].xmin + 0.21, sw_refs[1].ymin + 0.50
    add_via_stack(c, x=sw1_x, y=sw1_y, bottom_met=1, top_met=4, cols=1, rows=2)
    route_manhattan(
        c,
        [(sw1_x, sw1_y), (sw1_x, 6.0), (ua1["cx"], 6.0), (ua1["cx"], ua1["cy"])],
        0.85,
        LAYER_MET4,
    )

    # Connect Output Driver (M5) to Miller Cap and ua[2] (horizontal track at y=8.0)
    ua2 = TEMPLATE_PINS["ua[2]"]
    m5_dx = m5.xmax - 0.21
    add_via_stack(c, x=m5_dx, y=75.25, bottom_met=1, top_met=4, cols=1, rows=2)
    route_manhattan(c, [(m5_dx, 75.25), (m5_dx, 128.0), (88.0, 128.0)], 1.0, LAYER_MET4)
    route_manhattan(
        c,
        [(m5_dx, 75.25), (m5_dx, 8.0), (ua2["cx"], 8.0), (ua2["cx"], ua2["cy"])],
        0.85,
        LAYER_MET4,
    )

    return c


if __name__ == "__main__":
    os.makedirs("gds", exist_ok=True)
    os.makedirs("lef", exist_ok=True)
    layout = tt_um_Zero_Drift_Opamp()
    layout.flatten()

    out_file_gds = "gds/tt_um_Zero_Drift_Opamp.gds"
    out_file_lef = "lef/tt_um_Zero_Drift_Opamp.lef"

    # with_metadata=False strips $$$CONTEXT_INFO$$$ and layer (0, 0)
    layout.write_gds(out_file_gds, with_metadata=False)

    # Generate matching LEF macro with all 53 official template pins
    lef_lines = [
        "VERSION 5.7 ;",
        'BUSBITCHARS "[]" ;',
        'DIVIDERCHAR "/" ;',
        "MACRO tt_um_Zero_Drift_Opamp",
        "  CLASS BLOCK ;",
        "  FOREIGN tt_um_Zero_Drift_Opamp 0.000 0.000 ;",
        "  ORIGIN 0.000 0.000 ;",
        f"  SIZE {TILE_W:.3f} BY {TILE_H:.3f} ;",
        "  SYMMETRY X Y R90 ;",
    ]

    for pin_name, info in TEMPLATE_PINS.items():
        xmin, ymin, xmax, ymax = info["bbox"]
        lef_lines.extend(
            [
                f"  PIN {pin_name}",
                f"    DIRECTION {info['direction']} ;",
                f"    USE {info['use']} ;",
                "    PORT",
                f"      LAYER {info['layer']} ;",
                f"        RECT {xmin:.3f} {ymin:.3f} {xmax:.3f} {ymax:.3f} ;",
                "    END",
                f"  END {pin_name}",
            ]
        )

    lef_lines.extend(["END tt_um_Zero_Drift_Opamp", "END LIBRARY", ""])

    with open(out_file_lef, "w") as f:
        f.write("\n".join(lef_lines))

    print(f"Successfully generated layout: {out_file_gds}")
    print(f"Successfully generated LEF ({len(TEMPLATE_PINS)} pins): {out_file_lef}")
    print(f"Bounding box: {layout.xmax - layout.xmin:.2f} x {layout.ymax - layout.ymin:.2f} um")