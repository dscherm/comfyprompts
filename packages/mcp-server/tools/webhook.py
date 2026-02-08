"""Webhook tools for managing HTTP callbacks on events"""

import logging
from typing import List, Optional

from mcp.server.fastmcp import FastMCP

from managers.webhook_manager import SUPPORTED_EVENTS

logger = logging.getLogger("MCP_Server")


def register_webhook_tools(mcp: FastMCP, webhook_manager):
    """Register webhook management tools with the MCP server"""

    @mcp.tool()
    def set_webhook(
        url: str,
        events: Optional[List[str]] = None,
        secret: Optional[str] = None
    ) -> dict:
        """Register a webhook to receive event notifications.

        Webhooks receive HTTP POST requests when specified events occur.
        The payload includes the event type, timestamp, and event-specific data.

        **Supported Events:**
        - `generation_completed` - Any image/video/audio generation finishes
        - `asset_published` - An asset is published via publish_asset
        - `job_failed` - A generation job fails
        - `job_started` - A generation job begins
        - `job_cancelled` - A job is cancelled

        **Webhook Payload Format:**
        ```json
        {
            "event": "generation_completed",
            "timestamp": "2024-01-15T10:30:00.000Z",
            "webhook_id": "uuid",
            "data": {
                "tool": "generate_image",
                "asset_id": "uuid",
                ...
            }
        }
        ```

        **Security:**
        If a secret is provided, each request includes an `X-Webhook-Signature`
        header with an HMAC-SHA256 signature: `sha256=<hex_digest>`.
        Verify by computing `HMAC-SHA256(secret, request_body)`.

        Args:
            url: The webhook URL (must be http:// or https://)
            events: List of events to subscribe to. If None, subscribes to all events.
            secret: Optional secret for HMAC-SHA256 signature verification.

        Returns:
            Dict with:
            - webhook_id: Unique ID for this webhook registration
            - url: The registered URL
            - events: List of subscribed events
            - has_secret: Whether a secret was provided
            - created_at: Registration timestamp

        Examples:
            # Subscribe to all events
            set_webhook(url="https://my-server.com/webhook")

            # Subscribe to specific events with secret
            set_webhook(
                url="https://my-server.com/webhook",
                events=["generation_completed", "asset_published"],
                secret="my-secret-key"
            )
        """
        try:
            result = webhook_manager.register(
                url=url,
                events=events,
                secret=secret
            )
            return result
        except ValueError as e:
            return {"error": str(e)}
        except Exception as e:
            logger.exception("Failed to register webhook")
            return {"error": f"Failed to register webhook: {str(e)}"}

    @mcp.tool()
    def remove_webhook(webhook_id: str) -> dict:
        """Remove a registered webhook.

        Args:
            webhook_id: The webhook ID returned from set_webhook

        Returns:
            Dict with:
            - success: True if removed
            - webhook_id: The removed webhook ID
            - error: Error message if failed
        """
        try:
            removed = webhook_manager.unregister(webhook_id)
            if removed:
                return {"success": True, "webhook_id": webhook_id}
            else:
                return {"error": f"Webhook {webhook_id} not found"}
        except Exception as e:
            logger.exception("Failed to remove webhook")
            return {"error": f"Failed to remove webhook: {str(e)}"}

    @mcp.tool()
    def list_webhooks() -> dict:
        """List all registered webhooks.

        Returns:
            Dict with:
            - webhooks: List of webhook configurations
            - count: Total number of webhooks
            - supported_events: List of all supported event types
        """
        try:
            webhooks = webhook_manager.list_webhooks()
            return {
                "webhooks": webhooks,
                "count": len(webhooks),
                "supported_events": list(SUPPORTED_EVENTS)
            }
        except Exception as e:
            logger.exception("Failed to list webhooks")
            return {"error": f"Failed to list webhooks: {str(e)}"}

    @mcp.tool()
    def get_webhook_log(
        webhook_id: Optional[str] = None,
        event: Optional[str] = None,
        limit: int = 50
    ) -> dict:
        """Get webhook delivery log entries.

        Useful for debugging webhook delivery issues. Shows recent delivery
        attempts with status codes, errors, and response times.

        Args:
            webhook_id: Filter by specific webhook ID
            event: Filter by event type
            limit: Maximum entries to return (default: 50, max: 500)

        Returns:
            Dict with:
            - entries: List of delivery log entries (newest first)
            - count: Number of entries returned
            - filters: Applied filters

        Each entry includes:
        - delivery_id: Unique delivery attempt ID
        - webhook_id: Target webhook
        - event: Event type
        - timestamp: When delivery was attempted
        - status_code: HTTP response code (or null if failed before response)
        - success: Whether delivery succeeded
        - error: Error message if failed
        - retry_count: Number of retry attempts made
        - response_time_ms: Response time in milliseconds
        """
        try:
            # Cap limit at 500
            limit = min(limit, 500)

            entries = webhook_manager.get_delivery_log(
                webhook_id=webhook_id,
                event=event,
                limit=limit
            )

            return {
                "entries": entries,
                "count": len(entries),
                "filters": {
                    "webhook_id": webhook_id,
                    "event": event,
                    "limit": limit
                }
            }
        except Exception as e:
            logger.exception("Failed to get webhook log")
            return {"error": f"Failed to get webhook log: {str(e)}"}

    @mcp.tool()
    def update_webhook(
        webhook_id: str,
        active: Optional[bool] = None,
        events: Optional[List[str]] = None
    ) -> dict:
        """Update a webhook's configuration.

        Args:
            webhook_id: The webhook ID to update
            active: Enable (True) or disable (False) the webhook
            events: New list of events to subscribe to

        Returns:
            Dict with updated webhook configuration or error
        """
        try:
            # Get current webhook
            webhook = webhook_manager.get_webhook(webhook_id)
            if not webhook:
                return {"error": f"Webhook {webhook_id} not found"}

            # Apply updates
            if active is not None:
                webhook_manager.set_active(webhook_id, active)

            if events is not None:
                try:
                    webhook_manager.update_events(webhook_id, events)
                except ValueError as e:
                    return {"error": str(e)}

            # Return updated webhook
            updated = webhook_manager.get_webhook(webhook_id)
            return {
                "success": True,
                "webhook": updated
            }
        except Exception as e:
            logger.exception("Failed to update webhook")
            return {"error": f"Failed to update webhook: {str(e)}"}

    logger.info("Registered webhook tools: set_webhook, remove_webhook, list_webhooks, get_webhook_log, update_webhook")
