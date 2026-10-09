"""Real scene-provider calls must be collected on the host main thread."""

from __future__ import annotations

import sys
import threading
import types

import pytest

from dcc_mcp_maya import _resources as resources_mod
from dcc_mcp_maya.context_snapshot import MayaContextSnapshotProvider, collect_gateway_metadata


def _in_worker(callback):
    errors = []

    def invoke():
        try:
            callback()
        except BaseException as exc:
            errors.append(exc)

    thread = threading.Thread(target=invoke, name="scene-resource-timer", daemon=True)
    thread.start()
    thread.join(timeout=2)
    assert not thread.is_alive(), "resource refresh blocked its worker"
    assert not errors, repr(errors)


class _RecordingCmds:
    def __init__(self):
        self.calls = []
        self.on_query = None

    def __getattr__(self, name):
        def query(**kwargs):
            self.calls.append((name, threading.current_thread()))
            callback, self.on_query = self.on_query, None
            if callback:
                callback()
            if name == "file":
                return "C:/scenes/thread-contract.ma" if kwargs.get("sceneName") else False
            return {
                "ls": ["pSphere1"],
                "currentTime": 1001,
                "playbackOptions": 1001 if kwargs.get("min") else 1100,
                "upAxis": "y",
                "currentUnit": "cm",
                "about": "2023",
            }.get(name)

        return query


class _ManualTimer:
    def __init__(self, delay, callback, args=None, kwargs=None):
        self.delay, self.callback = delay, callback
        self.args, self.kwargs = args or (), kwargs or {}
        self.started = self.cancelled = self.daemon = False

    def start(self):
        self.started = True

    def cancel(self):
        self.cancelled = True

    def fire(self):
        # A callback already delivered by the OS may still arrive after cancel.
        _in_worker(lambda: self.callback(*self.args, **self.kwargs))


class _Runtime:
    def __init__(self, monkeypatch):
        self.cmds = _RecordingCmds()
        self.provider = MayaContextSnapshotProvider(cmds_provider=lambda: self.cmds)
        self.scenes, self.metadata, self.metadata_threads = [], [], []
        self.queue, self.timers, self.events, self.binders = [], [], [], []
        self.now, self.busy, self.refuse = 100.0, False, False
        self.event_ids = []
        handle = types.SimpleNamespace(register_producer=lambda *args: None, set_scene=self.scenes.append)
        self.server = types.SimpleNamespace(
            _server=types.SimpleNamespace(resources=lambda: handle),
            publish_capability_snapshot=self.publish_metadata,
        )
        maya, utils = types.ModuleType("maya"), types.ModuleType("maya.utils")
        utils.executeDeferred = self.defer
        maya.utils = utils
        monkeypatch.setitem(sys.modules, "maya", maya)
        monkeypatch.setitem(sys.modules, "maya.utils", utils)
        monkeypatch.setattr(resources_mod, "time", types.SimpleNamespace(monotonic=lambda: self.now))
        monkeypatch.setattr(resources_mod.threading, "Timer", self.make_timer)

    def defer(self, callback):
        if self.refuse:
            raise RuntimeError("host queue unavailable")
        self.queue.append(callback)

    def drain(self, fifo=False):
        assert threading.current_thread() is threading.main_thread()
        count = 0
        while self.queue:
            count += 1
            assert count < 20, "refresh keeps requeueing"
            self.queue.pop(0 if fifo else -1)()

    def publish_metadata(self, reason):
        assert reason == "scene_resource"
        self.metadata.append(collect_gateway_metadata(self.provider))
        self.metadata_threads.append(threading.current_thread())

    def make_timer(self, delay, callback, args=None, kwargs=None):
        timer = _ManualTimer(delay, callback, args=args, kwargs=kwargs)
        self.timers.append(timer)
        return timer

    def install_events(self, callback, events):
        self.events.append(callback)
        return list(self.event_ids)

    def make_binder(self, bind=True):
        binder = resources_mod.MayaResourceBinder(
            snapshot_provider=self.provider,
            event_installer=self.install_events,
            busy_checker=lambda: self.busy,
            throttle_secs=0.5,
        )
        self.binders.append(binder)
        if bind:
            assert binder.bind(self.server)
            binder.install_scene_events()
        return binder

    def clear_queries(self):
        self.cmds.calls.clear()
        self.metadata.clear()
        self.metadata_threads.clear()

    def assert_main_queries(self, check_metadata=True):
        assert self.cmds.calls, "production provider never queried the scene"
        assert {thread for _, thread in self.cmds.calls} == {threading.main_thread()}
        if check_metadata:
            assert self.metadata_threads
            assert set(self.metadata_threads) == {threading.main_thread()}
            assert self.metadata[-1]["scene"] == "C:/scenes/thread-contract.ma"


