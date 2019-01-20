from flask import Flask
app = Flask(__name__)

@app.route("/projects/<project_name>")
def create_project(project_name):
    return "{\"create project\"}"

@app.route("/users/<user_name>")
def create_user(user_name):
    return "{\"create user\"}"

@app.route("/users/<user_name>/projects/<project_name>/roles/<role>")
def map_project(user_name,project_name,role):
    return "{\"map\"}"

if __name__ == "__main__":
    application.run()
