# UI Theme Constants
COLORS = {
    "background": "#0A0A0A",
    "sidebar": "#111111",
    "card": "#141414",
    "card_hover": "#1A1A1A",
    "primary": "#2D63ED",
    "primary_hover": "#3D73FD",
    "danger": "#E03131",
    "danger_hover": "#F04141",
    "success": "#00BFA5",
    "secondary": "#222222",
    "secondary_hover": "#2A2A2A",
    "border": "#252525",
    "border_light": "#333333",
    "border_focus": "#444444",
    "text_main": "#FFFFFF",
    "text_secondary": "#888888",
    "text_muted": "#555555",
    "text_dim": "#999999",
    "input_bg": "#111111",
    "header_bg": "#161616",
}

STYLE_SHEET = f"""
    QMainWindow {{ background-color: {COLORS['background']}; }}
    QWidget {{ font-family: 'Inter', 'Segoe UI', 'Roboto', 'Arial'; color: {COLORS['text_main']}; }}

    /* Sidebar */
    #Sidebar {{ background-color: {COLORS['sidebar']}; border-right: 1px solid {COLORS['secondary']}; }}
    QListWidget#NavList {{ border: none; background-color: transparent; outline: none; }}

    /* Content Area */
    #ContentStack {{ background-color: {COLORS['background']}; }}
    #ContentStack > QWidget {{ background-color: {COLORS['background']}; }}

    /* Scrollbars */
    QScrollBar:vertical {{
        border: none;
        background: {COLORS['sidebar']};
        width: 10px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {COLORS['border_light']};
        min-height: 20px;
        border-radius: 5px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        border: none;
        background: none;
    }}

    /* Navigation Items */
    QListWidget#NavList::item {{
        padding: 16px;
        border-radius: 8px;
        margin: 4px 8px;
        color: {COLORS['text_secondary']};
        font-weight: 500;
    }}
    QListWidget#NavList::item:selected {{
        background-color: {COLORS['card_hover']};
        color: {COLORS['text_main']};
        border: 1px solid {COLORS['border_light']};
    }}
    QListWidget#NavList::item:hover:!selected {{
        background-color: {COLORS['header_bg']};
        color: #BBB;
    }}

    /* Cards */
    QFrame.Card {{
        background-color: {COLORS['card']};
        border-radius: 12px;
        border: 1px solid {COLORS['border']};
    }}
    QFrame.Card:hover {{
        border: 1px solid {COLORS['border_light']};
    }}

    /* Buttons */
    QPushButton {{
        padding: 10px 18px;
        border-radius: 8px;
        font-weight: 600;
        font-size: 13px;
        border: 1px solid transparent;
    }}
    QPushButton#PrimaryAction {{
        background-color: {COLORS['primary']};
        color: white;
    }}
    QPushButton#PrimaryAction:hover {{
        background-color: {COLORS['primary_hover']};
    }}
    QPushButton#StopAction {{
        background-color: {COLORS['danger']};
        color: white;
    }}
    QPushButton#StopAction:hover {{
        background-color: {COLORS['danger_hover']};
    }}
    QPushButton#SecondaryAction {{
        background-color: {COLORS['secondary']};
        color: #EEE;
        border: 1px solid {COLORS['border_light']};
    }}
    QPushButton#SecondaryAction:hover {{
        background-color: {COLORS['secondary_hover']};
    }}

    /* Inputs */
    QLineEdit, QSpinBox, QComboBox, QTextEdit {{
        background-color: {COLORS['input_bg']};
        color: #EEE;
        border: 1px solid {COLORS['secondary']};
        padding: 10px;
        border-radius: 8px;
        selection-background-color: {COLORS['primary']};
    }}
    QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QTextEdit:focus {{
        border: 1px solid {COLORS['border_focus']};
        background-color: {COLORS['card']};
    }}

    /* Tables */
    QTableWidget {{
        background-color: transparent;
        border: none;
        color: #DDD;
        gridline-color: {COLORS['secondary']};
        outline: none;
    }}
    QHeaderView::section {{
        background-color: {COLORS['header_bg']};
        color: {COLORS['text_dim']};
        padding: 12px;
        border: none;
        font-weight: 600;
        text-transform: uppercase;
        font-size: 11px;
        letter-spacing: 0.5px;
    }}
    QTableWidget::item {{ padding: 12px; }}

    /* Tabs */
    QTabWidget::pane {{ border: 1px solid {COLORS['secondary']}; background: {COLORS['card']}; border-radius: 8px; top: -1px; }}
    QTabBar::tab {{
        background: transparent;
        color: #777;
        padding: 12px 24px;
        font-weight: 600;
        border-bottom: 2px solid transparent;
    }}
    QTabBar::tab:selected {{
        color: {COLORS['primary']};
        border-bottom: 2px solid {COLORS['primary']};
    }}
    QTabBar::tab:hover:!selected {{ color: #BBB; }}

    /* Progress Bar */
    QProgressBar {{
        height: 8px;
        border-radius: 4px;
        background-color: {COLORS['card_hover']};
        text-align: center;
        border: none;
    }}
    QProgressBar::chunk {{
        background-color: {COLORS['primary']};
        border-radius: 4px;
    }}

    /* Log View specific */
    #LogView {{
        background-color: #050505;
        color: #BBB;
        font-family: 'Consolas', monospace;
        font-size: 12px;
        border: 1px solid {COLORS['secondary']};
    }}
"""