@pytest.fixture
def runtime(monkeypatch):
    runtime = _Runtime(monkeypatch)
    yield runtime
    for binder in runtime.binders:
        binder.unbind()
    runtime.drain()


def test_timer_only_enqueues_scene_and_gateway_queries(runtime):
    binder = runtime.make_binder()
    baseline = binder.scene_publish_count
    runtime.clear_queries()
    for _ in range(100):
        runtime.events[-1]()
    assert len(runtime.timers) == 1
    assert runtime.timers[0].started
    runtime.now += 0.5
    runtime.timers[0].fire()
    assert runtime.cmds.calls == [], "Timer entered the Maya command engine"
    assert binder.scene_publish_count == baseline
    assert len(runtime.queue) == 1
    for _ in range(100):
        runtime.events[-1]()
    assert len(runtime.queue) == 1
    runtime.drain()
    assert binder.scene_publish_count == baseline + 1
    assert runtime.scenes[-1]["selection"] == ["pSphere1"]
    runtime.assert_main_queries()


@pytest.mark.parametrize("entrypoint", ["bind", "publish_scene"])
def test_worker_entrypoints_defer_provider_collection(runtime, entrypoint):
    binder = runtime.make_binder(bind=entrypoint != "bind")
    baseline = binder.scene_publish_count
    runtime.clear_queries()
    callback = (lambda: binder.bind(runtime.server)) if entrypoint == "bind" else binder.publish_scene
    _in_worker(callback)
    assert runtime.cmds.calls == []
    assert binder.scene_publish_count == baseline
    assert len(runtime.queue) == 1
    runtime.drain()
    assert binder.scene_publish_count == baseline + 1
    runtime.assert_main_queries(check_metadata=entrypoint == "bind")
    if entrypoint == "publish_scene":
        assert runtime.metadata == []


def test_explicit_payload_never_queries_provider_from_worker(runtime):
    binder = runtime.make_binder()
    runtime.clear_queries()
    _in_worker(lambda: binder.publish_scene({"scene": "provided-by-caller"}))
    assert runtime.cmds.calls == []
    assert runtime.metadata == []
    assert runtime.scenes[-1] == {"scene": "provided-by-caller"}


@pytest.mark.parametrize("unbind_before_timer", [True, False])
def test_unbind_fences_late_timer_and_deferred_collection(runtime, unbind_before_timer):
    binder = runtime.make_binder()
    runtime.events[-1]()
    timer = runtime.timers[-1]
    baseline = binder.scene_publish_count
    runtime.clear_queries()
    if unbind_before_timer:
        binder.unbind()
        assert timer.cancelled
        timer.fire()
    else:
        timer.fire()
        assert len(runtime.queue) == 1
        binder.unbind()
    runtime.drain()
    assert runtime.cmds.calls == []
    assert runtime.metadata == []
    assert binder.scene_publish_count == baseline


@pytest.mark.parametrize("fifo", [False, True])
def test_rebind_preserves_new_pending_refresh_when_old_work_arrives(runtime, fifo):
    binder = runtime.make_binder()
    old_event = runtime.events[-1]
    old_event()
    old_timer = runtime.timers[-1]
    old_timer.fire()
    binder.unbind()
    assert binder.bind(runtime.server)
    binder.install_scene_events()
    new_event = runtime.events[-1]
    assert new_event is not old_event
    baseline = binder.scene_publish_count
    runtime.clear_queries()
    new_event()
    new_timer = runtime.timers[-1]
    assert new_timer is not old_timer
    old_timer.fire()
    old_event()
    runtime.drain(fifo=fifo)
    assert runtime.cmds.calls == []
    assert binder.scene_publish_count == baseline
    runtime.now += 0.5
    new_timer.fire()
    runtime.drain(fifo=fifo)
    assert binder.scene_publish_count == baseline + 1
    runtime.assert_main_queries()


@pytest.mark.parametrize("busy_before_timer", [True, False])
def test_busy_refresh_drops_work_but_allows_next_event(runtime, busy_before_timer):
    binder = runtime.make_binder()
    baseline = binder.scene_publish_count
    runtime.events[-1]()
    runtime.clear_queries()
    runtime.busy = busy_before_timer
    runtime.timers[-1].fire()
    runtime.busy = True
    runtime.drain()
    assert runtime.cmds.calls == []
    assert binder.scene_publish_count == baseline
    runtime.busy = False
    runtime.now += 1.0
    runtime.events[-1]()
    runtime.drain()
    assert binder.scene_publish_count == baseline + 1
    runtime.assert_main_queries()


