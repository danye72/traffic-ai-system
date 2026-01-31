import React, { useState, useEffect } from 'react';
import axios from 'axios';

const App = () => {
  const [points, setPoints] = useState([]);
  const [roiName, setRoiName] = useState("");
  const [data, setData] = useState({ stats: {}, rois: [] });
  const W = 800;
  const H = 450;

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await axios.get('http://localhost:8000/api/stats');
        setData(res.data);
      } catch (e) { console.error(e); }
    };
    fetchData();
    const interval = setInterval(fetchData, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleCanvasClick = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setPoints([...points, { 
      x: (e.clientX - rect.left) / rect.width, 
      y: (e.clientY - rect.top) / rect.height 
    }]);
  };

  const saveCurrentRoi = async () => {
    if (points.length < 3) return alert("Disegna un'area con almeno 3 punti!");
    if (!roiName) return alert("Assegna un nome alla zona prima di salvare.");
    
    const newRoi = { 
      id: Date.now(), 
      label: roiName,
      points: points 
    };
    
    const updatedRois = [...data.rois, newRoi];
    setPoints([]);
    setRoiName("");
    await axios.post('http://localhost:8000/api/roi', { rois: updatedRois });
  };

  const resetAll = async () => {
    if (!window.confirm("Vuoi cancellare tutte le zone e resettare i conteggi?")) return;
    await axios.post('http://localhost:8000/api/roi', { rois: [] });
    await axios.post('http://localhost:8000/api/stats/reset');
  };

  return (
    <div style={{ padding: '20px', backgroundColor: '#0f0f0f', color: 'white', fontFamily: 'Segoe UI, sans-serif', minHeight: '100vh' }}>
      <h2 style={{ color: '#00e5ff', borderBottom: '1px solid #333', paddingBottom: '10px' }}>Dashboard Analisi Traffico AI</h2>
      
      <div style={{ display: 'flex', gap: '30px', marginTop: '20px' }}>
        {/* Monitor Video */}
        <div>
          <div style={{ position: 'relative', border: '2px solid #444', borderRadius: '8px', overflow: 'hidden' }}>
            <img src="http://localhost:8000/api/video_feed" onClick={handleCanvasClick} style={{ width: W, height: H, cursor: 'crosshair', display: 'block' }} />
            <svg style={{ position: 'absolute', top: 0, left: 0, width: W, height: H, pointerEvents: 'none' }}>
              {points.map((p, i) => <circle key={i} cx={p.x * W} cy={p.y * H} r="4" fill="#ffea00" />)}
              {points.length > 1 && <polyline points={points.map(p => `${p.x * W},${p.y * H}`).join(' ')} fill="none" stroke="#ffea00" strokeWidth="2" strokeDasharray="4" />}
            </svg>
          </div>
          
          <div style={{ display: 'flex', gap: '10px', marginTop: '15px' }}>
            <input 
              type="text" 
              placeholder="Nome nuova zona..." 
              value={roiName}
              onChange={(e) => setRoiName(e.target.value)}
              style={{ flex: 1, padding: '12px', borderRadius: '4px', border: '1px solid #444', backgroundColor: '#1a1a1a', color: 'white' }}
            />
            <button onClick={saveCurrentRoi} style={{ padding: '10px 25px', background: '#00c853', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>
              SALVA AREA
            </button>
          </div>
        </div>

        {/* Tabella Dati */}
        <div style={{ flex: 1 }}>
          <table style={{ width: '100%', backgroundColor: '#181818', borderCollapse: 'collapse', borderRadius: '8px', overflow: 'hidden' }}>
            <thead>
              <tr style={{ background: '#333', color: '#00e5ff', textAlign: 'left' }}>
                <th style={{ padding: '15px' }}>ZONA</th>
                <th style={{ textAlign: 'center' }}>AUTO</th>
                <th style={{ textAlign: 'center' }}>MOTO</th>
                <th style={{ textAlign: 'center' }}>PESANTI</th>
                <th style={{ textAlign: 'center', background: '#00e5ff', color: '#000' }}>TOTALE</th>
              </tr>
            </thead>
            <tbody>
              {data.rois.map((roi) => {
                const s = data.stats[roi.id] || {car:0, motorcycle:0, bus:0, truck:0, occupied: false};
                const heavy = (s.bus || 0) + (s.truck || 0);
                const total = s.car + s.motorcycle + heavy;
                return (
                  <tr key={roi.id} style={{ borderBottom: '1px solid #2a2a2a', background: s.occupied ? 'rgba(0, 229, 255, 0.1)' : 'transparent' }}>
                    <td style={{ padding: '15px', fontWeight: '500' }}>{roi.label}</td>
                    <td style={{ textAlign: 'center' }}>{s.car}</td>
                    <td style={{ textAlign: 'center', color: '#ffea00' }}>{s.motorcycle}</td>
                    <td style={{ textAlign: 'center' }}>{heavy}</td>
                    <td style={{ textAlign: 'center', fontWeight: 'bold', fontSize: '1.1em', color: '#00e5ff' }}>{total}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          
          <button onClick={resetAll} style={{ width: '100%', marginTop: '25px', padding: '12px', background: '#d32f2f', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>
            RESETTA TUTTE LE ZONE
          </button>
        </div>
      </div>
    </div>
  );
};

export default App;