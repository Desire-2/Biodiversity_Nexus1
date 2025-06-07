from app import app, socketio

if __name__ == "__main__":
    # local dev
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)