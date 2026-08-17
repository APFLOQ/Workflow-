import fitz  # PyMuPDF
import os
import io
from PIL import Image
import pdfplumber
import logging

logger = logging.getLogger("pdf_processor")
logger.setLevel(logging.INFO)

class PDFProcessor:
    def __init__(self):
        pass

    def _is_pure_code_block(self, block_text: str) -> bool:
        """
        Only flags true programming code blocks (e.g. import numpy, def delta).
        Normal PDF body text must always be translated & redacted.
        """
        code_keywords = [
            "import numpy", "from scipy", "def delta(", "norm.cdf",
            "np.log", "0.250448229", "# signed put delta"
        ]
        text_lower = block_text.lower()
        for kw in code_keywords:
            if kw.lower() in text_lower:
                return True
        return False

    def create_translated_pdf(self, pdf_bytes: bytes, translator_engine, source_lang: str = "auto", target_lang: str = "es") -> bytes:
        """
        Creates a new PDF byte stream where English body text is 100% erased and replaced
        by Spanish translation in-place, preserving images and preventing double-layer text overlaps.
        """
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        all_blocks_to_translate = []
        page_targets_map = []

        for page_idx in range(len(doc)):
            page = doc[page_idx]
            page_rect = page.rect
            text_dict = page.get_text("dict")
            blocks = text_dict.get("blocks", [])

            page_targets = []

            for b in blocks:
                # Type 0 is text block
                if b.get("type") == 0:
                    orig_bbox = fitz.Rect(b["bbox"])

                    block_text = ""
                    max_font_size = 9.5
                    is_bold = False

                    lines = b.get("lines", [])
                    for line in lines:
                        line_text = ""
                        for span in line.get("spans", []):
                            s_text = span.get("text", "")
                            s_size = span.get("size", 9.5)
                            font_flags = span.get("flags", 0)

                            if s_size > max_font_size:
                                max_font_size = s_size
                            if font_flags & 2 or "bold" in span.get("font", "").lower():
                                is_bold = True

                            line_text += s_text
                        if line_text.strip():
                            block_text += line_text.strip() + " "

                    clean_text = block_text.strip()
                    if not clean_text or len(clean_text) < 1:
                        continue

                    # SKIP ONLY PURE PROGRAMMING CODE SNIPPETS
                    if self._is_pure_code_block(clean_text):
                        continue

                    batch_idx = len(all_blocks_to_translate)
                    all_blocks_to_translate.append(clean_text)

                    block_width = orig_bbox.width
                    is_full_width = block_width > (page_rect.width * 0.6)
                    
                    if is_full_width:
                        target_x1 = min(page_rect.width - 25, orig_bbox.x1 + 10)
                    else:
                        target_x1 = min(orig_bbox.x1 + 5, page_rect.width - 20)

                    page_targets.append({
                        "batch_idx": batch_idx,
                        "redact_rect": orig_bbox,
                        "orig_bbox": orig_bbox,
                        "target_x1": target_x1,
                        "font_size": max_font_size,
                        "is_bold": is_bold,
                        "color": (0.05, 0.05, 0.05)
                    })

            # Sort page targets top to bottom
            page_targets.sort(key=lambda t: (t["orig_bbox"].x0 > page_rect.width * 0.45, t["orig_bbox"].y0))
            page_targets_map.append(page_targets)

        # Step 2: High-speed batch translation
        translated_texts = translator_engine.translate_batch(
            all_blocks_to_translate, 
            source_lang=source_lang, 
            target_lang=target_lang
        )

        # Step 3: Redact ALL English body text first (erases original English text 100%)
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            page_rect = page.rect
            page_targets = page_targets_map[page_idx]

            # 100% erase English text boxes
            for item in page_targets:
                page.add_redact_annot(item["redact_rect"], fill=(1, 1, 1))

            page.apply_redactions()

            # Re-insert Spanish translation with vertical flow tracker
            left_col_y1 = 0
            right_col_y1 = 0

            for item in page_targets:
                b_idx = item["batch_idx"]
                trans_text = translated_texts[b_idx] if b_idx < len(translated_texts) else ""
                if not trans_text or not trans_text.strip():
                    continue

                orig_bbox = item["orig_bbox"]
                target_x1 = item["target_x1"]
                orig_fs = item["font_size"]
                color = item["color"]

                is_right_col = orig_bbox.x0 > (page_rect.width * 0.45)
                
                if is_right_col:
                    start_y0 = max(orig_bbox.y0, right_col_y1 + 4)
                else:
                    start_y0 = max(orig_bbox.y0, left_col_y1 + 4)

                if orig_fs >= 14.0:
                    font_size = min(orig_fs, 16.0)
                    font_name = "helv"
                else:
                    font_size = min(9.5, orig_fs)
                    font_name = "helv"

                insert_rect = fitz.Rect(orig_bbox.x0, start_y0, target_x1, min(page_rect.height - 10, start_y0 + 150))

                try:
                    rc = page.insert_textbox(
                        insert_rect,
                        trans_text,
                        fontname=font_name,
                        fontsize=font_size,
                        color=color,
                        align=fitz.TEXT_ALIGN_LEFT
                    )

                    if rc < 0:
                        font_size = max(7.5, font_size - 1.0)
                        rc = page.insert_textbox(
                            insert_rect,
                            trans_text,
                            fontname=font_name,
                            fontsize=font_size,
                            color=color,
                            align=fitz.TEXT_ALIGN_LEFT
                        )

                    actual_height = rc if rc > 0 else (font_size * 2.2)
                    new_bottom_y = start_y0 + actual_height

                    if is_right_col:
                        right_col_y1 = new_bottom_y
                    else:
                        left_col_y1 = new_bottom_y

                except Exception as e:
                    logger.warning(f"Error inserting translated text in page {page_idx+1}: {e}")

        translated_pdf_bytes = doc.tobytes()
        doc.close()
        return translated_pdf_bytes

    def extract_structure(self, pdf_bytes: bytes) -> dict:
        """
        Parses PDF bytes and extracts structured blocks (headings, paragraphs, lists, tables).
        Returns a dict containing document title, total pages, and a list of structured blocks per page.
        """
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        total_pages = len(doc)
        doc_title = doc.metadata.get("title", "") if doc.metadata else ""
        if not doc_title or doc_title.strip() == "":
            doc_title = "Documento_Traducido"

        pages_data = []

        for page_idx in range(total_pages):
            page = doc[page_idx]
            page_number = page_idx + 1

            text_instances = page.get_text("dict")["blocks"]
            blocks = []

            for b in text_instances:
                if b.get("type") == 0:
                    block_text = ""
                    max_font_size = 0
                    is_bold = False

                    for line in b.get("lines", []):
                        line_text = ""
                        for span in line.get("spans", []):
                            span_text = span.get("text", "")
                            font_size = span.get("size", 11)
                            font_flags = span.get("flags", 0)

                            if font_size > max_font_size:
                                max_font_size = font_size
                            if font_flags & 2 or "bold" in span.get("font", "").lower():
                                is_bold = True

                            line_text += span_text
                        block_text += line_text + "\n"

                    clean_text = block_text.strip()
                    if not clean_text:
                        continue

                    block_type = "paragraph"
                    if max_font_size >= 18:
                        block_type = "h1"
                    elif max_font_size >= 14:
                        block_type = "h2"
                    elif max_font_size >= 12 and is_bold:
                        block_type = "h3"
                    elif clean_text.startswith("•") or clean_text.startswith("- ") or clean_text.startswith("* "):
                        block_type = "bullet_item"

                    blocks.append({
                        "type": block_type,
                        "content": clean_text,
                        "font_size": max_font_size,
                        "page": page_number
                    })

            tables_data = []
            try:
                with pdfplumber.open(io.BytesIO(pdf_bytes)) as plumber_pdf:
                    if page_idx < len(plumber_pdf.pages):
                        plumber_page = plumber_pdf.pages[page_idx]
                        extracted_tables = plumber_page.extract_tables()
                        for tbl in extracted_tables:
                            if tbl:
                                clean_table = [[cell.strip() if cell else "" for cell in row] for row in tbl]
                                tables_data.append(clean_table)
            except Exception as e:
                logger.warning(f"pdfplumber table extraction warning on page {page_number}: {e}")

            pages_data.append({
                "page_number": page_number,
                "blocks": blocks,
                "tables": tables_data
            })

        doc.close()

        return {
            "title": doc_title,
            "total_pages": total_pages,
            "pages": pages_data
        }

    def extract_images(self, pdf_bytes: bytes, output_dir: str) -> list:
        """
        Extracts all embedded images from the PDF and saves them to output_dir.
        """
        os.makedirs(output_dir, exist_ok=True)
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        extracted_images = []

        image_count = 0
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            image_list = page.get_images(full=True)

            for img_index, img_info in enumerate(image_list):
                xref = img_info[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]

                image_count += 1
                filename = f"img_p{page_idx + 1}_{image_count}.{image_ext}"
                filepath = os.path.join(output_dir, filename)

                try:
                    with open(filepath, "wb") as f:
                        f.write(image_bytes)

                    extracted_images.append({
                        "filename": filename,
                        "page": page_idx + 1,
                        "relative_path": f"attachments/{filename}",
                        "obsidian_tag": f"![[{filename}]]",
                        "markdown_tag": f"![Imagen](attachments/{filename})"
                    })
                except Exception as e:
                    logger.error(f"Error saving image {filename}: {e}")

        doc.close()
        return extracted_images
