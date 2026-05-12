import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QApplication

from lulu_pet.focus_records import FocusRecord, FocusRecordStore
from lulu_pet.focus_records_dialog import FocusRecordsDialog
from pathlib import Path
import tempfile


class FocusRecordsDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_dialog_shows_learning_records_newest_first_in_table(self):
        records = [
            FocusRecord("2026-05-11", "08:00:00", "08:20:00", 20 * 60, "20分00秒"),
            FocusRecord("2026-05-12", "09:00:00", "09:30:00", 30 * 60, "30分00秒"),
        ]
        dialog = FocusRecordsDialog(records)
        try:
            self.assertEqual(dialog.windowTitle(), "学习记录")
            self.assertEqual(dialog.table.rowCount(), 2)
            self.assertEqual(dialog.table.columnCount(), 4)
            self.assertEqual(dialog.table.horizontalHeaderItem(0).text(), "日期")
            self.assertEqual(dialog.table.horizontalHeaderItem(1).text(), "开始时间")
            self.assertEqual(dialog.table.horizontalHeaderItem(2).text(), "结束时间")
            self.assertEqual(dialog.table.horizontalHeaderItem(3).text(), "学习时长")
            self.assertEqual(dialog.table.item(0, 0).text(), "2026-05-12")
            self.assertEqual(dialog.table.item(0, 1).text(), "09:00:00")
            self.assertEqual(dialog.table.item(0, 2).text(), "09:30:00")
            self.assertEqual(dialog.table.item(0, 3).text(), "30分00秒")
            self.assertEqual(dialog.table.item(1, 0).text(), "2026-05-11")
        finally:
            dialog.close()

    def test_dialog_omits_subtitle_and_keeps_selected_row_readable(self):
        dialog = FocusRecordsDialog([
            FocusRecord("2026-05-12", "09:00:00", "09:30:00", 30 * 60, "30分00秒"),
        ])
        try:
            self.assertEqual(dialog.title_label.text(), "学习记录")
            self.assertEqual(dialog.findChildren(type(dialog.title_label), "recordsSubtitle"), [])
            self.assertEqual(dialog.table.selectionMode(), QAbstractItemView.SingleSelection)
            self.assertEqual(dialog.table.focusPolicy(), Qt.NoFocus)
            self.assertIn("QTableWidget::item:selected", dialog.styleSheet())
            self.assertIn("color: #FFF8E8", dialog.styleSheet())
        finally:
            dialog.close()

    def test_dialog_can_delete_selected_record_from_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = FocusRecordStore(Path(tmp) / "focus_records.json")
            older = FocusRecord("2026-05-11", "08:00:00", "08:20:00", 20 * 60, "20分00秒")
            newer = FocusRecord("2026-05-12", "09:00:00", "09:30:00", 30 * 60, "30分00秒")
            store.add(older)
            store.add(newer)
            dialog = FocusRecordsDialog(store.load(), record_store=store)
            try:
                dialog.delete_record_at_row(0)

                self.assertEqual(store.load(), [older])
                self.assertEqual(dialog.table.rowCount(), 1)
                self.assertEqual(dialog.table.item(0, 0).text(), "2026-05-11")
            finally:
                dialog.close()

    def test_dialog_shows_empty_state_when_no_records(self):
        dialog = FocusRecordsDialog([])
        try:
            dialog.show()
            self.assertEqual(dialog.table.rowCount(), 0)
            self.assertTrue(dialog.empty_label.isVisible())
            self.assertEqual(dialog.empty_label.text(), "还没有超过 1 分钟的学习记录")
        finally:
            dialog.close()


if __name__ == "__main__":
    unittest.main()
