"""
Stub pyzmq module for offline nbconvert usage.

nbconvert's MarkdownExporter imports pyzmq through the chain:
    nbconvert -> nbclient -> jupyter_client -> pyzmq

For static notebook-to-markdown conversion (no kernel execution),
pyzmq is never actually used at runtime. This stub provides the
minimal module surface so the import chain succeeds without bundling
platform-specific C-extension wheels.

Usage (from doc_to_md.py bootstrap):

    import pyzmq_stub
    pyzmq_stub.install(sys.modules)
"""

import sys
import types
import json as _json

__version__ = "25.0.0"


# ── Socket type constants ──────────────────────────────────────────

REQ = 3
REP = 4
DEALER = 5
ROUTER = 6
PUB = 8
SUB = 9
XREQ = DEALER
XREP = ROUTER
XPUB = 19
XSUB = 20
PUSH = 5
PULL = 7
PAIR = 1
STREAM = 11

# Poll event flags
POLLIN = 1
POLLOUT = 2
POLLERR = 4
DONTWAIT = 1
NOBLOCK = 1

# Socket options
SNDMORE = 2
RCVMORE = 1
AFFINITY = 4
SUBSCRIBE = 5
UNSUBSCRIBE = 6
IDENTITY = 5
HWM = 1
LWM = 2
MAXMSGSIZE = 8
LINGER = 17
RECONNECT_IVL = 18
BACKLOG = 19
FD = 14
EVENTS = 15
TYPE = 16
RCVTIMEO = 27
SNDTIMEO = 28
LAST_ENDPOINT = 32
ROUTER_MANDATORY = 33
IPV6 = 42
PLAIN_SERVER = 44
PLAIN_PASSWORD = 46
PLAIN_USERNAME = 45
CURVE_SERVER = 47
CURVE_PUBLICKEY = 48
CURVE_SECRETKEY = 49
CURVE_SERVERKEY = 50
ZAP_DOMAIN = 55
HANDSHAKE_IVL = 66
CONNECT_RID = 56
CONFLATE = 54
CORRELATE = 53
IMMEDIATE = 39
PROBE_ROUTER = 51
TOS = 57
IPC_FILTER_PID = 58
IPC_FILTER_UID = 59
IPC_FILTER_GID = 60
ENABLE_IPV6 = IPV6
GATHER = 16
SCATTER = 17
CHANNEL = 18
CANARY = 21

# Context options
IO_THREADS = 1
MAX_SOCKETS = 2
SOCKET_TYPE = 3

# Messages
MORE = 1


# ── Dummy classes ──────────────────────────────────────────────────

class _Socket:
    """No-op socket. All methods are silent no-ops."""

    def __init__(self, *args, **kwargs):
        self.closed = False

    def close(self, *args, **kwargs):
        self.closed = True

    def bind(self, *args, **kwargs):
        pass

    def bind_to_random_port(self, *args, **kwargs):
        return 0

    def connect(self, *args, **kwargs):
        pass

    def disconnect(self, *args, **kwargs):
        pass

    def send(self, *args, **kwargs):
        pass

    def send_multipart(self, *args, **kwargs):
        pass

    def send_string(self, *args, **kwargs):
        pass

    def send_json(self, *args, **kwargs):
        pass

    def send_pyobj(self, *args, **kwargs):
        pass

    def recv(self, *args, **kwargs):
        return b""

    def recv_multipart(self, *args, **kwargs):
        return [b""]

    def recv_string(self, *args, **kwargs):
        return ""

    def recv_json(self, *args, **kwargs):
        return {}

    def recv_pyobj(self, *args, **kwargs):
        return None

    def setsockopt(self, *args, **kwargs):
        pass

    def set_string(self, *args, **kwargs):
        pass

    def getsockopt(self, *args, **kwargs):
        return 0

    def get_string(self, *args, **kwargs):
        return ""

    def subscribe(self, *args, **kwargs):
        pass

    def unsubscribe(self, *args, **kwargs):
        pass

    def poll(self, *args, **kwargs):
        return 0

    def copy(self):
        return self

    def fileno(self):
        return -1

    def monitor(self, *args, **kwargs):
        pass

    def has_more(self):
        return False


