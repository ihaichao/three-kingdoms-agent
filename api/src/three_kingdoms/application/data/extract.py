"""从古籍原文中抽取角色语料。

支持两部书，用 settings.CORPUS 切换：

    yanyi  《三国演义》（默认）—— 罗贯中，章回体小说
    zhi    《三国志》         —— 陈寿，纪传体正史

为什么默认用演义（2026-09 的决定，改自模块 3）：

1. **玩家的问题来自演义。**草船借箭、空城计、借东风、桃园结义、七擒孟获，
   这些在《三国志》里一件都没有。用正史当语料，角色对玩家八成的提问只能
   答"未见此事"。
2. **司马懿终于有语料。**《三国志》成书于西晋，陈寿不能给本朝先祖立传，
   他在正史里只以"宣王"散见他传；演义里出现 293 次。
3. **文本质量高一个数量级。**演义有标点、分段清楚、对白密集；正史那边我们
   花了整个模块 3 在跟数据搏斗——剥裴注、异体字表、校勘记、合传边界。

正史那条路径完整保留在下面，没有删。模块 6 要做双语料（角色能区分"史载如此"
和"世人传言"）时，是打开一个开关，不是重写。

---

演义的结构（已核实）：

    《三国演义》作者：罗贯中
    第001回　宴桃园豪杰三结义　斩黄巾英雄首立功      ← 目录，共 120 行，用阿拉伯数字
    ...
    第一回　宴桃园豪杰三结义　斩黄巾英雄首立功        ← 正文回目，用汉字数字
    却说鲁肃、孔明辞了玄德、刘琦，登舟望柴桑郡来...   ← 段落
    ...

目录和正文的回目写法不同（001 vs 一），正好拿来区分，不用另外判断位置。

全书 606351 字 / 120 回 / 平均 29 段一回、160 字一段。
"""

import re
from functools import lru_cache
from pathlib import Path
from typing import Generator

from langchain_core.documents import Document
from loguru import logger

from three_kingdoms.config import settings
from three_kingdoms.domain.character import Character
from three_kingdoms.domain.character_factory import CharacterFactory

SANGUOZHI_PATH = Path("data/guji/史藏/正史/三国志.txt")

# 每卷开头都有这一行，用它来定卷边界
VOLUME_MARK = "宋太中大夫国子博士闻喜裴松之注"

# character_id -> 在《三国志》里的定位方式
#
# 注意 simayi 不在这里：《三国志》成书于西晋，陈寿不能给本朝先祖立传，
# 司马懿全书只以"宣王"之名散见于他人传中。他的传在《晋书·宣帝纪》，
# 那个文件有标点、按段分行，格式跟这里完全不同，暂不接入。
CHARACTER_SOURCES: dict[str, dict[str, str]] = {
    "zhugeliang": {"locator": "诸葛亮字孔明", "volume": "蜀书五·诸葛亮传"},
    "liubei": {"locator": "先主姓刘", "volume": "蜀书二·先主传"},
    "caocao": {"locator": "太祖武皇帝", "volume": "魏书一·武帝纪"},
    "sunquan": {"locator": "孙权字仲谋", "volume": "吴书二·吴主传"},
    # 吴书九是周瑜、鲁肃、吕蒙合传。按卷取会混入另外两人的记载——
    # 这一点我最初判断为"影响不大"，是错的：评测集抽查显示周瑜 28 条题里
    # 12 条源自鲁肃/吕蒙段落，其中「吕蒙怎么当上别部司马」「打零陵怎么让
    # 郝普投降」（吕蒙）「后来怎么对付关羽」（吕蒙，周瑜死于 210 年）
    # 是明确张冠李戴。所以加 end_locator 在鲁肃传开头截断。
    # 代价：正文 7761 -> 2223 字。赤壁、黄葢献计、火攻、程普、精兵三万、
    # 曲有误顾都还在，丢的是本来就不属于他的部分。
    "zhouyu": {
        "locator": "周瑜字公瑾",
        "end_locator": "鲁肃字子敬",
        "volume": "吴书九·周瑜传",
    },
}


# ---------------------------------------------------------------------------
# 《三国演义》
# ---------------------------------------------------------------------------

SANYANYI_PATH = Path("data/guji/集藏/演义/三国演义.txt")

# 正文回目用汉字数字（第一回），目录用阿拉伯数字（第001回）。
CHAPTER_RE = re.compile(r"^第[零一二三四五六七八九十百]+回")

