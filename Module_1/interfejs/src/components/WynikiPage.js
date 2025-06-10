import React from "react";
import { useNavigate, useLocation } from "react-router-dom";
import "./SprawdzPage.css";

const WynikiPage = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const results = location.state?.results || [];
  const email = location.state?.email || null;

  const wynikAnalizy = JSON.parse(localStorage.getItem("wynikAnalizy")) || [];
    const handleDownload = () => {
      if (!wynikAnalizy || !wynikAnalizy.length) {
        alert("Brak danych do pobrania.");
        return;
      }

      const onlyDetected = wynikAnalizy.map((doc) => ({
        filename: doc.filename || doc.originalFilename,
        detectedItems: doc.analysisResult?.detectedItems || [],
      }));

      const blob = new Blob([JSON.stringify(onlyDetected, null, 2)], {
        type: "application/json",
      });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = "wynik_analizy.json";
      link.click();
    };

  return (
    <div className="sprawdz-container" style={{ position: "relative" }}>
      <div className="logo">
        <img src="/logo447.png" alt="Logo" style={{ height: "100px", width: "auto" }} />
      </div>

      <div className="top-right-text">PRZ INFORMATYKA 2025</div>

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
        <div className="left-column" style={{ flex: 1, marginRight: "20px", textAlign: "left" }}>
          <h2>Wyniki</h2>
          <div
            className="files-box"
            style={{
              border: "1px solid #76FDFE",
              borderRadius: "10px",
              padding: "10px",
              minHeight: "150px",
              maxHeight: "350px",
              overflowY: "auto",
            }}
          >
            {wynikAnalizy ? (
                <ul>
                  {wynikAnalizy.map((dokument, idx) => (
                    <li key={idx} style={{ marginBottom: "20px" }}>
                      <strong>{dokument.filename || dokument.originalFilename}</strong>
                      <ul style={{ marginTop: "5px" }}>
                        {(dokument.analysisResult?.detectedItems || []).map((item, i) => (
                          <li key={i}>
                            <strong>{item.label}</strong>: {item.value}
                          </li>
                        ))}
                      </ul>
                    </li>
                  ))}
                </ul>
            ) : results.length > 0 ? (
              <ul>
                {results.map((res, idx) => (
                  <li key={idx}>
                    <strong>{res.filename}</strong>:{" "}
                    {res.status === "uploaded" ? (
                      <span style={{ color: "green" }}>✅ przesłano (ID: {res.documentId})</span>
                    ) : (
                      <span style={{ color: "red" }}>❌ błąd – {res.error}</span>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <p>Brak danych do wyświetlenia.</p>
            )}
          </div>
        </div>

        <div className="right-column" style={{ flex: 1, textAlign: "left" }}>
          <h2>Pobierz wyniki</h2>
          <button
            className="custom-button"
            onClick={handleDownload}
            style={{ marginBottom: "15px", display: "flex", alignItems: "center", gap: "10px" }}
          >
            <img src="/pobierz.png" alt="Pobierz" style={{ height: "30px" }} />
            Pobierz jako JSON
          </button>

          {email && (
            <p style={{ fontSize: "0.95rem", color: "#76FDFE" }}>
              Wyniki dotrą na adres e-mail: <strong>{email}</strong>
            </p>
          )}
        </div>
      </div>

      <div style={{ position: "absolute", bottom: "80px", right: "20px" }}>
        <button className="custom-button" onClick={() => navigate("/sprawdz")}>
          Powrót
        </button>
      </div>

      <div className="footer">
        Obsługiwane formaty: PDF, DOCX, XLSX, CSV, HTML, TXT, JSON i XML. Maksymalny rozmiar przesyłanego pliku: 10 MB
      </div>
    </div>
  );
};

export default WynikiPage;
