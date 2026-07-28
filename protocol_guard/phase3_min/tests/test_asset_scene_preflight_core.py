"""Tests for asset_scene_preflight_core — CPython only, no bpy dependency."""

import json, math, os, subprocess, tempfile
import pytest
from protocol_guard.phase3_min.asset_scene_preflight_core import (
    SCHEMA_VERSION, CHECKER_NAME, SOURCE_REQUIREMENT_VERSION, RESULT_PREFIX,
    EXIT_PASS, EXIT_FAIL, EXIT_ERROR,
    GEOMETRY_SCOPES, AXIS_VALUES, VALID_RENDER_ENGINES,
    SpecParseError, SpecValidationError, UnsafePathError, NumericalValidationError,
    CanonicalizationError,
    validate_spec_paths,
    load_spec_bytes, parse_spec_json, validate_spec, load_and_validate_spec,
    axis_to_vector, vector_angle_degrees, quaternion_min_angle_degrees,
    is_within_absolute_tolerance, casefold_glob_match,
    sanitize_nonfinite, canonicalize_phase3_result, serialize_result_line,
    build_pass_result, build_fail_result, build_error_result,
    error_boundary,
)


def _minimal_spec(**overrides):
    s = {
        "schema_version": "1",
        "checker": "asset_scene_preflight_check",
        "source_requirement_version": "Blender 固定资产模板路线 v4",
        "repository_root": "D:\\blender-video-factory",
        "blend_path": "projects/test.blend",
        "scene_name": "Scene",
        "targets": [
            {
                "target_id": "CHR_TEST",
                "root_object_name": "CHR_Test_Root",
                "expected_root_type": "EMPTY",
                "geometry_scope": "DESCENDANT_MESHES"
            }
        ],
        "global_rules": {}
    }
    s.update(overrides)
    return s


# ════════════════ Path safety ════════════════

class TestPathSafety:
    def test_valid_path(self):
        abs_path, err = validate_spec_paths(
            "D:\\blender-video-factory",
            "protocol_guard/phase3_min/asset_scene_preflight_core.py")
        assert err is None
        assert abs_path is not None

    def test_absolute_blend_path_rejected(self):
        _, err = validate_spec_paths(
            "D:\\blender-video-factory",
            "D:\\absolute\\path.blend")
        assert err is not None

    def test_parent_traversal_rejected(self):
        _, err = validate_spec_paths(
            "D:\\blender-video-factory",
            "../escape.blend")
        assert err is not None

    def test_unc_path_rejected(self):
        _, err = validate_spec_paths(
            "D:\\blender-video-factory",
            "//server/share/file.blend")
        assert err is not None

    def test_nonexistent_target(self):
        _, err = validate_spec_paths(
            "D:\\blender-video-factory",
            "nonexistent_file_xyz.blend")
        assert err is not None

    def test_repo_root_not_dir(self):
        _, err = validate_spec_paths(
            "D:\\nonexistent_directory_xyz",
            "file.blend")
        assert err is not None

    def test_empty_blend_path(self):
        _, err = validate_spec_paths("D:\\blender-video-factory", "")
        assert err is not None

    def test_empty_repo_root(self):
        _, err = validate_spec_paths("", "file.blend")
        assert err is not None

    def test_control_character_in_path(self):
        _, err = validate_spec_paths(
            "D:\\blender-video-factory",
            "file\x00.blend")
        assert err is not None

    def test_intermediate_junction_escape_rejected(self):
        repo_td = tempfile.TemporaryDirectory()
        outside_td = tempfile.TemporaryDirectory()
        try:
            repo = repo_td.name
            outside = outside_td.name
            # Create a real file in the outside directory
            escape_path = os.path.join(outside, "escape.blend")
            with open(escape_path, "wb") as f:
                f.write(b"placeholder")

            # Create junction: repo/linked_out -> outside
            junction_path = os.path.join(repo, "linked_outside")
            r = subprocess.run(
                ["cmd", "/c", "mklink", "/J", junction_path, outside],
                capture_output=True, text=True)
            assert r.returncode == 0, (
                f"Junction creation failed: rc={r.returncode} "
                f"stdout={r.stdout} stderr={r.stderr}")

            abs_path, err = validate_spec_paths(repo, "linked_outside/escape.blend")
            assert abs_path is None, f"Expected rejection, got abs_path={abs_path}"
            assert err is not None
            combined = err.lower()
            assert any(kw in combined for kw in (
                "unsafe", "escape", "outside", "link", "junction",
                "realpath", "repository")), f"Unexpected error: {err}"

            # Remove junction only (not the target)
            os.rmdir(junction_path)
        finally:
            repo_td.cleanup()
            outside_td.cleanup()


# ════════════════ Spec validation ════════════════

