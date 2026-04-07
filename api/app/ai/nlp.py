from __future__ import annotations

import datetime as dt
import re
from typing import Literal


_AMOUNT_RE = re.compile(r"(-?\d+(?:\.\d{1,2})?)")
_MERCHANT_RE = re.compile(r"在(.+?)(?:花|消费|付款|付了|用了|买了|吃了)")
_DATE_TOKEN_RE = re.compile(r"(今天|昨日|昨天|明天)")
_TIME_RE = re.compile(r"(上午|中午|下午|晚上|凌晨)?\s*([0-9]{1,2}|[一二三四五六七八九十两]{1,3})(?:([:点])(\d{1,2})?)?(?:分)?(半)?")
_DATE_YMD_RE = re.compile(r"(\d{4})[./-](\d{1,2})[./-](\d{1,2})")
_TX_ID_RE = re.compile(r"(?:交易|流水)(?:编号|id|ID|#)?\s*[:：]?\s*(\d+)")
_CAT_ID_RE = re.compile(r"(?:类别|分类)(?:编号|id|ID)?\s*[:：]?\s*(\d+)")
_CATEGORY_NAME_QUOTED_RE = re.compile(r"[\"“](.+?)[\"”]")
_CATEGORY_CREATE_RE = re.compile(r"(?:新增|添加|创建|新建|建立)\s*(?:一个)?\s*(.+?)\s*(?:的)?\s*(?:分类|类别)")
_CATEGORY_CREATE_POST_RE = re.compile(r"(?:新增|添加|创建|新建|建立)(?:分类|类别)\s*(.+)")
_CATEGORY_CREATE_TYPED_POST_RE = re.compile(r"(?:新增|添加|创建|新建|建立)(?:一个)?(支出|收入)?(?:分类|类别)\s*(.+)")
_CATEGORY_CREATE_NAMED_RE = re.compile(r"(?:新增|添加|创建|新建|建立)(?:一个)?(?:分类|类别)(?:叫|名为)?(.+)")
_CATEGORY_TARGET_RE = re.compile(r"(?:归类到|归到|放到|分类到|归入|设为|改成)(.+?)(?:当中去|当中|里面|里|下|中|$)")
_TX_KEYWORD_RE = re.compile(r"(?:那笔|那条|这一笔|这笔|这条|帮我把|把)(.+?)(?:的)?(?:消费|支出|交易|流水)")


def infer_direction(message: str) -> Literal["income", "expense"]:
  if "收入" in message and "支出" not in message:
    return "income"
  return "expense"

def _norm(message: str) -> str:
  return re.sub(r"\s+", "", message)


def parse_amount_cents(message: str) -> int | None:
  m = _AMOUNT_RE.search(_norm(message))
  if not m:
    return None
  amount = float(m.group(1))
  return int(round(abs(amount) * 100))


def parse_merchant(message: str) -> tuple[str | None, bool]:
  m = _MERCHANT_RE.search(_norm(message))
  if not m:
    return None, False
  merchant = m.group(1).strip()
  if not merchant:
    return None, False
  return merchant[:128], True


