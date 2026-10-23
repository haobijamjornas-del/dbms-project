import json
import os
import random
import sqlite3
import sys
from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "mindcare.db")
SQL_DIR = os.path.join(BASE_DIR, "sql")
DATA_CSV = os.path.join(BASE_DIR, "data", "synthetic_stress_dataset.csv")
MODEL_DIR = os.path.join(BASE_DIR, "ml", "models")
HISTORY_ENDS_DAYS_AGO = 15

random.seed(7)

DEPARTMENTS = [
    ("CSE", "Computer Science & Engineering", "Dr. R. Venkatesan"),
    ("ECE", "Electronics & Communication Engg.", "Dr. Meenakshi Rao"),
    ("MEC", "Mechanical Engineering", "Dr. A. K. Bhattacharya"),
    ("CIV", "Civil Engineering", "Dr. Sunita Deshmukh"),
    ("BBA", "Business Administration", "Dr. Faisal Ahmed"),
    ("BIO", "Biotechnology", "Dr. Lalitha Krishnan"),
]

STRESS_LEVELS = [
    (0, "Low", 1, "#2E9E5B",
     "Language indicates stable or positive emotional state. Routine monitoring only.", 0),
    (1, "Medium", 2, "#E8A33D",
     "Early warning signs present. Suggest self-help resources and re-check in a week.", 0),
    (2, "High", 3, "#D64545",
     "Strong distress indicators. Requires counsellor review and follow-up.", 1),
]

THEMES = [
    ("academics",       "Academic Pressure",      "Academic",
     "Exams, grades, coursework load and academic competition."),
    ("burnout",         "Burnout & Exhaustion",   "Occupational",
     "Emotional depletion, loss of motivation, chronic fatigue."),
    ("family",          "Family Issues",          "Personal",
     "Conflict, expectations or illness within the family."),
    ("finance",         "Financial Stress",       "Financial",
     "Fees, loans, allowance shortfalls and money-related worry."),
    ("future_worry",    "Future Uncertainty",     "Personal",
     "Career direction, placements and fear about what comes next."),
    ("health",          "Physical Health",        "Health",
     "Illness, diet, exercise neglect and somatic complaints."),
    ("loneliness",      "Loneliness",             "Social",
     "Social isolation and lack of meaningful connection."),
    ("relationships",   "Relationships",          "Social",
     "Romantic and close interpersonal difficulties."),
    ("self_esteem",     "Self-Esteem",            "Personal",
     "Self-worth, self-criticism and body image concerns."),
    ("sleep",           "Sleep Disturbance",      "Health",
     "Insomnia, irregular sleep cycles and daytime tiredness."),
    ("social_anxiety",  "Social Anxiety",         "Social",
     "Fear of judgement and avoidance of social situations."),
    ("time_management", "Time Management",        "Academic",
     "Procrastination, missed deadlines and scheduling overload."),
    ("work",            "Work / Internship",      "Occupational",
     "Job, internship and workplace-related pressure."),
]

COUNSELLORS = [
    ("CNS-101", "Dr. Ananya Sharma",   "ananya.sharma@mindcare.edu",   "9810012345",
     "Clinical Psychology",       8),
    ("CNS-102", "Dr. Rajat Mehra",     "rajat.mehra@mindcare.edu",     "9810023456",
     "Cognitive Behavioural Therapy", 6),
    ("CNS-103", "Ms. Fatima Sheikh",   "fatima.sheikh@mindcare.edu",   "9810034567",
     "Student Counselling",       7),
    ("CNS-104", "Mr. Devendra Nair",   "devendra.nair@mindcare.edu",   "9810045678",
     "Career & Academic Guidance", 6),
    ("CNS-105", "Dr. Priya Balakrishnan", "priya.b@mindcare.edu",      "9810056789",
     "Anxiety & Mood Disorders",  5),
]

FIRST_NAMES = [
    "Aarav", "Ananya", "Rohan", "Ishita", "Karan", "Meera", "Siddharth", "Nandini",
    "Aditya", "Kavya", "Rahul", "Sneha", "Vikram", "Pooja", "Arjun", "Divya",
    "Nikhil", "Riya", "Harsh", "Tanya", "Manish", "Shreya", "Yash", "Aisha",
    "Chinmoy", "Jornas", "Ashbin", "Neha", "Sameer", "Lakshmi", "Imran", "Deepika",
    "Varun", "Anjali", "Kabir", "Swati", "Rishi", "Payal", "Tarun", "Bhavna",
    "Gaurav", "Ritika", "Aman", "Sanjana", "Pranav", "Kritika", "Dev", "Simran",
    "Abhinav", "Trisha", "Mohit", "Preeti", "Naveen", "Aditi", "Suraj", "Vaishnavi",
    "Akash", "Namrata", "Zaid", "Charu",
]
LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Reddy", "Nair", "Iyer", "Singh", "Das",
    "Goswami", "Haobijam", "Saji", "Kulkarni", "Banerjee", "Chatterjee", "Mishra",
    "Kapoor", "Malhotra", "Bose", "Pillai", "Joshi", "Rao", "Sinha", "Ghosh",
    "Menon", "Trivedi", "Bhatt", "Chauhan", "Dutta", "Khan", "Ahluwalia",
]

LEXICON = [
    ("hopeless", "Despair", 3.0, "negative"), ("worthless", "Self-Esteem", 3.0, "negative"),
    ("panic", "Anxiety", 2.8, "negative"), ("anxious", "Anxiety", 2.2, "negative"),
    ("overwhelmed", "Overload", 2.5, "negative"), ("exhausted", "Fatigue", 2.3, "negative"),
    ("burnout", "Fatigue", 2.6, "negative"), ("drained", "Fatigue", 2.2, "negative"),
    ("crushing", "Despair", 2.7, "negative"), ("crying", "Distress", 2.4, "negative"),
    ("insomnia", "Sleep", 2.3, "negative"), ("nightmares", "Sleep", 2.2, "negative"),
    ("lonely", "Isolation", 2.4, "negative"), ("isolated", "Isolation", 2.3, "negative"),
    ("alone", "Isolation", 1.8, "negative"), ("empty", "Despair", 2.5, "negative"),
    ("numb", "Despair", 2.6, "negative"), ("failing", "Academic", 2.2, "negative"),
    ("pressure", "Overload", 1.9, "negative"), ("deadline", "Overload", 1.5, "negative"),
    ("dread", "Anxiety", 2.5, "negative"), ("terrified", "Anxiety", 2.7, "negative"),
    ("useless", "Self-Esteem", 2.8, "negative"), ("hate", "Distress", 2.3, "negative"),
    ("cannot", "Distress", 1.4, "negative"), ("stuck", "Despair", 2.0, "negative"),
    ("lost", "Despair", 2.1, "negative"), ("broken", "Despair", 2.6, "negative"),
    ("suffocating", "Distress", 2.7, "negative"), ("trapped", "Despair", 2.5, "negative"),
    ("stressed", "Overload", 2.0, "negative"), ("worried", "Anxiety", 1.7, "negative"),
    ("tired", "Fatigue", 1.6, "negative"), ("struggling", "Distress", 2.1, "negative"),
    ("nervous", "Anxiety", 1.8, "negative"), ("guilty", "Self-Esteem", 2.0, "negative"),
    ("ashamed", "Self-Esteem", 2.3, "negative"), ("rejected", "Isolation", 2.2, "negative"),
    ("debt", "Financial", 1.9, "negative"), ("loans", "Financial", 1.7, "negative"),
    ("grateful", "Positive", 1.0, "positive"), ("hopeful", "Positive", 1.0, "positive"),
    ("calm", "Positive", 1.0, "positive"), ("confident", "Positive", 1.0, "positive"),
    ("balanced", "Positive", 1.0, "positive"), ("supported", "Positive", 1.0, "positive"),
    ("motivated", "Positive", 1.0, "positive"), ("improving", "Positive", 1.0, "positive"),
    ("refreshed", "Positive", 1.0, "positive"), ("productive", "Positive", 1.0, "positive"),
    ("proud", "Positive", 1.0, "positive"), ("relaxed", "Positive", 1.0, "positive"),
]


FOUR_POINT = [
    (0, "Not at all"),
    (1, "Several days"),
    (2, "More than half the days"),
    (3, "Nearly every day"),
]
FIVE_POINT = [
    (0, "Never"),
    (1, "Almost never"),
    (2, "Sometimes"),
    (3, "Fairly often"),
    (4, "Very often"),
]

