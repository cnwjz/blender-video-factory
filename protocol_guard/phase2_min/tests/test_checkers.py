"""Tests for Phase 2 Min — baseline B created BEFORE approval artifacts."""

import hashlib, json, os, shutil, subprocess, tempfile, yaml, pytest

from protocol_guard.phase2_min.change_scope_check import change_scope_check
from protocol_guard.phase2_min.upload_package_check import upload_package_check
from protocol_guard.phase2_min.io_utils import sha256_file, normalize_path


# ════════════════════════ Git helpers ════════════════════════
def _git_init(td):
    subprocess.run(["git", "init"], cwd=td, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=td, capture_output=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=td, capture_output=True)
    return td

def _git_commit(repo, msg):
    subprocess.run(["git", "add", "-A"], cwd=repo, capture_output=True)
    subprocess.run(["git", "commit", "-m", msg], cwd=repo, capture_output=True)

def _git_add(repo, path):
    subprocess.run(["git", "add", path], cwd=repo, capture_output=True)

def _write(repo, path, content):
    fp = os.path.join(repo, path)
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    with open(fp, "w") as f: f.write(content)
    return fp

def _task_dict(task_id, fixed_params):
    return {
        "task_id": task_id, "task_card_version": 2, "protocol_version": "v1.0",
        "execution_mode": "confirm_then_execute", "task_type": "PROTOCOL_MAINTENANCE",
        "project_state_file": "state.yaml", "input_files": [], "output_files": ["out.txt"],
        "primary_variable": "x", "dependent_variables": [], "fixed_params": fixed_params,
        "locked_items": [], "allowed_modifications": [], "forbidden_modifications": [],
        "preflight_checks": [], "technical_pass_conditions": [],
        "visual_intent": "", "visual_forbidden": "", "evidence_required": [],
        "upload_dir": "d", "upload_files": ["out.txt"], "stop_conditions": [],
        "primary_goal": "test", "state_patch_requested": None,
    }


# ════════════════════ Unified CS Helper ════════════════════════
def _cs_fixture(td, task_subdir=None, extra_allowed=None, denied=None, protected=None,
                worktree_clean=True, target_changes=None):
    """Unified Change Scope fixture.

    Lifecycle:
      1. Init repo. Create ok.txt. Commit baseline B.
      2. Create policy.json, task.yaml, frozen/ (AFTER B, as allowed artifacts).
      3. Apply target_changes to test the checker against.
      4. Return (repo_root, baseline_sha, task_path, frozen_dir, policy_path).
    """
    repo = _git_init(td)

    # Step 1: business file + baseline B
    _write(repo, "ok.txt", "ok")
    _git_commit(repo, "baseline B — business file only")
    bc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()

    # Step 2: policy
    allowed = [
        {"path": "policy.json", "path_type": "file"},
        {"path": "frozen", "path_type": "directory"},
    ]
    task_rel = "task.yaml"
    if task_subdir:
        task_rel = f"{task_subdir}/task.yaml"
        allowed.append({"path": task_subdir, "path_type": "directory"})
    else:
        allowed.append({"path": "task.yaml", "path_type": "file"})

    if extra_allowed:
        allowed.extend(extra_allowed)

    policy = {"schema_version": "1", "task_id": "TASK_CS",
              "allowed_paths": allowed,
              "denied_paths": denied or [],
              "protected_files": protected or []}
    pp = _write(repo, "policy.json", json.dumps(policy))

    # Step 3: task + frozen
    task = _task_dict("TASK_CS", {
        "baseline_commit_sha": bc,
        "policy_path": "policy.json",
        "policy_sha256": sha256_file(pp),
        "worktree_clean_at_approval": worktree_clean,
    })
    tp = os.path.join(repo, task_rel)
    os.makedirs(os.path.dirname(tp), exist_ok=True)
    with open(tp, "w") as f: yaml.dump(task, f)

    fd = os.path.join(repo, "frozen")
    os.makedirs(fd, exist_ok=True)
    shutil.copy2(tp, os.path.join(fd, "frozen_task.yaml"))
    sha = hashlib.sha256(open(tp, "rb").read()).hexdigest()
    with open(os.path.join(fd, "frozen_task.sha256"), "w") as f: f.write(sha + "\n")

    # Step 4: apply target changes
    if target_changes:
        target_changes(repo)

    return repo, bc, tp, fd, pp


# ════════════════════ Path Safety ════════════════════════
class TestPathSafety:
    def test_abs_rejected(self):
        with pytest.raises(ValueError): normalize_path("C:\\evil")
    def test_parent_rejected(self):
        with pytest.raises(ValueError): normalize_path("../etc")
    def test_unc_rejected(self):
        with pytest.raises(ValueError): normalize_path("\\\\s\\share")
    def test_drive_rel_rejected(self):
        with pytest.raises(ValueError): normalize_path("C:file.txt")
    def test_normal_ok(self):
        assert normalize_path("a/b.txt") == "a/b.txt"


# ════════════════════ Change Scope Check ════════════════════
class TestChangeScopeCheck:
    # ── PASS ──
    def test_clean_worktree_pass(self):
        with tempfile.TemporaryDirectory() as td:
            _, _, tp, fd, _ = _cs_fixture(td)
            code, result = change_scope_check(tp, fd)
            assert code == 0
            assert result["result"] == "PASS"

    def test_task_in_root_ok(self):
        with tempfile.TemporaryDirectory() as td:
            _, _, tp, fd, _ = _cs_fixture(td, task_subdir=None)
            code, _ = change_scope_check(tp, fd)
            assert code == 0

    def test_task_in_tasks_dir_ok(self):
        with tempfile.TemporaryDirectory() as td:
            _, _, tp, fd, _ = _cs_fixture(td, task_subdir="tasks")
            code, _ = change_scope_check(tp, fd)
            assert code == 0

    def test_task_in_nested_dir_ok(self):
        with tempfile.TemporaryDirectory() as td:
            _, _, tp, fd, _ = _cs_fixture(td, task_subdir="tasks/nested")
            code, _ = change_scope_check(tp, fd)
            assert code == 0

    # ── FAIL ──
    def test_oos_committed_fail(self):
        def chg(repo):
            _write(repo, "bad.txt", "bad")
            _git_commit(repo, "bad commit")
        with tempfile.TemporaryDirectory() as td:
            _, _, tp, fd, _ = _cs_fixture(td, denied=[{"path": "bad.txt", "path_type": "file"}],
                                           target_changes=chg)
            code, result = change_scope_check(tp, fd)
            assert code == 1
            assert result["result"] == "FAIL"

    def test_protected_sha_mismatch_fail(self):
        def chg(repo):
            _write(repo, "secret.key", "tampered")
        with tempfile.TemporaryDirectory() as td:
            _, _, tp, fd, _ = _cs_fixture(td,
                extra_allowed=[{"path": "secret.key", "path_type": "file"}],
                protected=[{"path": "secret.key", "sha256": hashlib.sha256(b"original").hexdigest()}],
                target_changes=lambda r: _write(r, "secret.key", "original"))
            chg(td)  # tamper after initial write
            # Re-do: write original as baseline state, then tamper
            pass
        # Use a manual setup for this one
        with tempfile.TemporaryDirectory() as td:
            repo = _git_init(td)
            _write(repo, "ok.txt", "ok")
            _write(repo, "secret.key", "original")
            _git_commit(repo, "baseline B")
            bc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()
            policy = {"schema_version": "1", "task_id": "TASK_CS",
                "allowed_paths": [{"path": "ok.txt", "path_type": "file"},
                    {"path": "policy.json", "path_type": "file"},
                    {"path": "task.yaml", "path_type": "file"},
                    {"path": "frozen", "path_type": "directory"},
                    {"path": "secret.key", "path_type": "file"}],
                "denied_paths": [],
                "protected_files": [{"path": "secret.key", "sha256": hashlib.sha256(b"original").hexdigest()}]}
            pp = _write(repo, "policy.json", json.dumps(policy))
            task = _task_dict("TASK_CS", {"baseline_commit_sha": bc, "policy_path": "policy.json",
                "policy_sha256": sha256_file(pp), "worktree_clean_at_approval": True})
            tp = os.path.join(repo, "task.yaml")
            with open(tp, "w") as f: yaml.dump(task, f)
            fd = os.path.join(repo, "frozen")
            os.makedirs(fd, exist_ok=True)
            shutil.copy2(tp, os.path.join(fd, "frozen_task.yaml"))
            sha = hashlib.sha256(open(tp, "rb").read()).hexdigest()
            with open(os.path.join(fd, "frozen_task.sha256"), "w") as f: f.write(sha + "\n")
            _write(repo, "secret.key", "tampered")
            code, result = change_scope_check(tp, fd)
            assert code == 1
            assert result["result"] == "FAIL"

    # ── ERROR ──
    def test_worktree_clean_false_error(self):
        with tempfile.TemporaryDirectory() as td:
            _, _, tp, fd, _ = _cs_fixture(td, worktree_clean=False)
            code, result = change_scope_check(tp, fd)
            assert code == 2
            assert result["result"] == "ERROR"

    def test_policy_sha_changed_error(self):
        with tempfile.TemporaryDirectory() as td:
            _, _, tp, fd, _ = _cs_fixture(td)
            # Corrupt the policy SHA in the task
            task2 = yaml.safe_load(open(tp))
            task2["fixed_params"]["policy_sha256"] = "f" * 64
            with open(tp, "w") as f: yaml.dump(task2, f)
            shutil.copy2(tp, os.path.join(fd, "frozen_task.yaml"))
            sha = hashlib.sha256(open(tp, "rb").read()).hexdigest()
            with open(os.path.join(fd, "frozen_task.sha256"), "w") as f: f.write(sha + "\n")
            code, result = change_scope_check(tp, fd)
            assert code == 2
            assert result["result"] == "ERROR"

    def test_baseline_not_found_error(self):
        with tempfile.TemporaryDirectory() as td:
            _, _, tp, fd, _ = _cs_fixture(td)
            task2 = yaml.safe_load(open(tp))
            task2["fixed_params"]["baseline_commit_sha"] = "deadbeef" * 5
            with open(tp, "w") as f: yaml.dump(task2, f)
            shutil.copy2(tp, os.path.join(fd, "frozen_task.yaml"))
            sha = hashlib.sha256(open(tp, "rb").read()).hexdigest()
            with open(os.path.join(fd, "frozen_task.sha256"), "w") as f: f.write(sha + "\n")
            code, result = change_scope_check(tp, fd)
            assert code == 2
            assert result["result"] == "ERROR"

    def test_nongit_dir_error(self):
        with tempfile.TemporaryDirectory() as td:
            task = _task_dict("TASK_CS", {"baseline_commit_sha": "x" * 40, "policy_path": "p.json",
                "policy_sha256": "f" * 64, "worktree_clean_at_approval": True})
            tp = os.path.join(td, "task.yaml")
            with open(tp, "w") as f: yaml.dump(task, f)
            fd = os.path.join(td, "frozen")
            os.makedirs(fd, exist_ok=True)
            shutil.copy2(tp, os.path.join(fd, "frozen_task.yaml"))
            sha = hashlib.sha256(open(tp, "rb").read()).hexdigest()
            with open(os.path.join(fd, "frozen_task.sha256"), "w") as f: f.write(sha + "\n")
            code, result = change_scope_check(tp, fd)
            assert code == 2
            assert result["result"] == "ERROR"

    def test_no_file_writes(self):
        with tempfile.TemporaryDirectory() as td:
            repo, _, tp, fd, _ = _cs_fixture(td)
            before = set()
            for dp, _, fns in os.walk(repo):
                for fn in fns: before.add(os.path.join(dp, fn))
            change_scope_check(tp, fd)
            after = set()
            for dp, _, fns in os.walk(repo):
                for fn in fns: after.add(os.path.join(dp, fn))
            assert before == after


