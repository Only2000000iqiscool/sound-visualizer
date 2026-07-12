from __future__ import annotations

import logging
import re
import shutil
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def _run(command: list[str]) -> str:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


def _sink_descriptions() -> dict[str, str]:
    if not shutil.which("pactl"):
        return {}

    output = _run(["pactl", "list", "sinks"])
    descriptions: dict[str, str] = {}
    current_name = ""
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("Name:"):
            current_name = line.split(":", 1)[1].strip()
        elif line.startswith("Description:") and current_name:
            descriptions[current_name] = line.split(":", 1)[1].strip()
    return descriptions


def list_pulse_output_devices() -> list[dict]:
    if not shutil.which("pactl"):
        return []

    default_sink = _run(["pactl", "get-default-sink"])
    descriptions = _sink_descriptions()
    devices: list[dict] = []

    for line in _run(["pactl", "list", "sinks", "short"]).splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        sink_name = parts[1]
        description = descriptions.get(sink_name, sink_name)
        devices.append(
            {
                "id": sink_name,
                "pulse_name": sink_name,
                "name": description,
                "display_name": description,
                "description": (
                    f"PipeWire/PulseAudio-Ausgang.\n"
                    f"Technischer Name: {sink_name}"
                ),
                "default": sink_name == default_sink,
                "backend": "pulse",
            }
        )

    devices.sort(key=lambda item: (not item["default"], item["display_name"].lower()))
    return devices


def pulse_sink_sample_rate(sink_name: str) -> int | None:
    """Return sample rate (Hz) for a PipeWire/PulseAudio sink."""
    if not shutil.which("pactl") or not sink_name:
        return None

    current_name = ""
    for line in _run(["pactl", "list", "sinks"]).splitlines():
        line = line.strip()
        if line.startswith("Name:"):
            current_name = line.split(":", 1)[1].strip()
        elif line.startswith("Sample Specification:") and current_name == sink_name:
            match = re.search(r"(\d+)Hz", line)
            if match:
                return int(match.group(1))
    return None


def _friendly_pyaudio_name(name: str, default: bool) -> dict:
    if default and name in {"default", "pulse", "pipewire"}:
        return {
            "display_name": "Automatisch – Systemstandard",
            "description": (
                "Verwendet den in Linux eingestellten Standard-Ausgang "
                f"({name})."
            ),
        }

    clean = name
    if match := re.search(r"\[([^\]]+)\]", name):
        clean = match.group(1)
    elif ":" in name:
        clean = name.split(":", 1)[0].strip()

    return {
        "display_name": clean,
        "description": f"ALSA/PyAudio-Ausgang.\nGerät: {name}",
    }


def list_pyaudio_output_devices(pa) -> list[dict]:
    try:
        default_index = int(pa.get_default_output_device_info()["index"])
    except Exception:
        default_index = -1

    devices = []
    for index in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(index)
        if int(info.get("maxOutputChannels", 0)) < 1:
            continue
        name = str(info.get("name", f"Ausgang {index}"))
        lower = name.lower()
        if lower in {"pipewire", "pulse", "default"} and index != default_index:
            continue

        entry = {
            "id": str(index),
            "pa_index": index,
            "name": name,
            "default": index == default_index,
            "sample_rate": int(info.get("defaultSampleRate", 44100)),
            "backend": "pyaudio",
        }
        entry.update(_friendly_pyaudio_name(name, entry["default"]))
        devices.append(entry)

    devices.sort(key=lambda item: (not item["default"], item["display_name"].lower()))
    return devices


def _source_descriptions() -> dict[str, str]:
    if not shutil.which("pactl"):
        return {}

    output = _run(["pactl", "list", "sources"])
    descriptions: dict[str, str] = {}
    current_name = ""
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("Name:"):
            current_name = line.split(":", 1)[1].strip()
        elif line.startswith("Description:") and current_name:
            descriptions[current_name] = line.split(":", 1)[1].strip()
    return descriptions


def _parse_pulse_rate(spec: str) -> int:
    match = re.search(r"(\d+)Hz", spec)
    if match:
        return int(match.group(1))
    return 44100


