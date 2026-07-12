# Sound Visualizer

Native **Desktop-App** (Python + PyQt6) mit **17 Audio-Visualizern** — läuft auf **Linux und Windows**.

Warum Python + PyQt6? Cross-platform, native Fenster/Dialoge und schnelle FFT mit NumPy. Dateien werden einmalig mit ffmpeg dekodiert und anschließend als PCM über Qt `QAudioSink` abgespielt; PyAudio wird ausschließlich für das Mikrofon verwendet.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![PyQt6](https://img.shields.io/badge/PyQt6-6.6+-green)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

## Features

- **17 Visualizer:** Bars, Circular, Waveform, Mirror, Radial, Particles, Spiral, Kaleido, Grid, Flame, Matrix, Orbits, Blobs, Warp, Terrain, Tunnel, 3D Scope
- **Native Oberfläche:** Menüleiste, Dateidialog, Einstellungen, Statusleiste
- **Audio-Quellen:** frei wählbares Mikrofon (PyAudio) oder Dateien (MP3, WAV, OGG, FLAC, … via ffmpeg)
- **Verständliche Eingänge:** automatische Bezeichnungen für Headset, Line-In, Front-Mikrofon und USB-Audio
- **Schnelles Laden:** Hintergrund-Dekodierung, Prozentanzeige, Datenmenge, Restzeit und Cache für zuletzt verwendete Dateien
- **Modernes Design:** violettes Kontrollpanel, große Quellen-Buttons und direkte Visualizer-Auswahl
- **Tastenkürzel:** `←`/`→` Visualizer, `Leertaste` Pause, `F11` randloses Vollbild, `Esc` Vollbild beenden, `Ctrl+O` Datei öffnen
- **Drag & Drop:** Audio-Dateien ins Fenster ziehen

## Voraussetzungen

- Python 3.11+
- PyQt6, numpy, PyAudio
- **ffmpeg** (für MP3/OGG/FLAC)

### Arch / CachyOS

```bash
sudo pacman -S python-pyqt6 python-numpy python-pyaudio ffmpeg
```

### Windows

- [Python 3.11+](https://www.python.org/downloads/)
- [ffmpeg](https://ffmpeg.org/download.html) im `PATH`
- Abhängigkeiten:

```bat
pip install -r requirements.txt
```

Unter Arch/CachyOS reicht **pacman** — kein pip nötig.

## Installation (optional: venv)

```bash
git clone https://github.com/Only2000000iqiscool/sound-visualizer.git
cd sound-visualizer
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Starten

**Linux:**
```bash
python3 run.py
```

**Windows:**
```bat
run.bat
```

## Bedienung

| Aktion | Shortcut / Menü |
|--------|-----------------|
| Audio öffnen | `Ctrl+O` → Datei |
| Mikrofon auswählen | `Ctrl+M` → Datei |
| Visualizer wechseln | `←` / `→` oder Menü Visualizer |
| Pause | `Leertaste` |
| Vollbild (randlos) | `F11` / `Esc` beenden |
| Audio per Drag & Drop | Datei ins Fenster ziehen |
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
