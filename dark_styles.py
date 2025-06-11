# dark_styles.py

LIGHT_STYLE_SHEET = """
    QMainWindow {
        background-color: #F0F0F0;
    }
    QWidget {
        color: #202020;
        font-size: 11pt;
    }
    QDialog {
        background-color: #FFFFFF;
    }
    QTabWidget::pane {
        border-top: 1px solid #C0C0C0;
        margin-top: -1px;
    }
    QTabBar::tab {
        background: #FFFFFF;
        border: 1px solid #C0C0C0;
        border-bottom-color: #F0F0F0;
        padding: 6px 12px;
        margin-right: 2px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }
    QTabBar::tab:selected {
        background: #F0F0F0;
        border-bottom-color: #F0F0F0;
        margin-bottom: -1px;
    }
    QTabBar::tab:!selected:hover {
        background: #FAFAFA;
    }

    QSplitter::handle {
        background-color: #C0C0C0;
        height: 1px;
        width: 1px;
    }
    QSplitter::handle:hover {
        background-color: #0078D7;
    }
    QSplitter::handle:pressed {
        background-color: #005A9E;
    }

    QTreeView, QTreeWidget {
        background-color: #FFFFFF;
        border: 1px solid #C0C0C0;
        alternate-background-color: #FAFAFA;
        selection-background-color: #0078D7;
        selection-color: #FFFFFF;
    }
    QTreeView::item, QTreeWidget::item {
        padding: 4px;
    }

    QHeaderView::section {
        background-color: #FFFFFF;
        border: 1px solid #C0C0C0;
        padding: 4px;
        font-weight: bold;
    }

    QLineEdit, QTextEdit {
        background-color: #FFFFFF;
        border: 1px solid #C0C0C0;
        padding: 4px;
        border-radius: 3px;
    }
    QTextEdit {
        selection-background-color: #0078D7;
        selection-color: #FFFFFF;
    }
    QLineEdit:focus, QTextEdit:focus {
        border: 1px solid #0078D7;
    }

    QPushButton {
        background-color: #E1E1E1;
        border: 1px solid #ADADAD;
        padding: 6px 12px;
        border-radius: 3px;
        min-width: 60px;
    }
    QPushButton:hover {
        background-color: #CACACA;
        border: 1px solid #0078D7;
    }
    QPushButton:pressed {
        background-color: #B0B0B0;
    }
    QPushButton:disabled {
        background-color: #D3D3D3;
        color: #A0A0A0;
        border-color: #C0C0C0;
    }

    QComboBox {
        border: 1px solid #C0C0C0;
        border-radius: 3px;
        padding: 1px 18px 1px 3px;
        min-width: 6em;
        background-color: #FFFFFF;
    }
    QComboBox:editable {
        background: #FFFFFF;
    }
    QComboBox:!editable, QComboBox::drop-down:editable {
         background: #FFFFFF;
    }
    QComboBox:!editable:on, QComboBox::drop-down:editable:on {
        background: #FFFFFF;
    }
    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 15px;
        border-left-width: 1px;
        border-left-color: #C0C0C0;
        border-left-style: solid;
        border-top-right-radius: 3px;
        border-bottom-right-radius: 3px;
    }
    QComboBox::down-arrow {
        image: url(:/qt-project.org/styles/commonstyle/images/arrow-down-16.png);
    }
    QComboBox::down-arrow:on {
        top: 1px;
        left: 1px;
    }
    QComboBox QAbstractItemView {
        border: 1px solid #C0C0C0;
        background-color: #FFFFFF;
        selection-background-color: #0078D7;
        selection-color: #FFFFFF;
    }

    QScrollBar:horizontal {
        border: none;
        background: #FFFFFF;
        height: 10px;
        margin: 0px 10px 0 10px;
    }
    QScrollBar::handle:horizontal {
        background: #B0B0B0;
        min-width: 20px;
        border-radius: 4px;
    }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        background: none;
        border: none;
        width: 10px;
    }
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
        background: none;
    }

    QScrollBar:vertical {
        border: none;
        background: #FFFFFF;
        width: 10px;
        margin: 10px 0 10px 0;
    }
    QScrollBar::handle:vertical {
        background: #B0B0B0;
        min-height: 20px;
        border-radius: 4px;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        background: none;
        border: none;
        height: 10px;
    }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        background: none;
    }

    QToolBar {
        background-color: #FFFFFF;
        border-bottom: 1px solid #C0C0C0;
        padding: 2px;
        spacing: 3px;
    }
    QToolBar QToolButton {
        background-color: transparent;
        border: 1px solid transparent;
        padding: 4px;
    }
    QToolBar QToolButton:hover {
        background-color: #CACACA;
        border: 1px solid #0078D7;
    }
    QToolBar QToolButton:pressed {
        background-color: #B0B0B0;
    }
    QToolBar::separator {
        height: 1px;
        background-color: #C0C0C0;
        margin-left: 2px;
        margin-right: 2px;
    }
    QLabel#periodLabel {
        padding: 4px 8px; border-radius: 4px; font-family: monospace; font-size: 10pt;
        background-color: #E8F5E8;
    }
    QLabel#totalLabel {
        padding: 4px 8px; border-radius: 4px; font-family: monospace; font-size: 10pt;
        background-color: #E3F2FD; font-weight: bold;
    }

    QPushButton#errorButton { background-color: #FFEBEE; color: #D32F2F; border: 1px solid #D32F2F; }
    QPushButton#errorButton:hover { background-color: #FFCDD2; }
    QPushButton#warnButton { background-color: #FFF3E0; color: #F57C00; border: 1px solid #F57C00; }
    QPushButton#warnButton:hover { background-color: #FFE0B2; }
    QPushButton#infoButton { background-color: #E3F2FD; color: #1976D2; border: 1px solid #1976D2; }
    QPushButton#infoButton:hover { background-color: #BBDEFB; }
    QPushButton#debugButton { background-color: #F3E5F5; color: #7B1FA2; border: 1px solid #7B1FA2; }
    QPushButton#debugButton:hover { background-color: #E1BEE7; }

    QPushButton#statsButton {
        font-size: 14pt; border: none; padding: 0px; min-width: 24px; background-color: transparent;
    }
    QPushButton#statsButton:hover {
        background-color: #CACACA;
    }
    QPushButton#messageTypeSearchClearBtn {
        font-size: 12pt; border: none; padding: 0px; min-width: 24px; background-color: transparent;
    }
    QPushButton#messageTypeSearchClearBtn:hover {
        background-color: #CACACA;
    }
"""

