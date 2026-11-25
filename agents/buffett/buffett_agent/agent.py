"""Claude Agent SDK로 버핏 페르소나 에이전트를 구성하고 질문을 보낸다."""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    query,
)

from .quotes import PERSONA_DIR
from .tools import TOOL_NAMES, build_server

DEFAULT_MODEL = None  # None이면 SDK 기본 모델. 필요하면 'sonnet' 등으로 지정한다.


def system_prompt() -> str:
    return (PERSONA_DIR / "system_prompt.md").read_text(encoding="utf-8")


def build_options(model: str | None = DEFAULT_MODEL, max_turns: int = 8) -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        system_prompt=system_prompt(),  # 기본 Claude Code 프롬프트를 쓰지 않고 페르소나만 사용
        mcp_servers={"buffett": build_server()},
        allowed_tools=TOOL_NAMES,  # 파일·셸 같은 내장 도구는 허용하지 않는다
        setting_sources=[],  # 로컬 CLAUDE.md·설정을 불러오지 않는다
        max_turns=max_turns,
        model=model,
    )


async def ask(question: str, *, model: str | None = DEFAULT_MODEL, show_tools: bool = False) -> AsyncIterator[str]:
    """답변 텍스트를 조각 단위로 내보낸다. show_tools=True면 도구 호출도 한 줄로 알린다."""
    async for msg in query(prompt=question, options=build_options(model)):
        if isinstance(msg, AssistantMessage):
            # 도구를 부르는 턴의 문장("먼저 도구를 불러오겠습니다" 등)은 최종 답이 아니므로 숨긴다
            calls_tool = any(isinstance(b, ToolUseBlock) for b in msg.content)
            for block in msg.content:
                if isinstance(block, TextBlock) and (show_tools or not calls_tool):
                    yield block.text
                elif show_tools and isinstance(block, ToolUseBlock):
                    yield f"\n[도구 호출: {block.name} {block.input}]\n"
        elif isinstance(msg, ResultMessage):
            if msg.is_error:
                yield f"\n[오류로 종료됨: {msg.subtype}]\n"
            elif show_tools and msg.total_cost_usd is not None:
                yield f"\n[비용: ${msg.total_cost_usd:.3f}, 턴 {msg.num_turns}]\n"


async def ask_once(question: str, **kw) -> str:
    return "".join([chunk async for chunk in ask(question, **kw)])


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="buffett_agent", description="워런 버핏 페르소나 에이전트 (AI 재현, 투자 조언 아님)")
    ap.add_argument("question")
    ap.add_argument("--model")
    ap.add_argument("--show-tools", action="store_true")
    a = ap.parse_args(argv)

    async def run() -> None:
        async for chunk in ask(a.question, model=a.model, show_tools=a.show_tools):
            print(chunk, end="", flush=True)
        print()

    asyncio.run(run())
    return 0
