from flask import Flask, render_template, redirect, url_for, session, request, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import json, os, re, subprocess, logging

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

def get_user_data():
    if not os.path.exists("users.json"):
        with open("users.json", "w") as file:
            json.dump([], file)

    with open("users.json", "r") as file:
        users = json.load(file)

    # Ensure the default admin user exists
    admin_username = "admin"
    admin_email = "admin@example.com"
    admin_password = "Blue123#"
    hashed_admin_password = generate_password_hash(admin_password)

    if not any(user['username'] == admin_username for user in users):
        admin_user = {
            "username": admin_username,
            "email": admin_email,
            "password": hashed_admin_password,
            "role": "admin"
        }
        users.append(admin_user)
        save_user_data(users)

    return users

def save_user_data(data):
    with open("users.json", "w") as file:
        json.dump(data, file)

def run_ansible_playbook(username, password):
    ambari_host = os.getenv("AMBARI_HOST")
    ssh_key_path = os.getenv("SSH_KEY_PATH")
    playbook_path = os.getenv("PLAYBOOK_PATH")
    
    if not all([ambari_host, ssh_key_path, playbook_path]):
        logging.error("Please set all required environment variables: SSH_HOST, SSH_KEY_PATH, PLAYBOOK_PATH")
        return False
    
    try:
        result = subprocess.run(
            ['ssh', '-i', ssh_key_path, f'root@{ambari_host}',
             'ansible-playbook', playbook_path, '-i', 'localhost,', '-e', f'username={username}', '-e', f'password={password}'],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        logging.info(f"Ansible Playbook Output: {result.stdout.decode()}")
        if result.stderr.decode():
            logging.error(f"Ansible Playbook Errors: {result.stderr.decode()}")
        return True
    except subprocess.CalledProcessError as e:
        error_msg = f"Ansible playbook failed: {e}\nOutput: {e.stderr.decode()}"
        logging.error(error_msg)
        return False


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
        role = request.form.get("role", "user")  # Default role is user

        # Check if any field is empty
        if not (username and password and confirm_password and email):
            return render_template("register.html", message="All fields are required.")

        # Check if passwords match
        if password != confirm_password:
            return render_template("register.html", message="Passwords do not match.")

        # Validate username
        if not re.match("^[a-z0-9]+$", username):
            return render_template("register.html", message="Username can only contain lowercase letters and digits.")

        # Validate email
        if not email.endswith("@uaeu.ac.ae"):
            return render_template("register.html", message="Email must be a @uaeu.ac.ae address.")

        users = get_user_data()

        # Check if username or email already exists
        if any(user['username'] == username for user in users) or any(user['email'] == email for user in users):
            return render_template("register.html", message="Username or email already exists.")

        # Run Ansible playbook to create the Linux user
        if not run_ansible_playbook(username, password):
            return render_template("register.html", message="Failed to create system user. Please contact the administrator.")

        # If the Ansible user creation is successful, save the web user data
        hashed_password = generate_password_hash(password)
        users.append({"username": username, "email": email, "password": hashed_password, "role": role})
        save_user_data(users)

        flash("User created successfully. Please log in.", "success")
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
            session["role"] = user["role"]  # Store the user's role in the session
            return redirect(url_for("home"))

        return render_template("login.html", message="Invalid username or password.")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/admin")
def admin():
    if "user_id" not in session or session.get("role") != "admin":
        return redirect(url_for("login"))

    users = get_user_data()
    return render_template("admin.html", users=users)

@app.route("/home")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))

    users = get_user_data()
    user = next((user for user in users if user['username'] == session["user_id"]), None)

    if user:
        if session.get("role") == "admin":
            return render_template("admin_home.html", username=user['username'], users=users)
        return render_template("home.html", username=user['username'])
    else:
        return redirect(url_for("login"))
    
@app.route('/execute', methods=['POST'])
def execute():
    ssh_host = os.getenv("SSH_HOST")
    ssh_key_path = os.getenv("SSH_KEY_PATH")
    command = request.form['command']
    try:
        ssh_command = f'ssh -i {ssh_key_path} root@{ssh_host} {command}'
        output = subprocess.check_output(ssh_command, shell=True, stderr=subprocess.STDOUT, text=True)
    except subprocess.CalledProcessError as e:
        output = e.output
    return jsonify({'output': output})

@app.route('/run_script', methods=['POST'])
def run_script():
    ssh_host = os.getenv("SSH_HOST")
    ssh_key_path = os.getenv("SSH_KEY_PATH")
    ssh_host_gpu = os.getenv("SSH_HOST_GPU")
    ssh_key_path_gpu = os.getenv("SSH_KEY_PATH_GPU")
    script_path_gpu = os.getenv("SCRIPT_PATH_GPU")
    script_path_no_gpu = os.getenv("SCRIPT_PATH_NO_GPU")
    if "user_id" not in session:
        return jsonify({'output': "Unauthorized access!"}), 403

    data = request.json
    username = data.get('username')
    container_name = data.get('container_name')
    cpu = data.get('cpu')
    memory = data.get('memory')
    gpu = 'yes' if data.get('gpu') else 'no'

    # Debugging: Log input data to the console
    app.logger.info(f"Received data: username={username}, container_name={container_name}, cpu={cpu}, memory={memory}, gpu={gpu}")

    try:
        if gpu == 'yes':
            ssh_command = f'ssh -i {ssh_key_path_gpu} root@{ssh_host_gpu} sh {script_path_gpu} {username} {container_name} {cpu} {memory} {gpu}'
        else:
            ssh_command = f'ssh -i {ssh_key_path} root@{ssh_host} sh {script_path_no_gpu} {username} {container_name} {cpu} {memory} {gpu}'
        
        result = subprocess.run(
            ssh_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True
        )
        output = result.stdout
    except subprocess.CalledProcessError as e:
        output = e.output

    return jsonify({'output': output})

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
