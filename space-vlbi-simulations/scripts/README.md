# Running the simulations

[Project overview](../README.md) · [Results guide](../results/README.md) · [Internship report](../docs/internship-report.pdf)

This guide describes the local workflow for the adapted Python scripts: **Ubuntu or Ubuntu under WSL2, Python 3.11, a local virtual environment, and the project's OmniUV copy**. Google Drive and Google Colab are no longer needed for execution.

The instructions use the repository layout shown in the main README. Source files, dependencies and scientific data must be available locally; copying a `.py` file alone is not a complete installation. The checked project layout has an empty root `requirements.txt`, so the commands below use **`omni-uv/requirements.txt`**. No automatic setup script or locked environment is assumed.

## 1. Prepare Ubuntu

On **Windows**, open PowerShell as administrator and install Ubuntu if WSL is not already configured:

```powershell
wsl --install -d Ubuntu
```

Restart if requested, launch Ubuntu and create your Linux username and password. If Ubuntu already works, skip this step. See [Microsoft's WSL installation guide](https://learn.microsoft.com/en-us/windows/wsl/install) for installation errors or unsupported Windows configurations.

**Run every remaining command in the Ubuntu terminal**, not at a `PS C:\...>` prompt. Native Ubuntu users can start here:

```bash
sudo apt update
sudo apt install -y build-essential git curl file python3-venv
mkdir -p ~/projects
cd ~/projects
```

`build-essential` provides the compiler and `make` needed for the SOFA library. A virtual environment isolates Python dependencies; it does not replace these system tools.

## 2. Download or open the project

Copy the repository's actual clone URL from GitHub, then run:

```bash
git clone YOUR_REPOSITORY_URL space-vlbi-simulations
cd space-vlbi-simulations
```

Replace `YOUR_REPOSITORY_URL` with that URL. Alternatively, download the repository ZIP, extract it inside `~/projects`, and open the extracted directory. Keep the complete folder structure.

For the original author's existing checkout, the command is:

```bash
cd "$HOME/projects/SVLBI Intership/space-vlbi-simulations"
```

Use the path that actually exists on your computer; do not create a second copy unnecessarily. From this point, commands assume the **project root** as the working directory.

Required resources include:

```text
omni-uv/omniuv/__init__.py
omni-uv/tool.py
omni-uv/requirements.txt
omni-uv/data/de421.bsp
omni-uv/data/moon_pa_de421_1900-2050.bpc
omni-uv/data/sofa/Makefile
```

The ephemerides belong to OmniUV's resources; PNG/TXT sky models belong in the project's `data/`. Do not silently replace a customized `omni-uv/` directory with a fresh upstream checkout: the local copy may contain required adaptations. If resource files are absent from a download, obtain the matching project resources before running.

## 3. Create the Python environment once

This workflow uses [uv](https://docs.astral.sh/uv/getting-started/installation/) to install Python and create a virtual environment. **uv, the environment manager, and OmniUV, the astronomy toolkit, are different tools.**

If `uv` is not installed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"
```

Then, from the project root:

```bash
uv python install 3.11
uv venv --python 3.11 --seed .venv
source .venv/bin/activate
python -m pip install -r omni-uv/requirements.txt
python -m pip install Pillow
```

Skip environment creation if this checkout already has a working `.venv`; simply activate it. Python 3.11 matches the environment used during the local migration. A different Windows Python installation is independent of WSL, and Python 3.14 compatibility has not been established for these scripts.

Check the active interpreter:

```bash
python --version
which python
```

The interpreter path should end in this project's `.venv/bin/python`. Keep `.venv/` out of Git: each user creates it locally.

## 4. Build SOFA for this computer

From the project root:

```bash
make -B -C omni-uv/data/sofa
file omni-uv/data/sofa/libsofa_c.so
```

This uses the supplied Makefile to compile the C library on the current Linux system. `-B` forces rebuilding, which avoids reusing an incompatible binary copied from another platform. The resulting library should be an **ELF shared object** for your machine's architecture.

An `invalid ELF header` error means the existing file cannot be loaded as the expected Linux library; rebuilding from the supplied sources resolved this during the migration. Rebuild when moving to another operating system or architecture. This step is normally unnecessary for every simulation run.

## 5. Check that OmniUV uses local resource paths

The migration replaced absolute Colab paths such as `/content/drive/MyDrive/...` in `omni-uv/omniuv/util.py`. A portable resource root can be derived from that file:

```python
from pathlib import Path

path_home = str(Path(__file__).resolve().parent.parent)
```

At the existing ephemeris-loading statements, the corresponding paths should be:

```python
spk = SPK.open(str(Path(path_home) / "data" / "de421.bsp"))
pck = PCK.open(str(Path(path_home) / "data" / "moon_pa_de421_1900-2050.bpc"))
path_libsofa = str(Path(path_home) / "data" / "sofa" / "libsofa_c.so")
```

These are **replacement statements at their original locations**, with existing indentation preserved—not a separate file to append. Keep the surrounding loading logic. If your copy is already patched, do not repeat the changes.

Run this import/resource check from the project root:

```bash
python - <<'PY'
from pathlib import Path
import ctypes
import sys

root = Path("omni-uv").resolve()
sys.path[:0] = [str(root), str(root / "omniuv"),
               str(root / "omniuv" / "orbital"), str(root / "dro")]
from jplephem.spk import SPK
from jplephem.pck import PCK

planetary = SPK.open(str(root / "data" / "de421.bsp"))
planetary.close()
print("Planetary ephemerides OK")
lunar = PCK.open(str(root / "data" / "moon_pa_de421_1900-2050.bpc"))
lunar.close()
print("Lunar ephemerides OK")
ctypes.CDLL(str(root / "data" / "sofa" / "libsofa_c.so"))
print("SOFA OK")
import omniuv
print("OmniUV import OK")
PY
```

The PCK object is closed explicitly because the version encountered during setup did not support a `with PCK.open(...)` context manager. Passing this check establishes resource readability and importability; it does not validate the scientific output of a full simulation.

## 6. Choose the script and its input type

List your actual filenames before running:

```bash
find scripts -type f -name '*.py' | sort
```

The supplied adaptations use these names. They can be organized under `Jet/`, `SMBHM87/` or `scenarios/`; choose the path in your checkout.

| Script basename | Input | Purpose / provenance |
|---|---|---|
| `fotojet_simulation.py` | TXT | Original local jet adaptation; check its root-path note below if moved into a subfolder. |
| `fotojet_custom_array_1p4ghz.py` | TXT | Custom jet-array example at 1.4 GHz. |
| `fotojet_custom_array_300mhz.py` | TXT | Custom jet-array example at 300 MHz. |
| `txt_source_svlbi_example.py` | TXT | Reconstructed exploratory example from an incomplete notebook. |
| `lagrange_point_svlbi.py` | PNG | Lagrange-point SVLBI example. |
| `lagrange_point_svlbi_explicit_ephemeris.py` | PNG | Variant retaining explicit planetary-ephemeris initialization. |
| `lovex_lunar_and_lagrange_array.py` | PNG | Hybrid lunar-orbit/Lagrange-point scenario, not a pure LOVEX mission model. |
| `lovex.py` | PNG | LOVEX-inspired example. |
| `sera.py` | PNG | SERA-inspired frequency exploration. |
| `slfro.py`, `radio_astron.py`, `prueba_i.py` | PNG | Earlier notebook-derived examples; inspect the actual station setup rather than inferring it from the filename. |

`radio_astron.py` and `slfro.py` came from identical simulation cells in the supplied notebooks. They should not be presented as two independently implemented mission models. Frequencies in exploratory scripts can extend beyond a mission's actual receiver bands.

### TXT sources

The jet adapters expect three numeric columns:

```text
# x_offset_arcsec y_offset_arcsec flux_Jy_per_pixel
0.000  0.000  0.020
0.001  0.002  0.015
```

The three values represent position offsets and flux density per model pixel. The adapter applies its own recentering, threshold and grid mapping. Comment headers do not configure the observing frequency: the frequency selected in the Python code controls the simulation. Check the adapter before substituting a differently formatted catalogue.

### PNG sources

The image is converted into a brightness template using grayscale values, resizing, a threshold, and the angular and flux scales set in the script. A readable PNG is not automatically a calibrated radio source. Verify orientation, field of view, intensity normalization and any background or annotations before using a new image.

Pass the correct source explicitly with `--input`; renaming a TXT file to `.png`, or the reverse, does not convert it.

## 7. Validate, then run

For a PNG scenario placed in `scripts/scenarios/`:

```bash
python scripts/scenarios/lagrange_point_svlbi.py --help
python scripts/scenarios/lagrange_point_svlbi.py \
  --input data/m87_image_normalized.png --check-input
python scripts/scenarios/lagrange_point_svlbi.py \
  --input data/m87_image_normalized.png
```

For a TXT scenario:

```bash
python scripts/scenarios/fotojet_custom_array_1p4ghz.py \
  --input data/Fotojet.txt --check-input
python scripts/scenarios/fotojet_custom_array_1p4ghz.py \
  --input data/Fotojet.txt
```

Adjust the script path and input filename to your checkout. On Linux, `Fotojet.txt` and `fotojet.txt` are different names. Quote paths containing spaces.

| Option | Effect |
|---|---|
| `--input PATH` | Selects the PNG or TXT input. Relative paths are interpreted from the terminal's current directory. |
| `--output PATH` | Selects an output directory. Use a new folder to avoid overwriting files with repeated names. |
| `--check-input` | Validates the input without running the simulation; does not certify physical scale, station setup or full dependency compatibility. |
| `--show` | Enables figure windows where a graphical display is available. Omit it for file-only runs. |
| `--max-nc N` | Available in the adapted TXT scripts. Caps the FFT grid; it changes numerical sampling and is not a scientifically equivalent shortcut. |

The wrappers normally create timestamped output directories under `results/`. The newer wrappers also write `run_metadata.json` when a run starts. That file can exist even if the simulation later fails. The script's `--help` is the authority for its available options.

Large grids can exhaust laptop memory. One 10,000 × 10,000 float64 array alone occupies about 0.8 GB; imaging can allocate several arrays and complex-valued buffers. If you reduce a TXT grid for a trial run, document the changed sampling and compare its results cautiously. PNG wrappers do not expose `--max-nc`.

## 8. What to change for a new experiment

The command-line options manage inputs and outputs. Scientific settings generally remain inside each script: frequency list, source position, observing dates and scans, station selection, orbit parameters, sensitivity, image scale and noise settings. Inspect the function calls that actually execute, as well as the helper definitions.

Before reporting a result, record the values used and verify that each requested ground station was actually added. Two supplied variants—`fotojet_custom_array_300mhz.py` and `lovex_lunar_and_lagrange_array.py`—retain a case mismatch between `MID BAND 5b)` and the helper's `MID BAND 5B)` branch. Correct the call to match the intended branch and check the resulting array before interpreting a ground-plus-space simulation. This repair changes the realized station configuration and should be recorded.

The `txt_source_svlbi_example.py` adaptation restored missing helper functions, imports and initialization from related notebooks. Treat it as an exploratory reconstruction pending scientific validation.

### Moving the earliest jet script into `Jet/`

The earliest `fotojet_simulation.py` used a fixed parent-directory assumption. If it is moved from `scripts/` into `scripts/Jet/`, replace that `PROJECT_ROOT` assignment with ancestor discovery:

```python
PROJECT_ROOT = next(
    parent for parent in Path(__file__).resolve().parents
    if (parent / "omni-uv" / "omniuv").is_dir()
)
```

The script must remain inside the project. The later scenario adaptations already search for an ancestor containing `omni-uv/omniuv`.

## Everyday use and VS Code

After the one-time setup, each new Ubuntu terminal session only needs:

```bash
cd "$HOME/projects/SVLBI Intership/space-vlbi-simulations"
source .venv/bin/activate
python scripts/scenarios/lagrange_point_svlbi.py --input data/m87_image_normalized.png
```

Substitute your own checkout path and desired script. Leave the environment with `deactivate` when finished.

For VS Code, install it on Windows with its **WSL extension**, open the project from Ubuntu using `code .`, and select the project's `.venv/bin/python` interpreter in the WSL window. See [VS Code's WSL guide](https://code.visualstudio.com/docs/remote/wsl). From Ubuntu, `explorer.exe .` opens the current Linux directory in Windows Explorer; it does not create or synchronize another copy.

## Troubleshooting

| Symptom | Check |
|---|---|
| `invalid ELF header` | Rebuild SOFA in Ubuntu and inspect the resulting library with `file`. |
| `No module named ...` | Activate `.venv`, verify `which python`, then check requirements and the local OmniUV directory layout. |
| A path still starts with `/content/drive/` | Replace the remaining Drive dependency with the corresponding local path. |
| `PCK` context-manager error | Use explicit `open` and `close`, as in the resource check. |
| Input file not found | Check filename case, current directory and `--input`; quote spaces. |
| Process is killed or memory usage grows sharply | Inspect grid size and memory requirements; a smaller trial grid changes the calculation. |
| No figure windows appear | File-only output is the default; inspect the output directory or use `--show` with a display. |
| UV tracks do not match the expected array | Inspect executed station calls, band-label spelling, schedules and visibility constraints. |

## Preserve a reproducible environment

Keep the exact script and source model alongside a run record, and record the dependency versions after a successful setup:

```bash
python -m pip freeze > results/environment-used.txt
```

Also record the repository revision and any uncommitted scientific edits. This version list is useful provenance, but does not include system compilers or external data and is not a complete cross-platform lockfile. Full simulation validation and exact reproduction of every report figure remain separate from syntax, input and import checks.
