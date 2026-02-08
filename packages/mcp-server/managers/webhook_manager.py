"""Webhook manager for HTTP callbacks on events"""

import hashlib
import hmac
import json
import logging
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

import requests

logger = logging.getLogger("MCP_Server")

# Supported webhook events
SUPPORTED_EVENTS = {
    "generation_completed",  # Any generation finishes
    "asset_published",       # publish_asset completes
    "job_failed",           # Generation fails
    "job_started",          # Job begins
    "job_cancelled",        # Job cancelled
}


@dataclass
class WebhookConfig:
    """Configuration for a registered webhook"""
    webhook_id: str
    url: str
    events: Set[str]
    secret: Optional[str] = None  # For HMAC signing
    created_at: datetime = field(default_factory=datetime.now)
    active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WebhookDelivery:
    """Record of a webhook delivery attempt"""
    delivery_id: str
    webhook_id: str
    event: str
    payload: Dict[str, Any]
    timestamp: datetime
    status_code: Optional[int] = None
    success: bool = False
    error: Optional[str] = None
    retry_count: int = 0
    response_time_ms: Optional[float] = None


class WebhookManager:
    """Manages webhook registrations and event dispatching.

    Features:
    - Register/unregister webhooks for specific events
    - HMAC-SHA256 signing for payload verification
    - Automatic retry with exponential backoff
    - Delivery logging for debugging
    - Thread-safe operations
    """

    def __init__(
        self,
        max_retries: int = 3,
        initial_retry_delay: float = 1.0,
        max_retry_delay: float = 30.0,
        timeout: float = 10.0,
        max_log_entries: int = 1000
    ):
        """Initialize the webhook manager.

        Args:
            max_retries: Maximum retry attempts for failed deliveries
            initial_retry_delay: Initial delay between retries (seconds)
            max_retry_delay: Maximum delay between retries (seconds)
            timeout: HTTP request timeout (seconds)
            max_log_entries: Maximum delivery log entries to keep
        """
        self._webhooks: Dict[str, WebhookConfig] = {}
        self._delivery_log: deque = deque(maxlen=max_log_entries)
        self._lock = threading.RLock()

        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay
        self.max_retry_delay = max_retry_delay
        self.timeout = timeout

        logger.info(f"WebhookManager initialized (max_retries={max_retries}, timeout={timeout}s)")

    def register(
        self,
        url: str,
        events: Optional[List[str]] = None,
        secret: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Register a new webhook.

        Args:
            url: The webhook URL to call
            events: List of events to subscribe to. If None, subscribes to all events.
            secret: Optional secret for HMAC signing
            metadata: Optional metadata to store with the webhook

        Returns:
            Dict with webhook_id and registration details
        """
        # Validate URL
        if not url or not url.startswith(("http://", "https://")):
            raise ValueError("Invalid webhook URL. Must start with http:// or https://")

        # Validate events
        if events:
            invalid_events = set(events) - SUPPORTED_EVENTS
            if invalid_events:
                raise ValueError(f"Invalid events: {invalid_events}. Supported: {SUPPORTED_EVENTS}")
            event_set = set(events)
        else:
            event_set = SUPPORTED_EVENTS.copy()

        webhook_id = str(uuid.uuid4())

        config = WebhookConfig(
            webhook_id=webhook_id,
            url=url,
            events=event_set,
            secret=secret,
            metadata=metadata or {}
        )

        with self._lock:
            self._webhooks[webhook_id] = config

        logger.info(f"Registered webhook {webhook_id} for events {event_set}")

        return {
            "webhook_id": webhook_id,
            "url": url,
            "events": list(event_set),
            "created_at": config.created_at.isoformat(),
            "has_secret": secret is not None
        }

    def unregister(self, webhook_id: str) -> bool:
        """Unregister a webhook.

        Args:
            webhook_id: The webhook ID to remove

        Returns:
            True if webhook was removed, False if not found
        """
        with self._lock:
            if webhook_id in self._webhooks:
                del self._webhooks[webhook_id]
                logger.info(f"Unregistered webhook {webhook_id}")
                return True
            return False

    def list_webhooks(self) -> List[Dict[str, Any]]:
        """List all registered webhooks.

        Returns:
            List of webhook configurations
        """
        with self._lock:
            return [
                {
                    "webhook_id": w.webhook_id,
                    "url": w.url,
                    "events": list(w.events),
                    "active": w.active,
                    "created_at": w.created_at.isoformat(),
                    "has_secret": w.secret is not None,
                    "metadata": w.metadata
                }
                for w in self._webhooks.values()
            ]

    def get_webhook(self, webhook_id: str) -> Optional[Dict[str, Any]]:
        """Get details of a specific webhook.

        Args:
            webhook_id: The webhook ID

        Returns:
            Webhook details or None if not found
        """
        with self._lock:
            w = self._webhooks.get(webhook_id)
            if not w:
                return None
            return {
                "webhook_id": w.webhook_id,
                "url": w.url,
                "events": list(w.events),
                "active": w.active,
                "created_at": w.created_at.isoformat(),
                "has_secret": w.secret is not None,
                "metadata": w.metadata
            }

    def dispatch(self, event: str, payload: Dict[str, Any]) -> List[str]:
        """Dispatch an event to all subscribed webhooks.

        Args:
            event: The event type
            payload: Event payload data

        Returns:
            List of webhook_ids that will receive the event
        """
        if event not in SUPPORTED_EVENTS:
            logger.warning(f"Unknown event type: {event}")
            return []

        with self._lock:
            subscribers = [
                w for w in self._webhooks.values()
                if w.active and event in w.events
            ]

        if not subscribers:
            logger.debug(f"No webhooks subscribed to event: {event}")
            return []

        webhook_ids = []
        for webhook in subscribers:
            webhook_ids.append(webhook.webhook_id)
            # Dispatch asynchronously to avoid blocking
            thread = threading.Thread(
                target=self._deliver_with_retry,
                args=(webhook, event, payload),
                daemon=True
            )
            thread.start()

        logger.info(f"Dispatching event '{event}' to {len(webhook_ids)} webhook(s)")
        return webhook_ids

    def _deliver_with_retry(
        self,
        webhook: WebhookConfig,
        event: str,
        payload: Dict[str, Any]
    ):
        """Deliver webhook with retry logic.

        Uses exponential backoff for retries.
        """
        delivery_id = str(uuid.uuid4())
        delivery = WebhookDelivery(
            delivery_id=delivery_id,
            webhook_id=webhook.webhook_id,
            event=event,
            payload=payload,
            timestamp=datetime.now()
        )

        delay = self.initial_retry_delay

        for attempt in range(self.max_retries + 1):
            delivery.retry_count = attempt

            try:
                success, status_code, error, response_time = self._send_webhook(
                    webhook, event, payload
                )

                delivery.status_code = status_code
                delivery.response_time_ms = response_time
                delivery.success = success

                if success:
                    logger.debug(f"Webhook {webhook.webhook_id} delivered successfully")
                    break

                delivery.error = error

                if attempt < self.max_retries:
                    logger.warning(
                        f"Webhook delivery failed (attempt {attempt + 1}/{self.max_retries + 1}): {error}. "
                        f"Retrying in {delay}s"
                    )
                    time.sleep(delay)
                    delay = min(delay * 2, self.max_retry_delay)
                else:
                    logger.error(
                        f"Webhook {webhook.webhook_id} delivery failed after {self.max_retries + 1} attempts: {error}"
                    )

            except Exception as e:
                delivery.error = str(e)
                delivery.success = False
                logger.exception(f"Unexpected error delivering webhook: {e}")
                break

        # Log the delivery
        with self._lock:
            self._delivery_log.append(delivery)

    def _send_webhook(
        self,
        webhook: WebhookConfig,
        event: str,
        payload: Dict[str, Any]
    ) -> tuple:
        """Send a single webhook request.

        Returns:
            Tuple of (success, status_code, error_message, response_time_ms)
        """
        # Build full payload
        full_payload = {
            "event": event,
            "timestamp": datetime.now().isoformat(),
            "webhook_id": webhook.webhook_id,
            "data": payload
        }

        body = json.dumps(full_payload, default=str)
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Event": event,
            "X-Webhook-Id": webhook.webhook_id,
            "X-Delivery-Id": str(uuid.uuid4())
        }

        # Add HMAC signature if secret is configured
        if webhook.secret:
            signature = hmac.new(
                webhook.secret.encode("utf-8"),
                body.encode("utf-8"),
                hashlib.sha256
            ).hexdigest()
            headers["X-Webhook-Signature"] = f"sha256={signature}"

        start_time = time.time()

        try:
            response = requests.post(
                webhook.url,
                data=body,
                headers=headers,
                timeout=self.timeout
            )
            response_time = (time.time() - start_time) * 1000

            if response.status_code >= 200 and response.status_code < 300:
                return True, response.status_code, None, response_time
            else:
                return False, response.status_code, f"HTTP {response.status_code}: {response.text[:200]}", response_time

        except requests.Timeout:
            return False, None, "Request timed out", None
        except requests.RequestException as e:
            return False, None, str(e), None

    def get_delivery_log(
        self,
        webhook_id: Optional[str] = None,
        event: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get webhook delivery log entries.

        Args:
            webhook_id: Filter by webhook ID
            event: Filter by event type
            limit: Maximum entries to return

        Returns:
            List of delivery log entries (newest first)
        """
        with self._lock:
            entries = list(self._delivery_log)

        # Filter
        if webhook_id:
            entries = [e for e in entries if e.webhook_id == webhook_id]
        if event:
            entries = [e for e in entries if e.event == event]

        # Sort by timestamp (newest first) and limit
        entries.sort(key=lambda x: x.timestamp, reverse=True)
        entries = entries[:limit]

        return [
            {
                "delivery_id": e.delivery_id,
                "webhook_id": e.webhook_id,
                "event": e.event,
                "timestamp": e.timestamp.isoformat(),
                "status_code": e.status_code,
                "success": e.success,
                "error": e.error,
                "retry_count": e.retry_count,
                "response_time_ms": e.response_time_ms
            }
            for e in entries
        ]

    def set_active(self, webhook_id: str, active: bool) -> bool:
        """Enable or disable a webhook.

        Args:
            webhook_id: The webhook ID
            active: Whether the webhook should be active

        Returns:
            True if updated, False if webhook not found
        """
        with self._lock:
            if webhook_id in self._webhooks:
                self._webhooks[webhook_id].active = active
                logger.info(f"Webhook {webhook_id} active={active}")
                return True
            return False

    def update_events(self, webhook_id: str, events: List[str]) -> bool:
        """Update the events a webhook is subscribed to.

        Args:
            webhook_id: The webhook ID
            events: New list of events

        Returns:
            True if updated, False if webhook not found
        """
        invalid_events = set(events) - SUPPORTED_EVENTS
        if invalid_events:
            raise ValueError(f"Invalid events: {invalid_events}")

        with self._lock:
            if webhook_id in self._webhooks:
                self._webhooks[webhook_id].events = set(events)
                logger.info(f"Webhook {webhook_id} events updated to {events}")
                return True
            return False
