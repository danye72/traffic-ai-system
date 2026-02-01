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
    if (points.length < 3) return alert("Disegna un'area!");
    if (!roiName) return alert("Inserisci un nome!");
    const newRoi = { id: Date.now(), label: roiName, points: points };
    const updatedRois = [...data.rois, newRoi];
    setPoints([]); setRoiName("");
    await axios.post('http://localhost:8000/api/roi', { rois: updatedRois });
  };

  const resetStatsOnly = async () => {
    if (!window.confirm("Vuoi azzerare i conteggi? Le zone rimarranno salvate.")) return;
    await axios.post('http://localhost:8000/api/stats/reset');
  };

  const deleteZones = async () => {
    if (!window.confirm("Vuoi eliminare tutte le zone?")) return;
    await axios.post('http://localhost:8000/api/roi', { rois: [] });
    await axios.post('http://localhost:8000/api/stats/reset');
  };

  return (
    <div style={{ padding: '20px', backgroundColor: '#0f0f0f', color: 'white', fontFamily: 'Arial', minHeight: '100vh' }}>
      <h2 style={{ color: '#00e5ff' }}>Traffic Monitor con Persistenza</h2>
      <div style={{ display: 'flex', gap: '20px' }}>
        <div>
          <div style={{ position: 'relative', border: '1px solid #444' }}>
            <img src="http://localhost:8000/api/video_feed" onClick={handleCanvasClick} style={{ width: W, height: H, cursor: 'crosshair' }} />
            <svg style={{ position: 'absolute', top: 0, left: 0, width: W, height: H, pointerEvents: 'none' }}>
              {points.map((p, i) => <circle key={i} cx={p.x * W} cy={p.y * H} r="4" fill="yellow" />)}
              {points.length > 1 && <polyline points={points.map(p => `${p.x * W},${p.y * H}`).join(' ')} fill="none" stroke="yellow" strokeWidth="2" />}
            </svg>
          </div>
          <div style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
            <input type="text" placeholder="Nome zona..." value={roiName} onChange={(e) => setRoiName(e.target.value)}
              style={{ flex: 1, padding: '10px', backgroundColor: '#1a1a1a', color: 'white', border: '1px solid #444' }} />
            <button onClick={saveCurrentRoi} style={{ padding: '10px', background: '#00c853', color: 'white', border: 'none', cursor: 'pointer' }}>SALVA ZONA</button>
          </div>
        </div>

        <div style={{ flex: 1 }}>
          <table style={{ width: '100%', backgroundColor: '#181818', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ color: '#00e5ff', textAlign: 'left', borderBottom: '2px solid #333' }}>
                <th style={{ padding: '10px' }}>ZONA</th><th>AUTO</th><th>PESANTI</th><th>TOTALE</th>
              </tr>
            </thead>
            <tbody>
              {data.rois.map((roi) => {
                const s = data.stats[roi.id] || {car:0, motorcycle:0, bus:0, truck:0};
                const total = s.car + s.motorcycle + s.bus + s.truck;
                return (
                  <tr key={roi.id} style={{ borderBottom: '1px solid #2a2a2a', background: s.occupied ? 'rgba(0,229,255,0.1)' : 'transparent' }}>
                    <td style={{ padding: '10px' }}>{roi.label}</td>
                    <td style={{ textAlign: 'center' }}>{s.car}</td>
                    <td style={{ textAlign: 'center' }}>{(s.bus||0)+(s.truck||0)}</td>
                    <td style={{ textAlign: 'center', color: '#00e5ff', fontWeight: 'bold' }}>{total}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '20px' }}>
            <button onClick={resetStatsOnly} style={{ padding: '12px', background: '#ff9100', color: 'black', border: 'none', fontWeight: 'bold', cursor: 'pointer' }}>AZZERA CONTEGGI</button>
            <button onClick={deleteZones} style={{ padding: '12px', background: '#d32f2f', color: 'white', border: 'none', cursor: 'pointer' }}>ELIMINA ZONE E DATI</button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;