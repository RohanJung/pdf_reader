from __future__ import annotations

from typing import List

import google.generativeai as genai

from config import settings


class GeminiLLM:
    """Google Gemini integration for natural language responses"""

    def __init__(self, model: str = "gemini-2.5-pro") -> None:
        if not settings.GOOGLE_API_KEY:
            raise RuntimeError(
                "GOOGLE_API_KEY is empty. Set it in your environment or config."
            )
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self.model = genai.GenerativeModel(model)

    def build_prompt(
        self,
        question: str,
        retrieved_chunks: List[str],
        history_block: str | None = None,
    ) -> str:
        context_block = "\n\n".join(
            f"[Chunk {i+1}]\n{t}" for i, t in enumerate(retrieved_chunks)
        )
        sys_rules = (
            "You are a helpful assistant. Answer using information from the provided context "
            "and previous conversation. If you mentioned information earlier in the conversation, "
            "you can reference it. If the answer is not available, say you don't know.\n\n"
        )

        prompt_parts = [sys_rules]
        if history_block:
            prompt_parts.append("Conversation so far:\n" + history_block + "\n\n")

        prompt_parts.append("Context:\n" + context_block + "\n\n")
        prompt_parts.append("Question:\n" + question + "\n\n")
        prompt_parts.append("Answer:")

        return "".join(prompt_parts)

    def generate(self, prompt: str) -> str:
        resp = self.model.generate_content(prompt)
        return (resp.text or "").strip()
