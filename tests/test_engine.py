from concurrent.futures import Future
import unittest
from spire.engine import Engine
from spire.decisions import candidates
from test_decisions import combat


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = Engine(judge=lambda body: {'answers': {'next_action': {'type': 'choice', 'choice': 'a0'}}})

    def tearDown(self):
        self.engine.close()

    def test_stale_result_is_discarded(self):
        e = self.engine
        before = combat(); e.observe(before, 10)
        old = e.generation
        after = combat(); after['player']['energy'] = 0
        e.observe(after, 10.1)
        f = Future(); f.set_result({'answers': {'next_action': {'type': 'choice', 'choice': 'a0'}}})
        e.complete(f, old, candidates(before))
        self.assertIsNone(e.action)

    def test_pause_invalidates_in_flight_decision(self):
        e = self.engine; e.observe(combat(), 10); old = e.generation
        e.control('pause')
        f = Future(); f.set_result({'answers': {'next_action': {'type': 'choice', 'choice': 'a0'}}})
        e.complete(f, old, candidates(combat()))
        self.assertIsNone(e.action)
        self.assertTrue(e.paused)

    def test_unchanged_state_is_not_billed_twice(self):
        e = self.engine; e.observe(combat(), 10); e.observe(combat(), 11)
        e.future.result(timeout=1)
        e.observe(combat(), 15)
        self.assertEqual(e.calls, 1)

    def test_request_limit(self):
        e = self.engine; e.calls = e.limit
        e.observe(combat(), 10); e.observe(combat(), 11)
        self.assertEqual(e.status, 'error')
        self.assertIsNone(e.future)


if __name__ == '__main__':
    unittest.main()