def _parse_pulse_channels(spec: str) -> int:
    match = re.search(r"(\d+)ch", spec)
    if match:
        return max(1, int(match.group(1)))
    return 1


def _parse_hw_card_device(name: str) -> tuple[int, int] | None:
    match = re.search(r"\(hw:(\d+),(\d+)\)", name)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None


def _arecord_capture_map() -> dict[tuple[int, int], dict[str, str]]:
    if not shutil.which("arecord"):
        return {}

    output = _run(["arecord", "-l"])
    devices: dict[tuple[int, int], dict[str, str]] = {}
    card_id = -1
    card_label = ""
    for line in output.splitlines():
        card_match = re.search(
            r"Karte\s+(\d+):\s+(\S+)\s+\[(.+?)\],\s+Gerät\s+(\d+):\s+(.+)$",
            line,
        )
        if not card_match:
            continue
        card_id = int(card_match.group(1))
        card_short = card_match.group(2)
        card_label = card_match.group(3).strip()
        device_id = int(card_match.group(4))
        device_label = card_match.group(5).strip()
        devices[(card_id, device_id)] = {
            "card_label": card_label,
            "card_short": card_short,
            "device_label": device_label,
        }
    return devices


def _parse_pulse_alsa_path(path: str) -> tuple[int, int] | None:
    """Parse pactl api.alsa.path values like hw:3,1 or hw:Audio,2."""
    path = path.strip().strip('"')
    aliases = _alsa_card_aliases()

    match = re.match(r"hw:(\d+),(\d+)$", path)
    if match:
        return int(match.group(1)), int(match.group(2))

    match = re.match(r"hw:(\w+),(\d+)$", path)
    if match:
        card_id = aliases.get(match.group(1))
        if card_id is not None:
            return card_id, int(match.group(2))

    match = re.match(r"hw:(\d+)$", path)
    if match:
        return int(match.group(1)), 0

    if path.startswith("front:"):
        try:
            return int(path.split(":", 1)[1]), 0
        except ValueError:
            return None

    return None


