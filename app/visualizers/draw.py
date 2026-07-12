from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF, QLinearGradient, QRadialGradient

from app.utils import avg_level, bass, bin_at, mid, treble, val_at, viz_hsl


def bars(p: QPainter, w: float, h: float, data: dict, state: dict, t: float) -> None:
    sf = data["smooth_freq"]
    n = 96
    gap = 2
    bar_w = w / n
    b = bass(sf)
    hue = 250 + b * 40 + mid(sf) * 30

    for i in range(n):
        v = val_at(sf, (i / n) ** 1.4) / 255.0
        bar_h = v * h * 0.72
        x = i * bar_w + gap / 2
        y = h - bar_h
        grad = QLinearGradient(x, y, x, h)
        grad.setColorAt(0, viz_hsl(state,hue + i * 0.8, 85, 65 + treble(sf) * 15))
        grad.setColorAt(1, viz_hsl(state,hue + i * 0.5, 70, 35, 0.2))
        p.fillRect(QRectF(x, y, bar_w - gap, bar_h), grad)
        if v > 0.55:
            p.fillRect(QRectF(x, y - 4, bar_w - gap, 3), viz_hsl(state,hue + 60, 90, 80, 0.35))

    p.fillRect(QRectF(0, h - 2, w, 2), viz_hsl(state,hue, 60, 50, 0.15 + b * 0.1))


def circular(p: QPainter, w: float, h: float, data: dict, state: dict, t: float) -> None:
    sf = data["smooth_freq"]
    cx, cy = w / 2, h / 2
    base_r = min(w, h) * 0.22
    n = 128
    b = bass(sf)
    hue = 200 + b * 80 + t * 8

    p.save()
    p.translate(cx, cy)
    p.rotate(t * 0.15)

    path_pts = []
    for i in range(n + 1):
        a = (i / n) * math.pi * 2
        v = val_at(sf, i / n) / 255.0
        r = base_r + v * base_r * 1.2
        path_pts.append((math.cos(a) * r, math.sin(a) * r))

    pen = QPen(viz_hsl(state,hue, 80, 60, 0.9), 2)
    p.setPen(pen)
    for i in range(1, len(path_pts)):
        p.drawLine(QPointF(*path_pts[i - 1]), QPointF(*path_pts[i]))
    p.drawLine(QPointF(*path_pts[-1]), QPointF(*path_pts[0]))

    for ring in range(3):
        off = ring * 0.4 + t * 0.5
        pts = []
        for i in range(n + 1):
            a = (i / n) * math.pi * 2 + off
            v = val_at(sf, (i / n) * 0.5) / 255.0 * 0.5
            r = base_r * (0.5 + ring * 0.25) + v * base_r * 0.4
            pts.append((math.cos(a) * r, math.sin(a) * r))
        p.setPen(QPen(viz_hsl(state,hue + ring * 40, 70, 50, 0.25), 1))
        for i in range(1, len(pts)):
            p.drawLine(QPointF(*pts[i - 1]), QPointF(*pts[i]))

    p.restore()
    lvl = avg_level(sf)
    p.setBrush(viz_hsl(state,hue + 120, 90, 55, 0.5 + b))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QPointF(cx, cy), base_r * 0.15 + lvl * 40, base_r * 0.15 + lvl * 40)


def waveform(p: QPainter, w: float, h: float, data: dict, state: dict, t: float) -> None:
    st = data["smooth_time"]
    b = bass(data["smooth_freq"])
    hue = 170 + b * 60
    slice_w = w / len(st)

    p.setPen(QPen(viz_hsl(state,hue, 85, 65), 2))
    for i in range(1, len(st)):
        v0 = (st[i - 1] - 128) / 128
        v1 = (st[i] - 128) / 128
        p.drawLine(
            QPointF((i - 1) * slice_w, h / 2 + v0 * h * 0.35),
            QPointF(i * slice_w, h / 2 + v1 * h * 0.35),
        )

    p.setPen(QPen(viz_hsl(state,hue + 80, 70, 55, 0.25), 2))
    for i in range(1, len(st)):
        v0 = (st[i - 1] - 128) / 128
        v1 = (st[i] - 128) / 128
        p.drawLine(
            QPointF((i - 1) * slice_w, h / 2 - v0 * h * 0.25),
            QPointF(i * slice_w, h / 2 - v1 * h * 0.25),
        )


