# MPC RandoKitter GUI — Design

**Date:** 2026-04-13
**Status:** Approved, ready for planning

## Purpose

Package the existing `mpc_random_kit.py` CLI script into a cross-platform GUI app so users who aren't comfortable with Python can drop in a samples folder, click a button, and get random MPC drum kits. Build pattern mirrors the sibling project `M8_KitCreator`: customtkinter UI, PyInstaller bundle, `build.sh` automation.

## Scope & UX decisions

- **UI scope:** "Standard" — samples folder picker, output folder picker, number of kits (1–10), pads per kit (16/32/64/128), optional custom kit name. Seed is not exposed (power users can still use the CLI).
- **Output location:** user-chosen output folder, separate from samples folder.
- **Progress feedback:** determinate progress bar plus status text, driven by a background thread. Window stays responsive; Generate becomes Cancel while running.
- **CLI lifecycle:** CLI stays fully supported. Core logic extracts into a shared module; both CLI and GUI import from it.

## Project structure

```
MPC_RandoKitter/
├── MPC_RandoKitter.py          # GUI entry point (run this)
├── mpc_random_kit.py           # CLI (thin argparse wrapper over core)
├── mpc_randokitter/
│   ├── __init__.py             # __version__
│   ├── core.py                 # All kit-building logic
│   └── gui.py                  # KitterApp (customtkinter)
├── MPC_RandoKitter.spec        # PyInstaller config
├── build.sh                    # build | clean | rebuild | test
├── requirements.txt            # customtkinter
├── requirements-build.txt      # + pyinstaller
├── BUILD.md
├── README.md                   # Updated with download + GUI usage
├── docs/plans/                 # Design docs
├── PLANNING.md, TASKS.md       # Existing
└── LICENSE
```

### `mpc_randokitter/core.py` — public API

- `scan_samples(source_dir, progress_cb=None) -> list[Path]`
- `load_or_build_cache(source_dir, progress_cb=None) -> list[Path]`
- `generate_kit(samples, output_dir, name=None, count=64, seed=None) -> Path`
- `generate_kits(source_dir, output_dir, num_kits, count, name_override, progress_cb, status_cb, cancel_event) -> list[Path]`
- Constants (`AUDIO_EXTENSIONS`, word pools) and helpers (`random_name`, `build_xpm`, etc.)

The CLI becomes a thin argparse wrapper calling `generate_kits()`. Same flags, same behavior. customtkinter is only imported by the GUI, so the CLI keeps its zero-runtime-dep story when run directly.

## GUI layout

```
┌─ MPC Random Kit Maker ─────────────────┐
│  Samples folder                        │
│  [ /Volumes/Samples/…          ][Pick] │
│                                        │
│  Output folder                         │
│  [ ~/Desktop                   ][Pick] │
│                                        │
│  Number of kits:   [ 4  ▼ ]  (1–10)    │
│  Pads per kit:     [ 64 ▼ ]            │
│                                        │
│  Kit name (optional)                   │
│  [ leave blank for random names      ] │
│                                        │
│  [████████░░░░░░░░░] 42%               │
│  Scanning samples… 12,438 found        │
│                                        │
│      [ Generate ]  [ Quit ]            │
└────────────────────────────────────────┘
```

**Widget specifics (customtkinter):**

- **Samples / Output folder** — readonly `CTkEntry` + `CTkButton` "Browse…". Output defaults to `~/Desktop` on first launch; last-used paths persist in `~/.mpc_randokitter.json`.
- **Number of kits** — `CTkOptionMenu`, 1–10.
- **Pads per kit** — `CTkOptionMenu`, 16/32/64/128, default 64.
- **Kit name** — `CTkEntry`, empty = random `Adjective_Noun`. Multi-kit with a custom name auto-suffixes `_1`, `_2`, etc.
- **Progress bar** — `CTkProgressBar`, determinate, idle at 0.
- **Status label** — single line below bar.
- **Generate button** — disabled while running; toggles to "Cancel" during a job.
- **Quit button** — confirms if a job is running.

Window size ~480×420, non-resizable.

## Threading & progress

- Clicking Generate spawns `threading.Thread(daemon=True)` running `core.generate_kits(...)`.
- Worker receives `progress_cb(float)` and `status_cb(str)`; both marshal via `self.after(0, …)` (tkinter is not thread-safe).
- A `threading.Event` cancels between kits; partial output folder is cleaned up on cancel.
- Any worker exception is surfaced via error dialog on the main thread; progress resets, Generate re-enables.

**Progress phases**

| Phase | Status text | Progress |
|---|---|---|
| Cache check | "Loading sample index…" | indeterminate pulse |
| Scan (miss) | "Scanning samples… N found" | 0–70% (best-effort by dirs walked) |
| Generate | "Generating kit 3 of 5: Molten_Anvil" | 70–100% linear over kits |

On cache hit, scan is skipped; progress jumps to 70% before kit generation.

## Cache behavior

Unchanged from the CLI. `mpc_random_kit.cache` lives in the **samples folder** (it's an index of that library). Daily rebuild, rebuilds on meaningful sample-count drift.

## Completion UX

Status shows `Done — 5 kits in /path/to/output`. A "Reveal in Finder" button next to the status opens the output folder via `open` (macOS) / `xdg-open` (Linux) / `explorer` (Windows).

## Build & packaging

**`MPC_RandoKitter.spec`** — near-copy of `M8_KitCreator.spec`:

```python
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = [], [], []
for pkg in ('customtkinter',):
    d, b, h = collect_all(pkg)
    datas += d; binaries += b; hiddenimports += h

a = Analysis(['MPC_RandoKitter.py'], ..., hiddenimports=hiddenimports, ...)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas,
          name='MPC_RandoKitter', console=False, upx=True, ...)
app = BUNDLE(exe, name='MPC_RandoKitter.app',
             bundle_identifier='com.atanguay.mpcrandokitter')
```

No `tkinterdnd2`, no `static-ffmpeg` — zero audio-processing deps. Expected bundle size ~40–50 MB (vs. M8's ~100 MB).

**`build.sh`** — direct port of M8's, names swapped. Same `build | clean | rebuild | test` commands, macOS/Linux detection, colored output.

**`requirements.txt`**
```
customtkinter>=5.0.0
```

**`requirements-build.txt`**
```
-r requirements.txt
pyinstaller>=5.0.0
```

**`BUILD.md`** — port of M8's, trimmed: no ffmpeg / static-ffmpeg / stereo / cue-chunk sections. Keep DMG / Gatekeeper / notarization sections verbatim.

**Output artifacts:**
- macOS: `dist/MPC_RandoKitter.app` → optional DMG via `create-dmg`
- Linux: `dist/MPC_RandoKitter` → tarball
- Windows: `dist/MPC_RandoKitter.exe` (spec is cross-platform; not tested from macOS)

**README update** — a "Download" section above "Quick start" links to GitHub Releases for non-Python users; existing CLI docs stay underneath.

## Out of scope

- Merging with M8_KitCreator (future work, per user note).
- Drag-and-drop folder targets (M8 has it; not required here).
- Seed / reproducibility UI (CLI still handles it).
- Windows testing (spec should work; verification deferred).
- Code signing / notarization setup (documented in BUILD.md but not performed).
