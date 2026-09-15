from types import SimpleNamespace

import pytest
from app.integrations import mcp_client
from app.integrations.mcp_client import (
    McpClientError,
    McpStdioClientAdapter,
    McpStdioServerConfig,
)
from mcp.types import TextContent


def make_adapter() -> McpStdioClientAdapter:
    return McpStdioClientAdapter(
        McpStdioServerConfig(
            command="python",
            args=("server.py",),
        )
    )


def test_stdio_server_config_rejects_blank_command() -> None:
    with pytest.raises(
        ValueError,
        match="command",
    ):
        McpStdioServerConfig(command="   ")


@pytest.mark.asyncio
async def test_lists_tools_from_configured_mcp_server(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = {}

    class FakeClient:
        def __init__(self, target):
            captured["target"] = target

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def list_tools(self):
            return SimpleNamespace(
                tools=[
                    SimpleNamespace(
                        name="read_documents",
                        title="Read documents",
                        description="Read an approved document.",
                        input_schema={
                            "type": "object",
                            "properties": {
                                "document_id": {
                                    "type": "string",
                                }
                            },
                            "required": ["document_id"],
                        },
                    )
                ]
            )

    monkeypatch.setattr(
        mcp_client,
        "Client",
        FakeClient,
    )

    tools = await make_adapter().list_tools()

    assert len(tools) == 1
    assert tools[0].name == "read_documents"
    assert tools[0].input_schema["type"] == "object"

    assert captured["target"].command == "python"
    assert captured["target"].args == ["server.py"]


@pytest.mark.asyncio
async def test_calls_tool_and_normalizes_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = {}

    class FakeClient:
        def __init__(self, target):
            captured["target"] = target

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def call_tool(
            self,
            name,
            *,
            arguments,
        ):
            captured["name"] = name
            captured["arguments"] = arguments

            return SimpleNamespace(
                is_error=False,
                structured_content={
                    "document_id": arguments["document_id"],
                    "status": "read",
                },
                content=[
                    TextContent(
                        type="text",
                        text="Document read successfully.",
                    )
                ],
            )

    monkeypatch.setattr(
        mcp_client,
        "Client",
        FakeClient,
    )

    result = await make_adapter().call_tool(
        "read_documents",
        {
            "document_id": "doc-001",
        },
    )

    assert captured["name"] == "read_documents"
    assert captured["arguments"] == {
        "document_id": "doc-001",
    }

    assert result["structured_content"] == {
        "document_id": "doc-001",
        "status": "read",
    }

    assert (
        result["content"][0]["text"]
        == "Document read successfully."
    )


@pytest.mark.asyncio
async def test_mcp_error_result_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeClient:
        def __init__(self, target):
            self.target = target

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def call_tool(
            self,
            name,
            *,
            arguments,
        ):
            return SimpleNamespace(
                is_error=True,
                structured_content=None,
                content=[],
            )

    monkeypatch.setattr(
        mcp_client,
        "Client",
        FakeClient,
    )

    with pytest.raises(
        McpClientError,
        match="error result",
    ):
        await make_adapter().call_tool(
            "read_documents",
            {
                "document_id": "doc-001",
            },
        )


@pytest.mark.asyncio
async def test_mcp_transport_failure_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeClient:
        def __init__(self, target):
            self.target = target

        async def __aenter__(self):
            raise OSError("MCP process unavailable.")

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        mcp_client,
        "Client",
        FakeClient,
    )

    with pytest.raises(
        McpClientError,
        match="execution failed",
    ):
        await make_adapter().call_tool(
            "read_documents",
            {
                "document_id": "doc-001",
            },
        )



@pytest.mark.asyncio
async def test_stdio_config_passes_explicit_trusted_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = {}

    class FakeClient:
        def __init__(self, target):
            captured["target"] = target

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def list_tools(self):
            return SimpleNamespace(tools=[])

    monkeypatch.setattr(
        mcp_client,
        "Client",
        FakeClient,
    )

    adapter = McpStdioClientAdapter(
        McpStdioServerConfig(
            command="python",
            args=("server.py",),
            env=(
                (
                    "SAFETYGATE_DOCUMENT_ROOT",
                    "/trusted/documents",
                ),
            ),
        )
    )

    await adapter.list_tools()

    assert captured["target"].env == {
        "SAFETYGATE_DOCUMENT_ROOT": "/trusted/documents",
    }
