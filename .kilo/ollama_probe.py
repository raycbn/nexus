import asyncio

import ollama


async def main():
    client = ollama.AsyncClient(host="http://127.0.0.1:11434", timeout=120)
    response = await client.chat(
        model="hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M",
        messages=[{"role": "user", "content": "Reply with exactly HELLO"}],
        think=False,
        options={"num_ctx": 2048},
    )
    print(type(response))
    print(response)
    print(getattr(response, "message", None))

asyncio.run(main())
