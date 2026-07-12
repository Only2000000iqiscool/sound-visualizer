# Sound Visualizer

Native **Desktop-App** (PyQt6) mit **17 Audio-Visualizern** — flüssig, ohne Browser.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![PyQt6](https://img.shields.io/badge/PyQt6-6.6+-green)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

## Features

- **17 Visualizer:** Bars, Circular, Waveform, Mirror, Radial, Particles, Spiral, Kaleido, Grid, Flame, Matrix, Orbits, Blobs, Warp, Terrain, Tunnel, 3D Scope
- **Native Oberfläche:** Menüleiste, Dateidialog, Einstellungen, Statusleiste
- **Audio-Quellen:** Mikrofon (PyAudio) oder Dateien (MP3, WAV, OGG, FLAC, … via ffmpeg)
- **Tastenkürzel:** `←`/`→` Visualizer, `Leertaste` Pause, `F11` Vollbild, `Ctrl+O` Datei öffnen

## Voraussetzungen

- Python 3.11+
- PyQt6, numpy, PyAudio
- **ffmpeg** (für MP3/OGG/FLAC)

### Arch / CachyOS

```bash
sudo pacman -S python-pyqt6 python-numpy python-pyaudio ffmpeg
```

## Installation

```bash
git clone https://github.com/Only2000000iqiscool/sound-visualizer.git
cd sound-visualizer
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Starten

```bash
python3 run.py
```

## Bedienung

| Aktion | Shortcut / Menü |
|--------|-----------------|
| Audio öffnen | `Ctrl+O` → Datei |
| Mikrofon | `Ctrl+M` → Datei |
| Visualizer wechseln | `←` / `→` oder Menü Visualizer |
| Pause | `Leertaste` |
| Vollbild | `F11` |
| Einstellungen | Ansicht → Einstellungen |

## Projektstruktur

```
sound-visualizer/
├── app/
│   ├── audio_engine.py    # FFT & Audio-Eingang
│   ├── canvas_widget.py   # Render-Loop (60 FPS)
│   ├── main_window.py     # Native Qt-Oberfläche
│   ├── settings_dialog.py
│   └── visualizers/       # 17 Zeichenmodi
├── run.py
└── requirements.txt
```

## Lizenz

MIT
