"""jrysprpr v1.1.1 - 今日运势
按 用户ID + 日期 确定性生成：同一人同一天全群同步、结果固定，
每天凌晨 0 点自动刷新新运势，不同群友结果不同，数据持久化到 data.json。

命令：
  今日运势 / 运势 / jrys   查看今日运势
"""

import os
import json
import random
import hashlib
from datetime import date

from astrbot.api.event import AstrMessageEvent, filter as filter_mod
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data.json")

# 运势等级：名称 / 分数区间 / 图标
LEVELS = [
    ("大吉", 90, 100, "🌟"),
    ("中吉", 80, 89, "✨"),
    ("小吉", 70, 79, "🌤"),
    ("吉",   60, 69, "🍀"),
    ("末吉", 45, 59, "🌫"),
    ("小凶", 30, 44, "☁️"),
    ("凶",   15, 29, "🌧"),
    ("大凶",  0, 14, "⛈"),
]

COLORS = [
    "琥珀金", "雾霾蓝", "焦糖棕", "薄荷绿", "樱草粉", "玄青", "朱砂红",
    "月牙白", "苔藓绿", "葡萄紫", "暮云灰", "落日橙", "深海蓝", "暖阳黄",
    "烟灰紫", "松柏绿", "玫瑰金", "黛青", "藕荷色", "苍绿", "鎏金", "冰蓝",
]

ITEMS = [
    "旧怀表", "铜钥匙", "玻璃弹珠", "泛黄的书签", "爷爷的烟斗", "折半的船票",
    "生锈的铃铛", "猫眼石", "褪色的合影", "檀木梳", "纸鹤", "幸运硬币",
    "青瓷茶杯", "磨损的骰子", "银质耳钉", "帆布包里的橡皮", "漂流瓶", "残缺的塔罗牌",
    "绿植叶片", "手写便签", "琥珀吊坠", "旧皮手套", "火柴盒", "纽扣",
]

YI_POOL = [
    "表白", "签合同", "远行", "搬家", "请客吃饭", "买新衣服", "早睡", "整理房间",
    "给家人打电话", "写日记", "晨跑", "学新东西", "存钱", "修补旧物", "理发",
    "清理手机相册", "约老友叙旧", "晒太阳", "泡茶", "记账", "逛旧书店", "赠人小礼",
    "洗衣服", "浇水养花", "换床单", "断舍离", "早到十分钟", "轻声哼歌",
]

JI_POOL = [
    "熬夜", "借贷", "冲动消费", "说人闲话", "闯红灯", "逞强喝酒", "捡路上东西",
    "撕票根", "背对门坐", "半夜点外卖", "打断别人话", "乱发誓", "踩井盖",
    "把伞借出去", "夹带私货", "和杠精争论", "空腹喝咖啡", "攒塑料瓶", "赌气关机",
    "在雷雨天开窗", "随手扔纸团", "翻旧账", "迟到", "把剪刀放枕边", "轻信广告",
]

COMMENT_GOOD = [
    "今日宜大胆，好运站在你这边。",
    "连窗外的猫都对你点头，顺。",
    "口袋里的硬币在发烫，是个好日子。",
    "风从东边来，带着好事的气味。",
    "今天你是酒馆里运气最好的那位。",
    "指针走得很顺，适合把所有计划往前推。",
    "抬头有光，低头有路，稳。",
    "今日份的好运已到账，请查收。",
]

COMMENT_MID = [
    "不温不火的一天，稳住就是赢。",
    "运势平平，但心态好就能扳回一局。",
    "别贪，今天求稳比求猛划算。",
    "半晴半多云，适合按部就班。",
    "不急不躁，日子自有它的节奏。",
    "运势一般，攒着劲等明天。",
]

COMMENT_BAD = [
    "今日宜低调，锋芒收一收。",
    "天公不作美，出门多留个心眼。",
    "运势低迷，但明天总会翻篇。",
    "少做决定，今天交给时间。",
    "乌云罩顶，躲着点麻烦事。",
    "诸事慢半拍，忍一忍就过去了。",
]

DIMS = ["财运", "事业", "爱情", "健康"]


def _load():
    try:
        if os.path.exists(DATA_PATH):
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"jrysprpr: 读取 data.json 失败: {e}")
    return {}


def _save(data):
    try:
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"jrysprpr: 保存 data.json 失败: {e}")


def _seed(uid: str, today: str) -> int:
    # 只按 用户+日期 播种：同一用户所有群同步同一份运势
    raw = f"{uid}:{today}".encode("utf-8")
    return int(hashlib.md5(raw).hexdigest()[:8], 16)


def _fortune_date() -> str:
    """运势日期：自然日，每天凌晨 0 点自动刷新"""
    return date.today().isoformat()


@register("jrysprpr", "扎恩斯", "今日运势：按群友+日期确定性生成，跨天刷新，数据持久化", "1.0.0")
class JrysPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self._data = _load()

    @filter_mod.command("今日运势", alias={"运势", "jrys", "jrysprpr"})
    async def fortune(self, event: AstrMessageEvent):
        uid = event.get_sender_id()
        today = _fortune_date()

        # 持久化：当天已有记录直接复用（全群同步，0点刷新）
        rec = self._data.get(uid)
        if rec and rec.get("date") == today:
            yield event.plain_result(self._render(rec, first=False))
            return

        # 确定性生成
        rng = random.Random(_seed(uid, today))
        score = rng.randint(0, 100)
        level_name = icon = ""
        for lv, a, b, ic in LEVELS:
            if a <= score <= b:
                level_name, icon = lv, ic
                break
        rec = {
            "date": today,
            "level": level_name,
            "icon": icon,
            "score": score,
            "dims": {d: rng.randint(20, 100) for d in DIMS},
            "color": rng.choice(COLORS),
            "num": rng.randint(1, 99),
            "item": rng.choice(ITEMS),
            "yi": rng.sample(YI_POOL, 2),
            "ji": rng.sample(JI_POOL, 2),
            "comment": rng.choice(
                COMMENT_GOOD if score >= 60 else COMMENT_BAD if score < 45 else COMMENT_MID
            ),
        }
        self._data[uid] = rec
        _save(self._data)
        yield event.plain_result(self._render(rec, first=True))

    @staticmethod
    def _render(rec: dict, first: bool) -> str:
        tip = "（今日运势已固定，凌晨0点自动刷新）" if not first else ""
        dims = "  ".join(f"{k}{v}" for k, v in rec["dims"].items())
        return (
            f"{rec['icon']} 今日运势：{rec['level']}（{rec['score']}分）{tip}\n"
            f"📊 维度：{dims}\n"
            f"🎨 幸运色：{rec['color']}　🔢 幸运数字：{rec['num']}\n"
            f"🍀 幸运物：{rec['item']}\n"
            f"✅ 宜：{'、'.join(rec['yi'])}\n"
            f"⚠️ 忌：{'、'.join(rec['ji'])}\n"
            f"💬 {rec['comment']}"
        )