# 演义里人物基本用字、号、爵位称呼，用本名去匹配会漏掉绝大部分：
#
#     孔明 1699 次  vs  诸葛亮 168 次
#     玄德 1820 次  vs  刘备   298 次
#     仲达   40 次  vs  司马懿 293 次
#
# 所以必须按别名表打标签。只收无歧义的称呼——"魏王"没收，因为曹丕称王之后
# 也叫魏王；"丞相""都督"这类职衔没收，一部书里能指好几个人。
CHARACTER_ALIASES: dict[str, list[str]] = {
    "zhugeliang": ["孔明", "诸葛亮", "武侯", "卧龙", "诸葛丞相"],
    "liubei": ["玄德", "刘备", "皇叔", "刘豫州"],
    "caocao": ["曹操", "孟德", "曹公"],
    "sunquan": ["孙权", "仲谋", "吴侯", "孙将军"],
    "zhouyu": ["周瑜", "公瑾", "周郎", "周都督"],
    "simayi": ["司马懿", "仲达"],
}

# 说话人标记。演义写对白用的是单字短名——「操曰」不是「曹操曰」，
# 「权曰」「瑜曰」「懿曰」同理。只按全名找说话人，曹操会从 476 篇掉到 9 篇。
# 单字本身有歧义（「权」可以是权力），但「X曰」这个上下文把歧义消掉了。
CHARACTER_SPEECH_TAGS: dict[str, list[str]] = {
    "zhugeliang": ["孔明曰", "亮曰", "诸葛亮曰"],
    "liubei": ["玄德曰", "备曰", "刘备曰"],
    "caocao": ["操曰", "曹操曰", "孟德曰"],
    "sunquan": ["权曰", "孙权曰"],
    "zhouyu": ["瑜曰", "周瑜曰"],
    "simayi": ["懿曰", "司马懿曰"],
}

# 演义用全角引号包对白。引号外的叙述才是"谁在台上"，引号内多半是
# "谁被谈论"。正文里偶有引号不配对（底本 OCR 的问题），所以这个正则
# 只求大致剥掉，剥不干净不影响大局。
_QUOTED = re.compile(r"[“\"][^”\"]*[”\"]")


def _split_chapters(lines: tuple[str, ...]) -> list[tuple[str, list[str]]]:
    """按回切开，返回 [(回目, [段落, ...]), ...]。

    从第一个汉字数字回目开始，前面 120 行目录自动被跳过。
    """
    chapters: list[tuple[str, list[str]]] = []
    current: list[str] | None = None

    for line in lines:
        if CHAPTER_RE.match(line):
            current = []
            chapters.append((line, current))
        elif line and current is not None:
            current.append(line)

    return chapters


def _appears_in(character_id: str, body: str) -> bool:
    """这一段里，该角色是不是"在场的人"，而不只是"被提到的人"。

    两条判据，满足其一即可：

    1. 别名出现在**叙述层**（引号之外）。叙述是作者在说谁做了什么，
       出现在这里基本等于人在场。
    2. 出现了他的说话人标记（「操曰」）。

    为什么不能直接全文匹配别名：第四十四回有一段是诸葛瑾和孔明对话，
    孔明嘴里两次提到「刘皇叔」，全文匹配就把这段算成刘备的，于是出了
    一道「你兄弟诸葛亮对他哥说了什么」问刘备——他根本不在场。
    改成只看叙述层之后，这段不再算刘备的。

    为什么不看标题：回目里带人名（「柴桑口卧龙吊丧」），全章每一段都会
    被算成诸葛亮的。回目仍然拼进 page_content 供检索，但不参与打标。

    实测：1622 篇 -> 1335 篇，减了 18%，三条人工确认的正例都没漏。
    """
    if any(tag in body for tag in CHARACTER_SPEECH_TAGS[character_id]):
        return True
    narration = _QUOTED.sub("", body)
    return any(alias in narration for alias in CHARACTER_ALIASES[character_id])


