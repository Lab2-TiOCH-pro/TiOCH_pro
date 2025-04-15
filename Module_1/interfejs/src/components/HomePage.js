import React from "react";
import { Link } from "react-router-dom";
import "./HomePage.css";

const HomePage = () => {
  return (
    <div className="homepage-container">
      {/* Logo */}
      <div className="logo">
        <img src="/logo447.png" alt="Logo" style={{ height: '100px', width: 'auto' }} />
      </div>

      {/* PRZ Informatyka 2025 */}
      <div className="top-right-text">PRZ INFORMATYKA 2025</div>

      {/* Główna zawartość */}
      <div className="content">
        <h1 className="title">SPRAWDŹ DOKUMENT</h1>
        <div className="button-container">
          <Link to="/sprawdz" className="custom-button">
            <span className="button-text">Przejdź</span>
          </Link>
        </div>
      </div>

      {/* Stopka */}
      <div className="footer">Obsługiwane formaty: pdf, word, odt</div>
    </div>
  );
};

export default HomePage;
