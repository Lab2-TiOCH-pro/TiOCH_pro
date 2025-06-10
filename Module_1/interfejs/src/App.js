import React from "react";
import { BrowserRouter as Router, Routes, Route, useParams } from "react-router-dom";
import HomePage from "./components/HomePage";
import SprawdzPage from "./components/SprawdzPage";
import WynikiPage from "./components/WynikiPage";
import EkranLadowania from "./components/EkranLadowania";

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/sprawdz" element={<SprawdzPage />} />
          <Route path="/wyniki" element={<WynikiPage />} />
          <Route path="/ladowanie" element={<EkranLadowania />} /> {/* nowa trasa */}
        </Routes>
      </div>
    </Router>
  );
}

function LadowanieWrapper() {
  const { id } = useParams();
  return <EkranLadowania idPliku={id} />;
}

export default App;
