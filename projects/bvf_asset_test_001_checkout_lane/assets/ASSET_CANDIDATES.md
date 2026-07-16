# Asset Candidates — bvf_asset_test_001_checkout_lane

Date: 2026-07-14 | Phase: A0

---

## 1. Source Summary

| Source | Characters | Checkout Props | Environment | License | Status |
|--------|-----------|----------------|-------------|---------|--------|
| Local D: drive | 0 | 0 | 0 | N/A | Empty |
| Poly Haven | **0** | **0** | 16 shelves, 27 tables, 19 food items | CC0 | Available |
| Sketchfab | Unknown | Unknown | Unknown | Varies | **API token required** |

## 2. Poly Haven Candidates (CC0 — Free Commercial Use)

### 2.1 Shelves / Racks (for background supermarket context)

| Asset ID | Name | Notes |
|----------|------|-------|
| `wooden_display_shelves_01` | Wooden Display Shelves | Closest to retail shelving |
| `steel_frame_shelves_01` | Steel Frame Shelves | Industrial/warehouse style |
| `painted_wooden_shelves` | Painted Wooden Shelves | Simple, clean |
| `worn_metal_rack` | Worn Metal Rack | Could work for stock room |

### 2.2 Tables / Desks (for checkout counter base)

| Asset ID | Name | Notes |
|----------|------|-------|
| `metal_office_desk` | Metal Office Desk | Could proxy as checkout counter |
| `industrial_storage_cart` | Industrial Storage Cart | Rolling cart proxy |
| `painted_wooden_table` | Painted Wooden Table | Simple surface |

### 2.3 Food / Products (for conveyors and shelves)

| Asset ID | Name | Notes |
|----------|------|-------|
| `food_apple_01` | Apple | Single produce item |
| `bananas` | Bananas | Bunch, recognizable |
| `russian_food_cans_01` | Food Cans | Packaged goods proxy |
| `lemon` | Lemon | Small produce |
| `croissant` | Croissant | Bakery item |
| `long_life_food` | Long Life Food | Canned/packaged |
| `hamburger_buns` | Hamburger Buns | Bakery item |

### 2.4 Electronics / Appliances (for checkout equipment proxy)

| Asset ID | Name | Notes |
|----------|------|-------|
| `gaming_console` | Gaming Console | Could proxy as POS terminal |
| `vintage_microwave` | Vintage Microwave | Size reference for appliance |

## 3. Critical Gaps

| Missing Asset Type | Severity | Alternatives |
|-------------------|----------|-------------|
| **Human characters (customer)** | **BLOCKING** | No source found. Sketchfab may have CC0 characters. |
| **Human characters (cashier)** | **BLOCKING** | Same as above. |
| **Checkout counter with conveyor** | **HIGH** | Would need to build from Poly Haven table + custom geometry for belt. |
| **Scanner / POS device** | **MEDIUM** | Can proxy with `gaming_console` + custom scanner box. |
| **Signboard / status light** | **MEDIUM** | Build from native Blender geometry (simple from previous project). |
| **Shutter / close door** | **MEDIUM** | Build from native Blender geometry. |
| **Shopping cart / basket** | **LOW** | Optional, not required for minimum viable test. |

## 4. Recommendation

**Cannot proceed to A1 without character assets.** Recommend:

1. **Priority 1**: Search Sketchfab for CC0 low-poly characters (requires SKETCHFAB_API_TOKEN)
2. **Priority 2**: Check if Blender addon MB-Lab or Human Generator is available for simple character generation
3. **Priority 3**: Evaluate Mixamo characters (requires Adobe account, non-commercial free tier)
4. **Fallback**: Accept that this test requires purchasing a small character pack

Poly Haven alone can supply shelving, food props, and table surfaces for the environment, but the scene cannot function without human figures.

## 5. Style Consistency Note

Poly Haven assets generally lean toward realistic PBR (8K textures, high polycounts). Mixing realistic Poly Haven shelves with stylized low-poly characters would violate the style consistency requirement. If characters end up being stylized/low-poly, the environment assets would need matching simplification or alternative sourcing.
