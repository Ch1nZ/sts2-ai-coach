"""Local test client. With no arguments, reads and saves game state.

--action is for disposable test sessions only; it is not the recommendation UI.
"""
import argparse
import json
from pathlib import Path
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument('--action', help='JSON action for the isolated test game')
parser.add_argument('--output', default='artifacts/latest-state.json')
args = parser.parse_args()
url = 'http://127.0.0.1:15526/api/v1/singleplayer'
payload = json.dumps(json.loads(args.action)).encode() if args.action else None
request = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open(request, timeout=15) as response:
    state = json.load(response)
output = Path(args.output)
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(state, indent=2))
print(json.dumps(state, indent=2))
