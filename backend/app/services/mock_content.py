"""离线 mock 内容生成：无 API key 也能跑通完整流水线，用于开发/验收。"""

import random

GENRE_TEMPLATES = {
    "都市复仇": {
        "title_prefix": "复仇",
        "audience": "追求强爽感与身份反转的观众",
        "tone": "冷峻都市风，深蓝与黑金色调，雨夜霓虹，高对比光影",
        "engine": "主角每次夺回一样被夺走的东西，都会揭开更大一层的幕后黑手",
        "locations": [
            {"name": "顶层办公室", "visual": "落地玻璃幕墙，俯瞰城市夜景，冷白灯光"},
            {"name": "地下停车场", "visual": "昏暗荧光灯，潮湿地面，回音明显"},
            {"name": "老宅", "visual": "陈旧木质结构，暖黄台灯，灰尘弥漫"},
        ],
    },
    "男频逆袭": {
        "title_prefix": "觉醒",
        "audience": "喜欢成长与实力打脸的观众",
        "tone": "热血玄幻风，金红主色调，灵气光效，厚重质感",
        "engine": "主角每突破一层境界，都会引来更强的对手与更深的宗门阴谋",
        "locations": [
            {"name": "宗门演武场", "visual": "石台广场，旌旗猎猎，晨光斜射"},
            {"name": "秘境入口", "visual": "巨大石门，符文流转，雾气弥漫"},
            {"name": "藏经阁", "visual": "层层书架，烛火摇曳，阴影交错"},
        ],
    },
    "女频甜宠": {
        "title_prefix": "心动",
        "audience": "喜欢双向奔赴与治愈感的观众",
        "tone": "明亮浪漫风，奶油白与樱花粉主调，柔和逆光，轻快节奏",
        "engine": "男女主每次误会解除，都会遇到一个考验信任的新事件",
        "locations": [
            {"name": "海边咖啡厅", "visual": "落地窗，海风轻拂，暖阳洒在桌面"},
            {"name": "樱花大道", "visual": "樱花纷落，粉色花瓣铺满路面"},
            {"name": "顶楼天台", "visual": "城市晚霞，霓虹渐亮，微风"},
        ],
    },
    "悬疑规则": {
        "title_prefix": "迷局",
        "audience": "喜欢解谜与规则怪的观众",
        "tone": "冷调悬疑风，青灰与暗红主色，低照度，潮湿质感",
        "engine": "主角每破解一条规则，就会触发一条更危险的隐藏规则",
        "locations": [
            {"name": "废弃医院", "visual": "剥落墙皮，忽明忽暗的日光灯，消毒水味"},
            {"name": "老式电梯", "visual": "锈蚀轿厢，楼层按键闪烁"},
            {"name": "档案室", "visual": "密集铁柜，昏黄台灯，尘封卷宗"},
        ],
    },
}

NAME_POOL = {
    "都市复仇": {"male": ["沈砚", "陆沉", "顾言"], "female": ["林晚", "苏念", "江离"]},
    "男频逆袭": {"male": ["叶尘", "秦渊", "萧炎"], "female": ["云璃", "洛璃", "白月"]},
    "女频甜宠": {"male": ["陆之珩", "裴行舟", "沈辞"], "female": ["温言", "顾瑶", "林之夏"]},
    "悬疑规则": {"male": ["周野", "韩烬", "许深"], "female": ["姜黎", "阮清", "程一"]},
}

VOICE_NOTES = {
    "主角": "青年，普通话，冷静克制，情绪有起伏",
    "对手": "中年男性，普通话，声音沙哑，阴鸷缓慢",
    "盟友": "青年，普通话，爽朗轻快",
    "幕后黑手": "老年男性，普通话，低沉缓慢，压迫感强",
}

DIALOGUE_POOL = {
    "都市复仇": [
        ("林晚", "你拿走的一切，我会一样一样讨回来。"),
        ("沈砚", "这么多年，你终于敢站在我面前了。"),
        ("林晚", "不是敢，是时候到了。"),
        ("陆沉", "你以为凭你一个人，能翻得了这天？"),
        ("林晚", "那就试试看。"),
    ],
    "男频逆袭": [
        ("叶尘", "这一掌，是你欠我的。"),
        ("秦渊", "区区凡人，也敢挑衅宗门？"),
        ("叶尘", "凡人？今天之后，你会记住这个名字。"),
        ("云璃", "我等你回来。"),
        ("叶尘", "等我，踏平这座山。"),
    ],
    "女频甜宠": [
        ("温言", "你怎么又来了？"),
        ("陆之珩", "因为你在的地方，我想来就来。"),
        ("温言", "油嘴滑舌。"),
        ("陆之珩", "只对你一个人油嘴滑舌。"),
        ("温言", "……那，留下来吃饭吧。"),
    ],
    "悬疑规则": [
        ("姜黎", "规则第一条：天黑之后，不要看镜子。"),
        ("周野", "你怎么不早说？"),
        ("姜黎", "因为第二条规则是，说出规则的人，会成为下一个目标。"),
        ("周野", "那我们现在怎么办？"),
        ("姜黎", "跑。"),
    ],
}