def _pulse_capture_entries() -> list[dict]:
    """Capture sources with ALSA hardware paths from PipeWire."""
    if not shutil.which("pactl"):
        return []

    entries: list[dict] = []
    current: dict[str, str] = {}

    def _flush() -> None:
        nonlocal current
        source_name = current.get("source_name", "")
        if not source_name.startswith("alsa_input.") or ".monitor" in source_name:
            current = {}
            return
        hw = _parse_pulse_alsa_path(current.get("alsa_path", ""))
        if hw is not None:
            entries.append(
                {
                    "source_name": source_name,
                    "description": current.get("description", source_name),
                    "alsa_path": current.get("alsa_path", ""),
                    "hw": hw,
                }
            )
        current = {}

    for line in _run(["pactl", "list", "sources"]).splitlines():
        stripped = line.strip()
        if stripped.startswith("Source #"):
            _flush()
            current = {}
            continue
        if stripped.startswith("Name:"):
            current["source_name"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("Description:"):
            current["description"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("api.alsa.path ="):
            current["alsa_path"] = stripped.split("=", 1)[1].strip().strip('"')
        elif stripped == "":
            _flush()

    _flush()
    return entries


def _pulse_sources_by_hw() -> dict[tuple[int, int], str]:
    return {entry["hw"]: entry["source_name"] for entry in _pulse_capture_entries()}


def pulse_source_for_device(device: dict) -> str | None:
    """Return PipeWire source name for a capture device, if known."""
    pulse_source = device.get("pulse_source")
    if pulse_source:
        return str(pulse_source)
    hw = _parse_hw_card_device(str(device.get("name", "")))
    if hw is None:
        return None
    return _pulse_sources_by_hw().get(hw)


def _pulse_capture_roles() -> dict[tuple[int, int], str]:
    return {entry["hw"]: entry["description"] for entry in _pulse_capture_entries()}


def _german_input_role(label: str) -> str:
    lower = label.lower()
    if "front" in lower and "microphone" in lower:
        return "Front-Mikrofon"
    if "line" in lower:
        return "Line-Eingang"
    if "headset" in lower or "mono" in lower:
        return "Headset-Mikrofon"
    if "microphone" in lower or "mic" in lower:
        return "Mikrofon"
    return label


def _is_virtual_input(name: str) -> bool:
    lower = name.lower().strip()
    virtual = {
        "pipewire",
        "pulse",
        "default",
        "sysdefault",
        "spdif",
        "lavrate",
        "samplerate",
        "speexrate",
        "speex",
        "upmix",
        "vdownmix",
        "jack",
    }
    if lower in virtual:
        return True
    if lower.startswith(("dmix", "dsnoop", "surround", "front", "rear", "center")):
        return True
    return "(hw:" not in name


def _fallback_hw_label(hw: tuple[int, int], meta: dict[str, str]) -> str | None:
    if meta.get("card_short") != "Audio":
        return None
    device_id = hw[1]
    if device_id == 1:
        return "Line-Eingang"
    if device_id == 2:
        return "Front-Mikrofon"
    if device_id == 0:
        return "Mikrofon"
    return None


def _friendly_input_label(
    pa_name: str,
    arecord: dict[tuple[int, int], dict[str, str]],
    pulse_roles: dict[tuple[int, int], str],
) -> tuple[str, str]:
    hw = _parse_hw_card_device(pa_name)
    card_label = ""
    device_label = ""
    role_label = ""

    if hw is not None:
        meta = arecord.get(hw, {})
        card_label = meta.get("card_label", "")
        device_label = meta.get("device_label", "")
        role_label = pulse_roles.get(hw, "") or _fallback_hw_label(hw, meta) or ""

    if role_label:
        card_name = card_label or pa_name.split(":", 1)[0].strip()
        display = f"{card_name} – {_german_input_role(role_label)}"
    elif card_label:
        suffix = f" ({device_label})" if device_label else ""
        display = f"{card_label}{suffix}"
    else:
        display = pa_name.split(":", 1)[0].strip() if ":" in pa_name else pa_name

    description_lines = [f"Direkter Hardware-Eingang (ALSA)."]
    if role_label:
        description_lines.append(f"PipeWire-Bezeichnung: {role_label}")
    if card_label:
        description_lines.append(f"Soundkarte: {card_label}")
    if device_label:
        description_lines.append(f"Anschluss: {device_label}")
    description_lines.append(f"PyAudio: {pa_name}")
    return display, "\n".join(description_lines)


def resolve_default_input_device(pa) -> dict | None:
    """Map KDE/PipeWire default source to a working ALSA capture device."""
    if shutil.which("pactl"):
        default_source = _run(["pactl", "get-default-source"])
        if default_source and ".monitor" not in default_source:
            resolved = resolve_input_device(
                pa,
                {
                    "backend": "pulse",
                    "pulse_source": default_source,
                    "id": default_source,
                    "default": True,
                },
            )
            if resolved.get("backend") == "pyaudio":
                return resolved

    for device in list_pyaudio_input_devices(pa):
        if device.get("default"):
            return device
    devices = list_pyaudio_input_devices(pa)
    return devices[0] if devices else None


def _default_input_entry(default_device: dict | None) -> dict:
    description = (
        "Verwendet den in KDE/PipeWire eingestellten Standard-Eingang.\n"
        "Empfohlen, wenn du unsicher bist."
    )
    if default_device:
        description += f"\nAktuell zugeordnet: {default_device['display_name']}"
    return {
        "id": "__default__",
        "backend": "default",
        "default": True,
        "display_name": "Automatisch – Systemstandard",
        "description": description,
        "sample_rate": default_device["sample_rate"] if default_device else 44100,
        "channels": default_device.get("channels", 1) if default_device else 1,
        "visible": True,
    }


def list_pulse_input_devices() -> list[dict]:
    if not shutil.which("pactl"):
        return []

    default_source = _run(["pactl", "get-default-source"])
    descriptions = _source_descriptions()
    devices: list[dict] = []

    for line in _run(["pactl", "list", "sources", "short"]).splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        source_name = parts[1]
        if ".monitor" in source_name:
            continue
        if not source_name.startswith("alsa_input."):
            continue

        spec = parts[3] if len(parts) > 3 else ""
        description = descriptions.get(source_name, source_name)
        devices.append(
            {
                "id": source_name,
                "index": source_name,
                "pulse_source": source_name,
                "name": description,
                "display_name": description,
                "description": (
                    f"Echter Mikrofon-Eingang.\n"
                    f"Technischer Name: {source_name}"
                ),
                "default": source_name == default_source,
                "sample_rate": _parse_pulse_rate(spec),
                "backend": "pulse",
                "visible": True,
            }
        )

    devices.sort(key=lambda item: (not item["default"], item["display_name"].lower()))
    return devices


def list_pyaudio_input_devices(pa) -> list[dict]:
    try:
        default_index = int(pa.get_default_input_device_info()["index"])
    except Exception:
        default_index = -1

    arecord = _arecord_capture_map() if sys.platform.startswith("linux") else {}
    pulse_roles = _pulse_capture_roles() if sys.platform.startswith("linux") else {}
    pulse_sources = _pulse_sources_by_hw() if sys.platform.startswith("linux") else {}

    devices = []
    for index in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(index)
        max_channels = int(info.get("maxInputChannels", 0))
        if max_channels < 1:
            continue
        name = str(info.get("name", f"Mikrofon {index}"))
        if _is_virtual_input(name):
            continue

        channels = min(max_channels, 2)
        display_name, description = _friendly_input_label(name, arecord, pulse_roles)
        hw = _parse_hw_card_device(name)
        pulse_source = pulse_sources.get(hw) if hw else None
        devices.append(
            {
                "id": str(index),
                "index": index,
                "pa_index": index,
                "name": name,
                "default": index == default_index,
                "sample_rate": int(info.get("defaultSampleRate", 44100)),
                "channels": channels,
                "backend": "pyaudio",
                "visible": True,
                "display_name": display_name,
                "description": description,
                "pulse_source": pulse_source,
            }
        )

    devices.sort(key=lambda item: item["display_name"].lower())
    return devices


def _alsa_card_aliases() -> dict[str, int]:
    cards_path = Path("/proc/asound/cards")
    if not cards_path.is_file():
        return {}
    aliases: dict[str, int] = {}
    for line in cards_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = re.match(r"\s*(\d+)\s+\[(\S+)\s*\]:", line)
        if match:
            aliases[match.group(2)] = int(match.group(1))
    return aliases


def _pulse_source_to_hw(pulse_source: str) -> tuple[int, int] | None:
    for entry in _pulse_capture_entries():
        if entry["source_name"] == pulse_source:
            return entry["hw"]
    return None


def resolve_input_device(pa, device: dict) -> dict:
    """Map legacy PipeWire entries to working PyAudio hardware devices."""
    if device.get("backend") != "pulse":
        return device

    pulse_source = str(device.get("pulse_source") or device.get("id") or "")
    target_hw = _pulse_source_to_hw(pulse_source)
    if target_hw is None:
        return device

    arecord = _arecord_capture_map()
    roles = _pulse_capture_roles()
    for index in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(index)
        if int(info.get("maxInputChannels", 0)) < 1:
            continue
        name = str(info.get("name", ""))
        if _parse_hw_card_device(name) != target_hw:
            continue
        channels = min(int(info.get("maxInputChannels", 1)), 2)
        display_name, description = _friendly_input_label(name, arecord, roles)
        hw = _parse_hw_card_device(name)
        pulse_source = _pulse_sources_by_hw().get(hw) if hw else None
        return {
            "id": str(index),
            "index": index,
            "pa_index": index,
            "name": name,
            "default": device.get("default", False),
            "sample_rate": int(info.get("defaultSampleRate", device.get("sample_rate", 44100))),
            "channels": channels,
            "backend": "pyaudio",
            "visible": True,
            "display_name": display_name,
            "description": description,
            "pulse_source": pulse_source,
        }

    return device


def list_input_devices(pa) -> list[dict]:
    devices = list_pyaudio_input_devices(pa)
    if not devices:
        return []

    default_device = resolve_default_input_device(pa)
    default_entry = _default_input_entry(default_device)
    return [default_entry, *devices]


def list_output_devices(pa) -> list[dict]:
    if sys.platform.startswith("linux"):
        pulse_devices = list_pulse_output_devices()
        if pulse_devices:
            return pulse_devices
    return list_pyaudio_output_devices(pa)
