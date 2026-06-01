from telegram import Bot
import time
import os
import face_recognition
from flask import Flask, jsonify, send_from_directory, Response
from flask_cors import CORS
from ultralytics import YOLO
import cv2
import requests
import yagmail
from dotenv import load_dotenv
import os

load_dotenv()

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

app = Flask(__name__)
CORS(app)

# =========================
# EMAIL CONFIGURATION
# =========================
EMAIL_ADDRESS = "ankitmondal.cse22@gmail.com"
EMAIL_PASSWORD = "qgooahqkrksnttvu"

# =========================
# TELEGRAM CONFIGURATION
# =========================
TELEGRAM_BOT_TOKEN = "8059657579:AAFCim6p9YQJ6FcwOkgzWJhAlJj6_UNTmII"
TELEGRAM_CHAT_ID = "1095851239"

# =========================
# LOAD YOLO MODEL
# =========================
model = YOLO("yolov8n.pt")

# =========================
# CAMERA
# =========================
camera = cv2.VideoCapture(0)

# =========================
# KNOWN FACE STORAGE
# =========================
known_face_encodings = []
known_face_names = []

known_faces_dir = "known_faces"

# =========================
# LOAD KNOWN FACES
# =========================
for filename in os.listdir(known_faces_dir):

    if filename.endswith(".jpg") or filename.endswith(".png"):

        try:

            image_path = os.path.join(
                known_faces_dir,
                filename
            )

            image = face_recognition.load_image_file(
                image_path
            )

            face_encodings = face_recognition.face_encodings(
                image
            )

            if len(face_encodings) > 0:

                known_face_encodings.append(
                    face_encodings[0]
                )

                known_face_names.append(
                    os.path.splitext(filename)[0]
                )

                print("Loaded face:", filename)

            else:

                print(f"No face found in {filename}")

        except Exception as e:

            print(f"Error processing {filename}: {e}")

# =========================
# LIVE CAMERA STREAM
# =========================
def generate_frames():

    while True:

        success, frame = camera.read()

        if not success:
            break

        # RESTRICTED ZONE
        cv2.rectangle(
            frame,
            (100, 100),
            (500, 400),
            (0, 0, 255),
            3
        )

        cv2.putText(
            frame,
            "RESTRICTED ZONE",
            (100, 90),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 255),
            2
        )

        ret, buffer = cv2.imencode('.jpg', frame)

        frame_bytes = buffer.tobytes()

        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' +
            frame_bytes +
            b'\r\n'
        )

# =========================
# VIDEO FEED ROUTE
# =========================
@app.route('/video_feed')
def video_feed():

    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

# =========================
# SCREENSHOT ROUTE
# =========================
@app.route('/screenshots/<path:filename>')
def get_screenshot(filename):

    return send_from_directory(
        'screenshots',
        filename
    )

