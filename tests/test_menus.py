import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from lulu_pet.assets import AssetManager
from lulu_pet.contract_dialog import ContractDialog
from lulu_pet.controller import PetController
from lulu_pet.focus_records import FocusRecord, FocusRecordStore
from lulu_pet.models import PetSettings
from lulu_pet.motion import MotionMode
import lulu_pet.pet_window as pet_window_module
from lulu_pet.pet_window import PetWindow
from lulu_pet.tray import TrayController, _tray_icon


def default_settings() -> PetSettings:
    return PetSettings(
        window_size=(220, 180),
        always_on_top=True,
        speech_interval_seconds=45,
        edge_snap=True,
        autostart=False,
        motion_speed_percent=100,
    )


def action_texts(menu):
    return [action.text() for action in menu.actions() if not action.isSeparator()]


def submenu_by_text(menu, text):
    return next(action.menu() for action in menu.actions() if action.text() == text)


def action_by_text(menu, text):
    return next(action for action in menu.actions() if action.text() == text)


def assert_lulu_menu_style(test_case, menu):
    style = menu.styleSheet()
    test_case.assertIn("#FFF4DA", style)
    test_case.assertIn("#3B271C", style)
    test_case.assertIn("#C78652", style)
    test_case.assertIn("padding: 5px;", style)
    test_case.assertIn("font-size: 12px;", style)
    test_case.assertIn("padding: 5px 22px 5px 14px;", style)


class MenuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_pet_context_menu_hides_manual_random_and_settings_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = FocusRecordStore(Path(tmp) / "focus_records.json")
            window = PetWindow(PetController(AssetManager(None)), default_settings(), focus_record_store=store)
            try:
                menu = window.context_menu()
                texts = action_texts(menu)

                self.assertNotIn("随机运动", texts)
                self.assertNotIn("随机表情包", texts)
                self.assertNotIn("设置", texts)
                self.assertIn("专注模式", texts)
                self.assertIn("休息一下", texts)
                self.assertIn("签订契约", texts)
                self.assertIn("小游戏", texts)
                self.assertIn("暂停移动", texts)
                self.assertIn("保持置顶", texts)
                self.assertIn("退出", texts)
                focus_menu = submenu_by_text(menu, "专注模式")
                self.assertEqual(action_texts(focus_menu), ["开始专注", "学习记录"])
                self.assertIsNone(action_by_text(focus_menu, "学习记录").menu())
                games_menu = submenu_by_text(menu, "小游戏")
                self.assertEqual(action_texts(games_menu), ["打噜鼠", "贪吃噜", "2048噜", "Flappy Lulu"])
                self.assertIsNone(action_by_text(games_menu, "打噜鼠").menu())
                self.assertIsNone(action_by_text(games_menu, "贪吃噜").menu())
                self.assertIsNone(action_by_text(games_menu, "2048噜").menu())
                self.assertIsNone(action_by_text(games_menu, "Flappy Lulu").menu())
            finally:
                window.close()

    def test_pet_context_menu_learning_records_action_opens_dialog(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = FocusRecordStore(Path(tmp) / "focus_records.json")
            store.add(FocusRecord("2026-05-11", "08:00:00", "08:20:00", 20 * 60, "20分00秒"))
            store.add(FocusRecord("2026-05-12", "09:00:00", "09:30:00", 30 * 60, "30分00秒"))
            window = PetWindow(PetController(AssetManager(None)), default_settings(), focus_record_store=store)
            try:
                records_action = action_by_text(submenu_by_text(window.context_menu(), "专注模式"), "学习记录")

                records_action.trigger()

                self.assertIsNotNone(window._focus_records_dialog)
                self.assertTrue(window._focus_records_dialog.isVisible())
            finally:
                window.close()

    def test_pet_context_menu_in_focus_mode_only_keeps_end_focus_and_exit(self):
        window = PetWindow(PetController(AssetManager(None)), default_settings())
        try:
            window.trigger_focus_mode()

            texts = action_texts(window.context_menu())

            self.assertEqual(texts, ["结束专注模式", "学习记录", "退出"])
            self.assertNotIn("签订契约", texts)
            self.assertNotIn("小游戏", texts)
        finally:
            window.close()

    def test_pet_context_menu_can_pause_motion(self):
        window = PetWindow(PetController(AssetManager(None)), default_settings())
        try:
            action = next(action for action in window.context_menu().actions() if action.text() == "暂停移动")

            self.assertTrue(action.isCheckable())
            self.assertFalse(action.isChecked())

            action.trigger()

            self.assertTrue(window.motion_paused)
            self.assertTrue(next(action for action in window.context_menu().actions() if action.text() == "暂停移动").isChecked())
        finally:
            window.close()

    def test_pet_context_menu_can_switch_character_images(self):
        window = PetWindow(PetController(AssetManager(None)), default_settings())
        try:
            menu = window.context_menu()
            change_menu = submenu_by_text(menu, "更换形象")
            texts = action_texts(change_menu)

            self.assertEqual(
                texts,
                [
                    "游泳噜噜",
                    "睡衣噜噜",
                    "得瑟噜噜",
                    "小鸭噜噜",
                    "小象噜噜",
                    "野人噜噜",
                    "粉嘟嘟噜",
                    "霸王龙噜",
                ],
            )

            swim_action = next(action for action in change_menu.actions() if action.text() == "游泳噜噜")
            swim_action.trigger()

            self.assertEqual(window._character_assets["body"].name, "lulu_transparent_01.gif")

            pajama_action = next(action for action in change_menu.actions() if action.text() == "睡衣噜噜")
            pajama_action.trigger()

            self.assertEqual(window._character_assets["body"].name, "xhs_lulu_02.gif")

            proud_action = next(action for action in change_menu.actions() if action.text() == "得瑟噜噜")
            proud_action.trigger()

            self.assertEqual(window._character_assets["body"].name, "lulu_transparent_09.gif")

            custom_characters = {
                "小鸭噜噜": "640 - 2026-05-14T123937.674.gif",
                "小象噜噜": "640 (81).gif",
                "野人噜噜": "640 (21).gif",
                "粉嘟嘟噜": "640 (94).gif",
                "霸王龙噜": "640 (98).gif",
            }
            for label, filename in custom_characters.items():
                action = next(action for action in change_menu.actions() if action.text() == label)
                action.trigger()

                self.assertEqual(window._character_assets["body"].name, filename)
        finally:
            window.close()

    def test_pet_context_menu_and_submenu_use_lulu_style(self):
        window = PetWindow(PetController(AssetManager(None)), default_settings())
        try:
            menu = window.context_menu()
            focus_menu = submenu_by_text(menu, "专注模式")
            change_menu = submenu_by_text(menu, "更换形象")
            games_menu = submenu_by_text(menu, "小游戏")

            assert_lulu_menu_style(self, menu)
            self.assertEqual(focus_menu.styleSheet(), menu.styleSheet())
            self.assertEqual(change_menu.styleSheet(), menu.styleSheet())
            self.assertEqual(games_menu.styleSheet(), menu.styleSheet())
        finally:
            window.close()

    def test_sign_contract_saves_name_and_updates_controller(self):
        class FakeSettingsStore:
            def __init__(self):
                self.saved = []

            def save(self, settings):
                self.saved.append(settings)

        class FakeBubble:
            def __init__(self):
                self.messages = []

            def show_message(self, message, anchor, duration_ms=None):
                self.messages.append(message)

            def hide(self):
                pass

            def close(self):
                pass

        original_get_contract_name = pet_window_module.ContractDialog.get_contract_name
        pet_window_module.ContractDialog.get_contract_name = staticmethod(lambda *args, **kwargs: ("  小露露  ", True))
        store = FakeSettingsStore()
        window = PetWindow(PetController(AssetManager(None)), default_settings(), settings_store=store)
        bubble = FakeBubble()
        window._bubble = bubble
        try:
            window.sign_contract()

            self.assertEqual(window.settings.contract_name, "小露露")
            self.assertEqual(window.controller.contract_name, "小露露")
            self.assertEqual(store.saved[-1].contract_name, "小露露")
            self.assertEqual(bubble.messages, ["契约签订成功，噜噜以后会这样叫你。"])
        finally:
            pet_window_module.ContractDialog.get_contract_name = original_get_contract_name
            window.close()

    def test_contract_dialog_uses_lulu_visual_style(self):
        dialog = ContractDialog("shouting")
        try:
            style = dialog.styleSheet()

            self.assertEqual(dialog.windowTitle(), "签订契约")
            self.assertEqual(dialog.name_edit.maxLength(), 12)
            self.assertIn("#FFF4DA", style)
            self.assertIn("#7B4D32", style)
            self.assertIn("border-radius: 10px", style)
            self.assertIn("QPushButton#primaryButton", style)
            self.assertEqual(dialog.name_edit.text(), "shouting")
        finally:
            dialog.close()

    def test_paused_motion_does_not_move_on_tick(self):
        window = PetWindow(PetController(AssetManager(None)), default_settings())
        try:
            window.motion.start(MotionMode.WALK_RIGHT, duration_ticks=20)
            window.set_motion_paused(True)
            position = window.pos()

            window._on_tick()

            self.assertEqual(window.pos(), position)
        finally:
            window.close()

    def test_tray_menu_hides_manual_random_and_settings_actions(self):
        window = PetWindow(PetController(AssetManager(None)), default_settings())
        tray = TrayController(window)
        try:
            menu = tray.tray.contextMenu()
            texts = action_texts(menu)

            self.assertNotIn("随机运动", texts)
            self.assertNotIn("随机表情包", texts)
            self.assertNotIn("设置", texts)
            self.assertIn("显示/隐藏", texts)
            self.assertIn("专注模式", texts)
            self.assertIn("休息一下", texts)
            self.assertIn("签订契约", texts)
            self.assertIn("小游戏", texts)
            self.assertIn("暂停移动", texts)
            self.assertIn("保持置顶", texts)
            self.assertIn("退出", texts)
            focus_menu = submenu_by_text(menu, "专注模式")
            self.assertEqual(action_texts(focus_menu), ["开始专注", "学习记录"])
            self.assertIsNone(action_by_text(focus_menu, "学习记录").menu())
            games_menu = submenu_by_text(menu, "小游戏")
            self.assertEqual(action_texts(games_menu), ["打噜鼠", "贪吃噜", "2048噜", "Flappy Lulu"])
            self.assertIsNone(action_by_text(games_menu, "打噜鼠").menu())
            self.assertIsNone(action_by_text(games_menu, "贪吃噜").menu())
            self.assertIsNone(action_by_text(games_menu, "2048噜").menu())
            self.assertIsNone(action_by_text(games_menu, "Flappy Lulu").menu())
        finally:
            tray.hide()
            window.close()

    def test_tray_menu_can_toggle_autostart_and_save_settings(self):
        class FakeAutostartManager:
            def __init__(self):
                self.enabled = False
                self.calls = []

            def is_enabled(self):
                return self.enabled

            def set_enabled(self, enabled):
                self.enabled = enabled
                self.calls.append(enabled)

        class FakeSettingsStore:
            def __init__(self):
                self.saved = []

            def save(self, settings):
                self.saved.append(settings)

        window = PetWindow(PetController(AssetManager(None)), default_settings())
        window.settings_store = FakeSettingsStore()
        autostart = FakeAutostartManager()
        tray = TrayController(window, autostart_manager=autostart)
        try:
            action = action_by_text(tray.tray.contextMenu(), "开机自启动")

            self.assertTrue(action.isCheckable())
            self.assertFalse(action.isChecked())

            action.trigger()

            self.assertEqual(autostart.calls, [True])
            self.assertTrue(window.settings.autostart)
            self.assertTrue(window.settings_store.saved[-1].autostart)

            action = action_by_text(tray.tray.contextMenu(), "开机自启动")
            action.trigger()

            self.assertEqual(autostart.calls, [True, False])
            self.assertFalse(window.settings.autostart)
            self.assertFalse(window.settings_store.saved[-1].autostart)
        finally:
            tray.hide()
            window.close()

    def test_tray_rewrites_autostart_command_when_setting_is_enabled(self):
        class FakeAutostartManager:
            is_available = True

            def __init__(self):
                self.enabled = True
                self.enable_calls = 0

            def enable(self):
                self.enable_calls += 1

            def is_enabled(self):
                return self.enabled

            def set_enabled(self, enabled):
                self.enabled = enabled

        settings = PetSettings(
            window_size=(220, 180),
            always_on_top=True,
            speech_interval_seconds=45,
            edge_snap=True,
            autostart=True,
            motion_speed_percent=100,
        )
        window = PetWindow(PetController(AssetManager(None)), settings)
        autostart = FakeAutostartManager()
        tray = TrayController(window, autostart_manager=autostart)
        try:
            self.assertEqual(autostart.enable_calls, 1)
        finally:
            tray.hide()
            window.close()

    def test_tray_menu_switches_to_end_focus_action_in_focus_mode(self):
        window = PetWindow(PetController(AssetManager(None)), default_settings())
        tray = TrayController(window)
        try:
            window.trigger_focus_mode()
            tray.refresh_menu()

            texts = action_texts(tray.tray.contextMenu())

            self.assertIn("显示/隐藏", texts)
            self.assertIn("结束专注模式", texts)
            self.assertIn("学习记录", texts)
            self.assertIn("开机自启动", texts)
            self.assertIn("退出", texts)
            self.assertNotIn("专注模式", texts)
            self.assertNotIn("休息一下", texts)
            self.assertNotIn("签订契约", texts)
            self.assertNotIn("小游戏", texts)
            self.assertNotIn("暂停移动", texts)
            self.assertNotIn("保持置顶", texts)
        finally:
            tray.hide()
            window.close()

    def test_tray_menu_can_pause_motion(self):
        window = PetWindow(PetController(AssetManager(None)), default_settings())
        tray = TrayController(window)
        try:
            action = next(action for action in tray.tray.contextMenu().actions() if action.text() == "暂停移动")

            self.assertTrue(action.isCheckable())
            self.assertFalse(action.isChecked())

            action.trigger()

            self.assertTrue(window.motion_paused)
        finally:
            tray.hide()
            window.close()

    def test_tray_menu_can_toggle_always_on_top_and_save_settings(self):
        class FakeSettingsStore:
            def __init__(self):
                self.saved = []

            def save(self, settings):
                self.saved.append(settings)

        window = PetWindow(PetController(AssetManager(None)), default_settings())
        window.settings_store = FakeSettingsStore()
        tray = TrayController(window)
        try:
            action = action_by_text(tray.tray.contextMenu(), "保持置顶")

            self.assertTrue(action.isCheckable())
            self.assertTrue(action.isChecked())

            action.trigger()

            self.assertFalse(window.settings.always_on_top)
            self.assertFalse(window.settings_store.saved[-1].always_on_top)
            self.assertFalse(action_by_text(tray.tray.contextMenu(), "保持置顶").isChecked())

            action = action_by_text(tray.tray.contextMenu(), "保持置顶")
            action.trigger()

            self.assertTrue(window.settings.always_on_top)
            self.assertTrue(window.settings_store.saved[-1].always_on_top)
            self.assertTrue(action_by_text(tray.tray.contextMenu(), "保持置顶").isChecked())
        finally:
            tray.hide()
            window.close()

    def test_tray_menu_and_submenu_use_lulu_style(self):
        window = PetWindow(PetController(AssetManager(None)), default_settings())
        tray = TrayController(window)
        try:
            menu = tray.tray.contextMenu()
            focus_menu = submenu_by_text(menu, "专注模式")
            change_menu = submenu_by_text(menu, "更换形象")
            games_menu = submenu_by_text(menu, "小游戏")

            assert_lulu_menu_style(self, menu)
            self.assertEqual(focus_menu.styleSheet(), menu.styleSheet())
            self.assertEqual(change_menu.styleSheet(), menu.styleSheet())
            self.assertEqual(games_menu.styleSheet(), menu.styleSheet())
        finally:
            tray.hide()
            window.close()

    def test_tray_icon_is_cute_little_orange(self):
        pixmap = _tray_icon().pixmap(64, 64)
        image = pixmap.toImage()

        center = image.pixelColor(32, 34)
        leaf = image.pixelColor(35, 13)

        self.assertGreater(center.red(), 220)
        self.assertGreater(center.green(), 120)
        self.assertLess(center.blue(), 80)
        self.assertGreater(leaf.green(), leaf.red())
        self.assertGreater(leaf.green(), leaf.blue())


if __name__ == "__main__":
    unittest.main()
