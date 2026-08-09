"""jrysprpr v1.3.0 - 今日运势（丰富版 + 今日特调）
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
from astrbot.api.message_components import Plain, Image as MsgImage
from PIL import Image, ImageDraw, ImageFont

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
KEEP_DAYS = 30    # 历史记录保留天数（统计用）
MAX_REROLL = 3    # 每天转运次数上限
TRANSFER_STEP = 25  # 转运单次最大增幅

# ============ 今日特调：白名单 + 鸡尾酒库 ============
WHITELIST_PATH = os.path.join(BASE_DIR, "whitelist.json")
COCKTAIL_DIR = os.path.join(BASE_DIR, "assets")
FONT_DIR = os.path.join(BASE_DIR, "fonts")
FONT_REG = os.path.join(FONT_DIR, "NotoSansSC-400.ttf")
FONT_BOLD = os.path.join(FONT_DIR, "NotoSansSC-700.ttf")

# 每款：名称/基酒/度数/杯型/配料/做法/装饰/口感/分层颜色(自上而下)/背景渐变(顶->底)
COCKTAILS = [
    {
        "name": "午夜旧金山", "en": "Midnight S.F.", "base": "波本威士忌",
        "abv": 38, "glass": "古典杯",
        "ingredients": ["波本威士忌 45ml", "黑樱桃利口酒 15ml", "鲜柠檬汁 20ml", "糖浆 10ml"],
        "recipe": "所有材料加冰摇匀，滤入冰古典杯，橙皮喷香后投入杯沿。",
        "garnish": "橙皮", "desc": "焦糖与黑樱桃交织，尾韵是烟熏味的深夜。",
        "layers": [(152, 78, 28), (198, 118, 48), (228, 158, 78)],
        "bg": [(12, 16, 34), (2, 3, 8)],
    },
    {
        "name": "醚都霓虹", "en": "Neon Ether", "base": "金酒",
        "abv": 32, "glass": "高球杯",
        "ingredients": ["金酒 40ml", "蓝橙利口酒 20ml", "菠萝汁 30ml", "苏打水 60ml"],
        "recipe": "金酒与蓝橙、菠萝汁摇匀倒入冰杯，苏打水补满，樱桃点缀。",
        "garnish": "樱桃", "desc": "霓虹蓝渐层，喝一口像走进醚都的夜。",
        "layers": [(24, 60, 150), (60, 110, 200), (150, 180, 240)],
        "bg": [(20, 12, 46), (3, 2, 10)],
    },
    {
        "name": "西伯利亚白桦", "en": "Siberian Birch", "base": "伏特加",
        "abv": 40, "glass": "马天尼杯",
        "ingredients": ["伏特加 50ml", "白可可利口酒 15ml", "鲜奶油 20ml", "少许肉桂粉"],
        "recipe": "伏特加与利口酒摇匀，奶油浮面，撒肉桂粉，杯口挂橄榄。",
        "garnish": "橄榄", "desc": "冷冽之下藏着奶香，像冻原上的篝火。",
        "layers": [(240, 240, 246), (215, 222, 235)],
        "bg": [(28, 30, 36), (4, 5, 8)],
    },
    {
        "name": "熔岩之心", "en": "Lava Heart", "base": "龙舌兰",
        "abv": 35, "glass": "岩石杯",
        "ingredients": ["龙舌兰 45ml", "血橙汁 25ml", "红石榴糖浆 10ml", "辣椒盐边"],
        "recipe": "龙舌兰与血橙汁摇匀，石榴糖浆沉底做熔岩层，杯口沾辣椒盐。",
        "garnish": "盐边", "desc": "甜辣交织，血色渐层像熔岩在心口翻涌。",
        "layers": [(168, 22, 30), (224, 82, 40), (240, 168, 60)],
        "bg": [(30, 8, 14), (4, 2, 4)],
    },
    {
        "name": "量子迷雾", "en": "Quantum Haze", "base": "金酒",
        "abv": 30, "glass": "柯林斯杯",
        "ingredients": ["金酒 35ml", "蓝橙利口酒 15ml", "青柠汁 15ml", "汤力水 90ml"],
        "recipe": "金酒、蓝橙、青柠汁摇匀入冰杯，汤力水补满，薄荷轻拍入杯。",
        "garnish": "薄荷", "desc": "观测即坍缩，喝之前它同时是好喝与不好喝。",
        "layers": [(20, 90, 160), (40, 140, 190), (150, 210, 220)],
        "bg": [(8, 26, 30), (2, 5, 8)],
    },
    {
        "name": "虎纹", "en": "Whisky Tiger", "base": "苏格兰威士忌",
        "abv": 42, "glass": "岩石杯",
        "ingredients": ["苏格兰威士忌 50ml", "蜂蜜利口酒 10ml", "烟熏盐少许", "大冰球一枚"],
        "recipe": "威士忌与蜂蜜利口酒轻搅，注入冰球杯，撒烟熏盐。",
        "garnish": "烟熏", "desc": "浓烈斑驳，像虎纹一样不讲道理地好看。",
        "layers": [(120, 62, 20), (168, 92, 32), (200, 122, 48)],
        "bg": [(20, 12, 8), (4, 3, 2)],
    },
    {
        "name": "樱桃悖论", "en": "Cherry Paradox", "base": "白兰地",
        "abv": 34, "glass": "马天尼杯",
        "ingredients": ["白兰地 40ml", "樱桃利口酒 20ml", "柠檬汁 10ml", "糖渍樱桃一颗"],
        "recipe": "所有材料加冰摇匀，双重过滤入冰马天尼杯，樱桃沉底。",
        "garnish": "樱桃", "desc": "甜得明目张胆，苦得不动声色。",
        "layers": [(150, 22, 40), (196, 60, 80), (226, 140, 150)],
        "bg": [(26, 8, 16), (5, 2, 4)],
    },
    {
        "name": "极光之夜", "en": "Aurora Night", "base": "伏特加",
        "abv": 28, "glass": "高球杯",
        "ingredients": ["伏特加 30ml", "蓝橙利口酒 15ml", "青苹果汁 40ml", "可尔必思 20ml"],
        "recipe": "伏特加与蓝橙、青苹果汁摇匀，可尔必思浮面成极光带。",
        "garnish": "纸伞", "desc": "青绿蓝紫在杯里流动，极光只在今晚营业。",
        "layers": [(30, 150, 120), (40, 110, 190), (110, 70, 180)],
        "bg": [(10, 24, 24), (3, 3, 10)],
    },
    {
        "name": "琥珀时间", "en": "Amber Time", "base": "朗姆酒",
        "abv": 36, "glass": "古典杯",
        "ingredients": ["陈年朗姆 45ml", "杏仁利口酒 15ml", "橙苦精 2滴", "方糖一块"],
        "recipe": "方糖置于杯中，苦精浸润后捣化，朗姆与杏仁利口酒搅拌入杯。",
        "garnish": "柠檬", "desc": "时间被琥珀封存，入口是上世纪的老派浪漫。",
        "layers": [(180, 120, 30), (210, 150, 60), (235, 185, 100)],
        "bg": [(22, 14, 6), (4, 3, 2)],
    },
    {
        "name": "雾都低语", "en": "Misty Whispers", "base": "金酒",
        "abv": 31, "glass": "马天尼杯",
        "ingredients": ["伦敦干金酒 45ml", "苦艾酒 15ml", "柑橘皮一片"],
        "recipe": "金酒与苦艾酒冰镇搅拌，滤入冰马天尼杯，柑橘皮喷香。",
        "garnish": "柠檬", "desc": "雾一样的温柔，杯沿有低语般的柑橘香。",
        "layers": [(235, 235, 228), (210, 218, 222)],
        "bg": [(18, 20, 26), (4, 5, 8)],
    },
    {
        "name": "草莓脉搏", "en": "Strawberry Pulse", "base": "伏特加",
        "abv": 27, "glass": "柯林斯杯",
        "ingredients": ["伏特加 30ml", "草莓利口酒 25ml", "鲜草莓 3颗", "柠檬气泡水 80ml"],
        "recipe": "草莓捣碎与伏特加、利口酒摇匀，气泡水补满，整颗草莓点缀。",
        "garnish": "樱桃", "desc": "粉红渐层像心跳，甜度刚好卡在心动阈值。",
        "layers": [(190, 40, 70), (228, 100, 130), (240, 190, 200)],
        "bg": [(24, 8, 18), (5, 2, 5)],
    },
    {
        "name": "黑曜石", "en": "Obsidian", "base": "黑朗姆",
        "abv": 43, "glass": "岩石杯",
        "ingredients": ["黑朗姆 50ml", "咖啡利口酒 15ml", "烟熏海盐", "黑巧克力一片"],
        "recipe": "黑朗姆与咖啡利口酒加冰搅拌，杯口抹烟熏海盐，黑巧搭杯。",
        "garnish": "烟熏", "desc": "黑得发亮，烈得清醒，像打磨过的火山玻璃。",
        "layers": [(18, 14, 24), (40, 28, 60)],
        "bg": [(8, 8, 12), (2, 2, 5)],
    },
]


# 首抽加权：吉及以上占 65%，压低分概率（顺序对应 LEVELS）
SCORE_WEIGHTS = [11, 14, 17, 23, 15, 10, 7, 3]


def _load():
    try:
        if os.path.exists(DATA_PATH):
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:  # noqa: BLE001
        logger.error(f"jrysprpr: 读取 data.json 失败: {e}")
    return {}


def _save(data, path=DATA_PATH):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:  # noqa: BLE001
        logger.error(f"jrysprpr: 保存 {path} 失败: {e}")


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

def _load_whitelist() -> dict:
    """加载今日特调白名单：{"groups": ["群号", ...]}"""
    try:
        if os.path.exists(WHITELIST_PATH):
            with open(WHITELIST_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:  # noqa: BLE001
        logger.error(f"jrysprpr: 读取白名单失败: {e}")
    return {"groups": []}


def _today_cocktail(today: str) -> dict:
    """按日期确定性选酒：全群每日同一杯"""
    idx = int(hashlib.md5(f"jrys:special:{today}".encode()).hexdigest()[:8], 16) % len(COCKTAILS)
    return COCKTAILS[idx]


def _render_special(ck: dict, today: str) -> str:
    _, m, d = today.split("-")
    ing = "\n".join(f"・{i}" for i in ck["ingredients"])
    return (
        f"🍸 今日特调｜{int(m)}月{int(d)}日（全群每日相同）\n"
        f"━━━━━━━━━━━━━━\n"
        f"「{ck['name']}」 {ck['en']}\n"
        f"基酒：{ck['base']}　｜　{ck['abv']}% vol　｜　{ck['glass']}\n"
        f"━━━━━━━━━━━━━━\n"
        f"🧪 配料：\n{ing}\n"
        f"🫗 做法：{ck['recipe']}\n"
        f"👅 口感：{ck['desc']}\n"
        f"━━━━━━━━━━━━━━\n"
        f"— 醚都城 · 威廉酒馆特供 —"
    )


@register("jrysprpr", "扎恩斯", "今日运势：多群同步/0点刷新/统计/排行/转运，数据持久化", "1.3.0")
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
            yield event.plain_result(self._render(rec, first=False) + self._whitelist_tip(gid))
            return

        rec = self._gen(uid, today, 0)
        rec["gid"] = gid
        rec["rerolls"] = 0
        recs[today] = rec
        self._prune(uid)
        _save(self._data)
        yield event.plain_result(self._render(rec, first=True) + self._whitelist_tip(gid))

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
        # 转运上升：分数/维度每次最多 +25，只升不降
        # 低运保底：底线随剩余次数逐次抬升，保证最后一次转运后 70+ 分
        rem = MAX_REROLL - used  # 本次之后还剩几次转运
        floor = max(rec["score"], 70 - rem * 10)
        nrec = self._gen(uid, today, used, min_score=rec["score"],
                         min_dims=rec["dims"], floor=floor)
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
            "今日特调 - 白名单群专属调酒（含配方与图）",
            "特调菜单 - 查看特调酒单（白名单群）",
        ]
        yield event.plain_result("\n".join(lines))

    # ---------- 今日特调（白名单群专属） ----------
    @filter_mod.command("今日特调", alias={"特调", "jt", "jrys_t"})
    async def special(self, event: AstrMessageEvent):
        gid = event.get_group_id()
        if not gid:
            yield event.plain_result("「今日特调」是群功能，私聊不开放")
            return
        if not self._is_whitelisted(gid):
            yield event.plain_result(
                "本群未开通「今日特调」\n"
                "此功能为大扎群专属，需将群号加入白名单。\n"
                "（管理员可发送：特调白名单 add 群号）"
            )
            return
        today = _fortune_date()
        ck = _today_cocktail(today)
        img_path = _ensure_cocktail_image(ck, today)
        yield event.chain_result([Plain(_render_special(ck, today)), MsgImage(img_path)])

    # ---------- 特调菜单 ----------
    @filter_mod.command("特调菜单", alias={"酒单", "jrysmenu"})
    async def special_menu(self, event: AstrMessageEvent):
        gid = event.get_group_id()
        if not gid:
            yield event.plain_result("「特调菜单」是群功能")
            return
        if not self._is_whitelisted(gid):
            yield event.plain_result("本群未开通「今日特调」，无法查看菜单")
            return
        lines = ["🍸 醚都城·威廉酒馆 特调酒单：", ""]
        for i, c in enumerate(COCKTAILS, 1):
            lines.append(f"{i:02d}. {c['name']} {c['en']} ｜ {c['abv']}% vol ｜ {c['glass']}")
        lines += ["", "发送「今日特调」获取今日随机一杯（全群每日相同）"]
        yield event.plain_result("\n".join(lines))

    # ---------- 白名单管理 ----------
    @filter_mod.command("特调白名单", alias={"jrys_wl"})
    async def special_whitelist(self, event: AstrMessageEvent):
        parts = event.message_str.split()
        if len(parts) == 1:
            groups = _load_whitelist().get("groups", [])
            if not groups:
                yield event.plain_result("当前白名单为空\n用法：特调白名单 add 群号 / del 群号")
            else:
                yield event.plain_result("当前「今日特调」白名单群：\n" + "\n".join(groups))
            return
        op = parts[1].lower()
        gid = parts[2] if len(parts) > 2 else ""
        if op not in ("add", "del"):
            yield event.plain_result("用法：特调白名单 add 群号 / del 群号")
            return
        if not gid.isdigit():
            yield event.plain_result("群号格式不对，应为纯数字")
            return
        groups = _load_whitelist()
        if op == "add":
            if gid in groups["groups"]:
                yield event.plain_result(f"{gid} 已在白名单中")
            else:
                groups["groups"].append(gid)
                _save(groups, WHITELIST_PATH)
                yield event.plain_result(f"已添加 {gid}，该群解锁「今日特调」")
        else:
            if gid in groups["groups"]:
                groups["groups"].remove(gid)
                _save(groups, WHITELIST_PATH)
                yield event.plain_result(f"已移除 {gid} 的白名单")
            else:
                yield event.plain_result(f"{gid} 不在白名单中")

    # ---------- 内部 ----------
    def _gen(self, uid: str, today: str, salt: int,
             min_score: int | None = None, min_dims: dict | None = None,
             floor: int | None = None) -> dict:
        rng = random.Random(_seed(uid, today, salt))
        # 转运上升：每次最多 +25 分（只升不降）；首抽加权偏吉
        if min_score is not None:
            score = rng.randint(min_score, min(100, min_score + TRANSFER_STEP))
        else:
            score = self._roll_score(rng)
        # 低运保底：分数至少抬到 floor（保证最后能及格）
        if floor is not None:
            score = max(score, min(100, floor))
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
                dims[d] = rng.randint(lo, min(100, lo + TRANSFER_STEP))
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

    @staticmethod
    def _roll_score(rng: random.Random) -> int:
        """加权抽分：先按权重选档，再在档内随机。吉及以上约 60%，低分被压低"""
        idx = rng.choices(range(len(LEVELS)), weights=SCORE_WEIGHTS)[0]
        lo, hi = LEVELS[idx][1], LEVELS[idx][2]
        return rng.randint(lo, hi)

    def _prune(self, uid: str):
        """历史只保留最近 KEEP_DAYS 天，防止 data.json 无限膨胀"""
        recs = self._data.get(uid, {})
        if len(recs) <= KEEP_DAYS:
            return
        for d in sorted(recs)[:-KEEP_DAYS]:
            recs.pop(d, None)

    def _is_whitelisted(self, gid: str) -> bool:
        return str(gid) in _load_whitelist().get("groups", [])

    def _whitelist_tip(self, gid: str) -> str:
        if self._is_whitelisted(gid):
            return "\n🍸 本群已解锁「今日特调」，发送 今日特调 获取今日特调鸡尾酒"
        return ""

    @staticmethod
    def _render(rec: dict, first: bool) -> str:
        tip = ""
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
            f"使用 运势帮助 查看命令, 使用 转运 重新抽取今日运势\n"
            f"（仅供娱乐，理性看待）"
        )

# ============ 今日特调：绘图 ============
def _ensure_cocktail_image(ck: dict, today: str) -> str:
    """按日期缓存图片：special_YYYY-MM-DD.png"""
    os.makedirs(COCKTAIL_DIR, exist_ok=True)
    fname = f"special_{today}.png"
    path = os.path.join(COCKTAIL_DIR, fname)
    if os.path.exists(path):
        return path
    draw_cocktail(ck, path)
    return path


def _font(size: int, bold: bool = False):
    try:
        return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)
    except Exception:  # noqa: BLE001
        return ImageFont.load_default()


def draw_cocktail(ck: dict, path: str):
    W, H = 800, 1000
    bg_top, bg_bot = ck["bg"]
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    # 背景竖向渐变
    for y in range(H):
        t = y / H
        c = tuple(int(bg_top[i] + (bg_bot[i] - bg_top[i]) * t) for i in range(3))
        d.line([(0, y), (W, y)], fill=c)

    # 星点（按酒名播种，每杯稳定）
    rng = random.Random(ck["name"])
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    do = ImageDraw.Draw(ov)
    for _ in range(150):
        x, y = rng.randint(0, W - 1), rng.randint(0, int(H * 0.5))
        r = rng.choice([1, 1, 2, 2, 3])
        a = rng.randint(40, 120)
        do.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, a))
    img = Image.alpha_composite(img.convert("RGBA"), ov)
    d = ImageDraw.Draw(img)

    # 杯身几何
    cx = W // 2
    mouth_w, base_w = 340, 130
    g_top, g_bot = 300, 740
    lx0, rx0 = cx - mouth_w // 2, cx + mouth_w // 2
    lx1, rx1 = cx - base_w // 2, cx + base_w // 2

    # 液体分层
    liq_top = g_top + 26
    liq_h = g_bot - liq_top - 6
    layers = ck["layers"]
    seg = liq_h / len(layers)
    for i, col in enumerate(layers):
        y0 = liq_top + i * seg
        y1 = y0 + seg
        t0 = (y0 - g_top) / (g_bot - g_top)
        t1 = (y1 - g_top) / (g_bot - g_top)
        w0 = mouth_w + (base_w - mouth_w) * t0
        w1 = mouth_w + (base_w - mouth_w) * t1
        x0l, x0r = cx - w0 / 2, cx + w0 / 2
        x1l, x1r = cx - w1 / 2, cx + w1 / 2
        d.polygon([(x0l, y0), (x0r, y0), (x1r, y1), (x1l, y1)], fill=col)

    # 液体高光
    hx = cx - 58
    for y in range(liq_top, g_bot - 6):
        t = (y - g_top) / (g_bot - g_top)
        w = mouth_w + (base_w - mouth_w) * t
        if abs(hx - cx) < w / 2:
            a = max(0, 110 - int((y - liq_top) * 0.22))
            d.line([(hx, y), (hx + 12, y)], fill=(255, 255, 255, a))

    # 杯身描边
    d.line([(lx0, g_top), (lx1, g_bot)], fill=(255, 255, 255, 170), width=4)
    d.line([(rx0, g_top), (rx1, g_bot)], fill=(255, 255, 255, 170), width=4)
    d.line([(lx0, g_top), (rx0, g_top)], fill=(255, 255, 255, 210), width=6)
    d.line([(lx1, g_bot), (rx1, g_bot)], fill=(255, 255, 255, 150), width=4)

    # 杯脚与底座
    d.line([(cx, g_bot), (cx, 832)], fill=(255, 255, 255, 160), width=16)
    d.ellipse([cx - 125, 848, cx + 125, 890], outline=(255, 255, 255, 180), width=5)
    d.ellipse([cx - 72, 856, cx + 72, 882], fill=(255, 255, 255, 46))

    _draw_garnish(d, ck["garnish"], cx, g_top, mouth_w, rng)

    # 文字
    f_sm = _font(20)
    f_bold = _font(62, bold=True)
    f_reg = _font(27)
    f_xs = _font(17)
    t1 = "TODAY'S SPECIAL · 今日特调"
    w1 = d.textlength(t1, font=f_sm)
    d.text(((W - w1) / 2, 92), t1, font=f_sm, fill=(255, 255, 255, 190))
    name = ck["name"]
    w2 = d.textlength(name, font=f_bold)
    d.text(((W - w2) / 2 + 3, 138 + 3), name, font=f_bold, fill=(0, 0, 0, 150))
    d.text(((W - w2) / 2, 138), name, font=f_bold, fill=(255, 255, 255, 255))
    sub = f"{ck['en']}  ｜  {ck['abv']}% vol  ｜  {ck['glass']}"
    w3 = d.textlength(sub, font=f_reg)
    d.text(((W - w3) / 2, 226), sub, font=f_reg, fill=(255, 255, 255, 215))
    t2 = "AETHER CITY BAR · WILLIAM'S PUB · EST. 2026"
    w4 = d.textlength(t2, font=f_xs)
    d.text(((W - w4) / 2, 942), t2, font=f_xs, fill=(255, 255, 255, 120))

    img.save(path, "PNG")


def _draw_garnish(d: ImageDraw.ImageDraw, kind: str, cx: int, g_top: int, mouth_w: int, rng: random.Random):
    """按装饰类型绘制杯口/杯中装饰"""
    lx = cx - mouth_w // 2
    rx = cx + mouth_w // 2
    if "柠檬" in kind:
        # 杯口左缘挂柠檬片
        r = 52
        cxy = (lx + 26, g_top + 34)
        d.ellipse([cxy[0] - r, cxy[1] - r, cxy[0] + r, cxy[1] + r], fill=(245, 210, 60), outline=(235, 180, 40), width=5)
        d.ellipse([cxy[0] - 34, cxy[1] - 34, cxy[0] + 34, cxy[1] + 34], fill=(250, 230, 120))
        for i in range(8):
            ang = i * 45
            import math
            x0 = cxy[0] + 10 * math.cos(math.radians(ang))
            y0 = cxy[1] + 10 * math.sin(math.radians(ang))
            x1 = cxy[0] + 40 * math.cos(math.radians(ang))
            y1 = cxy[1] + 40 * math.sin(math.radians(ang))
            d.line([(x0, y0), (x1, y1)], fill=(245, 200, 70), width=3)
    elif "橙皮" in kind:
        # 杯口悬橙皮条
        pts = [(rx - 10, g_top + 20), (rx + 30, g_top + 70), (rx + 4, g_top + 120), (rx + 34, g_top + 168)]
        d.line(pts, fill=(250, 150, 40), width=16)
        d.line(pts, fill=(255, 190, 90), width=6)
    elif "樱桃" in kind:
        # 杯中沉樱桃
        for _ in range(2):
            x = cx + rng.randint(-60, 60)
            y = g_top + 130 + rng.randint(0, 120)
            r = 20
            d.ellipse([x - r, y - r, x + r, y + r], fill=(200, 30, 50), outline=(140, 16, 32), width=3)
            d.ellipse([x - 8, y - 8, x + 8, y + 8], fill=(255, 120, 130))
            d.line([(x, y - r), (x + 12, y - r - 26)], fill=(60, 140, 70), width=4)
    elif "薄荷" in kind:
        # 杯口绿叶
        for i, (dx, dy, rr) in enumerate([(-14, 2, 34), (8, -8, 30), (30, 4, 26)]):
            x, y = cx + dx, g_top + 6 + dy
            d.ellipse([x - rr, y - rr * 0.6, x + rr, y + rr * 0.6], fill=(50, 150, 80), outline=(30, 110, 60), width=3)
            d.line([(x - rr, y), (x + rr, y)], fill=(30, 110, 60), width=3)
    elif "橄榄" in kind:
        # 杯口插橄榄签
        d.line([(cx, g_top - 10), (cx + 40, g_top + 90)], fill=(200, 190, 170), width=5)
        x, y = cx + 40, g_top + 90
        d.ellipse([x - 16, y - 12, x + 16, y + 12], fill=(120, 160, 90), outline=(80, 120, 60), width=3)
        d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(200, 60, 60))
    elif "盐边" in kind:
        # 杯口盐边：白色细点
        y = g_top
        for x in range(lx - 8, cx + mouth_w // 2 + 10, 8):
            rr = rng.randint(3, 6)
            d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(255, 255, 255, 200))
    elif "纸伞" in kind:
        # 杯口插小纸伞
        sx, sy = cx + 40, g_top - 6
        d.line([(sx, sy), (sx - 8, sy + 110)], fill=(160, 140, 110), width=5)
        pts = [(sx - 60, sy - 8), (sx + 60, sy - 8), (sx, sy - 58)]
        d.polygon(pts, fill=(230, 80, 90), outline=(180, 50, 60))
        d.line([(sx - 60, sy - 8), (sx + 60, sy - 8)], fill=(180, 50, 60), width=3)
        d.line([(sx, sy - 8), (sx, sy - 56)], fill=(255, 200, 200), width=2)
    elif "烟熏" in kind:
        # 杯口飘烟
        for i in range(4):
            x0 = cx + rng.randint(-50, 50)
            y0 = g_top + 10
            pts = [(x0, y0), (x0 + rng.randint(-30, 30), y0 - 30),
                   (x0 + rng.randint(-50, 50), y0 - 62), (x0 + rng.randint(-30, 30), y0 - 96)]
            d.line(pts, fill=(220, 220, 230, 90), width=rng.randint(6, 10))
    else:
        pass
