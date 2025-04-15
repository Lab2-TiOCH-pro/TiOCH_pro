import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./SprawdzPage.css";

const WynikiPage = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [isValidEmail, setIsValidEmail] = useState(true);

  const handleEmailChange = (e) => {
    const value = e.target.value;
    setEmail(value);
    setIsValidEmail(/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value));
  };

  const handleSend = () => {
    if (!isValidEmail || !email) {
      alert("Podaj poprawny adres e-mail.");
      return;
    }
    alert("Wyniki zostały wysłane na e-mail.");
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
            style={{ marginBottom: "15px", display: "flex", alignItems: "center", gap: "10px" }}
          >
            <img src="/pobierz.png" alt="Pobierz" style={{ height: "30px" }} />
          </button>

          <p style={{ marginBottom: "10px", fontSize: "0.9rem", color: "#76FDFE" }}>
            lub wyślij je na e-maila
          </p>

          <div style={{ display: "flex", alignItems: "center" }}>
            <input
              type="email"
              placeholder="Podaj swój adres e-mail"
              value={email}
              onChange={handleEmailChange}
              className="email-input"
              style={{
                flex: 1,
                padding: "10px",
                borderRadius: "999px",
                border: `2px solid ${isValidEmail || !email ? "#76FDFE" : "red"}`,
                marginRight: "10px",
                backgroundColor: "#d8f9ff",
                color: "#0F2C3D",
              }}
            />
            <button className="custom-button" onClick={handleSend}>
              <img src="/wyslij.png" alt="Wyślij" style={{ height: "25px" }} />
            </button>
          </div>
        </div>
      </div>

      {/* Przycisk Powrót – lekko wyżej, poza stopką */}
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
