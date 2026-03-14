'''
This module defines the DAG : Direct Acyclic Graph that orchestrates the video compliance audit process.
It connects the nodes using the StateGraph from Langgraph
START -> index_video_node -> audit_content_node -> END
'''

from langgraph.graph import StateGraph, END

from backend.src.graph.state import VideoAuditedState
from backend.src.graph.node import (
    index_video_node,
    audio_content_node
)

def create_graph():
    '''
    Constructs and compiles the LangGraph workflow
    Returns : 
    Complied Graph : runnable garph object for execution
    '''

    # initializes the graph with state schema
    workflow = StateGraph(VideoAuditedState)

    # add nodes
    workflow.add_node("indexer", index_video_node)
    workflow.add_node("auditor", audio_content_node)

    # define the entry point : indexer
    # define the edges
    workflow.set_entry_point("indexer")

    #define the edges
    workflow.add_edge("indexer", "auditor")

    # once the audit is complete, the workflow ends
    workflow.add_edge("auditor", END)

    # compile the graph
    app = workflow.compile()
    return app

# expose this runnable app
app = create_graph()