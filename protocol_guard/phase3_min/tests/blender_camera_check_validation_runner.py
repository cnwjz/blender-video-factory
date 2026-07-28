"""Camera Check I2 R3 — 22 scenarios, iterate until all pass."""
import bpy, sys, os, json, math, mathutils, traceback, bmesh, importlib

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from protocol_guard.phase3_min.blender_scene_reader import (
    _check_camera_check, _check_root_objects, _recompute_target_overall,
)

BLENDER_VER = ".".join(str(x) for x in bpy.app.version)

def _clear():
    for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
    for m in list(bpy.data.meshes): bpy.data.meshes.remove(m)
    for c in list(bpy.data.cameras): bpy.data.cameras.remove(c)

def _cc(**kw):
    return {"camera_object_name": kw.get("cam","Camera"),
            "minimum_visible_projected_corner_count": kw.get("mvc",8),
            "required_screen_bbox": {"min_left": kw.get("ml",0.0),"max_right": kw.get("mr",1.0),
                                     "min_bottom": kw.get("mb",0.0),"max_top": kw.get("mt",1.0)}}

def _t(tid, root, rt="MESH", gs="SELF_MESH", cc=None):
    t = {"target_id": tid, "root_object_name": root, "expected_root_type": rt, "geometry_scope": gs}
    if cc is not None: t["camera_check"] = cc
    return t

def _pt(rt="MESH"):
    return {"checks": {"object_exists": {"result": "PASS"}, "object_type": {"result": "PASS", "actual": rt}}}

def _look_at(cam, target=(0,0,0)):
    d = mathutils.Vector(target) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()

def _add_cam(name="Camera", loc=(0,-10,0), look=(0,0,0)):
    d = bpy.data.cameras.new("Cd")
    cam = bpy.data.objects.new(name, d)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = loc; _look_at(cam, look)
    bpy.context.scene.camera = cam
    bpy.context.view_layer.update()
    return cam

SCENARIOS = []
def S(sid, desc, fn): SCENARIOS.append((sid, desc, fn))

# ════ CC-BL-01: Perspective PASS ════
def bl01():
    _clear()
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0,0,0))
    bpy.context.object.name = "root"
    _add_cam("Camera", (0,-10,0), (0,0,0))
    r = _check_camera_check(bpy.context.scene, _t("A","root",cc=_cc(mvc=8,mb=0.5,mt=0.5)), _pt())
    return (r.get("result")=="PASS" and r.get("projected_corner_count")==8
            and r.get("front_facing_projected_corner_count")==8,
            dict(r=r.get("result"),pc=r.get("projected_corner_count"),fc=r.get("front_facing_projected_corner_count")),
            "PASS 8/8")
S("CC-BL-01","Perspective Camera PASS",bl01)

# ════ CC-BL-02: Orthographic PASS ════
def bl02():
    _clear()
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0,0,0))
    bpy.context.object.name = "root"
    cam = _add_cam("Camera", (0,-10,0), (0,0,0))
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = 6
    bpy.context.view_layer.update()
    r = _check_camera_check(bpy.context.scene, _t("A","root",cc=_cc(mvc=8,mb=0.5,mt=0.5)), _pt())
    return (r.get("result")=="PASS" and r.get("projected_corner_count")==8
            and r.get("front_facing_projected_corner_count")==8,
            dict(r=r.get("result"),type=cam.data.type,pc=r.get("projected_corner_count")),
            "ORTHO PASS 8/8")
S("CC-BL-02","Orthographic Camera PASS",bl02)

# ════ CC-BL-03: Behind camera ════
def bl03():
    _clear()
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0,-10,0))
    bpy.context.object.name = "root"
    _add_cam("Camera", (0,0,0), (0,10,0))  # looking +Y, cube behind at -Y
    bpy.context.view_layer.update()
    r = _check_camera_check(bpy.context.scene, _t("A","root",cc=_cc(mvc=1)), _pt())
    return (r.get("result")=="FAIL" and r.get("failure_code")=="BEHIND_CAMERA"
            and r.get("projected_corner_count")==8 and r.get("front_facing_projected_corner_count")==0,
            dict(fc=r.get("failure_code"),pc=r.get("projected_corner_count"),ffc=r.get("front_facing_projected_corner_count")),
            "BEHIND_CAMERA 0/8")
S("CC-BL-03","All corners behind camera",bl03)