def test_deferred_submission_failure_allows_next_event(runtime):
    binder = runtime.make_binder()
    baseline = binder.scene_publish_count
    runtime.events[-1]()
    runtime.clear_queries()
    runtime.refuse = True
    runtime.timers[-1].fire()
    assert runtime.cmds.calls == []
    assert runtime.queue == []
    runtime.refuse = False
    runtime.now += 1.0
    _in_worker(runtime.events[-1])
    assert runtime.cmds.calls == []
    runtime.drain()
    assert binder.scene_publish_count == baseline + 1
    runtime.assert_main_queries()


def test_scene_query_reentrant_event_coalesces_without_deadlock(runtime):
    binder = runtime.make_binder()
    baseline = binder.scene_publish_count
    runtime.events[-1]()
    runtime.clear_queries()
    runtime.cmds.on_query = runtime.events[-1]
    runtime.now += 1.0
    runtime.timers[-1].fire()
    assert runtime.cmds.calls == []
    runtime.drain()
    assert binder.scene_publish_count == baseline + 1
    assert len(runtime.timers) == 1
    assert runtime.queue == []
    runtime.assert_main_queries()


def test_provider_exception_does_not_permanently_block_next_event(runtime):
    binder = runtime.make_binder()
    baseline = binder.scene_publish_count
    runtime.events[-1]()

    def broken_provider():
        raise RuntimeError("scene temporarily unavailable")

    binder.snapshot_provider = broken_provider
    runtime.now += 1.0
    runtime.timers[-1].fire()
    runtime.drain()
    assert binder.scene_publish_count == baseline
    binder.snapshot_provider = runtime.provider
    runtime.clear_queries()
    runtime.events[-1]()
    runtime.drain()
    assert binder.scene_publish_count == baseline + 1
    runtime.assert_main_queries()


def test_unbind_during_provider_collection_discards_old_payload_and_metadata(runtime):
    binder = runtime.make_binder()
    baseline = binder.scene_publish_count
    baseline_scenes = len(runtime.scenes)
    runtime.events[-1]()
    runtime.clear_queries()
    runtime.cmds.on_query = binder.unbind
    runtime.now += 1.0
    runtime.timers[-1].fire()
    assert runtime.cmds.calls == []
    runtime.drain()
    assert runtime.cmds.calls
    assert {thread for _, thread in runtime.cmds.calls} == {threading.main_thread()}
    assert binder.scene_publish_count == baseline
    assert len(runtime.scenes) == baseline_scenes
    assert runtime.metadata == []


@pytest.mark.parametrize("fifo", [False, True])
def test_late_teardown_kills_only_old_hooks_after_rebind(runtime, monkeypatch, fifo):
    killed = []

    def remove(ids):
        killed.append(list(ids))
        return []

    monkeypatch.setattr(resources_mod, "_default_event_remover", remove)
    runtime.event_ids = [11, 12]
    binder = runtime.make_binder()
    assert binder.scene_event_ids == [11, 12]
    _in_worker(binder.unbind)
    assert len(runtime.queue) == 1
    runtime.event_ids = [21, 22]
    assert binder.bind(runtime.server)
    binder.install_scene_events()
    baseline = binder.scene_publish_count
    runtime.clear_queries()
    runtime.events[-1]()
    runtime.now += 0.5
    runtime.timers[-1].fire()
    assert len(runtime.queue) == 2
    runtime.drain(fifo=fifo)
    assert killed == [[11, 12]]
    assert binder.scene_event_ids == [21, 22]
    assert binder.scene_publish_count == baseline + 1
    runtime.assert_main_queries()


def test_old_refresh_cannot_redirect_metadata_to_rebound_server(runtime, monkeypatch):
    binder = runtime.make_binder()
    new_metadata = []
    new_server = types.SimpleNamespace(
        _server=runtime.server._server,
        publish_capability_snapshot=lambda reason: new_metadata.append(reason),
    )
    sync_metadata = binder._sync_gateway_scene_metadata

    def rebind_before_sync(*args):
        monkeypatch.setattr(binder, "_sync_gateway_scene_metadata", sync_metadata)

        def rebind():
            binder.unbind()
            assert binder.bind(new_server)

        _in_worker(rebind)
        sync_metadata(*args)

    monkeypatch.setattr(binder, "_sync_gateway_scene_metadata", rebind_before_sync)
    runtime.events[-1]()
    runtime.now += 0.5
    runtime.timers[-1].fire()
    runtime.queue.pop(0)()
    assert new_metadata == [], "old refresh reached the new binding"
    assert len(runtime.queue) == 1
    runtime.drain()
    assert new_metadata == ["scene_resource"]