class TestSpecValidation:
    def test_valid_minimal_spec(self):
        assert validate_spec(_minimal_spec()) == []

    def test_spec_not_dict(self):
        errs = validate_spec("not a dict")
        assert any("must be a JSON object" in e for e in errs)

    def test_wrong_schema_version(self):
        s = _minimal_spec(schema_version="2")
        assert any("schema_version" in e for e in validate_spec(s))

    def test_wrong_checker(self):
        s = _minimal_spec(checker="wrong")
        assert any("checker" in e for e in validate_spec(s))

    def test_missing_repository_root(self):
        s = _minimal_spec(); del s["repository_root"]
        assert any("repository_root" in e for e in validate_spec(s))

    def test_non_absolute_repository_root(self):
        s = _minimal_spec(repository_root="relative")
        assert any("absolute" in e for e in validate_spec(s))

    def test_absolute_blend_path(self):
        s = _minimal_spec(blend_path="D:\\abs.blend")
        assert any("relative" in e for e in validate_spec(s))

    def test_parent_traversal_blend_path(self):
        s = _minimal_spec(blend_path="../escape.blend")
        assert any("parent traversal" in e for e in validate_spec(s))

    def test_empty_targets(self):
        s = _minimal_spec(targets=[])
        assert any("targets" in e for e in validate_spec(s))

    def test_duplicate_target_id(self):
        s = _minimal_spec(targets=[
            {"target_id": "A", "root_object_name": "r1", "expected_root_type": "E", "geometry_scope": "SELF_MESH"},
            {"target_id": "A", "root_object_name": "r2", "expected_root_type": "E", "geometry_scope": "SELF_MESH"},
        ])
        assert any("unique" in e for e in validate_spec(s))

    def test_invalid_geometry_scope(self):
        s = _minimal_spec(targets=[{
            "target_id": "A", "root_object_name": "r", "expected_root_type": "E", "geometry_scope": "INVALID"}])
        assert any("geometry_scope" in e for e in validate_spec(s))

    def test_wrong_source_requirement_version(self):
        s = _minimal_spec(source_requirement_version="wrong_version_string")
        errs = validate_spec(s)
        assert any("source_requirement_version" in e for e in errs)

    def test_missing_blend_path(self):
        s = _minimal_spec(); del s["blend_path"]
        errs = validate_spec(s)
        assert any("blend_path" in e for e in errs)

    def test_missing_scene_name(self):
        s = _minimal_spec(); del s["scene_name"]
        errs = validate_spec(s)
        assert any("scene_name" in e for e in errs)

    def test_targets_not_array(self):
        s = _minimal_spec(targets="not_an_array")
        errs = validate_spec(s)
        assert any("targets" in e for e in errs)

    def test_missing_root_object_name(self):
        s = _minimal_spec(targets=[
            {"target_id": "A", "expected_root_type": "EMPTY", "geometry_scope": "SELF_MESH"}
        ])
        errs = validate_spec(s)
        assert any("root_object_name" in e for e in errs)

    def test_valid_standing(self):
        s = _minimal_spec(targets=[{
            "target_id": "A", "root_object_name": "r", "expected_root_type": "EMPTY",
            "geometry_scope": "SELF_MESH",
            "standing": {
                "local_up_axis": "+Z", "expected_world_up_axis": "+Z",
                "up_axis_tolerance_degrees": 15.0, "minimum_height_to_horizontal_ratio": 2.0,
                "required_landmark_relationships": [
                    {"upper_object_name": "Head", "lower_object_name": "Body",
                     "axis": "Z", "minimum_difference": 0.2}
                ]
            }
        }])
        assert validate_spec(s) == []

    def test_invalid_standing_axis(self):
        s = _minimal_spec(targets=[{
            "target_id": "A", "root_object_name": "r", "expected_root_type": "EMPTY",
            "geometry_scope": "SELF_MESH",
            "standing": {"local_up_axis": "+W"}
        }])
        errs = validate_spec(s)
        assert any("local_up_axis" in e for e in errs)

    def test_negative_tolerance_rejected(self):
        s = _minimal_spec(targets=[{
            "target_id": "A", "root_object_name": "r", "expected_root_type": "EMPTY",
            "geometry_scope": "SELF_MESH",
            "standing": {"up_axis_tolerance_degrees": -1.0}
        }])
        errs = validate_spec(s)
        assert any("tolerance" in e.lower() for e in errs)

    def test_valid_facing(self):
        s = _minimal_spec(targets=[{
            "target_id": "A", "root_object_name": "r", "expected_root_type": "EMPTY",
            "geometry_scope": "SELF_MESH",
            "facing": {"local_forward_axis": "+Y", "expected_world_forward_axis": "+Y",
                       "facing_tolerance_degrees": 5.0}
        }])
        assert validate_spec(s) == []

    def test_invalid_facing_axis(self):
        s = _minimal_spec(targets=[{
            "target_id": "A", "root_object_name": "r", "expected_root_type": "EMPTY",
            "geometry_scope": "SELF_MESH",
            "facing": {"local_forward_axis": "+W"}
        }])
        errs = validate_spec(s)
        assert any("local_forward_axis" in e for e in errs)

    def test_valid_rotation(self):
        s = _minimal_spec(targets=[{
            "target_id": "A", "root_object_name": "r", "expected_root_type": "EMPTY",
            "geometry_scope": "SELF_MESH",
            "rotation": {"expected_world_rotation_euler_degrees": [90, 0, 180],
                         "rotation_tolerance_degrees": 2.0}
        }])
        assert validate_spec(s) == []

    def test_ground_contact_valid(self):
        s = _minimal_spec(targets=[{
            "target_id": "A", "root_object_name": "r", "expected_root_type": "EMPTY",
            "geometry_scope": "SELF_MESH",
            "ground_contact": {"ground_z": 0.0, "ground_contact_tolerance": 0.02}
        }])
        assert validate_spec(s) == []

    def test_hierarchy_valid(self):
        s = _minimal_spec(targets=[{
            "target_id": "A", "root_object_name": "r", "expected_root_type": "EMPTY",
            "geometry_scope": "SELF_MESH",
            "hierarchy": {
                "required_direct_child_names": ["Armature"],
                "forbidden_direct_child_name_patterns": ["Icosphere*"],
                "required_descendant_names": ["Body", "Head"],
                "required_descendant_types": {"Body": "MESH", "Head": "MESH"}
            }
        }])
        assert validate_spec(s) == []

    def test_visibility_valid(self):
        s = _minimal_spec(targets=[{
            "target_id": "A", "root_object_name": "r", "expected_root_type": "EMPTY",
            "geometry_scope": "SELF_MESH",
            "visibility": {"require_not_hidden_viewport": True, "require_not_hidden_render": True}
        }])
        assert validate_spec(s) == []

    def test_material_assignment_valid(self):
        s = _minimal_spec(targets=[{
            "target_id": "A", "root_object_name": "r", "expected_root_type": "EMPTY",
            "geometry_scope": "SELF_MESH",
            "material_assignment": {"require_material_assignment_presence": True}
        }])
        assert validate_spec(s) == []

    def test_animation_state_valid(self):
        s = _minimal_spec(targets=[{
            "target_id": "A", "root_object_name": "r", "expected_root_type": "EMPTY",
            "geometry_scope": "SELF_MESH",
            "animation_state": {
                "animation_object_name": "Armature",
                "require_animation_data": True,
                "expected_action_name": "idle",
                "expected_pose_position": "POSE",
                "record_current_frame": True
            }
        }])
        assert validate_spec(s) == []

    def test_animation_state_missing_object_name(self):
        s = _minimal_spec(targets=[{
            "target_id": "A", "root_object_name": "r", "expected_root_type": "EMPTY",
            "geometry_scope": "SELF_MESH",
            "animation_state": {}
        }])
        errs = validate_spec(s)
        assert any("animation_object_name" in e for e in errs)

    def test_camera_check_valid(self):
        s = _minimal_spec(targets=[{
            "target_id": "A", "root_object_name": "r", "expected_root_type": "EMPTY",
            "geometry_scope": "SELF_MESH",
            "camera_check": {
                "camera_object_name": "Camera",
                "minimum_visible_projected_corner_count": 8,
                "required_screen_bbox": {"min_left": 0.04, "max_right": 0.96,
                                         "min_bottom": 0.04, "max_top": 0.96}
            }
        }])
        assert validate_spec(s) == []

    def test_scene_rules_valid(self):
        s = _minimal_spec(scene_rules={"expected_render_engine": "BLENDER_EEVEE_NEXT"})
        assert validate_spec(s) == []

    def test_collection_rules_valid(self):
        s = _minimal_spec(collection_rules={
            "required_collection_names": ["CHR_A"],
            "forbidden_collection_name_patterns": ["*test*"]
        })
        assert validate_spec(s) == []

    def test_projection_group_valid(self):
        s = _minimal_spec(projection_groups=[{
            "group_id": "essentials",
            "target_ids": ["CHR_TEST"],
            "additional_object_names": ["Prop_A"],
            "camera_object_name": "Camera",
            "minimum_visible_projected_corner_count": 8,
            "required_screen_bbox": {"min_left": 0.0, "max_right": 1.0,
                                     "min_bottom": 0.0, "max_top": 1.0},
            "require_camera_outside_world_bbox": True
        }])
        assert validate_spec(s) == []

    def test_projection_group_unknown_target(self):
        s = _minimal_spec(projection_groups=[{
            "group_id": "essentials",
            "target_ids": ["NONEXISTENT"],
            "additional_object_names": [],
            "camera_object_name": "Camera",
            "minimum_visible_projected_corner_count": 1,
            "required_screen_bbox": {"min_left": 0, "max_right": 1, "min_bottom": 0, "max_top": 1},
            "require_camera_outside_world_bbox": False
        }])
        errs = validate_spec(s)
        assert any("unknown target_id" in e for e in errs)

    def test_projection_bbox_order_invalid(self):
        s = _minimal_spec(projection_groups=[{
            "group_id": "essentials",
            "target_ids": ["CHR_TEST"],
            "additional_object_names": [],
            "camera_object_name": "Camera",
            "minimum_visible_projected_corner_count": 1,
            "required_screen_bbox": {"min_left": 0.9, "max_right": 0.1,
                                     "min_bottom": 0.0, "max_top": 1.0},
            "require_camera_outside_world_bbox": False
        }])
        errs = validate_spec(s)
        assert any("min_left > max_right" in e for e in errs)


