TOOL_PERMISSION_REQUIREMENTS: dict[str, set[str]] = {
    "read_documents": {"documents:read"},
    "send_message": {"messages:send"},
    "deploy_service": {"deploy:write"},
    "delete_records": {"records:delete"},
}
