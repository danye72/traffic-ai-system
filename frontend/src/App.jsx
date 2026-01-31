import React, { useState, useEffect } from 'react';
import axios from 'axios';

const App = () => {
  const [points, setPoints] = useState([]);
  const [rois, setRois] = useState([]);
  const [data, setData] = useState({ stats: {}, order: [] });
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
    const interval = setInterval(fetchData, 1500); // Meno frequente per fluidità
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
    if (points.length < 3) return alert("Disegna zona!");
    const newRois = [...rois, { id: Date.now(), points }];
    setRois(newRois);
    setPoints([]);
    await axios.post('http://localhost:8000/api/roi', { rois: newRois });
  };

  const resetAll = async () => {
    setRois([]); setPoints([]); setData({ stats: {}, order: [] });
    await axios.post('http://localhost:8000/api/roi', { rois: [] });
  };

  return (
    <div style={{ padding: '20px', backgroundColor: '#0f0f0f', color: 'white', fontFamily: 'sans-serif', minHeight: '100vh' }}>
      <h1 style={{ color: '#00e5ff' }}>Traffic Monitor AI - Turbo Mode</h1>
      
      <div style={{ display: 'flex', gap: '30px' }}>
        <div style={{ position: 'relative', width: 'fit-content', border: '1px solid #444' }}>
          <img src="http://localhost:8000/api/video_feed" onClick={handleCanvasClick} style={{ width: W, height: H, display: 'block', cursor: 'crosshair' }} />
          <svg style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none' }} viewBox={`0 0 ${W} ${H}`}>
            {points.map((p, i) => (<circle key={i} cx={p.x * W} cy={p.y * H} r="4" fill="#ffea00" />))}
            {points.length > 1 && (<polyline points={points.map(p => `${p.x * W},${p.y * H}`).join(' ')} fill="none" stroke="#ffea00" strokeWidth="2" strokeDasharray="5" />)}
          </svg>
        </div>

        <div style={{ flexGrow: 1 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', backgroundColor: '#181818' }}>
            <thead>
              <tr style={{ background: '#222', color: '#00e5ff' }}>
                <th style={{ padding: '10px' }}>ZONA</th>
                <th style={{ padding: '10px' }}>MOTO 🏍️</th>
                <th style={{ padding: '10px' }}>AUTO 🚗</th>
                <th style={{ padding: '10px' }}>PESANTI 🚛</th>
              </tr>
            </thead>
            <tbody>
              {data.order.map((id, index) => {
                const val = data.stats[id] || {motorcycle:0, car:0, bus:0, truck:0, occupied:false};
                return (
                  <tr key={id} style={{ borderBottom: '1px solid #333', background: val.occupied ? 'rgba(0, 229, 255, 0.1)' : 'transparent' }}>
                    <td style={{ padding: '10px', textAlign: 'center' }}>Z-{index + 1}</td>
                    <td style={{ padding: '10px', textAlign: 'center', color: '#ffea00', fontWeight: 'bold' }}>{val.motorcycle}</td>
                    <td style={{ padding: '10px', textAlign: 'center' }}>{val.car}</td>
                    <td style={{ padding: '10px', textAlign: 'center' }}>{val.bus + val.truck}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <div style={{ marginTop: '20px', display: 'grid', gap: '10px' }}>
            <button onClick={saveCurrentRoi} style={{ padding: '12px', background: '#00838f', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>SALVA AREA</button>
            <button onClick={resetAll} style={{ padding: '12px', background: '#ad1457', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>CANCELLA TUTTO</button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;
