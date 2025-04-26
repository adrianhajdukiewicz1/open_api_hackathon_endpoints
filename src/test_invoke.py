import aiohttp
import asyncio

async def test_invoke(content):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:8080/api/invoke",  # fixed path
            json={"content": content}
        ) as response:
            if response.status != 200:
                print(f"Error: {response.status}")
                return
            async for chunk in response.content.iter_chunked(1024):
                print(chunk.decode(), end="", flush=True)

# if __name__ == "__main__":
#     asyncio.run(test_invoke('what is 10 + 10'))