# =========================
# DETECTION ROUTE
# =========================
@app.route("/detect")
def detect():

    success, frame = camera.read()

    if not success:

        return jsonify({
            "error": "Camera not working"
        })

    # =========================
    # RESTRICTED ZONE
    # =========================
    zone_x1 = 100
    zone_y1 = 100
    zone_x2 = 500
    zone_y2 = 400

    cv2.rectangle(
        frame,
        (zone_x1, zone_y1),
        (zone_x2, zone_y2),
        (0, 0, 255),
        3
    )

    cv2.putText(
        frame,
        "RESTRICTED ZONE",
        (zone_x1, zone_y1 - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 0, 255),
        2
    )

    # =========================
    # YOLO DETECTION
    # =========================
    results = model(frame)

    detected_objects = []

    threat_level = "LOW"

    intrusion_detected = False

    for result in results:

        for box in result.boxes:

            x1, y1, x2, y2 = map(
                int,
                box.xyxy[0]
            )

            class_id = int(box.cls[0])

            object_name = model.names[class_id]

            detected_objects.append(object_name)

            # PERSON INSIDE ZONE
            if object_name == "person":

                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2

                if (
                    zone_x1 < center_x < zone_x2 and
                    zone_y1 < center_y < zone_y2
                ):

                    intrusion_detected = True

                    threat_level = "HIGH"

                    cv2.putText(
                        frame,
                        "INTRUSION DETECTED",
                        (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1.2,
                        (0, 0, 255),
                        3
                    )

    # =========================
    # FACE RECOGNITION
    # =========================
    rgb_frame = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )

    face_locations = face_recognition.face_locations(
        rgb_frame
    )

    face_encodings = face_recognition.face_encodings(
        rgb_frame,
        face_locations
    )

    detected_faces = []

    for face_encoding in face_encodings:

        name = "Unknown"

        if len(known_face_encodings) > 0:

            face_distances = (
                face_recognition.face_distance(
                    known_face_encodings,
                    face_encoding
                )
            )

            print(
                "Face distances:",
                face_distances
            )

            best_match_index = (
                face_distances.argmin()
            )

            if (
                face_distances[
                    best_match_index
                ] < 0.8
            ):

                name = (
                    known_face_names[
                        best_match_index
                    ].split("_")[0]
                )

            else:

                threat_level = "HIGH"

                unknown_filename = (
                    f"unknown_faces/"
                    f"unknown_{int(time.time())}.jpg"
                )

                cv2.imwrite(
                    unknown_filename,
                    frame
                )

        else:

            threat_level = "HIGH"

        detected_faces.append(name)

    # =========================
    # SAVE ALERT
    # =========================
    if "person" in detected_objects:

        screenshot_filename = (
            f"screenshots/"
            f"detection_{int(time.time())}.jpg"
        )

        cv2.imwrite(
            screenshot_filename,
            frame
        )

        # =========================
        # SEND ALERTS
        # =========================
        if threat_level == "HIGH":

            # EMAIL ALERT
            try:

                yag = yagmail.SMTP(
                    EMAIL_ADDRESS,
                    EMAIL_PASSWORD
                )

                yag.send(
                    to="ankitmondalcse.022@gmail.com",
                    subject="🚨 AI Surveillance Alert",
                    contents=[
                        "Restricted Zone Intrusion Detected",
                        f"Threat Level: {threat_level}",
                        f"Detected Faces: {detected_faces}"
                    ],
                    attachments=screenshot_filename
                )

                print("Email alert sent")

            except Exception as e:

                print("Email failed:", e)

                        # TELEGRAM ALERT
            try:

                import asyncio

                async def send_telegram():

                    bot = Bot(
                        token=TELEGRAM_BOT_TOKEN
                    )

                    await bot.send_message(
                        chat_id=TELEGRAM_CHAT_ID,
                        text=(
                            f"🚨 AI SURVEILLANCE ALERT 🚨\n\n"
                            f"Threat Level: {threat_level}\n"
                            f"Detected Faces: {detected_faces}\n"
                            f"Intrusion Detected!"
                        )
                    )

                asyncio.run(send_telegram())

                print("Telegram alert sent")

            except Exception as e:

                print("Telegram failed:", e)
        # =========================
        # SEND TO BACKEND
        # =========================
        try:

            event_message = (
                "Restricted Zone Intrusion"
                if intrusion_detected
                else f"Detected Faces: {detected_faces}"
            )

            requests.post(
                "http://localhost:8080/alerts",
                json={
                    "event": event_message,
                    "objects": detected_objects,
                    "image": screenshot_filename,
                    "threatLevel": threat_level
                }
            )

        except Exception as e:

            print(
                "Backend connection failed:",
                e
            )

    # =========================
    # RETURN JSON
    # =========================
    return jsonify({
        "detected_objects": detected_objects,
        "detected_faces": detected_faces,
        "threat_level": threat_level,
        "intrusion_detected": intrusion_detected
    })

# =========================
# RUN APP
# =========================
if __name__ == "__main__":

    app.run(port=5000)