# ════════════════════ Upload Package Check ════════════════════
class TestUploadPackageCheck:
    def _up_setup(self, td, spec_entries, manifest_entries=None, task_subdir=None, extra_pkg=None):
        repo = _git_init(td)
        _write(repo, "ok.txt", "ok")
        _git_commit(repo, "baseline B")
        upload_dir = os.path.join(repo, "reviews", "UPLOAD_NEXT")
        src_dir = os.path.join(repo, "reports")
        os.makedirs(upload_dir, exist_ok=True)
        os.makedirs(src_dir, exist_ok=True)
        for e in spec_entries:
            sp = os.path.join(repo, e["source_path"])
            os.makedirs(os.path.dirname(sp), exist_ok=True)
            content = e.get("content", "payload")
            with open(sp, "w") as f: f.write(content)
            pp = os.path.join(upload_dir, e["package_path"])
            os.makedirs(os.path.dirname(pp), exist_ok=True)
            with open(pp, "w") as f: f.write(content)
        if extra_pkg:
            for epf, content in extra_pkg.items():
                ep = os.path.join(upload_dir, epf)
                os.makedirs(os.path.dirname(ep), exist_ok=True)
                with open(ep, "w") as f: f.write(content)
        spec_data = {"schema_version": "1", "task_id": "TASK_UP",
                     "manifest_filename": "UPLOAD_MANIFEST.json",
                     "entries": [{"package_path": e["package_path"], "source_path": e["source_path"]} for e in spec_entries]}
        sp = _write(repo, "upload_spec.json", json.dumps(spec_data))
        me = manifest_entries if manifest_entries else [
            {"package_path": e["package_path"], "source_path": e["source_path"],
             "sha256": sha256_file(os.path.join(upload_dir, e["package_path"]))} for e in spec_entries]
        _write(repo, "reviews/UPLOAD_NEXT/UPLOAD_MANIFEST.json", json.dumps(
            {"schema_version": "1", "task_id": "TASK_UP", "entries": me}))
        task = _task_dict("TASK_UP", {"upload_spec_path": "upload_spec.json",
                          "upload_spec_sha256": sha256_file(sp)})
        task_dir = os.path.join(repo, task_subdir) if task_subdir else repo
        os.makedirs(task_dir, exist_ok=True)
        tp = os.path.join(task_dir, "task.yaml")
        with open(tp, "w") as f: yaml.dump(task, f)
        fd = os.path.join(repo, "frozen")
        os.makedirs(fd, exist_ok=True)
        shutil.copy2(tp, os.path.join(fd, "frozen_task.yaml"))
        sha = hashlib.sha256(open(tp, "rb").read()).hexdigest()
        with open(os.path.join(fd, "frozen_task.sha256"), "w") as f: f.write(sha + "\n")
        return tp, fd, repo

    def test_valid_pass(self):
        with tempfile.TemporaryDirectory() as td:
            tp, fd, _ = self._up_setup(td, [{"package_path": "r.md", "source_path": "reports/r.md"}])
            code, result = upload_package_check(tp, fd)
            assert code == 0
            assert result["result"] == "PASS"

    def test_tasks_dir_ok(self):
        with tempfile.TemporaryDirectory() as td:
            tp, fd, _ = self._up_setup(td, [{"package_path": "r.md", "source_path": "reports/r.md"}], task_subdir="tasks")
            code, _ = upload_package_check(tp, fd)
            assert code == 0

    def test_nested_dir_ok(self):
        with tempfile.TemporaryDirectory() as td:
            tp, fd, _ = self._up_setup(td, [{"package_path": "r.md", "source_path": "reports/r.md"}], task_subdir="tasks/nested")
            code, _ = upload_package_check(tp, fd)
            assert code == 0

    def test_hash_mismatch_fail(self):
        with tempfile.TemporaryDirectory() as td:
            tp, fd, _ = self._up_setup(td, [{"package_path": "r.md", "source_path": "reports/r.md"}],
                manifest_entries=[{"package_path": "r.md", "source_path": "reports/r.md", "sha256": "f" * 64}])
            code, _ = upload_package_check(tp, fd)
            assert code == 1

    def test_manifest_self_ref_fail(self):
        with tempfile.TemporaryDirectory() as td:
            tp, fd, _ = self._up_setup(td, [{"package_path": "UPLOAD_MANIFEST.json", "source_path": "reports/r.md"}])
            code, _ = upload_package_check(tp, fd)
            assert code == 1

    def test_source_missing_fail(self):
        with tempfile.TemporaryDirectory() as td:
            repo = _git_init(td)
            _write(repo, "ok.txt", "ok")
            _git_commit(repo, "baseline B")
            upload_dir = os.path.join(repo, "reviews", "UPLOAD_NEXT")
            os.makedirs(upload_dir, exist_ok=True)
            _write(repo, "reviews/UPLOAD_NEXT/r.md", "x")
            spec_data = {"schema_version": "1", "task_id": "TASK_UP",
                         "manifest_filename": "UPLOAD_MANIFEST.json",
                         "entries": [{"package_path": "r.md", "source_path": "missing/s.txt"}]}
            sp = _write(repo, "upload_spec.json", json.dumps(spec_data))
            _write(repo, "reviews/UPLOAD_NEXT/UPLOAD_MANIFEST.json", json.dumps(
                {"schema_version": "1", "task_id": "TASK_UP", "entries": [
                    {"package_path": "r.md", "source_path": "missing/s.txt", "sha256": sha256_file(os.path.join(upload_dir, "r.md"))}]}))
            task = _task_dict("TASK_UP", {"upload_spec_path": "upload_spec.json", "upload_spec_sha256": sha256_file(sp)})
            tp = os.path.join(repo, "task.yaml")
            with open(tp, "w") as f: yaml.dump(task, f)
            fd = os.path.join(repo, "frozen")
            os.makedirs(fd, exist_ok=True)
            shutil.copy2(tp, os.path.join(fd, "frozen_task.yaml"))
            sha = hashlib.sha256(open(tp, "rb").read()).hexdigest()
            with open(os.path.join(fd, "frozen_task.sha256"), "w") as f: f.write(sha + "\n")
            code, result = upload_package_check(tp, fd)
            assert code == 1

    def test_extra_file_fail(self):
        with tempfile.TemporaryDirectory() as td:
            tp, fd, _ = self._up_setup(td, [{"package_path": "r.md", "source_path": "reports/r.md"}],
                                        extra_pkg={"rogue.txt": "evil"})
            code, _ = upload_package_check(tp, fd)
            assert code == 1

    def test_spec_sha_changed_error(self):
        with tempfile.TemporaryDirectory() as td:
            repo = _git_init(td)
            _write(repo, "ok.txt", "ok")
            _git_commit(repo, "baseline B")
            os.makedirs(os.path.join(repo, "reviews", "UPLOAD_NEXT"), exist_ok=True)
            sp = _write(repo, "spec.json", json.dumps({"schema_version": "1", "task_id": "TASK_UP",
                "manifest_filename": "UPLOAD_MANIFEST.json", "entries": []}))
            task = _task_dict("TASK_UP", {"upload_spec_path": "spec.json", "upload_spec_sha256": "f" * 64})
            tp = os.path.join(repo, "task.yaml")
            with open(tp, "w") as f: yaml.dump(task, f)
            fd = os.path.join(repo, "frozen")
            os.makedirs(fd, exist_ok=True)
            shutil.copy2(tp, os.path.join(fd, "frozen_task.yaml"))
            sha = hashlib.sha256(open(tp, "rb").read()).hexdigest()
            with open(os.path.join(fd, "frozen_task.sha256"), "w") as f: f.write(sha + "\n")
            code, result = upload_package_check(tp, fd)
            assert code == 2

    def test_dup_package_path_error(self):
        with tempfile.TemporaryDirectory() as td:
            repo = _git_init(td)
            _write(repo, "ok.txt", "ok")
            _git_commit(repo, "baseline B")
            upload_dir = os.path.join(repo, "reviews", "UPLOAD_NEXT")
            os.makedirs(upload_dir, exist_ok=True)
            _write(repo, "reviews/UPLOAD_NEXT/a.md", "x")
            sp = _write(repo, "spec.json", json.dumps({"schema_version": "1", "task_id": "TASK_UP",
                "manifest_filename": "UPLOAD_MANIFEST.json", "entries": [
                    {"package_path": "a.md", "source_path": "s/a.md"},
                    {"package_path": "a.md", "source_path": "s/a.md"}]}))
            task = _task_dict("TASK_UP", {"upload_spec_path": "spec.json", "upload_spec_sha256": sha256_file(sp)})
            tp = os.path.join(repo, "task.yaml")
            with open(tp, "w") as f: yaml.dump(task, f)
            fd = os.path.join(repo, "frozen")
            os.makedirs(fd, exist_ok=True)
            shutil.copy2(tp, os.path.join(fd, "frozen_task.yaml"))
            sha = hashlib.sha256(open(tp, "rb").read()).hexdigest()
            with open(os.path.join(fd, "frozen_task.sha256"), "w") as f: f.write(sha + "\n")
            code, result = upload_package_check(tp, fd)
            assert code == 2

    def test_nongit_error(self):
        with tempfile.TemporaryDirectory() as td:
            task = _task_dict("TASK_UP", {"upload_spec_path": "s.json", "upload_spec_sha256": "f" * 64})
            tp = os.path.join(td, "task.yaml")
            with open(tp, "w") as f: yaml.dump(task, f)
            fd = os.path.join(td, "frozen")
            os.makedirs(fd, exist_ok=True)
            shutil.copy2(tp, os.path.join(fd, "frozen_task.yaml"))
            sha = hashlib.sha256(open(tp, "rb").read()).hexdigest()
            with open(os.path.join(fd, "frozen_task.sha256"), "w") as f: f.write(sha + "\n")
            code, result = upload_package_check(tp, fd)
            assert code == 2

    def test_no_file_writes(self):
        with tempfile.TemporaryDirectory() as td:
            tp, fd, repo = self._up_setup(td, [{"package_path": "r.md", "source_path": "reports/r.md"}])
            before = set()
            for dp, _, fns in os.walk(repo):
                for fn in fns: before.add(os.path.join(dp, fn))
            upload_package_check(tp, fd)
            after = set()
            for dp, _, fns in os.walk(repo):
                for fn in fns: after.add(os.path.join(dp, fn))
            assert before == after


