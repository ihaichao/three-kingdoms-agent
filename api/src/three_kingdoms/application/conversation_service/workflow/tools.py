from typing import Annotated

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from three_kingdoms.application.rag.retrievers import get_retriever
from three_kingdoms.infrastructure.timing import timed


@tool
def search_character_history(
    query: str,
    state: Annotated[dict, InjectedState],
) -> str:
    """检索该角色在《三国演义》中的相关段落。

    返回与查询相关的原文段落，并注明出自第几回。
    只检索当前对话角色出现过的段落，不会返回与他无关的内容。

    何时使用：
    - 对方问及具体的人、事、时间、地点，而你需要确认史实
    - 对方提起某事，你不确定是否发生过，或细节记不真切
    - 你要引述自己说过的话、写过的表文、打过的仗

    何时不要使用：
    - 寒暄、问候、玩笑
    - 对方问你的看法、志向、好恶——这些出于你的本心，不在史册
    - 你已经从先前的检索结果里得到了答案

    Args:
        query: 检索词。写成一句带上下文的话，不要只丢一个词——例如查
            "赤壁之战中用火攻烧曹操战船"，而不是只查"赤壁"。
            （实测：单个专有名词的召回最差。）
            抽象的关系词效果很差——查"认识""关系""评价"多半一无所获，
            应改用事件本身：把"和刘备怎么认识的"换成"三顾茅庐隆中对策"。
            后世流行的情节名（草船借箭、空城计、借东风）在原文里不出现，
            但回目里有近义的说法（用奇谋孔明借箭、武侯弹琴退仲达），
            所以这类词照样可以直接查。
            若一次检索无所得，可换一个说法再试一次。

    Returns:
        若干段原文及其回目；若检索不到，返回一句说明。
    """
    character_id = state["character_id"]

    with timed(f"检索 embedding+向量查询 query={query!r}"):
        docs = get_retriever(character_id=character_id).invoke(query)
    if not docs:
        return f"此事{state['character_name']}记不真切了。"
    return "\n\n".join(
        f"《{d.metadata.get('volume', '三国演义')}》：{d.page_content}" for d in docs
    )


tools = [search_character_history]