CAMERA_MOVES = ["缓慢推镜", "跟拍", "固定机位微摇", "环绕半圈", "快速拉近"]


def pick_genre() -> str:
    return random.choice(list(GENRE_TEMPLATES))


def make_series(idea: str = "", genre: str = "", episode_count: int = 1) -> dict:
    genre = genre or pick_genre()
    tpl = GENRE_TEMPLATES[genre]
    names = NAME_POOL[genre]
    is_female = genre in ("女频甜宠",)
    lead = names["female"][0] if is_female else names["male"][0]
    rival = names["male"][1] if is_female else names["male"][1]
    title = f"{tpl['title_prefix']}{random.randint(10, 99)}：{lead}的{genre[:2]}"
    logline = idea.strip() or f"{lead}被迫失去一切，靠{tpl['engine'].split('每次')[1][:12]}卷土重来，向{tpl['engine']}"
    return {
        "title": title,
        "logline": logline[:200],
        "genre": genre,
        "audience": tpl["audience"],
        "tone": tpl["tone"],
        "conflict_engine": tpl["engine"],
        "season_arc": f"第1季共{episode_count}集：主角从谷底起步，每集夺回一部分失去的东西，最终揭开幕后主使。",
        "first_three_episodes": ["第一集：失去一切，绝地反击", "第二集：第一次反击，代价显现", "第三集：敌人升级，盟友登场"],
        "locations": tpl["locations"],
        "characters_hint": f"主角 {lead}；对手 {rival}；另有配角和幕后黑手。",
    }


def make_characters(series: dict) -> dict:
    genre = series.get("genre", "都市复仇")
    names = NAME_POOL[genre]
    is_female = genre in ("女频甜宠",)
    lead_name = names["female"][0] if is_female else names["male"][0]
    rival_name = names["male"][1] if is_female else names["male"][1]
    characters = [
        {
            "id": "lead",
            "name": lead_name,
            "role": "主角",
            "age": 26,
            "gender": "女" if is_female else "男",
            "desire": "夺回被夺走的一切，并揭开真相",
            "wound": "曾经信任的人背叛，失去家业与尊严",
            "leverage": "掌握一份足以翻盘的秘密证据",
            "personality": "隐忍、果决，外冷内热",
            "dialogue_style": "短句、克制、有锋芒",
            "visual_anchor": {
                "face": "轮廓清晰，黑色直发/利落短发",
                "body": "高挑，气场强",
                "wardrobe": "深色大衣/玄色劲装",
                "props": "一枚旧怀表/一枚玉佩",
                "palette": "黑、金、深蓝",
                "invariants": ["发型不变", "标志性配饰不变"],
            },
        },
        {
            "id": "rival",
            "name": rival_name,
            "role": "对手",
            "age": 32,
            "gender": "男",
            "desire": "巩固地位，阻止主角翻盘",
            "wound": "出身卑微，靠不光彩手段上位",
            "leverage": "握有主角当年被迫签下的协议",
            "personality": "冷静、多疑、笑里藏刀",
            "dialogue_style": "绵里藏针，表面客气",
            "visual_anchor": {
                "face": "剑眉，眼神锐利",
                "body": "挺拔",
                "wardrobe": "深色西装/宗门长老袍",
                "props": "金丝眼镜/折扇",
                "palette": "黑、暗红",
                "invariants": ["眉形与眼神不变"],
            },
        },
        {
            "id": "ally",
            "name": names["female"][1],
            "role": "盟友",
            "age": 24,
            "gender": "女",
            "desire": "帮助主角并找回自己的价值",
            "wound": "曾经被家族放弃",
            "leverage": "掌握关键情报网",
            "personality": "机灵、仗义、嘴硬心软",
            "dialogue_style": "活泼、直率",
            "visual_anchor": {
                "face": "圆脸/清秀，笑眼",
                "body": "中等",
                "wardrobe": "浅色休闲装/月白长裙",
                "props": "手机/储物袋",
                "palette": "白、浅蓝",
                "invariants": ["笑容特征不变"],
            },
        },
        {
            "id": "boss",
            "name": names["male"][2],
            "role": "幕后黑手",
            "age": 50,
            "gender": "男",
            "desire": "维持旧的利益格局",
            "wound": "害怕被时代抛弃",
            "leverage": "掌控整个局面的最终手段",
            "personality": "深不可测，极少露面",
            "dialogue_style": "低沉、慢、压迫感",
            "visual_anchor": {
                "face": "灰发，面容威严",
                "body": "微胖/高大",
                "wardrobe": "长款深色大衣/玄袍",
                "props": "手杖/古书",
                "palette": "暗灰、紫黑",
                "invariants": ["灰发不变"],
            },
        },
    ]
    voice_notes = {c["name"]: VOICE_NOTES[c["role"]] for c in characters}
    return {
        "characters": characters,
        "cast_rules": "主角与对手每集必出场；盟友第2集登场；幕后黑手每3集露一次面。",
        "voice_notes": voice_notes,
    }


