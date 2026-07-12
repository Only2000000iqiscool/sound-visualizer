#!/usr/bin/env python3
"""Sound Visualizer – native desktop application."""

import logging
import os

# Qt Multimedia probes video hardware decoders even though this is an audio-only
# app. Disable those probes before importing PyQt to avoid missing-driver errors
# (for example libvdpau_nvidia.so on Linux).
os.environ.setdefault("QT_FFMPEG_DECODING_HW_DEVICE_TYPES", ",")
os.environ.setdefault("QT_FFMPEG_ENCODING_HW_DEVICE_TYPES", ",")
os.environ.setdefault("QT_LOGGING_RULES", "qt.multimedia.*=false;qt.qpa.*=false")

from app.logging_config import setup_logging

setup_logging()

from app.main import main

if __name__ == "__main__":
    raise SystemExit(main())