# ════════════════════ Adversarial ════════════════════
class TestAdversarial:
    def test_staged_oos_add_fail(self):
        def chg(repo):
            _write(repo, "rogue.txt", "bad")
            _git_add(repo, "rogue.txt")
        with tempfile.TemporaryDirectory() as td:
            _, _, tp, fd, _ = _cs_fixture(td, target_changes=chg)
            code, result = change_scope_check(tp, fd)
            assert code == 1
            assert result["result"] == "FAIL"

    def test_staged_denied_delete_fail(self):
        def chg(repo):
            _write(repo, "denied.txt", "x")
            _git_add(repo, "denied.txt")
            _git_commit(repo, "add denied")  # commit after baseline
            os.remove(os.path.join(repo, "denied.txt"))
            _git_add(repo, "denied.txt")
        with tempfile.TemporaryDirectory() as td:
            _, _, tp, fd, _ = _cs_fixture(td, denied=[{"path": "denied.txt", "path_type": "file"}],
                extra_allowed=[{"path": "denied.txt", "path_type": "file"}],
                target_changes=chg)
            code, result = change_scope_check(tp, fd)
            assert code == 1
            assert result["result"] == "FAIL"

    def test_unstaged_delete_fail(self):
        def chg(repo):
            _write(repo, "other.txt", "x")
            _git_add(repo, "other.txt")
            _git_commit(repo, "add other")
            os.remove(os.path.join(repo, "other.txt"))
        with tempfile.TemporaryDirectory() as td:
            _, _, tp, fd, _ = _cs_fixture(td, target_changes=chg)
            code, result = change_scope_check(tp, fd)
            assert code == 1
            assert result["result"] == "FAIL"

    def test_committed_oos_fail(self):
        def chg(repo):
            _write(repo, "bad.txt", "bad")
            _git_commit(repo, "bad commit")
        with tempfile.TemporaryDirectory() as td:
            _, _, tp, fd, _ = _cs_fixture(td, denied=[{"path": "bad.txt", "path_type": "file"}],
                                           target_changes=chg)
            code, result = change_scope_check(tp, fd)
            assert code == 1
            assert result["result"] == "FAIL"

    def test_protected_sha_wrong_fail(self):
        with tempfile.TemporaryDirectory() as td:
            repo = _git_init(td)
            _write(repo, "ok.txt", "ok")
            _write(repo, "secret.key", "original")
            _git_commit(repo, "baseline B")
            bc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()
            policy = {"schema_version": "1", "task_id": "TASK_ADV",
                "allowed_paths": [
                    {"path": "ok.txt", "path_type": "file"},
                    {"path": "policy.json", "path_type": "file"},
                    {"path": "task.yaml", "path_type": "file"},
                    {"path": "frozen", "path_type": "directory"},
                    {"path": "secret.key", "path_type": "file"}],
                "denied_paths": [],
                "protected_files": [{"path": "secret.key", "sha256": hashlib.sha256(b"original").hexdigest()}]}
            pp = _write(repo, "policy.json", json.dumps(policy))
            task = _task_dict("TASK_ADV", {"baseline_commit_sha": bc, "policy_path": "policy.json",
                "policy_sha256": sha256_file(pp), "worktree_clean_at_approval": True})
            tp = os.path.join(repo, "task.yaml")
            with open(tp, "w") as f: yaml.dump(task, f)
            fd = os.path.join(repo, "frozen")
            os.makedirs(fd, exist_ok=True)
            shutil.copy2(tp, os.path.join(fd, "frozen_task.yaml"))
            sha = hashlib.sha256(open(tp, "rb").read()).hexdigest()
            with open(os.path.join(fd, "frozen_task.sha256"), "w") as f: f.write(sha + "\n")
            _write(repo, "secret.key", "tampered")
            code, result = change_scope_check(tp, fd)
            assert code == 1
            assert result["result"] == "FAIL"

    def test_worktree_clean_false_error(self):
        with tempfile.TemporaryDirectory() as td:
            _, _, tp, fd, _ = _cs_fixture(td, worktree_clean=False)
            code, result = change_scope_check(tp, fd)
            assert code == 2
            assert result["result"] == "ERROR"

    def test_policy_sha_wrong_error(self):
        with tempfile.TemporaryDirectory() as td:
            _, _, tp, fd, _ = _cs_fixture(td)
            task2 = yaml.safe_load(open(tp))
            task2["fixed_params"]["policy_sha256"] = "b" * 64
            with open(tp, "w") as f: yaml.dump(task2, f)
            shutil.copy2(tp, os.path.join(fd, "frozen_task.yaml"))
            sha = hashlib.sha256(open(tp, "rb").read()).hexdigest()
            with open(os.path.join(fd, "frozen_task.sha256"), "w") as f: f.write(sha + "\n")
            code, result = change_scope_check(tp, fd)
            assert code == 2
            assert result["result"] == "ERROR"

    def test_nongit_error(self):
        with tempfile.TemporaryDirectory() as td:
            task = _task_dict("TASK_ADV", {"baseline_commit_sha": "x" * 40, "policy_path": "p.json",
                "policy_sha256": "f" * 64, "worktree_clean_at_approval": True})
            tp = os.path.join(td, "task.yaml")
            with open(tp, "w") as f: yaml.dump(task, f)
            fd = os.path.join(td, "frozen")
            os.makedirs(fd, exist_ok=True)
            shutil.copy2(tp, os.path.join(fd, "frozen_task.yaml"))
            sha = hashlib.sha256(open(tp, "rb").read()).hexdigest()
            with open(os.path.join(fd, "frozen_task.sha256"), "w") as f: f.write(sha + "\n")
            code, result = change_scope_check(tp, fd)
            assert code == 2
            assert result["result"] == "ERROR"

    def test_upload_spec_sha_wrong_error(self):
        with tempfile.TemporaryDirectory() as td:
            repo = _git_init(td)
            _write(repo, "ok.txt", "ok")
            _git_commit(repo, "baseline B")
            os.makedirs(os.path.join(repo, "reviews", "UPLOAD_NEXT"), exist_ok=True)
            sp = _write(repo, "spec.json", json.dumps({"schema_version": "1", "task_id": "TASK_UP",
                "manifest_filename": "UPLOAD_MANIFEST.json", "entries": []}))
            task = _task_dict("TASK_UP", {"upload_spec_path": "spec.json", "upload_spec_sha256": "c" * 64})
            tp = os.path.join(repo, "task.yaml")
            with open(tp, "w") as f: yaml.dump(task, f)
            fd = os.path.join(repo, "frozen")
            os.makedirs(fd, exist_ok=True)
            shutil.copy2(tp, os.path.join(fd, "frozen_task.yaml"))
            sha = hashlib.sha256(open(tp, "rb").read()).hexdigest()
            with open(os.path.join(fd, "frozen_task.sha256"), "w") as f: f.write(sha + "\n")
            code, result = upload_package_check(tp, fd)
            assert code == 2
            assert result["result"] == "ERROR"

    def test_source_swapped_fail(self):
        with tempfile.TemporaryDirectory() as td:
            repo = _git_init(td)
            _write(repo, "ok.txt", "ok")
            _git_commit(repo, "baseline B")
            upload_dir = os.path.join(repo, "reviews", "UPLOAD_NEXT")
            src_dir = os.path.join(repo, "reports")
            os.makedirs(upload_dir, exist_ok=True)
            os.makedirs(src_dir, exist_ok=True)
            _write(repo, "reports/a.md", "aaa")
            _write(repo, "reports/b.md", "bbb")
            _write(repo, "reviews/UPLOAD_NEXT/a.md", "aaa")
            _write(repo, "reviews/UPLOAD_NEXT/b.md", "bbb")
            h_a = sha256_file(os.path.join(upload_dir, "a.md"))
            h_b = sha256_file(os.path.join(upload_dir, "b.md"))
            _write(repo, "reviews/UPLOAD_NEXT/UPLOAD_MANIFEST.json", json.dumps(
                {"schema_version": "1", "task_id": "TASK_UP", "entries": [
                    {"package_path": "a.md", "source_path": "reports/b.md", "sha256": h_a},
                    {"package_path": "b.md", "source_path": "reports/a.md", "sha256": h_b}]}))
            sp = _write(repo, "spec.json", json.dumps({"schema_version": "1", "task_id": "TASK_UP",
                "manifest_filename": "UPLOAD_MANIFEST.json", "entries": [
                    {"package_path": "a.md", "source_path": "reports/a.md"},
                    {"package_path": "b.md", "source_path": "reports/b.md"}]}))
            task = _task_dict("TASK_UP", {"upload_spec_path": "spec.json", "upload_spec_sha256": sha256_file(sp)})
            tp = os.path.join(repo, "task.yaml")
            with open(tp, "w") as f: yaml.dump(task, f)
            fd = os.path.join(repo, "frozen")
            os.makedirs(fd, exist_ok=True)
            shutil.copy2(tp, os.path.join(fd, "frozen_task.yaml"))
            sha = hashlib.sha256(open(tp, "rb").read()).hexdigest()
            with open(os.path.join(fd, "frozen_task.sha256"), "w") as f: f.write(sha + "\n")
            code, result = upload_package_check(tp, fd)
            assert code == 1
            assert result["result"] == "FAIL"

    def test_dup_package_path_error(self):
        with tempfile.TemporaryDirectory() as td:
            repo = _git_init(td)
            _write(repo, "ok.txt", "ok")
            _git_commit(repo, "baseline B")
            os.makedirs(os.path.join(repo, "reviews", "UPLOAD_NEXT"), exist_ok=True)
            _write(repo, "reviews/UPLOAD_NEXT/x.md", "x")
            sp = _write(repo, "spec.json", json.dumps({"schema_version": "1", "task_id": "TASK_UP",
                "manifest_filename": "UPLOAD_MANIFEST.json", "entries": [
                    {"package_path": "x.md", "source_path": "s/x.md"},
                    {"package_path": "x.md", "source_path": "s/x.md"}]}))
            task = _task_dict("TASK_UP", {"upload_spec_path": "spec.json", "upload_spec_sha256": sha256_file(sp)})
            tp = os.path.join(repo, "task.yaml")
            with open(tp, "w") as f: yaml.dump(task, f)
            fd = os.path.join(repo, "frozen")
            os.makedirs(fd, exist_ok=True)
            shutil.copy2(tp, os.path.join(fd, "frozen_task.yaml"))
            sha = hashlib.sha256(open(tp, "rb").read()).hexdigest()
            with open(os.path.join(fd, "frozen_task.sha256"), "w") as f: f.write(sha + "\n")
            code, result = upload_package_check(tp, fd)
            assert code == 2
            assert result["result"] == "ERROR"

    def test_no_file_writes_either(self):
        with tempfile.TemporaryDirectory() as td:
            repo, _, tp, fd, _ = _cs_fixture(td)
            before = set()
            for dp, _, fns in os.walk(repo):
                for fn in fns: before.add(os.path.join(dp, fn))
            change_scope_check(tp, fd)
            after = set()
            for dp, _, fns in os.walk(repo):
                for fn in fns: after.add(os.path.join(dp, fn))
            assert before == after

    def test_stdout_single_json(self):
        with tempfile.TemporaryDirectory() as td:
            _, _, tp, fd, _ = _cs_fixture(td)
            code, result = change_scope_check(tp, fd)
            assert isinstance(result, dict)
            assert "result" in result


