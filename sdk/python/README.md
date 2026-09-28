# NEXUS Python SDK

Minimal typed client for the NEXUS Public API v1.

```python
from nexus_sdk import NEXUSClient

client = NEXUSClient("https://nexus.example.com/api", "<api-key>")
resources = client.list_resources()
incidents = client.list_incidents()
```

The SDK uses the standard library only and sends the API key in `X-API-Key`.
