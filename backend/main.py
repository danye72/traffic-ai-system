import cv2
import json
import os
import numpy as np
import threading
import time
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO
from shapely.geometry import Point, Polygon

# --- CONFIGURAZIONE ---
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Torniamo al modello Nano per la velocità, ma con ByteTrack per la precisione
MODEL_PATH = 'yolov8n.pt' 
VIDEO_PATH = "data/video.mp4"
CONFIG_PATH = "config/rois.json"

os.makedirs("config", exist_ok=True)
model = YOLO(MODEL_PATH)

# --- STATO GLOBALE ---
stats = {}
counted_ids_per_roi = {}
current_rois = []
latest_processed_frame = None
class_map = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}
data_lock = threading.Lock()

def sync_stats():
    global stats, counted_ids_per_roi, current_rois
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                current_rois = json.load(f).get("rois", [])
        except: current_rois = []
    
    c_ids = {str(r['id']) for r in current_rois}
    with data_lock:
        stats = {rid: val for rid, val in stats.items() if rid in c_ids}
        counted_ids_per_roi = {rid: val for rid, val in counted_ids_per_roi.items() if rid in c_ids}
        for rid in c_ids:
            if rid not in stats:
                stats[rid] = {"car": 0, "bus": 0, "truck": 0, "motorcycle": 0, "occupied": False}
                counted_ids_per_roi[rid] = set()

sync_stats()

# --- STREAMING VIDEO ---
class VideoStream:
    def __init__(self, path):
        self.cap = cv2.VideoCapture(path)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 25.0
        self.frame_delay = 1.0 / self.fps
        self.frame = None
        self.stopped = False

    def start(self):
        threading.Thread(target=self.update, daemon=True).start()
        return self

    def update(self):
        while not self.stopped:
            t1 = time.time()
            success, frame = self.cap.read()
            if not success:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            self.frame = frame
            wait = self.frame_delay - (time.time() - t1)
            if wait > 0: time.sleep(wait)

vs = VideoStream(VIDEO_PATH).start()

# --- CORE DI ELABORAZIONE ---
def processing_worker():
    global stats, latest_processed_frame
    frame_counter = 0
    
    while True:
        frame = vs.frame
        if frame is None:
            time.sleep(0.01)
            continue
        
        frame_counter += 1
        # Analizziamo 1 frame ogni 3 per non saturare la CPU
        if frame_counter % 3 != 0:
            continue

        h, w = frame.shape[:2]
        
        # ByteTrack gestisce i salti temporali tra i frame e le ombre
        results = model.track(
            frame, 
            persist=True, 
            verbose=False, 
            conf=0.15, 
            imgsz=640, 
            classes=[2, 3, 5, 7],
            tracker="bytetrack.yaml"
        )
        
        detections = []
        if results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            ids = results[0].boxes.id.int().cpu().numpy()
            clss = results[0].boxes.cls.int().cpu().numpy()
            for b, obj_id, cls in zip(boxes, ids, clss):
                detections.append({"box": [b[0]/w, b[1]/h, b[2]/w, b[3]/h], "id": int(obj_id), "class": int(cls)})

        with data_lock:
            for roi in current_rois:
                rid = str(roi['id'])
                poly = Polygon([(p['x'], p['y']) for p in roi['points']])
                
                is_occ = False
                for det in detections:
                    # Multi-punto: se una parte della moto tocca la zona, conta
                    p_center = Point((det["box"][0]+det["box"][2])/2, (det["box"][1]+det["box"][3])/2)
                    p_base = Point((det["box"][0]+det["box"][2])/2, det["box"][3])
                    
                    if poly.contains(p_center) or poly.contains(p_base):
                        is_occ = True
                        if det["id"] not in counted_ids_per_roi[rid]:
                            label = class_map.get(det["class"], "car")
                            stats[rid][label] += 1
                            counted_ids_per_roi[rid].add(det["id"])
                
                if rid in stats:
                    stats[rid]["occupied"] = is_occ

        # Disegno semplificato per ridurre carico video
        annotated_frame = frame.copy()
        for idx, roi in enumerate(current_rois):
            rid = str(roi['id'])
            occ = stats.get(rid, {}).get("occupied", False)
            color = (0, 255, 0) if occ else (0, 0, 255)
            pts = np.array([[p['x']*w, p['y']*h] for p in roi['points']], np.int32)
            cv2.polylines(annotated_frame, [pts], True, color, 2)
            cv2.putText(annotated_frame, f"Z {idx+1}", (int(pts[0][0]), int(pts[0][1])-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        latest_processed_frame = annotated_frame

threading.Thread(target=processing_worker, daemon=True).start()

# --- API ---
@app.get("/api/video_feed")
async def video_feed():
    def stream():
        while True:
            if latest_processed_frame is not None:
                # JPEG Quality a 70 per fluidità web
                ret, buffer = cv2.imencode('.jpg', latest_processed_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(0.05)
    return StreamingResponse(stream(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/api/stats")
async def get_stats():
    with data_lock:
        return {"stats": stats, "order": [str(r['id']) for r in load_rois_from_file()]}

def load_rois_from_file():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f: return json.load(f).get("rois", [])
        except: return []
    return []

@app.post("/api/stats/reset")
async def reset_stats():
    global stats, counted_ids_per_roi
    with data_lock:
        for rid in stats:
            for k in ["car", "bus", "truck", "motorcycle"]: stats[rid][k] = 0
            counted_ids_per_roi[rid] = set()
    return {"status": "reset"}

@app.post("/api/roi")
async def save_roi(data: dict):
    with open(CONFIG_PATH, "w") as f: json.dump(data, f)
    sync_stats()
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
