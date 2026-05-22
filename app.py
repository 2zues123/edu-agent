from __future__ import annotations

import streamlit as st

from src.graph import LangGraphAcademicAgent, GraphAgentAnswer


EXAMPLE_QUESTIONS = [
    "机器学习课程多少学分？",
    "数字图像处理课程的考核方式是什么？",
    "2024培养方案的软件工程专业毕业要求是什么？",
    "如果挂科会影响毕业吗？",
    "人工智能导论有哪些先修课程？",
]


@st.cache_resource
def load_agent() -> LangGraphAcademicAgent:
    return LangGraphAcademicAgent()


def render_answer(result: GraphAgentAnswer) -> None:
    intent_label = f"{result.intent_name}｜{result.intent_description}"
    risk_label = "高风险事项" if result.high_risk else "普通咨询"

    col_intent, col_risk, col_sources = st.columns([2, 1, 1])
    col_intent.metric("识别意图", intent_label)
    col_risk.metric("风险级别", risk_label)
    col_sources.metric("引用数量", len(result.sources))

    if result.high_risk:
        st.warning("该问题涉及正式教务认定，最终结果以教务系统、学院和教务部门审核为准。")

    st.subheader("回答")
    st.markdown(result.answer)

    st.subheader("引用来源")
    if not result.sources:
        st.info("当前知识库没有返回可引用来源。")
        return

    for index, source in enumerate(result.sources, start=1):
        heading = source.heading or "未识别章节"
        with st.expander(f"{index}. {source.title}｜{heading}", expanded=index == 1):
            st.caption(f"类别：{source.category} ｜ 来源：{source.source_file} ｜ 分数：{source.score:.4f}")
            st.write(source.text)


def main() -> None:
    st.set_page_config(
        page_title="高校教务教学智能体",
        page_icon="🎓",
        layout="wide",
    )

    st.title("高校教务教学智能体")
    st.caption("面向培养方案、课程大纲、考试成绩事务和办事流程的知识库问答原型")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    with st.sidebar:
        st.header("设置")
        use_llm = st.toggle("调用大模型生成回答", value=True)
        top_k = st.slider("检索片段数量", min_value=1, max_value=10, value=5)

        st.divider()
        st.subheader("示例问题")
        for question in EXAMPLE_QUESTIONS:
            if st.button(question, use_container_width=True):
                st.session_state.pending_question = question

        st.divider()
        if st.button("清空对话", use_container_width=True):
            st.session_state.messages = []
            st.session_state.pop("pending_question", None)
            st.rerun()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant" and "result" in message:
                render_answer(message["result"])
            else:
                st.markdown(message["content"])

    typed_question = st.chat_input("请输入教务或课程相关问题")
    question = st.session_state.pop("pending_question", None) or typed_question
    if not question:
        return

    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("正在识别意图、检索知识库并生成回答..."):
            try:
                result = load_agent().answer(question, top_k=top_k, use_llm=use_llm)
            except Exception as exc:
                st.error(f"运行失败：{exc}")
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": f"运行失败：{exc}",
                    }
                )
                return
        render_answer(result)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result.answer,
            "result": result,
        }
    )


if __name__ == "__main__":
    main()
