import json
import os
from pathlib import Path
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
ENDPOINT = 'https://openrouter.ai/api/alpha/decisions'


def config():
    values = {}
    path = ROOT / '.env.local'
    if path.exists():
        for line in path.read_text().splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                key, value = line.split('=', 1)
                values[key.strip()] = value.strip().strip('\"\'')
    return (os.environ.get('OPENROUTER_API_KEY') or values.get('OPENROUTER_API_KEY', ''),
            os.environ.get('OPENROUTER_MODEL') or values.get('OPENROUTER_MODEL', 'typesafe/jev-1.13'))


def game_state():
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open('http://127.0.0.1:15526/api/v1/singleplayer?format=json', timeout=3) as response:
        value = json.load(response)
    if not isinstance(value, dict) or value.get('error'):
        raise ValueError('Game state unavailable.')
    return value


def evaluate(body):
    key, _ = config()
    if not key:
        raise ValueError('Add your OpenRouter key to .env.local.')
    payload = json.dumps(body).encode()
    if len(payload) > 90000:
        raise ValueError('This game state is too large to evaluate.')
    request = urllib.request.Request(ENDPOINT, data=payload, headers={
        'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json',
        'X-Title': 'Showing Your Hand'})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        messages = {401: 'OpenRouter rejected the API key.', 402: 'OpenRouter credits are exhausted.',
                    403: 'OpenRouter access is restricted.', 429: 'OpenRouter is rate limiting requests.'}
        # Do not expose remote error bodies or request headers.
        raise ValueError(messages.get(error.code, f'OpenRouter request failed ({error.code}).')) from None
    except (urllib.error.URLError, TimeoutError):
        raise ValueError('Could not reach OpenRouter. Retry shortly.') from None
    if not isinstance(result, dict) or result.get('error'):
        raise ValueError('OpenRouter could not return a decision.')
    return result
