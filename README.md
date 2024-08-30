# Flask User Management Web App

This web application is designed for creating new users and setting passwords. It supports multi-user operations and simultaneously creates the corresponding Linux user in the deployed node using Ansible playbooks.

### Features

- **User Registration**: Register a new user and set a password.
- **Linux User Creation**: Each registered user will have a corresponding Linux user created with a home directory.
- **User Login**: Users can log in using the username and password.
- **Welcome Page**: Users are welcomed with a personalized home page after login.

#admin user
this is deafult user
user name: admin
user-pass: Blue123#

#defualt user
pankaj
pankaj
### Prerequisites

- **Python 3.x**: Ensure Python is installed on your system.
- **Pip**: Ensure you have pip installed to manage Python packages.
- **Ansible**: Ensure Ansible is installed and properly configured.

### Installation

1. **Clone the Repository**:
    ```shell
    git clone https://github.com/pankajzendesk/flask.git
    cd flask
    ```

2. **Install Dependencies**:
    ```shell
    pip install -r requirements.txt
    ```

### Usage

1. **Run the Flask Application**:
    ```shell
    python app.py
    ```

2. **Access the Web Application**:
    - Open your web browser and navigate to: 
      ```
      http://127.0.0.1:5001/register
      ```

### Example

If you create a user named `pankaj` with the password `pankaj`, you can log in to the web application with the same credentials. Simultaneously, in the background, the application will execute an Ansible playbook to create the `/home/pankaj` directory and set the specified password.

### Directory Structure
flask/
├── app.py
├── users.json
├── requirements.txt
├── static/
│   ├── style.css
│   └── background.jpg
├── templates/
│   ├── login.html
│   └── register.html
│   └── home.html
├── playbooks/
│   └── create_user.yml
└── README.md


### Setup Steps and Environment

1. **Ensure Ansible is Installed**:
   ```shell
   sudo apt-get update
   sudo apt-get install ansible
