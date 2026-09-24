"""
Tests for the education companion: daily advice, chat, and quizzes.
Confirms the deterministic AI-stand-in logic (app/education_ai.py)
genuinely personalizes per-user based on quiz history, without
depending on any actual AI model existing yet.
"""
from app.education_content import EDUCATION_TOPICS, QUIZ_QUESTIONS


def _seed_education(db_session):
    from app import models

    for topic in EDUCATION_TOPICS:
        db_session.add(models.EducationTopic(
            title=topic["title"], body=topic["body"], category=topic["category"],
        ))
    for q in QUIZ_QUESTIONS:
        db_session.add(models.QuizQuestion(
            prompt=q["prompt"], options=q["options"], correct_option_id=q["correct_option_id"],
            explanation=q["explanation"], category=q["category"], source="seed",
        ))
    db_session.commit()


def test_daily_advice_requires_auth(client):
    r = client.get("/education/daily-advice")
    assert r.status_code == 401


def test_daily_advice_returns_a_topic(client, auth_headers, db_session):
    _seed_education(db_session)
    headers = auth_headers()
    r = client.get("/education/daily-advice", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["title"]
    assert body["body"]
    assert body["category"]


def test_daily_advice_not_personalized_with_no_quiz_history(client, auth_headers, db_session):
    _seed_education(db_session)
    headers = auth_headers()
    r = client.get("/education/daily-advice", headers=headers)
    assert r.json()["is_personalized"] is False


def test_daily_advice_with_no_content_loaded_returns_503(client, auth_headers):
    headers = auth_headers()
    r = client.get("/education/daily-advice", headers=headers)
    assert r.status_code == 503


def test_daily_advice_is_deterministic_for_same_user_same_day(client, auth_headers, db_session):
    """Repeated calls on the same day must return the same topic, not
    a random one each time, the rotation is deterministic by design."""
    _seed_education(db_session)
    headers = auth_headers()
    r1 = client.get("/education/daily-advice", headers=headers)
    r2 = client.get("/education/daily-advice", headers=headers)
    assert r1.json()["title"] == r2.json()["title"]


def test_chat_stores_and_returns_a_reply(client, auth_headers, db_session):
    _seed_education(db_session)
    headers = auth_headers()
    r = client.post("/education/chat", json={"message": "Tell me about OTP scams"}, headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "assistant"
    assert len(body["content"]) > 0
    assert body["is_ai_generated"] is False


def test_chat_response_is_honestly_labeled_as_not_ai_generated(client, auth_headers, db_session):
    """Every reply today is a deterministic stand-in, this must be
    labeled honestly, not implied to be a real AI conversation."""
    _seed_education(db_session)
    headers = auth_headers()
    r = client.post("/education/chat", json={"message": "hello"}, headers=headers)
    assert r.json()["is_ai_generated"] is False


def test_chat_reply_matches_relevant_topic_by_keyword(client, auth_headers, db_session):
    _seed_education(db_session)
    headers = auth_headers()
    r = client.post("/education/chat", json={"message": "What about investment scams?"}, headers=headers)
    content = r.json()["content"].lower()
    assert "invest" in content or "return" in content or "risk" in content


def test_chat_history_persists_across_requests(client, auth_headers, db_session):
    _seed_education(db_session)
    headers = auth_headers()
    client.post("/education/chat", json={"message": "First message"}, headers=headers)
    client.post("/education/chat", json={"message": "Second message"}, headers=headers)

    r = client.get("/education/chat/history", headers=headers)
    messages = r.json()
    assert len(messages) == 4
    assert messages[0]["content"] == "First message"


def test_chat_history_is_scoped_to_own_user(client, auth_headers, db_session):
    _seed_education(db_session)
    headers_a = auth_headers(email="educhata@fraudlens.mu")
    headers_b = auth_headers(email="educhatb@fraudlens.mu")

    client.post("/education/chat", json={"message": "A's message"}, headers=headers_a)

    r = client.get("/education/chat/history", headers=headers_b)
    assert r.json() == []


def test_quiz_returns_a_question_without_the_answer(client, auth_headers, db_session):
    _seed_education(db_session)
    headers = auth_headers()
    r = client.get("/education/quiz", headers=headers)
    body = r.json()
    assert "prompt" in body
    assert "options" in body
    assert "correct_option_id" not in body
    assert "explanation" not in body


def test_quiz_filtered_by_category(client, auth_headers, db_session):
    _seed_education(db_session)
    headers = auth_headers()
    r = client.get("/education/quiz?category=otp", headers=headers)
    assert r.status_code == 200
    assert r.json()["category"] == "otp"


def test_quiz_with_no_questions_loaded_returns_503(client, auth_headers):
    headers = auth_headers()
    r = client.get("/education/quiz", headers=headers)
    assert r.status_code == 503


def test_answer_correct_option_marks_correct(client, auth_headers, db_session):
    _seed_education(db_session)
    headers = auth_headers()
    r = client.get("/education/quiz?category=otp", headers=headers)
    question_id = r.json()["id"]

    r2 = client.post(f"/education/quiz/{question_id}/answer", json={"selected_option_id": "b"}, headers=headers)
    assert r2.json()["was_correct"] is True
    assert r2.json()["correct_option_id"] == "b"


def test_answer_wrong_option_marks_incorrect_but_reveals_explanation(client, auth_headers, db_session):
    _seed_education(db_session)
    headers = auth_headers()
    r = client.get("/education/quiz?category=otp", headers=headers)
    question_id = r.json()["id"]

    r2 = client.post(f"/education/quiz/{question_id}/answer", json={"selected_option_id": "a"}, headers=headers)
    body = r2.json()
    assert body["was_correct"] is False
    assert len(body["explanation"]) > 0


def test_answer_nonexistent_question_returns_404(client, auth_headers):
    headers = auth_headers()
    r = client.post("/education/quiz/999999/answer", json={"selected_option_id": "a"}, headers=headers)
    assert r.status_code == 404


def test_getting_a_question_wrong_personalizes_future_daily_advice(client, auth_headers, db_session):
    """
    The core personalization property: after getting a question in a
    given category wrong, daily advice should switch to that category
    and be flagged as personalized, demonstrated live during
    development, encoded here as a permanent test.
    """
    _seed_education(db_session)
    headers = auth_headers()

    r = client.get("/education/quiz?category=urgency", headers=headers)
    question_id = r.json()["id"]
    client.post(f"/education/quiz/{question_id}/answer", json={"selected_option_id": "a"}, headers=headers)

    r2 = client.get("/education/daily-advice", headers=headers)
    body = r2.json()
    assert body["is_personalized"] is True
    assert body["category"] == "urgency"


def test_personalization_is_scoped_per_user(client, auth_headers, db_session):
    """One user's wrong quiz answer must not affect another user's
    daily advice, this is per-user state, not global."""
    _seed_education(db_session)
    headers_a = auth_headers(email="personalizea@fraudlens.mu")
    headers_b = auth_headers(email="personalizeb@fraudlens.mu")

    r = client.get("/education/quiz?category=urgency", headers=headers_a)
    question_id = r.json()["id"]
    client.post(f"/education/quiz/{question_id}/answer", json={"selected_option_id": "a"}, headers=headers_a)

    r2 = client.get("/education/daily-advice", headers=headers_b)
    assert r2.json()["is_personalized"] is False


# ---------------------------------------------------------------------------
# Multilingual education content
# ---------------------------------------------------------------------------

def test_daily_advice_defaults_to_english(client, auth_headers, db_session):
    _seed_education(db_session)
    headers = auth_headers()
    r = client.get("/education/daily-advice", headers=headers)
    # English content should not contain obvious French/Kreol markers
    assert "vous" not in r.json()["body"].lower()


def test_daily_advice_in_french(client, auth_headers, db_session):
    _seed_education(db_session)
    headers = auth_headers()
    r = client.get("/education/daily-advice?language=fr", headers=headers)
    body = r.json()
    assert body["title"] != ""
    # A French translation should differ from the English one
    assert "the" not in body["body"].lower().split()


def test_daily_advice_in_kreol(client, auth_headers, db_session):
    _seed_education(db_session)
    headers = auth_headers()
    r = client.get("/education/daily-advice?language=cr", headers=headers)
    body = r.json()
    assert body["title"] != ""


def test_chat_reply_in_french_matches_relevant_topic(client, auth_headers, db_session):
    _seed_education(db_session)
    headers = auth_headers()
    r = client.post("/education/chat?language=fr", json={"message": "Parlez-moi des arnaques OTP"}, headers=headers)
    content = r.json()["content"].lower()
    assert "otp" in content or "mot de passe" in content


def test_chat_reply_in_kreol_matches_relevant_topic(client, auth_headers, db_session):
    _seed_education(db_session)
    headers = auth_headers()
    r = client.post("/education/chat?language=cr", json={"message": "Koz mwa lor OTP"}, headers=headers)
    content = r.json()["content"].lower()
    assert "otp" in content


def test_quiz_in_french_has_french_prompt_and_options(client, auth_headers, db_session):
    _seed_education(db_session)
    headers = auth_headers()
    r = client.get("/education/quiz?language=fr&category=otp", headers=headers)
    body = r.json()
    assert "vous" in body["prompt"].lower() or "votre" in body["prompt"].lower()


def test_quiz_in_kreol_has_kreol_prompt(client, auth_headers, db_session):
    _seed_education(db_session)
    headers = auth_headers()
    r = client.get("/education/quiz?language=cr&category=otp", headers=headers)
    body = r.json()
    assert "ou" in body["prompt"].lower()


def test_answer_explanation_returned_in_requested_language(client, auth_headers, db_session):
    _seed_education(db_session)
    headers = auth_headers()
    r = client.get("/education/quiz?language=fr&category=otp", headers=headers)
    question_id = r.json()["id"]

    r2 = client.post(
        f"/education/quiz/{question_id}/answer?language=fr",
        json={"selected_option_id": "a"},
        headers=headers,
    )
    explanation = r2.json()["explanation"].lower()
    assert "banque" in explanation or "téléphone" in explanation


def test_correct_option_id_is_language_independent(client, auth_headers, db_session):
    """
    Option ids (a/b/c) must stay identical across languages, only the
    option TEXT differs — this is what lets a French or Kreol quiz
    submit the same correct_option_id as the English version.
    """
    _seed_education(db_session)
    headers = auth_headers()

    r_en = client.get("/education/quiz?language=en&category=otp", headers=headers)
    r_fr = client.get("/education/quiz?language=fr&category=otp", headers=headers)

    en_ids = {o["id"] for o in r_en.json()["options"]}
    fr_ids = {o["id"] for o in r_fr.json()["options"]}
    assert en_ids == fr_ids
