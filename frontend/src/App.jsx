import React, { useState, useRef } from 'react';
import { 
  FileText, 
  UploadCloud, 
  Languages, 
  Sparkles, 
  Copy, 
  Check, 
  Download, 
  Archive, 
  Eye, 
  Code, 
  FileCheck, 
  RefreshCw,
  FolderArchive,
  Workflow,
  ExternalLink,
  FileType
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const API_BASE = "http://127.0.0.1:8000/api";

export default function App() {
  const [file, setFile] = useState(null);
  const [sourceLang, setSourceLang] = useState('auto');
  const [targetLang, setTargetLang] = useState('es');
  
  const [isTranslating, setIsTranslating] = useState(false);
  const [progressText, setProgressText] = useState('');
  const [translatedResult, setTranslatedResult] = useState(null);

  const [isConvertingObsidian, setIsConvertingObsidian] = useState(false);
  const [obsidianResult, setObsidianResult] = useState(null);
  const [copiedObsidian, setCopiedObsidian] = useState(false);
  const [copiedText, setCopiedText] = useState(false);

  const [leftViewMode, setLeftViewMode] = useState('pdf'); // 'pdf' | 'text'
  const [activeTab, setActiveTab] = useState('obsidian_preview'); // 'obsidian_preview' | 'obsidian_source'
  const fileInputRef = useRef(null);

  const handleFileDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.type === 'application/pdf' || droppedFile.name.endsWith('.pdf')) {
        setFile(droppedFile);
        resetState();
      } else {
        alert("Por favor sube un archivo PDF válido.");
      }
    }
  };

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      resetState();
    }
  };

  const resetState = () => {
    setTranslatedResult(null);
    setObsidianResult(null);
    setLeftViewMode('pdf');
  };

  const handleStartTranslation = async () => {
    if (!file) return;

    setIsTranslating(true);
    setProgressText('Subiendo PDF y conservando diseño original...');
    setTranslatedResult(null);
    setObsidianResult(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('source_lang', sourceLang);
    formData.append('target_lang', targetLang);

    try {
      setProgressText('Traduciendo texto de forma gratuita manteniendo imágenes y formato...');
      const response = await fetch(`${API_BASE}/translate-pdf`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Error al traducir el PDF.');
      }

      const data = await response.json();
      setTranslatedResult(data);
      setLeftViewMode('pdf');
    } catch (err) {
      alert(`Error: ${err.message}`);
    } finally {
      setIsTranslating(false);
      setProgressText('');
    }
  };

  const handleConvertObsidian = async () => {
    if (!translatedResult || !translatedResult.session_id) return;

    setIsConvertingObsidian(true);

    const formData = new FormData();
    formData.append('session_id', translatedResult.session_id);
    formData.append('use_wiki_links', 'true');

    try {
      const response = await fetch(`${API_BASE}/export-obsidian`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error('Error al convertir a formato Obsidian.');
      }

      const data = await response.json();
      setObsidianResult(data);
      setActiveTab('obsidian_preview');
    } catch (err) {
      alert(`Error al generar para Obsidian: ${err.message}`);
    } finally {
      setIsConvertingObsidian(false);
    }
  };

  const copyToClipboard = (text, setCopyState) => {
    navigator.clipboard.writeText(text);
    setCopyState(true);
    setTimeout(() => setCopyState(false), 2000);
  };

  const downloadTextFile = (content, filename) => {
    const element = document.createElement("a");
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    element.href = URL.createObjectURL(blob);
    element.download = filename;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  const downloadTranslatedPdf = () => {
    if (!translatedResult || !translatedResult.session_id) return;
    window.location.href = `${API_BASE}/download-pdf?session_id=${translatedResult.session_id}`;
  };

  const downloadObsidianZip = () => {
    if (!translatedResult || !translatedResult.session_id) return;
    window.location.href = `${API_BASE}/download-obsidian-zip?session_id=${translatedResult.session_id}`;
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="header">
        <div className="logo-group">
          <div className="logo-icon">
            <Workflow size={24} color="#ffffff" />
          </div>
          <div className="logo-text">
            <h1>Work flow</h1>
            <p>Traductor de PDF (formato idéntico) & Conversor Opcional a Obsidian (EN ↔ ES)</p>
          </div>
        </div>
        <div className="badge-free">
          <Sparkles size={14} /> 100% Gratuito e Ilimitado
        </div>
      </header>

      {/* Upload Card */}
      <section className="card">
        <div 
          className="dropzone"
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleFileDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleFileSelect} 
            accept=".pdf" 
            style={{ display: 'none' }} 
          />
          <div className="dropzone-icon">
            <UploadCloud size={32} />
          </div>
          {file ? (
            <div>
              <p style={{ fontWeight: 600, fontSize: '1.1rem', color: '#f3f4f6' }}>{file.name}</p>
              <p style={{ fontSize: '0.85rem', color: '#9ca3af', marginTop: '0.2rem' }}>
                {(file.size / (1024 * 1024)).toFixed(2)} MB — Clic para cambiar archivo
              </p>
            </div>
          ) : (
            <div>
              <p style={{ fontWeight: 600, fontSize: '1.1rem' }}>Arrastra tu archivo PDF aquí o haz clic para buscar</p>
              <p style={{ fontSize: '0.85rem', color: '#9ca3af', marginTop: '0.25rem' }}>
                Soporta PDFs en Inglés o Español (imágenes, gráficos y diseño idéntico al original)
              </p>
            </div>
          )}
        </div>

        {/* Controls Bar */}
        <div className="controls-bar">
          <div className="lang-select-group">
            <Languages size={18} color="#9ca3af" />
            <select 
              className="select-input"
              value={sourceLang} 
              onChange={(e) => setSourceLang(e.target.value)}
            >
              <option value="auto">Detectar Idioma Origen</option>
              <option value="en">Inglés</option>
              <option value="es">Español</option>
            </select>

            <span style={{ color: '#6b7280', fontWeight: 600 }}>➔</span>

            <select 
              className="select-input"
              value={targetLang} 
              onChange={(e) => setTargetLang(e.target.value)}
            >
              <option value="es">Traducir a Español</option>
              <option value="en">Traducir a Inglés</option>
            </select>
          </div>

          <button 
            className="btn-primary" 
            onClick={handleStartTranslation}
            disabled={!file || isTranslating}
          >
            {isTranslating ? (
              <>
                <RefreshCw size={18} className="spin" /> Traduciendo PDF...
              </>
            ) : (
              <>
                <Languages size={18} /> Traducir PDF (Mismo Formato)
              </>
            )}
          </button>
        </div>

        {isTranslating && (
          <div className="progress-container">
            <p style={{ fontSize: '0.85rem', color: '#a78bfa' }}>{progressText}</p>
            <div className="progress-bar-bg">
              <div className="progress-bar-fill" style={{ width: '80%' }}></div>
            </div>
          </div>
        )}
      </section>

      {/* Main Workspace */}
      {translatedResult && (
        <section className="workspace-grid">
          {/* Left Panel: Embedded PDF Viewer */}
          <div className="card">
            <div className="panel-header">
              <div className="panel-title">
                <FileCheck size={20} color="#10b981" />
                <span>PDF Traducido (Mismo Formato)</span>
              </div>

              <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                <button 
                  className="btn-primary"
                  onClick={downloadTranslatedPdf}
                  style={{ padding: '0.4rem 0.85rem', fontSize: '0.82rem' }}
                >
                  <Download size={14} /> Descargar PDF
                </button>
                <a 
                  className="btn-secondary"
                  href={`${API_BASE}/view-pdf?session_id=${translatedResult.session_id}`}
                  target="_blank"
                  rel="noreferrer"
                  style={{ textDecoration: 'none', padding: '0.4rem 0.75rem', fontSize: '0.82rem' }}
                >
                  <ExternalLink size={14} /> Abrir Pestaña
                </a>
                <button 
                  className={`btn-secondary ${leftViewMode === 'text' ? 'active' : ''}`}
                  onClick={() => setLeftViewMode(leftViewMode === 'pdf' ? 'text' : 'pdf')}
                  style={{ padding: '0.4rem 0.75rem', fontSize: '0.82rem' }}
                >
                  {leftViewMode === 'pdf' ? <FileType size={14} /> : <Eye size={14} />}
                  {leftViewMode === 'pdf' ? 'Texto' : 'PDF'}
                </button>
              </div>
            </div>

            <div className="content-viewer" style={{ padding: leftViewMode === 'pdf' ? '0' : '1.25rem', overflow: 'hidden' }}>
              {leftViewMode === 'pdf' ? (
                <iframe 
                  src={`${API_BASE}/view-pdf?session_id=${translatedResult.session_id}`} 
                  title="PDF Traducido"
                  width="100%" 
                  height="100%" 
                  style={{ border: 'none', borderRadius: '12px' }}
                />
              ) : (
                <div style={{ whiteSpace: 'pre-wrap', height: '100%', overflowY: 'auto' }}>
                  {translatedResult.translated_text}
                </div>
              )}
            </div>
          </div>

          {/* Right Panel: Optional Obsidian Conversion */}
          <div className="card" style={{ borderColor: obsidianResult ? 'rgba(124, 58, 237, 0.4)' : 'var(--border-color)' }}>
            <div className="panel-header">
              <div className="panel-title">
                <Sparkles size={20} color="#a78bfa" />
                <span>Formato Obsidian (Opcional)</span>
              </div>

              {obsidianResult && (
                <div style={{ display: 'flex', gap: '0.4rem' }}>
                  <button 
                    className={`btn-secondary ${activeTab === 'obsidian_preview' ? 'active' : ''}`}
                    onClick={() => setActiveTab('obsidian_preview')}
                    style={{ padding: '0.4rem 0.75rem', fontSize: '0.8rem' }}
                  >
                    <Eye size={14} /> Vista Previa
                  </button>
                  <button 
                    className={`btn-secondary ${activeTab === 'obsidian_source' ? 'active' : ''}`}
                    onClick={() => setActiveTab('obsidian_source')}
                    style={{ padding: '0.4rem 0.75rem', fontSize: '0.8rem' }}
                  >
                    <Code size={14} /> Markdown
                  </button>
                </div>
              )}
            </div>

            {!obsidianResult ? (
              <div style={{ 
                height: '520px', 
                display: 'flex', 
                flexDirection: 'column', 
                alignItems: 'center', 
                justifyContent: 'center',
                textAlign: 'center',
                padding: '2rem',
                border: '2px dashed rgba(124, 58, 237, 0.2)',
                borderRadius: '12px',
                background: 'rgba(124, 58, 237, 0.03)'
              }}>
                <div style={{ 
                  width: '56px', 
                  height: '56px', 
                  borderRadius: '50%', 
                  background: 'rgba(124, 58, 237, 0.15)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#a78bfa',
                  marginBottom: '1rem'
                }}>
                  <Archive size={28} />
                </div>
                <h3 style={{ fontSize: '1.2rem', marginBottom: '0.5rem', color: '#f3f4f6' }}>
                  ¿Deseas guardar esto en Obsidian?
                </h3>
                <p style={{ fontSize: '0.9rem', color: '#9ca3af', maxWidth: '380px', marginBottom: '1.5rem' }}>
                  Extrae las imágenes y genera la nota `.md` formateada para Obsidian.
                </p>
                <button 
                  className="btn-obsidian"
                  onClick={handleConvertObsidian}
                  disabled={isConvertingObsidian}
                >
                  {isConvertingObsidian ? (
                    <>
                      <RefreshCw size={18} className="spin" /> Extrayendo imágenes y formateando...
                    </>
                  ) : (
                    <>
                      <Sparkles size={18} /> Convertir a Formato Obsidian
                    </>
                  )}
                </button>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {/* Export toolbar */}
                <div style={{ 
                  display: 'flex', 
                  flexWrap: 'wrap', 
                  gap: '0.6rem', 
                  background: 'rgba(124, 58, 237, 0.1)', 
                  padding: '0.85rem', 
                  borderRadius: '12px',
                  border: '1px solid rgba(167, 139, 250, 0.2)'
                }}>
                  <button 
                    className={`btn-obsidian ${copiedObsidian ? 'btn-success' : ''}`}
                    onClick={() => copyToClipboard(obsidianResult.markdown_content, setCopiedObsidian)}
                  >
                    {copiedObsidian ? <Check size={16} /> : <Copy size={16} />}
                    {copiedObsidian ? '¡Markdown Copiado!' : '📋 Copiar a Obsidian (1-Clic)'}
                  </button>

                  <button 
                    className="btn-secondary"
                    onClick={() => downloadTextFile(obsidianResult.markdown_content, `${obsidianResult.title}.md`)}
                  >
                    <Download size={16} /> Descargar .md
                  </button>

                  <button 
                    className="btn-secondary"
                    onClick={downloadObsidianZip}
                  >
                    <FolderArchive size={16} color="#a78bfa" /> Paquete .ZIP ({obsidianResult.images_count} imágenes)
                  </button>
                </div>

                <div className="content-viewer">
                  {activeTab === 'obsidian_preview' ? (
                    <div className="obsidian-preview">
                      <div className="frontmatter-box">
                        <p>---</p>
                        <p>title: "{obsidianResult.title}"</p>
                        <p>tags: [pdf-import, translation, obsidian-note]</p>
                        <p>---</p>
                      </div>
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {obsidianResult.markdown_content}
                      </ReactMarkdown>
                    </div>
                  ) : (
                    <pre className="markdown-source">
                      {obsidianResult.markdown_content}
                    </pre>
                  )}
                </div>
              </div>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
