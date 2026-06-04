import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import "leaflet/dist/leaflet.css";
import "./styles.css";

import App from "./App";
import DataPage from "./routes/DataPage";
import GraphsPage from "./routes/GraphsPage";
import IntroPage from "./routes/IntroPage";
import MapPage from "./routes/MapPage";
import PredictionsPage from "./routes/PredictionsPage";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />}>
          <Route index element={<IntroPage />} />
          <Route path="graphs" element={<GraphsPage />} />
          <Route path="predictions" element={<PredictionsPage />} />
          <Route path="map" element={<MapPage />} />
          <Route path="data" element={<DataPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
);
