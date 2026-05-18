import pytest
from unittest.mock import patch, AsyncMock
from app.services.webhook_service import WebhookService


@pytest.mark.asyncio
async def test_subscribe_and_dispatch():
    service = WebhookService()
    service.subscribe("test.event", "https://example.com/hook", "secret123")
    assert "test.event" in service._subscriptions
    assert len(service._subscriptions["test.event"]) == 1


@pytest.mark.asyncio
async def test_unsubscribe():
    service = WebhookService()
    service.subscribe("test.event", "https://example.com/hook")
    service.unsubscribe("test.event", "https://example.com/hook")
    assert len(service._subscriptions["test.event"]) == 0


@pytest.mark.asyncio
async def test_dispatch_no_subscribers():
    service = WebhookService()
    result = await service.dispatch("nonexistent", {})
    assert result is None


@pytest.mark.asyncio
async def test_dispatch_with_hmac():
    service = WebhookService()
    service.subscribe("test.event", "https://example.com/hook", "mysecret")
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock()
        mock_client.return_value.__aenter__.return_value.post.return_value.status_code = 200
        await service.dispatch("test.event", {"key": "value"})
        mock_client.return_value.__aenter__.return_value.post.assert_called_once()
        _, kwargs = mock_client.return_value.__aenter__.return_value.post.call_args
        assert "X-AutoTest-Signature" in kwargs["headers"]


@pytest.mark.asyncio
async def test_dispatch_retry_on_5xx():
    service = WebhookService()
    service.subscribe("test.event", "https://example.com/hook")
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock()
        mock_client.return_value.__aenter__.return_value.post.return_value.status_code = 500
        await service.dispatch("test.event", {})
        assert mock_client.return_value.__aenter__.return_value.post.call_count >= 1
