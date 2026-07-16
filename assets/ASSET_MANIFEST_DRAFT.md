# Asset Manifest (Draft)

DOCUMENT_STATUS = DRAFT
GIT_TRACKING_DECISION = NOT_EXECUTED
LAST_UPDATED = 2026-07-16T11:30:00+08:00

---

## Field Definitions

| Field | Description |
|-------|-------------|
| ASSET_ID | Unique identifier for this asset set |
| DISPLAY_NAME | Human-readable name |
| SOURCE_PROVIDER | Creator or distributor name |
| SOURCE_REFERENCE | URL, store page, or package identifier |
| LOCAL_DOWNLOAD_PATH | Path to original downloaded archive, relative to project root |
| LOCAL_IMPORTED_PATH | Path to expanded/imported assets, relative to project root |
| CANONICAL_FORMAT | Primary working format for this project |
| DERIVED_OR_DEPRECATED_FORMATS | Formats present on disk but not canonical or deprecated |
| LICENSE_STATUS | VERIFIED_FROM_LOCAL_LICENSE / UNKNOWN / NONE_FOUND |
| LICENSE_FILE | Path to centralized license copy in assets/licenses/ |
| LICENSE_SHA256 | SHA256 of the centralized license file |
| REDISTRIBUTION_STATUS | VERIFIED / UNVERIFIED / RESTRICTED |
| FIRST_COMMIT_STATUS | INCLUDE / EXCLUDE / INCLUDE_EXCEPT_PROVISIONAL_GLB_EXCLUSIONS |
| NOTES | Additional context, decisions, or warnings |

---

## Asset: Kenney Mini Characters

| Field | Value |
|-------|-------|
| ASSET_ID | KENNEY_MINI_CHARACTERS |
| DISPLAY_NAME | Kenney Mini Characters |
| SOURCE_PROVIDER | Kenney |
| SOURCE_REFERENCE | UNKNOWN (downloaded before this manifest was created) |
| LOCAL_DOWNLOAD_PATH | assets/downloads/kenney_mini-characters.zip |
| LOCAL_IMPORTED_PATH | projects/bvf_asset_test_001_checkout_lane/assets/imported/kenney_mini-characters/ |
| CANONICAL_FORMAT | FBX (26 files in Models/FBX format/) |
| DERIVED_OR_DEPRECATED_FORMATS | GLB character files excluded by project rule (26 files in Models/GLB format/) — V4 §四.3 |
| LICENSE_STATUS | VERIFIED_FROM_LOCAL_LICENSE |
| LICENSE_FILE | assets/licenses/kenney_mini-characters_LICENSE.txt |
| LICENSE_SHA256 | 28358AE5ACCC85B572EB42507956AFC8BEAE05ACB4648BB9026A5714D421B785 |
| REDISTRIBUTION_STATUS | VERIFIED — CC0 (public domain dedication, per license text) |
| FIRST_COMMIT_STATUS | INCLUDE |
| NOTES | Characters normalized to 1.75 Blender units in character_library_v1.blend. GLB format deprecated per project rule V4 §四.3 and §十八.1. OBJ format also present in Models/OBJ format/ — status not audited. |

---

## Asset: Kenney Mini Market

| Field | Value |
|-------|-------|
| ASSET_ID | KENNEY_MINI_MARKET |
| DISPLAY_NAME | Kenney Mini Market |
| SOURCE_PROVIDER | Kenney |
| SOURCE_REFERENCE | UNKNOWN (downloaded before this manifest was created) |
| LOCAL_DOWNLOAD_PATH | assets/downloads/kenney_mini-market.zip |
| LOCAL_IMPORTED_PATH | projects/bvf_asset_test_001_checkout_lane/assets/imported/kenney_mini-market/ |
| CANONICAL_FORMAT | FBX (20 files in Models/FBX format/) |
| DERIVED_OR_DEPRECATED_FORMATS | GLB: 1 character-employee.glb excluded by character GLB rule + 19 market prop GLB files provisionally excluded pending review (20 files in Models/GLB format/) |
| LICENSE_STATUS | VERIFIED_FROM_LOCAL_LICENSE |
| LICENSE_FILE | assets/licenses/kenney_mini-market_LICENSE.txt |
| LICENSE_SHA256 | 5EE4DF809330C05896F223C97F250CC1BDC13B46A370EB464533C85C94146070 |
| REDISTRIBUTION_STATUS | VERIFIED — CC0 (public domain dedication, per license text) |
| FIRST_COMMIT_STATUS | INCLUDE_EXCEPT_PROVISIONAL_GLB_EXCLUSIONS |
| NOTES | 1 character-employee.glb excluded per character GLB rule. 19 market prop GLB files provisionally excluded from first commit pending review of whether GLB market props exhibit the Icosphere issue documented in V4 §五.1. Long-term disposition of the 19 market prop GLB files has not been decided. OBJ format also present in Models/OBJ format/ — status not audited. |

---

## Asset: pensamientoazul Supermarket

| Field | Value |
|-------|-------|
| ASSET_ID | PENSAMIENTOAZUL_SUPERMARKET |
| DISPLAY_NAME | pensamientoazul Supermarket Props |
| SOURCE_PROVIDER | pensamientoazul |
| SOURCE_REFERENCE | UNKNOWN |
| LOCAL_DOWNLOAD_PATH | NONE_FOUND |
| LOCAL_IMPORTED_PATH | assets/third_party/pensamientoazul_supermarket/Supermercado/ |
| CANONICAL_FORMAT | FBX (29 files) |
| DERIVED_OR_DEPRECATED_FORMATS | NONE |
| LICENSE_STATUS | UNKNOWN |
| LICENSE_FILE | NONE_FOUND |
| LICENSE_SHA256 | NONE_FOUND |
| REDISTRIBUTION_STATUS | UNVERIFIED |
| FIRST_COMMIT_STATUS | EXCLUDE |
| NOTES | Local copy retained on disk. Excluded from first commit pending source and license confirmation. No README, LICENSE, or attribution file found in directory tree. Not referenced in Blender asset handoff document V4. Prohibited from inferring usage or redistribution rights from file presence alone. |

---

## First Commit Summary

### INCLUDE
- Kenney Mini Characters: FBX models, license file, download archive
- Kenney Mini Market: FBX models, license file, download archive
- Centralized license copies in assets/licenses/

### EXCLUDE
- pensamientoazul Supermarket (29 FBX files, no license)
- Deprecated character GLB files (27 total: 26 characters + 1 employee)
- 19 market prop GLB files (provisional, pending review)

### UNRESOLVED
- pensamientoazul source and license
- Long-term format strategy for 19 market prop GLB files
- OBJ format copies (present on disk, not audited in this manifest)