DARK_STYLE_SHEET = """
    QMainWindow {
        background-color: #2E2E2E;
    }
    QWidget {
        color: #E0E0E0;
        font-size: 11pt;
    }
    QDialog {
        background-color: #3C3C3C;
    }
    QTabWidget::pane {
        border-top: 1px solid #4A4A4A;
        margin-top: -1px;
    }
    QTabBar::tab {
        background: #3C3C3C;
        border: 1px solid #4A4A4A;
        border-bottom-color: #2E2E2E;
        padding: 6px 12px;
        margin-right: 2px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }
    QTabBar::tab:selected {
        background: #2E2E2E;
        border-bottom-color: #2E2E2E;
        margin-bottom: -1px;
    }
    QTabBar::tab:!selected:hover {
        background: #353535;
    }

    QSplitter::handle {
        background-color: #4A4A4A;
        height: 1px;
        width: 1px;
    }
    QSplitter::handle:hover {
        background-color: #007ACC;
    }
    QSplitter::handle:pressed {
        background-color: #005C9E;
    }

    QTreeView, QTreeWidget {
        background-color: #383838;
        border: 1px solid #4A4A4A;
        alternate-background-color: #353535;
        selection-background-color: #007ACC;
        selection-color: #FFFFFF;
    }
    QTreeView::item, QTreeWidget::item {
        padding: 4px;
    }

    QHeaderView::section {
        background-color: #3C3C3C;
        border: 1px solid #4A4A4A;
        padding: 4px;
        font-weight: bold;
    }

    QLineEdit, QTextEdit {
        background-color: #383838;
        border: 1px solid #4A4A4A;
        padding: 4px;
        border-radius: 3px;
    }
    QTextEdit {
        selection-background-color: #007ACC;
        selection-color: #FFFFFF;
    }
    QLineEdit:focus, QTextEdit:focus {
        border: 1px solid #007ACC;
    }

    QPushButton {
        background-color: #4A4A4A;
        border: 1px solid #5A5A5A;
        padding: 6px 12px;
        border-radius: 3px;
        min-width: 60px;
    }
    QPushButton:hover {
        background-color: #585858;
        border: 1px solid #007ACC;
    }
    QPushButton:pressed {
        background-color: #656565;
    }
    QPushButton:disabled {
        background-color: #404040;
        color: #777777;
        border-color: #505050;
    }

    QComboBox {
        border: 1px solid #4A4A4A;
        border-radius: 3px;
        padding: 1px 18px 1px 3px;
        min-width: 6em;
        background-color: #383838;
    }
    QComboBox:editable {
        background: #383838;
    }
    QComboBox:!editable, QComboBox::drop-down:editable {
         background: #383838;
    }
    QComboBox:!editable:on, QComboBox::drop-down:editable:on {
        background: #383838;
    }
    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 15px;
        border-left-width: 1px;
        border-left-color: #4A4A4A;
        border-left-style: solid;
        border-top-right-radius: 3px;
        border-bottom-right-radius: 3px;
    }
    QComboBox::down-arrow {
        image: url(:/qt-project.org/styles/commonstyle/images/arrow-down-inverted-16.png); /* Inverted arrow for dark themes */
    }
    QComboBox::down-arrow:on {
        top: 1px;
        left: 1px;
    }
    QComboBox QAbstractItemView {
        border: 1px solid #4A4A4A;
        background-color: #383838;
        selection-background-color: #007ACC;
        selection-color: #FFFFFF;
    }

    QScrollBar:horizontal {
        border: none;
        background: #3C3C3C;
        height: 10px;
        margin: 0px 10px 0 10px;
    }
    QScrollBar::handle:horizontal {
        background: #555555;
        min-width: 20px;
        border-radius: 4px;
    }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        background: none;
        border: none;
        width: 10px;
    }
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
        background: none;
    }

    QScrollBar:vertical {
        border: none;
        background: #3C3C3C;
        width: 10px;
        margin: 10px 0 10px 0;
    }
    QScrollBar::handle:vertical {
        background: #555555;
        min-height: 20px;
        border-radius: 4px;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        background: none;
        border: none;
        height: 10px;
    }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        background: none;
    }

    QToolBar {
        background-color: #3C3C3C;
        border-bottom: 1px solid #4A4A4A;
        padding: 2px;
        spacing: 3px;
    }
    QToolBar QToolButton {
        background-color: transparent;
        border: 1px solid transparent;
        padding: 4px;
        color: #E0E0E0; /* Couleur du texte pour les QToolButton */
    }
    QToolBar QToolButton:hover {
        background-color: #585858;
        border: 1px solid #007ACC;
    }
    QToolBar QToolButton:pressed {
        background-color: #656565;
    }
    QToolBar::separator {
        height: 1px;
        background-color: #4A4A4A;
        margin-left: 2px;
        margin-right: 2px;
    }
    QLabel#periodLabel {
        padding: 4px 8px; border-radius: 4px; font-family: monospace; font-size: 10pt;
        background-color: #3A4F3A; /* Vert foncé */
    }
    QLabel#totalLabel {
        padding: 4px 8px; border-radius: 4px; font-family: monospace; font-size: 10pt;
        background-color: #3A3A4F; /* Bleu foncé */
        font-weight: bold;
    }

    QPushButton#errorButton { background-color: #5D3F3F; color: #F48A8A; border: 1px solid #F48A8A; }
    QPushButton#errorButton:hover { background-color: #6D4F4F; }
    QPushButton#warnButton { background-color: #605542; color: #FFCC80; border: 1px solid #FFCC80; }
    QPushButton#warnButton:hover { background-color: #706552; }
    QPushButton#infoButton { background-color: #3F525D; color: #A0D8FF; border: 1px solid #A0D8FF; }
    QPushButton#infoButton:hover { background-color: #4F626D; }
    QPushButton#debugButton { background-color: #504260; color: #CEA0F2; border: 1px solid #CEA0F2; }
    QPushButton#debugButton:hover { background-color: #605270; }

    QPushButton#statsButton {
        font-size: 14pt; border: none; padding: 0px; min-width: 24px; background-color: transparent;
    }
    QPushButton#statsButton:hover {
        background-color: #585858;
    }
    QPushButton#messageTypeSearchClearBtn {
        font-size: 12pt; border: none; padding: 0px; min-width: 24px; background-color: transparent;
    }
    QPushButton#messageTypeSearchClearBtn:hover {
        background-color: #585858;
    }
"""

