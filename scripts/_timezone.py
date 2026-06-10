#!/usr/bin/env python3
"""
时区工具模块
服务器UTC时间，业务使用CST（Asia/Shanghai，UTC+8）
所有脚本统一从此模块导入时间函数，禁止直接使用 datetime.now()
"""
from datetime import datetime, timezone, timedelta

# CST 时区常量（UTC+8）
CST = timezone(timedelta(hours=8))

def today_cst_str(fmt: str = "%Y-%m-%d") -> str:
    """返回今日 CST 日期字符串"""
    return datetime.now(CST).strftime(fmt)

def now_cst() -> datetime:
    """返回当前 CST datetime 对象"""
    return datetime.now(CST)

def now_iso() -> str:
    """返回当前 UTC ISO 字符串（用于存储/跨Agent通信）"""
    return datetime.now(timezone.utc).isoformat()

# 标准写法（推荐）：datetime.now(CST)
# 禁止：datetime.now() — 会产生 naive datetime，歧义的根源