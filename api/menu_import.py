"""
Menu import — turn a CSV / spreadsheet / PDF / photo of a menu into draft rows
the owner reviews before saving.

Reuses the Ollama box that care-ai already runs:
  - a text model (default llama3.2:3b) structures messy text (e.g. a text PDF)
  - a vision model (default llama3.2-vision) reads photos / scanned PDFs

This returns DRAFTS only — nothing is written to the DB here. The frontend shows
the rows in the review screen, the owner corrects them, and items are created
through the normal /api/menu-items/ endpoint. So a wrong AI guess can never
silently land in the live menu.
"""
import base64
import csv
import io
import json
import re

import requests
from django.conf import settings

VALID_FOOD = {"veg", "nonveg", "egg"}

EXTRACT_INSTRUCTIONS = (
    "You are extracting a restaurant menu into structured data. "
    "Return ONLY a JSON array and nothing else - no prose, no markdown fences. "
    "Each element must be an object with exactly these keys: "
    '"name" (string), "price" (number), "half_price" (number or null), '
    '"food_type" (one of "veg", "nonveg", "egg"). '
    "Rules: price is the full price as a plain number with no currency symbol. "
    "If a half / small portion price is shown, put it in half_price, else null. "
    'food_type: use "nonveg" for chicken/mutton/fish/prawn/meat dishes, "egg" '
    'for egg dishes, otherwise "veg". Indian menus often mark veg items with a '
    "green dot and non-veg with a red or brown dot - use those if visible. "
    "Skip section headings, addresses, phone numbers, GST notes, and any line "
    "without a price. Clean item names to Title Case and drop trailing dots."
)


class MenuImportError(Exception):
    """Raised for any import failure surfaced to the user."""
    pass


# ---------------------------------------------------------------- Ollama call