def _pack(paragraphs: list[str], max_chars: int) -> list[str]:
    """把段落攒成不超过 max_chars 的块。

    段落是演义的天然语义单元，在段落边界切比按字数硬切干净得多。
    但有少数段落自己就超长（实测最长 1500+ 字），那种先按句号拆开再攒——
    不拆的话下游 splitter 会替我们拆，而它拆出来的后半截就没有回目前缀了，
    「情节名称」这一层的检索抓手会丢掉。
    """
    units: list[str] = []
    for para in paragraphs:
        if len(para) <= max_chars:
            units.append(para)
            continue
        sentence = ""
        for piece in para.split("。"):
            piece = f"{piece}。" if piece else ""
            if sentence and len(sentence) + len(piece) > max_chars:
                units.append(sentence)
                sentence = piece
            else:
                sentence += piece
        if sentence:
            units.append(sentence)

    # 单句就超预算的兜底。必须堵死：只要成品超过 chunk_size，下游 splitter
    # 就会再切一刀，切出来的尾巴既没有回目，又继承了整段的人物标签——
    # 实测就是这样产生过一条"问诸葛亮鲁肃孙权的对话"的废题。
    units = [
        u[i : i + max_chars] if len(u) > max_chars else u
        for u in units
        for i in (range(0, len(u), max_chars) if len(u) > max_chars else [0])
    ]

    buckets: list[str] = []
    buf = ""
    for unit in units:
        # +1 是拼接用的换行符。不算它的话每拼一次就溢出一个字，
        # 成品会卡在 chunk_size + 1，正好触发下游 splitter 再切一刀。
        if buf and len(buf) + 1 + len(unit) > max_chars:
            buckets.append(buf)
            buf = unit
        else:
            buf = f"{buf}\n{unit}" if buf else unit
    if buf:
        buckets.append(buf)
    return buckets


@lru_cache(maxsize=1)
def _build_yanyi_chunks() -> tuple[Document, ...]:
    """把全书切成带回目的 chunk，并标注每个 chunk 出现了哪些角色。

    两个设计决定值得说明：

    **回目要进正文，不能只放 metadata。**实测「草船借箭」「空城计」「借东风」
    在演义原文里出现 0 次——它们是后世戏曲评书的叫法。原文对应的是回目：
    「用奇谋孔明借箭」「武侯弹琴退仲达」「七星坛诸葛祭风」。回目是"情节名称"
    这一层唯一的检索入口，放进 page_content 才检索得到。

    **一个 chunk 命中多人时，按人复制多份。**检索永远按单个 character_id
    过滤，复制天然正确，也让 character_id 保持单值——向量索引的 filter、
    retrievers 的 pre_filter、long_term_memory 的入库循环都不用动。
    实测 1090 个 chunk 复制成 1792 篇，存储代价可以忽略。

    一个人都没命中的 chunk（实测 152 个，14%）直接丢掉——那是纯过场叙事，
    六个角色都问不到。
    """
    lines = _load_lines(str(SANYANYI_PATH))
    max_chars = settings.RAG_CHUNK_SIZE

    docs: list[Document] = []
    orphan = 0

    for number, (title, paragraphs) in enumerate(_split_chapters(lines), start=1):
        # 回目要占掉一部分预算——不扣的话成品会略微超过 chunk_size，
        # 下游 splitter 就会再切一刀，切出一堆几十字的碎片。
        buckets = _pack(paragraphs, max_chars - len(title) - 1)

        for body in buckets:
            text = f"{title}\n{body}"
            hits = [cid for cid in CHARACTER_ALIASES if _appears_in(cid, body)]
            if not hits:
                orphan += 1
                continue
            for character_id in hits:
                docs.append(
                    Document(
                        page_content=text,
                        metadata={
                            "character_id": character_id,
                            "character_name": CharacterFactory.get_character(
                                character_id
                            ).name,
                            "source": "三国演义",
                            "volume": title,
                            "chapter": number,
                        },
                    )
                )

    logger.info(f"《三国演义》切出 {len(docs)} 篇（丢弃无人物 chunk {orphan} 个）")
    return tuple(docs)


def extract_yanyi(character: Character) -> list[Document]:
    """取某个角色在《三国演义》里的全部 chunk。"""
    docs = [
        d for d in _build_yanyi_chunks() if d.metadata["character_id"] == character.id
    ]
    logger.info(f"{character.name}: {len(docs)} 篇")
    return docs


# ---------------------------------------------------------------------------
# 《三国志》（模块 3 的实现，保留备用）
# ---------------------------------------------------------------------------


def strip_annotations(text: str) -> str:
    """剥掉裴松之注（【】及其内容）。

    裴注占全文约 44%，是南朝裴松之引其他史书对陈寿正文的补注，
    跟角色本人的第一人称知识不是一回事，留着会稀释检索。

    代价：裴注里的一些名场面会一并丢掉，比如"鞠躬尽力死而后已"
    （出自裴注引《汉晋春秋》的后出师表）和"隆中"这个地名。

    用计数而不是正则，这样嵌套的【】也能正确处理。
    """
    out: list[str] = []
    depth = 0
    for ch in text:
        if ch == "【":
            depth += 1
        elif ch == "】":
            depth = max(0, depth - 1)
        elif depth == 0:
            out.append(ch)
    return "".join(out)