# ════════════════════ R2 Bypass Fixes ════════════════════
class TestManifestStrictComparison:
    def test_manifest_extra_entry_fail(self):
        """upload_spec has a.txt only; manifest has a.txt + ghost.txt -> FAIL code 1"""
        with tempfile.TemporaryDirectory() as td:
            repo = _git_init(td)
            _write(repo, "ok.txt", "ok")
            _git_commit(repo, "baseline B")
            upload_dir = os.path.join(repo, "reviews", "UPLOAD_NEXT")
            src_dir = os.path.join(repo, "reports")
            os.makedirs(upload_dir, exist_ok=True)
            os.makedirs(src_dir, exist_ok=True)
            _write(repo, "reports/a.txt", "aaa")
            _write(repo, "reviews/UPLOAD_NEXT/a.txt", "aaa")
            h_a = sha256_file(os.path.join(upload_dir, "a.txt"))
            spec = {"schema_version": "1", "task_id": "TASK_UP",
                    "manifest_filename": "UPLOAD_MANIFEST.json",
                    "entries": [{"package_path": "a.txt", "source_path": "reports/a.txt"}]}
            sp = _write(repo, "upload_spec.json", json.dumps(spec))
            manifest = {"schema_version": "1", "task_id": "TASK_UP", "entries": [
                {"package_path": "a.txt", "source_path": "reports/a.txt", "sha256": h_a},
                {"package_path": "ghost.txt", "source_path": "reports/ghost.txt", "sha256": "f" * 64},
            ]}
            _write(repo, "reviews/UPLOAD_NEXT/UPLOAD_MANIFEST.json", json.dumps(manifest))
            task = _task_dict("TASK_UP", {"upload_spec_path": "upload_spec.json",
                              "upload_spec_sha256": sha256_file(sp)})
            tp = os.path.join(repo, "task.yaml")
            with open(tp, "w") as f: yaml.dump(task, f)
            fd = os.path.join(repo, "frozen")
            os.makedirs(fd, exist_ok=True)
            shutil.copy2(tp, os.path.join(fd, "frozen_task.yaml"))
            sha = hashlib.sha256(open(tp, "rb").read()).hexdigest()
            with open(os.path.join(fd, "frozen_task.sha256"), "w") as f: f.write(sha + "\n")
            code, result = upload_package_check(tp, fd)
            assert code == 1
            assert result["result"] == "FAIL"

    def test_source_path_mismatch_fail(self):
        """Same package_path, different source_path -> FAIL"""
        with tempfile.TemporaryDirectory() as td:
            repo = _git_init(td)
            _write(repo, "ok.txt", "ok")
            _git_commit(repo, "baseline B")
            upload_dir = os.path.join(repo, "reviews", "UPLOAD_NEXT")
            os.makedirs(upload_dir, exist_ok=True)
            os.makedirs(os.path.join(repo, "reports"), exist_ok=True)
            _write(repo, "reports/a.txt", "aaa")
            _write(repo, "reports/b.txt", "bbb")
            _write(repo, "reviews/UPLOAD_NEXT/a.txt", "aaa")
            h = sha256_file(os.path.join(upload_dir, "a.txt"))
            spec = {"schema_version": "1", "task_id": "TASK_UP", "manifest_filename": "UPLOAD_MANIFEST.json",
                    "entries": [{"package_path": "a.txt", "source_path": "reports/a.txt"}]}
            sp = _write(repo, "spec.json", json.dumps(spec))
            manifest = {"schema_version": "1", "task_id": "TASK_UP", "entries": [
                {"package_path": "a.txt", "source_path": "reports/b.txt", "sha256": h}]}
            _write(repo, "reviews/UPLOAD_NEXT/UPLOAD_MANIFEST.json", json.dumps(manifest))
            task = _task_dict("TASK_UP", {"upload_spec_path": "spec.json", "upload_spec_sha256": sha256_file(sp)})
            tp = os.path.join(repo, "task.yaml")
            with open(tp, "w") as f: yaml.dump(task, f)
            fd = os.path.join(repo, "frozen")
            os.makedirs(fd, exist_ok=True)
            shutil.copy2(tp, os.path.join(fd, "frozen_task.yaml"))
            sha = hashlib.sha256(open(tp, "rb").read()).hexdigest()
            with open(os.path.join(fd, "frozen_task.sha256"), "w") as f: f.write(sha + "\n")
            code, result = upload_package_check(tp, fd)
            assert code == 1
            assert result["result"] == "FAIL"


