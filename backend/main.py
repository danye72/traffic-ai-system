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
from shapely.geometry import Polygon, box

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Configurazione Percorsi
MODEL_PATH = 'yolov8n.pt'
VIDEO_PATH = "data/video.mp4"
CONFIG_PATH = "config/rois.json"

os.makedirs("config", exist_ok=True)

# Caricamento modello tramite helper per permettere switch a runtime
model_lock = threading.Lock()
model = None

def load_model(path: str):
    global model, MODEL_PATH
    with model_lock:
        model = YOLO(path)
        MODEL_PATH = path
    return model

# Carica modello iniziale (puoi scegliere 'yolov8n.pt' o 'yolov8s.pt')
load_model(MODEL_PATH)

# Modelli predefiniti (inclusi nomi che Ultralyics può scaricare automaticamente)
DEFAULT_MODELS = [
    'yolov8n.pt',
    'yolov8s.pt',
    'yolov8m.pt',
    'yolov8l.pt',
    'yolov8x.pt'
]

# Stato
stats = {}
counted_ids_per_roi = {}
object_segment_history = {}  # Traccia il segmento per ogni oggetto per ROI
current_rois = []
latest_processed_frame = None
class_map = {0: "person", 2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}
data_lock = threading.Lock()

# Impostazioni Globali (Incluso Frame Skip e Box)
settings = {
    "conf": 0.25, 
    "imgsz": 640, 
    "clahe_limit": 2.0, 
    "model": MODEL_PATH,
    "classes": [0, 2, 3, 5, 7], 
    "show_boxes": True,
    "frame_skip": 2  # Elabora 1 frame ogni X
}

def sync_config():
    global stats, counted_ids_per_roi, current_rois
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                data = json.load(f)
                current_rois = data.get("rois", [])
        except: current_rois = []
    
    with data_lock:
        # Pulisci stats per ROI che non existono più nel config
        rois_ids = {str(roi['id']) for roi in current_rois}
        for rid in list(stats.keys()):
            if rid not in rois_ids:
                del stats[rid]
                if rid in counted_ids_per_roi:
                    del counted_ids_per_roi[rid]
        
        # Aggiungi o aggiorna stats per tutte le ROI nel config
        for roi in current_rois:
            rid = str(roi['id'])
            
            # Inizializza se non esiste
            if rid not in stats:
                stats[rid] = {
                    "total": {"person": 0, "car": 0, "motorcycle": 0, "bus": 0, "truck": 0, "occupied": False},
                    "directions": {}
                }
                if rid not in counted_ids_per_roi:
                    counted_ids_per_roi[rid] = set()
            
            # Aggiorna la lista di direzioni preservando i conteggi
            old_directions = stats[rid].get("directions", {})
            stats[rid]["directions"] = {}
            
            directions = roi.get('directions', [])
            for dir_idx, direction in enumerate(directions):
                dir_name = direction.get('name', f"{direction['from']}→{direction['to']}")
                dir_key = f"dir_{dir_idx}"
                
                # Se la direzione già esiste, preserva i conteggi
                if dir_key in old_directions:
                    stats[rid]["directions"][dir_key] = old_directions[dir_key]
                    # Aggiorna solo il nome se è cambiato
                    stats[rid]["directions"][dir_key]["name"] = dir_name
                else:
                    # Nuova direzione: inizializza con zeri
                    stats[rid]["directions"][dir_key] = {
                        "name": dir_name,
                        "from": direction['from'],
                        "to": direction['to'],
                        "person": 0,
                        "car": 0,
                        "motorcycle": 0,
                        "bus": 0,
                        "truck": 0
                    }

sync_config()

def get_segment_for_point(roi, point_x, point_y):
    """Determina in quale segmento del ROI si trova un punto, basato sulla proiezione sul perimetro"""
    points = roi['points']
    if len(points) < 2:
        return None
    
    segment_count = roi.get('segments', 4)
    
    # Calcola la posizione lungo il perimetro del poligono
    min_distance = float('inf')
    closest_perimeter_pos = 0
    perimeter_length = 0
    
    # Itera attraverso ogni lato del poligono
    for i in range(len(points)):
        p1 = points[i]
        p2 = points[(i + 1) % len(points)]  # Prossimo punto (wrap around)
        
        x1, y1 = p1['x'], p1['y']
        x2, y2 = p2['x'], p2['y']
        
        # Lunghezza di questo lato
        dx = x2 - x1
        dy = y2 - y1
        side_length = (dx**2 + dy**2)**0.5
        
        if side_length > 0:
            # Proietta il punto su questo lato (0 = p1, 1 = p2)
            t = max(0, min(1, ((point_x - x1) * dx + (point_y - y1) * dy) / (side_length**2)))
            
            # Punto proiettato sul lato
            proj_x = x1 + t * dx
            proj_y = y1 + t * dy
            
            # Distanza dal punto alla proiezione
            dist = ((proj_x - point_x)**2 + (proj_y - point_y)**2)**0.5
            
            if dist < min_distance:
                min_distance = dist
                closest_perimeter_pos = perimeter_length + t * side_length
        
        perimeter_length += side_length
    
    # Determina il segmento basato sulla posizione lungo il perimetro
    if perimeter_length > 0:
        segment_length = perimeter_length / segment_count
        segment_id = int(closest_perimeter_pos / segment_length) + 1
        segment_id = min(segment_id, segment_count)
    else:
        segment_id = 1
    
    return segment_id