# 异体字归一表（旧字形/俗字 -> 现代通行字形）
#
# 为什么需要：殆知阁这套底本是影印古籍 OCR 出来的，保留了大量异体字。
# 它们不是繁体字——OpenCC 的 t2s / tw2sp 对这些字全部原样输出（实测），
# 因为在 OpenCC 眼里它们本来就"是简体"，只是另一个字。
#
# 为什么影响检索：向量检索靠 token 对齐。原文写「黄葢」，用户问「黄盖」，
# bge-m3 切出来是两组完全不同的 token，语义再近也对不上。
# 实测：加这张表之前，「黄盖献计火攻」在周瑜卷里检索不到任何相关段落，
# 而原文第一句就是「瑜部将黄葢曰今冦众我寡难与持久」。
#
# 表是人工核对出来的，不是穷举：把五卷正文里出现过的、且有现代通行写法
# 的字挑出来逐个看上下文确认。没出现过的不收，拿不准的不收
# （例如「夏侯楙」的「楙」本来就是本名用字，不是「茂」的异体，故不收）。
VARIANT_CHARS: dict[str, str] = {
    # 人名、地名（对检索影响最大的一批）
    "葢": "盖",  # 黄葢 -> 黄盖
    "闗": "关",  # 闗羽 -> 关羽
    "呉": "吴",  # 呉会 -> 吴会
    "袆": "祎",  # 费袆 -> 费祎
    "冦": "寇",
    "臯": "皋",  # 成臯 -> 成皋
    "昬": "昏",  # 海昬 -> 海昏
    "邉": "边",
    "隂": "阴",  # 隂平 -> 阴平
    "夀": "寿",  # 陈夀 -> 陈寿
    # 常用字
    "眀": "明",
    "歴": "历",
    "寜": "宁",
    "鬬": "斗",  # 鬬舰 -> 斗舰
    "畧": "略",  # 将畧 -> 将略
    "嵗": "岁",
    "髙": "高",
    "寳": "宝",
    "衞": "卫",
    "宻": "密",
    "幷": "并",
    "竝": "并",
    "賔": "宾",
    "撃": "击",
    "噐": "器",
    "渉": "涉",
    "徴": "征",
    "讐": "仇",
    "刼": "劫",
    "逹": "达",
    "蔵": "藏",
    "觧": "解",
    "頋": "顾",
    "顔": "颜",
    "鳯": "凤",
    "勅": "敕",
    "勑": "敕",
    "塲": "场",
    "擕": "携",
    "鋭": "锐",
    "疎": "疏",
    "麤": "粗",
    "靣": "面",
    "黙": "默",
    "効": "效",
    "勦": "剿",
    "奨": "奖",
    "悮": "误",
    "眎": "视",
    "禆": "裨",
    "苐": "第",
    "衂": "衄",
    "貎": "貌",
    "軰": "辈",
    "麽": "么",
    "竒": "奇",
    "羣": "群",
    "彊": "强",
    "勲": "勋",
    "覩": "睹",
    "脩": "修",
    "冡": "冢",
    "叅": "参",
    "廵": "巡",
    "徃": "往",
    "敎": "教",
    "滛": "淫",
    "燿": "耀",
}

# 一次性编译成 translate 表。str.translate 是单遍扫描，
# 比链式调用 68 次 str.replace 快得多，也不会出现"前一次替换的结果
# 被后一次替换又改一遍"的连锁问题。
_VARIANT_TABLE = str.maketrans(VARIANT_CHARS)


def normalize_variants(text: str) -> str:
    """把异体字换成现代通行字形。

    已知无法修复、故意不处理的：「防」。

    底本里有 218 处「防」是坏字占位符（五卷正文共 42674 字，占 0.51%；
    周瑜卷 92 处 / 7761 字，高达 1.19%）。它至少顶替了三个不同的原字：

        防策将东渡   -> 孙策
        中防军       -> 中护军
        防冲鬬舰     -> 蒙冲斗舰
        吕防计       -> 吕蒙计
        钟防征       -> 钟会

    同时「防」本身也有正常用法（「数为邉寇防」），所以既不能整体替换，
    也不能整体删除——只能如实记下来，作为这个数据源的已知质量上限。
    """
    return text.translate(_VARIANT_TABLE)


