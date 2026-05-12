from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHeaderView,
    QLabel,
    QMenu,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from .focus_records import FocusRecord, FocusRecordStore
from .menu_style import apply_lulu_menu_style


class FocusRecordsDialog(QDialog):
    def __init__(self, records: list[FocusRecord], parent=None, record_store: FocusRecordStore | None = None):
        super().__init__(parent)
        self.record_store = record_store
        self._records: list[FocusRecord] = []
        self.setWindowTitle("学习记录")
        self.setModal(False)
        self.resize(560, 360)

        self.title_label = QLabel("学习记录", self)
        self.title_label.setObjectName("recordsTitle")

        self.empty_label = QLabel("还没有超过 1 分钟的学习记录", self)
        self.empty_label.setObjectName("emptyState")
        self.empty_label.setAlignment(Qt.AlignCenter)

        self.table = QTableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["日期", "开始时间", "结束时间", "学习时长"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setShowGrid(False)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_record_context_menu)

        close_button = QPushButton("关闭", self)
        close_button.clicked.connect(self.close)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)
        layout.addWidget(self.title_label)
        layout.addWidget(self.empty_label)
        layout.addWidget(self.table)
        layout.addWidget(close_button, alignment=Qt.AlignRight)

        self._populate(records)
        self.setStyleSheet(RECORDS_DIALOG_STYLE)

    def _populate(self, records: list[FocusRecord]) -> None:
        ordered_records = list(reversed(records))
        self._records = ordered_records
        self.table.setRowCount(len(ordered_records))
        self.empty_label.setVisible(not ordered_records)
        self.table.setVisible(bool(ordered_records))
        for row, record in enumerate(ordered_records):
            values = [record.date, record.start_time, record.end_time, record.duration_text]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, column, item)

    def delete_record_at_row(self, row: int) -> None:
        if row < 0 or row >= len(self._records):
            return
        record = self._records[row]
        if self.record_store:
            self.record_store.remove(record)
            self._populate(self.record_store.load())
            return
        self._records.pop(row)
        self._populate(list(reversed(self._records)))

    def _show_record_context_menu(self, position: QPoint) -> None:
        item = self.table.itemAt(position)
        if not item:
            return
        self.table.selectRow(item.row())
        menu = apply_lulu_menu_style(QMenu(self))
        delete_action = menu.addAction("删除记录")
        selected_action = menu.exec(self.table.viewport().mapToGlobal(position))
        if selected_action == delete_action:
            self.delete_record_at_row(item.row())


RECORDS_DIALOG_STYLE = """
QDialog {
    background-color: #FFF4DA;
    color: #3B271C;
}

QLabel#recordsTitle {
    color: #3B271C;
    font-size: 20px;
    font-weight: 700;
}

QLabel#emptyState {
    background-color: #FFF8E8;
    border: 1px dashed #D8B487;
    border-radius: 8px;
    color: #8F6346;
    font-size: 14px;
    min-height: 160px;
}

QTableWidget {
    background-color: #FFF8E8;
    alternate-background-color: #F9E8C7;
    border: 1px solid #D8B487;
    border-radius: 8px;
    color: #3B271C;
    font-size: 12px;
    selection-background-color: #C78652;
    selection-color: #FFF8E8;
}

QHeaderView::section {
    background-color: #E8C38F;
    border: none;
    border-bottom: 1px solid #B78358;
    color: #3B271C;
    font-size: 12px;
    font-weight: 700;
    padding: 7px;
}

QTableWidget::item {
    border: none;
    padding: 6px;
}

QTableWidget::item:selected {
    background-color: #C78652;
    color: #FFF8E8;
}

QPushButton {
    background-color: #7B4D32;
    border: none;
    border-radius: 7px;
    color: #FFF8E8;
    min-width: 76px;
    padding: 7px 14px;
}

QPushButton:hover {
    background-color: #9B6743;
}
"""