def check_direction_counting(roi, obj_id, current_segment, cls_name):
    """Controlla se l'oggetto soddisfa i criteri di direzione e conta se necessario.
    Ritorna (should_count, direction_index) dove direction_index è l'indice della direzione matching (-1 se nessuna direzione)
    """
    rid = str(roi['id'])
    directions = roi.get('directions', [])
    
    # Se non ci sono direzioni specificate, conta come prima
    if not directions:
        return True, -1
    
    # Inizializza la history dell'oggetto se non esiste
    if obj_id not in object_segment_history:
        object_segment_history[obj_id] = {}
    
    if rid not in object_segment_history[obj_id]:
        object_segment_history[obj_id][rid] = {
            'entry_segment': None,      # Primo segmento visto (FISSO)
            'last_segment': None,       # Ultimo segmento visto (per tracciare transizioni)
            'counted': False,           # Se è stato già conteggiato
            'direction_idx': -1         # Indice della direzione che ha fatto scattare il conteggio
        }
    
    history = object_segment_history[obj_id][rid]
    
    # Se è il primo rilevamento, registra il segmento di ingresso
    if history['entry_segment'] is None:
        history['entry_segment'] = current_segment
        history['last_segment'] = current_segment
        return False, -1
    
    # Se già contato, non contare di nuovo
    if history['counted']:
        return False, -1
    
    # Se il segmento è diverso dal precedente, c'è una transizione
    if current_segment != history['last_segment']:
        # Controlla se la transizione dal PRIMO segmento al NUOVO segmento è valida
        for dir_idx, direction in enumerate(directions):
            if direction['from'] == history['entry_segment'] and direction['to'] == current_segment:
                # La direzione è corretta, conta l'oggetto
                history['counted'] = True
                history['direction_idx'] = dir_idx
                return True, dir_idx
    
    # Aggiorna l'ultimo segmento visto (ma entry_segment rimane fisso)
    history['last_segment'] = current_segment
    
    return False, -1