# Les dictionnaires de couleurs ne sont plus utilisés pour formater COMMON_STYLE,
# mais peuvent être utiles si vous voulez accéder à des couleurs spécifiques
# dans votre code Python pour, par exemple, Matplotlib.
# Si vous n'en avez pas besoin ailleurs, vous pouvez les supprimer.
DARK_COLORS = {
    "BG_COLOR": "#2E2E2E",
    "BG_COLOR_LIGHTER": "#3C3C3C",
    "BG_COLOR_SLIGHTLY_LIGHTER": "#353535",
    "TEXT_COLOR": "#E0E0E0",
    "TEXT_COLOR_ACCENT": "#FFFFFF",
    "BORDER_COLOR": "#4A4A4A",
    "INPUT_BG_COLOR": "#383838",
    "ACCENT_COLOR": "#007ACC",
    "ACCENT_COLOR_DARKER": "#005C9E",
    "BUTTON_BG_COLOR": "#4A4A4A",
    "BUTTON_BORDER_COLOR": "#5A5A5A",
    "BUTTON_HOVER_BG_COLOR": "#585858",
    "BUTTON_PRESSED_BG_COLOR": "#656565",
    "SCROLLBAR_HANDLE_COLOR": "#555555",
    "DISABLED_BG_COLOR": "#404040",
    "DISABLED_TEXT_COLOR": "#777777",
    "DISABLED_BORDER_COLOR": "#505050",
    "INFO_BG_LIGHT": "#3A4F3A",
    "SUCCESS_BG_LIGHT": "#3A3A4F",
    "ERROR_BG": "#5D3F3F", "ERROR_FG": "#F48A8A", "ERROR_BG_HOVER": "#6D4F4F",
    "WARN_BG": "#605542", "WARN_FG": "#FFCC80", "WARN_BG_HOVER": "#706552",
    "INFO_BTN_BG": "#3F525D", "INFO_BTN_FG": "#A0D8FF", "INFO_BTN_BG_HOVER": "#4F626D",
    "DEBUG_BG": "#504260", "DEBUG_FG": "#CEA0F2", "DEBUG_BG_HOVER": "#605270",
}

