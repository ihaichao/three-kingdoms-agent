from loguru import logger

from three_kingdoms.domain.character_factory import CharacterFactory
from three_kingdoms.domain.exceptions import CharacterNotFound
from three_kingdoms.infrastructure.mongo.checkpointer import get_checkpointer


def _threads_for(character_ids: list[str]) -> list[str]:
    """找出属于这些角色的所有 thread_id。

    正常对话的 thread_id 就是 character_id；带 new_thread=True 的会话是
    "<character_id>-<uuid>"。两种都要清掉，所以这里从 checkpoint 集合里
    捞出实际存在的 thread_id 再按前缀过滤。
    """
    checkpointer = get_checkpointer()
    existing = checkpointer.checkpoint_collection.distinct("thread_id")

    targets = []
    for cid in character_ids:
        for tid in existing:
            if tid == cid or tid.startswith(f"{cid}-"):
                targets.append(tid)
    return targets


async def reset_conversation_state(character_id: str | None = None) -> dict:
    """清空对话记忆。

    Args:
        character_id: 指定角色则只清该角色；为 None 时清全部角色。

    Returns:
        清理结果，含被删除的 thread_id 列表。

    Raises:
        CharacterNotFound: 传了不存在的 character_id。
    """
    available = CharacterFactory.get_available_characters()

    if character_id is not None:
        key = character_id.lower()
        if key not in available:
            raise CharacterNotFound(key)
        character_ids = [key]
    else:
        character_ids = available

    targets = _threads_for(character_ids)

    checkpointer = get_checkpointer()
    for thread_id in targets:
        await checkpointer.adelete_thread(thread_id)

    logger.info(f"已清空 {len(targets)} 条对话: {targets}")

    return {
        "characters": character_ids,
        "deleted_threads": targets,
        "count": len(targets),
    }
