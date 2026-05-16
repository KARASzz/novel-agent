from rag_engine.mcp_client import _redact_mcp_log


def test_redact_mcp_log_masks_keys():
    line = 'Using custom headers: {"Authorization":"Bearer abc123"} tavilyApiKey=tvly-xyz'
    redacted = _redact_mcp_log(line)

    assert "abc123" not in redacted
    assert "tvly-xyz" not in redacted
    assert "Bearer <redacted>" in redacted
    assert "tavilyApiKey=<redacted>" in redacted