# ════ CC-BL-04: Exactly 4 front corners ════
def bl04():
    _clear()
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0,0,0))
    bpy.context.object.name = "root"
    d = bpy.data.cameras.new("Cd"); d.type = 'ORTHO'; d.ortho_scale = 6
    cam = bpy.data.objects.new("Camera", d)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = (0,0,0); cam.rotation_euler = (math.pi/2,0,0)
    bpy.context.scene.camera = cam; bpy.context.view_layer.update()
    r = _check_camera_check(bpy.context.scene,
        _t("A","root",cc=_cc(mvc=4,ml=0.0,mr=1.0,mb=0.5,mt=0.5)), _pt())
    ab = r.get("actual_screen_bbox",{})
    rb = r.get("required_screen_bbox",{})
    return (r.get("result")=="PASS" and r.get("projected_corner_count")==8
            and r.get("front_facing_projected_corner_count")==4
            and r.get("minimum_visible_projected_corner_count")==4
            and ab.get("min_x",-1)>=rb.get("min_left",2)
            and ab.get("max_x",2)<=rb.get("max_right",-1)
            and ab.get("min_y",2)<=rb.get("min_bottom",-1)
            and ab.get("max_y",-1)>=rb.get("max_top",2),
            dict(fc=r.get("front_facing_projected_corner_count"),ab=ab,rb=rb,
                 type=cam.data.type), "PASS 4/8 ortho")
S("CC-BL-04","Exactly 4 front corners",bl04)

# ════ CC-BL-05～08: Boundary FAILs ════
def _boundary(side, cube_pos, cc_kw, check):
    _clear()
    bpy.ops.mesh.primitive_cube_add(size=2, location=cube_pos)
    bpy.context.object.name = "root"
    _add_cam("Camera", (0,-15,0), (0,0,0))
    r = _check_camera_check(bpy.context.scene, _t("A","root",cc=_cc(mvc=1,**cc_kw)), _pt())
    ab = r.get("actual_screen_bbox",{})
    ok = (r.get("result")=="FAIL" and r.get("failure_code")=="SCREEN_BBOX_REQUIREMENT_NOT_MET"
          and check(ab))
    return ok, dict(fc=r.get("failure_code"),ab=ab), "SCREEN_BBOX_REQUIREMENT_NOT_MET"

def bl05():
    r = _boundary("left", (2,0,0), {"ml":0.6,"mr":1.0,"mb":0.5,"mt":0.5},
        lambda ab: ab.get("min_x",0)<0.6 and ab.get("max_x",1)<=1.0
                   and ab.get("min_y",1)<=0.5 and ab.get("max_y",0)>=0.5)
    return r
S("CC-BL-05","Left boundary FAIL",bl05)

def bl06():
    r = _boundary("right", (-2,0,0), {"ml":0.0,"mr":0.4,"mb":0.5,"mt":0.5},
        lambda ab: ab.get("max_x",1)>0.4 and ab.get("min_x",0)>=0.0
                   and ab.get("min_y",1)<=0.5 and ab.get("max_y",0)>=0.5)
    return r
S("CC-BL-06","Right boundary FAIL",bl06)

def bl07():
    r = _boundary("bottom", (0,0,5), {"ml":0.0,"mr":1.0,"mb":0.7,"mt":0.5},
        lambda ab: ab.get("min_y",1)>0.7 and ab.get("max_y",0)>=0.5
                   and ab.get("min_x",0)>=0.0 and ab.get("max_x",1)<=1.0)
    return r
S("CC-BL-07","Bottom boundary FAIL",bl07)

def bl08():
    r = _boundary("top", (0,0,-5), {"ml":0.0,"mr":1.0,"mb":0.5,"mt":0.3},
        lambda ab: ab.get("max_y",0)<0.3 and ab.get("min_y",1)<=0.5
                   and ab.get("min_x",0)>=0.0 and ab.get("max_x",1)<=1.0)
    return r
S("CC-BL-08","Top boundary FAIL",bl08)

# ════ CC-BL-09: 4 boundaries equal ════
def bl09():
    _clear()
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0,0,0))
    bpy.context.object.name = "root"
    _add_cam("Camera", (0,-10,0), (0,0,0))
    r_m = _check_camera_check(bpy.context.scene, _t("A","root",cc=_cc(mvc=8,mb=0.5,mt=0.5)), _pt())
    ab = r_m.get("actual_screen_bbox",{})
    t = _t("A","root",cc=_cc(mvc=8,ml=ab["min_x"],mr=ab["max_x"],mb=ab["min_y"],mt=ab["max_y"]))
    r = _check_camera_check(bpy.context.scene, t, _pt())
    a2 = r.get("actual_screen_bbox",{})
    rb = r.get("required_screen_bbox",{})
    eps=1e-6
    return (r.get("result")=="PASS" and abs(a2["min_x"]-rb["min_left"])<=eps
            and abs(a2["max_x"]-rb["max_right"])<=eps
            and abs(a2["min_y"]-rb["min_bottom"])<=eps
            and abs(a2["max_y"]-rb["max_top"])<=eps,
            dict(ab=a2,rb=rb), "PASS boundaries equal")
