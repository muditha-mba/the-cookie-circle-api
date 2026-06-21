from app.core.enums import Weekday
from app.utils.delivery_schedule import build_delivery_schedule_copy
from app.utils.faq_schedule import resolve_schedule_faq_answer


def test_cutoff_faq_uses_schedule_copy() -> None:
    copy = build_delivery_schedule_copy(
        cutoff_day=Weekday.THURSDAY,
        delivery_day=Weekday.SATURDAY,
    )
    answer = resolve_schedule_faq_answer(
        question="What is the order cutoff for this week's batch?",
        stored_answer="Old static answer",
        copy=copy,
    )
    assert answer == copy.explanation
    assert "Thursday evening" in answer
    assert "Saturday" in answer


def test_delivery_day_faq_uses_schedule_copy() -> None:
    copy = build_delivery_schedule_copy(
        cutoff_day=Weekday.WEDNESDAY,
        delivery_day=Weekday.FRIDAY,
    )
    answer = resolve_schedule_faq_answer(
        question="When is your delivery day?",
        stored_answer="We deliver on Saturday.",
        copy=copy,
    )
    assert "Friday" in answer
    assert "Saturday" not in answer