LIGHT_COLORS = {
    "BG_COLOR": "#F0F0F0",
    "BG_COLOR_LIGHTER": "#FFFFFF",
    "BG_COLOR_SLIGHTLY_LIGHTER": "#FAFAFA",
    "TEXT_COLOR": "#202020",
    "TEXT_COLOR_ACCENT": "#FFFFFF",
    "BORDER_COLOR": "#C0C0C0",
    "INPUT_BG_COLOR": "#FFFFFF",
    "ACCENT_COLOR": "#0078D7",
    "ACCENT_COLOR_DARKER": "#005A9E",
    "BUTTON_BG_COLOR": "#E1E1E1",
    "BUTTON_BORDER_COLOR": "#ADADAD",
    "BUTTON_HOVER_BG_COLOR": "#CACACA",
    "BUTTON_PRESSED_BG_COLOR": "#B0B0B0",
    "SCROLLBAR_HANDLE_COLOR": "#B0B0B0",
    "DISABLED_BG_COLOR": "#D3D3D3",
    "DISABLED_TEXT_COLOR": "#A0A0A0",
    "DISABLED_BORDER_COLOR": "#C0C0C0",
    "INFO_BG_LIGHT": "#E8F5E8",
    "SUCCESS_BG_LIGHT": "#E3F2FD",
    "ERROR_BG": "#FFEBEE", "ERROR_FG": "#D32F2F", "ERROR_BG_HOVER": "#FFCDD2",
    "WARN_BG": "#FFF3E0", "WARN_FG": "#F57C00", "WARN_BG_HOVER": "#FFE0B2",
    "INFO_BTN_BG": "#E3F2FD", "INFO_BTN_FG": "#1976D2", "INFO_BTN_BG_HOVER": "#BBDEFB",
    "DEBUG_BG": "#F3E5F5", "DEBUG_FG": "#7B1FA2", "DEBUG_BG_HOVER": "#E1BEE7",
}