S("CC-BL-09","Boundary equality PASS",bl09)

# ════ CC-BL-10: SELF_AND_DESCENDANT_MESHES ════
def bl10():
    _clear()
    bpy.ops.mesh.primitive_cube_add(size=1.5, location=(0,0,0))
    rt = bpy.context.object; rt.name = "root"
    bpy.ops.mesh.primitive_ico_sphere_add(radius=0.5, location=(0,0,2))
    ch = bpy.context.object; ch.name = "child"; ch.parent = rt
    _add_cam("Camera", (0,-15,3), (0,0,1))
    t = _t("A","root",gs="SELF_AND_DESCENDANT_MESHES",cc=_cc(mvc=8,mb=0.5,mt=0.5))
    r = _check_camera_check(bpy.context.scene, t, _pt())
    meshes = r.get("evaluated_mesh_names",[])
    ok = (r.get("result")=="PASS" and set(meshes)=={"root","child"})
    # Verify union bbox != root-only bbox
    r2 = _check_camera_check(bpy.context.scene, _t("A","root",gs="SELF_MESH",cc=_cc(mvc=8,mb=0.5,mt=0.5)), _pt())
    union_differs = (r.get("actual_screen_bbox") != r2.get("actual_screen_bbox"))
    return ok and union_differs, dict(meshes=meshes,union_differs=union_differs), "PASS both meshes"
S("CC-BL-10","SELF_AND_DESCENDANT_MESHES",bl10)

# ════ CC-BL-11: SELF_MESH ════
def bl11():
    _clear()
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0,0,0))
    rt = bpy.context.object; rt.name = "root"
    bpy.ops.mesh.primitive_ico_sphere_add(radius=0.5, location=(0,0,2))
    ch = bpy.context.object; ch.name = "child"; ch.parent = rt
    _add_cam("Camera", (0,-15,2), (0,0,1))
    r = _check_camera_check(bpy.context.scene, _t("A","root",gs="SELF_MESH",cc=_cc(mvc=8,mb=0.5,mt=0.5)), _pt())
    meshes = r.get("evaluated_mesh_names",[])
    return (r.get("result")=="PASS" and meshes==["root"],
            dict(meshes=meshes), "PASS root only")
S("CC-BL-11","SELF_MESH geometry scope",bl11)

# ════ CC-BL-12: DESCENDANT_MESHES ════
def bl12():
    _clear()
    rt = bpy.data.objects.new("root", None)
    rt.empty_display_type = 'PLAIN_AXES'
    bpy.context.scene.collection.objects.link(rt)
    bpy.ops.mesh.primitive_ico_sphere_add(radius=0.5, location=(0,0,2))
    ch = bpy.context.object; ch.name = "child"; ch.parent = rt
    _add_cam("Camera", (0,-15,3), (0,0,2))
    r = _check_camera_check(bpy.context.scene,
        _t("A","root","EMPTY",gs="DESCENDANT_MESHES",cc=_cc(mvc=8,mb=0.5,mt=0.5)),
        {"checks":{"object_exists":{"result":"PASS"},"object_type":{"result":"PASS","actual":"EMPTY"}}})
    meshes = r.get("evaluated_mesh_names",[])
    return (r.get("result")=="PASS" and meshes==["child"],
            dict(meshes=meshes), "PASS child only")
S("CC-BL-12","DESCENDANT_MESHES geometry scope",bl12)

