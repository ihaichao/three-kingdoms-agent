"""从《三国志》原文中抽取角色史料。

数据源：https://github.com/garychowcmu/daizhigev20 （殆知阁古代文献，公有领域）
放在 api/data/guji/ 下，不入库、不提交。

文件结构（已核实）：

    钦定四库全书
    蜀志卷五
    晋著作郎巴西中正安汉陈　夀撰
    宋太中大夫国子博士闻喜裴松之注     ← 卷头标记，全文 65 处
    诸葛亮【子乔　瞻　董厥樊建】        ← 传名行
    诸葛亮字孔明琅邪阳都人也...         ← 正文，按年/事分行
    ...
    （下一个卷头标记 = 本卷结束）

所以一个人物的史料 = 从其特征起始句所在行，到下一个卷头标记行为止。
"""

from functools import lru_cache
from pathlib import Path
from typing import Generator

from langchain_core.documents import Document
from loguru import logger

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
    # 吴书九是周瑜、鲁肃、吕蒙合传，按卷取会混入另外两人的记载。
    # 对检索影响不大（同时代同阵营），但 metadata 如实标注。
    "zhouyu": {"locator": "周瑜字公瑾", "volume": "吴书九·周瑜鲁肃吕蒙传"},
}


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


@lru_cache(maxsize=1)
def _load_lines(path: str) -> tuple[str, ...]:
    """读文件并按行切。用 lru_cache 避免六个角色各读一次 2.2MB。"""
    text = Path(path).read_text(encoding="utf-8")
    return tuple(line.strip() for line in text.split("\n"))


def extract(character: Character) -> list[Document]:
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

    body = "\n".join(
        line for line in lines[start:end] if line and not _is_toc_line(line)
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
