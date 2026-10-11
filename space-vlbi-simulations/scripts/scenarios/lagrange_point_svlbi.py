#!/usr/bin/env python3
"""lagrange_point_svlbi: local adaptation of LAGRANGE FINAL.ipynb.
Input type: png. Run inside the project containing omni-uv/ and data/.
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
                        default=PROJECT_ROOT / 'data' / 'm87_image_normalized.png',
                        help='Input path; relative paths refer to the terminal directory.')
    parser.add_argument('--output', type=Path, help='Output directory (default: a new directory for each run).')
    parser.add_argument('--show', action='store_true', help='Allow figure windows.')
    parser.add_argument('--check-input', action='store_true', help='Validate the input without running OmniUV.')
    # PNG grid settings remain exactly as in the original notebook.
    options = parser.parse_args()
    options.input = options.input.expanduser().resolve()
    if not options.input.is_file():
        parser.error(f'Input file not found: {options.input}. Use --input to select a file.')
    from PIL import Image as _PILImage
    try:
        with _PILImage.open(options.input) as image:
            if image.format != 'PNG':
                parser.error('Expected a valid PNG image.')
            image.load()
            dimensions, mode = image.size, image.mode
            intensity_range = image.convert('L').getextrema()
    except (OSError, ValueError) as error:
        parser.error(f'Cannot read the PNG: {error}')
    if options.check_input:
        print(f'PNG OK: {dimensions[0]} x {dimensions[1]} pixels; mode={mode}; grayscale range={intensity_range}.')
        print('This checks image readability, not angular scale or flux calibration.')
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
        options.output = PROJECT_ROOT / 'results' / 'lagrange_point_svlbi' / datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    options.output = options.output.expanduser().resolve()
    options.output.mkdir(parents=True, exist_ok=True)
    metadata = {
        'scenario': 'lagrange_point_svlbi', 'source_notebook': 'LAGRANGE FINAL.ipynb',
        'input_type': 'png', 'created_at': datetime.now().astimezone().isoformat(),
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


import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from PIL import Image as PILImage
from tool import *

# Specify the path that contains the omniuv package.
# Necessary when your source code and the pacakge are not in the same
# folder.
# Local import paths are configured in the header.

# Import the specific OmniUV package
from omniuv import *

with_moon = True

#________________________________SNAPSHOT TIME__________________________________

def gen_ts1():
    ts = 86400 * 0.0 + np.arange(0, 24 * 60 * 60, 60, dtype=float)
    return ts


def gen_ts2():
    # 2s AP, 1 hour per day, 28 days /ADEMÁS, ESTE LO USAREMOS CUANDO HAY SATÉLITES
    # EN TORNO A LA TIERRA
    ts = []
    for i in range(28):
    #for i in [0, 7, 14, 21]:
        _ts = (i + 0.5) * 86400 + np.arange(0, 3600, 60, dtype=float)
        ts.append(_ts)
    ts = np.concatenate(ts)
    return ts

#def gen_Radio_Astron_scans_mes():

    #Genera timestamps para simulaciones de observaciones VSOP
    #durante 28 días, con 2 scans de 4 horas (4*3600 s) por día.

    #Devuelve:
    #array de timestamps en segundos desde epoch 0
    #ts = []
    #for i in range(28):  # 28 días
    #    # Inicio de la sesión diaria a mediodía (0.5 * 86400 s)
    #    _ts = (i + 0.5) * 86400 + np.arange(0, 2*4*3600, 300, dtype=float)
    #    ts.append(_ts)
    #ts = np.concatenate(ts)
    #return ts
#----------------------------- RADIO ASTRON ------------------------------------
def gen_Radio_Astron_scans_mes():

    #Genera timestamps para simulaciones de observaciones con RadioAstron:
    #2 scans diarios de 4 horas, durante 28 días, con un punto cada 60 s.

    ts = []
    scan_duration = 4 * 3600  # 4 horas en segundos
    scan_interval = 60        # resolución temporal: cada 60 s

    for day in range(28):
        base_time = day * 86400  # inicio del día en segundos

        # Primer scan del día: comienza a las 00:00 UTC
        scan1 = base_time + np.arange(0, scan_duration, scan_interval)
        ts.append(scan1)

        # Segundo scan del día: por ejemplo, empieza a las 12:00 UTC
        scan2_start = base_time + 12 * 3600  # 12h después
        scan2 = scan2_start + np.arange(0, scan_duration, scan_interval)
        ts.append(scan2)

    ts = np.concatenate(ts)
    return ts

def gen_LOVEX_scans(duration_days=28, scan_duration_h=2, orbit_period_h=26.18, scan_interval_s=60):
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

def print_radioastron_scan_info():
    scans = gen_LOVEX_scans()
    n_scans_total = int(len(scans) / (4 * 3600 / 60))  # puntos por scan
    print("---------------------------------------------------------------------")
    print("SLFRO simulated scans:")
    print(f"    Total days simulated   :365")
    print(f"    Orbital period          : 26.18 hours")
    print(f"    Scans per period          : 1")
    print(f"    Duration per scan      : 2 hours")
    print(f"    Time resolution        : 60 seconds")
    print(f"    Number of timestamps   : {len(scans)}")
    print(f"    Total scans simulated  : {n_scans_total}")
    return scans
#-------------------------------------------------------------------------------
def gen_ts3():
    # 2s AP, 0.5 hour per day, twice per day, 28 days
    ts = []
    for i in range(28):
        #    for i in [0, 7, 14, 21]:
        _ts = (i) * 86400 + np.arange(0, 900, 60, dtype=float)
        ts.append(_ts)
        _ts = (i + 0.5) * 86400 + np.arange(0, 900, 60, dtype=float)
        ts.append(_ts)
    ts = np.concatenate(ts)
    return ts

#import numpy as np
#from PIL import Image
from math import pi, cos
#import util  # Debes tener mas2rad() y crs2rqu() o usar el ejemplo que doy abajo              total_size_ma=None

def image_to_omniuv_input(image_path,
                          task,total_size_ma,
                          ra_deg=187.705930, dec_deg=12.391123,
                          flux_max_jy=0.5, flux_threshold=0.01,outfile="entrada_Omni_UV"):

    #Convierte una imagen en escala de grises a una entrada compatible con OmniUV,
    #incluyendo cálculo automático del vector ruvw0 a partir de RA/DEC.

    #Parámetros:
    #- image_path: Ruta a la imagen (JPG/PNG normalizada)
    #- ra_deg, dec_deg: RA/DEC en grados
    #- total_size_mas: tamaño angular total de la imagen en milisegundos de arco
    #- flux_max_jy: flujo máximo arbitrario
    #- flux_threshold: umbral para descartar píxeles débiles


    # Convertir RA/DEC a radianes
    ra0 = ra_deg * pi / 180.0
    dec0 = dec_deg * pi / 180.0

    # Calcular vector ruvw0
    ruvw0 = np.array([
        np.cos(dec0) * np.cos(ra0),
        np.cos(dec0) * np.sin(ra0),
        np.sin(dec0)
    ])

    # --- CORRECCIÓN AQUÍ: usar tamaño de campo de visión según el simulador ---
    if total_size_ma is None:
        diameter_mas = task.cellsize * task.nc
    else:
        diameter_mas = total_size_ma

    # 1. Leer imagen y convertir a intensidad
    img = PILImage.open(image_path).convert("L")
    img = img.resize((task.nc, task.nc))  # Redimensionar imagen al tamaño de la malla
    img_data = np.array(img, dtype=np.float32) / 255.0
    img_data *= flux_max_jy

    # 2. Escala angular por píxel
    h, w = img_data.shape
    cellsize_mas = diameter_mas / h
    dra = util.mas2rad(cellsize_mas)  # en radianes
    ddec = dra

    print(f"[INFO] Cell size: {cellsize_mas:.5f} mas, dra = {dra:.2e} rad")

    # 3. Índices de píxel
    y, x = np.indices((h, w))
    dx = x - w // 2
    dy = y - h // 2

    # 4. Coordenadas RA/DEC por píxel
    mask = img_data > flux_threshold
    fluxes = img_data[mask]
    ras = ra0 + dx[mask] * dra / cos(dec0)
    decs = dec0 + dy[mask] * ddec

    # 5. Convertir a vectores lmn
    def crs2rqu_batch(ra, dec):
        return np.stack([
            np.cos(dec) * np.cos(ra),
            np.cos(dec) * np.sin(ra),
            np.sin(dec)
        ], axis=1)

    rqu = crs2rqu_batch(ras, decs)
    lmn = np.dot(rqu, ruvw0)

    #Filtrado de puntos fuera de los bordes de la malla
    rad2mas = 180 * 3600 * 1000 / np.pi
    offset_ra_mas = (ras - ra0) * np.cos(dec0) * rad2mas
    offset_dec_mas = (decs - dec0) * rad2mas
    ix = (offset_ra_mas + diameter_mas / 2) / task.cellsize
    iy = (offset_dec_mas + diameter_mas / 2) / task.cellsize

    valid = (ix >= 0) & (ix < task.nc) & (iy >= 0) & (iy < task.nc)

    # Aplicar filtro
    ras = ras[valid]
    decs = decs[valid]
    fluxes = fluxes[valid]
    lmn = lmn[valid]

   # Crear objeto de fuente si hace falta
    src = Source()
    src.name = "M87"
    src.ra = ra0
    src.dec = dec0
    src.ruvw=ruvw0

    # Crear objeto imagen
    omni_img = Image(src)
    omni_img.ras = ras
    omni_img.decs = decs
    omni_img.fluxes = fluxes
    omni_img.npixel = len(fluxes)
    omni_img.lmn = lmn
    omni_img.ruvw = ruvw0


    # Reproducimos el mapa de imagen en coordenadas relativas (mas)
    extent_mas = [
        -task.cellsize * task.nc / 2,
         task.cellsize * task.nc / 2,
        -task.cellsize * task.nc / 2,
         task.cellsize * task.nc / 2,
    ]

    plt.figure(figsize=(6, 6))
    im = plt.imshow(img_data, origin='lower', extent=extent_mas,
                    cmap='inferno', aspect='equal')

    plt.xlabel("ΔRA (mas)")
    plt.ylabel("ΔDec (mas)")
    plt.title("Imagen proyectada de entrada a OmniUV")
    plt.gca().invert_xaxis()  # estándar astronómico: RA decrece a la derecha

    cbar = plt.colorbar(im, fraction=0.046, pad=0.04)
    cbar.set_label("Flujo (Jy/píxel)")
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.tight_layout()
    plt.savefig(outfile)
    plt.close()

    print(f"[INFO] Imagen adaptada al FOV = {diameter_mas:.3f} mas con resolución {cellsize_mas:.5f} mas/pixel")
    print(f"[INFO] Se usarán {omni_img.npixel} píxeles con flujo > {flux_threshold:.2f} Jy")
    return omni_img

#============================= EARTH FIXED STATIONS ============================

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

    elif band == "MID BAND 7":

             # VLA
     g = EarthFixed("Very Large Array")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([ -1601185.0, -5041982.0, 3554872.0 ]))
     # Minimum elevation, in degree
     g.set_el_min_deg(13.2)
     g.set_SEFD(54)
     stns.append(g)

                 # YS
     g = EarthFixed("Yebes")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([4848761.803,-261484.1746,	4123085.053]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(340.0)
     stns.append(g)

                 # T6
     g = EarthFixed("TMRT Tianma")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([-2826708.829,	4679236.997,3274667.487	]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(120.0)
     stns.append(g)

         # Ef
     g = EarthFixed("Effelsberg")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([4033947.23550, 486990.79430, 4900431.00170]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(200.0)
     stns.append(g)

         # GB
     g = EarthFixed("Green Banck Telescope")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([882589.4102,	-4924872.342,	3943729.406]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(200.0)
     stns.append(g)

          # SM (SKA) (Radio 4 km)
     g = EarthFixed("SKA-MID core")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([5109261.392,2006742.35,-3239104.8939]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(15)
     stns.append(g)

         # ALMA (hipotético en banda de 7 mm / 43 GHz)
     g = EarthFixed("ALMA")
     g.set_trs(np.array([2225056.149, -5441193.100, -2481687.017]))
     g.set_el_min_deg(5.0)
     g.set_SEFD(100.0)
     stns.append(g)

    else:
        raise ValueError(f"Banda no reconocida: '{band}'. Usa una de las siguientes: "
                         "'MID BAND 1', 'MID BAND 2', 'MID BAND 3', 'MID BAND 4', 'MID BAND 5a)', 'MID BAND 5b)','7mm'")




#===============================================================================

def main():
    # Instance of Task class. Entry of the program.
    task = Task()



#________________________________ SOURCE _______________________________________
    # OmniUV supports uvw calculations for multiple sources.
    # Aquí se crea una lista vacía srcs que almacenará todas las fuentes (targets) que quieres observar o simular.
    srcs = []

    # Instance of Source class.
    # "src" here refers to phase center

    #Se crea una instancia de la clase Source(), que representa
    #una fuente astronómica puntual (como una estrella, cuásar o el centro de una galaxia)
    # phase center” quiere decir que esta fuente será el punto central respecto
    # al cual se calcularán las fases de las visibilidades.
    #src = Source()
    #src.name = "T1"

    # ra and dec are provided in radian
    #src.ra = 180.0 / 180.0 * np.pi
    #src.dec = 60.0 / 180.0 * np.pi
    #srcs.append(src)  # Se añade la fuente a la lista de fuentes

    src=Source()
    src.name=   'M87'
    src.ra   =   187.705930 / 180.  * np.pi
    src.dec  =   12.391123 / 180. * np.pi
    srcs.append(src)

    #    src     =   Source()
    #    src.name=   'SouthPole'
    #    src.ra   =  0.0
    #    src.dec  =  -np.pi/2
    #    srcs.append(src)
    #

    # Register srcs in task.
    task.set_srcs(srcs)

    # If you are not familier with EOPs, set them to 0
    tmu = 35.0
    dut1 = -2.211724
    xp = 0.027840
    yp = 0.370850
    task.set_eops(tmu=tmu, dut1=dut1, xp=xp, yp=yp)

    # Starting date and time
    t0 = datetime(2020, 3, 11, 0, 0, 0)

    # Time series to calculate coordinate and uvw, as offset to t0,
    # in second.
    # Two functions provides different schedule.
    if with_moon:
        ts = gen_LOVEX_scans(duration_days=28, scan_duration_h=4, orbit_period_h=26.18, scan_interval_s=60)
    else:
        ts = gen_Radio_Astron_scans_mes
    # Register time series
    task.set_ts(t0, ts)


#______________________________ EARTH ORBIT ____________________________________

    stns = []

    #hh = 90000e3
    #hl = 2000e3

    # Calculate semi-major and eccentricity for Earth orbit.
    #a, e = util.h2ae(hl, hh, util.Re)
    a=7e8
    e=0.7
    print("---------------------------------------------------------------------")
    print("Earth satellite, a: %.2f x 1E4 km, e: %.2f" % (a / 1e7, e))

    #---------------------------------------------------------------------------
    # Earth orbit station
    #s = EarthOrbit("TRIASTRON 1")
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
    #s.set_orbit(
    #    a=a,
    #    e=e,
    #    i=77.6*(np.pi / 180),
    #    raan=97.5,
    #    arg_pe=90,
    #    M0=180.0,
    #    t_ref=datetime(2020, 1, 1, 0, 0, 0),
    #)
    #s.set_SEFD(225.0)
    #stns.append(s)

    #s = EarthOrbit("TRIASTRON 2")

    #s.set_orbit(
    #    a=a,
    #    e=e,
    #    i=77.6*(np.pi / 180),
    #    raan=217.5,
    #    arg_pe=90,
    #    M0=300.0,
    #    t_ref=datetime(2020, 1, 1, 0, 0, 0),
    #)
    #s.set_SEFD(225.0)
    #stns.append(s)

    #s = EarthOrbit("TRIASTRON 3")

    #s.set_orbit(
    #    a=a,
    #    e=e,
    #    i=77.6*(np.pi / 180),
    #    raan=337.5,
    #    arg_pe=90,
    #    M0=60.0,
    #    t_ref=datetime(2020, 1, 1, 0, 0, 0),
    #)
    #s.set_SEFD(225.0)
    #stns.append(s)
    #---------------------------------------------------------------------------
    # 3.6 cm, 30 m diameter
    #s.set_SEFD(225.0)  # K-Band in Jy
    #stns.append(s)

    #s = EarthOrbit("SLFRO Station 2")

    #hh = 60000e3
    #hl = 2000e3

    # Calculate semi-major and eccentricity for Earth orbit.
    #a, e = util.h2ae(hl, hh, util.Re)
    #s.set_sep_min_deg(Earth=5.0)
    #Standard six orbital elements, a in meter, angles in radian
    #t_ref defaults to task.t0
    #s.set_orbit(a=a, e=e, i=-np.pi / 6, raan=15.0, arg_pe=0.0, M0=np.pi, t_ref=t0)
    #3.6 cm, 30 m diameter
    #s.set_SEFD(225.0)
    #stns.append(s)

#________________________________ EARTH FIXED __________________________________

    add_ska_mid_stations("MID BAND 7", stns)
    task.set_stns(stns)

#__________________________________ LUNAR FIXED ________________________________

    # Lunar fixed, far side of the moon
    # Please contact the author (liulei@shao.ac.cn) for collaboration.
    #    lf   =   LunarFixed('M1')
    # Set lunar fixed frame coordinate (Principal Axis)
    # This one in the farside of the Moon
    #    lf.set_lfs(np.array([-util.Rm, 0.0, 0.0]))
    #    lf.set_el_min_deg(15.0)
    # Specify the celestial object that you want to calculate the
    # seperation and availabilty accordingly.
    #    lf.set_sep_min_deg(Earth=5.0)
    #    lf.set_SEFD(2028.0)
    #    if with_moon:
    #        stns.append(lf)

#__________________________________ LUNAR ORBIT ________________________________

     # Lunar orbit
    #lo = LunarOrbit("LOVEX ")
    #lo.set_sep_min_deg(Moon=1.0, Sun=10.0)

    #hl = 1991.69e3- util.Rm
    #hh = 18678.5e3- util.Rm

    # Calculate semi-major and eccentricity for Earth orbit.
    #a, e = util.h2ae(hl, hh, util.Rm)
    # t_ref defaults to task.t0
    #lo.set_orbit(
    #    a=a,
    #    e=e,
    #    i=119.25*(np.pi / 180),
    #    raan=0.0,
    #    arg_pe=0.0,
    #    M0=0.0,
    #   t_ref=t0,
    #)
    #lo.set_SEFD(200)
    #if with_moon:
        #stns.append(lo)

    l2_es = EarthSunL2("EarthSun L2")
    l2_es.set_sep_min_deg(Earth=5.0)
    l2_es.set_SEFD(30000)
    stns.append(l2_es)

    l2_me = MoonEarthL2("me")
    l2_me.set_sep_min_deg(Moon=1.0)
    l2_me.set_SEFD(30000)
    if with_moon:
        stns.append(l2_me)
#_______________________________________________________________________________

    # Gain error, see Explanation of Eq. 4.
    task.gain_error = 0.1  # Es la Yi(t) de la que depende la Ganancia Gi(t).
                           # Se deja como un parámetro libre

    # Register all stations
    task.set_stns(stns)

#-------------------------------------------------------------------------------

         #Calcula las coordenadas uvw de todas las líneas base (pares de estaciones),
         #para cada fuente y cada instante temporal

    # Calculate baseline uvw, in the shape (bl, target, nt, 3(uvw))
    # Assuming there are 3 stations, 2 targets.
    # The baseline (bl) indices are:
    # bl0: stn0-stn1, bl1: stn0 - stn2, bl2: stn1 - stn2
    #    uvw_bl = uvw_bls[2][1]
    # retrieves a 2-D array in the shape (nt, 3) for baseline stn1-stn2
    # of source 1 (0 indexed).
    uvw_bls = task.calc_uvw_bl()

    # One may also retrieve the station crs coordinate and uvw data
    # explicitely:
    #    stn     =   task.stns[0]
    #    p_crs   =   stn.calc_crs()
    #    uvw     =   stn.calc_uvw()

    # Note! uvw is calculated only when both stations are available.
    # OmniUV provides a list that contains the indices of the available
    # moments in ts for all baselines and srcs:
    #    idt_bls =   task.idt_avail
    # idt_bl retrives the indices of avail. moments for bl 2, src 1:
    #    idt_bl =   idt_bls[2][1]
    # The corresponding time in ts array could be retrived as:
    #    ts_avail    =   task.ts[idt_bl]
#-------------------------------------------------------------------------------

          #Aplana los datos uvw para facilitar el trabajo con ellos.

          #Toma los componentes u y v (ignorando w) para la fuente 0.

          #Añade los conjugados (simetría necesaria en el espacio uv).

    # Aux function to flat the uvw result
    # src, ts, uvw(3)
    uvw_flat = task.flat_uvw_bl(uvw_bls)

    # Select uv of src 0:
    # ts, uvw(3)
    uv = uvw_flat[0][:, :2]

    # Add conjugate:
    uv = np.concatenate([uv, -uv], axis=0)

    # Plot to check CRS and LCS calculation result
    # Refer to the corresponding functions in tool.py to find out how
    # these data are retrived.
    #    tool.plot_crs(task)
    #    tool.plot_lcs(task)

#-------------------------------------------------------------------------------

          # CONFIGURACIÓN DE FRECUENCIAS Y RESOLUCIÓN ANGULAR

    # Define la frecuencia de observación (8.4 GHz), el tiempo de integración y el ancho de banda.
    # Estos parámetros influyen tanto en el ruido como en el cálculo de resolución. Eq (4) y (5)


    ##### Parameters for vis calculatio and imaging ######

    # Sky frequency of each IF. The wave length of each IF is calculated with these
    # frequenceis and has ** nothing ** to do with the bandwidth.


    task.freqs = np.array([1.4e9,6e9,8e9,9e9,43e9,289e9])  # in Hz   289e9
                                        # Aquí se almacenan las frecuencias que queremos estudiar.
                                        # Podemos incluir un puñado de ellas. Más abajo se puede
                                        # elegir con cual se quiere trabajar.

    # t_ap and bandwidth are ** only ** used for calculating system
    # noise. See Eq. 5 of the paper. (SOLO SE UTILIZA PARA EL CÁLCULO DEL RUIDO)

    # Accumulation period (integration time) {SNAPSHOT TIME (TIEMPO DE EXPOSICIÓN)}
    task.t_ap = 600  # in second, could be float, e.g. 0.128

    # Bandwidth of each IF
    task.bandwidth = 32e6  # in Hz

    # Resolution calculations that helps determine the cellsize.
    # Usually the cell size is a fraction of the estimated resolution.

    #Convierte las longitudes uv a kilómetro, y luego a número de onda (λ).
    #Calcula la resolución angular del arreglo en milisegundos de arco (mas).

    # IMPRIMO ANTES EL SNAPTSHOT TIME

    scans = print_radioastron_scan_info()

    # Ahora podemos imprimir el resto
    print("---------------------------------------------------------------------")
    uvmax = np.max(np.abs(uv), axis=0) / 1e7  # in 10^4 km
    rmax = np.max(uvmax)  # Maximum uv along certain axis

    print(
        "uv max: %.1f x 10^4 km, %.1f x 10^4 km, rmax = %.3f x 10^4 km"
        % (uvmax[0], uvmax[1], rmax)
    )
    # ESTO DE AQUÍ ES UNA SUGERENCIA (LO DE ABAJO). ES LA RESOLUCIÓN ESTIMADA
    # MÁS ABAJO PUEDE CAMBIARSE EL TAMAÑO DE LA CELDA, QUE NORMALMENTE SERÁ
    # UNA FRACCIÓN DE LA RESOLUCIÓN ESTIMADA

# ------------------------ CONFIGURACIÓN FOV Y CELLSIZE ------------------------

    # Longitud de onda de la frecuencia principal
    lam = 3e8 / task.freqs[4]

    # Resolución angular esperada en mas
    res_mas = 1.0 / (rmax / lam) / 1e7 / np.pi * 180 * 3600e3  # mas

    # Campo de visión FIJO
    fov_mas = 0.07  # en mas

    # Escoge una resolución de grilla más fina que la resol. angular
    task.cellsize = res_mas / 10.0  # en mas /5.0

    # Número de píxeles necesario para cubrir ese campo de visión
    task.nc = int(2 ** np.ceil(np.log2(fov_mas / task.cellsize)))
    #task.nc=128
    # Reajusta el FOV real al tamaño de grilla elegido (por si acaso)
    #fov_mas = task.cellsize * task.nc
    #Esto es esencial para generar más detalle. Si no se ajusta, al final sale con peor resolución
    print(f"[INFO] Resolución esperada: {res_mas:.4f} mas")
    print(f"[INFO] Cellsize fijado: {task.cellsize:.5f} mas")
    print(f"[INFO] Campo de visión ajustado: {fov_mas:.3f} mas")
    print(f"[INFO] Tamaño de malla: {task.nc} x {task.nc}")

    ##### Preparation of sample image for simulation #####

    # Select the first src, retrive ra and dec
    src = task.srcs[0]
    ra = src.ra
    dec = src.dec


    # AQUÍ SE CONFIGURA LO ALEJADOS QUE ESTÁN LOS PUNTOS DE LA FIGURA A ESTUDIAR
    # SE TOMA UNA SEPARACIÓN DE 30 PIXELES. PARA EL CASO DE EJEMPLO, SON
    # 0.005*30=0.15 mas de separación EN EL PLANO. LUEGO HAY QUE TRANSFORMARLO A
    # RADIANES

    # En este ejemplo con el VSOP se llega en 5 GHz a una resolución de 0.59 mas,
    #insuficiente para la separación de 0.15 mas

    #    ds  =   0.5 # in mas
    ds = task.cellsize * 30.0  # in mas
    ddec = util.mas2rad(ds)
    # For RA, take the coordinate contraction into account.
    dra = util.mas2rad(ds) / np.cos(dec)

    print(f"Grid cell size:{task.cellsize:.5f} mas")
    print(f"Image size: {task.nc} x {task.nc} pixels "
      f"({task.nc * task.cellsize:.2f} mas field of view)")
    #print(f"Source separation  : {ds:.3f} mas "
    #  f"({util.mas2rad(ds):.3e} rad)")
    print("---------------------------------------------------------------------")
    print("                         RESOLUTION RANGE                            ")
    for freq in task.freqs:
     lam = 3e8 / freq  # longitud de onda
     rmax_lam = rmax / lam  # Maximum uv in wave number
     res = 1.0 / rmax_lam / 1e7 / np.pi * 180 * 3600e3  # in mas
     print("resolution at %.3f GHz (λ = %.3f m): %.4f mas." % (freq / 1e9, lam, res))
    print("---------------------------------------------------------------------")


#-------------------------------------------------------------------------------
    #Crea una imagen con 5 fuentes puntuales de 5 Jy cada una, ligeramente
    #desplazadas en RA y Dec alrededor de una fuente centra

    # Instance of Image class
    #img = Image(src)

    # Fluxes of each point, in Jy
    #img.fluxes = [5.0, 5.0, 5.0, 5.0, 5.0]

    # Ra and dec, in radian:
    #img.ras = [ra, ra + dra, ra, ra - dra, ra]
    #img.decs = [dec, dec, dec + ddec, dec, dec - ddec]

    # Total number of pixels
    #img.npixel = len(img.fluxes)

    # Calculate lmn for each pixel in the image
    # This part is exposed to users purposely. See Image section in
    # GitHub repo for a detailed explanation.

    # rqu: pixel position in CRS, or s0 in GitHub document.
    # lmn: shape (npixel, 3), projection of rqu (s0) in uvw system.
    #lmn = []
    #for i in range(img.npixel):
        # util.crs2rqu converts R.A. and decl. to unit vector form (rqu or s0)
        #Convierte coordenadas del cielo (RA/Dec) a vectores unitarios en
        #el sistema uvw (proyección direccional para la observación).

    #    rqu = util.crs2rqu(img.ras[i], img.decs[i])
    #    lmn.append(np.dot(img.ruvw0, rqu))
    #img.lmn = np.array(lmn)
    #src.img = img

#=================================== SMBH M87 ==================================
    # 1. Cargar imagen en blanco y negro
    img = PILImage.open(str(LOCAL_OPTIONS.input)).convert("L")
    img_data = np.array(img, dtype=np.float32)

    # 2. Normalizar la intensidad (en Jy arbitrarios)
    img_data /= img_data.max()
    img_data *= 5.0  # Asigna un flujo máximo arbitrario

    # 3. Definir parámetros de escala
    diameter_mas = 0.042  # 42 μas en milisegundos de arco
    cellsize_mas = diameter_mas / img_data.shape[0]
    dra = util.mas2rad(cellsize_mas)  # tamaño de píxel en RA (radianes)
    ddec = dra  # para pequeña escala, se puede aproximar igual

    print("Cell size given the SMBH image at : %.5f mas." % (cellsize_mas))
    # 4. Coordenadas de cada píxel
    npixel = img_data.size
    dec0 = 12.391123 / 180.0 * np.pi
    ra0 = 187.705930 / 180.0 * np.pi
    h, w = img_data.shape
    fluxes, ras, decs = [], [], []

    for y in range(h):
       for x in range(w):
           f = img_data[y, x]
           if f > 0.01:  # umbral para evitar ruido
            dy = y - h // 2
            dx = x - w // 2
            ras.append(ra0 + dx * dra / np.cos(dec0))
            decs.append(dec0 + dy * ddec)
            fluxes.append(f)

    # 5. Crear imagen en OmniUV
    #src = Source()
    #src.name = "M87"
    #src.ra = ra0
    #src.dec = dec0
    #srcs.append(src)

    image = Image(src)
    image.ras = ras
    image.decs = decs
    image.fluxes = fluxes
    image.npixel = len(fluxes)

    # 6. Calcular vectores lmn
    lmn = []
    for ra, dec in zip(ras, decs):
         rqu = util.crs2rqu(ra, dec)
         lmn.append(np.dot(image.ruvw0, rqu))
    image.lmn = np.array(lmn)

    img = image_to_omniuv_input(str(LOCAL_OPTIONS.input),task,total_size_ma=None) #
    src.img = img
#-------------------------------------------------------------------------------
    # GENERACIÓN DE VISIBILIDADES

    # Generate visibility of each baseline using FFT method
    # Input: src generated above
    # Output: bls, see below.
    # bls is a baseline list. The index of each baseline is the same
    # as the output of cacl_uvw_bl.
    # bl = bls[bl_id] is a dict, which has the following keys:
    # bl['uvw_m']:      2-D float array, shape (nt, 3), uvw in meter
    # bl['t']:          1-D array, time of available moments for the
    #                   corresponding  uvw_m, see explanation of
    #                   idt_avail after explanation of calc_uvw_bl()
    # bl['uvw_wav']:    3-D float array, shape (nt, nfreq, 3),
    #                   uvw in wavenumber
    # bl['vis']:        2-D complex array, shape (nt, nfreq),
    #                   visibility at each available moment and freq

    # Usa FFT para convertir la imagen del cielo a visibilidades en el espacio uv (teoría del interferómetro).
    # bls es una lista de diccionarios con visibilidades por línea base.
    bls = task.gen_vis_fft(src)

    # Verifica visibilidades generadas
    total_vis = sum(len(bl['vis']) for bl in bls if 'vis' in bl and bl['vis'] is not None)
    print(f"[DEBUG] Visibilidades generadas: {total_vis}")

    if total_vis == 0:
       print("[ERROR] No se han generado visibilidades a esta frecuencia. Revisa el FOV, resolución o estructura de la imagen.")
       return  # Evita intentar exportar a FITS


    # Add noise for each baseline. See Sec. 2.3 for an explanation.
    # Input: src, bls generated above
    # Output: bls orgainzed in the same structure as input
    bls = task.vis_add_noise(src, bls)

    # The visibility simumation result together with the calculated UVW
    # could be exported to FITS-IDI format:
    # Check if bls is empty or contains invalid data
    # "¿Hay datos válidos para todas las líneas base?"

    print("--------------------------------------------------------------------------------------")
    print("[DEBUG] Estaciones cargadas:")
    for stn in task.stns:
          print(f"  - {stn.name}, SEFD: {getattr(stn, 'SEFD', 'N/A')}, tipo: {type(stn).__name__}")
    print("--------------------------------------------------------------------------------------")

    if bls and all(len(bl.get("t", [])) > 0 for bl in bls):
      # Use len instead of .size
      # Check if 't' is present and not empty
      print("[DEBUG] Estaciones cargadas:")
      for stn in task.stns:
          print(f"  - {stn.name}, SEFD: {getattr(stn, 'SEFD', 'N/A')}, tipo: {type(stn).__name__}")

      #task.to_fitsidi("EXAMPLE", bls)
    else:
     print("Warning: Skipping FITS-IDI export due to empty or invalid baseline data.")

    # Se emite una advertencia indicando que la exportación se omitió por falta de datos válidos.
    # En simulaciones como las de OmniUV, a veces por error en parámetros o tiempos no se genera visibilidad para ciertas líneas base. Exportar archivos vacíos puede romper otros procesos.

    # Este if actúa como una protección para evitar eso.


#-------------------------------------------------------------------------------
    # OPCIONES ADICIONALES DE SIMULACIÓN

    # Permiten aplicar diferentes tipos de pesado uv (radial, uniforme)
    # La corrección del haz ajusta el brillo si la fuente es extendida.

    # Radial weighting, default to False
    task.do_rad = False

    # Uniform weighting, default to False
    task.do_unif = False

    # For diffuse source simulation, image flux must be corrected according
    # to the beam size and source image resolution. Default to False.
    task.do_beam_correction = False
    # If do_beam_correction is on, cellsize of souce image must be set
    # for normalization. Default to the cellsize of the output image,
    # you may set it according
    #    if task.do_beam_correction:
    #        task.cs_src_rad =   util.mas2rad(task.cellsize)

#-------------------------------------------------------------------------------
    # GENERACIÓN Y VISUALIZACIÓN DE IMAGEN

    # Generate beam pattern.
    # Input: bls above
    # Output: beam pattern, 2-D float array in the shape (nc, nc)
    beam = task.gen_beam(bls)

    # Generate image.
    # Input: bls above
    # Output:
    #   uv: 2-D float array, in the shape (nvis, 2)
    #   image: 2-D float array, in the shape (nc, nc)
    uv, image = task.gen_image_fft(bls)

    # Or you may use the DFT method:
    #    uv, image   =   task.gen_image_direct(bls)

    nc = task.nc  # grid size, same as in image and beam shape
    cs = task.cellsize  # cellsize, in mas

    #ESCALAMOS EL FLUJO
    # Supongamos que `image` es tu array 2D de flotantes (Jy/beam)
    # y quieres que el máximo sea `F_max` (por defecto, 1.0 Jy/beam)
    F_max = 0.5

    # Calcula el factor de escala
    F_current_max = np.max(image)
    scale = F_max / F_current_max

    # Aplica el escalado
    image_scaled = image * scale

    plot_beam(beam, cs, nc, "example_beam.png")
    plt.close()
    plot_uv(uv, cs, nc, "example_uv.png")
    plt.close()
    plot_image(image, cs, nc, "example_image.png")
    plt.close()
    plot_image(image_scaled, cs, nc, "image_scaled.png")
    plt.close()

   # Vamos a redefinir la función plot_uv para incorporar algún tipo de límite
    def plot_uv2(uv, cs, nc, outfile, xlim=None, ylim=None):
         plt.figure()
         plt.plot(uv[:,0]/1e7, uv[:,1]/1e7, 'b.', markersize=1)
         plt.xlabel(r'$u\ (10^4\ \mathrm{km})$')
         plt.ylabel(r'$v\ (10^4\ \mathrm{km})$')
         plt.title('UV Coverage')

         if xlim:
            plt.xlim(xlim)
         if ylim:
            plt.ylim(ylim)

         plt.grid(True)
         plt.savefig(outfile)
         plt.close()

  # Vamos a dibujar
    #xlim=(uvmax[0]/(lam*1e6));#21400*2)/(lam*1e6) # perigeo del VSOP
    #ylim=(uvmax[1]/(lam*1e6));#(21400*2)/(lam*1e6)  # perigeo del VSOP

    plot_uv2(uv, cs, nc, "funcion_uv.png")


if __name__ == "__main__":
    main()
