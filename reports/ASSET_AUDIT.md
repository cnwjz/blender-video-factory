# Asset Audit Report

DOCUMENT_STATUS = INITIAL_ASSET_AUDIT
AUDIT_BASIS = LOCAL_EVIDENCE_ONLY
GIT_INIT_STATUS = NOT_RUN
LAST_UPDATED = 2026-07-16T12:00:00+08:00

---

## Audit Basis

This audit relies on the following authoritative local files:

| File | Size | SHA256 |
|------|------|--------|
| `assets/ASSET_MANIFEST_DRAFT.md` | 5,265 B | `E61827999712705564EEA2FB8C20FBFC922781E869A67016A08D9A620F307209` |
| `assets/licenses/kenney_mini-characters_LICENSE.txt` | 718 B | `28358AE5ACCC85B572EB42507956AFC8BEAE05ACB4648BB9026A5714D421B785` |
| `assets/licenses/kenney_mini-market_LICENSE.txt` | 767 B | `5EE4DF809330C05896F223C97F250CC1BDC13B46A370EB464533C85C94146070` |
| `.gitignore` | 1,640 B | `F078CDC31BD818E75A0D17F3FD65A0A46306F9482063D54E903B71EE8DB9B375` |

No internet searches or external references were used. All conclusions are based on local file evidence.

---

## Asset Rulings

### Kenney Mini Characters

| Field | Value |
|-------|-------|
| ASSET_ID | KENNEY_MINI_CHARACTERS |
| LICENSE_STATUS | VERIFIED_FROM_LOCAL_LICENSE |
| CANONICAL_FORMAT | FBX |
| FIRST_COMMIT_STATUS | INCLUDE |

**Excluded from first commit (local files retained):**

| Exclusion | Count | Reason |
|-----------|-------|--------|
| Deprecated character GLB | 26 files | Project rule V4 §四.3 — GLB import produces stray Icospheres |
| OBJ export-format copies | 26 files + 26 MTL | FBX is canonical; OBJ is an export-format duplicate |

**Included in first commit:**

| Inclusion | Count | Path |
|-----------|-------|------|
| Canonical FBX models | 26 files | `projects/.../kenney_mini-characters/Models/FBX format/` |
| Download archive | 1 file | `assets/downloads/kenney_mini-characters.zip` |
| Centralized license | 1 file | `assets/licenses/kenney_mini-characters_LICENSE.txt` |

### Kenney Mini Market

| Field | Value |
|-------|-------|
| ASSET_ID | KENNEY_MINI_MARKET |
| LICENSE_STATUS | VERIFIED_FROM_LOCAL_LICENSE |
| CANONICAL_FORMAT | FBX |
| FIRST_COMMIT_STATUS | INCLUDE_EXCEPT_PROVISIONAL_FORMAT_EXCLUSIONS |

**Excluded from first commit (local files retained):**

| Exclusion | Count | Reason |
|-----------|-------|--------|
| Deprecated character-employee.glb | 1 file | Character GLB rule (V4 §四.3) |
| Market prop GLB | 19 files | Provisional — pending review of whether GLB market props exhibit Icosphere issue |
| OBJ export-format copies | 20 files + 20 MTL | FBX is canonical; OBJ is an export-format duplicate |

**Included in first commit:**

| Inclusion | Count | Path |
|-----------|-------|------|
| Canonical FBX models | 20 files | `projects/.../kenney_mini-market/Models/FBX format/` |
| Download archive | 1 file | `assets/downloads/kenney_mini-market.zip` |
| Centralized license | 1 file | `assets/licenses/kenney_mini-market_LICENSE.txt` |

### pensamientoazul Supermarket

| Field | Value |
|-------|-------|
| ASSET_ID | PENSAMIENTOAZUL_SUPERMARKET |
| LICENSE_STATUS | UNKNOWN |
| REDISTRIBUTION_STATUS | UNVERIFIED |
| FIRST_COMMIT_STATUS | EXCLUDE |

**Excluded from first commit (local files retained):**

29 FBX files in `assets/third_party/pensamientoazul_supermarket/Supermercado/`. No local license file, source documentation, or download archive found. Usage and redistribution rights cannot be inferred from file presence alone. Awaiting user confirmation of source and license.

---

## .gitignore Boundary Verification

Current `.gitignore` (SHA256: `F078CDC31BD818E75A0D17F3FD65A0A46306F9482063D54E903B71EE8DB9B375`) was checked for the following asset-related rules:

| Rule | Target | PRESENT |
|------|--------|---------|
| pensamientoazul directory exclusion | `/assets/third_party/pensamientoazul_supermarket/` | TRUE |
| Kenney character GLB directory exclusion | `.../kenney_mini-characters/Models/GLB format/` | TRUE |
| Kenney market employee GLB exclusion | `.../character-employee.glb` | TRUE |
| Kenney market GLB directory exclusion | `.../kenney_mini-market/Models/GLB format/` | TRUE |
| Kenney character OBJ directory exclusion | `.../kenney_mini-characters/Models/OBJ format/` | TRUE |
| Kenney market OBJ directory exclusion | `.../kenney_mini-market/Models/OBJ format/` | TRUE |

```
ASSET_GITIGNORE_ALIGNMENT = PASSED
```

All six asset exclusion categories are present in `.gitignore`. No rule is missing. Boundary is consistent with the asset manifest and this audit.

---

## Risk Register

| ID | Risk | Status |
|----|------|--------|
| A1 | pensamientoazul Supermarket: source and license unknown | UNRESOLVED — excluded from first commit; local files retained; awaiting user confirmation |
| A2 | 19 market prop GLB files: long-term format strategy undecided | UNRESOLVED — provisionally excluded; user review required on whether GLB market props exhibit Icosphere issue |
| A3 | Kenney OBJ and MTL: long-term disposition not locked | UNRESOLVED — provisionally excluded for first commit only; final disposition pending |
| A4 | SOURCE_REFERENCE field is UNKNOWN in asset manifest | UNRESOLVED — download URLs were not recorded at time of asset acquisition; can be filled retroactively |

No risks beyond these four are identified in the current asset boundary.

---

## Final Conclusion

```
ASSET_GOVERNANCE_STATUS = READY_FOR_GIT_INIT
```

All prerequisite governance files exist. All asset licenses are centralized and verified. All unlicensed, deprecated, and provisionally-excluded assets are covered by `.gitignore` rules. No asset will enter the first commit without a documented license and format decision.

This status indicates readiness for `git init` from an asset governance perspective only. It does not indicate assets have been committed, nor that pensamientoazul has been authorized.
