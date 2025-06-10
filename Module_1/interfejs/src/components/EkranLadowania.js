import React, { useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import "./EkranLadowania.css";



function EkranLadowania() {
  const navigate = useNavigate();
  const location = useLocation();
  const ids = location.state?.ids || [];

  useEffect(() => {
    const interval = setInterval(() => {
      fetch("http://localhost:8002/api/documents/")
        .then((res) => res.json())
        .then((dane) => {
          const lista = dane.documents || [];
          const wyniki = ids
            .map((id) => lista.find((d) => d._id === id))
            .filter((d) => d && d.analysisResult);

          if (wyniki.length === ids.length) {
            clearInterval(interval);
            localStorage.setItem("wynikAnalizy", JSON.stringify(wyniki));
            navigate("/wyniki");
          }
        })
        .catch((err) => {
          console.error("Błąd podczas pollingu:", err);
        });
    }, 500);
    if (!ids.length) {
      return <p style={{ color: "white" }}>Brak dokumentów do sprawdzenia.</p>;
    }
    return () => clearInterval(interval);
  }, [ids, navigate]);

  return (
    <div className="loader-container">
      <img src="/logo447.png" alt="Logo" className="logo" />
      <div className="loader" />
      <h2>Analizujemy Twoje dokumenty...</h2>
      <p>To może potrwać kilka sekund. Prosimy o cierpliwość.</p>
    </div>
  );
}

export default EkranLadowania;