def mirror_wave(p: QPainter, w: float, h: float, data: dict, state: dict, t: float) -> None:
    st = data["smooth_time"]
    sf = data["smooth_freq"]
    m = mid(sf)
    tr = treble(sf)
    hue = 280 + m * 50
    slice_w = w / len(st)

    for flip, alpha in ((False, 0.9), (True, 0.7)):
        p.setPen(QPen(viz_hsl(state,hue + (60 if flip else 0), 80, 55 + tr * 20, alpha), 1.5))
        for i in range(1, len(st)):
            v0 = (st[i - 1] - 128) / 128
            v1 = (st[i] - 128) / 128
            sign = -1 if flip else 1
            p.drawLine(
                QPointF((i - 1) * slice_w, h / 2 + v0 * h * 0.38 * sign),
                QPointF(i * slice_w, h / 2 + v1 * h * 0.38 * sign),
            )

    grad = QLinearGradient(0, h / 2 - 80, 0, h / 2 + 80)
    grad.setColorAt(0, viz_hsl(state,hue, 70, 50, 0))
    grad.setColorAt(0.5, viz_hsl(state,hue, 80, 50, 0.08 + m * 0.1))
    grad.setColorAt(1, viz_hsl(state,hue, 70, 50, 0))
    p.fillRect(QRectF(0, h / 2 - 100, w, 200), grad)


def radial(p: QPainter, w: float, h: float, data: dict, state: dict, t: float) -> None:
    sf = data["smooth_freq"]
    cx, cy = w / 2, h / 2
    bars_n = 72
    max_r = min(w, h) * 0.48
    b = bass(sf)

    p.save()
    p.translate(cx, cy)
    p.rotate(t * 0.08)

    for i in range(bars_n):
        a0 = (i / bars_n) * math.pi * 2
        a1 = ((i + 0.7) / bars_n) * math.pi * 2
        v = val_at(sf, (i / bars_n) ** 1.2) / 255.0
        r0 = max_r * 0.35
        r1 = r0 + v * max_r * 0.55

        poly = [
            QPointF(math.cos(a0) * r0, math.sin(a0) * r0),
            QPointF(math.cos(a0) * r1, math.sin(a0) * r1),
            QPointF(math.cos(a1) * r1, math.sin(a1) * r1),
            QPointF(math.cos(a1) * r0, math.sin(a1) * r0),
        ]
        p.setBrush(viz_hsl(state,260 + (i / bars_n) * 100 + b * 30, 75, 45 + v * 25, 0.85))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPolygon(*poly)

    p.restore()


def spiral(p: QPainter, w: float, h: float, data: dict, state: dict, t: float) -> None:
    sf = data["smooth_freq"]
    cx, cy = w / 2, h / 2
    b = bass(sf)
    m = mid(sf)
    arms = 3
    steps = 400

    for arm in range(arms):
        offset = (arm / arms) * math.pi * 2
        p.setPen(QPen(viz_hsl(state,240 + arm * 50 + b * 40, 85, 55, 0.7), 1.5))
        for i in range(1, steps):
            prog0 = (i - 1) / steps
            prog1 = i / steps
            v0 = val_at(sf, prog0) / 255.0
            v1 = val_at(sf, prog1) / 255.0
            a0 = prog0 * math.pi * 8 + offset + t * (0.5 + b)
            a1 = prog1 * math.pi * 8 + offset + t * (0.5 + b)
            r0 = prog0 * min(w, h) * 0.45 * (1 + v0 * 0.8 + m * 0.3)
            r1 = prog1 * min(w, h) * 0.45 * (1 + v1 * 0.8 + m * 0.3)
            p.drawLine(
                QPointF(cx + math.cos(a0) * r0, cy + math.sin(a0) * r0),
                QPointF(cx + math.cos(a1) * r1, cy + math.sin(a1) * r1),
            )


def kaleidoscope(p: QPainter, w: float, h: float, data: dict, state: dict, t: float) -> None:
    sf = data["smooth_freq"]
    cx, cy = w / 2, h / 2
    segments = 8
    b = bass(sf)
    n = 64

    for s in range(segments):
        p.save()
        p.translate(cx, cy)
        p.rotate((s / segments) * math.pi * 2 + t * 0.1)
        if s % 2:
            p.scale(1, -1)

        p.setPen(QPen(viz_hsl(state,280 + s * 15 + b * 50, 80, 55, 0.6), 2))
        for i in range(1, n + 1):
            prog0 = (i - 1) / n
            prog1 = i / n
            v0 = val_at(sf, prog0) / 255.0
            v1 = val_at(sf, prog1) / 255.0
            x0 = prog0 * min(w, h) * 0.4
            x1 = prog1 * min(w, h) * 0.4
            y0 = math.sin(prog0 * math.pi * 4 + t * 2) * v0 * 120 * (1 + b * 2)
            y1 = math.sin(prog1 * math.pi * 4 + t * 2) * v1 * 120 * (1 + b * 2)
            p.drawLine(QPointF(x0, y0), QPointF(x1, y1))
        p.restore()


