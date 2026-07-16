"""List all available actions in Kenney characters."""
import bpy, os

CH_FBX = r"D:\blender-video-factory\projects\bvf_asset_test_001_checkout_lane\assets\imported\kenney_mini-characters\Models\FBX format"
full = os.path.join(CH_FBX, "character-male-a.fbx")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=full)

print(f"Actions: {len(bpy.data.actions)}")
for i, a in enumerate(bpy.data.actions):
    fc = len(a.fcurves) if hasattr(a,'fcurves') else 0
    fr = (int(a.frame_range[0]), int(a.frame_range[1]))
    print(f"  [{i:2d}] {a.name:40s} frames={fr} curves={fc}")

# Try playing action 0 on armature
arm = [o for o in bpy.data.objects if o.type=='ARMATURE']
if arm:
    arm = arm[0]
    print(f"\nArmature: {arm.name}")
    print(f"  Bones: {len(arm.data.bones)}")
    for b in arm.data.bones:
        print(f"    {b.name}")

print("ACTIONS AUDIT COMPLETE")
