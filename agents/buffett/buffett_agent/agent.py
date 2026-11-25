"""Claude Agent SDK로 버핏 페르소나 에이전트를 구성하고 질문을 보낸다."""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
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


def _chunks(msg, show_tools: bool) -> list[str]:
    """메시지 하나에서 화면에 보여 줄 문장을 뽑는다."""
    out: list[str] = []
    if isinstance(msg, AssistantMessage):
        # 도구를 부르는 턴의 문장("먼저 도구를 불러오겠습니다" 등)은 최종 답이 아니므로 숨긴다
        calls_tool = any(isinstance(b, ToolUseBlock) for b in msg.content)
        for block in msg.content:
            if isinstance(block, TextBlock) and (show_tools or not calls_tool):
                out.append(block.text)
            elif show_tools and isinstance(block, ToolUseBlock):
                out.append(f"\n[도구 호출: {block.name} {block.input}]\n")
    elif isinstance(msg, ResultMessage):
        if msg.is_error:
            out.append(f"\n[오류로 종료됨: {msg.subtype}]\n")
        elif show_tools and msg.total_cost_usd is not None:
            out.append(f"\n[비용: ${msg.total_cost_usd:.3f}, 턴 {msg.num_turns}]\n")
    return out


async def ask(question: str, *, model: str | None = DEFAULT_MODEL, show_tools: bool = False) -> AsyncIterator[str]:
    """답변 텍스트를 조각 단위로 내보낸다. show_tools=True면 도구 호출과 비용도 한 줄로 알린다."""
    async for msg in query(prompt=question, options=build_options(model)):
        for chunk in _chunks(msg, show_tools):
            yield chunk


async def ask_once(question: str, **kw) -> str:
    return "".join([chunk async for chunk in ask(question, **kw)])


COST_NOTICE = (
    "※ 이 대화는 Claude 모델을 호출합니다. 요금제에 따라 사용량이나 비용이 생길 수 있습니다.\n"
    "  질문 한 번에 보통 몇 번의 도구 호출과 모델 응답이 오갑니다(--show-tools로 비용 확인).\n"
)


async def chat(*, model: str | None = DEFAULT_MODEL, show_tools: bool = False, assume_yes: bool = False) -> None:
    """여러 턴 대화. 같은 세션을 이어 가므로 앞선 질문을 기억한다. 'exit' 또는 빈 줄 두 번으로 종료."""
    print(COST_NOTICE)
    if not assume_yes and input("계속할까요? (y/N) ").strip().lower() not in ("y", "yes", "예", "ㅇ"):
        print("취소했습니다. 비용이 없는 확인은 `pytest -q`로 오프라인 테스트만 돌려 보세요.")
        return
    print("버핏 페르소나와 대화합니다. (AI 재현, 투자 조언 아님) 종료: exit\n")
    async with ClaudeSDKClient(options=build_options(model)) as client:
        blank = 0
        while True:
            try:
                text = input("나> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if text.lower() in ("exit", "quit", "종료"):
                break
            blank = blank + 1 if not text else 0
            if blank >= 2:
                break
            if not text:
                continue
            await client.query(text)
            print("버핏> ", end="", flush=True)
            async for msg in client.receive_response():
                for chunk in _chunks(msg, show_tools):
                    print(chunk, end="", flush=True)
            print("\n")


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="buffett_agent", description="워런 버핏 페르소나 에이전트 (AI 재현, 투자 조언 아님)")
    ap.add_argument("question", nargs="?", help="한 번만 묻기. 생략하거나 --chat이면 대화 모드")
    ap.add_argument("--chat", action="store_true", help="여러 턴 대화 모드")
    ap.add_argument("--yes", action="store_true", help="대화 모드의 비용 안내 확인을 건너뜀")
    ap.add_argument("--model")
    ap.add_argument("--show-tools", action="store_true")
    a = ap.parse_args(argv)

    async def run() -> None:
        if a.chat or not a.question:
            await chat(model=a.model, show_tools=a.show_tools, assume_yes=a.yes)
            return
        async for chunk in ask(a.question, model=a.model, show_tools=a.show_tools):
            print(chunk, end="", flush=True)
        print()

    asyncio.run(run())
    return 0
