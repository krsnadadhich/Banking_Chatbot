import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from chatbot.classifier import predict
from chatbot.responses import get_reply, new_session_state


@pytest.mark.parametrize("text,expected_intent", [
    ("hi", "greeting"),
    ("bye", "goodbye"),
    ("thanks a lot", "thanks"),
    ("what's my balance", "balance_inquiry"),
    ("show my last 5 transactions", "transaction_history"),
    ("block my debit card", "card_block"),
    ("tell me about home loans", "loan_info"),
    ("what's the current savings interest rate", "interest_rates"),
    ("find a branch near me", "branch_locator"),
    ("i want to file a complaint", "complaint"),
])
def test_intent_classification(text, expected_intent):
    intent, confidence = predict(text)
    assert intent == expected_intent
    assert confidence >= 0.4


def test_fallback_for_gibberish():
    intent, _confidence = predict("asdkjaslkdj qweqwe zzxx")
    assert intent == "fallback"


def test_balance_inquiry_reply_mentions_dollar_amount():
    state = new_session_state()
    reply, intent = get_reply(state, "what's my balance")
    assert intent == "balance_inquiry"
    assert "$" in reply


def test_card_block_flow_confirm():
    state = new_session_state()

    reply, intent = get_reply(state, "i need to block my card")
    assert intent == "card_block"
    assert "debit or credit" in reply.lower()

    reply, intent = get_reply(state, "debit")
    assert "confirm" in reply.lower()
    assert state["pending_confirmation"] == "debit"

    reply, intent = get_reply(state, "yes")
    assert "blocked" in reply.lower()
    assert state["pending_confirmation"] is None


def test_card_block_flow_cancel():
    state = new_session_state()

    get_reply(state, "please block my credit card")
    reply, intent = get_reply(state, "no")

    assert "won't block" in reply.lower()
    assert state["pending_confirmation"] is None


def test_card_block_with_type_in_first_message_skips_follow_up():
    state = new_session_state()

    reply, intent = get_reply(state, "block my credit card please")
    assert intent == "card_block"
    assert "confirm" in reply.lower()
    assert state["pending_confirmation"] == "credit"