class _Context:
    """No-op context."""

    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, *args, **kwargs):
        self.closed = False

    def term(self):
        self.closed = True

    def destroy(self, *args, **kwargs):
        self.closed = True

    def socket(self, *args, **kwargs):
        return _Socket()

    def setsockopt(self, *args, **kwargs):
        pass

    def getsockopt(self, *args, **kwargs):
        return 0

    def shadow(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.term()


class _Poller:
    """No-op poller."""

    def register(self, *args, **kwargs):
        pass

    def unregister(self, *args, **kwargs):
        pass

    def modify(self, *args, **kwargs):
        pass

    def poll(self, *args, **kwargs):
        return []


# ── Exceptions ─────────────────────────────────────────────────────

class ZMQError(Exception):
    pass


class Again(ZMQError):
    pass


class NotDone(ZMQError):
    pass


class ContextTerminated(ZMQError):
    pass


# ── Message types ──────────────────────────────────────────────────

class Message:
    def __init__(self, data=b"", *args, **kwargs):
        self._data = data if isinstance(data, bytes) else str(data).encode()

    def __bytes__(self):
        return self._data

    def __len__(self):
        return len(self._data)

    def __eq__(self, other):
        if isinstance(other, Message):
            return self._data == other._data
        return self._data == other

    def copy(self):
        return Message(self._data)

    @property
    def buffer(self):
        return self._data


Frame = Message


class MessageTracker:
    """No-op message tracker."""

    def __init__(self, *args):
        pass

    def track(self, msg):
        pass

    def wait(self, *args, **kwargs):
        return True

    def done(self):
        return True


# ── Utility functions ──────────────────────────────────────────────

def device(*args, **kwargs):
    pass


def proxy(*args, **kwargs):
    pass


def zmq_version():
    return __version__


def has(*args):
    return False


def get_library():
    return None


# ── asyncio submodule ──────────────────────────────────────────────

class _AsyncSocket(_Socket):
    pass


class _AsyncContext(_Context):
    def socket(self, *args, **kwargs):
        return _AsyncSocket()


# ── Module construction ────────────────────────────────────────────

def _make_zmq_module():
    """Build the fake zmq module object."""
    mod = types.ModuleType("zmq")
    mod.__path__ = []
    mod.__version__ = __version__

    for name, obj in list(globals().items()):
        if not name.startswith("_") and name not in ("types", "sys", "json", "_json"):
            setattr(mod, name, obj)

    mod.Context = _Context
    mod.Socket = _Socket
    mod.Poller = _Poller
    mod.ZMQError = ZMQError
    mod.Again = Again
    mod.NotDone = NotDone
    mod.ContextTerminated = ContextTerminated
    mod.Message = Message
    mod.Frame = Frame
    mod.MessageTracker = MessageTracker

    asyncio_mod = types.ModuleType("zmq.asyncio")
    asyncio_mod.Context = _AsyncContext
    asyncio_mod.Socket = _AsyncSocket
    asyncio_mod.Poller = _Poller
    asyncio_mod.ZMQError = ZMQError
    asyncio_mod.Again = Again
    asyncio_mod.NotDone = NotDone
    mod.asyncio = asyncio_mod

    eventloop_mod = types.ModuleType("zmq.eventloop")
    eventloop_mod.__path__ = []
    eventloop_mod.Context = _Context
    eventloop_mod.Socket = _Socket
    eventloop_mod.Poller = _Poller
    eventloop_mod.ZMQError = ZMQError
    eventloop_mod.Again = Again
    eventloop_mod.NotDone = NotDone
    eventloop_mod.IOLoop = type("IOLoop", (), {
        "instance": classmethod(lambda cls: cls()),
        "current": classmethod(lambda cls: cls()),
        "run_sync": lambda *a, **k: None,
    })
    mod.eventloop = eventloop_mod

    zmqstream_mod = types.ModuleType("zmq.eventloop.zmqstream")
    zmqstream_mod.ZMQStream = type("ZMQStream", (), {
        "__init__": lambda self, *a, **k: None,
        "on_recv": lambda *a, **k: None,
        "on_send": lambda *a, **k: None,
        "send_multipart": lambda *a, **k: None,
        "recv_multipart": lambda *a, **k: [b""],
        "flush": lambda *a, **k: None,
        "close": lambda *a, **k: None,
    })
    eventloop_mod.zmqstream = zmqstream_mod

    sugar_mod = types.ModuleType("zmq.sugar")
    sugar_mod.__path__ = []
    sugar_mod.Context = _Context
    sugar_mod.Socket = _Socket
    sugar_mod.Poller = _Poller
    sugar_mod.ZMQError = ZMQError
    sugar_mod.Again = Again
    sugar_mod.NotDone = NotDone
    sugar_mod.MessageTracker = MessageTracker
    sugar_mod.Frame = Frame
    sugar_mod.Message = Message
    for _n in ('IDENTITY','SUBSCRIBE','UNSUBSCRIBE','SNDMORE','RCVMORE',
               'DONTWAIT','NOBLOCK','POLLIN','POLLOUT','POLLERR',
               'REQ','REP','DEALER','ROUTER','PUB','SUB','PUSH','PULL','PAIR'):
        setattr(sugar_mod, _n, globals()[_n])

    sugar_socket_mod = types.ModuleType("zmq.sugar.socket")
    sugar_socket_mod.Socket = _Socket
    sugar_mod.socket = sugar_socket_mod

    sugar_stopwatch_mod = types.ModuleType("zmq.sugar.stopwatch")
    sugar_stopwatch_mod.Stopwatch = type("Stopwatch", (), {
        "__init__": lambda self: None,
        "start": lambda self: 0,
        "stop": lambda self: 0,
    })
    sugar_mod.stopwatch = sugar_stopwatch_mod
    mod.sugar = sugar_mod

    backend_mod = types.ModuleType("zmq.backend")
    backend_mod.__path__ = []
    cython_mod = types.ModuleType("zmq.backend.cython")
    for name, obj in list(globals().items()):
        if not name.startswith("_") and name not in ("types", "sys", "json", "_json"):
            setattr(cython_mod, name, obj)
    backend_mod.cython = cython_mod
    mod.backend = backend_mod

    utils_mod = types.ModuleType("zmq.utils")
    utils_mod.__path__ = []
    jsonapi_mod = types.ModuleType("zmq.utils.jsonapi")
    jsonapi_mod.loads = _json.loads
    jsonapi_mod.dumps = _json.dumps
    utils_mod.jsonapi = jsonapi_mod
    mod.utils = utils_mod

    return mod, asyncio_mod, eventloop_mod, zmqstream_mod, sugar_mod, sugar_socket_mod, sugar_stopwatch_mod, backend_mod, cython_mod, utils_mod, jsonapi_mod


def install(modules=None):
    """Inject the stub into sys.modules so `import zmq` succeeds."""
    if modules is None:
        modules = sys.modules

    try:
        import zmq  # noqa: F401
        return False
    except ImportError:
        pass

    zmq_mod, asyncio_mod, eventloop_mod, zmqstream_mod, sugar_mod, sugar_socket_mod, sugar_stopwatch_mod, backend_mod, cython_mod, utils_mod, jsonapi_mod = (
        _make_zmq_module()
    )

    modules["zmq"] = zmq_mod
    modules["zmq.asyncio"] = asyncio_mod
    modules["zmq.eventloop"] = eventloop_mod
    modules["zmq.eventloop.zmqstream"] = zmqstream_mod
    modules["zmq.sugar"] = sugar_mod
    modules["zmq.sugar.socket"] = sugar_socket_mod
    modules["zmq.sugar.stopwatch"] = sugar_stopwatch_mod
    modules["zmq.backend"] = backend_mod
    modules["zmq.backend.cython"] = cython_mod
    modules["zmq.utils"] = utils_mod
    modules["zmq.utils.jsonapi"] = jsonapi_mod

    return True
