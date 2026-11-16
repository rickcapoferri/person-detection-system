import unittest

from targeting import Detection, TargetState


class TargetStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.person = Detection(4, 0.9, 10, 10, 100, 200)
        self.other = Detection(9, 0.8, 200, 20, 300, 220)
        self.state = TargetState(lost_timeout=2.0)
        self.state.lock(4, now=10.0)

    def test_brief_loss_preserves_lock_and_allows_return(self) -> None:
        self.assertIsNone(self.state.update([self.other], now=10.5))
        self.assertEqual(self.state.target_id, 4)
        self.assertEqual(self.state.missing_frames, 1)
        self.assertIs(self.state.update([self.person], now=11.5), self.person)
        self.assertEqual(self.state.missing_frames, 0)
        self.assertIsNone(self.state.update([], now=12.5))
        self.assertEqual(self.state.target_id, 4)

    def test_lock_expires_at_deadline(self) -> None:
        self.state.update([], now=11.0)
        self.assertIsNone(self.state.update([], now=12.0))
        self.assertIsNone(self.state.target_id)
        self.assertIsNone(self.state.last_seen)
        self.assertEqual(self.state.missing_frames, 0)

    def test_return_at_or_after_deadline_requires_click(self) -> None:
        for returned_at in (12.0, 15.0):
            with self.subTest(returned_at=returned_at):
                self.state.lock(4, now=10.0)
                self.state.update([], now=11.0)
                self.assertIsNone(self.state.update([self.person], now=returned_at))
                self.assertIsNone(self.state.target_id)

    def test_expired_lock_stays_unselected_until_explicit_lock(self) -> None:
        self.state.update([], now=12.0)
        self.assertIsNone(self.state.update([self.person, self.other], now=13.0))
        self.state.lock(4, now=13.0)
        self.assertIs(self.state.update([self.person], now=13.0), self.person)

    def test_replacement_resets_timeout(self) -> None:
        self.state.update([], now=11.0)
        self.state.lock(9, now=11.5)
        self.assertIs(self.state.update([self.other], now=12.5), self.other)
        self.assertEqual(self.state.target_id, 9)

    def test_manual_reset_clears_loss_and_pending_click(self) -> None:
        self.state.update([], now=11.0)
        self.state.pending_click = (50, 50)
        self.state.clear()
        self.assertIsNone(self.state.target_id)
        self.assertIsNone(self.state.last_seen)
        self.assertIsNone(self.state.pending_click)
        self.assertEqual(self.state.missing_frames, 0)
        self.assertIsNone(self.state.update([self.person], now=11.5))

    def test_custom_timeout_is_independent_of_frame_count(self) -> None:
        for updates in ([11.0], [10.1, 10.2, 10.3, 11.0]):
            with self.subTest(updates=updates):
                state = TargetState(lost_timeout=0.75)
                state.lock(4, now=10.0)
                for now in updates:
                    state.update([], now=now)
                self.assertIsNone(state.target_id)

    def test_invalid_timeout_is_rejected(self) -> None:
        for timeout in (0, -1, float("inf"), float("-inf"), float("nan")):
            with self.subTest(timeout=timeout):
                with self.assertRaises(ValueError):
                    TargetState(lost_timeout=timeout)


if __name__ == "__main__":
    unittest.main()
