import os
import uuid
import shutil
import logging
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse, StreamingResponse, FileResponse
import json

from pdf_processor import PDFProcessor
from translator_engine import TranslationEngine
from obsidian_builder import ObsidianBuilder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

app = FastAPI(title="Work flow — PDF Translator & Obsidian Exporter API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp_sessions")
os.makedirs(TEMP_DIR, exist_ok=True)

pdf_processor = PDFProcessor()
translator_engine = TranslationEngine()
obsidian_builder = ObsidianBuilder()

@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": "Work flow API"}

@app.post("/api/translate-pdf")
async def translate_pdf(
    file: UploadFile = File(...),
    source_lang: str = Form("auto"),
    target_lang: str = Form("es")
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="El archivo subido debe ser un PDF válido.")

    session_id = str(uuid.uuid4())
    session_folder = os.path.join(TEMP_DIR, session_id)
    os.makedirs(session_folder, exist_ok=True)

    pdf_bytes = await file.read()
    pdf_path = os.path.join(session_folder, "original.pdf")
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)

    try:
        # Step 1: Create layout-preserving translated PDF
        translated_pdf_bytes = pdf_processor.create_translated_pdf(
            pdf_bytes, 
            translator_engine, 
            source_lang=source_lang, 
            target_lang=target_lang
        )
        
        translated_pdf_path = os.path.join(session_folder, "translated.pdf")
        with open(translated_pdf_path, "wb") as f:
            f.write(translated_pdf_bytes)

        # Step 2: Also extract structure & translated text for session storage (used for optional Obsidian export)
        structure = pdf_processor.extract_structure(pdf_bytes)
        translated_pages = []
        full_translated_text_lines = []

        for page in structure["pages"]:
            translated_blocks = translator_engine.translate_blocks(
                page["blocks"], 
                source_lang=source_lang, 
                target_lang=target_lang
            )
            translated_pages.append({
                "page_number": page["page_number"],
                "blocks": translated_blocks,
                "tables": page["tables"]
            })

            for b in translated_blocks:
                content = b.get("translated_content", b.get("content", ""))
                if content.strip():
                    full_translated_text_lines.append(content)

        clean_doc_title = structure["title"] or file.filename.rsplit('.', 1)[0]
        translated_doc = {
            "title": clean_doc_title,
            "total_pages": structure["total_pages"],
            "pages": translated_pages
        }

        session_json_path = os.path.join(session_folder, "translated.json")
        with open(session_json_path, "w", encoding="utf-8") as f:
            json.dump(translated_doc, f, ensure_ascii=False, indent=2)

        return {
            "session_id": session_id,
            "title": clean_doc_title,
            "total_pages": structure["total_pages"],
            "translated_text": "\n\n".join(full_translated_text_lines),
            "translated_pdf_url": f"/api/view-pdf?session_id={session_id}"
        }

    except Exception as e:
        logger.error(f"Error during translation process: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al traducir el PDF: {str(e)}")


@app.get("/api/view-pdf")
async def view_pdf(session_id: str):
    session_folder = os.path.join(TEMP_DIR, session_id)
    translated_pdf_path = os.path.join(session_folder, "translated.pdf")

    if not os.path.exists(translated_pdf_path):
        raise HTTPException(status_code=404, detail="PDF traducido no encontrado.")

    return FileResponse(
        path=translated_pdf_path,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=translated.pdf"}
    )


@app.get("/api/download-pdf")
async def download_pdf(session_id: str):
    session_folder = os.path.join(TEMP_DIR, session_id)
    translated_pdf_path = os.path.join(session_folder, "translated.pdf")
    session_json_path = os.path.join(session_folder, "translated.json")

    if not os.path.exists(translated_pdf_path):
        raise HTTPException(status_code=404, detail="PDF traducido no encontrado.")

    title = "Documento_Traducido"
    if os.path.exists(session_json_path):
        with open(session_json_path, "r", encoding="utf-8") as f:
            doc_data = json.load(f)
            title = doc_data.get("title", title)

    clean_filename = f"{title}_Traducido.pdf"

    return FileResponse(
        path=translated_pdf_path,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={clean_filename}"}
    )


@app.post("/api/export-obsidian")
async def export_obsidian(
    session_id: str = Form(...),
    use_wiki_links: bool = Form(True)
):
    session_folder = os.path.join(TEMP_DIR, session_id)
    pdf_path = os.path.join(session_folder, "original.pdf")
    session_json_path = os.path.join(session_folder, "translated.json")

    if not os.path.exists(pdf_path) or not os.path.exists(session_json_path):
        raise HTTPException(status_code=404, detail="Sesión no encontrada.")

    with open(session_json_path, "r", encoding="utf-8") as f:
        translated_doc = json.load(f)

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    images_dir = os.path.join(session_folder, "attachments")
    extracted_images = pdf_processor.extract_images(pdf_bytes, images_dir)

    markdown_text = obsidian_builder.build_markdown(
        translated_doc, 
        extracted_images, 
        use_wiki_links=use_wiki_links
    )

    md_file_path = os.path.join(session_folder, "note.md")
    with open(md_file_path, "w", encoding="utf-8") as f:
        f.write(markdown_text)

    return {
        "markdown_content": markdown_text,
        "title": translated_doc["title"],
        "images_count": len(extracted_images),
        "images": extracted_images
    }


@app.get("/api/download-obsidian-zip")
async def download_obsidian_zip(session_id: str):
    session_folder = os.path.join(TEMP_DIR, session_id)
    md_file_path = os.path.join(session_folder, "note.md")
    session_json_path = os.path.join(session_folder, "translated.json")
    images_dir = os.path.join(session_folder, "attachments")

    if not os.path.exists(session_json_path):
        raise HTTPException(status_code=404, detail="Sesión no encontrada.")

    with open(session_json_path, "r", encoding="utf-8") as f:
        translated_doc = json.load(f)

    markdown_text = ""
    if os.path.exists(md_file_path):
        with open(md_file_path, "r", encoding="utf-8") as f:
            markdown_text = f.read()
    else:
        pdf_path = os.path.join(session_folder, "original.pdf")
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        extracted_images = pdf_processor.extract_images(pdf_bytes, images_dir)
        markdown_text = obsidian_builder.build_markdown(translated_doc, extracted_images, True)

    zip_bytes = obsidian_builder.build_zip_package(markdown_text, translated_doc["title"], images_dir)
    filename = f"{translated_doc['title']}_Obsidian.zip"

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