# ════════════════ Spec file loading ════════════════

class TestSpecLoading:
    def test_load_and_validate_valid(self):
        import tempfile
        td = tempfile.TemporaryDirectory()
        try:
            repo = td.name
            blend = os.path.join(repo, "scene.blend")
            with open(blend, "wb") as f:
                f.write(b"placeholder blend content")
            spec = _minimal_spec(repository_root=repo, blend_path="scene.blend")
            sf = os.path.join(repo, "spec.json")
            with open(sf, "w", encoding="utf-8") as f:
                json.dump(spec, f)
            parsed, sha, errs = load_and_validate_spec(sf)
            assert errs == []
            assert parsed is not None
            assert len(sha) == 64
        finally:
            td.cleanup()

    def test_load_and_validate_rejects_missing_blend_file(self):
        import tempfile
        td = tempfile.TemporaryDirectory()
        try:
            repo = td.name
            spec = _minimal_spec(repository_root=repo, blend_path="missing.blend")
            sf = os.path.join(repo, "spec.json")
            with open(sf, "w", encoding="utf-8") as f:
                json.dump(spec, f)
            parsed, sha, errs = load_and_validate_spec(sf)
            assert len(errs) > 0
            assert parsed is None
            combined = " ".join(errs).lower()
            assert any(kw in combined for kw in (
                "blend_path", "unsafe", "missing", "not found", "existing file", "file"))
        finally:
            td.cleanup()

    def test_load_and_validate_rejects_parent_traversal(self):
        import tempfile
        td = tempfile.TemporaryDirectory()
        try:
            repo = td.name
            spec = _minimal_spec(repository_root=repo, blend_path="../escape.blend")
            sf = os.path.join(repo, "spec.json")
            with open(sf, "w", encoding="utf-8") as f:
                json.dump(spec, f)
            parsed, sha, errs = load_and_validate_spec(sf)
            assert len(errs) > 0
            assert parsed is None
            combined = " ".join(errs).lower()
            assert any(kw in combined for kw in (
                "parent traversal", "blend_path", "rejected", "unsafe", "path"))
        finally:
            td.cleanup()

    def test_load_invalid_json(self):
        import tempfile
        td = tempfile.TemporaryDirectory()
        try:
            sf = os.path.join(td.name, "spec.json")
            with open(sf, "w", encoding="utf-8") as f:
                f.write("not json")
            spec, sha, errs = load_and_validate_spec(sf)
            assert len(errs) > 0
            assert spec is None
        finally:
            td.cleanup()

    def test_load_nonexistent_file(self):
        spec, sha, errs = load_and_validate_spec(
            os.path.join("nonexistent_dir_xyz", "spec.json"))
        assert len(errs) > 0
        assert spec is None

    def test_load_and_validate_rejects_intermediate_junction_escape(self):
        repo_td = tempfile.TemporaryDirectory()
        outside_td = tempfile.TemporaryDirectory()
        try:
            repo = repo_td.name
            outside = outside_td.name
            escape_path = os.path.join(outside, "escape.blend")
            with open(escape_path, "wb") as f:
                f.write(b"placeholder")

            junction_path = os.path.join(repo, "linked_outside")
            r = subprocess.run(
                ["cmd", "/c", "mklink", "/J", junction_path, outside],
                capture_output=True, text=True)
            assert r.returncode == 0, (
                f"Junction creation failed: rc={r.returncode} "
                f"stdout={r.stdout} stderr={r.stderr}")

            spec = _minimal_spec(
                repository_root=repo, blend_path="linked_outside/escape.blend")
            sf = os.path.join(repo, "spec.json")
            with open(sf, "w", encoding="utf-8") as f:
                json.dump(spec, f)

            parsed, sha, errs = load_and_validate_spec(sf)
            assert parsed is None
            assert len(errs) > 0
            combined = " ".join(errs).lower()
            assert any(kw in combined for kw in (
                "unsafe", "escape", "outside", "link", "junction",
                "realpath", "blend_path", "repository")), f"Unexpected errors: {errs}"

            os.rmdir(junction_path)
        finally:
            repo_td.cleanup()
            outside_td.cleanup()