def parse_occurred_at(message: str, *, tz_offset_hours: int = 8) -> tuple[dt.datetime, bool]:
  tz = dt.timezone(dt.timedelta(hours=tz_offset_hours))
  now = dt.datetime.now(tz)

  message = _norm(message)
  date = now.date()
  provided = False

  ymd = _DATE_YMD_RE.search(message)
  if ymd:
    date = dt.date(int(ymd.group(1)), int(ymd.group(2)), int(ymd.group(3)))
    provided = True

  dm = _DATE_TOKEN_RE.search(message)
  if dm:
    token = dm.group(1)
    if token in ["昨日", "昨天"]:
      date = date - dt.timedelta(days=1)
    elif token == "明天":
      date = date + dt.timedelta(days=1)
    provided = True

  tm = _TIME_RE.search(message)
  if tm and (tm.group(1) or tm.group(3)):
    part = tm.group(1) or ""

    def _cn_to_int(s: str) -> int:
      if s.isdigit():
        return int(s)
      if s == "十":
        return 10
      if s == "两":
        return 2
      table = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
      if "十" in s:
        left, _, right = s.partition("十")
        tens = table.get(left, 1) if left else 1
        ones = table.get(right, 0) if right else 0
        return tens * 10 + ones
      return table.get(s, 0)

    hour = _cn_to_int(tm.group(2))
    minute_str = tm.group(4)
    half = tm.group(5)
    minute = int(minute_str) if minute_str is not None and minute_str != "" else 0
    if half:
      minute = 30

    if part in ["下午", "晚上"] and hour < 12:
      hour += 12
    if part == "中午" and hour < 11:
      hour += 12
    if part == "凌晨" and hour == 12:
      hour = 0

    hour = max(0, min(hour, 23))
    minute = max(0, min(minute, 59))
    return dt.datetime(date.year, date.month, date.day, hour, minute, tzinfo=tz), True

  return now, provided


def parse_transaction_id(message: str) -> int | None:
  m = _TX_ID_RE.search(_norm(message))
  return int(m.group(1)) if m else None


def parse_category_id(message: str) -> int | None:
  m = _CAT_ID_RE.search(_norm(message))
  return int(m.group(1)) if m else None


def parse_category_name(message: str) -> str | None:
  message = _norm(message)
  q = _CATEGORY_NAME_QUOTED_RE.search(message)
  if q:
    name = q.group(1).strip()
    return name[:64] if name else None
  t = _CATEGORY_CREATE_TYPED_POST_RE.search(message)
  if t:
    name = t.group(2).strip()
  else:
    n = _CATEGORY_CREATE_NAMED_RE.search(message)
    if n:
      name = n.group(1).strip()
    else:
      name = None
  m = _CATEGORY_CREATE_RE.search(message)
  if m and not name:
    name = m.group(1).strip()
  elif not m and not name:
    m2 = _CATEGORY_CREATE_POST_RE.search(message)
    if not m2:
      return None
    name = m2.group(1).strip()
  if not name:
    return None
  for sep in ["然后", "并且", "并", "再", "同时", "以及"]:
    if sep in name:
      name = name.split(sep, 1)[0]
  for t in ["支出", "收入", "消费", "记账", "记一笔"]:
    name = name.replace(t, "")
  name = name.strip()
  return name[:64] if name else None


def parse_category_target_name(message: str) -> str | None:
  message = _norm(message)
  q = _CATEGORY_NAME_QUOTED_RE.search(message)
  if q:
    name = q.group(1).strip()
    return name[:64] if name else None
  m = _CATEGORY_TARGET_RE.search(message)
  if not m:
    return None
  name = m.group(1).strip()
  for t in ["分类", "类别"]:
    name = name.replace(t, "")
  for t in ["当中去", "当中"]:
    name = name.replace(t, "")
  if name.endswith("当"):
    name = name[:-1]
  name = name.strip()
  return name[:64] if name else None


def parse_transaction_keyword(message: str) -> str | None:
  message = _norm(message)
  q = _CATEGORY_NAME_QUOTED_RE.search(message)
  if q:
    k = q.group(1).strip()
    return k[:64] if k else None
  m = _TX_KEYWORD_RE.search(message)
  if not m:
    return None
  k = m.group(1).strip()
  if not k:
    return None
  for t in ["今天", "昨日", "昨天", "明天", "上午", "中午", "下午", "晚上", "凌晨"]:
    k = k.replace(t, "")
  if "在" in k:
    k = k.split("在", 1)[-1]
  for t in ["那笔", "这笔", "这条", "那条"]:
    k = k.replace(t, "")
  k = k.strip()
  return k[:64] if k else None


def infer_category_type(message: str) -> Literal["income", "expense"]:
  if "收入" in message and "支出" not in message:
    return "income"
  return "expense"