class TestRecursiveScan:
    def test_nested_package_pass(self):
        with tempfile.TemporaryDirectory() as td:
            repo = _git_init(td)
            _write(repo, "ok.txt", "ok")
            _git_commit(repo, "baseline B")
            upload_dir = os.path.join(repo, "reviews", "UPLOAD_NEXT")
            os.makedirs(os.path.join(upload_dir, "nested"), exist_ok=True)
            os.makedirs(os.path.join(repo, "reports"), exist_ok=True)
            _write(repo, "reports/data.txt", "data")
            _write(repo, "reviews/UPLOAD_NEXT/nested/data.txt", "data")
            h = sha256_file(os.path.join(upload_dir, "nested", "data.txt"))
            spec = {"schema_version": "1", "task_id": "TASK_UP", "manifest_filename": "UPLOAD_MANIFEST.json",
                    "entries": [{"package_path": "nested/data.txt", "source_path": "reports/data.txt"}]}
            sp = _write(repo, "spec.json", json.dumps(spec))
            _write(repo, "reviews/UPLOAD_NEXT/UPLOAD_MANIFEST.json", json.dumps(
                {"schema_version": "1", "task_id": "TASK_UP", "entries": [
                    {"package_path": "nested/data.txt", "source_path": "reports/data.txt", "sha256": h}]}))
            task = _task_dict("TASK_UP", {"upload_spec_path": "spec.json", "upload_spec_sha256": sha256_file(sp)})
            tp = os.path.join(repo, "task.yaml")
            with open(tp, "w") as f: yaml.dump(task, f)
            fd = os.path.join(repo, "frozen")
            os.makedirs(fd, exist_ok=True)
            shutil.copy2(tp, os.path.join(fd, "frozen_task.yaml"))
            sha = hashlib.sha256(open(tp, "rb").read()).hexdigest()
            with open(os.path.join(fd, "frozen_task.sha256"), "w") as f: f.write(sha + "\n")
            code, result = upload_package_check(tp, fd)
            assert code == 0
            assert result["result"] == "PASS"

    def test_nested_extra_file_fail(self):
        with tempfile.TemporaryDirectory() as td:
            repo = _git_init(td)
            _write(repo, "ok.txt", "ok")
            _git_commit(repo, "baseline B")
            upload_dir = os.path.join(repo, "reviews", "UPLOAD_NEXT")
            os.makedirs(os.path.join(upload_dir, "nested"), exist_ok=True)
            os.makedirs(os.path.join(repo, "reports"), exist_ok=True)
            _write(repo, "reports/data.txt", "data")
            _write(repo, "reviews/UPLOAD_NEXT/nested/data.txt", "data")
            _write(repo, "reviews/UPLOAD_NEXT/nested/extra.txt", "evil")
            h = sha256_file(os.path.join(upload_dir, "nested", "data.txt"))
            spec = {"schema_version": "1", "task_id": "TASK_UP", "manifest_filename": "UPLOAD_MANIFEST.json",
                    "entries": [{"package_path": "nested/data.txt", "source_path": "reports/data.txt"}]}
            sp = _write(repo, "spec.json", json.dumps(spec))
            _write(repo, "reviews/UPLOAD_NEXT/UPLOAD_MANIFEST.json", json.dumps(
                {"schema_version": "1", "task_id": "TASK_UP", "entries": [
                    {"package_path": "nested/data.txt", "source_path": "reports/data.txt", "sha256": h}]}))
            task = _task_dict("TASK_UP", {"upload_spec_path": "spec.json", "upload_spec_sha256": sha256_file(sp)})
            tp = os.path.join(repo, "task.yaml")
            with open(tp, "w") as f: yaml.dump(task, f)
            fd = os.path.join(repo, "frozen")
            os.makedirs(fd, exist_ok=True)
            shutil.copy2(tp, os.path.join(fd, "frozen_task.yaml"))
            sha = hashlib.sha256(open(tp, "rb").read()).hexdigest()
            with open(os.path.join(fd, "frozen_task.sha256"), "w") as f: f.write(sha + "\n")
            code, result = upload_package_check(tp, fd)
            assert code == 1
            assert result["result"] == "FAIL"


class TestFrozenDirBinding:
    def test_frozen_outside_repo_error(self):
        with tempfile.TemporaryDirectory() as td:
            repo = _git_init(td)
            _write(repo, "ok.txt", "ok")
            _git_commit(repo, "baseline B")
            os.makedirs(os.path.join(repo, "reviews", "UPLOAD_NEXT"), exist_ok=True)
            spec = {"schema_version": "1", "task_id": "TASK_UP", "manifest_filename": "UPLOAD_MANIFEST.json", "entries": []}
            sp = _write(repo, "spec.json", json.dumps(spec))
            _write(repo, "reviews/UPLOAD_NEXT/UPLOAD_MANIFEST.json", json.dumps(
                {"schema_version": "1", "task_id": "TASK_UP", "entries": []}))
            task = _task_dict("TASK_UP", {"upload_spec_path": "spec.json", "upload_spec_sha256": sha256_file(sp)})
            tp = os.path.join(repo, "task.yaml")
            with open(tp, "w") as f: yaml.dump(task, f)
            # Create frozen OUTSIDE repo
            outside = tempfile.mkdtemp()
            fd = os.path.join(outside, "frozen")
            os.makedirs(fd, exist_ok=True)
            shutil.copy2(tp, os.path.join(fd, "frozen_task.yaml"))
            sha = hashlib.sha256(open(tp, "rb").read()).hexdigest()
            with open(os.path.join(fd, "frozen_task.sha256"), "w") as f: f.write(sha + "\n")
            code, result = upload_package_check(tp, fd)
            assert code == 2
            assert result["result"] == "ERROR"


class TestManifestFilenameValidation:
    def test_parent_traversal_error(self):
        with tempfile.TemporaryDirectory() as td:
            repo = _git_init(td)
            _write(repo, "ok.txt", "ok")
            _git_commit(repo, "baseline B")
            os.makedirs(os.path.join(repo, "reviews", "UPLOAD_NEXT"), exist_ok=True)
            spec = {"schema_version": "1", "task_id": "TASK_UP",
                    "manifest_filename": "../evil.json", "entries": []}
            sp = _write(repo, "spec.json", json.dumps(spec))
            task = _task_dict("TASK_UP", {"upload_spec_path": "spec.json", "upload_spec_sha256": sha256_file(sp)})
            tp = os.path.join(repo, "task.yaml")
            with open(tp, "w") as f: yaml.dump(task, f)
            fd = os.path.join(repo, "frozen")
            os.makedirs(fd, exist_ok=True)
            shutil.copy2(tp, os.path.join(fd, "frozen_task.yaml"))
            sha = hashlib.sha256(open(tp, "rb").read()).hexdigest()
            with open(os.path.join(fd, "frozen_task.sha256"), "w") as f: f.write(sha + "\n")
            code, result = upload_package_check(tp, fd)
            assert code == 2
            assert result["result"] == "ERROR"


