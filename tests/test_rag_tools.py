import pytest

from app.rag.retriever import Retriever
from app.tools.registry import ToolError, ToolRegistry


def test_retrieval_ranks_relevant_section_first():
    top = Retriever().search("how do I reset my password")[0]
    assert (top.doc, top.section) == ("account", "Reset password")


def test_retrieval_no_match_is_empty():
    assert Retriever().search("zxqv blorp") == []


def test_subscription_detects_duplicates():
    sub = ToolRegistry(Retriever()).get_subscription("cus_1001")
    assert sub["duplicate_charges"] == [["ch_9001", "ch_9002"]]


def test_unknown_tool_raises():
    with pytest.raises(ToolError):
        ToolRegistry(Retriever()).call("drop_database", "cus_1001")


def test_unknown_customer():
    assert ToolRegistry(Retriever()).get_customer_profile("nope") == {"found": False}