# ════════════════ Render engine validation ════════════════

class TestRenderEngine:
    def test_valid_eevee_next(self):
        s = _minimal_spec(scene_rules={"expected_render_engine": "BLENDER_EEVEE_NEXT"})
        assert validate_spec(s) == []

    def test_valid_cycles(self):
        s = _minimal_spec(scene_rules={"expected_render_engine": "CYCLES"})
        assert validate_spec(s) == []

    def test_invalid_render_engine(self):
        s = _minimal_spec(scene_rules={"expected_render_engine": "BLENDER_RANDOM"})
        errs = validate_spec(s)
        assert any("recognized" in e for e in errs)

    def test_empty_render_engine(self):
        s = _minimal_spec(scene_rules={"expected_render_engine": ""})
        errs = validate_spec(s)
        assert any("expected_render_engine" in e for e in errs)


# ════════════════ Stronger numerical validation ════════════════

class TestNumericalValidation:
    def test_bool_rejected_for_number(self):
        s = _minimal_spec(targets=[{
            "target_id": "A", "root_object_name": "r", "expected_root_type": "E",
            "geometry_scope": "SELF_MESH",
            "standing": {"minimum_height_to_horizontal_ratio": True}
        }])
        errs = validate_spec(s)
        assert any("number" in e for e in errs)

    def test_nan_rejected_for_number(self):
        s = _minimal_spec(targets=[{
            "target_id": "A", "root_object_name": "r", "expected_root_type": "E",
            "geometry_scope": "SELF_MESH",
            "ground_contact": {"ground_z": float('nan'), "ground_contact_tolerance": 0.02}
        }])
        errs = validate_spec(s)
        assert any("finite" in e for e in errs)

    def test_inf_rejected_for_number(self):
        s = _minimal_spec(targets=[{
            "target_id": "A", "root_object_name": "r", "expected_root_type": "E",
            "geometry_scope": "SELF_MESH",
            "ground_contact": {"ground_z": float('inf'), "ground_contact_tolerance": 0.02}
        }])
        errs = validate_spec(s)
        assert any("finite" in e for e in errs)

    def test_euler_nan_component_rejected(self):
        s = _minimal_spec(targets=[{
            "target_id": "A", "root_object_name": "r", "expected_root_type": "E",
            "geometry_scope": "SELF_MESH",
            "rotation": {"expected_world_rotation_euler_degrees": [0, float('nan'), 0]}
        }])
        errs = validate_spec(s)
        assert any("finite" in e for e in errs)

    def test_screen_bbox_nan_rejected(self):
        s = _minimal_spec(projection_groups=[{
            "group_id": "g", "target_ids": ["CHR_TEST"], "additional_object_names": [],
            "camera_object_name": "C",
            "minimum_visible_projected_corner_count": 1,
            "required_screen_bbox": {"min_left": float('nan'), "max_right": 1, "min_bottom": 0, "max_top": 1},
            "require_camera_outside_world_bbox": False
        }])
        errs = validate_spec(s)
        assert any("finite" in e for e in errs)

    def test_mvc_bool_rejected(self):
        s = _minimal_spec(targets=[{
            "target_id": "A", "root_object_name": "r", "expected_root_type": "E",
            "geometry_scope": "SELF_MESH",
            "camera_check": {
                "camera_object_name": "C",
                "minimum_visible_projected_corner_count": True,
                "required_screen_bbox": {"min_left": 0, "max_right": 1, "min_bottom": 0, "max_top": 1}
            }
        }])
        errs = validate_spec(s)
        assert any("integer" in e for e in errs)