def grid_pulse(p: QPainter, w: float, h: float, data: dict, state: dict, t: float) -> None:
    sf = data["smooth_freq"]
    b = bass(sf)
    cols, rows = 24, 14
    cell_w, cell_h = w / cols, h / rows

    for row in range(rows):
        for col in range(cols):
            col_ratio = col / cols
            v = val_at(sf, col_ratio * 0.7 + (row / rows) * 0.3) / 255.0
            pulse = 0.3 + v * 0.7 + b * 0.2
            size = min(cell_w, cell_h) * 0.35 * pulse
            p.setBrush(viz_hsl(state,200 + col * 4 + row * 6, 70, 40 + v * 35, 0.5 + v * 0.4))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(
                QPointF(col * cell_w + cell_w / 2, row * cell_h + cell_h / 2),
                size,
                size,
            )


def flame(p: QPainter, w: float, h: float, data: dict, state: dict, t: float) -> None:
    sf = data["smooth_freq"]
    cols = max(1, min(120, int(w / 8)))
    if state.get("flame_cols") != cols or "flame" not in state:
        state["flame_cols"] = cols
        state["flame"] = [0.0] * cols

    b = bass(sf)
    tr = treble(sf)
    cell_w = w / cols
    buf = state["flame"]

    for i in range(cols):
        target = (val_at(sf, (i / cols) * 0.3) / 255.0) * h * 0.55 + b * h * 0.15
        buf[i] = buf[i] * 0.88 + target * 0.12

    for i, fh in enumerate(buf):
        x = i * cell_w
        heat = fh / max(h, 1)
        r = min(255, 180 + heat * 75 + tr * 40)
        g = min(255, 40 + heat * 180)
        bl = min(255, heat * 120)
        p.fillRect(QRectF(x, h - fh, cell_w + 1, fh), QColor(int(r), int(g), int(bl), 217))


def matrix(p: QPainter, w: float, h: float, data: dict, state: dict, t: float) -> None:
    sf = data["smooth_freq"]
    cols = max(1, int(w / 16))
    if state.get("matrix_cols") != cols or "matrix" not in state:
        import random

        state["matrix_cols"] = cols
        state["matrix"] = [{"y": random.random() * h, "speed": 4 + random.random() * 8} for _ in range(cols)]

    b = bass(sf)
    p.setFont(QFont("Monospace", 14))
    for i, col in enumerate(state["matrix"]):
        energy = val_at(sf, i / len(state["matrix"])) / 255.0
        col["speed"] = 3 + energy * 18 + b * 8
        col["y"] += col["speed"]
        if col["y"] > h + 50:
            import random

            col["y"] = -random.random() * 200

        x = i * 16 + 4
        g = int(120 + energy * 135 + b * 40)
        char = chr(0x30A0 + ((i * 7 + int(t * 10)) % 96))
        p.setPen(QColor(0, g, int(80 + energy * 100), int(102 + energy * 130)))
        p.drawText(QPointF(x, col["y"]), char)
        p.setPen(QColor(180, 255, 200, int(38 + energy * 102)))
        p.drawText(QPointF(x, col["y"] - 21), char)


def orbits(p: QPainter, w: float, h: float, data: dict, state: dict, t: float) -> None:
    sf = data["smooth_freq"]
    st = data["smooth_time"]
    if "orbits" not in state:
        import random

        state["orbits"] = [
            {"radius": 40 + i * 22, "speed": 0.3 + i * 0.08, "phase": (i / 12) * math.pi * 2, "hue": i * 30}
            for i in range(12)
        ]

    cx, cy = w / 2, h / 2
    b = bass(sf)
    m = mid(sf)

    for i, o in enumerate(state["orbits"]):
        v = val_at(sf, i / len(state["orbits"])) / 255.0
        angle = t * o["speed"] + o["phase"] + (st[min(i * 64, len(st) - 1)] - 128) * 0.02
        r = o["radius"] * (1 + v * 0.8 + b * 0.5)
        x = cx + math.cos(angle) * r
        y = cy + math.sin(angle) * r * (0.7 + m * 0.3)

        p.setBrush(viz_hsl(state,o["hue"] + t * 30, 85, 55, 0.7 + v * 0.3))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(x, y), 4 + v * 12, 4 + v * 12)

        p.setPen(QPen(viz_hsl(state,o["hue"] + t * 20, 60, 45, 0.08 + v * 0.12), 1))
        p.drawEllipse(QPointF(cx, cy), r, r * (0.7 + m * 0.3))


