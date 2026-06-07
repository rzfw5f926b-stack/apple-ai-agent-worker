import asyncio
from apple_fm_wrapper.core import AppleFMClient

async def main():
    client = AppleFMClient()
    
    categories = ["科技", "財經", "政治", "娛樂"]
    prompt = "這是一個關於 OpenAI 發布新模型的新聞。"
    
    print(f"測試 Prompt: {prompt}")
    result = await client.fast_classify(prompt, categories)
    print(f"分類結果: {result.label}, 置信度: {result.confidence}")

if __name__ == "__main__":
    asyncio.run(main())
