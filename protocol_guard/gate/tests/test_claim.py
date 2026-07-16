import json, os, tempfile
from protocol_guard.gate.claim import create_claim

def _write_json(td, name, data):
    p = os.path.join(td, name)
    with open(p, 'w') as f: json.dump(data, f)
    return p

def _auth(aid='A1'):
    return {'authorization_id':aid,'task_id':'T','task_card_sha256':'a'*64,'freeze_bundle_sha256':'b'*64,'understand_record_sha256':'c'*64,'project_state_sha256':'d'*64,'input_files_sha256':{},'requested_operation_ids':[],'allowed_modification_paths':[],'declared_output_paths':[],'scope':['preflight','mock_execute','finalize'],'issued_at':'2026-01-01T00:00:00Z','authorized_by':'USER','gpt_review_reference':'r'}

class TestClaim:
    def test_atomic_create(self):
        with tempfile.TemporaryDirectory() as td:
            ap = _write_json(td, 'auth.json', _auth('A1'))
            ok, claim, cpath, errs = create_claim(ap, json.load(open(ap,'r')), td)
            assert ok
            assert os.path.exists(cpath)
            assert claim['authorization_id'] == 'A1'
            assert 'attempt_id' in claim

    def test_double_claim_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            ap = _write_json(td, 'auth.json', _auth('A2'))
            ok1, _, _, _ = create_claim(ap, json.load(open(ap,'r')), td)
            assert ok1
            ok2, _, _, _ = create_claim(ap, json.load(open(ap,'r')), td)
            assert not ok2

    def test_claim_required_fields(self):
        with tempfile.TemporaryDirectory() as td:
            ap = _write_json(td, 'auth.json', _auth('A3'))
            ok, claim, _, _ = create_claim(ap, json.load(open(ap,'r')), td)
            assert ok
            for f in ['authorization_id','authorization_sha256','attempt_id','task_id','claimed_at','process_id']:
                assert f in claim

    def test_claim_path_isolation(self):
        with tempfile.TemporaryDirectory() as td:
            ap1 = _write_json(td, 'a1.json', _auth('ISO1'))
            ap2 = _write_json(td, 'a2.json', _auth('ISO2'))
            ok1, _, cp1, _ = create_claim(ap1, json.load(open(ap1,"r")), td)
            ok2, _, cp2, _ = create_claim(ap2, json.load(open(ap2,"r")), td)
            assert ok1 and ok2
            assert cp1 != cp2

    def test_different_auth_different_attempt(self):
        with tempfile.TemporaryDirectory() as td:
            ap1 = _write_json(td, 'a1.json', _auth('C1'))
            ap2 = _write_json(td, 'a2.json', _auth('C2'))
            _, c1, _, _ = create_claim(ap1, json.load(open(ap1,"r")), td)
            _, c2, _, _ = create_claim(ap2, json.load(open(ap2,"r")), td)
            assert c1['attempt_id'] != c2['attempt_id']
    def test_claim_without_validated_auth_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            ap = _write_json(td, "auth.json", _auth("C5"))
            ok, _, _, errs = create_claim(ap, None, td)
            assert not ok

    def test_corrupted_claim_human_audit(self):
        with tempfile.TemporaryDirectory() as td:
            ap = _write_json(td, "auth.json", _auth("C6"))
            ad = json.load(open(ap, "r"))
            ok1, _, cp, _ = create_claim(ap, ad, td)
            assert ok1
            # Write invalid JSON
            with open(cp, "w") as f: f.write("not json")
            ok2, _, _, errs = create_claim(ap, ad, td)
            assert not ok2
            assert any("HUMAN_AUDIT" in e for e in errs)


