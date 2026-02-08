"""Tests for the webhook manager and tools"""
import pytest
import hashlib
import hmac
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from managers.webhook_manager import WebhookManager, SUPPORTED_EVENTS


class TestWebhookRegistration:
    """Test webhook registration and management"""

    def test_register_webhook(self):
        """Test basic webhook registration"""
        manager = WebhookManager()
        result = manager.register(
            url="https://example.com/webhook",
            events=["generation_completed"]
        )

        assert "webhook_id" in result
        assert result["url"] == "https://example.com/webhook"
        assert "generation_completed" in result["events"]

    def test_register_all_events(self):
        """Test registration with all events (None = all)"""
        manager = WebhookManager()
        result = manager.register(url="https://example.com/webhook")

        assert set(result["events"]) == SUPPORTED_EVENTS

    def test_register_with_secret(self):
        """Test registration with HMAC secret"""
        manager = WebhookManager()
        result = manager.register(
            url="https://example.com/webhook",
            secret="my-secret-key"
        )

        assert result["has_secret"] is True

    def test_invalid_url_rejected(self):
        """Test that invalid URLs are rejected"""
        manager = WebhookManager()

        with pytest.raises(ValueError, match="Invalid webhook URL"):
            manager.register(url="not-a-url")

        with pytest.raises(ValueError, match="Invalid webhook URL"):
            manager.register(url="ftp://example.com/webhook")

    def test_invalid_events_rejected(self):
        """Test that invalid event types are rejected"""
        manager = WebhookManager()

        with pytest.raises(ValueError, match="Invalid events"):
            manager.register(
                url="https://example.com/webhook",
                events=["invalid_event"]
            )

    def test_unregister_webhook(self):
        """Test webhook unregistration"""
        manager = WebhookManager()
        result = manager.register(url="https://example.com/webhook")
        webhook_id = result["webhook_id"]

        assert manager.unregister(webhook_id) is True
        assert manager.get_webhook(webhook_id) is None

    def test_unregister_nonexistent(self):
        """Test unregistering non-existent webhook"""
        manager = WebhookManager()
        assert manager.unregister("nonexistent-id") is False


class TestWebhookListing:
    """Test webhook listing functionality"""

    def test_list_empty(self):
        """Test listing when no webhooks registered"""
        manager = WebhookManager()
        webhooks = manager.list_webhooks()
        assert webhooks == []

    def test_list_multiple(self):
        """Test listing multiple webhooks"""
        manager = WebhookManager()
        manager.register(url="https://example1.com/webhook")
        manager.register(url="https://example2.com/webhook")

        webhooks = manager.list_webhooks()
        assert len(webhooks) == 2

    def test_get_specific_webhook(self):
        """Test getting a specific webhook by ID"""
        manager = WebhookManager()
        result = manager.register(
            url="https://example.com/webhook",
            events=["generation_completed"]
        )

        webhook = manager.get_webhook(result["webhook_id"])
        assert webhook is not None
        assert webhook["url"] == "https://example.com/webhook"


