import re
import logging
from deep_translator import GoogleTranslator

logger = logging.getLogger("translator_engine")
logger.setLevel(logging.INFO)

class TranslationEngine:
    def __init__(self):
        pass

    def _protect_syntax(self, text: str):
        """
        Replaces code blocks, math formulas, obsidian tags, and financial terms
        (Call, Put, Strike, GEX, VEX, DDOI, SPX, etc.) with placeholders before translating.
        """
        placeholders = []
        
        def replace_match(match):
            idx = len(placeholders)
            tag = f"__PROTECTED_TAG_{idx}__"
            placeholders.append((tag, match.group(0)))
            return tag

        # Protect code blocks ```...```
        text = re.sub(r'```[\s\S]*?```', replace_match, text)
        # Protect inline code `...`
        text = re.sub(r'`[^`]+`', replace_match, text)
        # Protect Obsidian image links ![[...]]
        text = re.sub(r'!\[\[.*?\]\]', replace_match, text)
        # Protect standard markdown images ![...](...)
        text = re.sub(r'!\[.*?\]\(.*?\)', replace_match, text)
        # Protect Obsidian internal links [[...]]
        text = re.sub(r'\[\[.*?\]\]', replace_match, text)
        # Protect LaTeX math $...$ or $$...$$
        text = re.sub(r'\$\$[\s\S]*?\$\$|\$[^$\n]+\$', replace_match, text)

        # Protect financial & trading terminology so options terms are not translated literally
        text = re.sub(r'\b(Call|Put|Calls|Puts|Strike|Strikes|GEX|VEX|DDOI|Black-Scholes|SPX|S&P 500|ATM|OTM|ITM)\b', replace_match, text)

        return text, placeholders

    def _restore_syntax(self, text: str, placeholders: list):
        for tag, original in placeholders:
            pattern = re.compile(r'\s*' + re.escape(tag) + r'\s*')
            text = pattern.sub(f" {original} ", text)
        return text

    def translate_text(self, text: str, source_lang: str = "auto", target_lang: str = "es") -> str:
        if not text or not text.strip():
            return text

        src = source_lang if source_lang in ["en", "es"] else "auto"
        tgt = target_lang if target_lang in ["en", "es"] else "es"
        
        if src == tgt and src != "auto":
            return text

        translator = GoogleTranslator(source=src, target=tgt)
        protected_text, placeholders = self._protect_syntax(text)

        try:
            trans = translator.translate(protected_text)
            result_text = trans if trans else text
        except Exception as e:
            logger.error(f"Error translating text: {e}")
            result_text = text

        return self._restore_syntax(result_text, placeholders)

    def translate_batch(self, texts_list: list, source_lang: str = "auto", target_lang: str = "es") -> list:
        if not texts_list:
            return []

        src = source_lang if source_lang in ["en", "es"] else "auto"
        tgt = target_lang if target_lang in ["en", "es"] else "es"
        
        if src == tgt and src != "auto":
            return texts_list

        translator = GoogleTranslator(source=src, target=tgt)
        DELIMITER = "\n\n===BLK_DELIM===\n\n"

        translated_results = []
        current_batch = []
        current_len = 0
        batches = []

        for item in texts_list:
            item_str = str(item) if item else ""
            if current_len + len(item_str) + len(DELIMITER) > 3500 and current_batch:
                batches.append(current_batch)
                current_batch = [item_str]
                current_len = len(item_str)
            else:
                current_batch.append(item_str)
                current_len += len(item_str) + len(DELIMITER)

        if current_batch:
            batches.append(current_batch)

        for b in batches:
            combined_text = DELIMITER.join(b)
            protected_text, placeholders = self._protect_syntax(combined_text)

            try:
                trans_combined = translator.translate(protected_text)
                if not trans_combined:
                    trans_combined = protected_text
            except Exception as e:
                logger.error(f"Batch translation exception: {e}")
                trans_combined = protected_text

            restored_text = self._restore_syntax(trans_combined, placeholders)
            split_parts = restored_text.split("===BLK_DELIM===")
            
            if len(split_parts) == len(b):
                for p in split_parts:
                    translated_results.append(p.strip())
            else:
                for orig in b:
                    try:
                        t = translator.translate(orig)
                        translated_results.append(t.strip() if t else orig)
                    except Exception:
                        translated_results.append(orig)

        return translated_results

    def translate_blocks(self, blocks: list, source_lang: str = "auto", target_lang: str = "es") -> list:
        texts_to_translate = []
        for block in blocks:
            b_type = block.get("type", "paragraph")
            if b_type in ["heading", "paragraph", "bullet_item", "quote"]:
                texts_to_translate.append(block.get("content", ""))
            else:
                texts_to_translate.append("")

        translated_texts = self.translate_batch(texts_to_translate, source_lang=source_lang, target_lang=target_lang)

        translated_blocks = []
        for idx, block in enumerate(blocks):
            b_type = block.get("type", "paragraph")
            if b_type in ["heading", "paragraph", "bullet_item", "quote"]:
                trans_content = translated_texts[idx] if idx < len(translated_texts) else block.get("content", "")
                translated_blocks.append({
                    **block,
                    "translated_content": trans_content
                })
            else:
                translated_blocks.append({
                    **block,
                    "translated_content": block.get("content", "")
                })

        return translated_blocks
