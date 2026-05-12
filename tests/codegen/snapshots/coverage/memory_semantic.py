import asyncio

from voss_runtime import SemanticMemory

async def lookup(q: str) -> list[str]:
    return kb.retrieve(q, top_k=3)

async def main():
    kb = SemanticMemory(source='./knowledge_base/')

if __name__ == "__main__":
    asyncio.run(main())
