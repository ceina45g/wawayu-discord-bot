#!/usr/bin/env python3
"""
FreshTok 页面审核员 MCP Server
为小智机器人提供 FreshTok 页面内容审核工具。

工具列表：
  - audit_freshtok_page   审核 FreshTok 页面整体状态
  - check_video_public    检查视频是否处于公开可审核状态
  - generate_audit_report 生成审核报告摘要
"""

import logging
from datetime import datetime, timezone
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

# ── 日志配置 ──
logger = logging.getLogger("freshtok_auditor")
logger.setLevel(logging.INFO)

# ── 创建 MCP Server ──
mcp = FastMCP("FreshTokAuditor")

# ── 审核结果常量 ──
AUDIT_PASS = "pass"
AUDIT_REVIEW = "review"
AUDIT_REJECT = "reject"

# FreshTok / TikTok 常见的审核标记关键词
FLAG_KEYWORDS = {
    "copyright": ["copyright", "dmca", "版权"],
    "community": ["community guidelines", "社区准则", "违规"],
    "safety": ["safety", "安全", "敏感"],
    "spam": ["spam", "垃圾信息", "重复"],
}


def _now_iso() -> str:
    """返回当前 UTC 时间的 ISO 格式字符串。"""
    return datetime.now(timezone.utc).isoformat()


def _match_flags(text: str) -> list[str]:
    """从文本中匹配审核标记关键词，返回命中的分类列表。"""
    text_lower = text.lower()
    matched = []
    for category, keywords in FLAG_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            matched.append(category)
    return matched


# ═══════════════════════════════════════════════════════════
#  工具 1：审核 FreshTok 页面整体状态
# ═══════════════════════════════════════════════════════════
@mcp.tool()
def audit_freshtok_page(
    page_url: Annotated[
        str,
        Field(description="FreshTok 页面 URL 或 TikTok 视频链接"),
    ],
    page_title: Annotated[
        str,
        Field(description="页面标题（用于内容合规检查）", default=""),
    ] = "",
    page_description: Annotated[
        str,
        Field(description="页面描述或文案（用于内容合规检查）", default=""),
    ] = "",
    is_flagged: Annotated[
        bool,
        Field(description="FreshTok/TikTok 是否将该页面标记为待审核", default=False),
    ] = False,
) -> dict:
    """
    审核 FreshTok 页面状态。

    当用户询问某个 FreshTok 页面是否可审核、是否被标记、
    或需要检查页面内容合规性时，调用此工具。

    返回审核结论、风险等级和建议操作。
    """
    logger.info("audit_freshtok_page url=%s flagged=%s", page_url, is_flagged)

    issues = []
    risk_level = "low"

    # 1. 平台标记检查
    if is_flagged:
        issues.append("平台已将该页面标记为待审核（Private 状态）")
        risk_level = "high"

    # 2. 标题/描述内容检查
    combined_text = f"{page_title} {page_description}".strip()
    if combined_text:
        matched = _match_flags(combined_text)
        if matched:
            issues.append(f"内容中命中审核分类: {', '.join(matched)}")
            risk_level = "medium" if risk_level != "high" else "high"

    # 3. 空页面检查
    if not page_url or not page_url.strip():
        issues.append("页面 URL 为空，无法定位审核对象")
        risk_level = "high"

    # 4. 得出审核结论
    if not issues:
        audit_result = AUDIT_PASS
        summary = "页面状态正常，未发现审核风险，可通过审核。"
    elif risk_level == "high":
        audit_result = AUDIT_REJECT
        summary = "页面存在高风险问题，建议拒绝或转人工复核。"
    else:
        audit_result = AUDIT_REVIEW
        summary = "页面存在潜在风险，建议转人工审核。"

    return {
        "success": True,
        "audit_result": audit_result,
        "risk_level": risk_level,
        "issues": issues,
        "summary": summary,
        "page_url": page_url,
        "audited_at": _now_iso(),
    }


# ═══════════════════════════════════════════════════════════
#  工具 2：检查视频公开状态
# ═══════════════════════════════════════════════════════════
@mcp.tool()
def check_video_public(
    video_id: Annotated[
        str,
        Field(description="TikTok / FreshTok 视频 ID"),
    ],
    visibility: Annotated[
        str,
        Field(
            description="视频可见性状态，可选值: public / private / flagged",
            default="public",
        ),
    ] = "public",
) -> dict:
    """
    检查视频是否处于可被 FreshTok 识别和审核的公开状态。

    仅 public 状态的视频可被 FreshTok 读取和审核；
    flagged 状态的视频在 TikTok 审核通过前为 Private，
    FreshTok 无法获取其内容。

    当用户询问某个视频是否可审核、为何 FreshTok 看不到视频时，
    调用此工具。
    """
    logger.info("check_video_public video_id=%s visibility=%s", video_id, visibility)

    status_map = {
        "public": {
            "accessible": True,
            "message": "视频为公开状态，FreshTok 可正常读取和审核。",
        },
        "private": {
            "accessible": False,
            "message": "视频为私密状态，FreshTok 无法获取内容。",
        },
        "flagged": {
            "accessible": False,
            "message": "视频已被平台标记待审核，审核通过前为 Private 状态，FreshTok 无法读取。",
        },
    }

    result = status_map.get(
        visibility.lower(),
        {"accessible": False, "message": f"未知的可见性状态: {visibility}"},
    )

    return {
        "success": True,
        "video_id": video_id,
        "visibility": visibility,
        "accessible_by_freshtok": result["accessible"],
        "message": result["message"],
        "checked_at": _now_iso(),
    }


# ═══════════════════════════════════════════════════════════
#  工具 3：生成审核报告摘要
# ═══════════════════════════════════════════════════════════
@mcp.tool()
def generate_audit_report(
    page_url: Annotated[
        str,
        Field(description="被审核的 FreshTok 页面 URL"),
    ],
    audit_result: Annotated[
        str,
        Field(description="审核结论: pass / review / reject"),
    ],
    risk_level: Annotated[
        str,
        Field(description="风险等级: low / medium / high"),
    ],
    issues: Annotated[
        list[str],
        Field(description="发现的问题列表", default_factory=list),
    ] = None,
) -> dict:
    """
    根据审核结果生成结构化的审核报告摘要。

    当用户需要将审核结果整理为报告、或需要以自然语言
    向他人转述审核结论时，调用此工具。

    返回可直接朗读或展示的报告文本。
    """
    if issues is None:
        issues = []

    logger.info("generate_audit_report url=%s result=%s", page_url, audit_result)

    result_label = {
        "pass": "通过",
        "review": "待人工复核",
        "reject": "拒绝",
    }.get(audit_result, audit_result)

    risk_label = {
        "low": "低",
        "medium": "中",
        "high": "高",
    }.get(risk_level, risk_level)

    lines = [
        f"FreshTok 页面审核报告",
        f"页面: {page_url}",
        f"审核结论: {result_label}",
        f"风险等级: {risk_label}",
        f"审核时间: {_now_iso()}",
    ]

    if issues:
        lines.append(f"发现 {len(issues)} 个问题:")
        for i, issue in enumerate(issues, 1):
            lines.append(f"  {i}. {issue}")
    else:
        lines.append("未发现问题。")

    report_text = "\n".join(lines)

    return {
        "success": True,
        "report_text": report_text,
        "audit_result": audit_result,
        "risk_level": risk_level,
        "issue_count": len(issues),
    }


# ═══════════════════════════════════════════════════════════
#  启动
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    mcp.run(transport="stdio")