# ════════════════ Quaternion ════════════════

class TestQuaternion:
    def test_zero_degrees(self):
        q = (1.0, 0.0, 0.0, 0.0)
        assert quaternion_min_angle_degrees(q, q) == pytest.approx(0.0)

    def test_90_degrees_z(self):
        q1 = (1.0, 0.0, 0.0, 0.0)
        q2 = (math.sqrt(0.5), 0.0, 0.0, math.sqrt(0.5))
        assert quaternion_min_angle_degrees(q1, q2) == pytest.approx(90.0, abs=0.01)

    def test_180_degrees(self):
        q1 = (1.0, 0.0, 0.0, 0.0)
        q2 = (0.0, 0.0, 0.0, 1.0)
        assert quaternion_min_angle_degrees(q1, q2) == pytest.approx(180.0, abs=0.01)

    def test_negative_equivalence(self):
        q1 = (1.0, 0.0, 0.0, 0.0)
        q2 = (-1.0, 0.0, 0.0, 0.0)
        assert quaternion_min_angle_degrees(q1, q2) == pytest.approx(0.0)

    def test_scaled_non_unit_quaternion_zero(self):
        """Scale both quaternions by same factor → still 0°."""
        q = (2.0, 0.0, 0.0, 0.0)
        assert quaternion_min_angle_degrees(q, q) == pytest.approx(0.0)

    def test_scaled_non_unit_90_degrees(self):
        """Non-unit quaternions representing 90° rotation."""
        q1 = (3.0, 0.0, 0.0, 0.0)
        q2 = (0.0, 0.0, 0.0, 3.0)
        assert quaternion_min_angle_degrees(q1, q2) == pytest.approx(180.0, abs=0.01)

    def test_large_scale_same_rotation(self):
        q = (1000.0, 0.0, 0.0, 0.0)
        assert quaternion_min_angle_degrees(q, q) == pytest.approx(0.0)

    def test_tiny_scale_same_rotation(self):
        q = (0.001, 0.0, 0.0, 0.0)
        assert quaternion_min_angle_degrees(q, q) == pytest.approx(0.0)

    def test_nan_raises(self):
        with pytest.raises(NumericalValidationError):
            quaternion_min_angle_degrees((float('nan'), 0, 0, 0), (1, 0, 0, 0))

    def test_bool_component_raises(self):
        with pytest.raises(NumericalValidationError):
            quaternion_min_angle_degrees((True, 0, 0, 0), (1, 0, 0, 0))

    def test_zero_length_quaternion(self):
        with pytest.raises(NumericalValidationError):
            quaternion_min_angle_degrees((0, 0, 0, 0), (1, 0, 0, 0))


# ════════════════ Vector angle ════════════════

class TestVectorAngle:
    def test_zero_degrees(self):
        assert vector_angle_degrees((1, 0, 0), (1, 0, 0)) == pytest.approx(0.0)

    def test_90_degrees(self):
        assert vector_angle_degrees((1, 0, 0), (0, 1, 0)) == pytest.approx(90.0)

    def test_180_degrees(self):
        assert vector_angle_degrees((1, 0, 0), (-1, 0, 0)) == pytest.approx(180.0)

    def test_zero_length_raises(self):
        with pytest.raises(NumericalValidationError):
            vector_angle_degrees((0, 0, 0), (1, 0, 0))

    def test_nan_raises(self):
        with pytest.raises(NumericalValidationError):
            vector_angle_degrees((float('nan'), 0, 0), (1, 0, 0))


# ════════════════ Axis ════════════════

class TestAxis:
    def test_all_axes_valid(self):
        for a in AXIS_VALUES:
            assert len(axis_to_vector(a)) == 3

    def test_invalid_axis(self):
        with pytest.raises(NumericalValidationError):
            axis_to_vector("+W")


# ════════════════ Tolerance ════════════════