def processing_worker():
    global latest_processed_frame
    cap = cv2.VideoCapture(VIDEO_PATH)
    f_counter = 0 
    
    while True:
        success, frame = cap.read()
        if not success:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        f_counter += 1
        # Logica Salto Frame Dinamica
        if f_counter % settings.get("frame_skip", 1) != 0:
            continue

        h, w = frame.shape[:2]
        
        # Miglioramento immagine
        clahe = cv2.createCLAHE(clipLimit=settings["clahe_limit"], tileGridSize=(8,8))
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b_chan = cv2.split(lab)
        cl = clahe.apply(l)
        enhanced = cv2.cvtColor(cv2.merge((cl, a, b_chan)), cv2.COLOR_LAB2BGR)

        # Inferenza
        results = model.track(enhanced, persist=True, verbose=False, conf=settings["conf"], imgsz=settings["imgsz"], classes=settings["classes"])
        annotated_frame = frame.copy()
        
        with data_lock:
            for rid in stats: stats[rid]["total"]["occupied"] = False

            if results[0].boxes.id is not None:
                boxes = results[0].boxes.xyxy.cpu().numpy()
                ids = results[0].boxes.id.int().cpu().numpy()
                clss = results[0].boxes.cls.int().cpu().numpy()

                for b, obj_id, cls in zip(boxes, ids, clss):
                    cls_id = int(cls)
                    cls_name = class_map.get(cls_id)
                    if not cls_name: continue
                    
                    if settings["show_boxes"]:
                        cv2.rectangle(annotated_frame, (int(b[0]), int(b[1])), (int(b[2]), int(b[3])), (255, 255, 0), 2)
                        cv2.putText(annotated_frame, f"ID:{obj_id} {cls_name}", (int(b[0]), int(b[1])-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)

                    veh_box = box(b[0], b[1], b[2], b[3])
                    for roi in current_rois:
                        rid = str(roi['id'])
                        allowed = roi.get('allowed_classes', [0, 2, 3, 5, 7])
                        poly = Polygon([(p['x']*w, p['y']*h) for p in roi['points']])
                        
                        if poly.intersects(veh_box):
                            if cls_id in allowed:
                                # Calcola il centroide della bounding box
                                cx = (b[0] + b[2]) / 2
                                cy = (b[1] + b[3]) / 2
                                current_segment = get_segment_for_point(roi, cx / w, cy / h)
                                
                                # Controlla se l'oggetto deve essere contato in base alla direzione
                                should_count, direction_idx = check_direction_counting(roi, int(obj_id), current_segment, cls_name)
                                
                                # Marca come occupato SOLO se l'oggetto segue una direzione valida (o nessuna direzione è configurata)
                                if should_count:
                                    stats[rid]["total"]["occupied"] = True
                                    
                                    if int(obj_id) not in counted_ids_per_roi[rid]:
                                        # Incrementa il conteggio totale
                                        stats[rid]["total"][cls_name] += 1
                                        
                                        # Se si sa quale direzione ha fatto scattare il conteggio, incrementa anche quella
                                        if direction_idx >= 0 and f"dir_{direction_idx}" in stats[rid]["directions"]:
                                            stats[rid]["directions"][f"dir_{direction_idx}"][cls_name] += 1
                                        
                                        counted_ids_per_roi[rid].add(int(obj_id))

            for roi in current_rois:
                rid = str(roi['id'])
                s = stats[rid]["total"]
                pts = np.array([[p['x']*w, p['y']*h] for p in roi['points']], np.int32)
                cv2.polylines(annotated_frame, [pts], True, (0, 255, 0) if s["occupied"] else (0, 0, 255), 2)
                label = f"{roi.get('label','')}: P:{s['person']} A:{s['car']} B:{s['bus']}"
                cv2.putText(annotated_frame, label, (int(pts[0][0]), int(pts[0][1]) - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        latest_processed_frame = annotated_frame
        time.sleep(0.01)

threading.Thread(target=processing_worker, daemon=True).start()

@app.get("/api/video_feed")
async def video_feed():
    def generate():
        while True:
            if latest_processed_frame is not None:
                ret, jpeg = cv2.imencode('.jpg', latest_processed_frame)
                if ret: yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
            time.sleep(0.04)
    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/api/stats")
async def get_stats():
    with data_lock: return {"stats": stats, "rois": current_rois}

@app.get("/api/settings")
async def get_settings(): return settings


@app.get("/api/models")
async def list_models():
    base = os.path.dirname(__file__)
    local = []
    try:
        local = [f for f in os.listdir(base) if f.endswith('.pt')]
    except Exception:
        local = []
    # Unione mantenendo ordine: DEFAULT_MODELS poi file locali aggiuntivi
    models = []
    for m in DEFAULT_MODELS:
        if m not in models:
            models.append(m)
    for m in local:
        if m not in models:
            models.append(m)
    return {"models": models}


@app.get("/api/models")
async def list_models():
    try:
        base = os.path.dirname(__file__)
        models = [f for f in os.listdir(base) if f.endswith('.pt')]
    except Exception:
        models = []
    return {"models": models}

@app.post("/api/settings")
async def update_settings(new_settings: dict):
    global settings
    # Se è richiesto un cambio modello, proviamo a caricarlo
    model_requested = new_settings.get('model')
    if model_requested and model_requested != MODEL_PATH:
        model_path_local = os.path.join(os.path.dirname(__file__), model_requested) if not os.path.isabs(model_requested) else model_requested
        # Prova a caricare il modello; se fallisce ritorna errore
        try:
            load_model(model_path_local)
            new_settings['model'] = MODEL_PATH
        except Exception as e:
            return {"error": f"Impossibile caricare modello: {e}"}

    settings.update(new_settings)
    return settings

@app.post("/api/roi")
async def save_roi(data: dict):
    with open(CONFIG_PATH, "w") as f: json.dump(data, f)
    sync_config()
    return {"status": "success"}

@app.delete("/api/roi/{roi_id}")
async def delete_roi(roi_id: int):
    global current_rois, stats, counted_ids_per_roi, object_segment_history
    rid_str = str(roi_id)
    with data_lock:
        current_rois = [r for r in current_rois if r['id'] != roi_id]
        if rid_str in stats: del stats[rid_str]
        if rid_str in counted_ids_per_roi: del counted_ids_per_roi[rid_str]
        
        # Pulisci history per questo ROI
        for obj_id in list(object_segment_history.keys()):
            if rid_str in object_segment_history[obj_id]:
                del object_segment_history[obj_id][rid_str]
            if not object_segment_history[obj_id]:
                del object_segment_history[obj_id]
        
        with open(CONFIG_PATH, "w") as f: json.dump({"rois": current_rois}, f)
    return {"status": "deleted"}

@app.post("/api/stats/reset")
async def reset_stats():
    global stats, counted_ids_per_roi, object_segment_history
    with data_lock:
        for rid in stats:
            # Reset conteggio totale
            for k in ["person", "car", "bus", "truck", "motorcycle"]: 
                stats[rid]["total"][k] = 0
            stats[rid]["total"]["occupied"] = False
            
            # Reset conteggi per direzione
            for dir_key in stats[rid]["directions"]:
                for k in ["person", "car", "bus", "truck", "motorcycle"]: 
                    stats[rid]["directions"][dir_key][k] = 0
            
            counted_ids_per_roi[rid] = set()
        
        object_segment_history.clear()
    return {"status": "reset"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)