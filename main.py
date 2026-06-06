from __future__ import annotations

import argparse
import sys

from src.graph import LangGraphAcademicAgent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="高校教务教学智能体命令行入口")
    parser.add_argument("question", nargs="*", help="要咨询的问题")
    parser.add_argument("--top-k", type=int, default=5, help="检索返回的知识片段数量")
    parser.add_argument("--no-llm", action="store_true", help="只检索依据，不调用 DeepSeek")
    return parser.parse_args()


def main() -> int:
    configure_stdout()
    args = parse_args()
    question = " ".join(args.question).strip()
    if not question:
        question = input("请输入问题：").strip()
    if not question:
        print("未输入问题。")
        return 1

    agent = LangGraphAcademicAgent()
    result = agent.answer(question, top_k=args.top_k, use_llm=not args.no_llm)

    print(f"问题：{result.question}")
    print(f"意图：{result.intent_name}（{result.intent_description}）")
    print(f"高风险：{'是' if result.high_risk else '否'}")
    print("\n回答：")
    print(result.answer)

    if result.sources:
        print("\n引用来源：")
        for index, source in enumerate(result.sources, start=1):
            heading = source_attr(source, "heading") or "未识别章节"
            title = source_attr(source, "title") or "未命名资料"
            source_file = source_attr(source, "source_file") or "未知来源"
            print(f"{index}. {title}｜{heading}｜{source_file}")
            source_url = source_attr(source, "source_url")
            if source_url:
                print(f"   官网链接：{source_url}")
    return 0


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def source_attr(source, name: str, default: str = "") -> str:
    value = getattr(source, name, default)
    return default if value is None else str(value)


if __name__ == "__main__":
    raise SystemExit(main())