def blobs(p: QPainter, w: float, h: float, data: dict, state: dict, t: float) -> None:
    sf = data["smooth_freq"]
    if "blobs" not in state:
        import random

        state["blobs"] = [
            {
                "x": 0.2 + (i % 3) * 0.3,
                "y": 0.2 + (i // 3) * 0.3,
                "vx": (random.random() - 0.5) * 0.002,
                "vy": (random.random() - 0.5) * 0.002,
            }
            for i in range(9)
        ]

    b = bass(sf)
    m = mid(sf)
    tr = treble(sf)

    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
    for i, bl in enumerate(state["blobs"]):
        v = val_at(sf, i / len(state["blobs"])) / 255.0
        bl["x"] += bl["vx"] * (1 + b * 3)
        bl["y"] += bl["vy"] * (1 + m)
        if bl["x"] < 0.1 or bl["x"] > 0.9:
            bl["vx"] *= -1
        if bl["y"] < 0.1 or bl["y"] > 0.9:
            bl["vy"] *= -1

        radius = (60 + v * 140) * (1 + b * 0.5)
        x = bl["x"] * w
        y = bl["y"] * h
        grad = QRadialGradient(x, y, radius)
        grad.setColorAt(0, viz_hsl(state,260 + i * 25 + tr * 60, 90, 60, 0.35 + v * 0.25))
        grad.setColorAt(1, viz_hsl(state,280 + i * 20, 80, 40, 0))
        p.setBrush(grad)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(x, y), radius, radius)

    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)


def warp(p: QPainter, w: float, h: float, data: dict, state: dict, t: float) -> None:
    sf = data["smooth_freq"]
    count = 350
    if state.get("stars_count") != count or "stars" not in state:
        import random

        state["stars_count"] = count
        state["stars"] = [
            {"x": (random.random() - 0.5) * w, "y": (random.random() - 0.5) * h, "z": random.random()}
            for _ in range(count)
        ]

    cx, cy = w / 2, h / 2
    b = bass(sf)
    speed = 0.02 + b * 0.12

    for s in state["stars"]:
        bin_i = bin_at(sf, s["z"])
        energy = sf[bin_i] / 255.0
        s["z"] -= speed * (1 + energy * 2)
        if s["z"] <= 0:
            import random

            s["z"] = 1.0
            s["x"] = (random.random() - 0.5) * w
            s["y"] = (random.random() - 0.5) * h

        k = 1 / s["z"]
        px = cx + s["x"] * k
        py = cy + s["y"] * k
        prev_z = s["z"] + speed
        pk = 1 / prev_z
        ppx = cx + s["x"] * pk
        ppy = cy + s["y"] * pk
        hue = 200 + energy * 100 + b * 40
        p.setPen(QPen(viz_hsl(state,hue, 80, 55 + energy * 30, 0.4 + energy * 0.5), 1 + energy * 2))
        p.drawLine(QPointF(ppx, ppy), QPointF(px, py))


def terrain(p: QPainter, w: float, h: float, data: dict, state: dict, t: float) -> None:
    sf = data["smooth_freq"]
    cols = max(1, min(160, int(w / 6)))
    if state.get("terrain_cols") != cols or "heights" not in state:
        state["terrain_cols"] = cols
        state["heights"] = [0.0] * cols
        state["target"] = [0.0] * cols

    b = bass(sf)
    slice_w = w / cols
    heights = state["heights"]
    target = state["target"]

    for i in range(cols):
        target[i] = (val_at(sf, (i / cols) ** 1.1) / 255.0) * h * 0.55 + b * h * 0.08
        heights[i] += (target[i] - heights[i]) * 0.25

    poly = QPolygonF([QPointF(0, h)])
    for i, ht in enumerate(heights):
        poly.append(QPointF(i * slice_w, h - ht))
    poly.append(QPointF(w, h))

    grad = QLinearGradient(0, h * 0.3, 0, h)
    grad.setColorAt(0, viz_hsl(state,260 + b * 40, 80, 55, 0.9))
    grad.setColorAt(0.5, viz_hsl(state,220 + t * 10, 70, 35, 0.6))
    grad.setColorAt(1, viz_hsl(state,200, 60, 15, 0.3))
    p.setBrush(grad)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawPolygon(poly)

    p.setPen(QPen(viz_hsl(state,180, 90, 70, 0.5 + b * 0.3), 2))
    for i in range(1, cols):
        p.drawLine(
            QPointF((i - 1) * slice_w, h - heights[i - 1]),
            QPointF(i * slice_w, h - heights[i]),
        )