# ════ CC-BL-13: Solidify modifier ════
def bl13():
    _clear()
    bpy.ops.mesh.primitive_plane_add(size=2, location=(0,0,0))
    rt = bpy.context.object; rt.name = "root"
    orig_zr = max(v.co.z for v in rt.data.vertices)-min(v.co.z for v in rt.data.vertices)
    mod = rt.modifiers.new("Solidify",'SOLIDIFY'); mod.thickness = 0.5
    _add_cam("Camera", (0,-15,3), (0,0,0))
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = rt.evaluated_get(dg)
    ev_mesh = ev.to_mesh()
    try:
        ev_zr = max(v.co.z for v in ev_mesh.vertices)-min(v.co.z for v in ev_mesh.vertices)
    finally:
        ev.to_mesh_clear()
    r = _check_camera_check(bpy.context.scene, _t("A","root",cc=_cc(mvc=8,mb=0.5,mt=0.5)), _pt())
    return (orig_zr<0.01 and ev_zr>0.1 and r.get("result")=="PASS"
            and r.get("evaluated_mesh_names")==["root"],
            dict(orig_z=orig_zr,ev_z=ev_zr,r=r.get("result")), "PASS evaluated changed")
S("CC-BL-13","Solidify modifier evaluated geometry",bl13)

# ════ CC-BL-14: Zero-vertex ════
def bl14():
    _clear()
    rt = bpy.data.objects.new("root", None)
    rt.empty_display_type = 'PLAIN_AXES'
    bpy.context.scene.collection.objects.link(rt)
    m = bpy.data.meshes.new("zero")
    o = bpy.data.objects.new("zero", m)
    bpy.context.scene.collection.objects.link(o); o.parent = rt
    _add_cam("Camera", (0,-5,3))
    r = _check_camera_check(bpy.context.scene,
        _t("A","root","EMPTY",gs="DESCENDANT_MESHES",cc=_cc(mvc=1)),
        {"checks":{"object_exists":{"result":"PASS"},"object_type":{"result":"PASS","actual":"EMPTY"}}})
    return (r.get("result")=="FAIL" and r.get("failure_code")=="NO_EVALUATED_GEOMETRY",
            dict(fc=r.get("failure_code")), "NO_EVALUATED_GEOMETRY")
S("CC-BL-14","Zero-vertex mesh",bl14)

# ════ CC-BL-15: Non-finite vertex ════
def bl15():
    _clear()
    bm = bmesh.new()
    bm.verts.new((0,0,0)); bm.verts.new((0,1,0)); bm.verts.new((float('nan'),0,0))
    bm.faces.new(list(bm.verts))
    m = bpy.data.meshes.new("nanm"); bm.to_mesh(m); bm.free()
    o = bpy.data.objects.new("root", m)
    bpy.context.scene.collection.objects.link(o)
    _add_cam("Camera", (0,-5,3))
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = o.evaluated_get(dg); evm = ev.to_mesh()
    try:
        has_nan = any(not math.isfinite(v.co.x) or not math.isfinite(v.co.y) or not math.isfinite(v.co.z)
                      for v in evm.vertices)
    finally:
        ev.to_mesh_clear()
    r = _check_camera_check(bpy.context.scene, _t("A","root",cc=_cc(mvc=1)), _pt())
    return (has_nan and r.get("result")=="FAIL" and r.get("failure_code")=="NON_FINITE_EVALUATED_VERTEX",
            dict(has_nan=has_nan,fc=r.get("failure_code")), "NON_FINITE_EVALUATED_VERTEX")
S("CC-BL-15","Non-finite vertex",bl15)

# ════ CC-BL-16: zero + non-finite → NON_FINITE precedence ════
def bl16():
    _clear()
    rt = bpy.data.objects.new("root", None)
    rt.empty_display_type = 'PLAIN_AXES'
    bpy.context.scene.collection.objects.link(rt)
    m0 = bpy.data.meshes.new("zero"); o0 = bpy.data.objects.new("zero", m0)
    bpy.context.scene.collection.objects.link(o0); o0.parent = rt
    bm = bmesh.new()
    bm.verts.new((float('nan'),0,0)); bm.verts.new((0,0,0)); bm.verts.new((0,1,0))
    bm.faces.new(list(bm.verts))
    m1 = bpy.data.meshes.new("nanm"); bm.to_mesh(m1); bm.free()
    o1 = bpy.data.objects.new("nan", m1)
    bpy.context.scene.collection.objects.link(o1); o1.parent = rt
    _add_cam("Camera", (0,-5,3))
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    # Precondition: zero mesh has 0 evaluated vertices
    ev0 = o0.evaluated_get(dg); evm0 = ev0.to_mesh()
    try: zero_count = len(evm0.vertices)
    finally: ev0.to_mesh_clear()
    # Precondition: NaN mesh has non-finite evaluated vertex
    ev1 = o1.evaluated_get(dg); evm1 = ev1.to_mesh()
    try:
        has_nan = any(not math.isfinite(v.co.x) or not math.isfinite(v.co.y) or not math.isfinite(v.co.z)
                      for v in evm1.vertices)
    finally: ev1.to_mesh_clear()
    assert zero_count == 0, f"zero mesh vertex count={zero_count}"
    assert has_nan, "NaN mesh has no non-finite vertices"
    r = _check_camera_check(bpy.context.scene,
        _t("A","root","EMPTY",gs="DESCENDANT_MESHES",cc=_cc(mvc=1)),
        {"checks":{"object_exists":{"result":"PASS"},"object_type":{"result":"PASS","actual":"EMPTY"}}})
    return (r.get("result")=="FAIL" and r.get("failure_code")=="NON_FINITE_EVALUATED_VERTEX",
            dict(fc=r.get("failure_code"),zero_v=zero_count,has_nan=has_nan), "NON_FINITE_EVALUATED_VERTEX")
