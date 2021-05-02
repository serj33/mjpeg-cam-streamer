import io, time, threading, random
from bottle import run, route, response
import cv2

class Camera():
    def __init__(self, path='/dev/video0'):
        self._image = None
        self._image_ready = threading.Condition()
        self._device = cv2.VideoCapture(path, cv2.CAP_V4L)
        if not (self._device.isOpened()):
            raise RuntimeError(f"cannot open {path}")
        self._device.set(cv2.CAP_PROP_CONVERT_RGB, False)
        self._device.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M','J','P','G'))
        self._do_capture = True
        self._capture_thread = threading.Thread(target = self._capture_image)
        self._capture_thread.start()

    def get_image(self):
        with self._image_ready:
            self._image_ready.wait()
            return self._image

    def _capture_image(self):
        while self._do_capture:
            ret, frame = self._device.read()
            if ret:
                with self._image_ready:
                    self._image = frame.tobytes()
                    self._image_ready.notify_all()
        self._device.release()

    def __del__(self):
        self._do_capture = False

class MJPEGHttpFrames():
    def __init__(self, boundary):
        self.boundary = boundary

    def __iter__(self):
        return self
    
    def __next__(self):
        global cam
        image = cam.get_image()
        header = f"--{self.boundary}\r\n" + "Content-Type: image/jpeg\r\n" + f"Content-Length: {len(image)}\r\n" + "\r\n"
        return header.encode('ascii') + image

def gen_boundary():
    boundary = bytearray(25)
    for i in range(0, 25):
        boundary[i] = random.choice((lambda: random.randint(0, 8) + 48, lambda: random.randint(0, 24) + 65, lambda: random.randint(0, 24) + 97))()
    return boundary.decode('ascii')

@route("/")
def index():
    boundary = gen_boundary()
    response.set_header('Content-Type', f'multipart/x-mixed-replace;boundary=\"{boundary}\"')
    return MJPEGHttpFrames(boundary)

cam = Camera()
run(host='0.0.0.0', port=8080, quiet=True)
