from datetime import date, datetime, timedelta

from backend.database import query

THOUGHTS = (
    "You do not have to have it all figured out today. One small step is enough.",
    "Rest is not a reward for finishing everything. It is part of doing things well.",
    "It is okay to ask for help. Most people are glad to be asked.",
    "A difficult day is not a difficult life.",
    "Drink some water, stretch for a minute, and breathe out slowly. Then carry on.",
    "Progress is still progress, even when it is slow.",
    "Be as kind to yourself as you would be to a good friend.",
    "You have handled hard days before, and you can handle this one.",
    "A short walk outside can change how the rest of the day feels.",
    "Feelings come and go like weather. You do not have to act on every one.",
    "Doing your best looks different on different days, and that is fine.",
    "Sleep is one of the best study tools there is.",
    "Talking about how you feel is a sign of strength, not weakness.",
    "Break the big task into a very small first step, then only do that step.",
    "Comparison steals joy. Your pace is your own.",
    "Notice three things you can see, two you can hear and one you can feel.",
    "Mistakes are how everyone learns. They do not define you.",
    "A message to a friend today could make both of your days better.",
    "It is okay to say no to something so you can say yes to rest.",
    "You are more than your marks, your results or your to-do list.",
    "Take a moment to notice something that went right today, however small.",
)

MOODS = (
    (2, "rough", "Rough"),
    (4, "low", "Low"),
    (6, "okay", "Okay"),
    (8, "good", "Good"),
    (10, "great", "Great"),
)

MOOD_REPLIES = {
    "rough": "Thank you for being honest. Hard days happen. Writing a few lines, or talking to someone, can really help.",
    "low": "Thanks for checking in. Go gently today, and remember small things like water, food and rest count.",
    "okay": "Thanks for checking in. Okay is a perfectly good place to be.",
    "good": "Glad to hear it. Thanks for checking in.",
    "great": "That is lovely to hear. Enjoy it, and thanks for checking in.",
}


def thought_for_today(today=None):
    today = today or date.today()
    return THOUGHTS[today.timetuple().tm_yday % len(THOUGHTS)]


def mood_for_rating(rating):
    if rating is None:
        return None
    for value, key, label in MOODS:
        if rating <= value:
            return {"value": value, "key": key, "label": label, "reply": MOOD_REPLIES[key]}
    return None


def today_mood(student_id):
    row = query("SELECT mood_rating FROM wellness_log WHERE student_id = ? AND log_date = ?",
                (student_id, date.today().isoformat()), one=True)
    return mood_for_rating(row["mood_rating"]) if row else None


def week_strip(student_id):
    start = date.today() - timedelta(days=6)
    rows = query(
        "SELECT DATE(created_at) AS d FROM assessment WHERE student_id = ? AND DATE(created_at) >= ?"
        " UNION SELECT log_date FROM wellness_log WHERE student_id = ? AND log_date >= ?"
        " UNION SELECT DATE(started_at) FROM screening WHERE student_id = ? AND DATE(started_at) >= ?"
        " UNION SELECT DATE(started_at) FROM aptitude_attempt WHERE student_id = ? AND DATE(started_at) >= ?",
        (student_id, start.isoformat()) * 4)
    active = {str(r[0])[:10] for r in rows}
    days = []
    for offset in range(7):
        day = start + timedelta(days=offset)
        days.append({"label": day.strftime("%a")[0], "name": day.strftime("%A"),
                     "active": day.isoformat() in active, "today": offset == 6})
    return {"days": days, "count": sum(1 for d in days if d["active"])}


def pretty_today():
    now = datetime.now()
    return f"{now.strftime('%A')}, {now.day} {now.strftime('%B')}"
