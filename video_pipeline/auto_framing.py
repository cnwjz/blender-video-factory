"""
Auto-framing module — extracted from build_style_v4.py.
Reusable cross-frame ortho camera optimization for narrative objects.
Placed in video_pipeline/ — NOT in protocol_guard/.
"""
import math


def is_narrative_object(obj_name, patterns=None):
    if patterns is None:
        patterns = ["Counter_", "Sign_", "Cashier_", "_Root", "_Body", "_Head",
                     "_Torso", "_Leg", "_Arm", "_Apron", "Product_", "Shutter_",
                     "_body", "_head"]  # lowercase variants for graybox objects
    return any(p in obj_name for p in patterns)


def get_cross_frame_union_bbox(frame_data):
    all_xs, all_ys = [], []
    for _frame, points in frame_data:
        for item in points:
            px, py = item[0], item[1]  # handles both (px,py) and (px,py,name)
            all_xs.append(px); all_ys.append(py)
    if not all_xs: return None
    return (min(all_xs), max(all_xs), min(all_ys), max(all_ys))


def compute_margins(screen_bbox):
    if screen_bbox is None: return (0, 0, 0, 0)
    ux_min, ux_max, uy_min, uy_max = screen_bbox
    return (ux_min, 1.0 - ux_max, 1.0 - uy_max, uy_min)


def check_clipping(screen_points, margin_left=0.05, margin_right=0.05,
                   margin_top=0.05, margin_bottom=0.05):
    clipped = []
    for px, py, obj_name in screen_points:
        if not (margin_left <= px <= 1.0 - margin_right and
                margin_bottom <= py <= 1.0 - margin_top):
            clipped.append(obj_name)
    return clipped


def score_framing(screen_bbox, target_top_empty_range=(0.10, 0.16),
                  min_bot_margin=0.06, min_left_margin=0.04,
                  min_right_margin=0.04, min_vert_occupancy=0.50):
    if screen_bbox is None: return (999, False, {"error": "no_screen_bbox"})
    ux_min, ux_max, uy_min, uy_max = screen_bbox
    top_empty = 1.0 - uy_max; bot_margin = uy_min
    left_margin = ux_min; right_margin = 1.0 - ux_max
    vert_occ = uy_max - uy_min
    if left_margin < min_left_margin or right_margin < min_right_margin:
        return (999, False, {"reason": "horizontal_margin_violation"})
    if top_empty < 0.02 or bot_margin < 0.02:
        return (999, False, {"reason": "vertical_margin_violation"})
    if vert_occ < min_vert_occupancy:
        return (999, False, {"reason": "vertical_occupancy_below_minimum"})
    te_low, te_high = target_top_empty_range
    te_score = 0 if te_low <= top_empty <= te_high else \
        min(abs(top_empty-te_low), abs(top_empty-te_high)) * 15
    bm_score = max(0, min_bot_margin - bot_margin) * 25
    score = te_score + bm_score
    return (score, True, {"top_empty": round(top_empty,4), "bot_margin": round(bot_margin,4),
            "left_margin": round(left_margin,4), "right_margin": round(right_margin,4),
            "vert_occupancy": round(vert_occ,4), "score": round(score,3)})


def scan_ortho_params(frame_data_func, ortho_range, shift_x_range, shift_y_range,
                      min_vert_occupancy=0.50, min_left_margin=0.04,
                      min_right_margin=0.04, min_top_margin=0.03, min_bot_margin=0.03):
    best = (None, None, None, 999, None)
    for ortho in ortho_range:
        for sx in shift_x_range:
            for sy in shift_y_range:
                frame_data = frame_data_func(ortho, sx, sy)
                if frame_data is None: continue
                bbox = get_cross_frame_union_bbox(frame_data)
                if bbox is None: continue
                score, valid, details = score_framing(
                    bbox, target_top_empty_range=(0.10, 0.25),
                    min_bot_margin=min_bot_margin, min_left_margin=min_left_margin,
                    min_right_margin=min_right_margin, min_vert_occupancy=min_vert_occupancy)
                if valid and score < best[3]: best = (ortho, sx, sy, score, details)
    if best[0] is None: return (None, None, None, None, None)
    return best
