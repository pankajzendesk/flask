from flask import Flask, render_template, redirect, url_for, session, request, flash
from werkzeug.security import generate_password_hash, check_password_hash
import json, os, re, subprocess

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Utility functions to handle user data stored in a JSON file
def get_user_data():
    if not os.path.exists("users.json"):
        with open("users.json", "w") as file:
            json.dump([], file)
    with open("users.json", "r") as file:
        return json.load(file)

def save_user_data(data):
    with open("users.json", "w") as file:
        json.dump(data, file)

def run_ansible_playbook(username, password):
    try:
        # Run the Ansible playbook with the necessary parameters
        result = subprocess.run(
            ['ansible-playbook', 'create_user.yml', '-e', f'username={username}', '-e', f'password={password}'],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(result.stdout.decode())
        print(result.stderr.decode())
    except subprocess.CalledProcessError as e:
        print(f"Ansible playbook failed: {e}")
        return False
    return True

@app.route("/")
def index():
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        email = request.form.get("email")

        if not (username and password and confirm_password and email):
            return render_template("register.html", message="All fields are required.")

        if password != confirm_password:
            return render_template("register.html", message="Passwords do not match.")

        # Validate username
        if not re.match("^[a-z0-9]+$", username):
            return render_template("register.html", message="Username can only contain lowercase letters and digits.")

        hashed_password = generate_password_hash(password)
        users = get_user_data()

        if any(user['username'] == username or user['email'] == email for user in users):
            return render_template("register.html", message="Username or email already exists.")

        users.append({"username": username, "email": email, "password": hashed_password})
        save_user_data(users)

        if run_ansible_playbook(username, password):
            flash("User created successfully. Please log in.", "success")
        else:
            flash("Failed to create system user. Please contact the administrator.", "error")
            
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        users = get_user_data()
        user = next((user for user in users if user['username'] == username), None)

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["username"]
            return redirect(url_for("home"))

        return render_template("login.html", message="Invalid username or password.")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/home")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))

    users = get_user_data()
    user = next((user for user in users if user['username'] == session["user_id"]), None)

    if user:
        return render_template("home.html", username=user['username'])
    else:
        return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5001)  # Port set to 5001