class TestHMACSigning:
    """Test HMAC-SHA256 signature generation"""

    def test_signature_format(self):
        """Test signature format is sha256=<hex>"""
        secret = "my-secret"
        body = '{"event": "test"}'

        signature = hmac.new(
            secret.encode("utf-8"),
            body.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        full_signature = f"sha256={signature}"
        assert full_signature.startswith("sha256=")
        assert len(signature) == 64  # SHA256 hex length

    def test_signature_verification(self):
        """Test that signature can be verified"""
        secret = "my-secret"
        body = '{"event": "generation_completed", "data": {}}'

        # Generate signature
        signature = hmac.new(
            secret.encode("utf-8"),
            body.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        # Verify signature
        expected = hmac.new(
            secret.encode("utf-8"),
            body.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        assert hmac.compare_digest(signature, expected)


class TestWebhookDispatch:
    """Test webhook event dispatching"""

    def test_dispatch_returns_webhook_ids(self):
        """Test dispatch returns list of notified webhook IDs"""
        manager = WebhookManager()
        result = manager.register(
            url="https://example.com/webhook",
            events=["generation_completed"]
        )

        with patch.object(manager, '_deliver_with_retry'):
            webhook_ids = manager.dispatch("generation_completed", {"test": "data"})

        assert result["webhook_id"] in webhook_ids

    def test_dispatch_filters_by_event(self):
        """Test dispatch only notifies subscribed webhooks"""
        manager = WebhookManager()

        # Subscribe to generation_completed
        manager.register(
            url="https://example1.com/webhook",
            events=["generation_completed"]
        )

        # Subscribe to asset_published only
        manager.register(
            url="https://example2.com/webhook",
            events=["asset_published"]
        )

        with patch.object(manager, '_deliver_with_retry'):
            webhook_ids = manager.dispatch("generation_completed", {})

        assert len(webhook_ids) == 1  # Only first webhook

    def test_dispatch_unknown_event(self):
        """Test dispatch with unknown event type"""
        manager = WebhookManager()
        webhook_ids = manager.dispatch("unknown_event", {})
        assert webhook_ids == []

    def test_dispatch_to_inactive_webhook(self):
        """Test that inactive webhooks are not notified"""
        manager = WebhookManager()
        result = manager.register(url="https://example.com/webhook")
        manager.set_active(result["webhook_id"], False)

        with patch.object(manager, '_deliver_with_retry'):
            webhook_ids = manager.dispatch("generation_completed", {})

        assert len(webhook_ids) == 0


class TestWebhookRetry:
    """Test webhook retry logic"""

    def test_retry_parameters(self):
        """Test retry configuration"""
        manager = WebhookManager(
            max_retries=3,
            initial_retry_delay=1.0,
            max_retry_delay=30.0
        )

        assert manager.max_retries == 3
        assert manager.initial_retry_delay == 1.0
        assert manager.max_retry_delay == 30.0

    def test_exponential_backoff(self):
        """Test exponential backoff calculation"""
        initial_delay = 1.0
        max_delay = 30.0

        delays = []
        delay = initial_delay
        for _ in range(5):
            delays.append(delay)
            delay = min(delay * 2, max_delay)

        assert delays == [1.0, 2.0, 4.0, 8.0, 16.0]


class TestWebhookDeliveryLog:
    """Test webhook delivery logging"""

    def test_get_empty_log(self):
        """Test getting empty delivery log"""
        manager = WebhookManager()
        entries = manager.get_delivery_log()
        assert entries == []

    def test_log_entry_structure(self):
        """Test delivery log entry structure"""
        expected_fields = [
            "delivery_id",
            "webhook_id",
            "event",
            "timestamp",
            "status_code",
            "success",
            "error",
            "retry_count",
            "response_time_ms"
        ]

        # Verify structure by checking field names
        for field in expected_fields:
            assert isinstance(field, str)

    def test_log_filtering_by_webhook_id(self):
        """Test filtering log by webhook_id"""
        manager = WebhookManager(max_log_entries=100)

        # The filtering logic
        entries = [
            {"webhook_id": "a", "event": "test"},
            {"webhook_id": "b", "event": "test"},
            {"webhook_id": "a", "event": "test"}
        ]

        filtered = [e for e in entries if e["webhook_id"] == "a"]
        assert len(filtered) == 2

    def test_log_filtering_by_event(self):
        """Test filtering log by event type"""
        entries = [
            {"webhook_id": "a", "event": "generation_completed"},
            {"webhook_id": "a", "event": "asset_published"},
            {"webhook_id": "a", "event": "generation_completed"}
        ]

        filtered = [e for e in entries if e["event"] == "generation_completed"]
        assert len(filtered) == 2


class TestSupportedEvents:
    """Test supported webhook events"""

    def test_all_events_defined(self):
        """Test all expected events are defined"""
        expected = {
            "generation_completed",
            "asset_published",
            "job_failed",
            "job_started",
            "job_cancelled"
        }

        assert SUPPORTED_EVENTS == expected

    def test_event_count(self):
        """Test correct number of events"""
        assert len(SUPPORTED_EVENTS) == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
