from __future__ import annotations

from PySide6.QtWidgets import QMenu


LULU_MENU_STYLE = """
QMenu {
    background-color: #FFF4DA;
    color: #3B271C;
    border: 1px solid #8F6346;
    border-radius: 7px;
    padding: 5px;
    font-size: 12px;
}

QMenu::item {
    background-color: transparent;
    border-radius: 5px;
    padding: 5px 22px 5px 14px;
    margin: 1px 0;
}

QMenu::item:selected {
    background-color: #C78652;
    color: #FFF8E8;
}

QMenu::item:disabled {
    color: #9C7A5E;
}

QMenu::separator {
    height: 1px;
    background-color: #D8B487;
    margin: 4px 7px;
}

QMenu::indicator {
    width: 11px;
    height: 11px;
}

QMenu::indicator:checked {
    background-color: #7B4D32;
    border: 1px solid #F5D39B;
    border-radius: 5px;
}

QMenu::right-arrow {
    image: none;
    width: 5px;
    height: 5px;
    border-right: 1px solid #7B4D32;
    border-bottom: 1px solid #7B4D32;
}
"""


def apply_lulu_menu_style(menu: QMenu) -> QMenu:
    menu.setStyleSheet(LULU_MENU_STYLE)
    return menu
