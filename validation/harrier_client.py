"""HTTP client for the Harrier MCP server (Streamable HTTP / JSON-RPC 2.0).

Implements the minimal MCP protocol needed for the validation harness:
  1. initialize handshake (stores Mcp-Session-Id)
  2. notifications/initialized signal
  3. tools/call for any Harrier tool

Uses only stdlib (urllib) — no boto3 or requests dependency.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any


class HarrierClientError(Exception):
    pass


@dataclass
class HarrierClient:
    """Minimal MCP Streamable HTTP client for validation harness use."""

    mcp_url: str
    timeout: int = 60
    _session_id: str | None = field(default=None, init=False, repr=False)
    _next_id: int = field(default=0, init=False, repr=False)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def initialize(self) -> dict[str, Any]:
        """Perform MCP initialize + initialized handshake; return server info."""
        req_id = self._alloc_id()
        body = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {
                    "name": "harrier-validation-harness",
                    "version": "1.0.0",
                },
            },
            "id": req_id,
        }
        result = self._post(body, req_id)

        # Send initialized notification (server may return 202 with no body)
        notify = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        }
        try:
            self._post(notify, req_id=None)
        except HarrierClientError:
            pass

        return result

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a named MCP tool and return the deserialized result dict."""
        req_id = self._alloc_id()
        body = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
            "id": req_id,
        }
        rpc_result = self._post(body, req_id)
        return self._extract_content(rpc_result)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _alloc_id(self) -> int:
        req_id = self._next_id
        self._next_id += 1
        return req_id

    def _post(self, body: dict, req_id: int | None) -> dict[str, Any]:
        data = json.dumps(body).encode()
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id

        request = urllib.request.Request(
            self.mcp_url, data=data, headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as resp:
                content_type = resp.headers.get("Content-Type", "")
                session_hdr = resp.headers.get("Mcp-Session-Id")
                if session_hdr:
                    self._session_id = session_hdr
                raw = resp.read()
        except urllib.error.HTTPError as exc:
            body_bytes = exc.read() if exc.fp else b""
            raise HarrierClientError(
                f"HTTP {exc.code} {exc.reason}: {body_bytes[:200]!r}"
            ) from exc
        except OSError as exc:
            raise HarrierClientError(f"Connection error: {exc}") from exc

        if not raw.strip():
            return {}

        if "text/event-stream" in content_type:
            return self._parse_sse(raw, req_id)

        try:
            envelope = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise HarrierClientError(
                f"Non-JSON response: {raw[:200]!r}"
            ) from exc

        if "error" in envelope:
            raise HarrierClientError(f"MCP error: {envelope['error']}")
        return envelope.get("result") or {}

    def _parse_sse(self, raw: bytes, req_id: int | None) -> dict[str, Any]:
        """Find the JSON-RPC response matching req_id in an SSE byte stream."""
        for line in raw.decode(errors="replace").splitlines():
            if not line.startswith("data: "):
                continue
            payload = line[6:]
            try:
                envelope = json.loads(payload)
            except json.JSONDecodeError:
                continue
            # Notifications omit "id"; skip them when we have a specific ID
            if req_id is not None and envelope.get("id") != req_id:
                continue
            if "error" in envelope:
                raise HarrierClientError(f"MCP error: {envelope['error']}")
            return envelope.get("result") or {}
        return {}

    def _extract_content(self, rpc_result: dict[str, Any]) -> dict[str, Any]:
        """Unpack the tool payload from MCP text content blocks.

        FastMCP serialises tool return values as JSON inside a text content block:
        {"content": [{"type": "text", "text": "{...json...}"}], "isError": false}
        """
        content = rpc_result.get("content") or []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "")
                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, dict):
                        return parsed
                except json.JSONDecodeError:
                    return {"raw": text}
        # Fall back to returning the rpc_result directly (e.g. direct-JSON mode)
        return rpc_result