def make_episode(series: dict, characters: dict, episode: int, seconds: int) -> dict:
    genre = series.get("genre", "都市复仇")
    dialogue = DIALOGUE_POOL.get(genre, DIALOGUE_POOL["都市复仇"])
    scene_count = max(4, min(8, seconds // 10))
    per_scene = seconds // scene_count
    scenes = []
    for i in range(scene_count):
        lead, rival, ally, boss = [c["name"] for c in characters["characters"]]
        lines = [dialogue[(episode + i) % len(dialogue)], dialogue[(episode + i + 2) % len(dialogue)]]
        scenes.append(
            {
                "scene": i + 1,
                "location": series["locations"][i % len(series["locations"])]["name"],
                "time": "夜" if i % 2 else "日",
                "beat": f"第{i+1}场：冲突升级第{i+1}步",
                "duration_seconds": per_scene,
                "actions": [
                    f"{lines[0][0]}进入场景，环视四周",
                    f"{lines[1][0]}逼近，气氛紧张",
                    "双方对峙，画面定格",
                ],
                "dialogue": [
                    {"speaker": lines[0][0], "line": lines[0][1], "emotion": "冷静"},
                    {"speaker": lines[1][0], "line": lines[1][1], "emotion": "挑衅"},
                ],
                "camera": CAMERA_MOVES[i % len(CAMERA_MOVES)],
            }
        )
    return {
        "episode": episode,
        "runtime_seconds": seconds,
        "opening_hook": f"{series['title']}：第{episode}集开场，主角遭遇新的危机",
        "emotional_hook": "压迫感与反击欲同时拉满",
        "main_conflict": f"主角与对手就'{series['conflict_engine']}'的下一步展开交锋",
        "escalation": "对手动用新的筹码，主角陷入被动",
        "reversal": "主角亮出提前布好的底牌",
        "ending_hook": "幕后黑手第一次露出马脚，指向下一集",
        "characters": ["lead", "rival", "ally" if episode > 1 else "boss"],
        "locations": [s["location"] for s in scenes],
        "continuity": "服装与视觉锚点保持系列设定一致",
        "scenes": scenes,
        "total_seconds": seconds,
    }


def make_shots(script: dict, characters: dict) -> dict:
    clips = []
    for scene in script.get("scenes", []):
        lead = characters["characters"][0]["name"]
        clips.append(
            {
                "clip": f"clip-{scene['scene']:02d}",
                "source_beat": scene["beat"],
                "duration_hint": scene["duration_seconds"],
                "references": {"images": ["characters/lead.png"], "purpose": f"保持{lead}身份/服装一致"},
                "timeline_beats": [
                    f"起：{lead}出现在{scene['location']}",
                    "中：对峙，动作展开",
                    "转：情绪变化，冲突升级",
                    "合：定格在关键瞬间",
                ],
                "continuity_rules": ["保持角色脸型/发型/服装不变", "从上一段尾帧状态开始"],
                "camera": scene["camera"],
                "dialogue_audio": " ".join(f'{d["speaker"]}：{d["line"]}' for d in scene["dialogue"]),
                "negative": ["多人同框", "文字水印", "穿帮动作"],
                "ending_frame": "镜头停在角色面部特写",
                "rerun_notes": "若动作不连贯，微调时间线节拍后重跑",
            }
        )
    return {"clips": clips}


def make_novel(series: dict, episodes: list[dict]) -> str:
    lines = [
        f"# {series['title']}",
        "",
        f"> {series['logline']}",
        "",
        "## 楔子",
        "",
        f"{series['characters_hint']}",
        "",
    ]
    for ep in episodes:
        lines.append(f"## 第{ep['episode']}集")
        lines.append("")
        for scene in ep.get("scenes", []):
            lines.append(f"### 场景{scene['scene']}：{scene['location']}（{scene['time']}）")
            for action in scene["actions"]:
                lines.append(f"- {action}")
            for d in scene["dialogue"]:
                lines.append(f'  「{d["line"]}」——{d["speaker"]}')
            lines.append("")
    return "\n".join(lines)