class TestPolicyEntryValidation:
    def test_escape_path_error(self):
        with tempfile.TemporaryDirectory() as td:
            _, bc, tp, fd, pp = _cs_fixture(td)
            policy = yaml.safe_load(open(pp))
            policy["allowed_paths"].append({"path": "../escape", "path_type": "file"})
            with open(pp, "w") as f: json.dump(policy, f)
            task = yaml.safe_load(open(tp))
            task["fixed_params"]["policy_sha256"] = sha256_file(pp)
            with open(tp, "w") as f: yaml.dump(task, f)
            shutil.copy2(tp, os.path.join(fd, "frozen_task.yaml"))
            sha = hashlib.sha256(open(tp, "rb").read()).hexdigest()
            with open(os.path.join(fd, "frozen_task.sha256"), "w") as f: f.write(sha + "\n")
            code, result = change_scope_check(tp, fd)
            assert code == 2
            assert result["result"] == "ERROR"


class TestModuleCommands:
    def test_cs_module_pass_stdout_json(self):
        with tempfile.TemporaryDirectory() as td:
            _, _, tp, fd, _ = _cs_fixture(td)
            r = subprocess.run(
                ["python", "-m", "protocol_guard.phase2_min.change_scope_check", tp, fd],
                capture_output=True, text=True, cwd=os.getcwd(),
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
            )
            assert r.returncode == 0
            out = json.loads(r.stdout.strip())
            assert out.get("result") == "PASS"

    def test_cs_module_fail_stdout_json(self):
        with tempfile.TemporaryDirectory() as td:
            _, _, tp, fd, _ = _cs_fixture(td)
            task = yaml.safe_load(open(tp))
            task["fixed_params"]["worktree_clean_at_approval"] = False
            with open(tp, "w") as f: yaml.dump(task, f)
            shutil.copy2(tp, os.path.join(fd, "frozen_task.yaml"))
            sha = hashlib.sha256(open(tp, "rb").read()).hexdigest()
            with open(os.path.join(fd, "frozen_task.sha256"), "w") as f: f.write(sha + "\n")
            r = subprocess.run(
                ["python", "-m", "protocol_guard.phase2_min.change_scope_check", tp, fd],
                capture_output=True, text=True, cwd=os.getcwd(),
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
            )
            assert r.returncode == 2
            out = json.loads(r.stdout.strip())
            assert out.get("result") == "ERROR"

    def test_up_module_pass_stdout_json(self):
        with tempfile.TemporaryDirectory() as td:
            repo = _git_init(td)
            _write(repo, "ok.txt", "ok")
            _git_commit(repo, "baseline B")
            upload_dir = os.path.join(repo, "reviews", "UPLOAD_NEXT")
            os.makedirs(upload_dir, exist_ok=True)
            os.makedirs(os.path.join(repo, "reports"), exist_ok=True)
            _write(repo, "reports/r.md", "x")
            _write(repo, "reviews/UPLOAD_NEXT/r.md", "x")
            h = sha256_file(os.path.join(upload_dir, "r.md"))
            spec = {"schema_version": "1", "task_id": "TASK_UP", "manifest_filename": "UPLOAD_MANIFEST.json",
                    "entries": [{"package_path": "r.md", "source_path": "reports/r.md"}]}
            sp = _write(repo, "spec.json", json.dumps(spec))
            _write(repo, "reviews/UPLOAD_NEXT/UPLOAD_MANIFEST.json", json.dumps(
                {"schema_version": "1", "task_id": "TASK_UP", "entries": [
                    {"package_path": "r.md", "source_path": "reports/r.md", "sha256": h}]}))
            task = _task_dict("TASK_UP", {"upload_spec_path": "spec.json", "upload_spec_sha256": sha256_file(sp)})
            tp = os.path.join(repo, "task.yaml")
            with open(tp, "w") as f: yaml.dump(task, f)
            fd = os.path.join(repo, "frozen")
            os.makedirs(fd, exist_ok=True)
            shutil.copy2(tp, os.path.join(fd, "frozen_task.yaml"))
            sha = hashlib.sha256(open(tp, "rb").read()).hexdigest()
            with open(os.path.join(fd, "frozen_task.sha256"), "w") as f: f.write(sha + "\n")
            r = subprocess.run(
                ["python", "-m", "protocol_guard.phase2_min.upload_package_check", tp, fd],
                capture_output=True, text=True, cwd=os.getcwd(),
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
            )
            assert r.returncode == 0
            out = json.loads(r.stdout.strip())
            assert out.get("result") == "PASS"

    def test_up_module_error_stdout_json(self):
        with tempfile.TemporaryDirectory() as td:
            repo = _git_init(td)
            _write(repo, "ok.txt", "ok")
            _git_commit(repo, "baseline B")
            os.makedirs(os.path.join(repo, "reviews", "UPLOAD_NEXT"), exist_ok=True)
            spec = {"schema_version": "1", "task_id": "TASK_UP",
                    "manifest_filename": "../evil.json", "entries": []}
            sp = _write(repo, "spec.json", json.dumps(spec))
            task = _task_dict("TASK_UP", {"upload_spec_path": "spec.json", "upload_spec_sha256": sha256_file(sp)})
            tp = os.path.join(repo, "task.yaml")
            with open(tp, "w") as f: yaml.dump(task, f)
            fd = os.path.join(repo, "frozen")
            os.makedirs(fd, exist_ok=True)
            shutil.copy2(tp, os.path.join(fd, "frozen_task.yaml"))
            sha = hashlib.sha256(open(tp, "rb").read()).hexdigest()
            with open(os.path.join(fd, "frozen_task.sha256"), "w") as f: f.write(sha + "\n")
            r = subprocess.run(
                ["python", "-m", "protocol_guard.phase2_min.upload_package_check", tp, fd],
                capture_output=True, text=True, cwd=os.getcwd(),
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
            )
            assert r.returncode == 2
            out = json.loads(r.stdout.strip())
            assert out.get("result") == "ERROR"


# ==============================================================
# R3 Link Escape & Structure Tests
# ==============================================================
class TestLinkEscape:
    def test_source_intermediate_symlink_rejected(self):
        """source_path goes through symlink dir -> outside repo -> must FAIL/ERROR"""
        with tempfile.TemporaryDirectory() as td:
            repo = _git_init(td)
            _write(repo, "ok.txt", "ok")
            _git_commit(repo, "baseline B")
            upload_dir = os.path.join(repo, "reviews", "UPLOAD_NEXT")
            os.makedirs(upload_dir, exist_ok=True)
            ext = os.path.join(td, "external")
            os.makedirs(ext, exist_ok=True)
            _write(td, "external/src.txt", "external content")
            link = os.path.join(repo, "linkdir")
            try:
                os.symlink(ext, link, target_is_directory=True)
            except OSError:
                pytest.skip("symlink requires admin on Windows")
            _write(repo, "reviews/UPLOAD_NEXT/pkg.txt", "external content")
            h = sha256_file(os.path.join(upload_dir, "pkg.txt"))
            spec = {"schema_version": "1", "task_id": "TASK_UP", "manifest_filename": "UPLOAD_MANIFEST.json",
                    "entries": [{"package_path": "pkg.txt", "source_path": "linkdir/src.txt"}]}
            sp = _write(repo, "spec.json", json.dumps(spec))
            _write(repo, "reviews/UPLOAD_NEXT/UPLOAD_MANIFEST.json", json.dumps(
                {"schema_version": "1", "task_id": "TASK_UP", "entries": [
                    {"package_path": "pkg.txt", "source_path": "linkdir/src.txt", "sha256": h}]}))
            task = _task_dict("TASK_UP", {"upload_spec_path": "spec.json", "upload_spec_sha256": sha256_file(sp)})
            tp = os.path.join(repo, "task.yaml")
            with open(tp, "w") as f: yaml.dump(task, f)
            fd = os.path.join(repo, "frozen")
            os.makedirs(fd, exist_ok=True)
            shutil.copy2(tp, os.path.join(fd, "frozen_task.yaml"))
            sha = hashlib.sha256(open(tp, "rb").read()).hexdigest()
            with open(os.path.join(fd, "frozen_task.sha256"), "w") as f: f.write(sha + "\n")
            code, result = upload_package_check(tp, fd)
            assert code != 0, f"source through linkdir MUST NOT pass, got {code}"
            assert result["result"] in ("FAIL", "ERROR")

    def test_protected_intermediate_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            repo = _git_init(td)
            _write(repo, "ok.txt", "ok")
            _git_commit(repo, "baseline B")
            bc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()
            ext = os.path.join(td, "external")
            os.makedirs(ext, exist_ok=True)
            _write(td, "external/secret.txt", "secret")
            ext_sha = sha256_file(os.path.join(td, "external", "secret.txt"))
            link = os.path.join(repo, "linkdir")
            try:
                os.symlink(ext, link, target_is_directory=True)
            except OSError:
                pytest.skip("symlink requires admin on Windows")
            policy = {"schema_version": "1", "task_id": "TASK_CS",
                "allowed_paths": [{"path": "ok.txt", "path_type": "file"},
                    {"path": "policy.json", "path_type": "file"},
                    {"path": "task.yaml", "path_type": "file"},
                    {"path": "frozen", "path_type": "directory"},
                    {"path": "linkdir", "path_type": "directory"}],
                "denied_paths": [], "protected_files": [{"path": "linkdir/secret.txt", "sha256": ext_sha}]}
            pp = _write(repo, "policy.json", json.dumps(policy))
            task = _task_dict("TASK_CS", {"baseline_commit_sha": bc, "policy_path": "policy.json",
                "policy_sha256": sha256_file(pp), "worktree_clean_at_approval": True})
            tp = os.path.join(repo, "task.yaml")
            with open(tp, "w") as f: yaml.dump(task, f)
            fd = os.path.join(repo, "frozen")
            os.makedirs(fd, exist_ok=True)
            shutil.copy2(tp, os.path.join(fd, "frozen_task.yaml"))
            sha = hashlib.sha256(open(tp, "rb").read()).hexdigest()
            with open(os.path.join(fd, "frozen_task.sha256"), "w") as f: f.write(sha + "\n")
            code, result = change_scope_check(tp, fd)
            assert code == 1
            assert result["result"] == "FAIL"
            assert any("LINK" in r.get("reason", "") for r in result.get("protected_file_changes", []))


