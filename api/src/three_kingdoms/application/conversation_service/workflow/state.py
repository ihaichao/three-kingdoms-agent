from langgraph.graph import MessagesState


class CharacterState(MessagesState):
    character_name: str
    character_perspective: str
    character_style: str
    summary: str
