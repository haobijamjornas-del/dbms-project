# MindCare: AI-Based Mental Health Monitoring System

A DBMS project that helps a college notice when students are under stress and makes sure a counsellor follows up. Students write a few lines about how they feel, answer standard questionnaires, log sleep and mood, solve age-matched brain puzzles and play a short game about where to get help in an emergency. A text classifier labels each entry as Low, Medium or High stress, and SQL triggers inside the database raise alerts, score questionnaires and puzzles, and stop bad data from being saved.

## Main features

- Sign up, sign in and three roles: student, counsellor and administrator
- Daily mood check-in and a 7-day activity strip
- Free-text entries classified as Low, Medium or High stress, with coping tips and Delhi NCR and Noida helplines
- Full assessment with PHQ-9, GAD-7 and PSS-10, scored by a trigger into a 0-100 composite score
- Brain puzzles for three age levels (1-10, 11-20, 21 and above): logic, number series, colour-word, colour patterns and colour codes
- City Rescue: drag each emergency (an accident, a fire, a lost child, a friend who is not okay) to the right building in a small town
- Counsellor tools: alert queue, session booking, student profiles and analytics
- Admin tools: model registry, database browser and a read-only SQL console
- A REST API under `/api/v1` with token sign-in

## Database at a glance

| Object | Count |
| --- | --- |
| Tables | 36 |
| Views | 18 |
| Triggers | 18 (T1 to T18) |
| Indexes | 30 |
| Report queries | 50 in `sql/04_queries_sqlite.sql` |

The application runs on SQLite. The same design is provided for MySQL 8 in `sql/mysql_*.sql`, including stored functions and procedures.

## How to run

You need Python 3.9 or newer.

```
python start.py
```

On macOS you can also double-click `start.command`, and on Windows `start.bat`. The first run creates a virtual environment, installs the packages in `requirements.txt`, trains the model if needed and builds `mindcare.db` with sample data. The browser then opens at `http://127.0.0.1:5000`.

Sample logins (password `mindcare123` for all):

| Role | Username |
| --- | --- |
| Administrator | `admin` |
| Counsellor | `cns101` |
| Student | `a2305231000` |

Other commands:

| Command | What it does |
| --- | --- |
| `python run.py` | Starts only the web server |
| `python init_db.py` | Builds a fresh database with sample data (deletes the existing one) |
| `python init_db.py --upgrade` | Adds new features to an existing database and keeps its data |
| `python ml/train_model.py` | Retrains and compares the four classifiers |
| `python tools/export_mysql.py` | Exports the current SQLite data to `sql/mysql_data.sql` |

## Loading the MySQL version

```
mysql -u root -p < sql/mysql_schema.sql
mysql -u root -p < sql/mysql_screening.sql
mysql -u root -p < sql/mysql_aptitude.sql
mysql -u root -p < sql/mysql_game.sql
mysql -u root -p < sql/mysql_data.sql
```

## Folder structure

```
backend/        Flask app: blueprints (pages and API), services, repositories (all SQL), templates, static files
data/           synthetic_stress_dataset.csv (5,000 labelled sentences)
ml/             train_model.py and the saved model files
sql/            SQLite schema, views, triggers, report queries, and the MySQL scripts
tools/          export_mysql.py
init_db.py      builds and seeds the database
start.py        one-command launcher
run.py          starts the web server
```

## Note

The sample students, entries and results are generated for demonstration. The questionnaires are screening tools and the puzzles are a wellbeing activity, so nothing in the app is a medical diagnosis. If you need to talk to someone, Tele-MANAS (14416) is free and available 24x7 in India.
