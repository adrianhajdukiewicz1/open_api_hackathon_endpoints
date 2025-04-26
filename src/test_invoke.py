import asyncio
import aiohttp

async def test_invoke():
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:8000/invoke",
            json={"content": "What is 10 + 10?"}
        ) as response:
            async for chunk in response.content.iter_chunked(1024):
                print(chunk.decode(), end="", flush=True)

if __name__ == "__main__":
    asyncio.run(test_invoke()) 