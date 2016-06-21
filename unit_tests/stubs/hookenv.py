from charmhelpers.core.hookenv import (
    Config,
    CRITICAL,
    ERROR,
    WARNING,
    INFO,
    DEBUG,
)

LEVELS = (CRITICAL, ERROR, WARNING, INFO, DEBUG)


class HookenvStub(object):
    """Testable stub for charmhelpers.core.hookenv."""

    def __init__(self, charm_dir):
        self.messages = []
        self.port = None
        self._config = Config()
        self._charm_dir = charm_dir

    def config(self):
        return self._config

    def log(self, message, level=None):
        if level is not None:
            assert level in LEVELS
        self.messages.append((message, level))
