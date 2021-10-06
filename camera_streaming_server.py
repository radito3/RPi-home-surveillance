import io
import picamera
import logging
import socketserver
import subprocess
from threading import Condition
from http import server

# TODO: move to different file and load dynamically
PAGE="""\
<html>
<head>
<title>picamera MJPEG streaming demo</title>
</head>
<body>
<h1>PiCamera MJPEG Streaming Demo</h1>
<img src="stream.mjpg" width="640" height="480" />
</body>
</html>
"""

# TODO: how is this used by the http handler?
class StreamingOutput(object):
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            # New frame, copy the existing buffer's content and notify all
            # clients it's available
            self.buffer.truncate()
            with self.condition:
                self.frame = self.buffer.getvalue()
                self.condition.notify_all()
            self.buffer.seek(0)
        return self.buffer.write(buf)

class StreamingHandler(server.BaseHTTPRequestHandler):
    # TODO: add another request that stops the streaming gracefully
    # (streaming could be offloaded to a different thread and the main thread could stop that)
    def do_GET(self):
        if self.path == '/':
	    # TODO: send json or html about available endpoints, do not redirect
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
	    # TODO: do not end URLs with file extensions
            content = PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
	# TODO: extract these path handlers in separate functions/objects
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning('Removed streaming client %s: %s', self.client_address, str(e))
        else:
            self.send_error(404)
            self.end_headers()

# Start rtsp server on a /start_stream call and stop it on a /stop_stream call
# This could lead to the API being RPC-oriented
class RTSPServerDelegate():
    # TODO: pass argumets from network request to process, do not use hardcoded values. Instead, have default values
    with subprocess.Popen(["v4l2rtspserver", "-W", "1920", "-H", "1080", "-F", "24", "-P", "8554", "/dev/video0"],
			  stdout=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
	proc.wait()

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

# TODO: move this to a request handler
# TODO: up the resolution to the max available (or 1080p)
with picamera.PiCamera(resolution='1920x1080', framerate=24) as camera:
    output = StreamingOutput()
    camera.start_recording(output, format='mjpeg')
    try:
        address = ('', 8080)
        server = StreamingServer(address, StreamingHandler)
        server.serve_forever() # TODO: make this stoppable
    except KeyboardInterrupt:
        print("exiting...")
    finally:
        camera.stop_recording()