class TestTolerance:
    def test_exact(self):
        ok, err = is_within_absolute_tolerance(1.0, 1.0, 0.0)
        assert ok and err is None

    def test_boundary_pass(self):
        ok, _ = is_within_absolute_tolerance(1.0, 1.5, 0.5)
        assert ok

    def test_boundary_fail(self):
        ok, _ = is_within_absolute_tolerance(1.0, 1.50001, 0.5)
        assert not ok

    def test_negative_tolerance(self):
        ok, err = is_within_absolute_tolerance(1.0, 1.0, -0.1)
        assert not ok

    def test_nan_actual(self):
        ok, err = is_within_absolute_tolerance(float('nan'), 1.0, 0.1)
        assert not ok

    def test_bool_rejected(self):
        ok, err = is_within_absolute_tolerance(True, 1.0, 0.1)
        assert not ok


# ════════════════ Glob ════════════════

class TestGlob:
    def test_exact_match_case_insensitive(self):
        assert casefold_glob_match("Icosphere", "icosphere*")

    def test_wildcard(self):
        assert casefold_glob_match("Icosphere.001", "Icosphere*")

    def test_no_match(self):
        assert not casefold_glob_match("Cube", "Icosphere*")


# ════════════════ Sanitize ════════════════

class TestSanitize:
    def test_nan(self):
        assert sanitize_nonfinite(float('nan')) == "NaN"

    def test_inf(self):
        assert sanitize_nonfinite(float('inf')) == "Infinity"

    def test_neg_inf(self):
        assert sanitize_nonfinite(float('-inf')) == "-Infinity"

    def test_nested_dict(self):
        v = {"a": {"b": float('nan')}}
        assert sanitize_nonfinite(v)["a"]["b"] == "NaN"

    def test_list(self):
        assert sanitize_nonfinite([float('inf'), 1.0]) == ["Infinity", 1.0]

    def test_normal_float(self):
        assert sanitize_nonfinite(1.5) == 1.5


# ════════════════ Canonicalization ════════════════

