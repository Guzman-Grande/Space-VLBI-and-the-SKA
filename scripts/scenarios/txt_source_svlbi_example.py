#!/usr/bin/env python3
"""txt_source_svlbi_example: local adaptation of Archivo random.ipynb.
Input type: txt. Run inside the project containing omni-uv/ and data/.
Scientific parameters are retained; see README.md for documented repairs.
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from datetime import datetime

_SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = next((p for p in _SCRIPT_PATH.parents
                     if (p / 'omni-uv' / 'omniuv').is_dir()),
                    _SCRIPT_PATH.parent.parent)

def _prepare_local_run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path,
                        default=PROJECT_ROOT / 'data' / 'Fotojet.txt',
                        help='Input path; relative paths refer to the terminal directory.')
    parser.add_argument('--output', type=Path, help='Output directory (default: a new directory for each run).')
    parser.add_argument('--show', action='store_true', help='Allow figure windows.')
    parser.add_argument('--check-input', action='store_true', help='Validate the input without running OmniUV.')
    parser.add_argument('--max-nc', type=int, help='Optional FFT grid cap; changes resolution. Default: original behavior.')
    options = parser.parse_args()
    options.input = options.input.expanduser().resolve()
    if not options.input.is_file():
        parser.error(f'Input file not found: {options.input}. Use --input to select a file.')
    import numpy as _np
    try:
        pixels = _np.loadtxt(options.input, comments='#', ndmin=2)
    except (OSError, ValueError) as error:
        parser.error(f'Cannot read the pixel table: {error}')
    if pixels.size == 0 or pixels.shape[1] != 3 or not _np.isfinite(pixels).all():
        parser.error('Expected three finite numeric columns: x [arcsec], y [arcsec], flux [Jy/pixel].')
    if not _np.any(pixels[:, 2] > 0):
        parser.error('No positive-flux pixels found.')
    if options.max_nc is not None and options.max_nc < 2:
        parser.error('--max-nc must be at least 2.')
    if options.check_input:
        print(f'TXT OK: {pixels.shape[0]} rows, 3 columns; {_np.count_nonzero(pixels[:,2] > 0)} positive-flux pixels.')
        print('Input-header frequencies are not applied automatically.')
    if options.check_input:
        raise SystemExit(0)
    root = PROJECT_ROOT / 'omni-uv'
    if not (root / 'omniuv').is_dir():
        parser.error('Cannot find omni-uv/omniuv. Place this script inside your project.')
    sys.path[:0] = [str(root), str(root / 'omniuv'), str(root / 'omniuv' / 'orbital'), str(root / 'dro')]
    import matplotlib
    if not options.show:
        matplotlib.use('Agg')
        import matplotlib.pyplot as _plt
        _plt.show = lambda *args, **kwargs: None
    if options.output is None:
        options.output = PROJECT_ROOT / 'results' / 'txt_source_svlbi_example' / datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    options.output = options.output.expanduser().resolve()
    options.output.mkdir(parents=True, exist_ok=True)
    metadata = {
        'scenario': 'txt_source_svlbi_example', 'source_notebook': 'Archivo random.ipynb',
        'input_type': 'txt', 'created_at': datetime.now().astimezone().isoformat(),
        'script_sha256': hashlib.sha256(_SCRIPT_PATH.read_bytes()).hexdigest(),
        'input': str(options.input), 'input_sha256': hashlib.sha256(options.input.read_bytes()).hexdigest(),
        'python': sys.version, 'command': sys.argv,
        'note': 'Run-start record; this does not certify successful completion.',
    }
    (options.output / 'run_metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    print(f'Input: {options.input}', flush=True)
    print(f'Results: {options.output}', flush=True)
    os.chdir(options.output)
    return options

LOCAL_OPTIONS = _prepare_local_run()

# simulate_from_txt_fixed.py

import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from math import pi, cos
from omniuv import Task, Source, Image, EarthFixed, EarthOrbit, util

# ... (here goes unchanged imports, gen_ts*, image_to_omniuv_input, add_ska_mid_stations definitions) ...

# ----------------------------------------
# 1) Función para leer y recentrar el txt
# ----------------------------------------
def gen_LOVEX_scans(duration_days=28, scan_duration_h=4, orbit_period_h=26.18, scan_interval_s=60):
    #Genera timestamps para simulaciones de observaciones de VLBI con LOVEX.
    #Un scan de 4 horas cada 26.18 horas, durante 'duration_days' días.

    #Args:
    #    duration_days (int): Duración total del experimento en días.
    #    scan_duration_h (float): Duración de cada scan (en horas).
    #    orbit_period_h (float): Periodo orbital del satélite (en horas).
    #    scan_interval_s (int): Intervalo de tiempo entre puntos (en segundos).

    #Returns:
        #np.ndarray: Vector de timestamps en segundos desde t=0.
    total_seconds = duration_days * 86400
    scan_duration_s = scan_duration_h * 3600*2
    orbit_period_s = orbit_period_h * 3600

    ts = []
    t = 0
    while t < total_seconds:
        scan = t + np.arange(0, scan_duration_s, scan_interval_s)
        ts.append(scan)
        t += orbit_period_s  # avanzar al siguiente paso orbital

    return np.concatenate(ts)

def add_ska_mid_stations(band: str, stns: list):

    #Añade estaciones terrestres al arreglo según la banda SKA seleccionada.

    #Parámetros:
    #    band (str): Nombre de la banda, debe ser una de:
    #                'MID BAND 1', 'MID BAND 2', 'MID BAND 3',
    #                'MID BAND 4', 'MID BAND 5a)', 'MID BAND 5b)'
    #   stns (list): Lista a la que se añadirán las estaciones (modifica in place)

    band = band.strip().upper()

    if band == "MID BAND 1":

     #______________________ SKA MID BAND 1 (610 MHz/1.0 GHz)_______________________
     # Ef
     g = EarthFixed("Effelsberg")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([4033947.23550, 486990.79430, 4900431.00170]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(60.0)
     stns.append(g)

         # JB1
     g = EarthFixed("Jodrell Bank (Mrk 1)")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([3822846.76,-153802.28,5086285.9]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(83.0)
     stns.append(g)


            # GBT
     g = EarthFixed("Green Banck Telescope")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([882589.4102,	-4924872.342,	3943729.406]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(24.0)
     stns.append(g)


            # SM (SKA) (Radio 4 km)
     g = EarthFixed("SKA-MID core")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([5109261.392,2006742.35,-3239104.8939]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(1.55)
     stns.append(g)

           #GMRT
     g = EarthFixed("Giant Metrewave Radio Telescope")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([601519.0,6091914.0,1972645.0]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(59.0)
     stns.append(g)

    elif band in ["MID BAND 2", "MID BAND 3"]:

     #_________________________ SKA MID BAND 2 y 3 (1.4 GHz y 1.67 GHz) ________________

     # Ef
     g = EarthFixed("Effelsberg")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([4033947.23550, 486990.79430, 4900431.00170]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(20.0)
     stns.append(g)

       # JB1
     g = EarthFixed("Jodrell Bank (Mrk 1)")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([3822846.76,-153802.28,5086285.9]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(35.0)
     stns.append(g)

        # JB2
     g = EarthFixed("Jodrell Bank (Mrk 2)")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([3822846.76,-153802.28,5086285.9]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(325.0)
     stns.append(g)

         # ON-85
     g = EarthFixed("Onsala (85m)")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([3370965.879,711466.1978,5349664.201]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(310.0)
     stns.append(g)

        # ON-60
     g = EarthFixed("Onsala (60m)")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([3370965.879,711466.1978,5349664.201]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(250.0)
     stns.append(g)

         # Tr
     g = EarthFixed("Torun")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([3665296.0, 1215404.0, 5070360.0]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(250.0)
     stns.append(g)

            # GB
     g = EarthFixed("Green Banck Telescope")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([882589.4102,	-4924872.342,	3943729.406]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(10.0)
     stns.append(g)


            # T6
     g = EarthFixed("TMRT Tianma")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([-2826708.829,	4679236.997,3274667.487	]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(39.0)
     stns.append(g)

            # UR
     g = EarthFixed("Urumqi")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([228310.2129,	4631922.766,	4367064.064]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(300.0)
     stns.append(g)


            # FA (EN BANDA X NO TIENE DETECTOR) & (NO ES APUNTABLE ESTA ANTENA)
     g = EarthFixed("FAST")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([-1668526.98,5506738.85,2744897.69]))
     # Minimum elevation, in degree
     g.set_el_min_deg(30.0)
     g.set_SEFD(1.0)
     stns.append(g)


            # SM (SKA) (Radio 4 km)
     g = EarthFixed("SKA-MID core")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([5109261.392,2006742.35,-3239104.8939]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(1.55)
     stns.append(g)

          # Cm
     g = EarthFixed("Cambridge")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([3875000.0, 116000.0, 5040000.0]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(200.0)
     stns.append(g)


          # Pk
     g = EarthFixed("Parkes")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([-4554231.5380, 2816758.8656, -3454034.9686]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(40.0)
     stns.append(g)

          # Sr
     g = EarthFixed("Sardinia")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([4607985.0, 1395045.0, 4138651.0]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(67.0)
     stns.append(g)

         #GMRT
     g = EarthFixed("Giant Metrewave Radio Telescope")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([  601519.0,  6091914.0,  1972645.0 ]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(47.0)
     stns.append(g)

         #At
     g = EarthFixed("ATCA")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([ -4751642.4,  2791705.7, -3200492.6 ]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(66.0)
     stns.append(g)

         #Td
     g = EarthFixed("Tidbinbilla")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([ -4460895.0,  2682365.0, -3674747.0 ]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(47.0)
     stns.append(g)

         # VLA
     g = EarthFixed("Very Large Array")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([ -1601185.0, -5041982.0, 3554872.0 ]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(17.9)
     stns.append(g)

        # ROBLEDO (Rob-70)
     g = EarthFixed("ROBLEDO 70m")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([4849121.788,-360281.362, 4114842.901]))
     # Minimum elevation, in degree
     g.set_el_min_deg(15.0)
     g.set_SEFD(27.0)
     stns.append(g)

    elif band == "MID BAND 4":
     #_____________________________SKA MID BAND 4 (5 GHz) _______________________

     # Ef
     g = EarthFixed("Effelsberg")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([4033947.23550, 486990.79430, 4900431.00170]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(20.0)
     stns.append(g)

        # JB1
     g = EarthFixed("Jodrell Bank (Mrk 1)")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([3822846.76,-153802.28,5086285.9]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(70.0)
     stns.append(g)

          # Cm
     g = EarthFixed("Cambridge")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([3875000.0, 116000.0, 5040000.0]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(200.0)
     stns.append(g)

         # Tr
     g = EarthFixed("Torun")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([3665296.0, 1215404.0, 5070360.0]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(250.0)
     stns.append(g)

          # MC
     g = EarthFixed("Medicina")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([4461369.695,919597.124,4449559.381]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(170.0)
     stns.append(g)

          # Sr
     g = EarthFixed("Sardinia")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([4607985.0, 1395045.0, 4138651.0]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(40.0)
     stns.append(g)

            # GB
     g = EarthFixed("Green Banck Telescope")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([882589.4102,	-4924872.342,	3943729.406]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(13.0)
     stns.append(g)


            # T6
     g = EarthFixed("TMRT Tianma")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([-2826708.829,	4679236.997,3274667.487	]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(26.0)
     stns.append(g)

            # YS
     g = EarthFixed("Yebes")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([4848761.803,-261484.1746,	4123085.053]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(180.0)
     stns.append(g)

            # UR
     g = EarthFixed("Urumqi")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([228310.2129,	4631922.766,	4367064.064]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(250.0)
     stns.append(g)


            # SM (SKA) (Radio 4 km)
     g = EarthFixed("SKA-MID core")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([5109261.392,2006742.35,-3239104.8939]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(2.38)
     stns.append(g)


          # Pk
     g = EarthFixed("Parkes")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([-4554231.5380, 2816758.8656, -3454034.9686]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(110.0)
     stns.append(g)


         #GMRT
     g = EarthFixed("Giant Metrewave Radio Telescope")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([  601519.0,  6091914.0,  1972645.0 ]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(47.0)
     stns.append(g)

         #At
     g = EarthFixed("ATCA")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([ -4751642.4,  2791705.7, -3200492.6 ]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(42.0)
     stns.append(g)


         # VLA
     g = EarthFixed("Very Large Array")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([ -1601185.0, -5041982.0, 3554872.0 ]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(13.2)
     stns.append(g)

    elif band == "MID BAND 5A)":
     #___________________________ SKA MID BAND 5a) (5 GHz) ______________________
     # Ef
     g = EarthFixed("Effelsberg")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([4033947.23550, 486990.79430, 4900431.00170]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(25.0)
     stns.append(g)

        # JB1
     g = EarthFixed("Jodrell Bank (Mrk 1)")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([3822846.76,-153802.28,5086285.9]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(80.0)
     stns.append(g)

          # Cm
     g = EarthFixed("Cambridge")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([3875000.0, 116000.0, 5040000.0]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(225.0)
     stns.append(g)

          # Sr
     g = EarthFixed("Sardinia")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([4607985.0, 1395045.0, 4138651.0]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(50.0)
     stns.append(g)

            # YS
     g = EarthFixed("Yebes")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([4848761.803,-261484.1746,	4123085.053]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(180.0)
     stns.append(g)

           # T6
     g = EarthFixed("TMRT Tianma")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([-2826708.829,	4679236.997,3274667.487	]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(26.0)
     stns.append(g)

            # GB
     g = EarthFixed("Green Banck Telescope")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([882589.4102,	-4924872.342,	3943729.406]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(13.0)
     stns.append(g)


           # SM (SKA) (Radio 4 km)
     g = EarthFixed("SKA-MID core")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([5109261.392,2006742.35,-3239104.8939]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(2.38)
     stns.append(g)


          # Pk
     g = EarthFixed("Parkes")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([-4554231.5380, 2816758.8656, -3454034.9686]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(110.0)
     stns.append(g)


         #At
     g = EarthFixed("ATCA")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([ -4751642.4,  2791705.7, -3200492.6 ]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(47.0)
     stns.append(g)


         # VLA
     g = EarthFixed("Very Large Array")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([ -1601185.0, -5041982.0, 3554872.0 ]))
     # Minimum elevation, in degree
     g.set_el_min_deg(13.2)
     g.set_SEFD(13.2)
     stns.append(g)

    elif band == "MID BAND 5B)":

     #_________________________  SKA MID BAND 5b) (5 GHz) ______________________

     # Ef
     g = EarthFixed("Effelsberg")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([4033947.23550, 486990.79430, 4900431.00170]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(20.0)
     stns.append(g)


          # Cm
     g = EarthFixed("Cambridge")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([3875000.0, 116000.0, 5040000.0]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(320.0)
     stns.append(g)

            # YS
     g = EarthFixed("Yebes")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([4848761.803,-261484.1746,	4123085.053]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(220.0)
     stns.append(g)

            # UR
     g = EarthFixed("Urumqi")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([228310.2129,	4631922.766,	4367064.064]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(350.0)
     stns.append(g)

            # T6
     g = EarthFixed("TMRT Tianma")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([-2826708.829,	4679236.997,3274667.487	]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(48.0)
     stns.append(g)

        # ROBLEDO (Rob-70)
     g = EarthFixed("ROBLEDO 70m")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([4849121.788,-360281.362, 4114842.901]))
     # Minimum elevation, in degree
     g.set_el_min_deg(18.0)
     g.set_SEFD(27.0)
     stns.append(g)

       # ROBLEDO (Rob-34)
     g = EarthFixed("ROBLEDO 34m")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([4849121.788,-360281.362, 4114842.901]))
     # Minimum elevation, in degree
     g.set_el_min_deg(15.0)
     g.set_SEFD(106.0)
     stns.append(g)

            # GB
     g = EarthFixed("Green Banck Telescope")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([882589.4102,	-4924872.342,	3943729.406]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(15.0)
     stns.append(g)


            # SM (SKA) (Radio 4 km)
     g = EarthFixed("SKA-MID core")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([5109261.392,2006742.35,-3239104.8939]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(2.38)
     stns.append(g)


          # Pk
     g = EarthFixed("Parkes")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([-4554231.5380, 2816758.8656, -3454034.9686]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(43.0)
     stns.append(g)

         #At
     g = EarthFixed("ATCA")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([ -4751642.4,  2791705.7, -3200492.6 ]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(47.0)
     stns.append(g)

         # VLA
     g = EarthFixed("Very Large Array")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([ -1601185.0, -5041982.0, 3554872.0 ]))
     # Minimum elevation, in degree
     g.set_el_min_deg(13.2)
     g.set_SEFD(10.7)
     stns.append(g)

         #Td
     g = EarthFixed("Tidbinbilla")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([ -4460895.0,  2682365.0, -3674747.0 ]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(25.0)
     stns.append(g)

    else:
        raise ValueError(f"Banda no reconocida: '{band}'. Usa una de las siguientes: "
                         "'MID BAND 1', 'MID BAND 2', 'MID BAND 3', 'MID BAND 4', 'MID BAND 5a)', 'MID BAND 5b)'")

def read_pixel_txt(filepath, ra_deg, dec_deg, flux_threshold=0.0):
    data = []
    with open(filepath, 'r') as f:
        for L in f:
            if L.startswith('#') or not L.strip(): continue
            x_as, y_as, flux = map(float, L.split())
            if flux > flux_threshold:
                data.append((x_as, y_as, flux))
    x_as, y_as, fluxes = map(np.array, zip(*data))
    ra0  = ra_deg  * pi/180.0
    dec0 = dec_deg * pi/180.0
    cx = 0.5*(x_as.min()+x_as.max())
    cy = 0.5*(y_as.min()+y_as.max())
    x_as -= cx; y_as -= cy
    ra0  += cx * (pi/(180*3600)) / cos(dec0)
    dec0 += cy * (pi/(180*3600))
    ras  = ra0  + (x_as * (pi/(180*3600))) / cos(dec0)
    decs = dec0 + (y_as * (pi/(180*3600)))
    return ras, decs, fluxes, ra0, dec0

# --------------------------------------------------
# 2) Función que monta la fuente OmniUV y simula UV
# --------------------------------------------------
def simulate_txt_source(txtfile,
                        ra_deg, dec_deg,
                        ts,
                        stations,
                        freqs_hz,
                        fov_mas,
                        rmax_km):
    # Crear tarea y phase center
    task = Task()
    # —————— ¡MUST CALL set_eops() BEFORE ANY TIME CALC! ——————
    task.set_eops(
        tmu=35.0,       # valor fijo de tu ejemplo
        dut1=-2.211724,
        xp=0.02784,
        yp=0.37085
    )
    # ——————————————————————————————————————————————————————

    # Phase center:
    src = Source()
    src.name = "TXT_SOURCE"
    src.ra  = ra_deg  * pi/180
    src.dec = dec_deg * pi/180
    task.set_srcs([src])

    # Ahora ya podemos fijar los tiempos sin que pete calc_jd()
    t0 = datetime(2020, 3, 11, 0, 0, 0)
    task.set_ts(t0, ts)

    # Frecuencias, integración y ancho de banda
    task.freqs     = np.array(freqs_hz)
    task.t_ap      = 60.0
    task.bandwidth = 32e6

    # Resolución teórica en mas
    lam      = 3e8 / freqs_hz[0]
    res_mas  = 1.0/(rmax_km*1e3/lam)/1e7/pi*180*3600e3

    # Calcular cellsize (mas) y grid
    max_nc       = LOCAL_OPTIONS.max_nc or 10000
    target_cell  = res_mas/5.0
    needed_nc    = np.ceil(fov_mas/target_cell)
    if needed_nc <= max_nc:
        nc      = int(2**np.ceil(np.log2(needed_nc)))
        cell_mas = fov_mas/nc
    else:
        nc      = max_nc
        cell_mas = fov_mas/max_nc
    if LOCAL_OPTIONS.max_nc is not None and nc > LOCAL_OPTIONS.max_nc:
        nc = LOCAL_OPTIONS.max_nc
        cell_mas = fov_mas / nc
    task.nc       = nc
    task.cellsize = cell_mas  # en mas
    print(f"--> res_mas={res_mas:.3f} mas, cell={cell_mas:.3f} mas, grid={nc}, FOV={cell_mas*nc:.1f} mas")

    # Leer píxeles y recentrar
    ras, decs, fluxes, ra0, dec0 = read_pixel_txt(txtfile, ra_deg, dec_deg)

    # Offset en mas
    rad2mas = 180*3600*1000/pi
    off_x = (ras - ra0) * np.cos(dec0) * rad2mas
    off_y = (decs - dec0) * rad2mas

    # Recorte FOV en píxeles
    half = fov_mas/2.0
    ix = np.floor((off_x + half)/cell_mas + 0.5).astype(int)
    iy = np.floor((off_y + half)/cell_mas + 0.5).astype(int)
    mask = (ix>=0)&(ix<nc)&(iy>=0)&(iy<nc)
    ras, decs, fluxes = ras[mask], decs[mask], fluxes[mask]

    # Montar imagen OmniUV
    img = Image(src)
    img.ras    = ras; img.decs = decs; img.fluxes=fluxes; img.npixel=len(fluxes)
    ruvw0 = np.array([cos(dec0)*np.cos(ra0), cos(dec0)*np.sin(ra0), np.sin(dec0)])
    rqu   = np.stack([np.cos(decs)*np.cos(ras), np.cos(decs)*np.sin(ras), np.sin(decs)],axis=1)
    img.lmn = rqu.dot(ruvw0); img.ruvw = ruvw0; src.img = img

    # Estaciones y UV
    task.set_stns(stations)
    uvw_bls  = task.calc_uvw_bl(); uvw_flat = task.flat_uvw_bl(uvw_bls)
    uv      = np.vstack([uvw_flat[0][:,:2], -uvw_flat[0][:,:2]])
    bls     = task.gen_vis_fft(src)
    print(f"Vis: {sum(len(b.get('vis',[])) for b in bls)}")

    beam, out_img = task.gen_beam(bls), task.gen_image_fft(bls)[1]

    # Plot UV
    plt.figure(); plt.plot(uv[:,0]/1e7, uv[:,1]/1e7, '.', ms=1)
    plt.savefig('uv.png'); plt.close()

    # Plot imagen
    extent = [-half, half, -half, half]
    plt.figure()
    plt.imshow(out_img, origin='lower', extent=extent, cmap='inferno')
    plt.savefig('sim_image.png'); plt.close()

    return beam, uv, out_img

#===============================================================================

def main():

    # Instance of Task class. Entry of the program.
    task = Task()
    # Repair: initialize EOPs and the source before the preliminary UVW calculation.
    task.set_eops(tmu=35.0, dut1=-2.211724, xp=0.02784, yp=0.37085)
    preliminary_source = Source()
    preliminary_source.name = "TXT_SOURCE"
    preliminary_source.ra = 187.70593 * pi / 180.0
    preliminary_source.dec = 12.391123 * pi / 180.0
    task.set_srcs([preliminary_source])

    # Series de tiempo
    ts = gen_LOVEX_scans(duration_days=28, scan_duration_h=4,
                         orbit_period_h=26.18, scan_interval_s=60)

    # Estaciones

    #______________________________ EARTH ORBIT ____________________________________

    stns = []

    hh = 90000e3
    hl = 2000e3

    # Calculate semi-major and eccentricity for Earth orbit.
    a, e = util.h2ae(hl, hh, util.Re)
    print("---------------------------------------------------------------------")
    print("Earth satellite, a: %.2f x 1E4 km, e: %.2f" % (a / 1e7, e))

    # Earth orbit station
    s = EarthOrbit("SLFRO Station 1")
    # Specify the seperation of the target source from the celestial
    # object, in degree.
    # If the seperation at one moment is less than this value,
    # uvw calculations for this moment is skipped.
    # You may set multiple objects by specifying their name.
    # E.g.: set_sep_min_deg(Earth=5.0, Moon=1.0, Sun=10.0)
    # At present separation calc. with Earth, Moon and Sun are supported.
    #s.set_sep_min_deg(Earth=5.0)

    # Standard six orbital elements, a in meter, angles in radian
    # set t_ref to 2020-01-01T00:00:00 UTC
    #
    s.set_orbit(
        a=a,
        e=e,
        i=30*(np.pi / 180),
        raan=15.0,
        arg_pe=0.0,
        M0=0.0,
        t_ref=datetime(2020, 1, 1, 0, 0, 0),
    )

    # 3.6 cm, 30 m diameter
    s.set_SEFD(225.0)  # K-Band in Jy
    stns.append(s)

    s = EarthOrbit("SLFRO Station 2")

    hh = 60000e3
    hl = 2000e3

    # Calculate semi-major and eccentricity for Earth orbit.
    a, e = util.h2ae(hl, hh, util.Re)
    s.set_sep_min_deg(Earth=5.0)
    #Standard six orbital elements, a in meter, angles in radian
    #t_ref defaults to task.t0
    t0 = datetime(2020, 3, 11, 0, 0, 0)
    task.set_ts(t0, ts)
    s.set_orbit(a=a, e=e, i=-np.pi / 6, raan=15.0, arg_pe=0.0, M0=np.pi, t_ref=t0)
    #3.6 cm, 30 m diameter
    s.set_SEFD(225.0)
    stns.append(s)

    add_ska_mid_stations("MID BAND 5B)", stns)
    task.set_stns(stns)
#-------------------------------------------------------------------------------
  # Aux function to flat the uvw result
    uvw_bls = task.calc_uvw_bl()
    # src, ts, uvw(3)
    uvw_flat = task.flat_uvw_bl(uvw_bls)

    # Select uv of src 0:
    # ts, uvw(3)
    uv = uvw_flat[0][:, :2]

    # Add conjugate:
    uv = np.concatenate([uv, -uv], axis=0)

    # Ahora podemos imprimir el resto
    print("---------------------------------------------------------------------")
    uvmax = np.max(np.abs(uv), axis=0) / 1e7  # in 10^4 km
    rmax = np.max(uvmax)  # Maximum uv along certain axis

    print(
        "uv max: %.1f x 10^4 km, %.1f x 10^4 km, rmax = %.3f x 10^4 km"
        % (uvmax[0], uvmax[1], rmax)
    )
#-------------------------------------------------------------------------------

    # Ejecutar simulación
    simulate_txt_source(
        txtfile=str(LOCAL_OPTIONS.input),
        ra_deg=187.70593, dec_deg=12.391123,
        ts=ts, stations=stns,
        freqs_hz=[300e6], fov_mas=0.45*1000,
        rmax_km=rmax*1e4  # reemplaza por tu rmax
    )

if __name__ == '__main__':
    main()
