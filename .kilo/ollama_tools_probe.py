import asyncio

import ollama


async def main():
    tools = []
    async with ollama.AsyncClient(host="http://127.0.0.1:11434") as client:
        response = await client.chat(
            model="hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M",
            messages=[
                {"role": "system", "content": "Use the available tool when useful."},
                {
                    "role": "user",
                    "content": (
                        "Check system information using the tool and then explain "
                        "what you found."
                    ),
                },
            ],
            tools=tools,
            think=False,
            options={"num_ctx": 2048},
        )
        print(response)


if __name__ == "__main__":
    asyncio.run(main())