def ring_tunnel(p: QPainter, w: float, h: float, data: dict, state: dict, t: float) -> None:
    sf = data["smooth_freq"]
    cx, cy = w / 2, h / 2
    b = bass(sf)
    lvl = avg_level(sf)
    rings = 28

    for i in range(rings, -1, -1):
        prog = i / rings
        v = val_at(sf, prog) / 255.0
        pulse = 1 + v * 0.6 + b * 0.4
        radius = prog * min(w, h) * 0.55 * pulse + math.sin(t * 2 + i * 0.4) * 8 * (1 + lvl)
        p.setPen(QPen(viz_hsl(state,280 - prog * 120 + t * 20, 75, 45 + v * 30, 0.15 + (1 - prog) * 0.5), 2 + v * 4))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), max(2, radius), max(2, radius))


def scope3d(p: QPainter, w: float, h: float, data: dict, state: dict, t: float) -> None:
    st = data["smooth_time"]
    sf = data["smooth_freq"]
    b = bass(sf)
    m = mid(sf)
    cx, cy = w / 2, h / 2
    scale = min(w, h) * 0.32
    n = 180
    tilt = 0.55 + m * 0.2

    points = []
    for i in range(n):
        a = (i / n) * math.pi * 2 + t * 0.5
        idx = bin_at(st, i / n)
        v = (st[idx] - 128) / 128
        f = val_at(sf, i / n) / 255.0
        r = scale * (0.6 + f * 0.5 + b * 0.3)
        x3 = math.cos(a) * r
        y3 = math.sin(a * 2 + t) * v * scale * 0.5
        z3 = math.sin(a) * r
        y2 = y3 * math.cos(tilt) - z3 * math.sin(tilt)
        points.append({"x": cx + x3, "y": cy + y2, "z": z3})

    points.sort(key=lambda pt: pt["z"])
    p.setPen(QPen(viz_hsl(state,200 + b * 80, 85, 60, 0.85), 2))
    for i in range(1, len(points)):
        p.drawLine(
            QPointF(points[i - 1]["x"], points[i - 1]["y"]),
            QPointF(points[i]["x"], points[i]["y"]),
        )
    p.drawLine(
        QPointF(points[-1]["x"], points[-1]["y"]),
        QPointF(points[0]["x"], points[0]["y"]),
    )

    for i in range(0, len(points), 4):
        pt = points[i]
        depth = (pt["z"] + scale) / (scale * 2)
        p.setBrush(viz_hsl(state,220 + depth * 80, 90, 55, 0.4 + depth * 0.4))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(pt["x"], pt["y"]), 2 + depth * 4, 2 + depth * 4)


def particles(p: QPainter, w: float, h: float, data: dict, state: dict, t: float) -> None:
    sf = data["smooth_freq"]
    count = state.get("particle_count", 1800)
    if state.get("particles_count") != count or "particles" not in state:
        import random

        state["particles_count"] = count
        state["particles"] = [
            {
                "x": random.random() * w,
                "y": random.random() * h,
                "vx": (random.random() - 0.5) * 2,
                "vy": (random.random() - 0.5) * 2,
                "hue": random.random() * 360,
                "size": 1 + random.random() * 2,
            }
            for _ in range(count)
        ]

    import random

    b = bass(sf)
    tr = treble(sf)
    cx, cy = w / 2, h / 2
    boost = 1 + b * 4 + tr * 2

    for i, part in enumerate(state["particles"]):
        energy = val_at(sf, i / len(state["particles"])) / 255.0
        dx = cx - part["x"]
        dy = cy - part["y"]
        dist = math.hypot(dx, dy) or 1
        part["vx"] += (dx / dist) * energy * 0.08 * boost
        part["vy"] += (dy / dist) * energy * 0.08 * boost
        part["vx"] += (random.random() - 0.5) * energy * 0.5
        part["vy"] += (random.random() - 0.5) * energy * 0.5
        part["vx"] *= 0.92
        part["vy"] *= 0.92
        part["x"] += part["vx"] * (1 + energy * 2)
        part["y"] += part["vy"] * (1 + energy * 2)

        if part["x"] < 0:
            part["x"] = w
        elif part["x"] > w:
            part["x"] = 0
        if part["y"] < 0:
            part["y"] = h
        elif part["y"] > h:
            part["y"] = 0

        sz = part["size"] + energy * 3 * boost
        p.setBrush(viz_hsl(state,200 + energy * 120 + part["hue"] * 0.02, 85, 55 + energy * 25, 0.3 + energy * 0.7))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(part["x"], part["y"]), sz, sz)
