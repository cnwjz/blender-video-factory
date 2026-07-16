"""
Kenney Character Import Audit — inspect GLB and FBX hierarchy, armatures, animations.
"""
import bpy, os, json

CH_GLB = r"D:\blender-video-factory\projects\bvf_asset_test_001_checkout_lane\assets\imported\kenney_mini-characters\Models\GLB format"
CH_FBX = r"D:\blender-video-factory\projects\bvf_asset_test_001_checkout_lane\assets\imported\kenney_mini-characters\Models\FBX format"
MK_GLB = r"D:\blender-video-factory\projects\bvf_asset_test_001_checkout_lane\assets\imported\kenney_mini-market\Models\GLB format"
MK_FBX = r"D:\blender-video-factory\projects\bvf_asset_test_001_checkout_lane\assets\imported\kenney_mini-market\Models\FBX format"

def audit_format(label, path, filename):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    full = os.path.join(path, filename)
    if not os.path.exists(full):
        print(f"  MISSING: {full}")
        return

    if full.endswith('.fbx'):
        bpy.ops.import_scene.fbx(filepath=full)
    else:
        bpy.ops.import_scene.gltf(filepath=full)

    objs = list(bpy.data.objects)
    meshes = [o for o in objs if o.type == 'MESH']
    armatures = [o for o in objs if o.type == 'ARMATURE']
    empties = [o for o in objs if o.type == 'EMPTY']

    # Check for animation data
    actions = list(bpy.data.actions)
    nla_tracks = 0
    for o in objs:
        if o.animation_data and o.animation_data.nla_tracks:
            nla_tracks += len(o.animation_data.nla_tracks)

    print(f"\n{'='*60}")
    print(f"  {label}: {filename}")
    print(f"  Objects: {len(objs)} (MESH:{len(meshes)} ARMATURE:{len(armatures)} EMPTY:{len(empties)})")
    print(f"  Actions: {len(actions)} NLA tracks: {nla_tracks}")

    # Print hierarchy
    roots = [o for o in objs if o.parent is None]
    def show_tree(obj, depth=0):
        prefix = "  " + "  " * depth + ("|- " if depth > 0 else "")
        arm_icon = "[A]" if obj.type == 'ARMATURE' else f"[{obj.type[0]}]" if obj.type else "[?]"
        has_anim = " ANIM" if (obj.animation_data and obj.animation_data.action) else ""
        kids = [c for c in obj.children]
        print(f"  {prefix}{arm_icon} {obj.name}{has_anim} ({len(kids)} children)")
        for child in sorted(kids, key=lambda x: x.name):
            show_tree(child, depth + 1)

    print(f"  Hierarchy:")
    for r in sorted(roots, key=lambda x: x.name):
        show_tree(r)
    print()

# ── Run audits ─────────────────────────────────────────────
# GLB Character
audit_format("GLB Character", CH_GLB, "character-male-a.glb")
# FBX Character
audit_format("FBX Character", CH_FBX, "character-male-a.fbx")
# GLB Employee
audit_format("GLB Employee", MK_GLB, "character-employee.glb")
# FBX Employee
audit_format("FBX Employee", MK_FBX, "character-employee.fbx")

print("AUDIT COMPLETE")
