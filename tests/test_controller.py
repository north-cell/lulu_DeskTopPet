import time
import unittest

from lulu_pet.assets import AssetManager
from lulu_pet.controller import PetController


class PetControllerTests(unittest.TestCase):
    def test_starts_in_default_action(self):
        controller = PetController(AssetManager(None))

        self.assertEqual(controller.current_action.name, "idle")

    def test_click_temporarily_switches_to_clicked(self):
        controller = PetController(AssetManager(None))

        controller.handle_click(now=100.0)

        self.assertEqual(controller.current_action.name, "clicked")
        self.assertGreater(controller.action_until, 100.0)

    def test_drag_state_restores_idle_after_release(self):
        controller = PetController(AssetManager(None))

        controller.start_drag(now=200.0)
        self.assertEqual(controller.current_action.name, "dragged")

        controller.end_drag(now=201.0)
        self.assertEqual(controller.current_action.name, "idle")

    def test_tick_chooses_new_action_after_duration(self):
        controller = PetController(AssetManager(None))
        controller.set_action("sleep", now=300.0)

        controller.tick(now=300.1)
        self.assertEqual(controller.current_action.name, "sleep")

        controller.tick(now=9999.0)
        self.assertIn(controller.current_action.name, controller.assets.action_names)

    def test_recent_speech_is_throttled(self):
        controller = PetController(AssetManager(None), speech_interval_seconds=60)
        first = controller.next_line(now=10.0)
        second = controller.next_line(now=20.0)

        self.assertIsInstance(first, str)
        self.assertEqual(second, "")

    def test_contract_name_replaces_shouting_in_speech(self):
        controller = PetController(AssetManager(None), contract_name="露露")
        controller.assets.random_line = lambda action_name: "shouting辛苦啦，噜噜陪你。"

        line = controller.next_line(now=10.0)

        self.assertEqual(line, "露露辛苦啦，噜噜陪你。")
        self.assertNotIn("shouting", line)

    def test_contract_name_can_be_updated(self):
        controller = PetController(AssetManager(None), contract_name="shouting")
        controller.assets.random_line = lambda action_name: "最喜欢shouting了"

        controller.set_contract_name("小明")

        self.assertEqual(controller.next_line(now=10.0), "最喜欢小明了")


if __name__ == "__main__":
    unittest.main()
