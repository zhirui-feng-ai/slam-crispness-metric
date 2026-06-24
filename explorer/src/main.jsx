import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

// NOTE: no React.StrictMode — its dev double-mount tears down and recreates the
// WebGL context/canvas in RoadScene, which can leave the 3D viewer blank.
ReactDOM.createRoot(document.getElementById('root')).render(<App />)
