import asyncio

from voss_runtime import WorkingMemory

async def note(content: str):
    scratchpad.add(content)

async def main():
    scratchpad = WorkingMemory(capacity=8)

if __name__ == "__main__":
    asyncio.run(main())
