# MPC RandoKitter GUI — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wrap the existing `mpc_random_kit.py` CLI in a cross-platform customtkinter GUI and package it as a standalone PyInstaller app, mirroring the `M8_KitCreator` build pattern.

**Architecture:** Extract the CLI's kit-building logic into a reusable `mpc_randokitter/core.py` module. Build `mpc_randokitter/gui.py` as a threaded customtkinter app. Refactor the existing CLI into a thin argparse wrapper that imports from core. Package with PyInstaller using a spec file copied from `M8_KitCreator`.

**Tech Stack:** Python 3.7+, customtkinter (GUI), threading (background work), PyInstaller (packaging), stdlib for everything else.

**Design doc:** `docs/plans/2026-04-13-mpc-randokitter-gui-design.md`

**Working dir:** `.worktrees/gui-wrapper/` on branch `feature/gui-wrapper`.

**Testing approach:** This project has no existing unit tests. Verification for each task is a **smoke test**: run the CLI/GUI and confirm the artifact produced is correct. Commit after each task passes its smoke test.

---

## Task 1: Create package scaffold

**Files:**
- Create: `mpc_randokitter/__init__.py`

**Step 1: Create the package**

```python
# mpc_randokitter/__init__.py
"""MPC Random Kit Maker — shared core + GUI."""

__version__ = "0.1.0"
```

**Step 2: Verify import works**

Run: `python3 -c "import mpc_randokitter; print(mpc_randokitter.__version__)"`
Expected: `0.1.0`

**Step 3: Commit**

```bash
git add mpc_randokitter/__init__.py
git commit -m "Scaffold mpc_randokitter package (v0.1.0)"
```

---

## Task 2: Extract constants and name helpers into core.py

**Files:**
- Create: `mpc_randokitter/core.py`
- Reference (read only): `mpc_random_kit.py:33-98`

**Step 1: Create core.py with constants and name/pad helpers**

Copy verbatim from `mpc_random_kit.py` lines 33–98:
- `AUDIO_EXTENSIONS`
- `_ADJECTIVES`, `_NOUNS` tuples
- `generate_fun_name()`
- `default_pad_notes(count=128)`

Add standard stdlib imports at top:

```python
"""Core kit-building logic for MPC RandoKitter.

Shared by the CLI (mpc_random_kit.py) and the GUI (mpc_randokitter/gui.py).
Zero third-party dependencies — Python 3.6+ stdlib only.
"""

import datetime
import io
import os
import random
import re
import shutil
import threading
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Callable, List, Optional
```

**Step 2: Smoke-test imports**

Run: `python3 -c "from mpc_randokitter import core; print(core.generate_fun_name())"`
Expected: e.g. `Molten_Anvil`

**Step 3: Commit**

```bash
git add mpc_randokitter/core.py
git commit -m "Extract constants and name helpers into core.py"
```

---

## Task 3: Move cache, scan, XPM, and copy logic into core.py

**Files:**
- Modify: `mpc_randokitter/core.py`
- Reference: `mpc_random_kit.py:104-453`

**Step 1: Copy these functions into core.py verbatim (with modifications below)**

- `CACHE_FILENAME = "mpc_random_kit.cache"` (line 104)
- `load_cache(source_dir)` — **modify:** replace `_cache_path()` with cache located inside `source_dir`: `os.path.join(os.path.abspath(source_dir), CACHE_FILENAME)`. Remove the separate `_cache_path()` function. Rationale: cache belongs with the sample library (per design doc).
- `write_cache(source_dir, samples)` — same `source_dir`-based path.
- `find_samples(root_dir, skip_dirs=None, progress_cb=None)` — **modify:** add `progress_cb: Optional[Callable[[int], None]] = None` parameter. Replace the `_print_progress()` body with:
  ```python
  def _print_progress():
      count = len(samples)
      if count - last_count[0] >= 500 or count == 0:
          if progress_cb:
              progress_cb(count)
          else:
              print(f"\r  Scanning... found {count:,} samples so far", end="", flush=True)
          last_count[0] = count
  ```
  Keep the final `print(...)` clearing line only when `progress_cb is None`.
