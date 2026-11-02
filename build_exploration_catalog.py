#!/usr/bin/env python3
"""Build the exploration, sea-monster, and navigation-event catalogue from this ROM."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
ROM_PATH = ROOT / "rom-investigation/4110423.original.bin"
OUT_PATH = Path(__file__).with_name("data") / "exploration-catalog.json"

# Names transcribed from the ROM's own text glyphs. The coordinate table stores
# map pixels and a discovery rating, but the ROM has no long-form descriptions.
DISCOVERY_NAMES = [
    "斯通亨奇巨石阵", "罗塞塔石碑", "胡夫金字塔", "大鳄鱼", "努比亚金字塔",
    "梯斯塞特瀑布", "努瓦人", "禽龙", "维多利亚湖", "迪奥戈石碑",
    "达贡人", "马查意人", "犰狳", "斑鸠", "俾格米人", "瓜尔格人",
    "迪亚士石碑", "津巴布韦土著", "山魈", "渡渡鸟", "变色龙", "纸莎草",
    "燃水", "摩亨约达罗", "眼镜王蛇", "东南亚矮人", "释迦牟尼佛像", "犀鸟",
    "吴哥窟", "迦陵频伽", "冬虫夏草", "登吕遗迹", "剥鬼", "乾陵",
    "万里长城", "刺猬", "熊猫", "候鸽", "印第安人", "翡翠面具",
    "瓜达维拉湖", "仙人掌", "髭龟", "捕蝇草", "尼亚加拉大瀑布", "王莲",
    "森蚺", "亚马逊河涌潮", "鬣蜥", "苇草筏", "颠茄", "狼蛛", "水虎鱼",
    "金蛙", "巨嘴鸟", "怪兽泥像", "大树懒", "食蚁兽", "企鹅", "吸血蝙蝠",
    "的的喀喀湖", "蒂瓦纳神庙遗迹", "梯拉可拓神像", "巨型石球", "马尔尼克壁画",
    "德累斯顿手抄本", "水晶头骨", "石头人像", "太阳历石", "毒蜥", "北美野牛",
    "土拨鼠", "波拉布德佛殿", "网纹蟒蛇", "科摩多巨蜥", "阿波吉尼人", "皱皮蜥蜴",
    "艾丽斯岩", "塔斯马尼亚恶魔", "考拉", "无翼鸟", "极乐鸟", "火山岩大佛",
    "猪笼草", "天堂树蛇", "伊洛哥特人", "恐鸟", "格陵兰海鸟", "极光", "海牛",
    "爱斯基摩人", "猛犸象", "剑齿虎", "拉德罗纳人", "虎斑宝贝", "鼻行兽",
    "加拉帕戈斯巨龟", "巨人石像", "彗星", "荷兰风车", "圣瓦西里大教堂",
    "亚马逊战士", "古罗马竞技场", "帕特农神庙", "狮身人面像", "萨夫罗金字塔",
    "猴面包树", "粘土清真寺", "泰姬陵", "卡提夫绿洲", "仰光大金塔",
    "珠穆朗玛峰", "蓝鲸", "椰子树", "果蝠", "长信宫灯", "太阳神鸟金箔",
    "黄鹤楼", "战国水晶杯", "蒙古包", "黄果树瀑布", "钱塘江大潮", "布达拉宫",
    "天坛", "奥古布古水怪", "始祖鸟", "库库尔坎金字塔", "马丘比丘", "纳斯卡线条",
    "月虹", "围猎场", "袋鼠", "榴莲", "白头鹰", "大猩猩", "河马", "食蛇鹫",
    "犀牛鸟", "人鱼", "袋狼", "火烈鸟", "穿山甲", "金缕玉衣", "鸭嘴兽",
    "亚瑟王的圣杯", "空棘鱼", "湿婆神像", "海怪", "河童", "野人", "长颈鹿",
]

ANIMALS = {
    3, 7, 12, 13, 18, 19, 20, 24, 27, 35, 36, 37, 42, 48, 52, 53, 54, 57, 58,
    59, 69, 70, 71, 73, 74, 76, 78, 79, 80, 81, 84, 86, 87, 89, 91, 92, 94, 95,
    96, 101, 112, 114, 125, 131, 133, 134, 135, 136, 137, 138, 139, 140, 141, 143,
    145, 150,
}
PLANTS = {21, 30, 41, 43, 45, 50, 83, 106, 113, 132}
PEOPLE = {6, 10, 11, 14, 15, 17, 25, 32, 38, 75, 85, 90, 93}
GEOGRAPHY = {5, 8, 22, 40, 44, 47, 60, 88, 98, 109, 111, 120, 121, 129}
ARTIFACTS = {1, 9, 16, 26, 39, 49, 63, 64, 65, 66, 67, 68, 97, 115, 116, 118, 119, 142, 144, 146}
MYTHS = {29, 55, 62, 124, 147, 148, 149}
ARCHAEOLOGY = {
    0, 2, 4, 23, 28, 31, 33, 34, 61, 72, 99, 100, 102, 104, 105, 107, 108, 110,
    117, 122, 123, 126, 127, 128, 130,
}


def coordinate_label(latitude: float, longitude: float) -> str:
    lat = f"{abs(latitude):.1f}°{'N' if latitude >= 0 else 'S'}"
    lon = f"{abs(longitude):.1f}°{'E' if longitude >= 0 else 'W'}"
    return f"{lat}, {lon}"


def discovery_category(index: int) -> str:
    if index in ANIMALS:
        return "动物"
    if index in PLANTS:
        return "植物"
    if index in PEOPLE:
        return "族群与人文"
    if index in GEOGRAPHY:
        return "地理与天象"
    if index in ARTIFACTS:
        return "文物与器物"
    if index in MYTHS:
        return "传说与神秘生物"
    if index in ARCHAEOLOGY:
        return "遗迹与建筑"
    return "其他发现"


def discovery_description(name: str, category: str) -> str:
    category_text = {
        "动物": "动物类探索发现",
        "植物": "植物类探索发现",
        "族群与人文": "族群或人文类探索发现",
        "地理与天象": "自然地理或天象类探索发现",
        "文物与器物": "文物、器物或艺术类探索发现",
        "传说与神秘生物": "传说或神秘生物类探索发现",
        "遗迹与建筑": "遗址、历史建筑或人工地标类探索发现",
        "其他发现": "探索发现",
    }[category]
    return f"{name}：{category_text}。此简述按 ROM 名称归类；游戏数据只保存名称、坐标和评价值，没有独立长描述。"


def main() -> None:
    rom = ROM_PATH.read_bytes()
    assert len(DISCOVERY_NAMES) == 151
    assert len(rom) >= 0x1B5BF0 + len(DISCOVERY_NAMES) * 6
    records = []
    for index, name in enumerate(DISCOVERY_NAMES):
        offset = 0x1B5BF0 + index * 6
        x = int.from_bytes(rom[offset : offset + 2], "big", signed=True)
        y = int.from_bytes(rom[offset + 2 : offset + 4], "big", signed=True)
        rating = rom[offset + 5]
        longitude = (x / 6 - 29 + 180) % 360 - 180
        latitude = 90 - y / 7
        category = discovery_category(index)
        records.append(
            {
                "id": index,
                "name": name,
                "kind": "发现物",
                "category": category,
                "description": discovery_description(name, category),
                "mapX": x,
                "mapY": y,
                "latitude": round(latitude, 4),
                "longitude": round(longitude, 4),
                "coordinateLabel": coordinate_label(latitude, longitude),
                "rating": rating,
                "locationBasis": "ROM 发现物坐标表 0x1B5BF0 + ID×6；地图像素按经度每度 6 格、纬度每度 7 格换算。",
            }
        )

    sea_spots = [
        (3, 176, 601), (9, 241, 148), (8, 477, 789), (8, 585, 919),
        (3, 950, 440), (3, 1088, 808), (8, 1221, 95), (8, 1235, 891),
        (8, 1358, 205), (9, 1502, 620), (9, 1744, 1060), (3, 1844, 597),
        (9, 1905, 538),
    ]
    for index, (event_type, x, y) in enumerate(sea_spots, start=1):
        longitude = (x / 6 - 29 + 180) % 360 - 180
        latitude = 90 - y / 7
        records.append(
            {
                "id": 150 + index,
                "name": f"海怪遭遇点 {index:02d}",
                "kind": "海怪",
                "category": f"海图事件类型 {event_type}",
                "description": f"ROM 海图中固定标记的海怪遭遇点（事件类型 {event_type}）。现有静态证据未能把该编号可靠映射到单一怪物名称；具体遭遇以游戏事件文本为准。",
                "mapX": x,
                "mapY": y,
                "latitude": round(latitude, 4),
                "longitude": round(longitude, 4),
                "coordinateLabel": coordinate_label(latitude, longitude),
                "eventType": event_type,
                "locationBasis": "ROM 海图事件点静态坐标；经纬度由地图像素换算。触发范围可能受游戏判定格影响。",
            }
        )

    hazards = [
        ("磁场与罗盘异常", "航海异常", 0x150, "航海文本提示地磁异常、罗盘失灵，并伴随船只失踪的描述；此条文本没有给出固定坐标。"),
        ("能见度异常", "航海异常", 0x151, "航海文本提示无法看见目标船只；没有发现与此文本绑定的固定坐标。"),
        ("暴风雨天气", "自然灾害", 0x154, "航海文本提示天色突变并可能出现暴风雨；没有发现与此文本绑定的固定坐标。"),
        ("异常平静海面", "自然现象", 0x158, "航海文本描述海面风平浪静；没有发现与此文本绑定的固定坐标。"),
        ("浓雾天气", "自然灾害", 0x15C, "航海文本提示周围湿气很重、可能起雾；没有发现与此文本绑定的固定坐标。"),
    ]
    for index, (name, category, message_id, description) in enumerate(hazards, start=1):
        records.append(
            {
                "id": 300 + index,
                "name": name,
                "kind": "自然灾害/航海异常",
                "category": category,
                "description": description,
                "mapX": None,
                "mapY": None,
                "latitude": None,
                "longitude": None,
                "coordinateLabel": "无固定坐标",
                "messageId": f"0x{message_id:03X}",
                "locationBasis": "ROM 航海事件文本；当前证据没有可核实的固定地图坐标。",
            }
        )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT_PATH} ({len(records)} records: {len(DISCOVERY_NAMES)} discoveries, {len(sea_spots)} sea-monster points, {len(hazards)} navigation events)")
    print(f"coordinate sanity: Stonehenge={records[0]['coordinateLabel']}, Rosetta={records[1]['coordinateLabel']}, Pyramids={records[2]['coordinateLabel']}")


if __name__ == "__main__":
    main()
