import re
from datetime import datetime

from backend.errors import ValidationError

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Field:
    def __init__(self, type_=str, required=False, default=None, min_=None,
                 max_=None, choices=None, pattern=None, min_len=None,
                 max_len=None, label=None):
        self.type = type_
        self.required = required
        self.default = default
        self.min = min_
        self.max = max_
        self.choices = choices
        self.pattern = pattern
        self.min_len = min_len
        self.max_len = max_len
        self.label = label

    def clean(self, name, raw):
        label = self.label or name.replace("_", " ")

        if raw is None or (isinstance(raw, str) and not raw.strip()):
            if self.required:
                raise ValidationError(f"{label.capitalize()} is required.",
                                      details={"field": name})
            return self.default

        if isinstance(raw, str):
            raw = raw.strip()

        try:
            if self.type is int:
                value = int(raw)
            elif self.type is float:
                value = float(raw)
            elif self.type is bool:
                value = str(raw).lower() in ("1", "true", "yes", "on")
            elif self.type == "date":
                datetime.strptime(str(raw), "%Y-%m-%d")
                value = str(raw)
            elif self.type == "email":
                value = str(raw)
                if not EMAIL_RE.match(value):
                    raise ValueError
            else:
                value = str(raw)
        except (TypeError, ValueError):
            raise ValidationError(f"{label.capitalize()} is not a valid "
                                  f"{'email address' if self.type == 'email' else self.type if isinstance(self.type, str) else self.type.__name__}.",
                                  details={"field": name})

        if self.min is not None and value < self.min:
            raise ValidationError(f"{label.capitalize()} must be at least {self.min}.",
                                  details={"field": name})
        if self.max is not None and value > self.max:
            raise ValidationError(f"{label.capitalize()} must be at most {self.max}.",
                                  details={"field": name})
        if self.min_len is not None and len(str(value)) < self.min_len:
            raise ValidationError(
                f"{label.capitalize()} must be at least {self.min_len} characters.",
                details={"field": name})
        if self.max_len is not None and len(str(value)) > self.max_len:
            raise ValidationError(
                f"{label.capitalize()} must be at most {self.max_len} characters.",
                details={"field": name})
        if self.choices and value not in self.choices:
            raise ValidationError(
                f"{label.capitalize()} must be one of: {', '.join(map(str, self.choices))}.",
                details={"field": name})
        if self.pattern and not re.match(self.pattern, str(value)):
            raise ValidationError(f"{label.capitalize()} is not in the expected format.",
                                  details={"field": name})
        return value


class Schema:
    fields = {}

    @classmethod
    def load(cls, data):
        return {name: field.clean(name, data.get(name))
                for name, field in cls.fields.items()}


class LoginSchema(Schema):
    fields = {
        "username": Field(required=True, max_len=40),
        "password": Field(required=True, max_len=200),
    }


class RegistrationSchema(Schema):
    fields = {
        "full_name":      Field(required=True, max_len=80, label="full name"),
        "enrollment_no":  Field(required=True, max_len=20, label="enrollment number"),
        "email":          Field("email", required=True, max_len=120),
        "phone":          Field(max_len=15),
        "gender":         Field(choices=("Male", "Female", "Other")),
        "dob":            Field("date", label="date of birth"),
        "dept_id":        Field(int, required=True, label="department"),
        "year_of_study":  Field(int, required=True, min_=1, max_=5, label="year"),
        "hostel_status":  Field(default="Day Scholar",
                                choices=("Hosteller", "Day Scholar")),
        "username":       Field(required=True, max_len=40, min_len=3),
        "password":       Field(required=True, min_len=6, max_len=200),
    }


class AssessmentSchema(Schema):
    fields = {
        "student_id": Field(int, label="student"),
        "entry_text": Field(required=True, min_len=10, max_len=1000,
                            label="entry"),
        "source":     Field(default="web",
                            choices=("web", "mobile", "chat", "import")),
    }


class AlertUpdateSchema(Schema):
    fields = {
        "status":      Field(choices=("OPEN", "ACKNOWLEDGED", "RESOLVED", "DISMISSED")),
        "assigned_to": Field(int, label="counsellor"),
        "remarks":     Field(max_len=300),
    }


class SessionSchema(Schema):
    fields = {
        "student_id":    Field(int, required=True, label="student"),
        "counsellor_id": Field(int, required=True, label="counsellor"),
        "alert_id":      Field(int),
        "scheduled_at":  Field(required=True, label="date and time"),
        "duration_min":  Field(int, default=45, min_=15, max_=180, label="duration"),
        "mode":          Field(default="In-Person",
                               choices=("In-Person", "Video", "Phone", "Chat")),
        "notes":         Field(max_len=500),
    }


class WellnessSchema(Schema):
    fields = {
        "log_date":        Field("date", required=True, label="date"),
        "sleep_hours":     Field(float, min_=0, max_=24, label="sleep"),
        "exercise_min":    Field(int, min_=0, max_=600, label="exercise"),
        "mood_rating":     Field(int, min_=1, max_=10, label="mood"),
        "screen_time_hrs": Field(float, min_=0, max_=24, label="screen time"),
    }


class PaginationSchema(Schema):
    fields = {
        "page":     Field(int, default=1, min_=1),
        "per_page": Field(int, default=15, min_=1, max_=100),
    }