- `indent_xml`, `make_audio_route`, `make_lfo`, `make_layer`, `make_instrument`, `make_pad_note_map`, `make_pad_group_map`, `generate_xpm` — copy verbatim from lines 205–418.
- `copy_samples_to_kit(selected_samples, out_dir, progress_cb=None)` — **modify:** add optional `progress_cb` param. Replace the `print(...)` progress line with:
  ```python
  if progress_cb:
      progress_cb(i, len(selected_samples))
  else:
      print(f"\r  Copying samples... {i}/{len(selected_samples)}", end="", flush=True)
  ```

**Step 2: Smoke-test**

Run:
```bash
python3 -c "
from mpc_randokitter import core
print('functions:', [n for n in dir(core) if not n.startswith('_') and callable(getattr(core, n))])
"
```
Expected: list includes `find_samples`, `generate_xpm`, `copy_samples_to_kit`, `load_cache`, `write_cache`.

**Step 3: Commit**

```bash
git add mpc_randokitter/core.py
git commit -m "Move cache, scan, XPM, and copy logic into core.py"
```

---

## Task 4: Add kit-generation orchestrator to core.py

**Files:**
- Modify: `mpc_randokitter/core.py`

**Step 1: Add `write_xpm_file` helper**

Encapsulates the write-to-disk fix-self-closing-tags logic from `mpc_random_kit.py:569-578`.

```python
def write_xpm_file(root: ET.Element, xpm_path: str) -> None:
    """Pretty-print an XPM tree and write to disk with MPC-compatible tags."""
    tree = ET.ElementTree(root)
    try:
        ET.indent(tree, space="  ")
    except AttributeError:
        indent_xml(root)

    buf = io.BytesIO()
    buf.write(b'<?xml version="1.0" encoding="UTF-8"?>\n\n')
    tree.write(buf, encoding="utf-8", xml_declaration=False)
    xml_str = buf.getvalue().decode("utf-8")
    xml_str = re.sub(r'<(\w+)\s*/>', r'<\1></\1>', xml_str)

    with open(xpm_path, "w", encoding="utf-8") as f:
        f.write(xml_str)
```

**Step 2: Add `generate_kit` single-kit function**

```python
def generate_kit(
    samples: List[str],
    out_root: str,
    kit_name: Optional[str] = None,
    count: int = 64,
    copy_progress_cb: Optional[Callable[[int, int], None]] = None,
) -> str:
    """Build one kit folder. Returns absolute path to the folder created.

    `samples` is the pool to select from; `out_root` is the parent dir under
    which the kit's folder will be created. `kit_name` of None = random.
    """
    count = min(count, 128, len(samples))
    if kit_name is None:
        kit_name = generate_fun_name()
        ts = datetime.datetime.now().strftime("%Y%m")
        folder_name = f"RandomKit_{kit_name}_{ts}"
    else:
        folder_name = kit_name

    out_dir = os.path.join(os.path.abspath(out_root), folder_name)
    os.makedirs(out_dir, exist_ok=True)

    selected = random.sample(samples, count)
    dest_names = copy_samples_to_kit(selected, out_dir, progress_cb=copy_progress_cb)

    root = generate_xpm(kit_name, dest_names, pad_count=count)
    write_xpm_file(root, os.path.join(out_dir, f"{kit_name}.xpm"))
    return out_dir
```

