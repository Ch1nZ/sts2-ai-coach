from concurrent.futures import ThreadPoolExecutor
import threading
import time
from .clients import config, evaluate, game_state
from .decisions import candidates, fingerprint, parse_choice, request_body


class Engine:
    """One in-flight decision; invalidate immediately whenever observed state changes."""
    def __init__(self, reader=game_state, judge=evaluate):
        self.reader, self.judge = reader, judge
        self.lock = threading.RLock()
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.stop = threading.Event()
        self.last_view = 0.0
        self.paused = False
        self.generation = 0
        self.current_hash = None
        self.changed_at = 0.0
        self.attempted = None
        self.future = None
        self.last_request = 0.0
        self.calls = 0
        self.limit = 120
        self.action = None
        self.message = 'Waiting for the game'
        self.status = 'waiting'
        self.last_good = 0.0
        self.thread = threading.Thread(target=self.loop, daemon=True)

    def snapshot(self):
        with self.lock:
            self.last_view = time.monotonic()
            if self.last_good and self.last_view - self.last_good > 4:
                self.action = None
            return {'action': self.action, 'message': self.message, 'status': self.status,
                    'paused': self.paused, 'calls': self.calls, 'limit': self.limit}

    def control(self, command):
        with self.lock:
            if command == 'pause':
                self.paused = True
            elif command == 'resume':
                self.paused = False
            elif command != 'retry':
                raise ValueError('Unknown control')
            self.generation += 1
            self.attempted = None
            self.action = None
            self.message = 'Paused' if self.paused else 'Updating…'
            self.status = 'paused' if self.paused else 'waiting'

    def complete(self, future, generation, actions):
        try:
            chosen = parse_choice(future.result(), actions)
            label, message = chosen.label, ''
        except Exception as error:
            label = None
            message = str(error) if isinstance(error, ValueError) else 'Decision unavailable. Retry.'
        with self.lock:
            if generation == self.generation and not self.paused:
                self.action = label
                self.message = message
                self.status = 'ready' if label else 'error'

    def observe(self, state, now):
        """Called after each successful poll; exposed separately for race-condition tests."""
        digest = fingerprint(state)
        with self.lock:
            self.last_good = now
            if digest != self.current_hash:
                self.current_hash = digest
                self.generation += 1
                self.changed_at = now
                self.attempted = None
                self.action = None
                self.message = 'Updating…'
                self.status = 'waiting'
            if self.paused:
                return
            actions = candidates(state)
            if not actions:
                self.action = None
                self.message = 'Waiting for your turn' if state.get('battle') else 'Choose in the game'
                self.status = 'waiting'
                return
            if now - self.changed_at < 0.5:
                return
            if len(actions) == 1:
                self.action, self.message, self.status = actions[0].label, '', 'ready'
                return
            if self.attempted == digest or (self.future and not self.future.done()):
                return
            if now - self.last_request < 2:
                return
            if self.calls >= self.limit:
                self.action, self.message, self.status = None, 'Session request limit reached', 'error'
                return
            _, model = config()
            body = request_body(state, actions, model)
            self.calls += 1
            self.last_request = now
            self.attempted = digest
            self.status, self.message = 'thinking', 'Choosing…'
            generation = self.generation
            self.future = self.pool.submit(self.judge, body)
            self.future.add_done_callback(lambda f: self.complete(f, generation, actions))

    def loop(self):
        while not self.stop.wait(0.25):
            with self.lock:
                if self.paused or time.monotonic() - self.last_view > 5:
                    continue
            try:
                state = self.reader()
                self.observe(state, time.monotonic())
            except Exception:
                with self.lock:
                    self.generation += 1
                    self.current_hash = None
                    self.action = None
                    self.status, self.message = 'waiting', 'Waiting for the game'

    def close(self):
        self.stop.set()
        if self.thread.is_alive():
            self.thread.join(timeout=4)
        self.pool.shutdown(wait=False, cancel_futures=True)