class TestInvalidStructure:
    def test_policy_allowed_paths_wrong_type_error(self):
        with tempfile.TemporaryDirectory() as td:
            _, bc, tp, fd, pp = _cs_fixture(td)
            policy = yaml.safe_load(open(pp))
            policy["allowed_paths"] = "oops"
            with open(pp, "w") as f: json.dump(policy, f)
            task = yaml.safe_load(open(tp))
            task["fixed_params"]["policy_sha256"] = sha256_file(pp)
            with open(tp, "w") as f: yaml.dump(task, f)
            shutil.copy2(tp, os.path.join(fd, "frozen_task.yaml"))
            sha = hashlib.sha256(open(tp, "rb").read()).hexdigest()
            with open(os.path.join(fd, "frozen_task.sha256"), "w") as f: f.write(sha + "\n")
            code, result = change_scope_check(tp, fd)
            assert code == 2
            assert result["result"] == "ERROR"

    def test_manifest_entries_wrong_type_error(self):
        with tempfile.TemporaryDirectory() as td:
            repo = _git_init(td)
            _write(repo, "ok.txt", "ok")
            _git_commit(repo, "baseline B")
            os.makedirs(os.path.join(repo, "reviews", "UPLOAD_NEXT"), exist_ok=True)
            spec = {"schema_version": "1", "task_id": "TASK_UP", "manifest_filename": "UPLOAD_MANIFEST.json",
                    "entries": []}
            sp = _write(repo, "spec.json", json.dumps(spec))
            _write(repo, "reviews/UPLOAD_NEXT/UPLOAD_MANIFEST.json", json.dumps(
                {"schema_version": "1", "task_id": "TASK_UP", "entries": "oops"}))
            task = _task_dict("TASK_UP", {"upload_spec_path": "spec.json", "upload_spec_sha256": sha256_file(sp)})
            tp = os.path.join(repo, "task.yaml")
            with open(tp, "w") as f: yaml.dump(task, f)
            fd = os.path.join(repo, "frozen")
            os.makedirs(fd, exist_ok=True)
            shutil.copy2(tp, os.path.join(fd, "frozen_task.yaml"))
            sha = hashlib.sha256(open(tp, "rb").read()).hexdigest()
            with open(os.path.join(fd, "frozen_task.sha256"), "w") as f: f.write(sha + "\n")
            code, result = upload_package_check(tp, fd)
            assert code == 2
            assert result["result"] == "ERROR"

    def test_source_is_dir_not_file(self):
        with tempfile.TemporaryDirectory() as td:
            repo = _git_init(td)
            _write(repo, "ok.txt", "ok")
            _git_commit(repo, "baseline B")
            upload_dir = os.path.join(repo, "reviews", "UPLOAD_NEXT")
            os.makedirs(upload_dir, exist_ok=True)
            os.makedirs(os.path.join(repo, "reports", "subdir"), exist_ok=True)
            _write(repo, "reviews/UPLOAD_NEXT/pkg.txt", "x")
            h = sha256_file(os.path.join(upload_dir, "pkg.txt"))
            spec = {"schema_version": "1", "task_id": "TASK_UP", "manifest_filename": "UPLOAD_MANIFEST.json",
                    "entries": [{"package_path": "pkg.txt", "source_path": "reports/subdir"}]}
            sp = _write(repo, "spec.json", json.dumps(spec))
            _write(repo, "reviews/UPLOAD_NEXT/UPLOAD_MANIFEST.json", json.dumps(
                {"schema_version": "1", "task_id": "TASK_UP", "entries": [
                    {"package_path": "pkg.txt", "source_path": "reports/subdir", "sha256": h}]}))
            task = _task_dict("TASK_UP", {"upload_spec_path": "spec.json", "upload_spec_sha256": sha256_file(sp)})
            tp = os.path.join(repo, "task.yaml")
            with open(tp, "w") as f: yaml.dump(task, f)
            fd = os.path.join(repo, "frozen")
            os.makedirs(fd, exist_ok=True)
            shutil.copy2(tp, os.path.join(fd, "frozen_task.yaml"))
            sha = hashlib.sha256(open(tp, "rb").read()).hexdigest()
            with open(os.path.join(fd, "frozen_task.sha256"), "w") as f: f.write(sha + "\n")
            code, result = upload_package_check(tp, fd)
            assert code in (1, 2)
            assert result["result"] in ("FAIL", "ERROR")

    def test_module_invalid_structure_json_error(self):
        with tempfile.TemporaryDirectory() as td:
            repo = _git_init(td)
            _write(repo, "ok.txt", "ok")
            _git_commit(repo, "baseline B")
            os.makedirs(os.path.join(repo, "reviews", "UPLOAD_NEXT"), exist_ok=True)
            spec = {"schema_version": "1", "task_id": "TASK_UP", "manifest_filename": "UPLOAD_MANIFEST.json",
                    "entries": [1, 2, 3]}
            sp = _write(repo, "spec.json", json.dumps(spec))
            task = _task_dict("TASK_UP", {"upload_spec_path": "spec.json", "upload_spec_sha256": sha256_file(sp)})
            tp = os.path.join(repo, "task.yaml")
            with open(tp, "w") as f: yaml.dump(task, f)
            fd = os.path.join(repo, "frozen")
            os.makedirs(fd, exist_ok=True)
            shutil.copy2(tp, os.path.join(fd, "frozen_task.yaml"))
            sha = hashlib.sha256(open(tp, "rb").read()).hexdigest()
            with open(os.path.join(fd, "frozen_task.sha256"), "w") as f: f.write(sha + "\n")
            r = subprocess.run(
                ["python", "-m", "protocol_guard.phase2_min.upload_package_check", tp, fd],
                capture_output=True, text=True, cwd=os.getcwd(),
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
            )
            assert r.returncode == 2
            out = json.loads(r.stdout.strip())
            assert out.get("result") == "ERROR"


class TestDeterministicOutput:
    def test_hashseed_1_vs_2_identical(self):
        with tempfile.TemporaryDirectory() as td:
            _, _, tp, fd, _ = _cs_fixture(td)
            env1 = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "1"}
            env2 = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "2"}
            r1 = subprocess.run(["python", "-m", "protocol_guard.phase2_min.change_scope_check", tp, fd],
                                capture_output=True, text=True, cwd=os.getcwd(), env=env1)
            r2 = subprocess.run(["python", "-m", "protocol_guard.phase2_min.change_scope_check", tp, fd],
                                capture_output=True, text=True, cwd=os.getcwd(), env=env2)
            assert r1.stdout.strip() == r2.stdout.strip()
            assert r1.returncode == r2.returncode



