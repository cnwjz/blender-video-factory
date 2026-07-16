import json, os, tempfile, yaml, pytest
from protocol_guard.gate.freeze_bundle import freeze_bundle
from protocol_guard.gate.preflight import preflight, _normalize_path

def _write_task(td, data):
    p = os.path.join(td, 'task.yaml')
    with open(p, 'w') as f: yaml.dump(data, f)
    return p

def _write_state(td, data):
    p = os.path.join(td, 'state.yaml')
    with open(p, 'w') as f: yaml.dump(data, f)
    return p

def _write_json(td, name, data):
    p = os.path.join(td, name)
    with open(p, 'w') as f: json.dump(data, f)
    return p

def _base_task():
    return {'task_id':'PF_TEST','task_card_version':2,'protocol_version':'v1.0','execution_mode':'confirm_then_execute','task_type':'PROTOCOL_MAINTENANCE','project_state_file':'state.yaml','input_files':[],'output_files':['out.txt'],'primary_goal':'Test','primary_variable':'x','dependent_variables':[],'fixed_params':{},'locked_items':[],'allowed_modifications':[],'forbidden_modifications':[],'preflight_checks':[],'technical_pass_conditions':[],'visual_intent':'','visual_forbidden':'','evidence_required':[],'upload_dir':'d','upload_files':['out.txt'],'stop_conditions':[],'state_patch_requested':None}

def _base_state():
    return {'protocol_version':'v1.0','project_id':'pf','workflow_phase':'code_guard_phase_1_locked','scene_phase':'paused','phase_approved':True,'project_work_paused':True,'last_task_id':'T','last_task_card_sha256':None,'last_technical_result':'TECHNICAL_PASS','evidence_status':'VALID','evidence_sha256':None,'output_files':[],'last_execution_time':'2026-07-15T15:00:00+08:00','locked_assets':[],'unlocked_assets':[],'diagnostic_only_outputs':[],'pending_review':None,'blocked_operations':[],'failed_paths':[],'change_log':[]}

class TestPathNormalize:
    def test_absolute_rejected(self):
        with pytest.raises(ValueError): _normalize_path('C:\\absolute', 'D:\\root')
    def test_parent_traversal_rejected(self):
        with pytest.raises(ValueError): _normalize_path('../etc', 'D:\\root')
    def test_valid_relative_passes(self):
        assert _normalize_path('subdir/file.txt', 'D:\\root') == 'subdir/file.txt'
    def test_unc_rejected(self):
        with pytest.raises(ValueError): _normalize_path('\\\\server\\share\\file', 'D:\\root')
    def test_drive_relative_rejected(self):
        with pytest.raises(ValueError): _normalize_path('C:file.txt', 'D:\\root')

class TestPreflightGate:
    def test_preflight_runs(self):
        with tempfile.TemporaryDirectory() as td:
            tp = _write_task(td, _base_task())
            sp = _write_state(td, _base_state())
            fd = os.path.join(td, 'frozen')
            ok, bundle, sha, errs = freeze_bundle(tp, sp, fd)
            assert ok
            fb_path = os.path.join(fd, 'freeze_bundle.json')
            auth = {'authorization_id':'A1','task_id':'PF_TEST','task_card_sha256':bundle['task_card_raw_sha256'],'freeze_bundle_sha256':sha,'understand_record_sha256':'c'*64,'project_state_sha256':bundle['project_state_canonical_sha256'],'input_files_sha256':{},'requested_operation_ids':[],'allowed_modification_paths':[],'declared_output_paths':[],'scope':['preflight','mock_execute','finalize'],'issued_at':'2026-01-01T00:00:00Z','authorized_by':'USER','gpt_review_reference':'r'}
            ap = _write_json(td, 'auth.json', auth)
            cleared, errs = preflight(tp, sp, fb_path, ap, td)
            assert isinstance(cleared, bool)
    def test_phase_not_approved_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            state = dict(_base_state())
            state['phase_approved'] = False
            tp = _write_task(td, _base_task())
            sp = _write_state(td, state)
            fd = os.path.join(td, 'frozen')
            _, bundle, sha, _ = freeze_bundle(tp, sp, fd)
            fb_path = os.path.join(fd, 'freeze_bundle.json')
            auth = {'authorization_id':'A2','task_id':'PF_TEST','task_card_sha256':bundle['task_card_raw_sha256'],'freeze_bundle_sha256':sha,'understand_record_sha256':'c'*64,'project_state_sha256':bundle['project_state_canonical_sha256'],'input_files_sha256':{},'requested_operation_ids':[],'allowed_modification_paths':[],'declared_output_paths':[],'scope':['preflight','mock_execute','finalize'],'issued_at':'2026-01-01T00:00:00Z','authorized_by':'USER','gpt_review_reference':'r'}
            ap = _write_json(td, 'auth.json', auth)
            cleared, _ = preflight(tp, sp, fb_path, ap, td)
            assert not cleared
