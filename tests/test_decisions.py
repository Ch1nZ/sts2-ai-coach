import unittest
from spire.decisions import candidates, parse_choice, request_body


def combat():
    return {'state_type': 'monster', 'battle': {'turn': 'player', 'is_play_phase': True,
            'enemies': [{'entity_id': 'E0', 'name': 'Enemy', 'hp': 10},
                        {'entity_id': 'E1', 'name': 'Enemy', 'hp': 0}]},
            'player': {'energy': 1, 'hand': [
                {'name': 'Strike', 'index': 0, 'can_play': True, 'target_type': 'AnyEnemy'},
                {'name': 'Bash', 'index': 1, 'can_play': False, 'target_type': 'AnyEnemy'},
                {'name': 'Defend', 'index': 2, 'can_play': True, 'target_type': 'Self'}]}}


class DecisionTests(unittest.TestCase):
    def test_excludes_unplayable_and_dead_targets(self):
        actions = candidates(combat())
        self.assertEqual(len(actions), 3)
        self.assertEqual(actions[0].details['target'], 'E0')
        self.assertNotIn('Bash', str(actions))

    def test_enemy_turn_has_no_recommendation(self):
        state = combat(); state['battle']['is_play_phase'] = False
        self.assertEqual(candidates(state), [])

    def test_unknown_targets_are_not_invented(self):
        state = combat(); state['player']['hand'][0]['target_type'] = 'NewMechanic'
        self.assertEqual(len(candidates(state)), 2)

    def test_reward_includes_skip(self):
        state = {'state_type': 'card_reward', 'card_reward': {
            'cards': [{'index': 0, 'name': 'Offering'}], 'can_skip': True}}
        self.assertEqual([a.label for a in candidates(state)], ['Take Offering (#1)', 'Skip'])

    def test_shop_affordability_and_potion_capacity(self):
        state = {'state_type': 'shop', 'player': {'potions': [{}], 'max_potion_slots': 1},
            'shop': {'items': [{'index': 0, 'category': 'potion', 'potion_name': 'Potion',
                'is_stocked': True, 'can_afford': True}, {'index': 1, 'card_name': 'Expensive',
                'is_stocked': True, 'can_afford': False}], 'can_proceed': True}}
        self.assertEqual([a.label for a in candidates(state)], ['Leave the shop'])

    def test_invalid_model_choice_rejected(self):
        with self.assertRaises(ValueError):
            parse_choice({'answers': {'next_action': {'type': 'choice', 'choice': 'invented'}}}, candidates(combat()))

    def test_protocol_and_private_fields(self):
        state = combat(); state['api_key'] = 'secret'; state['local_path'] = '/private'
        body = request_body(state, candidates(state), 'typesafe/jev-1.13')
        self.assertNotIn('secret', str(body)); self.assertNotIn('/private', str(body))
        self.assertNotIn('messages', body)
        self.assertEqual(body['questions']['next_action']['type'], 'choice')


if __name__ == '__main__':
    unittest.main()
