from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from three_kingdoms.application.conversation_service.workflow.edges import (
    should_summarize_conversation,
)
from three_kingdoms.application.conversation_service.workflow.nodes import (
    conversation_node,
    summarize_conversation_node,
)
from three_kingdoms.application.conversation_service.workflow.state import (
    CharacterState,
)
from three_kingdoms.application.conversation_service.workflow.tools import tools

retriever_node = ToolNode(tools)


async def connector_node(state: CharacterState):
    return {}


def create_workflow_graph() -> StateGraph:
    graph_builder = StateGraph(CharacterState)

    graph_builder.add_node("conversation_node", conversation_node)
    graph_builder.add_node("retriever_node", retriever_node)
    graph_builder.add_node("connector_node", connector_node)
    graph_builder.add_node("summarize_conversation_node", summarize_conversation_node)

    graph_builder.add_edge(START, "conversation_node")
    graph_builder.add_conditional_edges(
        "conversation_node",
        tools_condition,
        {"tools": "retriever_node", END: "connector_node"},
    )
    graph_builder.add_edge("retriever_node", "conversation_node")
    graph_builder.add_conditional_edges("connector_node", should_summarize_conversation)
    graph_builder.add_edge("summarize_conversation_node", END)

    return graph_builder


# 不带 checkpointer 编译，供 LangGraph Studio 可视化用
graph = create_workflow_graph().compile()
