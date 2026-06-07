import apple_fm_sdk as fm
import asyncio
from typing import Any, List, Optional, Type, Union

class AppleFMClient:
    """
    Apple Foundation Models SDK Wrapper
    封裝 README 中驗證過的高效能模式
    """
    def __init__(self, permissive: bool = True):
        # 預設使用 PERMISSIVE 模式以減少誤判
        self.model = fm.SystemLanguageModel(
            guardrails=fm.SystemLanguageModelGuardrails.PERMISSIVE_CONTENT_TRANSFORMATIONS if permissive 
            else fm.SystemLanguageModelGuardrails.DEFAULT
        )
        self.session: Optional[fm.LanguageModelSession] = None

    def ensure_session(self, tools: List[fm.Tool] = None):
        """確保 session 存在，用於維持多輪對話記憶"""
        if self.session is None:
            self.session = fm.LanguageModelSession(model=self.model, tools=tools)
        return self.session

    async def fast_classify(self, prompt: str, categories: List[str], confidence_range: tuple = (0, 100)) -> Any:
        """
        極速分類器：結合 anyOf guide 與 token 限制 (README 驗證: < 0.5s)
        """
        @fm.generable
        class Classification:
            label: str = fm.guide(anyOf=categories)
            confidence: int = fm.guide(minimum=confidence_range[0], maximum=confidence_range[1])

        options = fm.GenerationOptions(
            temperature=0.0,
            maximum_response_tokens=30,
            sampling=fm.SamplingMode(fm.SamplingModeType.GREEDY)
        )
        
        session = self.ensure_session()
        return await session.respond(prompt, generating=Classification, options=options)

    async def chat(self, prompt: str, tools: List[fm.Tool] = None) -> str:
        """標準對話，自動維持 session 記憶"""
        session = self.ensure_session(tools=tools)
        response = await session.respond(prompt)
        return response

    def reset_session(self):
        """清除記憶，建立新 session"""
        self.session = None

    async def finance_text_fetch(self, prompt: str) -> str:
        """
        財經內容 Workaround: 
        由於結構化財經輸出被 Hard Block，此方法強制使用純文字輸出
        """
        session = self.ensure_session()
        # 強制不傳入 generating 或 json_schema
        return await session.respond(prompt)
