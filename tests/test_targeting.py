import unittest

from targeting import Detection, select_detection, target_signals


class TargetingTests(unittest.TestCase):
    def test_click_selects_containing_detection(self) -> None:
        people = [
            Detection(4, 0.9, 10, 10, 100, 200),
            Detection(9, 0.8, 200, 20, 300, 220),
        ]
        self.assertEqual(select_detection(people, 250, 100).track_id, 9)

    def test_overlapping_boxes_prefer_smallest(self) -> None:
        people = [
            Detection(1, 0.9, 0, 0, 500, 500),
            Detection(2, 0.8, 100, 100, 200, 300),
        ]
        self.assertEqual(select_detection(people, 150, 150).track_id, 2)

    def test_click_outside_returns_none(self) -> None:
        people = [Detection(1, 0.9, 10, 10, 100, 100)]
        self.assertIsNone(select_detection(people, 500, 500))

    def test_target_signals_centered(self) -> None:
        person = Detection(1, 0.9, 400, 100, 600, 500)
        error_x, height_ratio = target_signals(person, 1000, 800)
        self.assertAlmostEqual(error_x, 0.0)
        self.assertAlmostEqual(height_ratio, 0.5)

    def test_target_signals_left(self) -> None:
        person = Detection(1, 0.9, 0, 0, 200, 400)
        error_x, _ = target_signals(person, 1000, 800)
        self.assertAlmostEqual(error_x, -0.8)


if __name__ == "__main__":
    unittest.main()