INSTRUMENTS = [
    {
        "code": "PHQ-9", "name": "PHQ-9",
        "full_name": "Patient Health Questionnaire-9",
        "measures": "Depression", "recall_period": "Last 2 weeks",
        "option_max": 3, "score_max": 27, "weight": 0.30, "display_order": 1,
        "source_note": "Kroenke, Spitzer & Williams (2001). Free to reproduce.",
        "options": FOUR_POINT,
        "items": [
            ("Little interest or pleasure in doing things", 0, 0),
            ("Feeling down, depressed, or hopeless", 0, 0),
            ("Trouble falling or staying asleep, or sleeping too much", 0, 0),
            ("Feeling tired or having little energy", 0, 0),
            ("Poor appetite or overeating", 0, 0),
            ("Feeling bad about yourself, or that you are a failure, "
             "or have let yourself or your family down", 0, 0),
            ("Trouble concentrating on things, such as reading or "
             "following a lecture", 0, 0),
            ("Moving or speaking noticeably slowly, or the opposite - "
             "being so restless that you move around far more than usual", 0, 0),
            ("Thoughts that you would be better off dead, "
             "or of hurting yourself in some way", 0, 1),
        ],
        "bands": [
            ("Minimal",           0,  4, 1, "#2E9E5B",
             "No action needed beyond routine self-care. Re-screen if things change."),
            ("Mild",              5,  9, 2, "#7FB069",
             "Watchful waiting. Self-help resources and a re-screen in two weeks."),
            ("Moderate",         10, 14, 3, "#E8A33D",
             "A counselling appointment is recommended."),
            ("Moderately severe",15, 19, 4, "#E07A34",
             "Active treatment is indicated. Book a counsellor promptly."),
            ("Severe",           20, 27, 5, "#D64545",
             "Priority referral. Same-week professional contact strongly advised."),
        ],
    },
    {
        "code": "GAD-7", "name": "GAD-7",
        "full_name": "Generalised Anxiety Disorder-7",
        "measures": "Anxiety", "recall_period": "Last 2 weeks",
        "option_max": 3, "score_max": 21, "weight": 0.30, "display_order": 2,
        "source_note": "Spitzer, Kroenke, Williams & Lowe (2006). Free to reproduce.",
        "options": FOUR_POINT,
        "items": [
            ("Feeling nervous, anxious, or on edge", 0, 0),
            ("Not being able to stop or control worrying", 0, 0),
            ("Worrying too much about different things", 0, 0),
            ("Trouble relaxing", 0, 0),
            ("Being so restless that it is hard to sit still", 0, 0),
            ("Becoming easily annoyed or irritable", 0, 0),
            ("Feeling afraid as if something awful might happen", 0, 0),
        ],
        "bands": [
            ("Minimal",  0,  4, 1, "#2E9E5B",
             "Anxiety is within the typical range."),
            ("Mild",     5,  9, 2, "#7FB069",
             "Monitor. Breathing and grounding exercises often help at this level."),
            ("Moderate",10, 14, 3, "#E8A33D",
             "A counselling appointment is recommended."),
            ("Severe",  15, 21, 4, "#D64545",
             "Priority referral for anxiety management support."),
        ],
    },
    {
        "code": "PSS-10", "name": "PSS-10",
        "full_name": "Perceived Stress Scale-10",
        "measures": "Perceived stress", "recall_period": "Last month",
        "option_max": 4, "score_max": 40, "weight": 0.20, "display_order": 3,
        "source_note": "Cohen, Kamarck & Mermelstein (1983). Free for "
                       "educational and research use. Items 4, 5, 7 and 8 are "
                       "reverse-scored.",
        "options": FIVE_POINT,
        "items": [
            ("Been upset because of something that happened unexpectedly", 0, 0),
            ("Felt unable to control the important things in your life", 0, 0),
            ("Felt nervous and stressed", 0, 0),
            ("Felt confident about your ability to handle your personal problems", 1, 0),
            ("Felt that things were going your way", 1, 0),
            ("Found that you could not cope with all the things you had to do", 0, 0),
            ("Been able to control irritations in your life", 1, 0),
            ("Felt that you were on top of things", 1, 0),
            ("Been angered by things outside of your control", 0, 0),
            ("Felt difficulties piling up so high that you could not overcome them", 0, 0),
        ],
        "bands": [
            ("Low",      0, 13, 1, "#2E9E5B",
             "Perceived stress is low. Current coping strategies are working."),
            ("Moderate",14, 26, 2, "#E8A33D",
             "Moderate perceived stress. Worth reviewing workload and routines."),
            ("High",    27, 40, 3, "#D64545",
             "High perceived stress. Structured support is recommended."),
        ],
    },
]


def seed_instruments(conn):
    cur = conn.cursor()
    for ins in INSTRUMENTS:
        cur.execute(
            "INSERT INTO instrument (code, name, full_name, measures,"
            " recall_period, item_count, option_min, option_max, score_min,"
            " score_max, weight, display_order, source_note)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (ins["code"], ins["name"], ins["full_name"], ins["measures"],
             ins["recall_period"], len(ins["items"]), 0, ins["option_max"], 0,
             ins["score_max"], ins["weight"], ins["display_order"],
             ins["source_note"]))
        iid = cur.lastrowid
        cur.executemany(
            "INSERT INTO response_option (instrument_id, option_value, option_label)"
            " VALUES (?,?,?)",
            [(iid, v, lbl) for v, lbl in ins["options"]])
        cur.executemany(
            "INSERT INTO instrument_item (instrument_id, item_no, question_text,"
            " reverse_scored, is_critical) VALUES (?,?,?,?,?)",
            [(iid, n, text, rev, crit)
             for n, (text, rev, crit) in enumerate(ins["items"], start=1)])
        cur.executemany(
            "INSERT INTO severity_band (instrument_id, band_name, min_score,"
            " max_score, severity_rank, color_hex, guidance) VALUES (?,?,?,?,?,?,?)",
            [(iid, b[0], b[1], b[2], b[3], b[4], b[5]) for b in ins["bands"]])
    conn.commit()

    n_i = cur.execute("SELECT COUNT(*) FROM instrument").fetchone()[0]
    n_it = cur.execute("SELECT COUNT(*) FROM instrument_item").fetchone()[0]
    n_o = cur.execute("SELECT COUNT(*) FROM response_option").fetchone()[0]
    n_b = cur.execute("SELECT COUNT(*) FROM severity_band").fetchone()[0]
    crit = cur.execute("SELECT COUNT(*) FROM instrument_item WHERE is_critical=1").fetchone()[0]
    rev = cur.execute("SELECT COUNT(*) FROM instrument_item WHERE reverse_scored=1").fetchone()[0]
    print(f"    instruments={n_i}  items={n_it} ({rev} reverse-scored, "
          f"{crit} critical)  options={n_o}  bands={n_b}")


def seed_screenings(conn):
    cur = conn.cursor()
    items = cur.execute(
        "SELECT ii.item_id, ii.instrument_id, ii.reverse_scored, ii.is_critical,"
        "       i.option_max"
        "  FROM instrument_item ii JOIN instrument i"
        "    ON ii.instrument_id = i.instrument_id"
        " ORDER BY i.display_order, ii.item_no").fetchall()

    pool = cur.execute(
        "SELECT a.assessment_id, a.student_id, a.predicted_level, a.created_at"
        "  FROM assessment a"
        " ORDER BY RANDOM() LIMIT 150").fetchall()

    used_students = {}
    made = 0
    for asmt_id, student_id, level, created_at in pool:
        if used_students.get(student_id, 0) >= 3:
            continue
        used_students[student_id] = used_students.get(student_id, 0) + 1

        cur.execute(
            "INSERT INTO screening (student_id, status, started_at, assessment_id,"
            " is_baseline) VALUES (?,?,?,?,?)",
            (student_id, "IN_PROGRESS", created_at, asmt_id,
             1 if used_students[student_id] == 1 else 0))
        sid = cur.lastrowid

        rows = []
        for item_id, _instr, reverse, critical, opt_max in items:
            centre = {0: 0.18, 1: 0.45, 2: 0.72}[level] * opt_max
            val = int(round(random.gauss(centre, opt_max * 0.22)))
            if reverse:
                val = opt_max - val
            val = max(0, min(opt_max, val))
            if critical:
                val = random.choice([0, 0, 0, 0, 1, 2]) if level == 2 else 0
            rows.append((sid, item_id, val, created_at))

        cur.executemany(
            "INSERT INTO screening_response (screening_id, item_id, option_value,"
            " answered_at) VALUES (?,?,?,?)", rows)

        finished = (datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
                    + timedelta(minutes=random.randint(4, 12)))
        cur.execute("UPDATE screening SET status='COMPLETED', completed_at=?"
                    " WHERE screening_id=?",
                    (finished.strftime("%Y-%m-%d %H:%M:%S"), sid))
        made += 1

    conn.commit()
    bands = dict(cur.execute(
        "SELECT composite_band, COUNT(*) FROM screening"
        " WHERE status='COMPLETED' GROUP BY composite_band").fetchall())
    scored = cur.execute("SELECT COUNT(*) FROM screening_score").fetchone()[0]
    crit = cur.execute(
        "SELECT COUNT(*) FROM alert WHERE alert_type='CRITICAL_ITEM'").fetchone()[0]
    avg = cur.execute("SELECT ROUND(AVG(composite_score),1) FROM screening"
                      " WHERE status='COMPLETED'").fetchone()[0]
    print(f"    screenings={made}  responses={made * len(items)}")
    print(f"    subscale scores computed by trigger T8 = {scored}")
    print(f"    composite bands={bands}  mean composite={avg}")
    print(f"    alerts escalated by trigger T9 (critical item) = {crit}")


SUPPORT_TIPS = [
    (0, "COPING", [
        ("Keep a steady sleep window",
         "Go to bed and wake up at about the same time every day, weekends included. Most students need 7 to 9 hours."),
        ("Move for 20 minutes",
         "A brisk walk, a game, cycling or yoga on most days lifts your mood and burns off stress."),
        ("Three good things",
         "Before sleeping, write down three things that went well today, however small. It trains your attention toward what is working."),
        ("Screen-free edges of the day",
         "Keep your phone away for the first 30 minutes after waking and the last hour before bed."),
    ]),
    (0, "ADVICE", [
        ("Keep doing what works",
         "Your words read as settled. Notice which habits are helping and protect time for them."),
        ("Stay connected",
         "Regular time with friends and family is one of the strongest protections against stress."),
        ("Check in now and then",
         "A quick entry every week or two helps you notice early if things start to change."),
        ("Look out for others",
         "If a friend seems low, a simple \"how are you really doing?\" can make a big difference."),
    ]),
    (1, "COPING", [
        ("Box breathing",
         "Breathe in for 4 counts, hold for 4, breathe out for 4, hold for 4. Repeat for two or three minutes whenever you feel tense."),
        ("Shrink the task",
         "Work in 25-minute blocks with a 5-minute break in between. Start with the smallest possible step, not the whole assignment."),
        ("A daily worry window",
         "Give worries a fixed 15 minutes a day and write them down. When they come up at other times, remind yourself they have a slot later."),
        ("Wind down before bed",
         "Dim the lights, put screens away and do something calm for 30 to 60 minutes before sleep. Avoid caffeine after 3 pm."),
        ("Get some daylight",
         "10 to 15 minutes outdoors, ideally in the morning, helps both mood and sleep."),
    ]),
    (1, "ADVICE", [
        ("Talk to someone you trust",
         "Tell a friend, family member or mentor how you have been feeling. Saying it out loud often makes it lighter."),
        ("Book a counselling check-in",
         "Contact your college counselling cell or one of the helplines below in the next week or two. You do not have to be in crisis to ask for help."),
        ("Ask for practical help early",
         "If deadlines or workload are the cause, speak to your faculty or mentor now about priorities or extensions."),
        ("Re-check in a week",
         "Take the full assessment again in about a week to see whether things are easing."),
    ]),
    (2, "COPING", [
        ("5-4-3-2-1 grounding",
         "Name 5 things you can see, 4 you can touch, 3 you can hear, 2 you can smell and 1 you can taste. It pulls your mind back to the present moment."),
        ("Longer out-breaths",
         "Breathe in through your nose for 4 counts and out slowly through your mouth for 6. A longer breath out calms the body within a few minutes."),
        ("Cold water reset",
         "Splash cold water on your face or hold something cold for 30 seconds. It can quickly take the edge off a wave of panic."),
        ("Don't stay alone with it",
         "Go where people are, such as a friend's room or a common area, or call someone. Company makes intense feelings easier to ride out."),
        ("Make your space safe",
         "If you are having thoughts of hurting yourself, move away from anything you could use to do so, and call a helpline now."),
    ]),
    (2, "ADVICE", [
        ("Talk to someone today",
         "Call one of the 24×7 helplines below or tell someone you trust. You do not have to handle this on your own."),
        ("If you are in danger, call 112",
         "If you are at immediate risk or have already hurt yourself, call 112 or go to the nearest hospital emergency department now."),
        ("Say yes to support",
         "If a counsellor contacts you after this, please accept. You can also reach your college counselling cell directly."),
        ("Tell someone close",
         "Let a friend, roommate, warden or family member know how you are feeling, so you are not alone tonight."),
        ("Get a professional assessment",
         "Distress this strong, especially if it has lasted two weeks or more, deserves a proper assessment by a psychologist or psychiatrist."),
    ]),
]

