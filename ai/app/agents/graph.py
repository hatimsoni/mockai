"""The LangGraph workflow wiring the three agents together.

        START
          |
   [route_start] --(last answer not yet scored)--> evaluator
          |                                           |
          |                                    [route_after_eval]
          |                                      /          \\
          +---(finish requested)-----------> coach       interviewer
          +---(otherwise)------------------------------> interviewer
                                               |              |
                                              END            END

One HTTP request = one run of this graph. The API calls it:
  - after every answer      -> evaluator -> interviewer (returns evaluation + next question)
  - when the user finishes  -> [evaluator] -> coach    (returns the report)
"""
from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.agents.coach import coach_node
from app.agents.evaluator import evaluator_node
from app.agents.interviewer import interviewer_node
from app.agents.state import InterviewState


def _needs_evaluation(state: InterviewState) -> bool:
    turns = state.get("turns", [])
    return bool(turns) and turns[-1].transcript is not None and turns[-1].evaluation is None


def route_start(state: InterviewState) -> str:
    if _needs_evaluation(state):
        return "evaluator"
    return "coach" if state.get("finish") else "interviewer"


def route_after_eval(state: InterviewState) -> str:
    return "coach" if state.get("finish") else "interviewer"


@lru_cache
def build_graph():
    g = StateGraph(InterviewState)
    g.add_node("evaluator", evaluator_node)
    g.add_node("interviewer", interviewer_node)
    g.add_node("coach", coach_node)

    g.add_conditional_edges(START, route_start, ["evaluator", "coach", "interviewer"])
    g.add_conditional_edges("evaluator", route_after_eval, ["coach", "interviewer"])
    g.add_edge("interviewer", END)
    g.add_edge("coach", END)
    return g.compile()


def run_step(state: InterviewState) -> InterviewState:
    return build_graph().invoke(state)
