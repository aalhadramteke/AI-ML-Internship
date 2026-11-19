import pytest
from pydantic import ValidationError

from app.schemas import OrderIn, ResearchIn


@pytest.mark.parametrize(
    "item,qty",
    [("ab", 1), ("book", 2), ("x" * 50, 100)],
)
def test_order_valid(item, qty):
    o = OrderIn(item=item, quantity=qty)
    assert o.item == item and o.quantity == qty


@pytest.mark.parametrize(
    "item,qty",
    [("a", 1), ("x" * 51, 1), ("book", 0), ("book", -5), ("book", 101), ("book", "many")],
)
def test_order_invalid(item, qty):
    with pytest.raises(ValidationError):
        OrderIn(item=item, quantity=qty)


def test_order_requires_both_fields():
    with pytest.raises(ValidationError):
        OrderIn(item="book")
    with pytest.raises(ValidationError):
        OrderIn(quantity=1)


def test_research_query_is_stripped():
    assert ResearchIn(query="   What is RAG?  ").query == "What is RAG?"


@pytest.mark.parametrize("q", ["", "    ", "abc", "x" * 501])
def test_research_query_invalid(q):
    with pytest.raises(ValidationError):
        ResearchIn(query=q)
