from app.extensions import db
from app.utils import utcnow


class Quiz(db.Model):
    __tablename__ = "quizzes"
    __table_args__ = (db.Index("idx_quizzes_status_category", "status", "category_id"),)

    quiz_id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.category_id", ondelete="RESTRICT"), nullable=False)
    quiz_title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    difficulty = db.Column(
        db.Enum("easy", "medium", "hard", name="quiz_difficulty", native_enum=False),
        nullable=False,
    )
    total_questions = db.Column(db.Integer, nullable=False, default=0)
    passing_percentage = db.Column(db.Numeric(5, 2), nullable=False, default=70)
    duration_minutes = db.Column(db.Integer)
    generation_type = db.Column(
        db.Enum("manual", "ai", name="quiz_generation", native_enum=False),
        nullable=False,
        default="manual",
    )
    status = db.Column(
        db.Enum("draft", "published", "inactive", name="quiz_status", native_enum=False),
        nullable=False,
        default="draft",
    )
    is_demo = db.Column(db.Boolean, nullable=False, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    category = db.relationship("Category", back_populates="quizzes")
    questions = db.relationship(
        "Question",
        back_populates="quiz",
        cascade="all, delete-orphan",
        order_by="Question.question_id",
    )
    attempts = db.relationship("QuizAttempt", back_populates="quiz")


class Question(db.Model):
    __tablename__ = "questions"

    question_id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quizzes.quiz_id", ondelete="CASCADE"), nullable=False, index=True)
    question_text = db.Column(db.Text, nullable=False)
    explanation = db.Column(db.Text)
    marks = db.Column(db.Integer, nullable=False, default=1)
    question_type = db.Column(
        db.Enum("mcq", name="question_type", native_enum=False),
        nullable=False,
        default="mcq",
    )
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    quiz = db.relationship("Quiz", back_populates="questions")
    options = db.relationship(
        "QuestionOption",
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="QuestionOption.option_id",
    )


class QuestionOption(db.Model):
    __tablename__ = "question_options"

    option_id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.question_id", ondelete="CASCADE"), nullable=False, index=True)
    option_text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False, default=False)

    question = db.relationship("Question", back_populates="options")


class QuizAttempt(db.Model):
    __tablename__ = "quiz_attempts"
    __table_args__ = (
        db.Index("idx_attempts_user_date", "user_id", "submitted_at"),
        db.Index("idx_attempts_user_quiz", "user_id", "quiz_id"),
    )

    attempt_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quizzes.quiz_id", ondelete="RESTRICT"), nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    correct_answers = db.Column(db.Integer, nullable=False, default=0)
    obtained_marks = db.Column(db.Numeric(8, 2), nullable=False, default=0)
    total_marks = db.Column(db.Numeric(8, 2), nullable=False)
    percentage = db.Column(db.Numeric(5, 2), nullable=False, default=0)
    result = db.Column(db.Enum("pass", "fail", name="attempt_result", native_enum=False))
    status = db.Column(
        db.Enum("in_progress", "submitted", name="attempt_status", native_enum=False),
        nullable=False,
        default="in_progress",
    )
    started_at = db.Column(db.DateTime)
    deadline_at = db.Column(db.DateTime)
    submitted_at = db.Column(db.DateTime)
    timed_out = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    user = db.relationship("User")
    quiz = db.relationship("Quiz", back_populates="attempts")
    answers = db.relationship("AttemptAnswer", back_populates="attempt", cascade="all, delete-orphan")
    certificate = db.relationship("Certificate", back_populates="attempt", uselist=False)


class AttemptAnswer(db.Model):
    __tablename__ = "attempt_answers"
    __table_args__ = (db.UniqueConstraint("attempt_id", "question_id", name="uq_attempt_question"),)

    answer_id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey("quiz_attempts.attempt_id", ondelete="CASCADE"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.question_id", ondelete="RESTRICT"), nullable=False)
    selected_option_id = db.Column(db.Integer, db.ForeignKey("question_options.option_id", ondelete="RESTRICT"))
    is_correct = db.Column(db.Boolean, nullable=False, default=False)
    marks_obtained = db.Column(db.Numeric(8, 2), nullable=False, default=0)

    attempt = db.relationship("QuizAttempt", back_populates="answers")
    question = db.relationship("Question")
    selected_option = db.relationship("QuestionOption")
