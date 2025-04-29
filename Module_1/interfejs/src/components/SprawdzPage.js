import React, { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useDropzone } from "react-dropzone";
import "./SprawdzPage.css";

const SprawdzPage = () => {
  const navigate = useNavigate();
  const [files, setFiles] = useState([]);

  const onDrop = useCallback((acceptedFiles) => {
    setFiles((prev) => [...prev, ...acceptedFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: true,
  });

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
          <div
            {...getRootProps({
              className: `file-upload-button${isDragActive ? " drag-active" : ""}`,
            })}
          >
            <input {...getInputProps()} />
            {isDragActive
              ? "Upuść tutaj pliki..."
              : "Przeciągnij lub kliknij, aby wybrać pliki"}
          </div>
        </div>

        <div className="right-column">
          <h2>Twoje pliki</h2>
          <div className="files-box">
            {files.length === 0 ? (
              <p>Tu będzie lista plików...</p>
            ) : (
              <p>{files.map((file, index) => (
                <React.Fragment key={index}>
                  • {file.name}
                  {index < files.length - 1 && ','}
                  <br />
                </React.Fragment>
              ))}</p>
            )}
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
