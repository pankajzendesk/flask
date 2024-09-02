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
    # Retrieve environment variables
    ambari_host = os.getenv("AMBARI_HOST")
    ssh_key_path = os.getenv("SSH_KEY_PATH")
    playbook_path = os.getenv("PLAYBOOK_PATH")

    # Check if all required environment variables are set
    if not all([ambari_host, ssh_key_path, playbook_path]):
        logging.error("Please set all required environment variables: AMBARI_HOST, SSH_KEY_PATH, PLAYBOOK_PATH")
        return False

    # Construct the SSH command with increased verbosity
    ssh_command = (
        f"ssh -i {ssh_key_path} root@{ambari_host} "
        f"'ansible-playbook {playbook_path} -i /etc/ansible/flaskhost -e username={username} -e password={password} -vvvv'"
    )

    logging.info(f"Running command: {ssh_command}")

    try:
        # Run the SSH command
        result = subprocess.run(
            ssh_command,
            shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        # Log the output and errors
        if result.stdout:
            logging.info("Ansible Playbook Output:\n" + result.stdout.decode())
        if result.stderr:
            logging.error("Ansible Playbook Errors:\n" + result.stderr.decode())
            parse_ansible_errors(result.stderr.decode())

        return True

    except subprocess.CalledProcessError as e:
        # Log the error and parse it
        error_msg = f"Ansible playbook failed: {e}\nOutput:\n" + e.stderr.decode()
        logging.error(error_msg)
        parse_ansible_errors(e.stderr.decode())

        return False

def parse_ansible_errors(stderr):
    if "Invalid characters were found in group names" in stderr:
        logging.error("Invalid characters found in group names in the inventory file. Please check the inventory file.")
    elif "Authentication failure" in stderr:
        logging.error("Authentication failure. Please check the SSH key and host access permissions.")
    elif "command not found" in stderr:
        logging.error("Ansible command not found. Make sure Ansible is installed on the remote host.")
    elif "FAILED!" in stderr:
        logging.error("Ansible Playbook encountered an error!")
    else:
        logging.error("An unspecified error occurred.")

# Ensure logging is configured
logging.basicConfig(level=logging.INFO)


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
