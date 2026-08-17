import os
import io
import zipfile
from datetime import datetime

class ObsidianBuilder:
    def __init__(self):
        pass

    def build_markdown(self, translated_data: dict, images: list, use_wiki_links: bool = True) -> str:
        """
        Builds a complete, formatted Obsidian Markdown note with Frontmatter and images.
        """
        title = translated_data.get("title", "Documento_Traducido").replace(" ", "_")
        pages = translated_data.get("pages", [])
        
        today_str = datetime.now().strftime("%Y-%m-%d")

        # 1. Frontmatter
        lines = [
            "---",
            f"title: \"{title}\"",
            f"date_converted: {today_str}",
            "source_type: pdf",
            "tags:",
              "  - pdf-import",
              "  - translation",
              "  - obsidian-note",
            "---",
            "",
            f"# {title.replace('_', ' ')}",
            ""
        ]

        # Map images per page for interleaving
        images_by_page = {}
        for img in images:
            p = img["page"]
            if p not in images_by_page:
                images_by_page[p] = []
            images_by_page[p].append(img)

        # 2. Process Page by Page
        for page in pages:
            page_num = page["page_number"]
            blocks = page.get("blocks", [])
            tables = page.get("tables", [])

            lines.append(f"<!-- Página {page_num} -->")

            # Add images belonging to this page
            if page_num in images_by_page:
                for img in images_by_page[page_num]:
                    if use_wiki_links:
                        lines.append(f"![[{img['filename']}]]")
                    else:
                        lines.append(f"![Imagen]({img['relative_path']})")
                    lines.append("")

            # Process text blocks
            for block in blocks:
                b_type = block.get("type", "paragraph")
                content = block.get("translated_content", block.get("content", ""))

                if not content.strip():
                    continue

                if b_type == "h1":
                    lines.append(f"# {content}")
                elif b_type == "h2":
                    lines.append(f"## {content}")
                elif b_type == "h3":
                    lines.append(f"### {content}")
                elif b_type == "bullet_item":
                    lines.append(f"- {content}")
                elif b_type == "quote":
                    lines.append(f"> {content}")
                elif b_type == "paragraph":
                    lines.append(content)
                
                lines.append("")

            # Process tables
            for tbl in tables:
                if tbl and len(tbl) > 0:
                    # Header row
                    header = tbl[0]
                    lines.append("| " + " | ".join(header) + " |")
                    lines.append("| " + " | ".join(["---"] * len(header)) + " |")
                    # Data rows
                    for row in tbl[1:]:
                        lines.append("| " + " | ".join(row) + " |")
                    lines.append("")

            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def build_zip_package(self, markdown_text: str, doc_title: str, images_dir: str) -> bytes:
        """
        Creates an in-memory ZIP package containing:
        - {doc_title}.md
        - attachments/{images...}
        """
        zip_buffer = io.BytesIO()

        clean_title = "".join([c for c in doc_title if c.isalnum() or c in (' ', '_', '-')]).rstrip()
        if not clean_title:
            clean_title = "Nota_Traducida"

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # Write markdown note
            zip_file.writestr(f"{clean_title}.md", markdown_text)

            # Write attached images if exists
            if os.path.exists(images_dir):
                for root, _, files in os.walk(images_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.join("attachments", file)
                        zip_file.write(file_path, arcname)

        zip_buffer.seek(0)
        return zip_buffer.getvalue()
