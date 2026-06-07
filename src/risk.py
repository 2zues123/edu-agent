"""Risk detection for high-stakes academic affairs answers."""

from __future__ import annotations


HIGH_RISK_KEYWORDS = [
    "毕业资格",
    "毕业",
    "学位",
    "学籍",
    "退学",
    "休学",
    "复学",
    "处分",
    "违纪",
    "成绩认定",
    "成绩",
    "挂科",
    "补考",
    "重修",
]

RISK_NOTICE = (
    "该问题涉及正式教务认定，系统仅根据当前知识库做初步判断，"
    "最终结果以教务系统、学院和教务部门审核为准。"
)


def is_high_risk(question: str) -> bool:
    return any(keyword in question for keyword in HIGH_RISK_KEYWORDS)

