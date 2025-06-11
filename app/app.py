from flask import Flask, render_template, request, redirect, url_for, flash, session
import json
import os
import random
from quiz import quiz_sets
import numpy as np
import joblib

model = joblib.load("C:\\Users\\PMLS\\Downloads\\AI-Powered-Career-Recommendation-System\\NoteBooks\\final_career_model.pkl")
vectorizer = joblib.load("C:\\Users\\PMLS\\Downloads\\AI-Powered-Career-Recommendation-System\\NoteBooks\\final_vectorizer.pkl")

app = Flask(__name__)
app.secret_key = 'dev'

DATA_FILE = 'users.json'

if os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'r') as f:
        users_db = json.load(f)
else:
    users_db = {}


def save_users():
    with open(DATA_FILE, 'w') as f:
        json.dump(users_db, f, indent=4)


def add_user(name, email, gender, age, password):
    users_db[email] = {
        "name": name,
        "gender": gender,
        "age": age,
        "password": password
    }
    save_users()


@app.route("/")
def home():
    # return users_db
    return redirect(url_for("login"))


@app.route('/signup', methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form['name']
        email = request.form['email']
        age = request.form['age']
        gender = request.form['gender']
        password = request.form['password']

        if email in users_db:
            flash("❌ Account with this email already exists.")
            return redirect(url_for("signup"))

        add_user(name, email, gender, age, password)
        flash("✅ Account created successfully!")
        return redirect(url_for("signup"))

    return render_template("index.html")


@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']

        user = users_db.get(email)

        if user and user['password'] == password:
            session['user_email'] = email
            flash(f"✅ Welcome, {user['name']}!")
            return redirect(url_for('dashboard'))

        flash("❌ Invalid email or password. Please try again.")
        return redirect(url_for('login'))

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if "user_email" not in session:
        flash("⚠️ Please log in to continue.")
        return redirect(url_for("login"))

    user_email = session["user_email"]
    user = users_db.get(user_email)

    return render_template("Dashboard.html", user=user)


@app.route('/quiz')
def start_quiz():
    selected_set = random.choice(quiz_sets)
    session['quiz_set'] = selected_set
    session['current_question_index'] = 0
    session['answers'] = []
    return redirect(url_for('questionnaire'))


@app.route('/questions', methods=["GET", "POST"])
def questionnaire():
    if 'quiz_set' not in session:
        return redirect(url_for('start_quiz'))

    quiz_set = session['quiz_set']
    index = session.get('current_question_index', 0)

    if request.method == "POST":
        # Save user's answer
        answer = request.form['answer']
        session['answers'].append(answer)
        index += 1
        session['current_question_index'] = index

    if index >= len(quiz_set):
        return redirect(url_for('recommendation'))  # Placeholder, implement later

    user_email = session["user_email"]
    user = users_db.get(user_email)

    current_q = quiz_set[index]
    return render_template("questions.html", user=user,
                           current_question=current_q['text'],
                           current_question_index=index + 1,
                           options=current_q.get('options', []))


@app.route('/history')
def history():
    return "History page coming soon!"  # Placeholder

@app.route('/recommendation')
def recommendation():
    if "user_email" not in session or "quiz_set" not in session or "answers" not in session:
        flash("⚠️ Session expired or quiz not completed.")
        return redirect(url_for("dashboard"))

    email = session["user_email"]
    user = users_db[email]
    answers = session["answers"]
    quiz_set = session["quiz_set"]

    interests = answers[0]
    skills = answers[1]

    def score_group(index1, index2):
        correct = 0
        for i in [index1, index2]:
            user_ans = answers[i].strip().lower()
            correct_ans = quiz_set[i].get("answer", "").strip().lower()
            if user_ans == correct_ans:
                correct += 1
        if correct == 2:
            return random.randint(7, 10)
        elif correct == 1:
            return random.randint(4, 6)
        else:
            return random.randint(0, 3)

    structured_data = {
        "interests": interests,
        "skills": skills,
        "programming_skills": score_group(2, 3),
        "logical_skills": score_group(4, 5),
        "problemSolving_skills": score_group(6, 7),
        "maths_score": score_group(8, 9)
    }

    users_db[email]["latest_quiz"] = structured_data

    with open("users.json", "w") as f:
        json.dump(users_db, f, indent=4)

    # Predict using model (only skills + interests)
    combined_text = structured_data['interests'].strip().lower() + ' ' + structured_data['skills'].strip().lower()
    text_vector = vectorizer.transform([combined_text])

    if hasattr(text_vector, "toarray"):
        text_vector = text_vector.toarray()

    # Predict top 5 careers based on probability
    probs = model.predict_proba(text_vector)[0]
    top_indices = probs.argsort()[-5:][::-1]
    top_careers = [model.classes_[i] for i in top_indices]

    return render_template("Recommendation.html", user=user, recommended_careers=top_careers, quiz_data=structured_data)


@app.route('/roadmap', methods=["POST"])
def show_roadmap():
    selected_career = request.form.get("selected_career")
    if not selected_career:
        flash("❌ No career selected.")
        return redirect(url_for("dashboard"))

    from roadmap_data import get_career_roadmap

    roadmap_dict = get_career_roadmap(selected_career)

    user_email = session["user_email"]
    user = users_db.get(user_email)

    return render_template(
        "Roadmap.html",
        selected_career=selected_career,
        roadmap_dict=roadmap_dict, user=user
    )


if __name__ == '__main__':
    app.run(debug=True)