def _is_toc_line(line: str) -> bool:
    """判断是不是目录行。

    诸葛亮那一卷末尾夹了《诸葛氏集目录》：

        开府作牧第一　　　权制第二
        南征第三　　　　　北出第四

    特征是用多个全角空格对齐。不能按行长度过滤——孙权传里
    "七年权母吴氏薨" 只有 7 个字但是真内容。
    """
    return line.count("\u3000") >= 2


def _is_kaokan_line(line: str) -> bool:
    """判断是不是《四库》考证（校勘记）行。

    每卷末尾有一整块版本考订，形如：

        诸葛亮父珪字君贡○君贡一本作子贡
        盖应变将略非其所长欤注即以为君臣百姓之心欣戴之矣○君臣疑作羣臣

    格式固定：被校片段 ○ 校语。五卷共 118 行 / 4663 字，占语料 10.9%。

    这些是版本学，不是内容。留着的后果实测过：出题时模型会拿它当史料，
    生成「你手下那个叫殷札的太守，到底叫什么名字？」这种问版本讹误的题；
    在向量库里则纯粹是噪声。

    安全性核过：诸葛亮卷 24 条校勘行中，20 条的被校片段在保留正文里
    找不到——它们校的是已被 strip_annotations 剥掉的裴注。所以整行丢弃
    不会丢掉正文内容。
    """
    return "○" in line


@lru_cache(maxsize=1)
def _load_lines(path: str) -> tuple[str, ...]:
    """读文件并按行切。用 lru_cache 避免六个角色各读一次 2.2MB。"""
    text = Path(path).read_text(encoding="utf-8")
    return tuple(line.strip() for line in text.split("\n"))


def extract_zhi(character: Character) -> list[Document]:
    """抽取单个角色的史料。

    Args:
        character: 角色对象。

    Returns:
        该角色的 Document 列表；没有配置史料来源的角色返回空列表。
    """
    source = CHARACTER_SOURCES.get(character.id)
    if source is None:
        logger.warning(f"{character.name}（{character.id}）没有配置史料来源，跳过")
        return []

    lines = _load_lines(str(SANGUOZHI_PATH))
    volume_marks = [i for i, line in enumerate(lines) if line == VOLUME_MARK]

    locator = source["locator"]
    start = next((i for i, line in enumerate(lines) if locator in line), None)
    if start is None:
        logger.error(f"在《三国志》中找不到 {character.name} 的定位串: {locator}")
        return []

    end = next((m for m in volume_marks if m > start), len(lines))

    # 合传的情况下，下一个人的传记开头就是本人传记的结尾
    end_locator = source.get("end_locator")
    if end_locator:
        next_person = next(
            (i for i in range(start, end) if end_locator in lines[i]), None
        )
        if next_person is None:
            logger.warning(f"{character.name}: 找不到截断串 {end_locator}，退回按卷取")
        else:
            end = next_person

    body = "\n".join(
        line
        for line in lines[start:end]
        if line and not _is_toc_line(line) and not _is_kaokan_line(line)
    )
    body = strip_annotations(body)
    body = normalize_variants(body)

    logger.info(
        f"{character.name}: {source['volume']} 行 {start}-{end}，正文 {len(body)} 字"
    )

    return [
        Document(
            page_content=body,
            metadata={
                "character_id": character.id,
                "character_name": character.name,
                "source": "三国志",
                "volume": source["volume"],
            },
        )
    ]


# ---------------------------------------------------------------------------
# 统一入口
# ---------------------------------------------------------------------------


def extract(character: Character) -> list[Document]:
    """按 settings.CORPUS 选择语料来源。"""
    if settings.CORPUS == "yanyi":
        return extract_yanyi(character)
    return extract_zhi(character)


def get_extraction_generator(
    character_ids: list[str] | None = None,
) -> Generator[tuple[Character, list[Document]], None, None]:
    """逐个抽取角色史料。

    用生成器而不是一次性返回全部，是为了让下游（切分、向量化、入库）
    能一个角色一个角色地处理，内存占用不随角色数增长。

    Args:
        character_ids: 要抽取的角色 id；None 表示全部可用角色。

    Yields:
        (角色, 该角色的文档列表)
    """
    ids = character_ids or CharacterFactory.get_available_characters()

    for character_id in ids:
        character = CharacterFactory.get_character(character_id)
        yield character, extract(character)
