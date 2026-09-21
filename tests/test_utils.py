"""
Shared test helpers for building an isolated OpenedxGamesXBlock instance in
tests -- own field storage (not ToyRuntime's shared global KVS, which would
otherwise leak state between tests) and a runtime whose `publish` calls are
captured for assertions (ToyRuntime's own `publish` only logs, so it can't be
asserted against directly).
"""

import uuid

from xblock.fields import ScopeIds
from xblock.runtime import DictKeyValueStore, KvsFieldData, MemoryIdManager, Runtime

from openedx_gamesxblock.games_block import OpenedxGamesXBlock

_ID_MANAGER = MemoryIdManager()


class _FakeUsageId:
    """
    Minimal stand-in for the opaque-key usage_id object edx-platform normally
    supplies (e.g. BlockUsageLocator), which exposes a `.block_id` attribute
    that upload_image relies on. A plain string usage_id (as ScopeIds accepts
    for simpler runtimes) has no such attribute, so tests need this shim.
    """

    def __init__(self, block_id):
        self.block_id = block_id

    def __str__(self):
        return self.block_id


class RecordingRuntime(Runtime):
    """
    A minimal Runtime with its own private field store (so tests never leak
    state into each other) that records every published event for assertions.
    """

    def __init__(self):
        super().__init__(
            _ID_MANAGER, _ID_MANAGER,
            services={"field-data": KvsFieldData(DictKeyValueStore())},
        )
        self.published_events = []

    def handler_url(self, block, handler_name, suffix="", query="", thirdparty=False):
        return f"/handler/{handler_name}"

    def local_resource_url(self, block, uri):
        return uri

    def resource_url(self, resource):
        return resource

    def publish(self, block, event_type, event_data):
        self.published_events.append((event_type, event_data))


def make_block(**field_overrides):
    """
    Build an OpenedxGamesXBlock with isolated per-test storage. Any keyword
    argument is applied as a field value immediately after construction.
    """
    block_id = f"test-{uuid.uuid4().hex}"
    scope_ids = ScopeIds("test-student", "openedx_gamesxblock", block_id, _FakeUsageId(block_id))
    runtime = RecordingRuntime()
    block = OpenedxGamesXBlock(runtime, scope_ids=scope_ids)
    for field_name, value in field_overrides.items():
        setattr(block, field_name, value)
    return block
