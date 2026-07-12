PURPLE_STYLESHEET = """
QWidget {
    color: #eeeaff;
    font-family: "Inter", "Segoe UI", "Noto Sans", sans-serif;
    font-size: 13px;
}

QMainWindow, QDialog {
    background: #090711;
}

QMenuBar {
    background: #100d1c;
    color: #cfc7e8;
    border-bottom: 1px solid #2a2142;
    padding: 3px 8px;
}
QMenuBar::item {
    padding: 6px 11px;
    border-radius: 6px;
}
QMenuBar::item:selected {
    background: #29203f;
    color: white;
}
QMenu {
    background: #171225;
    border: 1px solid #392b57;
    border-radius: 8px;
    padding: 6px;
}
QMenu::item {
    padding: 8px 28px 8px 12px;
    border-radius: 5px;
}
QMenu::item:selected {
    background: #6d3eea;
    color: white;
}

QDockWidget {
    background: #0f0c19;
    border: none;
}
QDockWidget > QWidget {
    border-right: 1px solid #2b2140;
}
#editorDock > QWidget {
    border-right: none;
    border-left: 1px solid #2b2140;
}
#visualizerEditor {
    background: #0f0c19;
}
#editorHint {
    color: #8b809c;
    font-size: 11px;
    line-height: 1.45;
    padding: 4px 2px 8px 2px;
}
#controlPanel {
    background: #0f0c19;
}
#logo {
    color: #b68cff;
    font-size: 27px;
    font-weight: 800;
    letter-spacing: 4px;
}
#tagline {
    color: #756b8c;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 3px;
}
#sectionTitle {
    color: #827795;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2px;
    margin-top: 4px;
}
#sourceStatus {
    background: #171223;
    color: #8b809c;
    border: 1px solid #2a203b;
    border-radius: 8px;
    padding: 9px 11px;
}
#sourceStatus[active="true"] {
    color: #d8c8ff;
    border-color: #5936a0;
    background: #1d1430;
}
#shortcuts {
    color: #6e657e;
    font-size: 10px;
    line-height: 1.5;
}
#divider {
    color: #2a2139;
    max-height: 1px;
}

QPushButton {
    background: #211833;
    color: #e9e2f8;
    border: 1px solid #3b2a5a;
    border-radius: 9px;
    padding: 9px 14px;
    font-weight: 600;
}
QPushButton:hover {
    background: #302047;
    border-color: #7651bc;
}
QPushButton:pressed {
    background: #1a1129;
}
#primaryButton {
    background: #7444e8;
    border-color: #9568f5;
    color: white;
}
#primaryButton:hover {
    background: #8555f2;
}
#secondaryButton {
    background: #211735;
    border-color: #5b3a91;
}
#ghostButton {
    background: transparent;
}
#dangerButton {
    background: transparent;
    color: #ad9dbd;
    border-color: #342a40;
}

#visualizerList {
    background: #0b0912;
    border: 1px solid #251c36;
    border-radius: 10px;
    padding: 5px;
    outline: none;
}
#visualizerList::item {
    color: #9d92ae;
    padding: 8px 10px;
    margin: 1px;
    border-radius: 6px;
}
#visualizerList::item:hover {
    background: #1b1429;
    color: #ddd2ee;
}
#visualizerList::item:selected {
    background: #6c3ee0;
    color: white;
}

QStatusBar {
    background: #0e0b17;
    color: #8e829f;
    border-top: 1px solid #2a213a;
}
QStatusBar QLabel {
    color: #a99db9;
    padding-left: 6px;
}

QProgressBar {
    background: #181225;
    border: 1px solid #382751;
    border-radius: 7px;
    min-height: 13px;
    text-align: center;
    color: white;
    font-weight: 700;
}
QProgressBar::chunk {
    border-radius: 6px;
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #6d3eea,
        stop: 0.55 #9a5cff,
        stop: 1 #d073ff
    );
}

QComboBox, QLineEdit {
    background: #171225;
    color: #eee8fa;
    border: 1px solid #49336b;
    border-radius: 8px;
    padding: 8px 11px;
}
QComboBox:hover, QComboBox:focus {
    border-color: #9264de;
}
QComboBox QAbstractItemView {
    background: #171225;
    color: #eee8fa;
    selection-background-color: #6d3eea;
    border: 1px solid #49336b;
    padding: 5px;
}

QSlider::groove:horizontal {
    height: 5px;
    background: #292037;
    border-radius: 2px;
}
QSlider::sub-page:horizontal {
    background: #8854ee;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    width: 16px;
    margin: -6px 0;
    border-radius: 8px;
    background: #c5a5ff;
    border: 2px solid #7542dc;
}
QCheckBox::indicator {
    width: 17px;
    height: 17px;
    border-radius: 4px;
    border: 1px solid #5a417c;
    background: #171225;
}
QCheckBox::indicator:checked {
    background: #8250e8;
    border-color: #ad82ff;
}

#dialogTitle, #importTitle {
    color: #f3edff;
    font-size: 20px;
    font-weight: 750;
}
#dialogSubtitle, #importMuted {
    color: #9186a3;
}
#deviceDescription, #hintCard, #importDetail {
    background: #171225;
    border: 1px solid #332448;
    border-radius: 8px;
    padding: 11px;
    color: #bdb1cc;
}
#hintCard {
    color: #aa91d7;
    background: #1b1230;
    border-color: #4a2b7b;
}
#importFile {
    color: #c7a7ff;
    font-size: 15px;
    font-weight: 650;
}

QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 3px;
}
QScrollBar::handle:vertical {
    background: #483462;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
"""
