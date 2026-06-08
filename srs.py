from datetime import date, timedelta


def next_review(repetitions: int, interval_days: float, ease: float, grade: int):
    """
    SM-2 simplified.
    grade: 0=nie znam, 1=średnio, 2=znam
    Returns (repetitions, interval_days, ease, due_date_str)
    """
    if grade == 0:
        repetitions = 0
        interval_days = 1.0
        ease = max(1.3, ease - 0.2)
    elif grade == 1:
        repetitions = max(0, repetitions - 1)
        interval_days = max(1.0, round(interval_days * 0.7, 1))
    else:
        if repetitions == 0:
            interval_days = 1.0
        elif repetitions == 1:
            interval_days = 3.0
        else:
            interval_days = round(interval_days * ease, 1)
        repetitions += 1
        ease = min(3.0, max(1.3, ease + 0.1))

    due = date.today() + timedelta(days=int(interval_days))
    return repetitions, interval_days, ease, due.isoformat()