# ==============================================================
# R4 Baseline Commit Type Validation Tests
# ==============================================================
class TestBaselineCommitType:
    def test_valid_40_char_commit_sha_passes(self):
        with tempfile.TemporaryDirectory() as td:
            _, _, tp, fd, _ = _cs_fixture(td)
            code, _ = change_scope_check(tp, fd)
            assert code == 0

    def test_tree_sha_returns_error(self):
        with tempfile.TemporaryDirectory() as td:
            repo = _git_init(td)
            _write(repo, "ok.txt", "ok")
            _git_commit(repo, "init")
            tree_sha = subprocess.run(
                ["git", "rev-parse", "HEAD^{tree}"], cwd=repo,
                capture_output=True, text=True
            ).stdout.strip()
            policy = {"schema_version": "1", "task_id": "TASK_CS",
                      "allowed_paths": [{"path": "ok.txt", "path_type": "file"},
                                        {"path": "policy.json", "path_type": "file"},
                                        {"path": "task.yaml", "path_type": "file"},
                                        {"path": "frozen", "path_type": "directory"}],
                      "denied_paths": [], "protected_files": []}
            pp = _write(repo, "policy.json", json.dumps(policy))
            task = _task_dict("TASK_CS", {"baseline_commit_sha": tree_sha,
                "policy_path": "policy.json", "policy_sha256": sha256_file(pp),
                "worktree_clean_at_approval": True})
            tp = os.path.join(repo, "task.yaml")
            with open(tp, "w") as f: yaml.dump(task, f)
            fd = os.path.join(repo, "frozen")
            os.makedirs(fd, exist_ok=True)
            shutil.copy2(tp, os.path.join(fd, "frozen_task.yaml"))
            sha = hashlib.sha256(open(tp, "rb").read()).hexdigest()
            with open(os.path.join(fd, "frozen_task.sha256"), "w") as f: f.write(sha + "\n")
            code, result = change_scope_check(tp, fd)
            assert code == 2
            assert result["result"] == "ERROR"

    def test_blob_sha_returns_error(self):
        with tempfile.TemporaryDirectory() as td:
            repo = _git_init(td)
            _write(repo, "ok.txt", "ok")
            _git_commit(repo, "init")
            blob_sha = subprocess.run(
                ["git", "rev-parse", "HEAD:ok.txt"], cwd=repo,
                capture_output=True, text=True
            ).stdout.strip()
            policy = {"schema_version": "1", "task_id": "TASK_CS",
                      "allowed_paths": [{"path": "ok.txt", "path_type": "file"},
                                        {"path": "policy.json", "path_type": "file"},
                                        {"path": "task.yaml", "path_type": "file"},
                                        {"path": "frozen", "path_type": "directory"}],
                      "denied_paths": [], "protected_files": []}
            pp = _write(repo, "policy.json", json.dumps(policy))
            task = _task_dict("TASK_CS", {"baseline_commit_sha": blob_sha,
                "policy_path": "policy.json", "policy_sha256": sha256_file(pp),
                "worktree_clean_at_approval": True})
            tp = os.path.join(repo, "task.yaml")
            with open(tp, "w") as f: yaml.dump(task, f)
            fd = os.path.join(repo, "frozen")
            os.makedirs(fd, exist_ok=True)
            shutil.copy2(tp, os.path.join(fd, "frozen_task.yaml"))
            sha = hashlib.sha256(open(tp, "rb").read()).hexdigest()
            with open(os.path.join(fd, "frozen_task.sha256"), "w") as f: f.write(sha + "\n")
            code, result = change_scope_check(tp, fd)
            assert code == 2
            assert result["result"] == "ERROR"

    def test_nonexistent_sha_returns_error(self):
        with tempfile.TemporaryDirectory() as td:
            repo = _git_init(td)
            _write(repo, "ok.txt", "ok")
            _git_commit(repo, "init")
            policy = {"schema_version": "1", "task_id": "TASK_CS",
                      "allowed_paths": [{"path": "ok.txt", "path_type": "file"},
                                        {"path": "policy.json", "path_type": "file"},
                                        {"path": "task.yaml", "path_type": "file"},
                                        {"path": "frozen", "path_type": "directory"}],
                      "denied_paths": [], "protected_files": []}
            pp = _write(repo, "policy.json", json.dumps(policy))
            task = _task_dict("TASK_CS", {"baseline_commit_sha": "d" * 40,
                "policy_path": "policy.json", "policy_sha256": sha256_file(pp),
                "worktree_clean_at_approval": True})
            tp = os.path.join(repo, "task.yaml")
            with open(tp, "w") as f: yaml.dump(task, f)
            fd = os.path.join(repo, "frozen")
            os.makedirs(fd, exist_ok=True)
            shutil.copy2(tp, os.path.join(fd, "frozen_task.yaml"))
            sha = hashlib.sha256(open(tp, "rb").read()).hexdigest()
            with open(os.path.join(fd, "frozen_task.sha256"), "w") as f: f.write(sha + "\n")
            code, result = change_scope_check(tp, fd)
            assert code == 2
            assert result["result"] == "ERROR"

    def test_abbreviated_sha_returns_error(self):
        with tempfile.TemporaryDirectory() as td:
            repo = _git_init(td)
            _write(repo, "ok.txt", "ok")
            _git_commit(repo, "init")
            policy = {"schema_version": "1", "task_id": "TASK_CS",
                      "allowed_paths": [{"path": "ok.txt", "path_type": "file"},
                                        {"path": "policy.json", "path_type": "file"},
                                        {"path": "task.yaml", "path_type": "file"},
                                        {"path": "frozen", "path_type": "directory"}],
                      "denied_paths": [], "protected_files": []}
            pp = _write(repo, "policy.json", json.dumps(policy))
            task = _task_dict("TASK_CS", {"baseline_commit_sha": "a" * 7,
                "policy_path": "policy.json", "policy_sha256": sha256_file(pp),
                "worktree_clean_at_approval": True})
            tp = os.path.join(repo, "task.yaml")
            with open(tp, "w") as f: yaml.dump(task, f)
            fd = os.path.join(repo, "frozen")
            os.makedirs(fd, exist_ok=True)
            shutil.copy2(tp, os.path.join(fd, "frozen_task.yaml"))
            sha = hashlib.sha256(open(tp, "rb").read()).hexdigest()
            with open(os.path.join(fd, "frozen_task.sha256"), "w") as f: f.write(sha + "\n")
            code, result = change_scope_check(tp, fd)
            assert code == 2
            assert result["result"] == "ERROR"

    def test_non_hex_sha_returns_error(self):
        with tempfile.TemporaryDirectory() as td:
            repo = _git_init(td)
            _write(repo, "ok.txt", "ok")
            _git_commit(repo, "init")
            policy = {"schema_version": "1", "task_id": "TASK_CS",
                      "allowed_paths": [{"path": "ok.txt", "path_type": "file"},
                                        {"path": "policy.json", "path_type": "file"},
                                        {"path": "task.yaml", "path_type": "file"},
                                        {"path": "frozen", "path_type": "directory"}],
                      "denied_paths": [], "protected_files": []}
            pp = _write(repo, "policy.json", json.dumps(policy))
            task = _task_dict("TASK_CS", {"baseline_commit_sha": "z" * 40,
                "policy_path": "policy.json", "policy_sha256": sha256_file(pp),
                "worktree_clean_at_approval": True})
            tp = os.path.join(repo, "task.yaml")
            with open(tp, "w") as f: yaml.dump(task, f)
            fd = os.path.join(repo, "frozen")
            os.makedirs(fd, exist_ok=True)
            shutil.copy2(tp, os.path.join(fd, "frozen_task.yaml"))
            sha = hashlib.sha256(open(tp, "rb").read()).hexdigest()
            with open(os.path.join(fd, "frozen_task.sha256"), "w") as f: f.write(sha + "\n")
            code, result = change_scope_check(tp, fd)
            assert code == 2
            assert result["result"] == "ERROR"

    def test_tree_sha_module_subprocess_error(self):
        with tempfile.TemporaryDirectory() as td:
            repo = _git_init(td)
            _write(repo, "ok.txt", "ok")
            _git_commit(repo, "init")
            tree_sha = subprocess.run(
                ["git", "rev-parse", "HEAD^{tree}"], cwd=repo,
                capture_output=True, text=True
            ).stdout.strip()
            policy = {"schema_version": "1", "task_id": "TASK_CS",
                      "allowed_paths": [{"path": "ok.txt", "path_type": "file"},
                                        {"path": "policy.json", "path_type": "file"},
                                        {"path": "task.yaml", "path_type": "file"},
                                        {"path": "frozen", "path_type": "directory"}],
                      "denied_paths": [], "protected_files": []}
            pp = _write(repo, "policy.json", json.dumps(policy))
            task = _task_dict("TASK_CS", {"baseline_commit_sha": tree_sha,
                "policy_path": "policy.json", "policy_sha256": sha256_file(pp),
                "worktree_clean_at_approval": True})
            tp = os.path.join(repo, "task.yaml")
            with open(tp, "w") as f: yaml.dump(task, f)
            fd = os.path.join(repo, "frozen")
            os.makedirs(fd, exist_ok=True)
            shutil.copy2(tp, os.path.join(fd, "frozen_task.yaml"))
            sha = hashlib.sha256(open(tp, "rb").read()).hexdigest()
            with open(os.path.join(fd, "frozen_task.sha256"), "w") as f: f.write(sha + "\n")
            r = subprocess.run(
                ["python", "-m", "protocol_guard.phase2_min.change_scope_check", tp, fd],
                capture_output=True, text=True, cwd=os.getcwd(),
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
            )
            assert r.returncode == 2
            out = json.loads(r.stdout.strip())
            assert out.get("result") == "ERROR"
            assert "traceback" not in r.stderr.lower()
