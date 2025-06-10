import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "./EkranLadowania.css";

function EkranLadowania({ idPliku }) {
  const navigate = useNavigate();

  useEffect(() => {
    const interval = setInterval(() => {
      fetch("http://localhost:8002/api/documents/")
        .then((res) => res.json())
        .then((dane) => {
          const lista = dane.documents;
          const dokument = lista.find((d) => d._id === idPliku);

          if (dokument?.analysisResult) {
            clearInterval(interval);
            localStorage.setItem("wynikAnalizy", JSON.stringify(dokument.analysisResult));
            navigate("/wyniki");
          }
        })
        .catch((err) => {
          console.error("Błąd podczas pollingu:", err);
        });
    }, 500);

    return () => clearInterval(interval);
  }, [idPliku, navigate]);

  return (
    <div className="loader-container">
      <img src="/logo447.png" alt="Logo" className="logo" />
      <div className="loader" />
      <h2>Analizujemy Twój dokument...</h2>
      <p>To może potrwać kilka sekund. Prosimy o cierpliwość.</p>
    </div>
  );
}

export default EkranLadowania;
