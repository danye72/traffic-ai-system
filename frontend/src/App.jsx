import React, { useState, useEffect } from 'react';
import axios from 'axios';

const App = () => {
  const [points, setPoints] = useState([]);
  const [roiName, setRoiName] = useState("");
  const [data, setData] = useState({ stats: {}, rois: [] });
  const [settings, setSettings] = useState({ 
    conf: 0.25, 
    clahe_limit: 2.0, 
    imgsz: 640, 
    classes: [0, 2, 3, 5, 7],
    show_boxes: true,
    frame_skip: 2 // Valore iniziale
  });
  
  const [videoSize, setVideoSize] = useState({ W: 800, H: 450 });

  const updateVideoSize = () => {
    const sidebarWidth = 300; // corrisponde al pannello sinistro
    const gap = 20; // gap tra colonne
    const availableWidth = window.innerWidth - sidebarWidth - gap - 60; // margine extra
    // assegniamo metà dello spazio disponibile al video e metà alla tabella
    const videoWidth = Math.min(900, Math.max(480, availableWidth * 0.5));
    const videoHeight = Math.round(videoWidth * 9 / 16);
    setVideoSize({ W: videoWidth, H: videoHeight });
  };

  const listaClassi = [
    { id: 0, label: "Persone" },
    { id: 2, label: "Auto" },
    { id: 3, label: "Moto" },
    { id: 5, label: "Bus" },
    { id: 7, label: "Camion" }
  ];

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const res = await axios.get('http://localhost:8000/api/settings');
        setSettings(res.data);
      } catch (e) { console.error("Errore caricamento impostazioni", e); }
    };
    fetchSettings();
    
    // imposta dimensione video iniziale e si aggiorna al resize
    updateVideoSize();
    window.addEventListener('resize', updateVideoSize);

    const interval = setInterval(async () => {
      try {
        const res = await axios.get('http://localhost:8000/api/stats');
        setData(res.data);
      } catch (e) { console.error(e); }
    }, 1000);
    return () => { clearInterval(interval); window.removeEventListener('resize', updateVideoSize); };
  }, []);

  const inviaSettings = async (nuoviSettaggi) => {
    const aggiornati = { ...settings, ...nuoviSettaggi };
    setSettings(aggiornati);
    await axios.post('http://localhost:8000/api/settings', aggiornati);
  };

  const toggleClasseGlobale = (idClasse) => {
    let nuoveClassi = settings.classes.includes(idClasse)
      ? settings.classes.filter(id => id !== idClasse)
      : [...settings.classes, idClasse];
    inviaSettings({ classes: nuoveClassi });
  };

  const toggleClasseZona = (roiId, idClasse) => {
    const roisAggiornate = data.rois.map(roi => {
      if (roi.id === roiId) {
        const attuali = roi.allowed_classes || [0, 2, 3, 5, 7];
        const nuove = attuali.includes(idClasse)
          ? attuali.filter(id => id !== idClasse)
          : [...attuali, idClasse];
        return { ...roi, allowed_classes: nuove };
      }
      return roi;
    });
    setData({ ...data, rois: roisAggiornate });
    axios.post('http://localhost:8000/api/roi', { rois: roisAggiornate });
  };

  const handleCanvasClick = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setPoints([...points, { x: (e.clientX - rect.left) / rect.width, y: (e.clientY - rect.top) / rect.height }]);
  };

  const aggiungiZona = async () => {
    if (points.length < 3 || !roiName) return alert("Disegna un'area e dai un nome!");
    const nuovaRoi = { id: Date.now(), label: roiName, points, allowed_classes: settings.classes };
    const aggiornate = [...data.rois, nuovaRoi];
    await axios.post('http://localhost:8000/api/roi', { rois: aggiornate });
    setPoints([]); setRoiName("");
  };

  return (
    <div style={{ padding: '20px', backgroundColor: '#121212', color: 'white', fontFamily: 'sans-serif', minHeight: '100vh' }}>
      <div style={{ display: 'flex', gap: '20px' }}>
        
        {/* SIDEBAR */}
        <div style={{ width: '300px', background: '#1e1e1e', padding: '15px', borderRadius: '12px', boxShadow: '0 4px 15px rgba(0,0,0,0.5)' }}>
          <h3 style={{ color: '#00e5ff', marginTop: 0, borderBottom: '1px solid #333', paddingBottom: '10px' }}>Pannello AI</h3>
          
          <div style={{marginBottom: '15px', marginTop: '10px'}}>
            <label style={{display:'block', fontSize:'14px'}}>Confidenza: <b>{settings.conf}</b></label>
            <input type="range" min="0.05" max="0.9" step="0.05" value={settings.conf} style={{width:'100%'}} onChange={e => inviaSettings({conf: parseFloat(e.target.value)})}/>
          </div>

          <div style={{marginBottom: '15px'}}>
            <label style={{display:'block', fontSize:'14px'}}>Contrasto (CLAHE): <b>{settings.clahe_limit}</b></label>
            <input type="range" min="0" max="5" step="0.1" value={settings.clahe_limit} style={{width:'100%'}} onChange={e => inviaSettings({clahe_limit: parseFloat(e.target.value)})}/>
          </div>

          {/* AGGIUNTO: SLIDER FRAME SKIP */}
          <div style={{marginBottom: '15px'}}>
            <label style={{display:'block', fontSize:'14px'}}>Salto Frame (Fluidità): <b>{settings.frame_skip}</b></label>
            <input type="range" min="1" max="10" step="1" value={settings.frame_skip || 1} style={{width:'100%'}} onChange={e => inviaSettings({frame_skip: parseInt(e.target.value)})}/>
            <small style={{color: '#888', fontSize: '11px'}}>Aumenta se il video rallenta (salta frame CPU)</small>
          </div>

          <div style={{marginBottom: '20px', display: 'flex', alignItems: 'center', background: '#2d2d2d', padding: '10px', borderRadius: '8px'}}>
            <input type="checkbox" id="showBoxes" checked={settings.show_boxes} onChange={e => inviaSettings({show_boxes: e.target.checked})} style={{marginRight: '10px', cursor:'pointer'}} />
            <label htmlFor="showBoxes" style={{fontSize: '14px', cursor:'pointer'}}>Mostra Box Rilevamento</label>
          </div>

          <div style={{marginBottom: '20px'}}>
            <label style={{display:'block', marginBottom:'5px', fontSize:'14px'}}>Risoluzione AI</label>
            <select value={settings.imgsz} onChange={e => inviaSettings({imgsz: parseInt(e.target.value)})} style={{width:'100%', padding:'8px', background:'#333', color:'white', border:'1px solid #444', borderRadius:'6px'}}>
              <option value="320">320px (Veloce)</option>
              <option value="480">480px (Medio)</option>
              <option value="640">640px (Preciso)</option>
            </select>
          </div>

          <div style={{background: '#252525', padding: '12px', borderRadius: '8px', marginBottom: '20px'}}>
            <h4 style={{margin: '0 0 10px 0', fontSize: '14px', color: '#00e5ff'}}>Oggetti da Rilevare</h4>
            {listaClassi.map(cls => (
              <div key={cls.id} style={{display: 'flex', alignItems: 'center', marginBottom: '6px', fontSize: '14px'}}>
                <input type="checkbox" checked={settings.classes.includes(cls.id)} onChange={() => toggleClasseGlobale(cls.id)} style={{marginRight: '10px'}} />
                <span>{cls.label}</span>
              </div>
            ))}
          </div>

          <button onClick={() => axios.post('http://localhost:8000/api/stats/reset')} style={{ width: '100%', padding: '12px', background: '#ff5252', border: 'none', borderRadius: '6px', color: 'white', fontWeight: 'bold', cursor: 'pointer' }}>AZZERA CONTEGGI</button>
          <button onClick={() => { if(window.confirm("Eliminare tutte le zone?")) axios.post('http://localhost:8000/api/roi', {rois:[]}) }} style={{ width: '100%', padding: '12px', background: 'transparent', border: '1px solid #ff5252', borderRadius: '6px', color: '#ff5252', fontWeight: 'bold', cursor: 'pointer', marginTop: '10px' }}>CANCELLA ZONE</button>
        </div>

        {/* VIDEO + TABELLA affiancate */}
        <div style={{ flex: 1, display: 'flex', gap: '20px', alignItems: 'flex-start' }}>
          {/* Video column */}
          <div style={{ flex: 1 }}>
            <div style={{ position: 'relative', border: '2px solid #333', borderRadius: '12px', overflow: 'hidden', width: videoSize.W, height: videoSize.H, background: '#000' }}>
              <img
                src="http://localhost:8000/api/video_feed"
                onClick={handleCanvasClick}
                style={{ width: videoSize.W, height: videoSize.H, cursor: 'crosshair' }}
              />
              <svg style={{ position: 'absolute', top: 0, left: 0, width: videoSize.W, height: videoSize.H, pointerEvents: 'none' }}>
                {points.map((p, i) => <circle key={i} cx={p.x * videoSize.W} cy={p.y * videoSize.H} r="6" fill="#00e5ff" stroke="white" strokeWidth="1" />)}
                {points.length > 1 && <polyline points={points.map(p => `${p.x * videoSize.W},${p.y * videoSize.H}`).join(' ')} fill="none" stroke="#00e5ff" strokeWidth="3" />}
              </svg>
            </div>

            <div style={{ marginTop: '15px', display: 'flex', gap: '10px' }}>
              <input placeholder="Nome zona..." value={roiName} onChange={e => setRoiName(e.target.value)} style={{ padding: '12px', flex: 1, borderRadius: '8px', border: 'none', background: '#1e1e1e', color: 'white' }} />
              <button onClick={aggiungiZona} style={{ padding: '12px 25px', background: '#00e5ff', color: 'black', fontWeight: 'bold', border: 'none', borderRadius: '8px', cursor: 'pointer' }}>AGGIUNGI ZONA</button>
            </div>
          </div>

          {/* Table column */}
          <div style={{ width: '48%', maxWidth: 720, overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'separate', borderSpacing: '0 5px', minWidth: '520px' }}>
              <thead>
                <tr style={{ textAlign: 'left', color: '#00e5ff' }}>
                  <th style={{ padding: '15px' }}>Zona</th>
                  <th style={{ textAlign: 'center' }}>Persone</th>
                  <th style={{ textAlign: 'center' }}>Auto</th>
                  <th style={{ textAlign: 'center' }}>Moto</th>
                  <th style={{ textAlign: 'center' }}>Bus</th>
                  <th style={{ textAlign: 'center' }}>Camion</th>
                  <th style={{ textAlign: 'center' }}>Filtri per Zona</th>
                  <th style={{ textAlign: 'right', paddingRight: '15px' }}>Azioni</th>
                </tr>
              </thead>
              <tbody>
                {data.rois.map(roi => {
                  const s = data.stats[roi.id] || {person:0, car:0, motorcycle:0, bus:0, truck:0, occupied: false};
                  const attivi = roi.allowed_classes || [0, 2, 3, 5, 7];
                  return (
                    <tr key={roi.id} style={{ background: s.occupied ? 'rgba(0,229,255,0.1)' : '#1e1e1e' }}>
                      <td style={{ padding: '15px', borderRadius: '10px 0 0 10px', fontWeight: 'bold' }}>{roi.label}</td>
                      <td style={{ textAlign: 'center' }}>{s.person}</td>
                      <td style={{ textAlign: 'center' }}>{s.car}</td>
                      <td style={{ textAlign: 'center' }}>{s.motorcycle}</td>
                      <td style={{ textAlign: 'center' }}>{s.bus}</td>
                      <td style={{ textAlign: 'center' }}>{s.truck}</td>
                      <td style={{ textAlign: 'center' }}>
                        <div style={{ display: 'flex', gap: '4px', justifyContent: 'center' }}>
                          {listaClassi.map(c => (
                            <button key={c.id} onClick={() => toggleClasseZona(roi.id, c.id)}
                              style={{ padding: '4px 7px', fontSize: '10px', borderRadius: '4px', border: 'none', cursor: 'pointer',
                                       background: attivi.includes(c.id) ? '#00e5ff' : '#333',
                                       color: attivi.includes(c.id) ? 'black' : '#777' }}>
                              {c.label.charAt(0)}
                            </button>
                          ))}
                        </div>
                      </td>
                      <td style={{ textAlign: 'right', paddingRight: '15px', borderRadius: '0 10px 10px 0' }}>
                        <button onClick={() => { if(window.confirm("Eliminare?")) axios.delete(`http://localhost:8000/api/roi/${roi.id}`) }} style={{ background: 'none', border: 'none', cursor: 'pointer' }}>🗑️</button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;