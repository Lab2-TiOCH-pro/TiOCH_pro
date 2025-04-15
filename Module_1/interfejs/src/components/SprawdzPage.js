import React from "react";
import { useNavigate } from "react-router-dom";
import "./SprawdzPage.css";

const SprawdzPage = () => {
  const navigate = useNavigate();

  const handleCheck = () => {
    navigate("/wyniki");
  };

  return (
    <div className="sprawdz-container">
      <div className="logo">
        <img src="/logo447.png" alt="Logo" style={{ height: '100px', width: 'auto' }} />
      </div>

      <div className="top-right-text">PRZ INFORMATYKA 2025</div>

      <div className="sprawdz-content">
        <div className="left-column">
          <h2>Wybierz pliki</h2>
          <label className="file-upload-button">
            Wybierz plik
            <input type="file" multiple className="file-input" />
          </label>
        </div>

        <div className="right-column">
          <h2>Twoje pliki</h2>
          <div className="files-box">
            <p>Tu będzie lista plików...</p>
          </div>
          <button className="custom-button sprawdz-button" onClick={handleCheck}>
            SPRAWDŹ
          </button>
        </div>
      </div>

      <div className="footer">Obsługiwane formaty: pdf, word, odt</div>
    </div>
  );
};

export default SprawdzPage;