**Step 3: Add `generate_kits` orchestrator (the GUI's single entry point)**

```python
def generate_kits(
    source_dir: str,
    output_dir: str,
    num_kits: int,
    pads_per_kit: int = 64,
    name_override: Optional[str] = None,
    seed: Optional[int] = None,
    progress_cb: Optional[Callable[[float, str], None]] = None,
    cancel_event: Optional[threading.Event] = None,
) -> List[str]:
    """Full pipeline: cache/scan samples, generate N kits. Returns kit paths.

    `progress_cb(fraction, status_text)` is called for UI updates; `fraction`
    is 0.0-1.0, `status_text` is a human-readable phase message. Passing
    `cancel_event` allows cooperative cancellation between kits.
    """
    def report(fraction: float, status: str) -> None:
        if progress_cb:
            progress_cb(fraction, status)

    if seed is not None:
        random.seed(seed)

    source_dir = os.path.abspath(source_dir)
    output_dir = os.path.abspath(output_dir)

    report(0.0, "Loading sample index…")
    samples = load_cache(source_dir)
    if not samples:
        skip_dirs = []
        try:
            for entry in os.scandir(source_dir):
                if entry.is_dir() and (entry.name.startswith("random_kit_")
                                       or entry.name.startswith("RandomKit_")):
                    skip_dirs.append(os.path.abspath(entry.path))
        except PermissionError:
            pass

        def scan_progress(count: int) -> None:
            report(0.4, f"Scanning samples… {count:,} found")

        samples = find_samples(source_dir, skip_dirs=skip_dirs,
                               progress_cb=scan_progress)
        if not samples:
            raise RuntimeError(f"No .wav/.aif/.aiff files found under {source_dir}")
        write_cache(source_dir, samples)

    report(0.7, f"Found {len(samples):,} samples — generating kits…")

    os.makedirs(output_dir, exist_ok=True)
    kits = []
    for kit_num in range(1, num_kits + 1):
        if cancel_event is not None and cancel_event.is_set():
            break

        if name_override:
            kit_name = name_override if num_kits == 1 else f"{name_override}_{kit_num}"
        else:
            kit_name = None  # generate_kit picks a random one

        display_name = kit_name or "(random)"
        report(0.7 + 0.3 * (kit_num - 1) / num_kits,
               f"Generating kit {kit_num} of {num_kits}: {display_name}")

        kit_path = generate_kit(samples, output_dir, kit_name=kit_name,
                                count=pads_per_kit)
        kits.append(kit_path)

    report(1.0, f"Done — {len(kits)} kit(s) in {output_dir}")
    return kits
```

**Step 4: Smoke-test end-to-end**

```bash
mkdir -p /tmp/rk_src /tmp/rk_out
# Drop a few tiny test wav files into /tmp/rk_src or point to a real sample dir
python3 -c "
from mpc_randokitter import core
kits = core.generate_kits('/tmp/rk_src', '/tmp/rk_out', num_kits=1, pads_per_kit=4)
print('Generated:', kits)
"
ls /tmp/rk_out
```

Expected: one `RandomKit_*` folder with an `.xpm` and copied samples. If `/tmp/rk_src` has no samples, expect `RuntimeError`.

**Step 5: Commit**

```bash
git add mpc_randokitter/core.py
git commit -m "Add generate_kit and generate_kits orchestrator to core"
```

---

## Task 5: Refactor CLI to use core

**Files:**
- Modify: `mpc_random_kit.py` (replace most of it)

**Step 1: Replace file with a thin wrapper**

```python
#!/usr/bin/env python3
"""
mpc_random_kit.py
-----------------
CLI for MPC RandoKitter. Wraps mpc_randokitter.core.

Usage:
    python3 mpc_random_kit.py [source_dir] [--name "My Kit"] [--count 64] [--seed 42] [--kits 5]

If source_dir is omitted, the script scans the directory it lives in.
If --kits is omitted, the script asks interactively (1-10).
Output folders are created alongside the samples (unchanged behavior).
"""

import argparse
import os
import sys

from mpc_randokitter import core


def _cli_progress(fraction: float, status: str) -> None:
    print(f"[{int(fraction * 100):3d}%] {status}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate random MPC Drum Programs (.xpm) from a sample directory."
    )
    parser.add_argument("source_dir", nargs="?", default=None,
                        help="Root directory to scan for samples (default: script's own directory)")
    parser.add_argument("--name", default=None, help="Kit name (default: auto-generated)")
    parser.add_argument("--count", type=int, default=64, help="Number of pads to fill (default: 64)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--kits", type=int, default=None, help="Number of kits to generate (1-10)")
    args = parser.parse_args()

    if args.kits is None:
        try:
            answer = input("How many kits would you like to generate? (1-10, default 1): ").strip()
            args.kits = int(answer) if answer else 1
        except (ValueError, EOFError):
            args.kits = 1
    args.kits = max(1, min(10, args.kits))

    if args.source_dir:
        source_dir = os.path.expanduser(args.source_dir)
    else:
        source_dir = os.path.dirname(os.path.abspath(__file__))

    if not os.path.isdir(source_dir):
        print(f"ERROR: '{source_dir}' is not a directory.", file=sys.stderr)
        sys.exit(1)

    # Unchanged legacy behavior: output folders live alongside samples.
    output_dir = source_dir

    try:
        core.generate_kits(
            source_dir=source_dir,
            output_dir=output_dir,
            num_kits=args.kits,
            pads_per_kit=args.count,
            name_override=args.name,
            seed=args.seed,
            progress_cb=_cli_progress,
        )
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

**Step 2: Smoke-test**

Create a small samples dir with a handful of `.wav` files, then:

```bash
python3 mpc_random_kit.py /path/to/test/samples --kits 2 --count 8
ls /path/to/test/samples | grep RandomKit
```

Expected: two `RandomKit_*` folders created, each with an `.xpm` and 8 sample files. Progress prints like `[ 70%] Generating kit 1 of 2: (random)`.

**Step 3: Commit**

```bash
git add mpc_random_kit.py
git commit -m "Refactor CLI as thin wrapper over mpc_randokitter.core"
```

---

## Task 6: Add requirements files

**Files:**
- Create: `requirements.txt`
- Create: `requirements-build.txt`

**Step 1: `requirements.txt`**

```
# MPC RandoKitter — runtime requirements
# Note: only the GUI uses customtkinter. The CLI (mpc_random_kit.py)
# runs on the Python stdlib alone with no installs.

customtkinter>=5.0.0
```

**Step 2: `requirements-build.txt`**

```
# MPC RandoKitter — build requirements
# Install with: pip install -r requirements-build.txt

-r requirements.txt

pyinstaller>=5.0.0
```

**Step 3: Verify install works**

Run: `python3 -m pip install -r requirements.txt`
Expected: `customtkinter` installs successfully.

**Step 4: Commit**

```bash
git add requirements.txt requirements-build.txt
git commit -m "Add runtime and build requirements files"
```

---

## Task 7: Build the GUI (`mpc_randokitter/gui.py`)

**Files:**
- Create: `mpc_randokitter/gui.py`

**Step 1: Write the GUI module**

```python
"""customtkinter GUI for MPC RandoKitter."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import traceback
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from mpc_randokitter import core, __version__


SETTINGS_PATH = Path.home() / ".mpc_randokitter.json"


def _load_settings() -> dict:
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save_settings(data: dict) -> None:
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError:
        pass


def _reveal(path: str) -> None:
    """Open a folder in the OS file browser."""
    if sys.platform == "darwin":
        subprocess.Popen(["open", path])
    elif sys.platform.startswith("win"):
        subprocess.Popen(["explorer", path])
    else:
        subprocess.Popen(["xdg-open", path])


class KitterApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.title(f"MPC Random Kit Maker v{__version__}")
        self.geometry("520x460")
        self.resizable(False, False)

        settings = _load_settings()
        self._worker: threading.Thread | None = None
        self._cancel = threading.Event()
        self._last_output: str | None = None

        self._build_ui(settings)

    # ---------- UI ----------

    def _build_ui(self, settings: dict) -> None:
        pad = {"padx": 16, "pady": 6}

        ctk.CTkLabel(self, text="Samples folder", anchor="w").pack(fill="x", **pad)
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=16)
        self.source_var = ctk.StringVar(value=settings.get("source_dir", ""))
        ctk.CTkEntry(row, textvariable=self.source_var, state="readonly").pack(
            side="left", fill="x", expand=True, padx=(0, 6)
        )
        ctk.CTkButton(row, text="Browse…", width=90,
                      command=self._pick_source).pack(side="left")

        ctk.CTkLabel(self, text="Output folder", anchor="w").pack(fill="x", **pad)
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=16)
        self.output_var = ctk.StringVar(
            value=settings.get("output_dir", str(Path.home() / "Desktop"))
        )
        ctk.CTkEntry(row, textvariable=self.output_var, state="readonly").pack(
            side="left", fill="x", expand=True, padx=(0, 6)
        )
        ctk.CTkButton(row, text="Browse…", width=90,
                      command=self._pick_output).pack(side="left")

        opts = ctk.CTkFrame(self, fg_color="transparent")
        opts.pack(fill="x", padx=16, pady=(12, 0))
        ctk.CTkLabel(opts, text="Number of kits:").grid(row=0, column=0, sticky="w")
        self.kits_var = ctk.StringVar(value=str(settings.get("num_kits", 4)))
        ctk.CTkOptionMenu(opts, variable=self.kits_var,
                         values=[str(n) for n in range(1, 11)],
                         width=80).grid(row=0, column=1, padx=(8, 20))
        ctk.CTkLabel(opts, text="Pads per kit:").grid(row=0, column=2, sticky="w")
        self.pads_var = ctk.StringVar(value=str(settings.get("pads", 64)))
        ctk.CTkOptionMenu(opts, variable=self.pads_var,
                         values=["16", "32", "64", "128"],
                         width=80).grid(row=0, column=3, padx=(8, 0))

        ctk.CTkLabel(self, text="Kit name (optional)", anchor="w").pack(fill="x", **pad)
        self.name_var = ctk.StringVar(value="")
        ctk.CTkEntry(self, textvariable=self.name_var,
                     placeholder_text="leave blank for random names").pack(
            fill="x", padx=16
        )

        self.progress = ctk.CTkProgressBar(self)
        self.progress.set(0.0)
        self.progress.pack(fill="x", padx=16, pady=(18, 4))

        self.status_var = ctk.StringVar(value="Ready.")
        self.status_label = ctk.CTkLabel(self, textvariable=self.status_var,
                                         anchor="w")
        self.status_label.pack(fill="x", padx=16)

        self.reveal_btn = ctk.CTkButton(self, text="Reveal output",
                                        width=140, command=self._reveal_output)
        self.reveal_btn.pack(pady=(8, 0))
        self.reveal_btn.pack_forget()  # hidden until a job completes

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(pady=16)
        self.generate_btn = ctk.CTkButton(buttons, text="Generate",
                                          width=140, command=self._on_generate)
        self.generate_btn.grid(row=0, column=0, padx=8)
        ctk.CTkButton(buttons, text="Quit", width=100,
                      command=self._on_quit).grid(row=0, column=1, padx=8)

    # ---------- Actions ----------

    def _pick_source(self) -> None:
        path = filedialog.askdirectory(title="Pick samples folder",
                                       initialdir=self.source_var.get() or str(Path.home()))
        if path:
            self.source_var.set(path)

    def _pick_output(self) -> None:
        path = filedialog.askdirectory(title="Pick output folder",
                                       initialdir=self.output_var.get() or str(Path.home()))
        if path:
            self.output_var.set(path)

    def _reveal_output(self) -> None:
        if self._last_output and os.path.isdir(self._last_output):
            _reveal(self._last_output)

    def _on_quit(self) -> None:
        if self._worker and self._worker.is_alive():
            if not messagebox.askyesno("Quit", "A job is running. Cancel and quit?"):
                return
            self._cancel.set()
        self._persist_settings()
        self.destroy()

    def _persist_settings(self) -> None:
        _save_settings({
            "source_dir": self.source_var.get(),
            "output_dir": self.output_var.get(),
            "num_kits": int(self.kits_var.get()),
            "pads": int(self.pads_var.get()),
        })

    def _on_generate(self) -> None:
        if self._worker and self._worker.is_alive():
            # In-flight: treat as cancel
            self._cancel.set()
            self.generate_btn.configure(state="disabled", text="Cancelling…")
            return

        source = self.source_var.get().strip()
        output = self.output_var.get().strip()
        if not source or not os.path.isdir(source):
            messagebox.showerror("Missing input", "Pick a valid samples folder.")
            return
        if not output:
            messagebox.showerror("Missing input", "Pick an output folder.")
            return

        num_kits = int(self.kits_var.get())
        pads = int(self.pads_var.get())
        name = self.name_var.get().strip() or None

        self._persist_settings()
        self._cancel.clear()
        self.reveal_btn.pack_forget()
        self.progress.set(0.0)
        self.status_var.set("Starting…")
        self.generate_btn.configure(text="Cancel")

        self._worker = threading.Thread(
            target=self._run_job,
            args=(source, output, num_kits, pads, name),
            daemon=True,
        )
        self._worker.start()

    # ---------- Worker thread ----------

    def _run_job(self, source: str, output: str, num_kits: int,
                 pads: int, name: str | None) -> None:
        try:
            core.generate_kits(
                source_dir=source,
                output_dir=output,
                num_kits=num_kits,
                pads_per_kit=pads,
                name_override=name,
                progress_cb=self._progress_cb,
                cancel_event=self._cancel,
            )
            cancelled = self._cancel.is_set()
            self.after(0, lambda: self._on_done(output, cancelled, None))
        except Exception as exc:
            tb = traceback.format_exc()
            self.after(0, lambda: self._on_done(output, False, (exc, tb)))

    def _progress_cb(self, fraction: float, status: str) -> None:
        # Marshal onto the main thread — tkinter isn't thread-safe.
        self.after(0, lambda: (self.progress.set(fraction),
                               self.status_var.set(status)))

    def _on_done(self, output: str, cancelled: bool,
                 error: tuple[Exception, str] | None) -> None:
        self.generate_btn.configure(state="normal", text="Generate")
        if error:
            exc, tb = error
            self.status_var.set(f"Error: {exc}")
            self.progress.set(0.0)
            messagebox.showerror("Kit generation failed", f"{exc}\n\n{tb}")
            return
        if cancelled:
            self.status_var.set("Cancelled.")
            self.progress.set(0.0)
            return
        self._last_output = output
        self.reveal_btn.pack(pady=(8, 0))


def main() -> None:
    app = KitterApp()
    app.mainloop()


if __name__ == "__main__":
    main()
```

**Step 2: Smoke-test the GUI launches**

Run: `python3 -m mpc_randokitter.gui`
Expected: window appears titled "MPC Random Kit Maker v0.1.0". Close it with Quit.

**Step 3: End-to-end test**

- Browse to a small samples folder (~10–20 wav files)
- Pick an output folder in `/tmp`
- Set kits=2, pads=16, leave name blank
- Click Generate
- Expected: progress bar advances through scan → generate, status updates, two `RandomKit_*` folders appear in output, "Reveal output" button shows

**Step 4: Commit**

```bash
git add mpc_randokitter/gui.py
git commit -m "Add KitterApp GUI with threaded progress and cancel"
```

---

## Task 8: Create root entry point

**Files:**
- Create: `MPC_RandoKitter.py`

**Step 1: Write the thin entry-point script**

```python
#!/usr/bin/env python3
"""MPC RandoKitter — GUI entry point.

Double-click this file (or run `python3 MPC_RandoKitter.py`) to launch the
graphical kit maker. The CLI (`mpc_random_kit.py`) remains available for
power users.
"""

from mpc_randokitter.gui import main


if __name__ == "__main__":
    main()
```

**Step 2: Smoke-test**

Run: `python3 MPC_RandoKitter.py`
Expected: same window as Task 7 step 2.

**Step 3: Commit**

```bash
git add MPC_RandoKitter.py
git commit -m "Add MPC_RandoKitter.py GUI entry point"
```

---

## Task 9: Add PyInstaller spec

**Files:**
- Create: `MPC_RandoKitter.spec`

**Step 1: Write the spec (copy pattern from `../../M8_KitCreator/M8_KitCreator.spec`)**

```python
# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []
tmp_ret = collect_all('customtkinter')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['MPC_RandoKitter.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MPC_RandoKitter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
app = BUNDLE(
    exe,
    name='MPC_RandoKitter.app',
    icon=None,
    bundle_identifier='com.atanguay.mpcrandokitter',
)
```

**Step 2: Commit (build happens in next task)**

```bash
git add MPC_RandoKitter.spec
git commit -m "Add PyInstaller spec for MPC_RandoKitter"
```

---

## Task 10: Add build.sh

**Files:**
- Create: `build.sh` (copy and adapt from `../../M8_KitCreator/build.sh`)

**Step 1: Copy M8's build.sh and replace name tokens**

Substitute `M8_KitCreator` → `MPC_RandoKitter` and `m8_kitcreator` → `mpc_randokitter` throughout. Fix the line in M8's script that checks `dist/KitBasher.app` (it's stale in the source — should be `MPC_RandoKitter.app` here, and `dist/MPC_RandoKitter` on Linux).

Key sections:

```bash
#!/usr/bin/env bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# (colour helpers omitted — copy from M8's build.sh)

clean() {
    rm -rf build dist __pycache__ mpc_randokitter/__pycache__
    find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
}

build() {
    # ... Python version check, pip install -r requirements-build.txt ...
    rm -rf build dist
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OUTPUT_NAME="MPC_RandoKitter.app"
    else
        OUTPUT_NAME="MPC_RandoKitter"
    fi
    pyinstaller --clean MPC_RandoKitter.spec

    if [[ "$OSTYPE" == "darwin"* ]] && [ -d "dist/MPC_RandoKitter.app" ]; then
        echo "Built dist/MPC_RandoKitter.app"
    elif [ -f "dist/MPC_RandoKitter" ]; then
        chmod +x dist/MPC_RandoKitter
        echo "Built dist/MPC_RandoKitter"
    else
        echo "Build failed."; exit 1
    fi
}

# (usage dispatch block copied from M8's)
```

**Step 2: Make executable and run it**

```bash
chmod +x build.sh
./build.sh
```

Expected: PyInstaller runs, produces `dist/MPC_RandoKitter.app` (macOS) or `dist/MPC_RandoKitter` (Linux). No errors.

**Step 3: Smoke-test the bundle**

macOS: `open dist/MPC_RandoKitter.app` — window should appear, same as `python3 MPC_RandoKitter.py`.
Linux: `./dist/MPC_RandoKitter` — same.

**Step 4: Commit**

```bash
git add build.sh
git commit -m "Add build.sh for PyInstaller bundling"
```

---

## Task 11: Write BUILD.md

**Files:**
- Create: `BUILD.md` (trim-down of `../../M8_KitCreator/BUILD.md`)

**Step 1: Adapt M8's BUILD.md**

Copy sections verbatim with name substitutions: Overview, Quick Start, Prerequisites, Installation, Building, Build Output, Troubleshooting (excluding `Cannot find ffmpeg` / static-ffmpeg sections), Testing the Build, Distribution, GitHub Releases, Build Script Reference.

**Remove these sections** (M8-specific, not relevant here):
- "What Gets Bundled" (remove ffmpeg bullets)
- "How static-ffmpeg Works"
- Any stereo/cue-chunk references

**Keep verbatim:**
- macOS "App is damaged" / Gatekeeper / notarization
- DMG creation recipe
- Linux AppImage / tarball sections

**Step 2: Commit**

```bash
git add BUILD.md
git commit -m "Add BUILD.md with packaging and distribution docs"
```

---

## Task 12: Update README.md with Download section

**Files:**
- Modify: `README.md`

**Step 1: Add a "Download" section above "Quick start"**

Insert after the intro paragraph:

```markdown
## Download (no Python needed)

Pre-built standalone apps live on the [Releases page](https://github.com/aTanguay/MPC_RandoKitter/releases). Grab the `.dmg` (macOS) or `.tar.gz` (Linux), open the app, pick your samples folder, and click Generate. No Python install required.

## Run the GUI from source

```bash
pip install -r requirements.txt
python3 MPC_RandoKitter.py
```

## Run the CLI (zero dependencies)

```
# existing Quick start content goes here, under this heading
```
```

Keep everything else in the README intact (Options table, How it works, Tips, License).

**Step 2: Commit**

```bash
git add README.md
git commit -m "Update README with Download + GUI sections"
```

---

## Task 13: Final end-to-end verification

**No new files.** This task is a manual run-through.

**Step 1: Fresh clone simulation**

```bash
./build.sh clean
rm -rf build dist
pip install -r requirements-build.txt
./build.sh
```

Expected: clean build completes without warnings.

**Step 2: Run the bundled app**

macOS: `open dist/MPC_RandoKitter.app`

Test flow:
1. Browse to a real samples folder (~100+ files)
2. Browse to `/tmp/test_output`
3. Set kits=3, pads=64
4. Click Generate
5. Verify progress bar animates, status updates through phases
6. Click Cancel mid-run — verify partial output cleans up (or documented behavior)
7. Re-run to completion — verify 3 kits land in output folder
8. Click Reveal Output — Finder opens correct folder
9. Open one `.xpm` in MPC Desktop or inspect it in a text editor — must begin with `<?xml version="1.0" encoding="UTF-8"?>` and contain no `<Tag />` self-closing tags

**Step 3: Verify CLI still works**

```bash
python3 mpc_random_kit.py /path/to/samples --kits 1 --count 16
```

Expected: exactly the behavior it had before the refactor, output folders in the samples dir.

**Step 4: Final commit (only if anything needed fixing)**

```bash
git commit -am "Final fixes from end-to-end verification"
```

---

## Out of scope

- Unit tests (project has none; smoke tests per task are the verification).
- Windows build verification (spec should work, deferred).
- Code signing / notarization (documented in BUILD.md, not performed).
- Merging CLI + GUI codebases with M8_KitCreator (future project).
- Drag-and-drop folder targets, seed UI (intentionally omitted — see design doc).
