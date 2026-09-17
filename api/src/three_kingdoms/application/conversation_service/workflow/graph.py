from langgraph.graph import END, START, StateGraph

from three_kingdoms.application.conversation_service.workflow.nodes import (
    conversation_node,
)
from three_kingdoms.application.conversation_service.workflow.state import (
    CharacterState,
)


def create_workflow_graph() -> StateGraph:
    graph_builder = StateGraph(CharacterState)

    graph_builder.add_node("conversation_node", conversation_node)

    graph_builder.add_edge(START, "conversation_node")
    graph_builder.add_edge("conversation_node", END)

    return graph_builder


# 不带 checkpointer 编译，供 LangGraph Studio 可视化用
graph = create_workflow_graph().compile()