S("CC-BL-16","Zero+nonfinite → NON_FINITE",bl16)

# ════ CC-BL-17: Two targets share Camera with caches ════
def bl17():
    _clear()
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0,0,0))
    bpy.context.object.name = "root1"
    bpy.ops.mesh.primitive_cube_add(size=1, location=(2,0,0))
    bpy.context.object.name = "root2"
    _add_cam("Camera", (0,-15,3), (1,0,0))
    t1 = _t("A","root1",cc=_cc(mvc=8,mb=0.5,mt=0.5))
    t2 = _t("B","root2",cc=_cc(mvc=8,mb=0.5,mt=0.5))
    caches = {}
    results = _check_root_objects(bpy.context.scene, [t1,t2], _target_caches=caches)
    assert "A" in caches and "B" in caches
    assert caches["A"] is not caches["B"]
    r1 = _check_camera_check(bpy.context.scene, t1, results[0], _target_cache=caches["A"])
    r2 = _check_camera_check(bpy.context.scene, t2, results[1], _target_cache=caches["B"])
    assert r1 is not r2
    return (r1.get("result")=="PASS" and r2.get("result")=="PASS",
            dict(r1=r1.get("result"),r2=r2.get("result")), "both PASS")
S("CC-BL-17","Two targets share Camera",bl17)

# ════ CC-BL-18: Entry PASS ════
def bl18():
    _clear()
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0,0,0))
    bpy.context.object.name = "root"
    _add_cam("Camera", (0,-10,0), (0,0,0))
    t = _t("A","root",cc=_cc(mvc=8,mb=0.5,mt=0.5))
    caches = {}
    results = _check_root_objects(bpy.context.scene, [t], _target_caches=caches)
    cc_r = _check_camera_check(bpy.context.scene, t, results[0], _target_cache=caches.get("A"))
    results[0]["checks"]["camera_check"] = cc_r
    results[0]["overall"] = _recompute_target_overall(results[0]["checks"])
    return (cc_r.get("result")=="PASS" and results[0]["overall"]=="PASS",
            dict(cc=cc_r.get("result"),ov=results[0]["overall"]), "PASS")
S("CC-BL-18","Entry orchestration PASS",bl18)

# ════ CC-BL-19: Camera not found ════
def bl19():
    _clear()
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0,0,0))
    bpy.context.object.name = "root"
    _add_cam("OtherCam", (0,-10,0))
    t = _t("A","root",cc=_cc(cam="NoExist",mvc=1))
    caches = {}
    results = _check_root_objects(bpy.context.scene, [t], _target_caches=caches)
    cc_r = _check_camera_check(bpy.context.scene, t, results[0], _target_cache=caches.get("A"))
    results[0]["checks"]["camera_check"] = cc_r
    results[0]["overall"] = _recompute_target_overall(results[0]["checks"])
    return (cc_r.get("failure_code")=="CAMERA_OBJECT_NOT_FOUND" and results[0]["overall"]=="FAIL",
            dict(fc=cc_r.get("failure_code"),ov=results[0]["overall"]), "CAMERA_OBJECT_NOT_FOUND")
S("CC-BL-19","Entry Camera not found",bl19)

