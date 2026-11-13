import os
import gdsfactory as gf

# Initialize standard gdsfactory layout environment
gf.gpdk.PDK.activate()

# ==============================================================================
# 1. SKY130 LAYER DEFINITIONS (Zero dependency on external sky130 package)
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

# ==============================================================================
# 2. EXACT SKY130 TINY TAPEOUT 1x2 FLOORPLAN & DEF PIN GEOMETRY
# ==============================================================================
TILE_W, TILE_H = 161.00, 225.76

DEF_PINS = {
    "ua[0]":    (152.26, 0.50,   0.90, 1.00),
    "ua[1]":    (132.94, 0.50,   0.90, 1.00),
    "ua[2]":    (113.62, 0.50,   0.90, 1.00),
    "ua[3]":    (94.30,  0.50,   0.90, 1.00),
    "ui_in[0]": (138.46, 225.26, 0.30, 1.00),
    "ui_in[1]": (135.70, 225.26, 0.30, 1.00),
}

POWER_X = {"VPWR": 10.00, "VGND": 156.50}

# ==============================================================================
# 3. NATIVE DEVICE GENERATORS (Auto-cached using @gf.cell)
# ==============================================================================
@gf.cell
def create_mosfet(w: float, l: float, nf: int, dev_type: str) -> gf.Component:
    """Draws a DRC-clean parameterizable Sky130 MOSFET from scratch."""
    c = gf.Component()
    sd_pitch = 0.42
    diff_len = nf * l + (nf + 1) * sd_pitch
    
    # Active & Implants
    c << gf.components.rectangle(size=(diff_len, w), layer=LAYER_DIFF)
    imp = c << gf.components.rectangle(size=(diff_len + 0.26, w + 0.26), layer=LAYER_NSDM if dev_type == "nfet" else LAYER_PSDM)
    imp.move((-0.13, -0.13))
    
    if dev_type == "pfet":
        nw = c << gf.components.rectangle(size=(diff_len + 1.2, w + 1.2), layer=LAYER_NWELL)
        nw.move((-0.6, -0.6))
        
    # Poly Fingers & M1 Contacts
    for i in range(nf):
        px = sd_pitch + i * (l + sd_pitch)
        poly = c << gf.components.rectangle(size=(l, w + 0.4), layer=LAYER_POLY)
        poly.move((px, -0.2))
        
    for i in range(nf + 1):
        cx = i * (l + sd_pitch) + sd_pitch / 2.0
        li = c << gf.components.rectangle(size=(0.17, w), layer=LAYER_LI)
        li.move((cx - 0.085, 0))
        m1 = c << gf.components.rectangle(size=(0.3, w + 0.2), layer=LAYER_MET1)
        m1.move((cx - 0.15, -0.1))
        
    return c

@gf.cell
def create_mimcap(w: float, l: float) -> gf.Component:
    """Draws a simple overlapping Met3/Met4 MIM Capacitor."""
    c = gf.Component()
    c << gf.components.rectangle(size=(w, l), layer=LAYER_MET3)
    top = c << gf.components.rectangle(size=(w - 2.0, l - 2.0), layer=LAYER_MET4)
    top.move((1.0, 1.0))
    return c

