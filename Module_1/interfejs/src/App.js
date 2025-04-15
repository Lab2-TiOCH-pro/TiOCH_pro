import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import HomePage from "./components/HomePage";
import SprawdzPage from "./components/SprawdzPage";
import WynikiPage from "./components/WynikiPage";

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/sprawdz" element={<SprawdzPage />} />
          <Route path="/wyniki" element={<WynikiPage />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