HELPLINES = [
    ("Emergency services", "112", "112", "Emergency", "24×7",
     "Police, fire and ambulance. Call if you are in immediate danger or have hurt yourself.", 1, 1),
    ("Tele-MANAS (Govt. of India)", "14416 / 1800-89-14416", "14416", "National", "24×7, free",
     "Government mental health helpline, in English and 20 Indian languages.", 1, 1),
    ("Vandrevala Foundation", "+91 99996 66555", "+919999666555", "National", "24×7, call or WhatsApp",
     "Free crisis counselling for depression, anxiety and distress.", 1, 2),
    ("iCALL (TISS)", "+91 91529 87821", "+919152987821", "National", "Mon–Sat, 8 am–9 pm",
     "Free counselling by trained professionals.", 0, 3),
    ("Sumaitri", "011-46018404 / +91-9315767849", "01146018404", "Delhi NCR", "Daily, 12:30–5 pm",
     "Emotional support for anyone in distress or feeling suicidal.", 1, 1),
    ("Sanjivini Society for Mental Health", "011-4076 9002 / 011-4109 2787", "01140769002", "Delhi NCR",
     "Mon–Fri, 10 am–7:30 pm", "Free, confidential counselling for adults (18+).", 0, 2),
    ("Fortis Stress Helpline", "+91 83768 04102", "+918376804102", "Delhi NCR", "24×7",
     "Stress and mental health support from Fortis Healthcare specialists.", 0, 3),
    ("IHBAS (Govt. of NCT of Delhi)", "011-22114021", "01122114021", "Delhi NCR", "Hospital line",
     "Government psychiatric hospital, Dilshad Garden. Ask for Emergency Psychiatry (ext. 414).", 0, 4),
    ("Amity Centre for Guidance and Counselling", "1800-102-6489", "18001026489", "Noida",
     "24×7 toll-free", "Amity University's own counselling centre, H-6 Block near Gate 4A, Sector 125. Office 0120-439-1650, Mon–Sat.", 1, 1),
    ("District Government Combined Hospital", "+91 92664 15010", "+919266415010", "Noida",
     "Hospital line", "Government hospital, Sector 39, Noida. Ask for the psychiatry OPD.", 0, 2),
    ("GIMS Hospital, Greater Noida", "0120-2341024", "01202341024", "Noida", "Emergency control room",
     "Government Institute of Medical Sciences. Control room also on 73038 84224.", 0, 3),
]


def seed_support(conn):
    cur = conn.cursor()
    tips = [(level, tip_type, title, body, order)
            for level, tip_type, items in SUPPORT_TIPS
            for order, (title, body) in enumerate(items, start=1)]
    cur.executemany("INSERT INTO support_tip (level_code, tip_type, title, body, display_order)"
                    " VALUES (?,?,?,?,?)", tips)
    cur.executemany("INSERT INTO helpline (name, phone, dial, region, hours, service, is_crisis,"
                    " display_order) VALUES (?,?,?,?,?,?,?,?)", HELPLINES)
    conn.commit()
    print(f"    support tips={len(tips)}  helplines={len(HELPLINES)}")


COLOR_KEYS = ["red", "blue", "green", "orange", "purple", "pink"]

AGE_GROUPS = [
    ("JUNIOR", "Junior", 1, 10, 1, "Friendly, slower puzzles for children aged 1 to 10."),
    ("INTERMEDIATE", "Intermediate", 11, 20, 2, "Puzzles for ages 11 to 20, from school to early college."),
    ("ADVANCED", "Advanced", 21, 120, 3, "The most demanding puzzles, for ages 21 and over."),
]

TIER_STYLES = {1: [0], 2: [1, 2, 3], 3: [3, 4]}
PUZZLES_PER_TYPE = 8

PUZZLE_CATEGORIES = [
    ("LOGIC", "Logical reasoning", "Reasoning",
     "Read carefully and choose the answer that must be true.", 1),
    ("NUMBER", "Number series", "Numerical thinking",
     "Find the rule and choose the number that comes next.", 2),
    ("STROOP", "Colour-word focus", "Attention",
     "Choose the colour of the ink, not the word you read. Be quick.", 3),
    ("PATTERN", "Colour patterns", "Visual patterns",
     "Spot the repeating pattern and choose the missing colour.", 4),
    ("CODE", "Colour codes", "Working memory",
     "Use the colour key to crack the code.", 5),
]

APTITUDE_BANDS = [
    ("Keep practising", 0, 49.9, "#D9774A",
     "Today felt harder. Focus and memory dip when we are stressed, tired or busy, so be kind to yourself and try again another day."),
    ("Fair", 50, 69.9, "#E8A33D",
     "Not bad at all. A few puzzles slowed you down, which is completely normal. A little practice makes a real difference."),
    ("Good", 70, 84.9, "#3F4FD8",
     "A solid result. You handled most puzzles well, and the tricky ones will get easier with practice."),
    ("Excellent", 85, 100, "#2E9E5B",
     "Sharp and focused today. Your reasoning and attention were working really well."),
]

LOGIC_PUZZLES = {
    1: [
        ("Which of these animals can fly?", ["Dog", "Cow", "Parrot", "Goat"], "Parrot",
         "A parrot is a bird, and birds can fly. Dogs, cows and goats cannot."),
        ("Monday, Tuesday, Wednesday, ... Which day comes next?",
         ["Friday", "Thursday", "Sunday", "Monday"], "Thursday",
         "The days of the week go Monday, Tuesday, Wednesday, Thursday."),
        ("Which one does not belong with the others?", ["Apple", "Banana", "Carrot", "Mango"], "Carrot",
         "Apple, banana and mango are fruits. A carrot is a vegetable."),
        ("Pen is to write as knife is to ___.", ["Cook", "Cut", "Eat", "Sharp"], "Cut",
         "A pen is used to write, and a knife is used to cut."),
        ("All cats have tails. Tom is a cat. What must be true?",
         ["Tom has a tail", "Tom is black", "Tom can climb", "Tom is a kitten"], "Tom has a tail",
         "Every cat has a tail, and Tom is a cat, so Tom has a tail."),
        ("Riya is taller than Aman. Aman is taller than Dev. Who is the shortest?",
         ["Riya", "Aman", "Dev", "Cannot tell"], "Dev",
         "Riya is taller than Aman, who is taller than Dev, so Dev is the shortest."),
    ],
    2: [
        ("Book is to library as painting is to ___.", ["Artist", "Gallery", "Frame", "Brush"], "Gallery",
         "Books are kept in a library, and paintings are displayed in a gallery."),
        ("Which one is the odd one out?", ["Triangle", "Square", "Cube", "Circle"], "Cube",
         "A cube is a solid 3D shape. The others are flat 2D shapes."),
        ("Some doctors are singers. All singers are cheerful. Which statement must be true?",
         ["All doctors are cheerful", "Some doctors are cheerful", "No doctors are cheerful",
          "All cheerful people are singers"], "Some doctors are cheerful",
         "The doctors who are singers must be cheerful, so at least some doctors are cheerful."),
        ("A clock shows exactly 3:00. What is the angle between the hands?", ["45°", "90°", "120°", "180°"], "90°",
         "Each hour mark is 30°, and the hands are 3 hours apart: 3 × 30° = 90°."),
        ("If CAT is written as DBU, how is DOG written?", ["EPH", "FQI", "CNF", "EOG"], "EPH",
         "Each letter moves one step forward: D becomes E, O becomes P and G becomes H."),
        ("Asha sits left of Bala, Bala left of Chirag, Chirag left of Diya, and Diya left of Esha. Who sits in the middle?",
         ["Bala", "Chirag", "Diya", "Asha"], "Chirag",
         "The order is Asha, Bala, Chirag, Diya, Esha, so Chirag is in the middle."),
    ],
    3: [
        ("No students are lazy. Some lazy people are artists. Which conclusion follows?",
         ["All artists are students", "Some artists are not students", "No artists are lazy",
          "Some students are artists"], "Some artists are not students",
         "The artists who are lazy cannot be students, because no students are lazy."),
        ("A train leaves at 9:40 and arrives at 13:15. How long is the journey?",
         ["3 h 25 min", "3 h 35 min", "4 h 35 min", "3 h 45 min"], "3 h 35 min",
         "From 9:40 to 12:40 is 3 hours, and from 12:40 to 13:15 is 35 minutes."),
        ("In a code, FRIEND is written as HUMJTK. How is CANDLE written in the same code?",
         ["EDRIRL", "EDRJRL", "DCQHQK", "EDRIQL"], "EDRIRL",
         "The letters move forward by 2, 3, 4, 5, 6 and 7 places: C to E, A to D, N to R, D to I, L to R, E to L."),
        ("A is B's sister. C is B's mother. D is C's father. How is A related to D?",
         ["Daughter", "Granddaughter", "Niece", "Grandmother"], "Granddaughter",
         "C is the mother of A and B, and D is C's father, so A is D's granddaughter."),
        ("If the day after tomorrow is Sunday, what day was it yesterday?",
         ["Wednesday", "Thursday", "Friday", "Saturday"], "Thursday",
         "If the day after tomorrow is Sunday, today is Friday, so yesterday was Thursday."),
        ("Pointing to a photo, Neha says: \"His mother is the only daughter of my mother.\" How is Neha related to the man?",
         ["Sister", "Mother", "Aunt", "Grandmother"], "Mother",
         "The only daughter of Neha's mother is Neha herself, so Neha is the man's mother."),
    ],
}


def _number_options(answer, near, rng):
    pool = [answer + 1, answer - 1, answer + 2, answer - 2, answer + near, answer - near,
            answer + near + 1, answer + 10]
    pool = [x for x in dict.fromkeys(pool) if x > 0 and x != answer]
    bump = 3
    while len(pool) < 3:
        if answer + bump not in pool:
            pool.append(answer + bump)
        bump += 1
    choices = [answer] + rng.sample(pool, 3)
    rng.shuffle(choices)
    return [(str(c), None, 1 if c == answer else 0) for c in choices]


