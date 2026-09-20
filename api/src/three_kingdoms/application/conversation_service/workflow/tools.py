from typing import Annotated

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from three_kingdoms.application.data.extract import CHARACTER_SOURCES
from three_kingdoms.application.rag.retrievers import get_retriever
from three_kingdoms.infrastructure.timing import timed


@tool
def search_character_history(
    query: str,
    state: Annotated[dict, InjectedState],
) -> str:
    """检索该角色在《三国志》中的原始记载。

    返回与查询相关的史料原文（文言，无标点），并注明出处篇目。
    只检索当前对话角色自己的传记，不会返回他人的记载。

    何时使用：
    - 对方问及具体的人、事、时间、地点，而你需要确认史实
    - 对方提起某事，你不确定是否发生过，或细节记不真切
    - 你要引述自己说过的话、写过的表文、打过的仗

    何时不要使用：
    - 寒暄、问候、玩笑
    - 对方问你的看法、志向、好恶——这些出于你的本心，不在史册
    - 你已经从先前的检索结果里得到了答案

    Args:
        query: 检索词。语料是文言原文、无标点。写成一句带上下文的话，
            不要只丢一个词——例如查"赤壁之战中用火攻烧曹操战船"，
            而不是只查"赤壁"。（实测：单个专有名词的召回最差。）
            抽象的关系词效果很差——查"认识""关系""评价"多半一无所获，
            应改用事件本身：把"和刘备怎么认识的"换成"三顾茅庐隆中对策"。
            若一次检索无所得，可换一个说法再试一次。

    Returns:
        若干段史料原文及其出处；若本角色无相应记载，返回一句说明。
    """
    character_id = state["character_id"]

    if character_id not in CHARACTER_SOURCES:
        return f"《三国志》中未见{state['character_name']}的传记。"

    with timed(f"检索 embedding+向量查询 query={query!r}"):
        docs = get_retriever(character_id=character_id).invoke(query)
    if not docs:
        return f"《三国志》中未见{state['character_name']}与此相关的记载。"
    return "\n\n".join(
        f"《{d.metadata.get('volume', '三国志')}》：{d.page_content}" for d in docs
    )


tools = [search_character_history]