class TestCanonicalization:
    def test_per_target_sorted(self):
        r = {"per_target_results": [{"target_id": "Z"}, {"target_id": "A"}]}
        c = canonicalize_phase3_result(r)
        assert c["per_target_results"][0]["target_id"] == "A"

    def test_projection_groups_sorted(self):
        r = {"projection_group_results": [{"group_id": "Z"}, {"group_id": "A"}]}
        c = canonicalize_phase3_result(r)
        assert c["projection_group_results"][0]["group_id"] == "A"

    def test_input_errors_sorted(self):
        r = {"input_errors": ["b", "a"]}
        c = canonicalize_phase3_result(r)
        assert c["input_errors"] == ["a", "b"]

    def test_name_lists_sorted_in_target(self):
        r = {"per_target_results": [{
            "target_id": "A",
            "required_children_found": ["Armature", "Body"],
            "forbidden_children_found": [],
            "unowned_meshes": ["Cube.002", "Cube.001"]
        }]}
        c = canonicalize_phase3_result(r)
        t = c["per_target_results"][0]
        assert t["required_children_found"] == ["Armature", "Body"]
        assert t["unowned_meshes"] == ["Cube.001", "Cube.002"]

    def test_empty_name_lists(self):
        r = {"per_target_results": [{"target_id": "A", "unowned_meshes": []}]}
        c = canonicalize_phase3_result(r)
        assert c["per_target_results"][0]["unowned_meshes"] == []

    def test_coordinate_order_preserved(self):
        r = {"per_target_results": [{"target_id": "A", "world_position": [3.0, 1.0, 2.0]}]}
        c = canonicalize_phase3_result(r)
        assert c["per_target_results"][0]["world_position"] == [3.0, 1.0, 2.0]

    # ── R2 Fix: new canonicalization tests ──

    def test_checks_nested_required_names_sorted(self):
        """required_* list inside per_target.checks dict is sorted."""
        r = {"per_target_results": [{
            "target_id": "A",
            "checks": {
                "hierarchy": {"result": "PASS",
                              "required_children_found": ["Armature", "Body", "Aux"]}
            }
        }]}
        c = canonicalize_phase3_result(r)
        found = c["per_target_results"][0]["checks"]["hierarchy"]["required_children_found"]
        assert found == ["Armature", "Aux", "Body"]

    def test_checks_nested_allowed_names_sorted(self):
        """allowed_* list inside per_target.checks dict is sorted."""
        r = {"per_target_results": [{
            "target_id": "A",
            "checks": {
                "hierarchy": {"result": "PASS",
                              "allowed_children_found": ["Zeta", "Alpha"]}
            }
        }]}
        c = canonicalize_phase3_result(r)
        found = c["per_target_results"][0]["checks"]["hierarchy"]["allowed_children_found"]
        assert found == ["Alpha", "Zeta"]

    def test_checks_nested_forbidden_names_sorted(self):
        """forbidden_* list inside per_target.checks dict is sorted."""
        r = {"per_target_results": [{
            "target_id": "A",
            "checks": {
                "unowned_mesh": {"result": "FAIL",
                                 "forbidden_descendants_found": ["Icosphere.002", "Icosphere.001"]}
            }
        }]}
        c = canonicalize_phase3_result(r)
        found = c["per_target_results"][0]["checks"]["unowned_mesh"]["forbidden_descendants_found"]
        assert found == ["Icosphere.001", "Icosphere.002"]

    def test_global_results_name_list_sorted(self):
        """Name list in global_results is sorted."""
        r = {"global_results": {"unowned_meshes": ["Z", "A", "M"]}}
        c = canonicalize_phase3_result(r)
        assert c["global_results"]["unowned_meshes"] == ["A", "M", "Z"]

    def test_projection_group_results_name_list_sorted(self):
        """Name list inside projection_group_results is sorted."""
        r = {"projection_group_results": [{
            "group_id": "G",
            "unowned_meshes": ["Charlie", "Alpha", "Bravo"]
        }]}
        c = canonicalize_phase3_result(r)
        assert c["projection_group_results"][0]["unowned_meshes"] == ["Alpha", "Bravo", "Charlie"]

    def test_deeply_nested_name_list_sorted(self):
        """Name list at arbitrary nesting depth is sorted."""
        r = {"per_target_results": [{
            "target_id": "A",
            "checks": {
                "collection": {
                    "details": {
                        "missing_required_collections": ["Z_col", "A_col", "M_col"]
                    }
                }
            }
        }]}
        c = canonicalize_phase3_result(r)
        found = (c["per_target_results"][0]["checks"]["collection"]
                  ["details"]["missing_required_collections"])
        assert found == ["A_col", "M_col", "Z_col"]

    def test_target_ids_order_preserved(self):
        """target_ids array preserves spec order."""
        r = {"projection_group_results": [{
            "group_id": "G",
            "target_ids": ["Z", "A", "M"]
        }]}
        c = canonicalize_phase3_result(r)
        assert c["projection_group_results"][0]["target_ids"] == ["Z", "A", "M"]

    def test_quaternion_order_preserved(self):
        """Quaternion array (4 numbers) not reordered."""
        r = {"per_target_results": [{
            "target_id": "A",
            "world_rotation_quaternion": [0.707, 0.0, 0.0, 0.707]
        }]}
        c = canonicalize_phase3_result(r)
        assert c["per_target_results"][0]["world_rotation_quaternion"] == [0.707, 0.0, 0.0, 0.707]

    def test_bbox_order_preserved(self):
        """bbox min/max arrays preserve definition order."""
        r = {"per_target_results": [{
            "target_id": "A",
            "bbox_min": [-1.0, -2.0, 0.0],
            "bbox_max": [3.0, 2.0, 5.0]
        }]}
        c = canonicalize_phase3_result(r)
        assert c["per_target_results"][0]["bbox_min"] == [-1.0, -2.0, 0.0]
        assert c["per_target_results"][0]["bbox_max"] == [3.0, 2.0, 5.0]

    def test_input_not_mutated(self):
        """Original result object is not modified."""
        r = {"per_target_results": [{
            "target_id": "Z",
            "unowned_meshes": ["c", "a", "b"]
        }]}
        canonicalize_phase3_result(r)
        assert r["per_target_results"][0]["unowned_meshes"] == ["c", "a", "b"]

    def test_idempotent(self):
        """Two consecutive canonicalizations produce identical output."""
        r = {"per_target_results": [{
            "target_id": "B",
            "unowned_meshes": ["c", "a", "b"]
        }, {
            "target_id": "A",
            "unowned_meshes": ["z", "m"]
        }]}
        c1 = canonicalize_phase3_result(r)
        c2 = canonicalize_phase3_result(c1)
        assert c1 == c2

    # ── 14A-FIX-CANONICALIZATION-02: new tests ──

    def test_checks_target_ids_preserved(self):
        """target_ids inside checks dict must NOT be sorted."""
        r = {"per_target_results": [{
            "target_id": "A",
            "checks": {
                "projection": {"target_ids": ["Z", "A", "M"]}
            }
        }]}
        c = canonicalize_phase3_result(r)
        assert c["per_target_results"][0]["checks"]["projection"]["target_ids"] == ["Z", "A", "M"]

    def test_checks_ordered_string_array_preserved(self):
        """A semantically ordered string list in checks must NOT be sorted."""
        r = {"per_target_results": [{
            "target_id": "A",
            "checks": {
                "action": {"expected_sequence": ["SECOND", "FIRST"]}
            }
        }]}
        c = canonicalize_phase3_result(r)
        assert c["per_target_results"][0]["checks"]["action"]["expected_sequence"] == ["SECOND", "FIRST"]

    def test_unwhitelisted_required_prefix_sorted(self):
        """New required_* field in global_results is sorted by pattern match."""
        r = {"global_results": {
            "required_object_names_found": ["Zulu", "alpha"]
        }}
        c = canonicalize_phase3_result(r)
        assert c["global_results"]["required_object_names_found"] == ["alpha", "Zulu"]

    def test_deeply_nested_allowed_prefix_sorted(self):
        """New allowed_* field in nested projection_group_results is sorted."""
        r = {"projection_group_results": [{
            "group_id": "G",
            "details": {
                "allowed_mesh_names_found": ["MESH_C", "mesh_a", "MESH_B"]
            }
        }]}
        c = canonicalize_phase3_result(r)
        assert (c["projection_group_results"][0]["details"]
                 ["allowed_mesh_names_found"] == ["mesh_a", "MESH_B", "MESH_C"])

    def test_deeply_nested_forbidden_prefix_sorted(self):
        """New forbidden_* field inside list-dict nesting is sorted."""
        r = {"per_target_results": [{
            "target_id": "A",
            "warnings": [{
                "category": "mesh",
                "forbidden_pattern_matches": ["Icosphere.003", "icosphere.001", "Icosphere.002"]
            }]
        }]}
        c = canonicalize_phase3_result(r)
        found = (c["per_target_results"][0]["warnings"][0]
                  ["forbidden_pattern_matches"])
        assert found == ["icosphere.001", "Icosphere.002", "Icosphere.003"]

    def test_empty_required_list_preserved(self):
        """Empty required_* list stays empty (not reordered)."""
        r = {"per_target_results": [{
            "target_id": "A",
            "required_children_found": []
        }]}
        c = canonicalize_phase3_result(r)
        assert c["per_target_results"][0]["required_children_found"] == []

    def test_nonstring_list_not_sorted_by_prefix(self):
        """required_* prefix on a non-string list does not trigger sorting."""
        r = {"per_target_results": [{
            "target_id": "A",
            "required_dimensions": [3.0, 1.0, 2.0]
        }]}
        c = canonicalize_phase3_result(r)
        assert c["per_target_results"][0]["required_dimensions"] == [3.0, 1.0, 2.0]