def _ollama_generate(prompt, images=None, model=None):
    url = settings.OLLAMA_BASE_URL.rstrip("/") + "/api/generate"
    payload = {
        "model": model or settings.OLLAMA_TEXT_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 2048},
    }
    if images:
        payload["images"] = images
        payload["model"] = model or settings.OLLAMA_VISION_MODEL
    try:
        resp = requests.post(url, json=payload, timeout=settings.OLLAMA_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise MenuImportError(
            "Couldn't reach the AI model. Is Ollama running and the model pulled? "
            f"({e})"
        )
    return resp.json().get("response", "")


# ---------------------------------------------------------------- Gemini call
# Same Gemini API pattern as DocSign's ai_detector (generateContent + JSON out),
# extended with inline image / PDF parts so it can read menu photos & PDFs.
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"


def _provider():
    """Which AI reads photos/PDFs: 'gemini' (cloud, fast) or 'ollama' (local)."""
    p = (getattr(settings, "MENU_AI_PROVIDER", "auto") or "auto").lower()
    if p in ("gemini", "ollama"):
        return p
    return "gemini" if getattr(settings, "GEMINI_API_KEY", "") else "ollama"


def _gemini_generate(parts):
    """Call the Gemini API with text and/or inline image/PDF parts; return text."""
    key = getattr(settings, "GEMINI_API_KEY", "")
    if not key:
        raise MenuImportError("Gemini API key not configured.")
    url = f"{GEMINI_API_URL}/{settings.GEMINI_MODEL}:generateContent?key={key}"
    resp = None
    try:
        resp = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": parts}],
                "generationConfig": {
                    "temperature": 0,
                    "maxOutputTokens": 8192,
                    "responseMimeType": "application/json",
                },
            },
            timeout=settings.GEMINI_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        snippet = ""
        if resp is not None:
            try:
                snippet = " " + resp.text[:200]
            except Exception:
                pass
        raise MenuImportError(f"Gemini request failed: {e}.{snippet}")
    raw = resp.json()
    try:
        return raw["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise MenuImportError("Gemini returned no readable menu. Try a clearer photo.")


# ---------------------------------------------------------------- parse output

def _num(v):
    if v is None or v == "":
        return None
    try:
        return round(float(str(v).replace(",", "").replace("\u20b9", "").strip()), 2)
    except (TypeError, ValueError):
        return None


def _clean_rows(data):
    rows = []
    if not isinstance(data, list):
        return rows
    for d in data:
        if not isinstance(d, dict):
            continue
        name = str(d.get("name", "")).strip()
        if not name:
            continue
        price = _num(d.get("price"))
        ft = str(d.get("food_type", "veg")).lower().strip()
        if ft not in VALID_FOOD:
            ft = "nonveg" if ft.startswith("non") else ("egg" if "egg" in ft else "veg")
        rows.append({
            "name": name[:120],
            "price": "" if price is None else price,
            "half_price": _num(d.get("half_price")),
            "food_type": ft,
            "gst_rate": 5,
        })
    return rows


def _parse_rows(text):
    """Pull a JSON array of items out of model output, defensively."""
    if not text:
        return []
    s = text.strip()
    s = re.sub(r"^```(?:json)?|```$", "", s, flags=re.MULTILINE).strip()
    a, b = s.find("["), s.rfind("]")
    if a != -1 and b != -1 and b > a:
        s = s[a:b + 1]
    try:
        data = json.loads(s)
    except json.JSONDecodeError:
        raise MenuImportError(
            "The AI didn't return a clean menu. Try a clearer photo, or use the paste box."
        )
    return _clean_rows(data)


# ---------------------------------------------------------------- extractors

def _rows_from_pairs(text):
    """Fallback: read 'Name 80' / 'Name, 80' lines without any AI."""
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^(.*?)[\s,\-\u2013]+(\d+(?:\.\d+)?)\s*$", line)
        if m:
            rows.append({"name": m.group(1).strip()[:120], "price": _num(m.group(2)) or "",
                         "half_price": None, "food_type": "veg", "gst_rate": 5})
    return rows


def extract_from_csv(raw):
    text = raw.decode("utf-8", errors="ignore")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames:
        fmap = {(h or "").strip().lower(): h for h in reader.fieldnames}

        def col(*names):
            for n in names:
                if n in fmap:
                    return fmap[n]
            return None

        c_name = col("name", "item", "item name", "dish")
        c_price = col("price", "full", "full price", "rate", "amount")
        c_half = col("half", "half price", "half_price")
        c_type = col("type", "food type", "food_type", "veg")
        c_gst = col("gst", "gst rate", "gst_rate", "tax")
        if c_name and c_price:
            rows = []
            for r in reader:
                name = (r.get(c_name) or "").strip()
                if not name:
                    continue
                ft = (r.get(c_type) or "veg").strip().lower() if c_type else "veg"
                if ft not in VALID_FOOD:
                    ft = "nonveg" if ft.startswith("non") else ("egg" if "egg" in ft else "veg")
                rows.append({
                    "name": name[:120],
                    "price": _num(r.get(c_price)) or "",
                    "half_price": _num(r.get(c_half)) if c_half else None,
                    "food_type": ft,
                    "gst_rate": (_num(r.get(c_gst)) or 5) if c_gst else 5,
                })
            return rows
    # no usable header -> treat as "name price" lines
    return _rows_from_pairs(text)


def extract_from_xlsx(raw):
    try:
        import openpyxl
    except ImportError:
        raise MenuImportError("Spreadsheet (.xlsx) support isn't installed on the server.")
    wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    ws = wb.active
    out = io.StringIO()
    w = csv.writer(out)
    for row in ws.iter_rows(values_only=True):
        w.writerow(["" if c is None else c for c in row])
    return extract_from_csv(out.getvalue().encode("utf-8"))


def extract_from_text(text):
    prompt = EXTRACT_INSTRUCTIONS + "\n\nMenu text:\n\n" + text[:12000]
    if _provider() == "gemini":
        return _parse_rows(_gemini_generate([{"text": prompt}]))
    return _parse_rows(_ollama_generate(prompt))


def extract_from_images(b64_images, mime="image/png"):
    instr = EXTRACT_INSTRUCTIONS + "\n\nRead the menu in the image(s) and output the JSON array."
    if _provider() == "gemini":
        parts = [{"text": instr}]
        for b in b64_images:
            parts.append({"inlineData": {"mimeType": mime, "data": b}})
        return _parse_rows(_gemini_generate(parts))
    out = _ollama_generate(instr, images=b64_images, model=settings.OLLAMA_VISION_MODEL)
    return _parse_rows(out)


def extract_from_pdf(raw):
    # Gemini reads a PDF directly (text or scanned) in one call.
    if _provider() == "gemini":
        b64 = base64.b64encode(raw).decode()
        parts = [
            {"text": EXTRACT_INSTRUCTIONS + "\n\nRead the menu in this PDF and output the JSON array."},
            {"inlineData": {"mimeType": "application/pdf", "data": b64}},
        ]
        return _parse_rows(_gemini_generate(parts))
    # Ollama path: pull text, else rasterise pages to images for the vision model.
    import fitz  # pymupdf
    doc = fitz.open(stream=raw, filetype="pdf")
    text = "\n".join(page.get_text() for page in doc)
    if len(re.sub(r"\s", "", text)) > 60 and any(ch.isdigit() for ch in text):
        return extract_from_text(text)
    images = []
    for page in list(doc)[:5]:
        pix = page.get_pixmap(dpi=150)
        images.append(base64.b64encode(pix.tobytes("png")).decode())
    return extract_from_images(images)


def extract_from_image_file(raw):
    # normalise + downscale big phone photos so the vision model is faster
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        img.thumbnail((1600, 1600))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        raw = buf.getvalue()
    except Exception:
        pass  # if Pillow can't open it, send the original bytes
    return extract_from_images([base64.b64encode(raw).decode()])


# ---------------------------------------------------------------- router

def parse_upload(filename, content_type, raw):
    """Return (rows, source) for an uploaded file, routed by type."""
    name = (filename or "").lower()
    ct = (content_type or "").lower()
    if name.endswith(".csv") or "csv" in ct:
        return extract_from_csv(raw), "csv"
    if name.endswith((".xlsx", ".xlsm")) or "spreadsheet" in ct:
        return extract_from_xlsx(raw), "spreadsheet"
    if name.endswith(".pdf") or "pdf" in ct:
        return extract_from_pdf(raw), "pdf"
    if ct.startswith("image/") or name.endswith((".png", ".jpg", ".jpeg", ".webp")):
        return extract_from_image_file(raw), "image"
    return _rows_from_pairs(raw.decode("utf-8", errors="ignore")), "text"
