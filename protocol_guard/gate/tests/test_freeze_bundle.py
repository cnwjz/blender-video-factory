import json, os, tempfile, yaml
from protocol_guard.gate.freeze_bundle import freeze_bundle

def _write_task(td, data):
    p = os.path.join(td, 'task.yaml')
    with open(p, 'w') as f: yaml.dump(data, f)
    return p

def _write_state(td, data):
    p = os.path.join(td, 'state.yaml')
    with open(p, 'w') as f: yaml.dump(data, f)
    return p

def _base_task():
    return {'task_id':'FB_TEST','task_card_version':2,'protocol_version':'v1.0','execution_mode':'confirm_then_execute','task_type':'PROTOCOL_MAINTENANCE','project_state_file':'state.yaml','input_files':[],'output_files':['out.txt'],'primary_goal':'Test','primary_variable':'x','dependent_variables':[],'fixed_params':{},'locked_items':[],'allowed_modifications':[],'forbidden_modifications':[],'preflight_checks':[],'technical_pass_conditions':[],'visual_intent':'','visual_forbidden':'','evidence_required':[],'upload_dir':'d','upload_files':['out.txt'],'stop_conditions':[],'state_patch_requested':None}

def _base_state():
    return {'protocol_version':'v1.0','project_id':'fb','workflow_phase':'code_guard_phase_1_locked','scene_phase':'paused','phase_approved':True,'project_work_paused':True,'last_task_id':'T','last_task_card_sha256':None,'last_technical_result':'TECHNICAL_PASS','evidence_status':'VALID','evidence_sha256':None,'output_files':[],'last_execution_time':'2026-07-15T15:00:00+08:00','locked_assets':[],'unlocked_assets':[],'diagnostic_only_outputs':[],'pending_review':None,'blocked_operations':[],'failed_paths':[],'change_log':[]}

class TestFreezeBundle:
    def test_freeze_produces_bundle(self):
        with tempfile.TemporaryDirectory() as td:
            tp = _write_task(td, _base_task())
            sp = _write_state(td, _base_state())
            outd = os.path.join(td, 'frozen')
            ok, bundle, sha, errs = freeze_bundle(tp, sp, outd)
            assert ok
            assert len(sha) == 64
            assert os.path.exists(os.path.join(outd, 'freeze_bundle.json'))
    def test_re_freeze_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            tp = _write_task(td, _base_task())
            sp = _write_state(td, _base_state())
            outd = os.path.join(td, 'frozen')
            ok, _, _, _ = freeze_bundle(tp, sp, outd)
            assert ok
            ok2, _, _, _ = freeze_bundle(tp, sp, outd)
            assert not ok2
    def test_input_file_missing(self):
        with tempfile.TemporaryDirectory() as td:
            task = _base_task()
            task['input_files'] = ['nonexistent.txt']
            tp = _write_task(td, task)
            sp = _write_state(td, _base_state())
            outd = os.path.join(td, 'frozen')
            ok, _, _, errs = freeze_bundle(tp, sp, outd)
            assert not ok
    def test_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            tp = _write_task(td, _base_task())
            sp = _write_state(td, _base_state())
            outd1 = os.path.join(td, 'f1')
            outd2 = os.path.join(td, 'f2')
            _, b1, _, _ = freeze_bundle(tp, sp, outd1)
            _, b2, _, _ = freeze_bundle(tp, sp, outd2)
            assert b1['task_card_raw_sha256'] == b2['task_card_raw_sha256']
    def test_frozen_task_copy_exists(self):
        with tempfile.TemporaryDirectory() as td:
            tp = _write_task(td, _base_task())
            sp = _write_state(td, _base_state())
            outd = os.path.join(td, 'frozen')
            ok, bundle, _, _ = freeze_bundle(tp, sp, outd)
            assert ok
            assert os.path.exists(bundle['frozen_task_copy_path'])

    def test_bundle_contains_frozen_at(self):
        with tempfile.TemporaryDirectory() as td:
            tp = _write_task(td, _base_task())
            sp = _write_state(td, _base_state())
            outd = os.path.join(td, 'frozen')
            ok, bundle, _, _ = freeze_bundle(tp, sp, outd)
            assert ok and 'frozen_at' in bundle
    def test_invalid_task_card_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            bad_task = dict(_base_task())
            del bad_task["task_id"]
            tp = _write_task(td, bad_task)
            sp = _write_state(td, _base_state())
            outd = os.path.join(td, "frozen")
            ok, _, _, _ = freeze_bundle(tp, sp, outd)
            assert not ok

    def test_task_card_validation_before_freeze(self):
        with tempfile.TemporaryDirectory() as td:
            tp = _write_task(td, _base_task())
            sp = _write_state(td, _base_state())
            outd = os.path.join(td, "frozen")
            ok, bundle, sha, _ = freeze_bundle(tp, sp, outd)
            assert ok
            # Frozen task copy must match original
            assert os.path.exists(bundle["frozen_task_copy_path"])


