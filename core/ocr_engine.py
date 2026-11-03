import re
from typing import Optional, Union, List
import numpy as np
from PIL import Image

class OCREngine:
    """Wrapper around RapidOCR with lazy initialization and smart text formatting."""
    
    _instance: Optional['OCREngine'] = None
    
    def __init__(self):
        self._ocr = None

    @classmethod
    def get_instance(cls) -> 'OCREngine':
        if cls._instance is None:
            cls._instance = OCREngine()
        return cls._instance

    def _ensure_ocr(self):
        if self._ocr is None:
            from rapidocr_onnxruntime import RapidOCR
            self._ocr = RapidOCR()

    def recognize(self, img_input: Union[np.ndarray, Image.Image, bytes, str]) -> str:
        """
        Runs OCR on given image input.
        img_input can be numpy array, PIL Image, bytes, or file path.
        Returns recognized string.
        """
        self._ensure_ocr()
        
        if isinstance(img_input, Image.Image):
            # Convert PIL to RGB numpy array
            img_np = np.array(img_input.convert("RGB"))
        elif isinstance(img_input, (bytes, bytearray)):
            import io
            pil_img = Image.open(io.BytesIO(img_input)).convert("RGB")
            img_np = np.array(pil_img)
        else:
            img_np = img_input

        results, _ = self._ocr(img_np)
        if not results:
            return ""

        return self._format_ocr_results(results)

    def _format_ocr_results(self, results: List) -> str:
        """
        Formats OCR bounding box results into natural readable paragraphs.
        results: list of [[box_coords], text, confidence]
        """
        # Sort results primarily by top Y coordinate, then X
        def get_box_top_left(item):
            box = item[0]
            # box is [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            return (box[0][1], box[0][0])

        sorted_items = sorted(results, key=get_box_top_left)
        lines = [item[1].strip() for item in sorted_items if len(item) > 1 and item[1].strip()]
        
        if not lines:
            return ""

        # Smart merge lines
        merged_text = []
        for i, line in enumerate(lines):
            if i == 0:
                merged_text.append(line)
                continue
            
            prev_line = merged_text[-1]
            # If prev_line ends with hyphen, strip hyphen and join
            if prev_line.endswith("-"):
                merged_text[-1] = prev_line[:-1] + line
            # If both lines are English/latin (end with ascii and start with ascii), add space
            elif prev_line and prev_line[-1].isascii() and prev_line[-1].isalnum() and line[0].isascii() and line[0].isalnum():
                merged_text[-1] = prev_line + " " + line
            # If CJK or punctuation, join directly or with newline if it looks like a paragraph break
            elif prev_line and (prev_line[-1] in "。！？.!?:；;" or prev_line.endswith(".")):
                merged_text.append(line)
            else:
                # Normal continuation
                # Check if both are Chinese
                if not prev_line[-1].isascii() and not line[0].isascii():
                    merged_text[-1] = prev_line + line
                else:
                    merged_text[-1] = prev_line + " " + line

        return "\n\n".join(merged_text)

ocr_engine = OCREngine.get_instance()
