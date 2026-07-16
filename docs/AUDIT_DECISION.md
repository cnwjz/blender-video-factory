# BVF Environment Audit — Formal Decision Record

Date: 2026-07-14
Project: Blender Video Factory
Phase: Stage 0 (Environment Audit) → Stage 1 (Mechanism & Shot Locking)

---

## System Environment

| Item | Result |
|------|--------|
| OS | Windows 10 Pro 10.0.19045 |
| CPU | i5-13490F |
| GPU | AMD Radeon RX 7600 |
| RAM | 32 GB |
| Python (system) | 3.14.5 |
| Node.js | v24.15.0 |
| uv | 0.11.17 |

## Blender

| Item | Result |
|------|--------|
| Version | 5.1.2 |
| Executable | `D:\Windows software\blender\blender.exe` |
| Built-in Python | 3.13.9 |
| `--background` mode | Working |
| Eevee | Working |

## FFmpeg

| Item | Result |
|------|--------|
| Version | 8.1.1 |
| Executable | `D:\ffmpeg\ffmpeg.exe` |
| CLI pipeline | Working |

## Formal Audit Status

| Audit Item | Status | Notes |
|---|---|---|
| `environment_checked` | **passed** | 2026-07-14 |
| `blender_cli_render` | **passed** | 10-frame Eevee render + PNG sequence verified |
| `eevee_render` | **passed** | BLENDER_EEVEE engine functional |
| `ffmpeg_pipeline` | **passed** | PNG sequence → H.264 MP4 confirmed |
| `blender_mcp_smoke_test` | **passed** | Status report, script execution, scene creation all work |
| `blender_mcp_reproducibility` | **pending** | Will be verified during graybox build |
| `jianying_draft_generation` | **passed** | Draft → track → text segment → export full chain verified |
| `jianying_desktop_open_test` | **pending** | Requires manual verification in Jiaying desktop app |
| `jianying_mp4_export_test` | **pending** | Requires manual export from Jiaying desktop app |
| `vfx_mcp` | **disabled** | Package entry point bug. Using FFmpeg CLI directly instead. |
| `ffmpeg_cli` | **active** | Direct FFmpeg CLI as vfx-mcp replacement |
| `local_vision_smoke_test` | **passed** | llava 7B via Ollama + mcp-vision returns valid analysis |
| `local_vision_quality` | **limited** | llava 7B accuracy insufficient for automated review decisions. Consider cloud API models for production. |

## Corrections

1. **RX7600 VRAM**: The 4 GB figure was read from the system adapter report. This value has not been independently verified against the actual physical hardware. Do not treat it as an authoritative hardware spec.

2. **CUEW Initialization Failure**: The Cycles GPU backend reported `CUEW initialization failed: Error opening the library`. This error alone is insufficient to determine AMD HIP status on this system. The correct status for Cycles HIP on this machine is **not verified**. Do not pursue HIP/Cycles GPU rendering unless Eevee proves insufficient for the target visual quality.

## Sign-off

- [ ] Environment audit accepted
- [ ] Ready to proceed to Phase 1: Mechanism & Shot Locking
- [ ] Phase 1 documents created: INPUT.yaml, direction.json, shots.json, HUMAN_REVIEW.md