def number_series(rng, level):
    if level == 0:
        start, step = rng.randint(1, 10), rng.choice([1, 2, 5, 10])
        terms = [start + step * i for i in range(6)]
        rule = f"count on by {step} each time"
    elif level == 1:
        start, step = rng.randint(1, 20), rng.randint(2, 9)
        terms = [start + step * i for i in range(6)]
        rule = f"add {step} each time"
    elif level == 2:
        if rng.random() < 0.5:
            start, ratio = rng.randint(1, 5), rng.choice([2, 3])
            terms = [start * ratio ** i for i in range(6)]
            rule = f"multiply by {ratio} each time"
        else:
            start, step = rng.randint(10, 60), rng.randint(11, 25)
            terms = [start + step * i for i in range(6)]
            rule = f"add {step} each time"
    elif level == 3:
        if rng.random() < 0.5:
            extra = rng.randint(0, 5)
            terms = [n * n + extra for n in range(1, 7)]
            rule = "square numbers" + (f" plus {extra}" if extra else "")
        else:
            start, growth = rng.randint(1, 10), rng.choice([1, 2, 3])
            terms = [start]
            for i in range(1, 6):
                terms.append(terms[-1] + growth * i)
            rule = f"the gap grows by {growth} each time"
    else:
        kind = rng.choice(["sum", "turns", "cube"])
        if kind == "sum":
            terms = [rng.randint(1, 4), rng.randint(2, 6)]
            while len(terms) < 6:
                terms.append(terms[-1] + terms[-2])
            rule = "each number is the sum of the two before it"
        elif kind == "turns":
            a, step_a = rng.randint(1, 5), rng.randint(2, 4)
            b, step_b = rng.randint(5, 10), rng.randint(5, 10)
            terms = [a, b, a + step_a, b + step_b, a + 2 * step_a, b + 2 * step_b]
            rule = f"two series take turns: one adds {step_a}, the other adds {step_b}"
        else:
            extra = rng.randint(0, 3)
            terms = [n ** 3 + extra for n in range(1, 7)]
            rule = "cube numbers" + (f" plus {extra}" if extra else "")
    answer = terms[5]
    near = max(1, abs(terms[5] - terms[4]) // 2)
    elements = [("SEQUENCE", i + 1, None, str(t)) for i, t in enumerate(terms[:5])]
    elements.append(("SEQUENCE", 6, None, "?"))
    return {
        "prompt": "Which number comes next?",
        "explanation": f"The rule is: {rule}. So the next number is {answer}.",
        "time_limit": {0: 60, 1: 40, 2: 45, 3: 50, 4: 60}[level],
        "options": _number_options(answer, near, rng),
        "elements": elements,
    }


def colour_word(rng, level):
    ink = rng.choice(COLOR_KEYS)
    word = rng.choice([c for c in COLOR_KEYS if c != ink])
    count = {0: 3, 1: 3, 2: 4, 3: 4, 4: 5}[level]
    others = rng.sample([c for c in COLOR_KEYS if c not in (ink, word)], count - 2)
    choices = [ink, word] + others
    rng.shuffle(choices)
    return {
        "prompt": "What colour is the ink? Ignore what the word says.",
        "explanation": f"The word says {word.capitalize()}, but it is printed in {ink.capitalize()} ink.",
        "time_limit": {0: 15, 1: 12, 2: 10, 3: 8, 4: 6}[level],
        "options": [(c.capitalize(), None, 1 if c == ink else 0) for c in choices],
        "elements": [("WORD", 1, ink, word.upper())],
    }


def _colour_cycle(rng, length):
    while True:
        if length == 2:
            cycle = rng.sample(COLOR_KEYS, 2)
        elif length == 3:
            a, b, c = rng.sample(COLOR_KEYS, 3)
            cycle = rng.choice([[a, b, c], [a, a, b]])
        elif length == 4:
            a, b, c, d = rng.sample(COLOR_KEYS, 4)
            cycle = rng.choice([[a, b, c, d], [a, a, b, b], [a, b, a, c]])
        else:
            picks = rng.sample(COLOR_KEYS, 3)
            cycle = [rng.choice(picks) for _ in range(length)]
        shorter = [p for p in range(1, length) if length % p == 0]
        if len(set(cycle)) > 1 and not any(all(cycle[i] == cycle[i % p] for i in range(length)) for p in shorter):
            return cycle


def colour_pattern(rng, level):
    length = {0: 2, 1: 2, 2: 3, 3: 4, 4: 5}[level]
    repeats = 3 if level <= 1 else 2
    cycle = _colour_cycle(rng, length)
    total = length * repeats + (1 if level < 4 else 0)
    sequence = [cycle[i % length] for i in range(total)]
    blank = total - 1 if level < 4 else rng.randint(length, total - 1)
    answer = sequence[blank]
    distractors = [c for c in dict.fromkeys(sequence) if c != answer]
    distractors += [c for c in COLOR_KEYS if c not in sequence]
    choices = [answer] + distractors[:3]
    rng.shuffle(choices)
    elements = [("SEQUENCE", i + 1, None if i == blank else c, "?" if i == blank else None)
                for i, c in enumerate(sequence)]
    return {
        "prompt": "Which colour comes next?" if level < 4 else "Which colour is missing?",
        "explanation": f"The pattern repeats every {length} colours: "
                       + ", ".join(c.capitalize() for c in cycle) + ".",
        "time_limit": {0: 40, 1: 30, 2: 30, 3: 35, 4: 40}[level],
        "options": [(c.capitalize(), c, 1 if c == answer else 0) for c in choices],
        "elements": elements,
    }


def _code_options(answer, extras, rng):
    pool = [x for x in dict.fromkeys(extras) if x > 0 and x != answer]
    bump = 1
    while len(pool) < 3:
        if answer + bump not in pool:
            pool.append(answer + bump)
        bump += 1
    choices = [answer] + rng.sample(pool, 3)
    rng.shuffle(choices)
    return [(str(c), None, 1 if c == answer else 0) for c in choices]


def colour_code(rng, level):
    size = {0: 3, 1: 4, 2: 4, 3: 5, 4: 6}[level]
    colours = rng.sample(COLOR_KEYS, size)
    values = dict(zip(colours, rng.sample(range(1, 10) if level else range(1, 6), size)))
    key = [("KEY", i + 1, c, str(values[c])) for i, c in enumerate(colours)]
    if level == 0:
        seq = rng.sample(colours, 2)
        digits = [values[c] for c in seq]
        answer = sum(digits)
        extras = [answer + 1, answer - 1, answer + 2, digits[0], digits[1]]
        joins = [None, "+"]
        prompt = "Add the numbers for these two colours."
        explanation = (f"{seq[0].capitalize()} is {digits[0]} and {seq[1].capitalize()} is {digits[1]}, "
                       f"so {digits[0]} + {digits[1]} = {answer}.")
    elif level in (1, 2):
        seq = rng.sample(colours, level + 1)
        digits = [values[c] for c in seq]
        answer = int("".join(map(str, digits)))
        swapped = digits[:]
        swapped[0], swapped[1] = swapped[1], swapped[0]
        extras = [int("".join(map(str, reversed(digits)))), int("".join(map(str, swapped))),
                  answer + 10, answer - 1, sum(digits)]
        joins = [None] * len(seq)
        prompt = "Use the key to turn these colours into a number."
        explanation = ("Read each colour in order: "
                       + ", ".join(f"{c.capitalize()} = {values[c]}" for c in seq)
                       + f". Together they make {answer}.")
    elif level == 3:
        seq = [rng.choice(colours) for _ in range(4)]
        digits = [values[c] for c in seq]
        answer = sum(digits)
        extras = [answer + 1, answer - 1, answer + 2, answer - digits[0], answer + digits[-1]]
        joins = [None, "+", "+", "+"]
        prompt = "Add up the values of these colours."
        explanation = " + ".join(map(str, digits)) + f" = {answer}."
    else:
        seq = rng.sample(colours, 3)
        a, b, c = (values[x] for x in seq)
        answer = a * b + c
        extras = [a * (b + c), a + b * c, answer + 1, answer - 1, a * b]
        joins = [None, "×", "+"]
        prompt = "Work it out: first colour × second colour + third colour."
        explanation = f"{a} × {b} + {c} = {answer}."
    return {
        "prompt": prompt,
        "explanation": explanation,
        "time_limit": {0: 60, 1: 40, 2: 45, 3: 50, 4: 60}[level],
        "options": _code_options(answer, extras, rng),
        "elements": key + [("SEQUENCE", i + 1, c, joins[i]) for i, c in enumerate(seq)],
    }


def build_puzzle_bank(seed=2026):
    rng = random.Random(seed)
    bank = []
    makers = [("NUMBER", number_series), ("STROOP", colour_word),
              ("PATTERN", colour_pattern), ("CODE", colour_code)]
    for level in (1, 2, 3):
        for prompt, choices, correct, explanation in LOGIC_PUZZLES[level]:
            shuffled = choices[:]
            rng.shuffle(shuffled)
            bank.append({"category": "LOGIC", "level": level, "prompt": prompt,
                         "explanation": explanation, "time_limit": 90 if level == 1 else 60,
                         "elements": [],
                         "options": [(c, None, 1 if c == correct else 0) for c in shuffled]})
        for code, maker in makers:
            seen, made = set(), 0
            while made < PUZZLES_PER_TYPE:
                puzzle = maker(rng, rng.choice(TIER_STYLES[level]))
                signature = (puzzle["prompt"], tuple(puzzle["elements"]))
                if signature in seen:
                    continue
                seen.add(signature)
                puzzle.update(category=code, level=level)
                bank.append(puzzle)
                made += 1
    return bank


def seed_aptitude_reference(conn):
    cur = conn.cursor()
    cur.executemany("INSERT INTO age_group (code, label, min_age, max_age, difficulty, description)"
                    " VALUES (?,?,?,?,?,?)", AGE_GROUPS)
    cur.executemany("INSERT INTO puzzle_category (code, name, skill, instructions, display_order)"
                    " VALUES (?,?,?,?,?)", PUZZLE_CATEGORIES)
    cur.executemany("INSERT INTO aptitude_band (label, min_pct, max_pct, color_hex, message)"
                    " VALUES (?,?,?,?,?)", APTITUDE_BANDS)
    conn.commit()


def seed_aptitude(conn):
    seed_aptitude_reference(conn)
    seed_puzzle_bank(conn)


def seed_puzzle_bank(conn):
    cur = conn.cursor()
    categories = dict(cur.execute("SELECT code, category_id FROM puzzle_category").fetchall())
    groups = dict(cur.execute("SELECT difficulty, age_group_id FROM age_group").fetchall())
    bank = build_puzzle_bank()
    for puzzle in bank:
        cur.execute("INSERT INTO puzzle (category_id, age_group_id, prompt, explanation, time_limit_sec)"
                    " VALUES (?,?,?,?,?)",
                    (categories[puzzle["category"]], groups[puzzle["level"]], puzzle["prompt"],
                     puzzle["explanation"], puzzle["time_limit"]))
        puzzle_id = cur.lastrowid
        cur.executemany("INSERT INTO puzzle_option (puzzle_id, label, color_key, is_correct, display_order)"
                        " VALUES (?,?,?,?,?)",
                        [(puzzle_id, label, colour, correct, order)
                         for order, (label, colour, correct) in enumerate(puzzle["options"], start=1)])
        cur.executemany("INSERT INTO puzzle_element (puzzle_id, role, position, color_key, text_value)"
                        " VALUES (?,?,?,?,?)",
                        [(puzzle_id, role, position, colour, text)
                         for role, position, colour, text in puzzle["elements"]])
    conn.commit()
    options = cur.execute("SELECT COUNT(*) FROM puzzle_option o JOIN puzzle p USING (puzzle_id)"
                          " WHERE p.is_active = 1").fetchone()[0]
    print(f"    age groups={len(AGE_GROUPS)}  puzzle types={len(PUZZLE_CATEGORIES)}  "
          f"puzzles={len(bank)}  answer options={options}")


def _age_on(dob, when):
    if not dob:
        return None
    born = datetime.strptime(str(dob)[:10], "%Y-%m-%d")
    return when.year - born.year - ((when.month, when.day) < (born.month, born.day))


def _stamp_ms(moment):
    return moment.strftime("%Y-%m-%d %H:%M:%S.") + f"{moment.microsecond // 1000:03d}"


def seed_aptitude_attempts(conn, anchor=None, count=40):
    cur = conn.cursor()
    anchor = anchor or (datetime.now() - timedelta(days=HISTORY_ENDS_DAYS_AGO))
    groups = cur.execute("SELECT age_group_id, min_age, max_age FROM age_group ORDER BY difficulty").fetchall()
    categories = [r[0] for r in cur.execute("SELECT category_id FROM puzzle_category ORDER BY display_order")]
    students = cur.execute("SELECT student_id, dob FROM student WHERE student_id <= 60"
                           " ORDER BY RANDOM() LIMIT ?", (count,)).fetchall()
    moments = sorted(anchor - timedelta(days=random.randint(0, 60), hours=random.randint(0, 9),
                                        minutes=random.randint(25, 59)) for _ in students)
    for (student_id, dob), started in zip(students, moments):
        age = _age_on(dob, started)
        group_id = next((g[0] for g in groups if age is not None and g[1] <= age <= g[2]), groups[1][0])
        cur.execute("INSERT INTO aptitude_attempt (student_id, age_group_id, age_at_attempt, started_at)"
                    " VALUES (?,?,?,?)", (student_id, group_id, age, started.strftime("%Y-%m-%d %H:%M:%S")))
        attempt_id = cur.lastrowid
        recent = cur.execute("SELECT AVG(predicted_level) FROM (SELECT predicted_level FROM assessment"
                             " WHERE student_id = ? AND created_at <= ? ORDER BY created_at DESC LIMIT 5)",
                             (student_id, started.strftime("%Y-%m-%d %H:%M:%S"))).fetchone()[0]
        skill = min(0.95, max(0.4, random.gauss(0.84 - 0.12 * (recent if recent is not None else 1), 0.08)))
        clock, position = started, 0
        for category_id in categories:
            picks = cur.execute("SELECT puzzle_id, time_limit_sec FROM puzzle WHERE category_id = ?"
                                " AND age_group_id = ? AND is_active = 1 ORDER BY RANDOM() LIMIT 3",
                                (category_id, group_id)).fetchall()
            for puzzle_id, limit in picks:
                position += 1
                shown = clock + timedelta(seconds=random.uniform(1.5, 4))
                spent = int(min(limit * 1000, max(900, random.gauss(limit * 450, limit * 150))))
                clock = shown + timedelta(milliseconds=spent)
                cur.execute("INSERT INTO aptitude_item (attempt_id, position, puzzle_id, shown_at)"
                            " VALUES (?,?,?,?)", (attempt_id, position, puzzle_id, _stamp_ms(shown)))
                if random.random() < 0.03:
                    cur.execute("UPDATE aptitude_item SET answered_at = ?, response_ms = ?"
                                " WHERE attempt_id = ? AND position = ?",
                                (_stamp_ms(clock), limit * 1000, attempt_id, position))
                    continue
                options = cur.execute("SELECT option_id, is_correct FROM puzzle_option WHERE puzzle_id = ?",
                                      (puzzle_id,)).fetchall()
                right = next(o for o, ok in options if ok)
                wrong = [o for o, ok in options if not ok]
                chosen = right if random.random() < skill else random.choice(wrong)
                cur.execute("UPDATE aptitude_item SET selected_option_id = ?, response_ms = ?, answered_at = ?"
                            " WHERE attempt_id = ? AND position = ?",
                            (chosen, spent, _stamp_ms(clock), attempt_id, position))
        cur.execute("UPDATE aptitude_attempt SET status = 'COMPLETED', completed_at = ? WHERE attempt_id = ?",
                    (clock.strftime("%Y-%m-%d %H:%M:%S"), attempt_id))
    conn.commit()
    done = cur.execute("SELECT COUNT(*), ROUND(AVG(accuracy_pct), 1) FROM aptitude_attempt"
                       " WHERE status = 'COMPLETED'").fetchone()
    bands = dict(cur.execute("SELECT b.label, COUNT(*) FROM aptitude_attempt a JOIN aptitude_band b"
                             " ON a.band_id = b.band_id GROUP BY b.label").fetchall())
    print(f"    puzzle attempts={done[0]}  mean accuracy={done[1]}%  scored by triggers T11-T14: {bands}")


PLACES = [
    ("HOSPITAL", "Hospital", "Injuries, sudden illness and anything that needs a doctor or an ambulance.", "#E5484D", 1),
    ("POLICE", "Police station", "Crime, danger from other people, lost children and online fraud.", "#3E63DD", 2),
    ("FIRE", "Fire station", "Fire, smoke, gas leaks, sparking wires and dangerous chemicals.", "#F17A1A", 3),
    ("SCHOOL", "School", "Bullying, lessons, and problems with classes or the college office.", "#E8A33D", 4),
    ("VET", "Vet clinic", "Animals that are hurt, sick or poisoned.", "#2F9E62", 5),
    ("COUNSEL", "Counselling centre", "Feelings that are too heavy to carry alone: sadness, worry and stress.", "#8E4EC6", 6),
]

RESCUE_TIME = {1: 30, 2: 20, 3: 15}
RESCUE_ROUNDS = 8

SCENARIOS = [
    (1, "🚗", "Road accident", "A car hit a cyclist. The cyclist is hurt and bleeding on the road.", "HOSPITAL",
     "People who are hurt need doctors. An ambulance takes them to hospital. Call 112.", 3, 1),
    (1, "🔥", "House on fire", "Smoke and flames are coming out of a house window.", "FIRE",
     "Firefighters put out fires. Get out, stay out, and call 112.", 3, 0),
    (1, "🐶", "Hurt puppy", "A puppy has hurt its leg and is limping.", "VET",
     "A vet is a doctor for animals.", 1, 0),
    (1, "👜", "Stolen bag", "Someone snatched a lady's bag and ran away.", "POLICE",
     "The police catch thieves and help people who have been robbed.", 2, 0),
    (1, "🤕", "Fell off the swing", "A child fell off a swing and cannot move their arm.", "HOSPITAL",
     "A doctor can check whether the arm is broken and fix it.", 2, 0),
    (1, "😟", "Bullied at school", "Some older kids keep teasing your friend at break time.", "SCHOOL",
     "Tell a teacher. Teachers stop bullying at school.", 1, 0),
    (1, "🧒", "Lost child", "A little child is crying alone in the market and cannot find their parents.", "POLICE",
     "Police help lost children find their families. Stay with the child near a shop counter.", 2, 0),
    (1, "🐦", "Injured bird", "A bird has a hurt wing and cannot fly.", "VET",
     "A vet can look after hurt birds and animals.", 1, 0),
    (1, "😢", "Feeling sad", "You have felt sad and alone for many days and you do not know why.", "COUNSEL",
     "Counsellors listen and help with big feelings. You can also tell a parent or a teacher.", 1, 0),
    (1, "🗑️", "Bin on fire", "A rubbish bin outside your building has caught fire.", "FIRE",
     "Keep away from the smoke and tell an adult to call the fire service.", 2, 0),
    (1, "📚", "Help with lessons", "Your maths lesson was confusing and there is a test soon.", "SCHOOL",
     "Teachers are happy to explain a lesson again. Just ask.", 1, 0),
    (1, "🤒", "Very high fever", "Your little brother has a very high fever and is very sleepy.", "HOSPITAL",
     "A high fever with sleepiness needs a doctor quickly.", 2, 0),
    (1, "🚲", "Bicycle stolen", "Your bicycle was stolen from outside the shop.", "POLICE",
     "Tell the police. They keep records and look for stolen things.", 1, 0),

    (2, "🏍️", "Accident on the highway", "Two bikes collided. One rider is lying on the road and is not waking up.",
     "HOSPITAL", "An unconscious person needs an ambulance straight away. Call 112 and do not move them "
     "unless they are in danger.", 3, 1),
    (2, "⚡", "Sparking wires", "Electric wires are sparking and a small fire has started near a shop.", "FIRE",
     "Fire and electricity together need firefighters. Keep well away and call 112.", 3, 0),
    (2, "📱", "Online threat", "A stranger online says they will post your photos unless you pay them.", "POLICE",
     "This is a crime. Save the messages, do not pay, and report it to the police or the cyber crime "
     "helpline 1930.", 2, 0),
    (2, "🐕", "Dog hit by a scooter", "A street dog was hit by a scooter and is bleeding.", "VET",
     "An injured animal needs a vet or an animal rescue service.", 2, 0),
    (2, "😰", "Panic before exams", "Your heart races, you cannot sleep, and you are sure you will fail every exam.",
     "COUNSEL", "Exam anxiety is common and it can be helped. A counsellor can teach you ways to calm your "
     "body and plan your studies.", 1, 0),
    (2, "🤢", "Food poisoning", "After eating at a stall, your friend keeps vomiting and feels faint.", "HOSPITAL",
     "Repeated vomiting and feeling faint can mean dangerous loss of fluids. See a doctor.", 2, 0),
    (2, "💨", "Smell of gas", "There is a strong smell of cooking gas in the kitchen.", "FIRE",
     "Do not switch anything on or off. Open the windows, get everyone out, and call the fire service "
     "or the LPG emergency line 1906.", 3, 0),
    (2, "👀", "Someone following you", "A stranger has followed you home from school for three days.", "POLICE",
     "Tell a trusted adult and the police. You can call 112 at any time.", 2, 0),
    (2, "😞", "Friend has given up", "Your friend has stopped eating properly and says nothing matters any more.",
     "COUNSEL", "Stay with them, listen, and help them talk to a counsellor. If they talk about hurting "
     "themselves, call 112 or Tele-MANAS 14416.", 2, 0),
    (2, "📖", "Falling behind", "You have missed several classes and are falling behind in one subject.", "SCHOOL",
     "Talk to your teacher or class advisor. They can arrange extra help.", 1, 0),
    (2, "🚨", "Shop break-in", "At night you see two people breaking the lock of a shop.", "POLICE",
     "Do not go near them. Call 112 from a safe place.", 3, 0),
    (2, "🦶", "Sports injury", "During a match a player twisted their ankle badly and it is swelling fast.",
     "HOSPITAL", "A badly swollen ankle may be broken. It needs an X-ray at a hospital.", 2, 0),
    (2, "🐄", "Cow with a deep cut", "A cow on the road has a deep cut on its leg.", "VET",
     "Large animals need a vet too. Many towns have an animal helpline.", 1, 0),
    (2, "💬", "Rumours in the group chat", "Classmates are spreading rumours about you in the class group chat.",
     "SCHOOL", "Take screenshots and tell a teacher. Schools must act on bullying, including online.", 1, 0),

    (3, "🚶", "Pedestrian hit at a junction", "A pedestrian was hit by a car. They are awake but cannot feel their legs.",
     "HOSPITAL", "This could be a spinal injury. Keep them still, do not move them, and call 112 for an "
     "ambulance.", 3, 1),
    (3, "🏢", "Smoke in the stairwell", "The fire alarm is ringing and the office stairwell is filling with smoke.",
     "FIRE", "Use the stairs, never the lift. Stay low under the smoke and call 112 once you are outside.", 3, 0),
    (3, "💳", "Bank fraud call", "You shared an OTP on a phone call and money has just left your account.", "POLICE",
     "Call the cyber crime helpline 1930 at once. Reporting within the first hour gives the best chance of "
     "stopping the money.", 2, 0),
    (3, "💔", "Crushing chest pain", "Your uncle suddenly has crushing chest pain spreading to his left arm, and he is sweating.",
     "HOSPITAL", "These are signs of a heart attack. Call 112 at once; every minute matters.", 3, 0),
    (3, "🧪", "Chemical spill", "A chemical has spilled in the lab and the fumes are making people cough.", "FIRE",
     "Leave the area and close the door. The fire service handles dangerous chemicals.", 3, 0),
    (3, "🌧️", "Colleague struggling", "A colleague has withdrawn for weeks, is drinking more, and says life feels pointless.",
     "COUNSEL", "Ask how they are, listen, and help them reach a counsellor or Tele-MANAS 14416. If they have "
     "a plan to harm themselves, it is an emergency: call 112.", 2, 0),
    (3, "🐕", "Dog bite", "A stray dog bit a child in the park and the wound is bleeding.", "HOSPITAL",
     "The child needs a doctor, not a vet. Wash the wound with soap and water for 15 minutes and get the "
     "rabies vaccine at a hospital the same day.", 3, 0),
    (3, "🐾", "Pet ate poison", "Your dog has eaten rat poison from the storeroom.", "VET",
     "Go to a vet immediately. Do not try to make the dog sick unless the vet tells you to.", 3, 0),
    (3, "🏠", "Cry for help next door", "You hear a neighbour screaming for help and things being smashed.", "POLICE",
     "Call 112. The police must respond to violence at home. The women's helpline is 181.", 3, 0),
    (3, "🥱", "Burnt out", "For months you have felt exhausted, cannot concentrate and dread every morning.",
     "COUNSEL", "Long-lasting exhaustion and dread are signs of burnout. A counsellor can help you find the "
     "cause and a way back.", 1, 0),
    (3, "🗂️", "Missed registration", "Your course registration was missed and you might lose a semester.", "SCHOOL",
     "The college office or your academic advisor handles registration and appeals.", 1, 0),
    (3, "👵", "Elderly neighbour fell", "An elderly neighbour fell in the bathroom. She is awake but cannot get up and her hip hurts.",
     "HOSPITAL", "A painful hip after a fall may be a fracture. Keep her warm and still and call an ambulance.", 2, 0),
    (3, "🦉", "Owl with a broken wing", "An owl with a broken wing is lying on your balcony.", "VET",
     "A vet or wildlife rescue can treat it. Keep it in a covered box somewhere quiet and dark.", 1, 0),
    (3, "👂", "Student cannot hear lectures", "A new student has a hearing problem and cannot follow lectures.",
     "SCHOOL", "The school or college must make reasonable adjustments, such as a front seat and shared notes.", 1, 0),
]


def seed_game(conn):
    cur = conn.cursor()
    cur.executemany("INSERT INTO place (code, name, helps_with, color_hex, display_order)"
                    " VALUES (?,?,?,?,?)", PLACES)
    places = dict(cur.execute("SELECT code, place_id FROM place").fetchall())
    groups = dict(cur.execute("SELECT difficulty, age_group_id FROM age_group").fetchall())
    cur.executemany(
        "INSERT INTO scenario (age_group_id, correct_place_id, icon, title, story, explanation,"
        " urgency, time_limit_sec, is_opening) VALUES (?,?,?,?,?,?,?,?,?)",
        [(groups[tier], places[place], icon, title, story, explanation, urgency, RESCUE_TIME[tier], opening)
         for tier, icon, title, story, place, explanation, urgency, opening in SCENARIOS])
    conn.commit()
    print(f"    places={len(PLACES)}  scenarios={len(SCENARIOS)}  rounds per game={RESCUE_ROUNDS}")


def seed_game_demo(conn, anchor=None, count=30):
    cur = conn.cursor()
    anchor = anchor or (datetime.now() - timedelta(days=HISTORY_ENDS_DAYS_AGO))
    groups = cur.execute("SELECT age_group_id, min_age, max_age FROM age_group ORDER BY difficulty").fetchall()
    places = [r[0] for r in cur.execute("SELECT place_id FROM place ORDER BY display_order")]
    students = cur.execute("SELECT student_id, dob FROM student WHERE student_id <= 60"
                           " ORDER BY RANDOM() LIMIT ?", (count,)).fetchall()
    moments = sorted(anchor - timedelta(days=random.randint(0, 50), hours=random.randint(0, 9),
                                        minutes=random.randint(25, 59)) for _ in students)
    for (student_id, dob), started in zip(students, moments):
        age = _age_on(dob, started)
        group_id = next((g[0] for g in groups if age is not None and g[1] <= age <= g[2]), groups[1][0])
        cur.execute("INSERT INTO rescue_game (student_id, age_group_id, age_at_play, started_at) VALUES (?,?,?,?)",
                    (student_id, group_id, age, started.strftime("%Y-%m-%d %H:%M:%S")))
        game_id = cur.lastrowid
        picks = cur.execute("SELECT scenario_id, correct_place_id, time_limit_sec FROM scenario"
                            " WHERE age_group_id = ? AND is_active = 1"
                            " ORDER BY is_opening DESC, RANDOM() LIMIT ?", (group_id, RESCUE_ROUNDS)).fetchall()
        recent = cur.execute("SELECT AVG(predicted_level) FROM (SELECT predicted_level FROM assessment"
                             " WHERE student_id = ? AND created_at <= ? ORDER BY created_at DESC LIMIT 5)",
                             (student_id, started.strftime("%Y-%m-%d %H:%M:%S"))).fetchone()[0]
        skill = min(0.97, max(0.5, random.gauss(0.9 - 0.08 * (recent if recent is not None else 1), 0.08)))
        clock = started
        for round_no, (scenario_id, correct_place, limit) in enumerate(picks, start=1):
            shown = clock + timedelta(seconds=random.uniform(2, 6))
            spent = int(min(limit * 1000, max(1200, random.gauss(limit * 380, limit * 150))))
            clock = shown + timedelta(milliseconds=spent)
            cur.execute("INSERT INTO rescue_round (game_id, round_no, scenario_id, shown_at) VALUES (?,?,?,?)",
                        (game_id, round_no, scenario_id, _stamp_ms(shown)))
            if random.random() < 0.03:
                cur.execute("UPDATE rescue_round SET answered_at = ?, response_ms = ?"
                            " WHERE game_id = ? AND round_no = ?",
                            (_stamp_ms(clock), limit * 1000, game_id, round_no))
                continue
            chosen = correct_place if random.random() < skill else random.choice(
                [p for p in places if p != correct_place])
            cur.execute("UPDATE rescue_round SET response_ms = ?, answered_at = ?, chosen_place_id = ?"
                        " WHERE game_id = ? AND round_no = ?",
                        (spent, _stamp_ms(clock), chosen, game_id, round_no))
        cur.execute("UPDATE rescue_game SET status = 'COMPLETED', completed_at = ? WHERE game_id = ?",
                    (clock.strftime("%Y-%m-%d %H:%M:%S"), game_id))
    conn.commit()
    done = cur.execute("SELECT COUNT(*), ROUND(AVG(accuracy_pct), 1), ROUND(AVG(score), 1) FROM rescue_game"
                       " WHERE status = 'COMPLETED'").fetchone()
    stars = dict(cur.execute("SELECT stars, COUNT(*) FROM rescue_game WHERE status = 'COMPLETED'"
                             " GROUP BY stars").fetchall())
    print(f"    rescue games={done[0]}  mean accuracy={done[1]}%  mean score={done[2]}"
          f"  stars given by trigger T18: {stars}")


APTITUDE_TABLES = ["age_group", "puzzle_category", "aptitude_band", "puzzle", "puzzle_option",
                   "puzzle_element", "aptitude_attempt", "aptitude_item"]


def _rows(conn, table):
    cur = conn.execute(f"SELECT * FROM {table}")
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _insert(conn, table, row):
    cols = list(row)
    conn.execute(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                 [row[c] for c in cols])


def migrate_age_levels(conn):
    old = {t: _rows(conn, t) for t in APTITUDE_TABLES}
    used = {i["puzzle_id"] for i in old["aptitude_item"]}
    run_sql_file(conn, "07_aptitude_sqlite.sql")
    seed_aptitude_reference(conn)

    by_difficulty = {min(d, len(AGE_GROUPS)): gid for d, gid in
                     conn.execute("SELECT difficulty, age_group_id FROM age_group")}
    ranges = conn.execute("SELECT age_group_id, min_age, max_age FROM age_group ORDER BY difficulty").fetchall()
    old_difficulty = {g["age_group_id"]: min(g["difficulty"], len(AGE_GROUPS)) for g in old["age_group"]}
    category = {c["category_id"]: c["code"] for c in old["puzzle_category"]}
    new_category = dict(conn.execute("SELECT code, category_id FROM puzzle_category"))
    band = {b["band_id"]: b["label"] for b in old["aptitude_band"]}
    new_band = dict(conn.execute("SELECT label, band_id FROM aptitude_band"))

    kept = [p for p in old["puzzle"] if p["puzzle_id"] in used]
    for p in kept:
        _insert(conn, "puzzle", dict(p, is_active=0, category_id=new_category[category[p["category_id"]]],
                                     age_group_id=by_difficulty[old_difficulty[p["age_group_id"]]]))
    for table in ("puzzle_option", "puzzle_element"):
        for row in old[table]:
            if row["puzzle_id"] in used:
                _insert(conn, table, row)
    conn.commit()
    seed_puzzle_bank(conn)

    for a in old["aptitude_attempt"]:
        age = a["age_at_attempt"]
        group = next((gid for gid, lo, hi in ranges if age is not None and lo <= age <= hi),
                     by_difficulty[old_difficulty[a["age_group_id"]]])
        _insert(conn, "aptitude_attempt", dict(a, age_group_id=group,
                                               band_id=new_band.get(band.get(a["band_id"]))))
    for item in old["aptitude_item"]:
        _insert(conn, "aptitude_item", item)
    conn.commit()
    print(f"    kept {len(old['aptitude_attempt'])} puzzle sets and the {len(kept)} retired puzzles they used;"
          f" {len(old['puzzle']) - len(kept)} unused old puzzles removed")


def run_sql_file(conn, filename):
    with open(os.path.join(SQL_DIR, filename)) as fh:
        conn.executescript(fh.read())
    print(f"    executed {filename}")


def seed_master(conn):
    cur = conn.cursor()
    cur.executemany(
        "INSERT INTO department (dept_code, dept_name, hod_name) VALUES (?,?,?)",
        DEPARTMENTS)
    cur.executemany(
        "INSERT INTO stress_level (level_code, level_name, severity_rank, color_hex,"
        " description, requires_alert) VALUES (?,?,?,?,?,?)", STRESS_LEVELS)
    cur.executemany(
        "INSERT INTO theme (theme_code, theme_name, category, description)"
        " VALUES (?,?,?,?)", THEMES)
    cur.executemany(
        "INSERT INTO counsellor (emp_code, full_name, email, phone, specialization,"
        " max_daily_slots) VALUES (?,?,?,?,?,?)", COUNSELLORS)
    cur.executemany(
        "INSERT INTO keyword_lexicon (word, category, weight, polarity)"
        " VALUES (?,?,?,?)", LEXICON)
    conn.commit()
    print(f"    departments={len(DEPARTMENTS)}  levels={len(STRESS_LEVELS)}  "
          f"themes={len(THEMES)}  counsellors={len(COUNSELLORS)}  "
          f"lexicon={len(LEXICON)}")


def seed_students(conn, n=60):
    cur = conn.cursor()
    dept_ids = [r[0] for r in cur.execute("SELECT dept_id FROM department")]
    used_names, rows = set(), []
    for i in range(n):
        while True:
            name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
            if name not in used_names:
                used_names.add(name)
                break
        year = random.choice([1, 2, 2, 3, 3, 4])
        adm_year = 2026 - year
        enroll = f"A{random.choice([23, 24])}05{adm_year % 100}{1000 + i}"
        handle = name.lower().replace(" ", ".")
        rows.append((
            enroll, name, f"{handle}@student.mindcare.edu",
            f"9{random.randint(100000000, 999999999)}",
            random.choice(["Male", "Female", "Female", "Male", "Other"]),
            f"{adm_year - 18}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
            random.choice(dept_ids), year,
            random.choice(["Hosteller", "Hosteller", "Day Scholar"]), adm_year))
    cur.executemany(
        "INSERT INTO student (enrollment_no, full_name, email, phone, gender, dob,"
        " dept_id, year_of_study, hostel_status, admission_year)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    print(f"    students={n}")


def seed_users(conn):
    cur = conn.cursor()
    pw = generate_password_hash("mindcare123", method="pbkdf2:sha256")
    cur.execute("INSERT INTO app_user (username, password_hash, role) VALUES (?,?,?)",
                ("admin", pw, "admin"))
    for cid, emp in cur.execute(
            "SELECT counsellor_id, emp_code FROM counsellor").fetchall():
        cur.execute("INSERT INTO app_user (username, password_hash, role,"
                    " counsellor_id) VALUES (?,?,?,?)",
                    (emp.lower().replace("-", ""), pw, "counsellor", cid))
    students = cur.execute(
        "SELECT student_id, enrollment_no FROM student ORDER BY student_id LIMIT 8"
    ).fetchall()
    for sid, enroll in students:
        cur.execute("INSERT INTO app_user (username, password_hash, role,"
                    " student_id) VALUES (?,?,?,?)",
                    (enroll.lower(), pw, "student", sid))
    conn.commit()
    print(f"    users=1 admin + {len(COUNSELLORS)} counsellors + {len(students)} students"
          f"   (password for all: mindcare123)")


def register_model(conn):
    meta_path = os.path.join(MODEL_DIR, "metadata.json")
    if not os.path.exists(meta_path):
        raise SystemExit("ml/models/metadata.json missing - run "
                         "`python ml/train_model.py` first.")
    with open(meta_path) as fh:
        m = json.load(fh)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO ml_model (model_name, algorithm, version, accuracy,"
        " precision_macro, recall_macro, f1_macro, train_size, test_size,"
        " feature_count, artifact_path, is_active)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,1)",
        (m["model_name"], m["algorithm"], m["version"], m["accuracy"],
         m["precision_macro"], m["recall_macro"], m["f1_macro"],
         m["train_size"], m["test_size"], m["feature_count"],
         "ml/models/stress_model.pkl"))
    for name, r in m.get("comparison", {}).items():
        if name == m["algorithm"]:
            continue
        cur.execute(
            "INSERT INTO ml_model (model_name, algorithm, version, accuracy,"
            " precision_macro, recall_macro, f1_macro, train_size, test_size,"
            " feature_count, is_active) VALUES (?,?,?,?,?,?,?,?,?,?,0)",
            ("MindCare Stress Classifier", name, "1.0", r["accuracy"],
             r["precision_macro"], r["recall_macro"], r["f1_macro"],
             m["train_size"], m["test_size"], m["feature_count"]))
    conn.commit()
    active = cur.execute("SELECT model_id FROM ml_model WHERE is_active=1").fetchone()[0]
    total = cur.execute("SELECT COUNT(*) FROM ml_model").fetchone()[0]
    print(f"    registered {total} models, active model_id={active} "
          f"({m['algorithm']}, acc={m['accuracy']:.4f})")
    return active


def load_corpus(conn):
    import pandas as pd
    df = pd.read_csv(DATA_CSV)
    cur = conn.cursor()
    theme_map = dict(cur.execute("SELECT theme_code, theme_id FROM theme").fetchall())
    rows = [(int(r.id), r.text, int(r.label), theme_map[r.theme],
             "test" if i % 5 == 4 else "train")
            for i, r in enumerate(df.itertuples())]
    cur.executemany(
        "INSERT INTO training_corpus (corpus_id, text, label, theme_id, split)"
        " VALUES (?,?,?,?,?)", rows)
    conn.commit()
    print(f"    training_corpus={len(rows)} rows "
          f"({sum(1 for r in rows if r[4]=='train')} train / "
          f"{sum(1 for r in rows if r[4]=='test')} test)")


def seed_assessments(conn, model_id, n=700):
    import sys
    sys.path.insert(0, BASE_DIR)
    from backend.services.prediction_service import StressPredictor

    predictor = StressPredictor()
    cur = conn.cursor()
    student_ids = [r[0] for r in cur.execute("SELECT student_id FROM student")]
    kw_map = dict(cur.execute("SELECT word, keyword_id FROM keyword_lexicon").fetchall())
    theme_map = dict(cur.execute("SELECT theme_code, theme_id FROM theme").fetchall())

    pool = cur.execute(
        "SELECT text FROM training_corpus WHERE split='test' ORDER BY RANDOM() LIMIT ?",
        (n,)).fetchall()

    now = datetime.now()
    timeline = []
    for (text,) in pool:
        days_ago = int(abs(random.gauss(0, 28))) % 90
        timeline.append((
            now - timedelta(days=days_ago,
                            hours=random.randint(0, 23),
                            minutes=random.randint(0, 59)),
            random.choice(student_ids), text))
    anchor = datetime.now() - timedelta(days=HISTORY_ENDS_DAYS_AGO)
    shift = anchor - max(t for t, _, _ in timeline)
    timeline = sorted(((t + shift, s, x) for t, s, x in timeline), key=lambda r: r[0])

    inserted = 0
    for entry_dt, student_id, text in timeline:
        ts = entry_dt.strftime("%Y-%m-%d %H:%M:%S")
        res = predictor.predict(text)
        cur.execute(
            "INSERT INTO assessment (student_id, model_id, entry_text, char_count,"
            " word_count, predicted_level, confidence, predicted_theme, source,"
            " created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (student_id, model_id, text, len(text), len(text.split()),
             res["level"], res["confidence"], theme_map.get(res["theme_code"]),
             random.choice(["web", "web", "web", "mobile", "chat"]), ts))
        aid = cur.lastrowid
        cur.executemany(
            "INSERT INTO assessment_score (assessment_id, level_code, probability)"
            " VALUES (?,?,?)",
            [(aid, lvl, prob) for lvl, prob in enumerate(res["probabilities"])])
        hits = {}
        for w in res["keywords"]:
            if w in kw_map:
                hits[kw_map[w]] = hits.get(kw_map[w], 0) + 1
        if hits:
            cur.executemany(
                "INSERT INTO assessment_keyword (assessment_id, keyword_id,"
                " occurrences) VALUES (?,?,?)",
                [(aid, k, v) for k, v in hits.items()])
        inserted += 1
    conn.commit()

    dist = cur.execute(
        "SELECT sl.level_name, COUNT(*) FROM assessment a"
        " JOIN stress_level sl ON a.predicted_level = sl.level_code"
        " GROUP BY sl.level_name ORDER BY sl.severity_rank").fetchall()
    alerts = cur.execute("SELECT COUNT(*) FROM alert").fetchone()[0]
    print(f"    assessments={inserted}  distribution={dict(dist)}")
    print(f"    alerts auto-created by trigger T1 = {alerts}")


def seed_wellness(conn, days=45):
    cur = conn.cursor()
    student_ids = [r[0] for r in cur.execute(
        "SELECT student_id FROM student ORDER BY student_id LIMIT 30")]
    last_day = (datetime.now() - timedelta(days=HISTORY_ENDS_DAYS_AGO)).date()
    rows = []
    for sid in student_ids:
        base_mood = random.randint(4, 8)
        for d in range(days):
            if random.random() < 0.45:
                continue
            day = last_day - timedelta(days=d)
            rows.append((
                sid, day.isoformat(),
                round(max(3.0, min(10.0, random.gauss(6.8, 1.4))), 1),
                max(0, int(random.gauss(28, 25))),
                max(1, min(10, int(random.gauss(base_mood, 1.6)))),
                round(max(0.5, random.gauss(5.5, 2.0)), 1)))
    cur.executemany(
        "INSERT INTO wellness_log (student_id, log_date, sleep_hours, exercise_min,"
        " mood_rating, screen_time_hrs) VALUES (?,?,?,?,?,?)", rows)
    conn.commit()
    print(f"    wellness_log={len(rows)} rows across {len(student_ids)} students")


def seed_sessions(conn):
    cur = conn.cursor()
    alerts = cur.execute(
        "SELECT al.alert_id, a.student_id, al.assigned_to, al.raised_at"
        " FROM alert al JOIN assessment a ON al.assessment_id = a.assessment_id"
        " ORDER BY al.raised_at").fetchall()
    couns = [r[0] for r in cur.execute(
        "SELECT counsellor_id FROM counsellor WHERE is_active=1")]
    booked, taken = 0, set()
    for alert_id, student_id, assigned, raised_at in alerts:
        if random.random() < 0.45:
            continue
        cid = assigned or random.choice(couns)
        base = datetime.strptime(raised_at, "%Y-%m-%d %H:%M:%S")
        for attempt in range(30):
            slot = (base + timedelta(days=random.randint(1, 6))).replace(
                hour=random.randint(10, 17), minute=random.choice([0, 30]),
                second=0, microsecond=0)
            if (cid, slot) not in taken:
                taken.add((cid, slot))
                break
        else:
            continue
        past = slot < datetime.now()
        status = random.choice(["COMPLETED", "COMPLETED", "NO_SHOW", "CANCELLED"]) \
            if past else "SCHEDULED"
        cur.execute(
            "INSERT INTO counselling_session (student_id, counsellor_id, alert_id,"
            " scheduled_at, duration_min, mode, status, notes, follow_up_needed)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (student_id, cid, alert_id, slot.strftime("%Y-%m-%d %H:%M:%S"),
             random.choice([30, 45, 45, 60]),
             random.choice(["In-Person", "In-Person", "Video", "Phone"]),
             "SCHEDULED",
             "Initial triage conversation. Student briefed on support options."
             if past else None,
             1 if random.random() < 0.4 else 0))
        sid_new = cur.lastrowid
        booked += 1
        if status != "SCHEDULED":
            cur.execute("UPDATE counselling_session SET status=? WHERE session_id=?",
                        (status, sid_new))
            if status == "COMPLETED":
                cur.execute("UPDATE alert SET resolved_at = ? WHERE alert_id = ?",
                            ((slot + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
                             alert_id))
    conn.commit()
    stats = dict(cur.execute(
        "SELECT status, COUNT(*) FROM counselling_session GROUP BY status").fetchall())
    resolved = cur.execute(
        "SELECT COUNT(*) FROM alert WHERE status='RESOLVED'").fetchone()[0]
    print(f"    counselling_session={booked}  {stats}")
    print(f"    alerts auto-resolved by trigger T5 = {resolved}")


def acknowledge_some_alerts(conn):
    cur = conn.cursor()
    ids = [r[0] for r in cur.execute(
        "SELECT alert_id FROM alert WHERE status='OPEN' ORDER BY RANDOM() LIMIT 12")]
    cur.executemany("UPDATE alert SET status='ACKNOWLEDGED' WHERE alert_id=?",
                    [(i,) for i in ids])
    cur.executemany("UPDATE alert SET acknowledged_at = datetime(raised_at, ?)"
                    " WHERE alert_id = ?",
                    [(f"+{random.randint(1, 20)} hours", i) for i in ids])
    conn.commit()
    print(f"    {len(ids)} alerts moved OPEN -> ACKNOWLEDGED (trigger T3 fires)")


def summary(conn):
    cur = conn.cursor()
    tables = [r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
        " AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    print("\n" + "=" * 64)
    print("  DATABASE SUMMARY")
    print("=" * 64)
    for t in tables:
        n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"    {t:<24} {n:>7} rows")
    nv = cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='view'").fetchone()[0]
    nt = cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='trigger'").fetchone()[0]
    ni = cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index'"
                     " AND name NOT LIKE 'sqlite_%'").fetchone()[0]
    print("-" * 64)
    print(f"    {len(tables)} tables | {nv} views | {nt} triggers | {ni} indexes")
    print(f"    file: {DB_PATH} "
          f"({os.path.getsize(DB_PATH) / 1024 / 1024:.2f} MB)")


