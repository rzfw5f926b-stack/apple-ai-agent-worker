import asyncio
from apple_fm_wrapper.core import AppleFMClient

async def main():
    client = AppleFMClient()
    
    print("--- 第一輪 ---")
    print(await client.chat("我叫 Jonas。"))
    
    print("\n--- 第二輪 ---")
    print(await client.chat("我喜歡藍色。"))
    
    print("\n--- 第三輪 (驗證記憶) ---")
    print(await client.chat("請問我叫什麼？我喜歡什麼顏色？"))

if __name__ == "__main__":
    asyncio.run(main())
