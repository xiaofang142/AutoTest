import pytest
from app.lib.event_bus import EventBus, DomainEvent


@pytest.mark.asyncio
async def test_publish_subscribe():
    bus = EventBus()
    received = []

    async def handler(event: DomainEvent):
        received.append(event.payload)

    bus.subscribe("test.event", handler)
    await bus.publish(DomainEvent("test.event", {"key": "value"}))
    assert len(received) == 1
    assert received[0]["key"] == "value"


@pytest.mark.asyncio
async def test_unsubscribed_event_not_delivered():
    bus = EventBus()
    received = []

    async def handler(event: DomainEvent):
        received.append(event)

    bus.subscribe("event.a", handler)
    await bus.publish(DomainEvent("event.b", {}))
    assert len(received) == 0


@pytest.mark.asyncio
async def test_handler_exception_does_not_block():
    bus = EventBus()
    received = []

    async def failing_handler(event: DomainEvent):
        raise ValueError("oops")

    async def good_handler(event: DomainEvent):
        received.append(event)

    bus.subscribe("test.event", failing_handler)
    bus.subscribe("test.event", good_handler)
    await bus.publish(DomainEvent("test.event", {}))
    assert len(received) == 1


def test_domain_event_has_id():
    event = DomainEvent("test", {"a": 1})
    assert event.event_id.startswith("evt_")
    assert event.event_type == "test"
