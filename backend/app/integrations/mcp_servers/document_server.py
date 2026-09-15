import os
import re
from pathlib import Path

from mcp.server import MCPServer

mcp = MCPServer("SafetyGate Document Server")

_DOCUMENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


def _document_root() -> Path:
    configured = os.getenv("SAFETYGATE_DOCUMENT_ROOT")

    if not configured:
        raise RuntimeError(
            "SAFETYGATE_DOCUMENT_ROOT is not configured."
        )

    root = Path(configured).expanduser().resolve()

    if not root.is_dir():
        raise RuntimeError(
            "SAFETYGATE_DOCUMENT_ROOT does not reference a directory."
        )

    return root


@mcp.tool()
def server_status() -> dict[str, str]:
    """Return diagnostic status from the MCP document server."""

    return {
        "status": "ready",
        "server": "safetygate-document-server",
    }


@mcp.tool()
def read_documents(document_id: str) -> dict[str, str]:
    """Read a document from the configured SafetyGate document root."""

    if not document_id or not _DOCUMENT_ID_PATTERN.fullmatch(document_id):
        raise ValueError(
            "document_id contains unsupported characters."
        )

    root = _document_root()
    document_path = (root / f"{document_id}.txt").resolve()

    if document_path.parent != root:
        raise ValueError(
            "Document path escaped the configured document root."
        )

    if not document_path.is_file():
        raise FileNotFoundError(
            f"Document '{document_id}' was not found."
        )

    content = document_path.read_text(encoding="utf-8")

    return {
        "document_id": document_id,
        "content": content,
    }


if __name__ == "__main__":
    mcp.run()