# ════ CC-BL-20: depsgraph ERROR ════
def bl20():
    _clear()
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0,0,0))
    bpy.context.object.name = "root"
    _add_cam("Camera", (0,-10,0))
    t = _t("A","root",cc=_cc(mvc=1))
    caches = {}
    results = _check_root_objects(bpy.context.scene, [t], _target_caches=caches)
    import protocol_guard.phase3_min.blender_scene_reader as reader
    saved_bpy = reader.bpy
    class FakeContext:
        @staticmethod
        def evaluated_depsgraph_get(): raise RuntimeError("injected")
    class FakeBpy:
        context = FakeContext()
    reader.bpy = FakeBpy()
    try:
        cc_r = reader._check_camera_check(bpy.context.scene, t, results[0], _target_cache=caches.get("A"))
    finally:
        reader.bpy = saved_bpy
    return (cc_r.get("result")=="ERROR" and cc_r.get("error_type")=="CAMERA_CHECK_COMPUTATION_ERROR"
            and cc_r.get("operation")=="GET_EVALUATED_DEPSGRAPH"
            and cc_r.get("note")=="GET_EVALUATED_DEPSGRAPH_FAILED",
            dict(op=cc_r.get("operation")), "GET_EVALUATED_DEPSGRAPH ERROR")
S("CC-BL-20","Depsgraph failure ERROR",bl20)

# ════ CC-BL-21: Mixed PASS/FAIL ════
def bl21():
    _clear()
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0,0,0))
    bpy.context.object.name = "root1"
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0,0,-2))
    bpy.context.object.name = "root2"
    _add_cam("Camera", (0,-15,3), (0,0,0))  # look at origin
    t1 = _t("A","root1",cc=_cc(mvc=8,mb=0.5,mt=0.5))
    t2 = _t("B","root2",cc=_cc(cam="NoExist",mvc=1))
    caches = {}
    results = _check_root_objects(bpy.context.scene, [t1,t2], _target_caches=caches)
    assert caches["A"] is not caches["B"]
    cc1 = _check_camera_check(bpy.context.scene, t1, results[0], _target_cache=caches["A"])
    cc2 = _check_camera_check(bpy.context.scene, t2, results[1], _target_cache=caches["B"])
    results[0]["checks"]["camera_check"] = cc1; results[1]["checks"]["camera_check"] = cc2
    ov1 = _recompute_target_overall(results[0]["checks"])
    ov2 = _recompute_target_overall(results[1]["checks"])
    return (cc1.get("result")=="PASS" and ov1=="PASS"
            and cc2.get("failure_code")=="CAMERA_OBJECT_NOT_FOUND" and ov2=="FAIL",
            dict(cc1=cc1.get("result"),ov1=ov1,cc2=cc2.get("failure_code"),ov2=ov2),
            "PASS + CAMERA_OBJECT_NOT_FOUND")
S("CC-BL-21","Multiple targets mixed PASS/FAIL",bl21)

# ════ CC-BL-22: Empty geometry scope ════
def bl22():
    _clear()
    rt = bpy.data.objects.new("root", None)
    rt.empty_display_type = 'PLAIN_AXES'
    bpy.context.scene.collection.objects.link(rt)
    _add_cam("Camera", (0,-5,3))
    r = _check_camera_check(bpy.context.scene,
        _t("A","root","EMPTY",gs="DESCENDANT_MESHES",cc=_cc(mvc=1)),
        {"checks":{"object_exists":{"result":"PASS"},"object_type":{"result":"PASS","actual":"EMPTY"}}})
    return (r.get("result")=="FAIL" and r.get("failure_code")=="NO_EVALUATED_GEOMETRY"
            and r.get("evaluated_mesh_names")==[],
            dict(fc=r.get("failure_code"),mn=r.get("evaluated_mesh_names")), "NO_EVALUATED_GEOMETRY")
S("CC-BL-22","Empty geometry scope",bl22)

# ════ main ════
def main():
    results = []; all_passed = True
    for sid, desc, fn in SCENARIOS:
        try: passed, actual, expected = fn()
        except Exception: passed = False; actual = {"exn": traceback.format_exc()}; expected = "NO_EXCEPTION"
        results.append({"scenario_id":sid,"description":desc,"passed":passed,
                        "expected":str(expected),"actual":actual})
        if not passed: all_passed = False
    output = {"blender_version":BLENDER_VER,"factory_startup":True,"scenario_count":len(SCENARIOS),
              "scenarios":results,"overall_passed":all_passed,
              "real_project_blend_opened":False,"real_project_blend_saved":False,
              "render_executed":False,"user_asset_modified":False,"temporary_files_created":[]}
    print("CAMERA_CHECK_I2_JSON_BEGIN")
    print(json.dumps(output, ensure_ascii=False, default=str, sort_keys=True))
    print("CAMERA_CHECK_I2_JSON_END")
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
