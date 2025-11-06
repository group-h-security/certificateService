from flask import Flask
from flask import jsonify
from flask import request
app = Flask(__name__)

messages = [
	{"id": 1, "author": "system", "text": "welcome to the flask api"}
]

@app.route("/")
def home():
	return jsonify({
		"status": "okay",
		"message": "flask is running"
		
	})

@app.route("/messages", methods=["GET"])
def getMessages():
	return jsonify(messages)

@app.route("/messages", methods=["POST"])
def addMessage():
	data = request.get_json()
	
	if not data or "author" not in data or "text" not in data:
		return jsonify({"error": "missing author or text field"})
	
	new_msg = {
		"id": len(messages)+1, 
		"author": data["author"],
		"text": data["text"]
	}

	messages.append(new_msg)
	return jsonify(new_msg), 201

@app.route("/messages/<int:msg_id>", methods=["GET"])
def getMessage(msg_id):
	msg = next((msg for msg in messages if msg["id"] == msg_id), None)
	if msg:
		return jsonify(msg)
	if not msg:
		return jsonify({
			"Error": "No message for this id"
		}), 404

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)
	
