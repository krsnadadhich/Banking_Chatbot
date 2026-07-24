"""Turns a classified intent (plus simple session state) into a reply string.

Dialog handling is intentionally minimal: everything is single-turn except
`card_block`, which needs at most one follow-up question (which card) and a
yes/no confirmation before "blocking" the card in the mock data.
"""

import json
from pathlib import Path

from chatbot.classifier import predict

ROOT = Path(__file__).resolve().parent.parent
MOCK_DATA_PATH = ROOT / "data" / "mock_data.json"

with open(MOCK_DATA_PATH, encoding="utf-8") as f:
    MOCK_DATA = json.load(f)

FALLBACK_REPLY = (
    "Sorry, I didn't quite understand that. You can ask me about your balance, "
    "recent transactions, blocking a card, loans, interest rates, or branch locations."
)

YES_WORDS = {"yes", "y", "yep", "yeah", "sure", "confirm", "ok", "okay", "please do"}
NO_WORDS = {"no", "n", "nope", "cancel", "don't", "dont", "stop"}


def new_session_state():
    return {"awaiting_card_type": False, "pending_confirmation": None}


def _format_currency(amount):
    sign = "-" if amount < 0 else ""
    return f"{sign}${abs(amount):,.2f}"


def _handle_balance_inquiry():
    checking = MOCK_DATA["accounts"]["checking"]["balance"]
    savings = MOCK_DATA["accounts"]["savings"]["balance"]
    return (
        f"Your checking balance is ${checking:,.2f} and your savings balance is "
        f"${savings:,.2f}."
    )


def _handle_transaction_history():
    lines = [
        f"{t['date']}: {t['description']} ({_format_currency(t['amount'])})"
        for t in MOCK_DATA["transactions"]
    ]
    return "Here are your recent transactions:\n" + "\n".join(lines)


def _handle_loan_info():
    lines = [f"{loan['type']}: {loan['blurb']}" for loan in MOCK_DATA["loans"]]
    return "Here are our current loan options:\n" + "\n".join(lines)


def _handle_interest_rates():
    rates = MOCK_DATA["interest_rates"]
    return (
        f"Savings: {rates['savings']}, Checking: {rates['checking']}, "
        f"12-Month Fixed Deposit: {rates['fixed_deposit_12mo']}."
    )


def _handle_branch_locator():
    lines = [f"{b['name']}: {b['address']}" for b in MOCK_DATA["branches"]]
    return "Here are our branches:\n" + "\n".join(lines)


def _handle_complaint():
    return (
        "I'm sorry to hear that. I've logged your complaint and a representative "
        "will follow up with you shortly."
    )


SIMPLE_INTENT_HANDLERS = {
    "greeting": lambda: "Hi! How can I help you with your banking today?",
    "goodbye": lambda: "Goodbye! Have a great day.",
    "thanks": lambda: "You're welcome! Anything else I can help with?",
    "balance_inquiry": _handle_balance_inquiry,
    "transaction_history": _handle_transaction_history,
    "loan_info": _handle_loan_info,
    "interest_rates": _handle_interest_rates,
    "branch_locator": _handle_branch_locator,
    "complaint": _handle_complaint,
}


def _extract_card_type(message):
    lowered = message.lower()
    if "debit" in lowered:
        return "debit"
    if "credit" in lowered:
        return "credit"
    return None


def _block_card(card_type):
    MOCK_DATA["cards"][card_type]["status"] = "blocked"


def get_reply(state, message):
    """Updates `state` in place and returns (reply, intent) for this turn."""
    message = message.strip()

    if state["pending_confirmation"]:
        card_type = state["pending_confirmation"]
        lowered = message.lower()
        if lowered in YES_WORDS:
            _block_card(card_type)
            state["pending_confirmation"] = None
            reply = f"Your {card_type} card ending in {MOCK_DATA['cards'][card_type]['last4']} has been blocked."
        elif lowered in NO_WORDS:
            state["pending_confirmation"] = None
            reply = "Okay, I won't block your card."
        else:
            reply = f"Please answer yes or no: block your {card_type} card?"
        return reply, "card_block"

    if state["awaiting_card_type"]:
        card_type = _extract_card_type(message)
        if card_type is None:
            return "Sorry, is that your debit or credit card?", "card_block"
        state["awaiting_card_type"] = False
        state["pending_confirmation"] = card_type
        reply = f"Just to confirm, block your {card_type} card ending in {MOCK_DATA['cards'][card_type]['last4']}? (yes/no)"
        return reply, "card_block"

    intent, _confidence = predict(message)

    if intent == "card_block":
        card_type = _extract_card_type(message)
        if card_type is None:
            state["awaiting_card_type"] = True
            return "Sure, is that your debit or credit card?", "card_block"
        state["pending_confirmation"] = card_type
        reply = f"Just to confirm, block your {card_type} card ending in {MOCK_DATA['cards'][card_type]['last4']}? (yes/no)"
        return reply, "card_block"

    handler = SIMPLE_INTENT_HANDLERS.get(intent)
    if handler is not None:
        return handler(), intent

    return FALLBACK_REPLY, "fallback"
