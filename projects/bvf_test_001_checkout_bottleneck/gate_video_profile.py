"""
Per-frame expected state profile for checkout_bottleneck video.
All expectations derived from graybox_config.json — NOT from scene state.
"""
import json, os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(SCRIPT_DIR, "graybox_config.json"), encoding="utf-8") as f:
    CFG = json.load(f)

# ── Derived constants ──
N_ENTRY_FRAMES = {nc["id"]: nc["frame"] for nc in CFG["new_customers"]}
WC = CFG["window_close"]
WC_LIGHT_OFF = WC["light_off"]       # [61, 72]
WC_SHUTTER = WC["shutter_down"]      # [70, 88]
WC_CASHIER = WC["cashier_retreat"]   # [72, 90]
WC_QUEUE_PAUSE = WC["middle_queue_pause"]  # [61, 105]
DIVERSION = CFG["diversion"]

# Sign/overlay visibility switch frames (from build_graybox.py keyframes)
SIGN_SWITCH_FRAME = 66    # Sign_middle→off, Sign_middle_off→on at frame 66
OVERLAY_APPEAR_FRAME = 78  # Counter_middle_overlay appears at frame 78


def is_visible_at_frame(target_id, frame):
    """Return (viewport_visible, render_visible) from video config.
    Objects without dynamic visibility are always visible.
    """
    # N1-N4: hidden before entry frame, visible at and after
    for nid, entry_frame in N_ENTRY_FRAMES.items():
        if target_id.startswith(nid):
            return (frame >= entry_frame, frame >= entry_frame)

    # Sign_middle: visible before switch, hidden after
    if target_id == "Sign_middle":
        return (frame < SIGN_SWITCH_FRAME, frame < SIGN_SWITCH_FRAME)

    # Sign_middle_off: hidden before switch, visible after
    if target_id == "Sign_middle_off":
        return (frame >= SIGN_SWITCH_FRAME, frame >= SIGN_SWITCH_FRAME)

    # Counter_middle_overlay: hidden before appear frame, visible after
    if target_id == "Counter_middle_overlay":
        return (frame >= OVERLAY_APPEAR_FRAME, frame >= OVERLAY_APPEAR_FRAME)

    # All other objects: always visible
    return (True, True)


def get_projection_targets_for_frame(frame):
    """Return list of target_ids expected in projection_groups at this frame.
    Includes all narrative objects that should be visible.
    Excludes objects hidden at this frame.
    """
    # Base narrative objects (always visible)
    base = []
    # L1-L3, M1-M3, R1-R3 bodies + heads
    for cid in ["L1","L2","L3","M1","M2","M3","R1","R2","R3"]:
        base.extend([f"{cid}_body", f"{cid}_head"])
    # N1-N4: only if entered
    for nid, ef in N_ENTRY_FRAMES.items():
        if frame >= ef:
            base.extend([f"{nid}_body", f"{nid}_head"])
    # Cashiers
    for cp in ["left","middle","right"]:
        base.extend([f"Cashier_{cp}_body", f"Cashier_{cp}_head"])
    # Counters
    base.extend(["Counter_left","Counter_middle","Counter_right"])
    # Counter_middle_overlay: only if appeared
    if frame >= OVERLAY_APPEAR_FRAME:
        base.append("Counter_middle_overlay")
    # Signs
    base.extend(["Sign_left","Sign_right"])
    if frame < SIGN_SWITCH_FRAME:
        base.append("Sign_middle")
    else:
        base.append("Sign_middle_off")
    # Shutters
    base.extend(["Shutter_left","Shutter_middle","Shutter_right"])

    return base


def get_visibility_targets_for_frame(frame):
    """Return dict of {target_id: {viewport, render}} for objects
    that should have visibility checked at this frame.
    Objects always visible can be omitted (checked via static).
    Dynamic-visibility objects return per-frame expectations.
    """
    result = {}
    # N1-N4: dynamic
    for nid, ef in N_ENTRY_FRAMES.items():
        vis = frame >= ef
        result[f"{nid}_body"] = vis
        result[f"{nid}_head"] = vis
    # Dynamic signs/overlay
    result["Sign_middle"] = frame < SIGN_SWITCH_FRAME
    result["Sign_middle_off"] = frame >= SIGN_SWITCH_FRAME
    result["Counter_middle_overlay"] = frame >= OVERLAY_APPEAR_FRAME
    return result


def get_event_frames():
    """Return sorted list of event frames derived from config."""
    fs = {1, 90, 150, 240, 345}
    for vals in CFG.get("window_close", {}).values():
        for v in vals: fs.update([v, v-1, v+1])
    for cd in CFG.get("diversion", {}).values():
        for fv in cd.get("frames", []): fs.update([fv, fv-1, fv+1])
    for nc in CFG.get("new_customers", []):
        fid = nc["frame"]; fs.update([fid, fid-1, fid+1])
    for f in [60, 120, 270]: fs.add(f)
    fs.add(345)
    return sorted(f for f in fs if 1 <= f <= 345)
