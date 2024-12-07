from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def hello():
    return render_template("test.html")

@app.route("/data")
def data():
    return ""
if __name__ == "__main__":
    app.run(port=80, debug=True)
