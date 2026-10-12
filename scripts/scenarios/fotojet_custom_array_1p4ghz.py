#!/usr/bin/env python3
"""fotojet_custom_array_1p4ghz: local adaptation of FotoJet Estaciones Random (Final).ipynb.
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
        options.output = PROJECT_ROOT / 'results' / 'fotojet_custom_array_1p4ghz' / datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    options.output = options.output.expanduser().resolve()
    options.output.mkdir(parents=True, exist_ok=True)
    metadata = {
        'scenario': 'fotojet_custom_array_1p4ghz', 'source_notebook': 'FotoJet Estaciones Random (Final).ipynb',
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


import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from PIL import Image as PILImage
from tool import *
from math import pi, cos


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

def print_radioastron_scan_info():
    scans = gen_LOVEX_scans()
    n_scans_total = int(len(scans) / (4 * 3600 / 60))  # puntos por scan
    print("---------------------------------------------------------------------")
    print("SLFRO simulated scans:")
    print(f"    Total days simulated   : 28")
    print(f"    Orbital period          : 26.18 hours")
    print(f"    Scans per period          : 1")
    print(f"    Duration per scan      : 4 hours")
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
                          flux_max_jy=5.0, flux_threshold=0.01,outfile="entrada_Omni_UV"):

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

    # Adaptado para trabajar con una lista de píxeles e intensidades desde un archivo txt


def read_pixel_file(filepath, ra_deg, dec_deg, flux_threshold=0.00):
    # Lee archivo con columnas x(as), y(as), I(Jy/pixel) y convierte a listas de RA, Dec y fluxes
    data = []
    with open(filepath, 'r') as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue
            x_as, y_as, I_jy = map(float, line.strip().split())
            if I_jy > flux_threshold:
                data.append((x_as, y_as, I_jy))

    x_as, y_as, fluxes = zip(*data)
    # Conversión origen en radianes
    ra0 = ra_deg * pi / 180.0
    dec0 = dec_deg * pi / 180.0

    # Offset en as desde el (0,0) original
    dx_as = np.array(x_as)
    dy_as = np.array(y_as)

    # 1) Determinar el centro de la grilla en arcsec
    center_offset_x = (dx_as.min() + dx_as.max()) / 2.0
    center_offset_y = (dy_as.min() + dy_as.max()) / 2.0

    # 2) Recentrar los offsets para que el centro pase a (0,0)
    dx_as -= center_offset_x
    dy_as -= center_offset_y

    # 3) Desplazar ra0/dec0 para llevar el nuevo (0,0) físico al RA/Dec correcto
    #    recordemos: 1 as = pi / (180*3600) rad
    ra0 += center_offset_x * (pi / (180.0 * 3600.0)) / np.cos(dec0)
    dec0 += center_offset_y * (pi / (180.0 * 3600.0))

    # Visualización rápida del input (RA/Dec offset) recentrado
    plt.figure(figsize=(6,6))
    plt.scatter(dx_as, dy_as, c=fluxes, cmap='inferno', s=2)
    plt.title("Distribución de flujo (input, recentrada)")
    plt.xlabel("RA offset (as)")
    plt.ylabel("Dec offset (as)")
    plt.colorbar(label='Jy/pixel')
    plt.gca().invert_xaxis()
    plt.savefig("Entrada_a_OmniUV_recentrado.png")
    plt.show() if LOCAL_OPTIONS.show else None

    # ----------------------- INTERPOLACIÓN PARA IMAGEN 2D -----------------------
    from scipy.interpolate import griddata
    grid_x, grid_y = np.mgrid[
        dx_as.min():dx_as.max():300j,
        dy_as.min():dy_as.max():300j
    ]
    grid_flux = griddata(
        (dx_as, dy_as), fluxes, (grid_x, grid_y),
        method='linear', fill_value=0
    )
    plt.figure()
    plt.imshow(grid_flux.T, origin='lower',
               extent=[dx_as.min(), dx_as.max(), dy_as.min(), dy_as.max()],
               cmap='inferno', aspect='equal')
    plt.title("Interpolación de flujo sobre grilla 2D (recentrada)")
    plt.xlabel("RA offset (as)")
    plt.ylabel("Dec offset (as)")
    plt.gca().invert_xaxis()
    plt.savefig("Interpolacion_2D_recentrada.png")
    plt.show() if LOCAL_OPTIONS.show else None

    # ----------------------- Conversión a radianes -----------------------
    ras  = ra0 + dx_as * (pi / (180.0 * 3600.0)) / np.cos(dec0)
    decs = dec0 + dy_as * (pi / (180.0 * 3600.0))

    print(f"------------------ DATOS IMAGEN RECENTRADA -------------------")
    print(f"[DEBUG] RA offset (as) tras centrar: min={dx_as.min():.3f}, max={dx_as.max():.3f}")
    print(f"[DEBUG] Dec offset (as) tras centrar: min={dy_as.min():.3f}, max={dy_as.max():.3f}")
    print(f"[DEBUG] Nuevo RA0 (rad): {ra0:.6f}, Nuevo Dec0 (rad): {dec0:.6f}")
    print("--------------------------------------------------------------")

    fluxes = np.array(fluxes)
    print("--------------- FLUXES (read_pixel_file) recentrada -------------")
    print(f"  - Número de píxeles       : {len(fluxes)}")
    print(f"  - Flujo máximo (Jy/píxel): {fluxes.max():.6f}")
    print(f"  - Flujo mínimo (Jy/píxel): {fluxes.min():.6f}")
    print(f"  - Valor medio (mean)             : {np.mean(fluxes):.6f} Jy/píxel")
    print(f"  - Desviación estándar (std)      : {np.std(fluxes):.6f} Jy/píxel")
    print(f"  - Total de flujo integrado (sum) : {np.sum(fluxes):.6f} Jy")
    print("----------------------------------------------------------------")

    return ras, decs, fluxes, ra0, dec0


from math import pi, cos
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
from omniuv import Task, Source, Image  # ajusta según tu import real
# asume que read_pixel_file ya está definida e importada

def run_simulation_from_txt(image_txt_path, ra_deg, dec_deg, task_params, freqs_ghz, rmax_km, fov_mas):

    #Corre la simulación leyendo un fichero de píxeles, recortando al FOV centrado,
    #generando visibilidades e imágenes FFT, y guardando los plots.

    for freq in freqs_ghz:
        # —————— Setup de tarea ——————
        task = Task()
        src  = Source()
        src.name = "M87"
        #src.ra   = ra_deg  * pi / 180.0
        #src.dec  = dec_deg * pi / 180.0
        task.set_srcs([src])

        # EOPs fijos
        task.set_eops(tmu=35.0, dut1=-2.211724, xp=0.027840, yp=0.370850)

        # Fechas
        t0 = datetime(2020, 3, 11, 0, 0, 0)
        task.set_ts(t0, task_params['ts'])

        # Frecuencia y ruido
        task.freqs     = np.array([freq])
        task.t_ap      = task_params['t_ap']
        task.bandwidth = task_params['bandwidth']

        # Resolución angular esperada (mas)
        lam     = 3e8 / freq
        res_mas = 1.0 / (rmax_km * 1e3 / lam) / 1e7 / pi * 180 * 3600e3

        # Elegir cellsize y nc controlando max_nc
        max_nc = LOCAL_OPTIONS.max_nc or 10000
        if (fov_mas / (res_mas / 5.0)) > max_nc:
            task.nc       = max_nc
            task.cellsize = fov_mas / task.nc
            print(f"[INFO] Resolución reducida: cellsize = {task.cellsize:.4f} mas")
        else:
            task.cellsize = res_mas / 5.0
            task.nc       = int(2 ** np.ceil(np.log2(fov_mas / task.cellsize)))

        if LOCAL_OPTIONS.max_nc is not None and task.nc > LOCAL_OPTIONS.max_nc:
            task.nc = LOCAL_OPTIONS.max_nc
            task.cellsize = fov_mas / task.nc

        print(f"\n[FREQ {freq/1e9:.2f} GHz] Res: {res_mas:.4f} mas | "
              f"Cell: {task.cellsize:.4f} mas | Grid: {task.nc}×{task.nc} | "
              f"FOV ≈ {task.cellsize*task.nc:.1f} mas")

        # —————— Leer y recentrar la imagen ——————
        ras, decs, fluxes, ra0, dec0 = read_pixel_file(
            image_txt_path, ra_deg, dec_deg
        )

        src.ra   = ra0
        src.dec  = dec0

        # Estadísticas previas al recorte
        print("----- FLUXES (pre-FOV cut) -----")
        print(f" píxeles: {len(fluxes)} | "
              f"max: {fluxes.max():.6f} Jy | min: {fluxes.min():.6f} Jy | "
              f"mean: {fluxes.mean():.6f} Jy | sum: {fluxes.sum():.6f} Jy")
        print("--------------------------------")

        # —————— Calcular offsets en mas ——————
        rad2mas        = 180 * 3600 * 1000 / pi
        offset_ra_mas  = (ras  - ra0) * rad2mas * np.cos(dec0)
        offset_dec_mas = (decs - dec0) * rad2mas


        # —————— Calcular offsets en mas y recortar al FOV (con margen) ——————

        half_fov   = (task.cellsize * task.nc) / 2.0
        print(f" half_fov: {half_fov} | ")

        # Para redondear igual que gen_vis_fft
        ix = np.floor((offset_ra_mas  + half_fov)/task.cellsize + 0.5).astype(int)
        iy = np.floor((offset_dec_mas + half_fov)/task.cellsize + 0.5).astype(int)

        # — Filtrado por índices válidos —
        valid = (ix>=0) & (ix<task.nc) & (iy>=0) & (iy<task.nc)


        ras    = ras[valid]
        decs   = decs[valid]
        fluxes = fluxes[valid]
        off_x  = offset_ra_mas [valid]
        off_y  = offset_dec_mas[valid]
        ix     = ix     [valid]
        iy     = iy     [valid]

        # ——— Informe de ras/decs ———
        print("–––––––––––––––––––––––––––––––––––––")
        print("   Resumen de píxeles seleccionados")
        print("–––––––––––––––––––––––––––––––––––––")
        print(f" Total de píxeles: {len(ras)}")

        # Estadísticas en radianes
        print("\nR.A. (rad):")
        print(f"  min = {ras.min():.6f},  max = {ras.max():.6f}")
        print(f"  mean= {ras.mean():.6f},  std = {ras.std():.6f}")
        print(f"  RA0 {ra0:.6f},  DEC0 = {dec0:.6f}")

        print("\nDec (rad):")
        print(f"  min = {decs.min():.6f},  max = {decs.max():.6f}")
        print(f"  mean= {decs.mean():.6f},  std = {decs.std():.6f}")

        # Estadísticas en radianes
        print("\nR.A. (mas):")
        print(f"  min = {ras.min()*rad2mas:.6f},  max = {ras.max()*rad2mas:.6f}")
        print(f"  mean= {ras.mean()*rad2mas:.6f},  std = {ras.std()*rad2mas:.6f}")

        print("\nDec (mas):")
        print(f"  min = {decs.min()*rad2mas:.6f},  max = {decs.max()*rad2mas:.6f}")
        print(f"  mean= {decs.mean()*rad2mas:.6f},  std = {decs.std()*rad2mas:.6f}")
        # ———____________________________________________———

        # recalcular lmn para los puntos válidos
        ruvw0 = np.array([
            np.cos(dec0)*np.cos(ra0),
            np.cos(dec0)*np.sin(ra0),
            np.sin(dec0)
        ])
        rqu = np.stack([
            np.cos(decs)*np.cos(ras),
            np.cos(decs)*np.sin(ras),
            np.sin(decs)
        ], axis=1)
        lmn = np.dot(rqu, ruvw0)
        off_x = offset_ra_mas[valid]
        off_y = offset_dec_mas[valid]

        # Estadísticas post‐recorte
        print("----- FLUXES (post-FOV cut) -----")
        print(f" píxeles: {len(fluxes)} | "
              f"FOV importado: {(off_x.max()-off_x.min()):.1f} mas | "
              f"max: {fluxes.max():.6f} Jy | min: {fluxes.min():.6f} Jy | "
              f"sum: {fluxes.sum():.6f} Jy")
        print("---------------------------------")

        # —————— Scatter input recortado ——————
        plt.figure(figsize=(6,6))
        plt.scatter(off_x, off_y, c=fluxes, cmap='inferno', s=2)
        plt.title("Flujo recortado (input)")
        plt.xlabel("RA offset (mas)")
        plt.ylabel("Dec offset (mas)")
        plt.colorbar(label='Jy/pixel')
        plt.gca().invert_xaxis()
        plt.savefig("input_recortado.png")
        plt.show() if LOCAL_OPTIONS.show else None

        # —————— Crear objeto imagen y asignar a la fuente ——————
        image = Image(src)
        image.ras    = ras
        image.decs   = decs
        image.fluxes = fluxes
        image.npixel = len(fluxes)
        image.lmn    = lmn
        image.ruvw   = ruvw0
        src.img      = image

        # —————— UVW, vis FFT y ruido ——————
        task.set_stns(task_params['stns'])
        uvw_bls   = task.calc_uvw_bl()
        uvw_flat  = task.flat_uvw_bl(uvw_bls)
        uv        = np.vstack([uvw_flat[0][:,:2], -uvw_flat[0][:,:2]])
        bls       = task.gen_vis_fft(src)

        total_vis = sum(len(bl.get('vis',[])) for bl in bls)
        print(f"[INFO] Vis generadas: {total_vis}")

        print("--------------------------------------------------------------------------------------")
        print("[DEBUG] Estaciones cargadas:")
        for stn in task.stns:
           print(f"  - {stn.name}, SEFD: {getattr(stn, 'SEFD', 'N/A')}, tipo: {type(stn).__name__}")
        print("--------------------------------------------------------------------------------------")

        # —————— Beam e imagen FFT de salida ——————
        beam, = (task.gen_beam(bls),)
        uv, vis_image = task.gen_image_fft(bls)

        # —————— Plots finales ——————
        plot_beam(beam, task.cellsize, task.nc,   "beam.png")
        plot_uv  (uv,   task.cellsize, task.nc,   "uv.png")
        plot_image(vis_image, task.cellsize, task.nc, "image.png")

        plt.figure(figsize=(6,6))
        plt.imshow(vis_image, cmap='inferno',
                   extent=[-half_fov, half_fov, -half_fov, half_fov])
        plt.title(f"Simulada @ {freq/1e9:.2f} GHz")
        plt.xlabel("RA offset (mas)")
        plt.ylabel("Dec offset (mas)")
        plt.colorbar(label='Jy')
        plt.savefig(f"sim_image_{int(freq/1e6)}MHz.png")
        plt.show() if LOCAL_OPTIONS.show else None
        plt.close()

        plt.figure()
        plt.plot(uv[:,0]/1e7, uv[:,1]/1e7, 'b.', markersize=1)
        plt.xlabel(r'$u\ (10^4\ \mathrm{km})$')
        plt.ylabel(r'$v\ (10^4\ \mathrm{km})$')
        plt.title('UV Coverage')
        plt.grid(True)
        plt.savefig("UV Coverage")
        plt.close()




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

         # LV
     g = EarthFixed("Lovell Telescope")
     # Terrestrial reference frame system coordinate (ECEF, en metros)
     g.set_trs(np.array([ 3822569.3803,  -154091.5713,  5086402.1713 ]))
     # Altura mínima de elevación
     g.set_el_min_deg(10.0)
     # SEFD típico en banda L (~1.6 GHz)
     g.set_SEFD(132.0)  # Lovell Telescope SEFD ≃36 Jy :contentReference[oaicite:2]{index=2}
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

         # LV
     g = EarthFixed("Lovell Telescope")
     # Terrestrial reference frame system coordinate (ECEF, en metros)
     g.set_trs(np.array([ 3822569.3803,  -154091.5713,  5086402.1713 ]))
     # Altura mínima de elevación
     g.set_el_min_deg(10.0)
     # SEFD típico en banda L (~1.6 GHz)
     g.set_SEFD(36.0)  # Lovell Telescope SEFD ≃36 Jy :contentReference[oaicite:2]{index=2}
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

         # LV
     g = EarthFixed("Lovell Telescope")
     # Terrestrial reference frame system coordinate (ECEF, en metros)
     g.set_trs(np.array([ 3822569.3803,  -154091.5713,  5086402.1713 ]))
     # Altura mínima de elevación
     g.set_el_min_deg(10.0)
     # SEFD típico en banda L (~1.6 GHz)
     g.set_SEFD(80.0)  # Lovell Telescope SEFD ≃36 Jy :contentReference[oaicite:2]{index=2}
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

    elif band == "SKA LOW":

        # GB
     g = EarthFixed("Green Banck Telescope")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([882589.4102,	-4924872.342,	3943729.406]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(35.0)
     stns.append(g)

     # GB
     g = EarthFixed("Lovell Telescope")
     # Terrestrial reference frame system coordinate (ECEF, en metros)
     g.set_trs(np.array([ 3822569.3803,  -154091.5713,  5086402.1713 ]))
     # Altura mínima de elevación
     g.set_el_min_deg(10.0)
     # SEFD típico en banda L (~1.6 GHz)
     g.set_SEFD(132.0)  # Lovell Telescope SEFD ≃36 Jy :contentReference[oaicite:2]{index=2}
     stns.append(g)

            # SM (SKA) (Radio 4 km)
     g = EarthFixed("SKA-Low core")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([5109261.392,2006742.35,-3239104.8939]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(2.38)
     stns.append(g)

          # Ef
     g = EarthFixed("Effelsberg")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([4033947.23550, 486990.79430, 4900431.00170]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(600.0)
     stns.append(g)

        # VLA
     g = EarthFixed("Very Large Array")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([ -1601185.0, -5041982.0, 3554872.0 ]))
     # Minimum elevation, in degree
     g.set_el_min_deg(13.2)
     g.set_SEFD(167)
     stns.append(g)

     # JB1
     g = EarthFixed("Jodrell Bank (Mrk 1)")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([3822846.76,-153802.28,5086285.9]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(132.0)
     stns.append(g)


     #GMRT
     g = EarthFixed("Giant Metrewave Radio Telescope")
     # Terrestial reference frame system coordinate
     g.set_trs(np.array([  601519.0,  6091914.0,  1972645.0 ]))
     # Minimum elevation, in degree
     g.set_el_min_deg(10.0)
     g.set_SEFD(55.0)
     stns.append(g)

    else:
        raise ValueError(f"Banda no reconocida: '{band}'. Usa una de las siguientes: "
                         "'MID BAND 1', 'MID BAND 2', 'MID BAND 3', 'MID BAND 4', 'MID BAND 5a)', 'MID BAND 5b)'")




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
    s.set_orbit(a=a, e=e, i=-np.pi / 6, raan=15.0, arg_pe=0.0, M0=np.pi, t_ref=t0)
    #3.6 cm, 30 m diameter
    s.set_SEFD(225.0)
    stns.append(s)

#________________________________ EARTH FIXED __________________________________

    add_ska_mid_stations("MID BAND 2", stns)
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
    lo = LunarOrbit("LOVEX ")
    lo.set_sep_min_deg(Moon=1.0, Sun=10.0)

    hl = 1991.69e3- util.Rm
    hh = 18678.5e3- util.Rm

    # Calculate semi-major and eccentricity for Earth orbit.
    a, e = util.h2ae(hl, hh, util.Rm)
    # t_ref defaults to task.t0
    lo.set_orbit(
        a=a,
        e=e,
        i=119.25*(np.pi / 180),
        raan=0.0,
        arg_pe=0.0,
        M0=0.0,
       t_ref=t0,
    )
    lo.set_SEFD(200)
    #if with_moon:
        #stns.append(lo)

    l2_es = EarthSunL2("EarthSun L2")
    l2_es.set_sep_min_deg(Earth=5.0)
    l2_es.set_SEFD(200)
    #stns.append(l2_es)

    l2_me = MoonEarthL2("me")
    l2_me.set_sep_min_deg(Moon=1.0)
    l2_me.set_SEFD(200)
    #if with_moon:
        #stns.append(l2_me)
#_______________________________________________________________________________

    # Gain error, see Explanation of Eq. 4.
    task.gain_error = 0.1  # Es la Yi(t) de la que depende la Ganancia Gi(t).
                           # Se deja como un parámetro libre

    # Register all stations
    task.set_stns(stns)

#-------------------------------------------------------------------------------

          # CONFIGURACIÓN DE FRECUENCIAS Y RESOLUCIÓN ANGULAR

    # Accumulation period (integration time) {SNAPSHOT TIME (TIEMPO DE EXPOSICIÓN)}
    task.t_ap = 600  # in second, could be float, e.g. 0.128

    # Bandwidth of each IF
    task.bandwidth = 32e6  # in Hz


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

    task_params = {
        'ts': ts,          # np.ndarray con los instantes de observación en segundos desde t0
        't_ap': 600,                          # Tiempo de integración por visibilidad (segundos)
        'bandwidth': 32e6,                    # Ancho de banda por canal (Hz)
        'stns': stns       # Lista de objetos EarthFixed, EarthOrbit, etc. (task.set_stns)
         }

    ra_deg=133.70364577
    dec_deg=20.108511
    freqs_ghz=np.array([1.4e9])
    fov_mas=0.30*1000 #0.457*1000

    run_simulation_from_txt(str(LOCAL_OPTIONS.input), ra_deg, dec_deg, task_params, freqs_ghz, rmax, fov_mas)

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

    #plot_uv2(uv, cs, nc, "funcion_uv.png")


if __name__ == "__main__":
    main()