# ==============================================================================
# 4. PRIMITIVE HELPER FUNCTIONS (VIAS, ROUTING, GUARD RINGS)
# ==============================================================================
def add_via_stack(comp: gf.Component, x: float, y: float, bottom_met: int, top_met: int, cols: int = 2, rows: int = 2):
    via_specs = {
        1: (LAYER_MET1, LAYER_VIA1, LAYER_MET2, 0.15, 0.32, 0.06),
        2: (LAYER_MET2, LAYER_VIA2, LAYER_MET3, 0.20, 0.40, 0.06),
        3: (LAYER_MET3, LAYER_VIA3, LAYER_MET4, 0.20, 0.40, 0.07),
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
        seg = comp << gf.components.rectangle(size=(xmax - xmin, ymax - ymin), layer=layer)
        seg.move((xmin, ymin))

def add_guard_ring(comp: gf.Component, x0: float, y0: float, w: float, h: float, ring_type: str):
    bar_w = 0.8
    imp = LAYER_PSDM if ring_type == "ptap" else LAYER_NSDM
    for sx, sy, sw, sh in [(x0, y0, w, bar_w), (x0, y0 + h - bar_w, w, bar_w), (x0, y0, bar_w, h), (x0 + w - bar_w, y0, bar_w, h)]:
        for lyr in (LAYER_TAP, LAYER_LI, LAYER_MET1):
            r = comp << gf.components.rectangle(size=(sw, sh), layer=lyr)
            r.move((sx, sy))
        i = comp << gf.components.rectangle(size=(sw + 0.26, sh + 0.26), layer=imp)
        i.move((sx - 0.13, sy - 0.13))

def build_common_centroid_array(comp: gf.Component, dev_type: str, w_finger: float, l: float, origin: tuple, pitch: float = 4.0):
    x0, y0 = origin
    pattern = ["DUM_L", "A", "B", "B", "A", "DUM_R"]
    terminals = {"A": {"S": [], "G": [], "D": []}, "B": {"S": [], "G": [], "D": []}}

    for idx, role in enumerate(pattern):
        mos = create_mosfet(w=w_finger, l=l, nf=1, dev_type=dev_type)
        ref = comp << mos
        ref.move((x0 + idx * pitch, y0))
        
        cx, cy = (ref.xmin + ref.xmax) / 2.0, (ref.ymin + ref.ymax) / 2.0
        s_pos, g_pos, d_pos = (ref.xmin + 0.25, cy), (cx, ref.ymax - 0.15), (ref.xmax - 0.25, cy)

        if role in terminals:
            terminals[role]["S"].append(s_pos)
            terminals[role]["G"].append(g_pos)
            terminals[role]["D"].append(d_pos)
            
    return terminals

# ==============================================================================
# 5. MAIN TOP-LEVEL CELL
# ==============================================================================
@gf.cell
def tt_um_Zero_Drift_Opamp() -> gf.Component:
    c = gf.Component()

    # PR Boundary & Power Rails
    c.add_polygon([(0, 0), (TILE_W, 0), (TILE_W, TILE_H), (0, TILE_H)], layer=LAYER_PR_BND)
    for rail, px in POWER_X.items():
        bar = c << gf.components.rectangle(size=(2.0, TILE_H - 20), layer=LAYER_MET4)
        bar.move((px - 1.0, 10.0))
        pin = c << gf.components.rectangle(size=(2.0, 2.5), layer=LAYER_MET4_PIN)
        pin.move((px - 1.0, 10.0))
        c.add_label(text=rail, position=(px, 11.25), layer=LAYER_MET4_LBL)

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
    route_manhattan(c, [(140.0, 38.0), (POWER_X["VGND"], 38.0)], 1.2, LAYER_MET1)
    add_via_stack(c, x=POWER_X["VGND"], y=38.0, bottom_met=1, top_met=4, cols=3, rows=3)

    mirror_terms = build_common_centroid_array(c, "pfet", 2.5, 1.0, origin=(34.0, 74.0))
    m5 = c << create_mosfet(w=2.5, l=0.5, nf=8, dev_type="pfet")
    m5.move((88.0, 74.0))

    add_guard_ring(c, x0=22.0, y0=68.0, w=118.0, h=20.0, ring_type="ntap")
    route_manhattan(c, [(POWER_X["VPWR"], 78.0), (22.0, 78.0)], 1.2, LAYER_MET1)
    add_via_stack(c, x=POWER_X["VPWR"], y=78.0, bottom_met=1, top_met=4, cols=3, rows=3)

    cmiller = c << create_mimcap(w=32.0, l=32.0)
    cmiller.move((60.0, 112.0))

    # Signal Routing Core
    mtail_cx = (mtail.xmin + mtail.xmax) / 2.0
    for dev in ("A", "B"):
        for sx, sy in diff_terms[dev]["S"]:
            route_manhattan(c, [(sx, sy), (sx, 44.5)], 0.3, LAYER_MET1)
    route_manhattan(c, [(37.0, 44.5), (118.0, 44.5), (mtail_cx + 0.5, 23.2)], 0.5, LAYER_MET1)

    # Route net_bias to ua[3]
    add_via_stack(c, x=94.30, y=26.5, bottom_met=1, top_met=4)
    route_manhattan(c, [(94.30, 26.5), (94.30, 0.50)], 0.8, LAYER_MET4)

    # Connect to Output Driver (M5) and ua[2]
    m5_dx = m5.xmax - 0.5
    add_via_stack(c, x=m5_dx, y=76.0, bottom_met=1, top_met=4)
    route_manhattan(c, [(m5_dx, 76.0), (m5_dx, 128.0), (88.0, 128.0)], 1.0, LAYER_MET4)
    route_manhattan(c, [(m5_dx, 76.0), (m5_dx, 8.0), (DEF_PINS["ua[2]"][0], 8.0), (DEF_PINS["ua[2]"][0], 0.50)], 0.85, LAYER_MET4)

    # DEF Pins Setup
    for pin_name, (px, py, pw, ph) in DEF_PINS.items():
        p = c << gf.components.rectangle(size=(pw, ph), layer=LAYER_MET4)
        p.move((px - pw / 2.0, py - ph / 2.0))
        p_pin = c << gf.components.rectangle(size=(pw, ph), layer=LAYER_MET4_PIN)
        p_pin.move((px - pw / 2.0, py - ph / 2.0))
        c.add_label(text=pin_name, position=(px, py), layer=LAYER_MET4_LBL)

    return c

if __name__ == "__main__":
    os.makedirs("gds", exist_ok=True)
    layout = tt_um_Zero_Drift_Opamp()
    out_file = "gds/tt_um_Zero_Drift_Opamp.gds"
    layout.write_gds(out_file)
    print(f"Successfully generated layout: {out_file}")
    print(f"Bounding box: {layout.xmax - layout.xmin:.2f} x {layout.ymax - layout.ymin:.2f} um")
