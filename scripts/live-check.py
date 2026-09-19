"""One billed request on a saved, non-private game snapshot. Prints no secret values."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from spire.clients import config, evaluate
from spire.decisions import candidates, request_body, parse_choice

path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('artifacts/state-combat-before.json')
state = json.loads(path.read_text())
actions = candidates(state)
assert len(actions) > 1, 'Snapshot needs multiple choices'
_, model = config()
response = evaluate(request_body(state, actions, model))
choice = parse_choice(response, actions)
result = {'model': response.get('model', model), 'action': choice.label,
          'valid_choice': True, 'usage': response.get('usage')}
Path('artifacts/jev-live-check.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
