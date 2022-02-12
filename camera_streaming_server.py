from flask import Flask, jsonify, redirect
import json
import signal
import subprocess

app = Flask(__name__)
rtspServerProcess = None

@app.route('/', methods=['GET'])
def index():
    return jsonify({'available_endpoints': ["/stream/start", "/stream/stop"]})

@app.route('/stream/start', methods=['POST'])
def startStream():
    global rtspServerProcess
    if rtspServerProcess is not None:
        return redirect("rtsp://raspberrypi.local:8554/stream")
    # TODO check request body for width, height and frames
    rtspServerProcess = subprocess.Popen(["v4l2rtspserver", "-W", "1240", "-H", "720", "-F", "24", "-P", "8554", "-u", "/stream", "/dev/video0"], 
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return redirect("rtsp://raspberrypi.local:8554/stream")

@app.route('/stream/stop', methods=['POST'])
def stopStream():
    global rtspServerProcess
    if rtspServerProcess is None:
        return "RTSP server not running", 400
    rtspServerProcess.send_signal(signal.SIGINT)
    rc = rtspServerProcess.wait()
    rtspServerProcess = None
    return f"RTSP server stopped with return code {rc}", 200

# TODO make port configurable with ENV variable
app.run(port=8080, debug=True, threaded=True)