def _has_table(conn, name):
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                        (name,)).fetchone() is not None


def upgrade():
    if not os.path.exists(DB_PATH):
        print("No database found. Run  python init_db.py  to build one.")
        return
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    has_puzzles = _has_table(conn, "aptitude_attempt")
    old_levels = has_puzzles and {r[0] for r in conn.execute("SELECT code FROM age_group")} != \
        {g[0] for g in AGE_GROUPS}
    has_game = _has_table(conn, "rescue_game")
    if has_puzzles and not old_levels and has_game:
        print("This database is already up to date. Nothing to do.")
        conn.close()
        return

    backup_dir = os.path.join(BASE_DIR, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    backup = os.path.join(backup_dir, f"mindcare-before-upgrade-{datetime.now():%Y%m%d-%H%M%S}.db")
    conn.execute("VACUUM INTO ?", (backup,))
    print(f"\nSaved a copy of your database first: backups/{os.path.basename(backup)}")

    demo = conn.execute("SELECT COUNT(*) FROM training_corpus").fetchone()[0]
    latest = conn.execute("SELECT MAX(created_at) FROM assessment WHERE student_id <= 60").fetchone()[0]
    anchor = datetime.strptime(str(latest)[:19], "%Y-%m-%d %H:%M:%S") if latest else None

    if not has_puzzles:
        print("\n[1/3] Adding brain puzzle tables, views and triggers (your data is kept)")
        run_sql_file(conn, "07_aptitude_sqlite.sql")
        seed_aptitude(conn)
        if demo and anchor:
            seed_aptitude_attempts(conn, anchor=anchor)
    elif old_levels:
        print("\n[1/3] Moving brain puzzles to three age levels: 1-10, 11-20 and 21+ (your results are kept)")
        migrate_age_levels(conn)
    else:
        print("\n[1/3] Brain puzzles are already up to date")

    if not has_game:
        print("\n[2/3] Adding the City Rescue game tables, views and triggers")
        run_sql_file(conn, "08_game_sqlite.sql")
        seed_game(conn)
        if demo and anchor:
            print("\n[3/3] Generating City Rescue history for the sample students")
            seed_game_demo(conn, anchor=anchor)
        else:
            print("\n[3/3] No sample students found, so no example games were added")
    else:
        print("\n[2/3] City Rescue is already installed")

    problems = conn.execute("PRAGMA foreign_key_check").fetchall()
    conn.close()
    if problems:
        raise SystemExit(f"Upgrade finished with {len(problems)} broken references. "
                         f"Restore from {backup} and report this.")
    print("\nUpgrade complete. Start the app with:  python run.py\n")


def main():
    if "--upgrade" in sys.argv:
        upgrade()
        return
    empty = "--empty" in sys.argv
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("Removed existing mindcare.db")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    steps = 5 if empty else 12

    print(f"\n[1/{steps}] Creating schema, views and triggers")
    run_sql_file(conn, "01_schema_sqlite.sql")
    run_sql_file(conn, "02_views_sqlite.sql")
    run_sql_file(conn, "03_triggers_sqlite.sql")
    run_sql_file(conn, "05_screening_sqlite.sql")
    run_sql_file(conn, "06_support_sqlite.sql")
    run_sql_file(conn, "07_aptitude_sqlite.sql")
    run_sql_file(conn, "08_game_sqlite.sql")

    print(f"\n[2/{steps}] Seeding reference data")
    seed_master(conn)
    seed_instruments(conn)
    seed_support(conn)
    seed_aptitude(conn)
    seed_game(conn)

    if empty:
        print(f"\n[3/{steps}] Creating staff logins")
        seed_users(conn)
        print(f"\n[4/{steps}] Registering trained ML models")
        register_model(conn)
        load_corpus(conn)
        print(f"\n[5/{steps}] Verifying")
        summary(conn)
        conn.close()
        print("\nEmpty database ready - there are no students yet.")
        print("Start the app, click 'Create a new account', then sign in.\n")
        return

    print(f"\n[3/{steps}] Seeding students")
    seed_students(conn)

    print(f"\n[4/{steps}] Creating application logins")
    seed_users(conn)

    print(f"\n[5/{steps}] Registering trained ML models")
    model_id = register_model(conn)

    print(f"\n[6/{steps}] Loading labelled corpus into the database")
    load_corpus(conn)

    print(f"\n[7/{steps}] Generating assessment history with the live model")
    seed_assessments(conn, model_id)

    print(f"\n[8/{steps}] Seeding wellness logs and counselling sessions")
    seed_wellness(conn)
    seed_sessions(conn)
    acknowledge_some_alerts(conn)

    print(f"\n[9/{steps}] Generating structured screenings (triggers T8-T10 score them)")
    seed_screenings(conn)

    print(f"\n[10/{steps}] Generating brain puzzle history (triggers T11-T14 score it)")
    seed_aptitude_attempts(conn)

    print(f"\n[11/{steps}] Generating City Rescue history (triggers T15-T18 score it)")
    seed_game_demo(conn)

    print(f"\n[12/{steps}] Verifying")
    summary(conn)
    conn.close()
    print("\nDatabase ready. Start the app with:  python run.py\n")


if __name__ == "__main__":
    main()
