"""jrysprpr v1.2.2 - 今日运势（丰富版）
按 用户ID + 日期 确定性生成：同一人同一天全群同步、结果固定，
每天凌晨 0 点自动刷新，不同群友结果不同，数据持久化到 data.json。

命令：
  今日运势 / 运势 / jrys        查看今日运势
  转运 / 重抽运势 / jrysreroll  转运今日运势（每天限3次，一般越转越好）
  运势统计 / jrysstat           近30天个人运势统计
  运势排行 / jrysrank / 今日榜  本群今日运势榜 TOP3
  运势帮助 / jryshelp           命令说明
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
    "酒红", "灰金", "钴蓝", "竹青", "蜜桃", "月桂绿",
]

ITEMS = [
    "旧怀表", "铜钥匙", "玻璃弹珠", "泛黄的书签", "爷爷的烟斗", "折半的船票",
    "生锈的铃铛", "猫眼石", "褪色的合影", "檀木梳", "纸鹤", "幸运硬币",
    "青瓷茶杯", "磨损的骰子", "银质耳钉", "帆布包里的橡皮", "漂流瓶", "残缺的塔罗牌",
    "绿植叶片", "手写便签", "琥珀吊坠", "旧皮手套", "火柴盒", "纽扣",
    "半截粉笔", "列车时刻表", "风干的枫叶", "爷爷的怀表链", "褪色校徽", "磨圆的鹅卵石",
]

DIRECTIONS = ["正东", "正南", "正西", "正北", "东南", "西南", "东北", "西北"]

TIME_SLOTS = [
    "05:00-07:00", "07:00-09:00", "09:00-11:00", "11:00-13:00",
    "13:00-15:00", "15:00-17:00", "17:00-19:00", "19:00-21:00",
    "21:00-23:00",
]

KEYWORDS = [
    "破局", "沉淀", "邂逅", "远行", "修旧", "开源", "守约", "微光",
    "转弯", "试错", "归零", "升温", "拾遗", "共振", "静待", "播种",
    "翻篇", "借力", "慢热", "重启", "补漏", "合拍", "蓄力", "明牌",
]

MOTTOS_GOOD = [
    "时来天地皆同力。",
    "今日所求，皆有回响。",
    "星光不负赶路人。",
    "行到水穷处，坐看云起时。",
    "好事多磨，磨完了就是好事。",
    "风起于青萍之末，浪成于微澜之间。",
    "念念不忘，必有回响。",
    "人间枝头，各自乘流，今日顺流。",
]

MOTTOS_MID = [
    "慢慢来，比较快。",
    "守得云开见月明。",
    "凡有所学，皆成性格。",
    "水到渠成，急不得。",
    "半山腰太挤，去山顶看看。",
    "日子是过出来的，不是想出来的。",
    "稳住，我们能赢。",
    "平平淡淡才是真，但今天可以更好。",
]

MOTTOS_BAD = [
    "天将降大任，必先苦其心志。",
    "否极泰来，低谷之后是上坡。",
    "今天先低头走路，明天再抬头看天。",
    "留得青山在，不怕没柴烧。",
    "沉住气，倒霉的日子也有尽头。",
    "低谷是给转折留的位置。",
    "别慌，月亮也正在大海某处迷茫。",
    "熬过今天，明天又是新的一天。",
]

YI_POOL = [
    "表白", "签合同", "远行", "搬家", "请客吃饭", "买新衣服", "早睡", "整理房间",
    "给家人打电话", "写日记", "晨跑", "学新东西", "存钱", "修补旧物", "理发",
    "清理手机相册", "约老友叙旧", "晒太阳", "泡茶", "记账", "逛旧书店", "赠人小礼",
    "洗衣服", "浇水养花", "换床单", "断舍离", "早到十分钟", "轻声哼歌",
    "主动加薪", "补牙", "整理书桌", "和猫说话", "炖一锅汤", "给绿植换盆",
]

JI_POOL = [
    "熬夜", "借贷", "冲动消费", "说人闲话", "闯红灯", "逞强喝酒", "捡路上东西",
    "撕票根", "背对门坐", "半夜点外卖", "打断别人话", "乱发誓", "踩井盖",
    "把伞借出去", "夹带私货", "和杠精争论", "空腹喝咖啡", "攒塑料瓶", "赌气关机",
    "在雷雨天开窗", "随手扔纸团", "翻旧账", "迟到", "把剪刀放枕边", "轻信广告",
    "囤货", "开夜车", "删聊天记录", "拍板大事", "赌气买彩票", "冷水澡",
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
KEEP_DAYS = 30   # 历史记录保留天数（统计用）
MAX_REROLL = 3   # 每天转运次数上限


def _load():
    try:
        if os.path.exists(DATA_PATH):
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:  # noqa: BLE001
        logger.error(f"jrysprpr: 读取 data.json 失败: {e}")
    return {}


def _save(data):
    try:
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:  # noqa: BLE001
        logger.error(f"jrysprpr: 保存 data.json 失败: {e}")


def _seed(uid: str, today: str, salt: int = 0) -> int:
    # 只按 用户+日期+重抽次数 播种：同一用户所有群同步同一份运势
    raw = f"{uid}:{today}:{salt}".encode("utf-8")
    return int(hashlib.md5(raw).hexdigest()[:8], 16)


def _fortune_date() -> str:
    """运势日期：自然日，每天凌晨 0 点自动刷新"""
    return date.today().isoformat()


def _bar(score: int, width: int = 10) -> str:
    filled = round(score / 100 * width)
    return "█" * filled + "░" * (width - filled)


@register("jrysprpr", "扎恩斯", "今日运势：多群同步/0点刷新/统计/排行/转运，数据持久化", "1.2.2")
class JrysPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self._data = _load()

    # ---------- 主命令 ----------
    @filter_mod.command("今日运势", alias={"运势", "jrys", "jrysprpr"})
    async def fortune(self, event: AstrMessageEvent):
        uid = event.get_sender_id()
        gid = event.get_group_id() or "私聊"
        today = _fortune_date()
        recs = self._data.setdefault(uid, {})

        # 持久化：当天已有记录直接复用（全群同步，0点刷新），只更新所在群
        rec = recs.get(today)
        if rec:
            if rec.get("gid") != gid:
                rec["gid"] = gid
                _save(self._data)
            yield event.plain_result(self._render(rec, first=False))
            return

        rec = self._gen(uid, today, 0)
        rec["gid"] = gid
        rec["rerolls"] = 0
        recs[today] = rec
        self._prune(uid)
        _save(self._data)
        yield event.plain_result(self._render(rec, first=True))

    # ---------- 转运 ----------
    @filter_mod.command("转运", alias={"转运运势", "重抽运势", "重抽", "jrysreroll"})
    async def reroll(self, event: AstrMessageEvent):
        uid = event.get_sender_id()
        today = _fortune_date()
        recs = self._data.setdefault(uid, {})
        rec = recs.get(today)
        if not rec:
            yield event.plain_result("今天还没抽过运势，先发「今日运势」")
            return
        if rec.get("rerolls", 0) >= MAX_REROLL:
            yield event.plain_result(f"今天的转运机会用完了（{MAX_REROLL}次），凌晨 0 点重置")
            return
        used = rec.get("rerolls", 0) + 1
        # 转运小步上升：分数/维度每次最多 +10，只升不降
        nrec = self._gen(uid, today, used, min_score=rec["score"], min_dims=rec["dims"])
        nrec["gid"] = rec.get("gid") or (event.get_group_id() or "私聊")
        nrec["rerolls"] = used
        recs[today] = nrec
        _save(self._data)
        yield event.plain_result(
            f"转运成功（{used}/{MAX_REROLL}），这是你新的今日运势：\n"
            + self._render(nrec, first=False)
        )

    # ---------- 统计 ----------
    @filter_mod.command("运势统计", alias={"jrysstat"})
    async def stat(self, event: AstrMessageEvent):
        uid = event.get_sender_id()
        recs = self._data.get(uid, {})
        items = sorted(recs.items())[-KEEP_DAYS:]
        if len(items) < 2:
            yield event.plain_result("记录还不够，连续抽几天再来统计吧")
            return
        best = max(items, key=lambda kv: kv[1]["score"])
        worst = min(items, key=lambda kv: kv[1]["score"])
        avg = sum(r["score"] for _, r in items) / len(items)
        dist = {lv: sum(1 for _, r in items if r["level"] == lv) for lv, _, _, _ in LEVELS}
        lines = [
            f"📊 近{len(items)}天运势统计",
            f"🏆 最佳：{best[1]['icon']}{best[1]['level']} {best[1]['score']}分（{best[0]}）",
            f"💢 最差：{worst[1]['icon']}{worst[1]['level']} {worst[1]['score']}分（{worst[0]}）",
            f"📈 平均：{avg:.1f}分",
            "等级分布：",
        ]
        for lv, _, _, ic in LEVELS:
            c = dist[lv]
            if c:
                lines.append(f"  {ic}{lv} {'█' * c}{c}天")
        yield event.plain_result("\n".join(lines))

    # ---------- 排行 ----------
    @filter_mod.command("运势排行", alias={"jrysrank", "今日榜"})
    async def rank(self, event: AstrMessageEvent):
        gid = event.get_group_id()
        if not gid:
            yield event.plain_result("排行只有群里能看")
            return
        today = _fortune_date()
        entries = []
        for uid, recs in self._data.items():
            rec = recs.get(today)
            if rec and rec.get("gid") == gid:
                entries.append((rec["score"], uid, rec))
        if not entries:
            yield event.plain_result("今天本群还没人抽过运势，发「今日运势」开抽")
            return
        entries.sort(key=lambda x: x[0], reverse=True)
        lines = ["🏆 本群今日运势榜 TOP3："]
        medals = ["🥇", "🥈", "🥉"]
        for i, (score, uid, rec) in enumerate(entries[:3]):
            lines.append(f"{medals[i]} {uid}：{rec['icon']}{rec['level']} {score}分")
        yield event.plain_result("\n".join(lines))

    # ---------- 帮助 ----------
    @filter_mod.command("运势帮助", alias={"jryshelp"})
    async def help_cmd(self, event: AstrMessageEvent):
        lines = [
            "🎲 运势插件命令：",
            "今日运势 - 查看今日运势",
            "重抽运势 - 重抽一次（每天限1次）",
            "运势统计 - 近30天个人统计",
            "运势排行 - 本群今日TOP3",
        ]
        yield event.plain_result("\n".join(lines))

    # ---------- 内部 ----------
    def _gen(self, uid: str, today: str, salt: int,
             min_score: int | None = None, min_dims: dict | None = None) -> dict:
        rng = random.Random(_seed(uid, today, salt))
        # 转运只小幅上升：每次最多 +10 分（只升不降）；首抽从 0~100 抽
        if min_score is not None:
            score = rng.randint(min_score, min(100, min_score + 10))
        else:
            score = rng.randint(0, 100)
        level_name = icon = ""
        for lv, a, b, ic in LEVELS:
            if a <= score <= b:
                level_name, icon = lv, ic
                break
        if score >= 60:
            comment_pool, motto_pool = COMMENT_GOOD, MOTTOS_GOOD
        elif score < 45:
            comment_pool, motto_pool = COMMENT_BAD, MOTTOS_BAD
        else:
            comment_pool, motto_pool = COMMENT_MID, MOTTOS_MID
        dims = {}
        for d in DIMS:
            if min_dims and d in min_dims:
                lo = min_dims[d]
                dims[d] = rng.randint(lo, min(100, lo + 10))
            else:
                dims[d] = rng.randint(20, 100)
        return {
            "date": today,
            "level": level_name,
            "icon": icon,
            "score": score,
            "dims": dims,
            "color": rng.choice(COLORS),
            "num": rng.randint(1, 99),
            "item": rng.choice(ITEMS),
            "direction": rng.choice(DIRECTIONS),
            "tslot": rng.choice(TIME_SLOTS),
            "keyword": rng.choice(KEYWORDS),
            "yi": rng.sample(YI_POOL, 2),
            "ji": rng.sample(JI_POOL, 2),
            "comment": rng.choice(comment_pool),
            "motto": rng.choice(motto_pool),
        }

    def _prune(self, uid: str):
        """历史只保留最近 KEEP_DAYS 天，防止 data.json 无限膨胀"""
        recs = self._data.get(uid, {})
        if len(recs) <= KEEP_DAYS:
            return
        for d in sorted(recs)[:-KEEP_DAYS]:
            recs.pop(d, None)

    @staticmethod
    def _render(rec: dict, first: bool) -> str:
        tip = "（今日运势已固定，凌晨0点自动刷新）" if not first else ""
        dims = "\n".join(
            f"  {_bar(v)} {k}{v}" for k, v in rec["dims"].items()
        )
        return (
            f"{rec['icon']} 今日运势：{rec['level']}（{rec['score']}分）{tip}\n"
            f"📊 综合 {_bar(rec['score'])} {rec['score']}\n"
            f"{dims}\n"
            f"🎨 幸运色：{rec['color']}　🔢 幸运数字：{rec['num']}\n"
            f"🧭 幸运方位：{rec['direction']}　⏰ 幸运时刻：{rec['tslot']}\n"
            f"🍀 幸运物：{rec['item']}　🔑 今日关键词：{rec['keyword']}\n"
            f"✅ 宜：{'、'.join(rec['yi'])}\n"
            f"⚠️ 忌：{'、'.join(rec['ji'])}\n"
            f"💬 {rec['comment']}\n"
            f"📜 {rec['motto']}\n"
            f"使用 运势帮助 查看命令, 使用 转运 重新抽取今日运势"
        )
