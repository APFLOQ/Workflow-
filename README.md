# ⚡ Work flow — Traductor de PDF (Mismo Formato) & Conversor a Obsidian

**Work flow** es una aplicación web moderna y gratuita diseñada para traducir documentos PDF entre **Inglés y Español** manteniendo el diseño original, formato, tablas e imágenes idénticas al archivo original. Además, ofrece la opción de exportar el contenido a formato **Obsidian (.md / .zip)** a petición del usuario.

---

## ✨ Características Principales

- **Traducción Gratuita e Ilimitada**: Sin claves de API ni restricciones de pago.
- **Conservación de Diseño de PDF**: Reemplaza el texto en su posición exacta respetando columnas, tablas, márgenes e imágenes.
- **Visor PDF Integrado**: Visualiza el PDF traducido directamente dentro de la aplicación o descárgalo en 1 clic.
- **Exportación para Obsidian**:
  - 📋 **Copiar a Obsidian (1-Clic)** con metadatos Frontmatter YAML.
  - 📄 **Descargar nota `.md` suelta**.
  - 📦 **Descargar paquete `.zip`** con carpeta `attachments/` de imágenes.
- **Protección de Código e Imágenes**: Mantiene intactos bloques de código de programación (Python/SciPy/NumPy) y gráficos oscuros.

---

## 🛠️ Requisitos e Instalación

### Backend (Python FastAPI)
```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev
```

Accede a la aplicación en `http://localhost:5173`.
