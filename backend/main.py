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

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

MODEL_PATH = 'yolov8n.pt' 
VIDEO_PATH = "data/video.mp4"
CONFIG_PATH = "config/rois.json"

os.makedirs("config", exist_ok=True)
model = YOLO(MODEL_PATH)

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
    
    with data_lock:
        for roi in current_rois:
            rid = str(roi['id'])
            if rid not in stats:
                stats[rid] = {"car": 0, "bus": 0, "truck": 0, "motorcycle": 0, "occupied": False}
                counted_ids_per_roi[rid] = set()

sync_stats()

class VideoStream:
    def __init__(self, path):
        self.cap = cv2.VideoCapture(path)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        if self.fps <= 0: self.fps = 25.0
        self.frame_time = 1.0 / self.fps
        self.frame = None
        self.stopped = False

    def start(self):
        threading.Thread(target=self.update, daemon=True).start()
        return self

    def update(self):
        while not self.stopped:
            start_time = time.time()
            success, frame = self.cap.read()
            if not success:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            self.frame = frame
            elapsed = time.time() - start_time
            wait = self.frame_time - elapsed
            if wait > 0:
                time.sleep(wait)

vs = VideoStream(VIDEO_PATH).start()

def processing_worker():
    global latest_processed_frame
    while True:
        frame = vs.frame
        if frame is None:
            time.sleep(0.01)
            continue

        h, w = frame.shape[:2]
        results = model.track(frame, persist=True, verbose=False, conf=0.20, imgsz=640, classes=[2, 3, 5, 7])
        
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
                    bx = det["box"]
                    p_center = Point((bx[0]+bx[2])/2, (bx[1]+bx[3])/2)
                    p_bottom = Point((bx[0]+bx[2])/2, bx[3])
                    
                    if poly.contains(p_center) or poly.contains(p_bottom):
                        is_occ = True
                        if det["id"] not in counted_ids_per_roi[rid]:
                            label_cls = class_map.get(det["class"], "car")
                            stats[rid][label_cls] += 1
                            counted_ids_per_roi[rid].add(det["id"])
                
                if rid in stats:
                    stats[rid]["occupied"] = is_occ

        annotated_frame = frame.copy()
        for roi in current_rois:
            rid = str(roi['id'])
            roi_label = roi.get('label', f"Zona {rid}")
            z_stats = stats.get(rid, {"car": 0, "bus": 0, "truck": 0, "motorcycle": 0})
            total = sum([z_stats[k] for k in ["car", "bus", "truck", "motorcycle"]])
            
            color = (0, 255, 0) if stats.get(rid, {}).get("occupied") else (0, 0, 255)
            pts = np.array([[p['x']*w, p['y']*h] for p in roi['points']], np.int32)
            cv2.polylines(annotated_frame, [pts], True, color, 3)
            
            txt_x, txt_y = int(pts[0][0]), int(pts[0][1]) - 15
            if txt_y < 20: txt_y = int(pts[0][1]) + 30
            
            display_text = f"{roi_label}: {total}"
            (t_w, t_h), _ = cv2.getTextSize(display_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            cv2.rectangle(annotated_frame, (txt_x, txt_y - t_h - 5), (txt_x + t_w, txt_y + 5), (0,0,0), -1)
            cv2.putText(annotated_frame, display_text, (txt_x, txt_y), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
        latest_processed_frame = annotated_frame

threading.Thread(target=processing_worker, daemon=True).start()

@app.get("/api/video_feed")
async def video_feed():
    def stream():
        while True:
            if latest_processed_frame is not None:
                ret, buffer = cv2.imencode('.jpg', latest_processed_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
                yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(0.04)
    return StreamingResponse(stream(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/api/stats")
async def get_stats():
    with data_lock:
        return {"stats": stats, "rois": current_rois}

@app.post("/api/roi")
async def save_roi(data: dict):
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f)
    sync_stats()
    return {"status": "success"}

@app.post("/api/stats/reset")
async def reset_stats():
    global stats, counted_ids_per_roi
    with data_lock:
        for rid in stats:
            for k in ["car", "bus", "truck", "motorcycle"]: stats[rid][k] = 0
            counted_ids_per_roi[rid] = set()
    return {"status": "reset"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)