# ════════════════ Serialization ════════════════

class TestSerialization:
    def test_prefix_present(self):
        line = serialize_result_line(build_pass_result(_minimal_spec(), "a"*64))
        assert line.startswith(RESULT_PREFIX)

    def test_prefix_only_once(self):
        line = serialize_result_line(build_pass_result(_minimal_spec(), "a"*64))
        assert line.count(RESULT_PREFIX) == 1

    def test_valid_json(self):
        line = serialize_result_line(build_pass_result(_minimal_spec(), "a"*64))
        j = line[len(RESULT_PREFIX):].strip()
        assert json.loads(j)["result"] == "PASS"

    def test_nan_serialized(self):
        r = build_fail_result(_minimal_spec(), "a"*64)
        r["test_nan"] = float('nan')
        line = serialize_result_line(r)
        assert '"NaN"' in line

    def test_canonical_json_valid(self):
        line = serialize_result_line(build_pass_result(_minimal_spec(), "a" * 64))
        j = line[len(RESULT_PREFIX):].strip()
        parsed = json.loads(j)
        assert parsed["result"] == "PASS"

    def test_result_types(self):
        r_pass = build_pass_result(_minimal_spec(), "a" * 64)
        assert r_pass["result"] == "PASS"
        r_fail = build_fail_result(_minimal_spec(), "a" * 64)
        assert r_fail["result"] == "FAIL"
        r_err = build_error_result(_minimal_spec(), "a" * 64, ["test error"])
        assert r_err["result"] == "ERROR"


# ════════════════ Result builders ════════════════

class TestResultStructure:
    def test_pass_has_required_fields(self):
        r = build_pass_result(_minimal_spec(), "a"*64)
        for f in ("schema_version", "checker", "spec_sha256", "blend_path", "scene_name"):
            assert f in r
        assert r["result"] == "PASS"

    def test_pass_result_fields(self):
        r = build_pass_result(_minimal_spec(), "a" * 64)
        for f in ("schema_version", "checker", "spec_sha256", "blend_path", "scene_name"):
            assert f in r

    def test_error_result_has_errors(self):
        r = build_error_result(_minimal_spec(), "a" * 64, ["err1", "err2"])
        assert len(r["input_errors"]) == 2

    def test_fail_result_has_fail(self):
        r = build_fail_result(_minimal_spec(), "a" * 64)
        assert r["result"] == "FAIL"

    def test_fail_has_fail(self):
        assert build_fail_result(_minimal_spec(), "a"*64)["result"] == "FAIL"

    def test_error_has_errors(self):
        r = build_error_result(_minimal_spec(), "a"*64, ["e1", "e2"])
        assert len(r["input_errors"]) == 2
        assert r["result"] == "ERROR"


# ════════════════ Error boundary ════════════════

class TestErrorBoundary:
    def test_normal_return_passthrough(self):
        def ok(): return (0, {"result": "PASS"})
        code, res = error_boundary(ok)
        assert code == 0
        assert res["result"] == "PASS"

    def test_exception_trapped_as_error(self):
        def boom(): raise ValueError("test boom")
        code, res = error_boundary(boom)
        assert code == EXIT_ERROR
        assert res["result"] == "ERROR"
        assert any("ValueError" in e for e in res["input_errors"])


# ════════════════ Exceptions ════════════════

class TestExceptions:
    def test_axis_to_vector_raises_numerical(self):
        with pytest.raises(NumericalValidationError):
            axis_to_vector("INVALID")

    def test_vector_angle_zero_vec_raises(self):
        with pytest.raises(NumericalValidationError):
            vector_angle_degrees((0, 0, 0), (1, 0, 0))

    def test_quaternion_zero_vec_raises(self):
        with pytest.raises(NumericalValidationError):
            quaternion_min_angle_degrees((0, 0, 0, 0), (1, 0, 0, 0))

    def test_canonicalize_non_dict_raises(self):
        with pytest.raises(CanonicalizationError):
            canonicalize_phase3_result("not_a_dict")


# ════════════════ Constants ════════════════

class TestConstants:
    def test_exit_codes_distinct(self):
        assert EXIT_PASS != EXIT_FAIL != EXIT_ERROR

    def test_geometry_scopes(self):
        for s in ("SELF_MESH", "DESCENDANT_MESHES", "SELF_AND_DESCENDANT_MESHES"):
            assert s in GEOMETRY_SCOPES

    def test_render_engines_include_eevee(self):
        assert "BLENDER_EEVEE_NEXT" in VALID_RENDER_ENGINES

    def test_all_axes_have_vectors(self):
        for a in AXIS_VALUES:
            v = axis_to_vector(a)
            assert len(v) == 3
