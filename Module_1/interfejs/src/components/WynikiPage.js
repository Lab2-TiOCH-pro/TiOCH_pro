import React from "react";
import { useNavigate, useLocation } from "react-router-dom";
import "./SprawdzPage.css";

const WynikiPage = () => {
  const navigate = useNavigate();
  const location = useLocation();

  // Pobranie e-maila przekazanego ze SprawdzPage
  const email = location.state?.email || null;

  const handleDownload = () => {
    alert("Pobieranie wyników...");
  };

  return (
    <div className="sprawdz-container" style={{ position: "relative" }}>
      {/* Logo */}
      <div className="logo">
        <img src="/logo447.png" alt="Logo" style={{ height: "100px", width: "auto" }} />
      </div>

      {/* PRZ INFORMATYKA */}
      <div className="top-right-text">PRZ INFORMATYKA 2025</div>

      {/* Zawartość */}
      <div
        className="sprawdz-content"
        style={{
          display: "flex",
          justifyContent: "space-between",
          width: "100%",
          maxWidth: "1000px",
          marginTop: "150px",
        }}
      >
        {/* Lewa kolumna */}
        <div className="left-column" style={{ flex: 1, marginRight: "20px", textAlign: "left" }}>
          <h2>Wyniki</h2>
          <div
            className="files-box"
            style={{
              border: "1px solid #76FDFE",
              borderRadius: "10px",
              padding: "10px",
              minHeight: "150px",
            }}
          >
            <p>Tu będzie lista wyników...</p>
          </div>
        </div>

        {/* Prawa kolumna */}
        <div className="right-column" style={{ flex: 1, textAlign: "left" }}>
          <h2>Pobierz wyniki</h2>

          <button
            className="custom-button"
            onClick={handleDownload}
            style={{ marginBottom: "15px", display: "flex", alignItems: "center", gap: "10px" }}
          >
            <img src="/pobierz.png" alt="Pobierz" style={{ height: "30px" }} />
          </button>

          {email && (
            <p style={{ fontSize: "0.95rem", color: "#76FDFE" }}>
              Wyniki dotrą na adres e-mail: <strong>{email}</strong>
            </p>
          )}
        </div>
      </div>

      {/* Przycisk Powrót */}
      <div style={{ position: "absolute", bottom: "80px", right: "20px" }}>
        <button className="custom-button" onClick={() => navigate("/sprawdz")}>
          Powrót
        </button>
      </div>

      {/* Stopka */}
      <div className="footer">Obsługiwane formaty: pdf, word, odt</div>
    </div>
  );
};

export default WynikiPage;
