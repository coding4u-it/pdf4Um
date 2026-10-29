import base64
from html.parser import HTMLParser
import io
import logging
import os
import re
import secrets
import shutil
import tempfile
import zipfile
import warnings
import sys
from pathlib import Path

_VENDOR_DIR = Path(__file__).resolve().parent / "vendor"
if _VENDOR_DIR.is_dir():
    sys.path.insert(0, str(_VENDOR_DIR))

import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

import mammoth
import reportlab
from docx import Document
from docx.text.paragraph import Paragraph as DocxParagraph
from xhtml2pdf import pisa
from flask import Flask, Response, abort, jsonify, request, send_file
from PIL import Image, ImageOps, UnidentifiedImageError
from pypdf import PdfReader, PdfWriter
from pypdf.constants import UserAccessPermissions
from pypdf.errors import PdfReadError
from pypdf import Transformation
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge


MAX_REQUEST_BYTES = 100 * 1024 * 1024
MAX_FILES = 32
MAX_IMAGE_PIXELS = 40_000_000
MAX_TOTAL_IMAGE_PIXELS = 100_000_000
MAX_DOCUMENT_XML_BYTES = 20 * 1024 * 1024
MAX_DOCUMENT_ARCHIVE_ENTRIES = 10_000
A4_WIDTH = 595.275590551
A4_HEIGHT = 841.88976378
SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
SUPPORTED_DOCUMENT_SUFFIXES = {".docx", ".odt"}

# Namespaces per DOCX
DOCX_NAMESPACE = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

# Namespaces per ODT
ODT_TEXT_NAMESPACE = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"
ODT_TABLE_NAMESPACE = "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}"
ODT_OFFICE_NAMESPACE = "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}"
ODT_DRAW_NAMESPACE = "{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}"
ODT_XLINK_NAMESPACE = "{http://www.w3.org/1999/xlink}"
ODT_STYLE_NAMESPACE = "{urn:oasis:names:tc:opendocument:xmlns:style:1.0}"
ODT_FO_NAMESPACE = "{urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0}"

RANDOM_ALPHABET = "[]()abcdefghijklmnopqrstuvwxyz#.&0123456789$£€,ABCDEFGHIJKLMNOPQRSTUVWXYZ@"
APP_DIRECTORY = Path(__file__).resolve().parent
SOURCE_WEB_DIRECTORY = APP_DIRECTORY / "src" / "main" / "resources" / "web"
DEPLOY_WEB_DIRECTORY = APP_DIRECTORY / "pdf4um-web"
CONFIGURED_WEB_DIRECTORY = os.environ.get("PDF4UM_WEB_DIRECTORY")


def _resolve_web_directory(app_directory: Path, configured_directory: str | None) -> Path:
    if configured_directory:
        directory = Path(configured_directory).expanduser()
        return directory if directory.is_absolute() else app_directory / directory

    required_files = ("index.html", "app.js", "styles.css")
    for directory in (app_directory / "pdf4um-web",
                      app_directory / "src" / "main" / "resources" / "web"):
        if all((directory / name).is_file() for name in required_files):
            return directory
    return app_directory / "pdf4um-web"


WEB_DIRECTORY = _resolve_web_directory(APP_DIRECTORY, CONFIGURED_WEB_DIRECTORY)
ROOT_ASSET_NAMES = {
    "index.html": "pdf4um-index.html",
    "app.js": "pdf4um-app.js",
    "styles.css": "pdf4um-styles.css",
    "logoinfo.png": "pdf4um-logoinfo.png",
}
LOGGER = logging.getLogger(__name__)


class ApiProblem(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_BYTES

    @app.after_request
    def add_security_headers(response: Response) -> Response:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(ApiProblem)
    def handle_api_problem(error: ApiProblem):
        return jsonify(error=error.args[0]), error.status

    @app.errorhandler(RequestEntityTooLarge)
    def handle_large_request(_error: RequestEntityTooLarge):
        return jsonify(error="The upload exceeds the 100 MB request limit."), 413

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        if request.path.startswith("/api/"):
            return jsonify(error=error.description), error.code
        return error

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        LOGGER.exception("Unexpected PDF workbench request failure.", exc_info=error)
        return jsonify(error="The operation could not be completed."), 500

    @app.get("/")
    def index():
        return _static_file("index.html")

    @app.get("/app.js")
    def javascript():
        return _static_file("app.js", "text/javascript; charset=utf-8")

    @app.get("/styles.css")
    def stylesheet():
        return _static_file("styles.css", "text/css; charset=utf-8")

    @app.get("/logoinfo.png")
    def logo():
        return _static_file("logoinfo.png", "image/png")

    @app.route(
        "/api/<path:operation>",
        methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
        provide_automatic_options=False,
    )
    def api(operation: str):
        if operation not in {
            "split", "merge", "rename", "encrypt", "extract-text", "images-to-pdf",
            "documents-to-pdf",
        }:
            abort(404)
        if request.method != "POST":
            abort(405)

        workspace = Path(tempfile.mkdtemp(prefix="pdf4um-request-"))
        try:
            response = _run_operation(operation, workspace)
        except Exception:
            _remove_workspace(workspace)
            raise
        return response

    return app


def _static_file(name: str, mimetype: str = "text/html; charset=utf-8"):
    root_asset_name = ROOT_ASSET_NAMES.get(name)
    root_asset = APP_DIRECTORY / root_asset_name if root_asset_name else None
    if name == "logoinfo.png":
        uploaded_logo = APP_DIRECTORY / name
        if uploaded_logo.is_file():
            root_asset = uploaded_logo
    path = root_asset if root_asset and root_asset.is_file() else WEB_DIRECTORY / name
    if not path.is_file():
        abort(
            503,
            description=(
                "The browser workbench assets are missing. Provide the pdf4um-index.html, "
                "pdf4um-app.js, and pdf4um-styles.css files beside app.py, or provide "
                "index.html, app.js, and styles.css in PDF4UM_WEB_DIRECTORY."
            ),
        )
    return send_file(path, mimetype=mimetype, conditional=False)


def _run_operation(operation: str, workspace: Path) -> Response:
    input_directory = workspace / "input"
    input_directory.mkdir()

    if operation == "split":
        uploads = _save_uploads("file", 1, 1, input_directory)
        pages_per_part = _integer(_text("pagesPerPart", "1"), "pagesPerPart")
        if pages_per_part < 1:
            raise ApiProblem(400, "Pages per part must be greater than zero.")
        readers = _readable_pdfs(uploads)
        stem = uploads[0].stem
        outputs = []
        reader = readers[0]
        for start in range(0, len(reader.pages), pages_per_part):
            writer = PdfWriter()
            for page in reader.pages[start : start + pages_per_part]:
                writer.add_page(page)
            output = input_directory / f"{stem}_{len(outputs) + 1:04d}.pdf"
            with output.open("wb") as stream:
                writer.write(stream)
            outputs.append(output)
        if not outputs:
            raise OSError("No split documents were generated.")
        return _zip_response(outputs, workspace, "split-pdfs.zip")

    if operation == "merge":
        uploads = _save_uploads("files", 2, MAX_FILES, input_directory)
        readers = _readable_pdfs(uploads)
        writer = PdfWriter()
        for reader in readers:
            writer.append(reader)
        output = input_directory / f"{uploads[0].stem}_merged.pdf"
        with output.open("wb") as stream:
            writer.write(stream)
        return _file_response(output, workspace, "application/pdf")

    if operation == "rename":
        uploads = _save_uploads("files", 1, MAX_FILES, input_directory)
        mode = _text("mode", "")
        if mode not in {"sequential", "random"}:
            raise ApiProblem(400, "Rename mode must be sequential or random.")
        prefix = _safe_prefix(_text("prefix", ""))
        starting_number = _integer(_text("startingNumber", "0"), "startingNumber")
        code_length = _integer(_text("codeLength", "8"), "codeLength")
        use_symbols = _boolean("useSymbols", False)
        if starting_number < 0 or starting_number > 9:
            raise ApiProblem(400, "Starting number must be between 0 and 9.")
        if code_length < 4 or code_length > 20:
            raise ApiProblem(400, "Random code length must be between 4 and 20.")
        _readable_pdfs(uploads)
        output_directory = workspace / "renamed"
        output_directory.mkdir()
        outputs = []
        csv_rows = []
        for index, source in enumerate(uploads):
            if mode == "sequential":
                output_name = f"{prefix}{starting_number + index}.pdf"
            else:
                alphabet = RANDOM_ALPHABET if use_symbols else "0123456789"
                code = "".join(secrets.choice(alphabet) for _ in range(code_length))
                output_name = f"{source.stem}{code}.pdf"
                csv_rows.append(f".pdf;{code}\n")
            output = output_directory / output_name
            shutil.copyfile(source, output)
            outputs.append(output)
        if mode == "random":
            export = output_directory / "esporta.csv"
            export.write_text("".join(csv_rows), encoding="utf-8")
            outputs.append(export)
        return _zip_response(outputs, workspace, "renamed-pdfs.zip")

    if operation == "encrypt":
        uploads = _save_uploads("files", 1, MAX_FILES, input_directory)
        password = _text("password", "")
        if not password:
            raise ApiProblem(400, "Password is required.")
        allow_open = _boolean("allowOpen", False)
        allow_print = _boolean("allowPrint", False)
        allow_copy = _boolean("allowCopy", False)
        allow_modify = _boolean("allowModify", False)
        allow_assembly = _boolean("allowAssembly", False)
        readers = _readable_pdfs(uploads)
        permissions = UserAccessPermissions(0)
        if allow_print:
            permissions |= UserAccessPermissions.PRINT
        if allow_copy:
            permissions |= UserAccessPermissions.EXTRACT
        if allow_modify:
            permissions |= UserAccessPermissions.MODIFY
        if allow_assembly:
            permissions |= UserAccessPermissions.ASSEMBLE_DOC
        outputs = []
        for source, reader in zip(uploads, readers):
            writer = PdfWriter()
            writer.append(reader)
            writer.encrypt(
                user_password="" if allow_open else password,
                owner_password=password + password,
                permissions_flag=permissions,
                algorithm="AES-256",
            )
            output = input_directory / f"{source.stem}_cript.pdf"
            with output.open("wb") as stream:
                writer.write(stream)
            outputs.append(output)
        return _zip_response(outputs, workspace, "encrypted-pdfs.zip")

    if operation == "images-to-pdf":
        uploads = _save_image_uploads(input_directory)
        output = input_directory / "immagini.pdf"
        _images_to_pdf(uploads, output)
        return _file_response(output, workspace, "application/pdf")

    if operation == "documents-to-pdf":
        upload = _save_document_upload(input_directory)
        output = _document_to_pdf(upload, workspace)
        return _file_response(output, workspace, "application/pdf")

    uploads = _save_uploads("file", 1, 1, input_directory)
    reader = _readable_pdfs(uploads)[0]
    output = workspace / f"{uploads[0].stem}_text.txt"
    output.write_text("".join(page.extract_text() or "" for page in reader.pages), encoding="utf-8")
    return _file_response(output, workspace, "text/plain; charset=utf-8")


def _save_uploads(field_name: str, minimum: int, maximum: int, directory: Path) -> list[Path]:
    parts = request.files.getlist(field_name)
    if len(parts) < minimum or len(parts) > maximum:
        if minimum == 2:
            message = "Select at least two PDF files."
        elif minimum == maximum == 1:
            message = "Select exactly one PDF file."
        else:
            message = "Select at least one PDF file."
        raise ApiProblem(400, message)

    used_names = set()
    files = []
    for index, part in enumerate(parts, start=1):
        if not part.filename or not part.filename.strip():
            raise ApiProblem(400, "A PDF file is required.")
        filename = _safe_pdf_filename(part.filename, index, used_names)
        destination = directory / filename
        part.save(destination)
        files.append(destination)
    return files


def _save_image_uploads(directory: Path) -> list[Path]:
    parts = request.files.getlist("images")
    if not parts or len(parts) > MAX_FILES:
        raise ApiProblem(400, "Select between one and 32 JPG or PNG images.")

    used_names = set()
    files = []
    for index, part in enumerate(parts, start=1):
        if not part.filename or not part.filename.strip():
            raise ApiProblem(400, "An image file is required.")
        supplied_name = part.filename.replace("\\", "/").rsplit("/", 1)[-1]
        suffix = Path(supplied_name).suffix.lower()
        if suffix not in SUPPORTED_IMAGE_SUFFIXES:
            raise ApiProblem(415, "Only JPG and PNG images are supported.")

        base = re.sub(r'[<>:"/\\|?*]', "_", supplied_name[:-len(Path(supplied_name).suffix)])
        base = "".join(char for char in base if ord(char) >= 32 and ord(char) != 127).strip()
        if not base or base in {".", ".."}:
            base = f"image-{index}"
        filename = f"{base}{suffix}"
        duplicate = 2
        while filename.casefold() in used_names:
            filename = f"{base} ({duplicate}).{suffix.lstrip('.')}"
            duplicate += 1
        used_names.add(filename.casefold())
        destination = directory / filename
        part.save(destination)
        files.append(destination)
    return files


def _save_document_upload(directory: Path) -> Path:
    parts = request.files.getlist("file")
    if len(parts) != 1 or not parts[0].filename or not parts[0].filename.strip():
        raise ApiProblem(400, "Select exactly one DOCX or ODT file.")

    supplied_name = parts[0].filename.replace("\\", "/").rsplit("/", 1)[-1]
    suffix = Path(supplied_name).suffix.lower()
    if suffix not in SUPPORTED_DOCUMENT_SUFFIXES:
        raise ApiProblem(415, "Only DOCX and ODT documents are supported.")

    base = re.sub(r'[<>:"/\\|?*]', "_", supplied_name[:-len(Path(supplied_name).suffix)])
    base = "".join(char for char in base if ord(char) >= 32 and ord(char) != 127).strip()
    if not base or base in {".", ".."}:
        base = "document"
    destination = directory / f"{base}{suffix}"
    parts[0].save(destination)
    return destination


# ---------------------------------------------------------------------------
# CONVERSIONE DOCUMENTI (DOCX / ODT) -> PDF
# ---------------------------------------------------------------------------

def _document_to_pdf(source: Path, workspace: Path) -> Path:
    output = workspace / f"{source.stem}.pdf"
    try:
        if source.suffix.lower() == ".docx":
            html, page_css = _docx_to_html(source)
        else:
            html, page_css = _odt_to_html(source)

        if not html.strip():
            raise ValueError("The document has no supported content.")

        _html_to_pdf(html, page_css, output)

        reader = PdfReader(output, strict=False)
        if reader.is_encrypted or not reader.pages:
            raise PdfReadError("Converted PDF is encrypted or empty.")
    except ApiProblem:
        raise
    except Exception as error:
        LOGGER.info("Document conversion failed for %s.", source.suffix)
        raise ApiProblem(422, "The DOCX or ODT document could not be converted.") from error
    return output


# --- Funzioni specifiche per DOCX ---

def _docx_page_css(source: Path) -> str:
    doc = Document(str(source))
    section = doc.sections[0]

    def inches(value):
        return int(value) / 914400 if value is not None else None

    width = inches(section.page_width) or 8.27
    height = inches(section.page_height) or 11.69
    top = inches(section.top_margin) or 0.79
    bottom = inches(section.bottom_margin) or 0.79
    left = inches(section.left_margin) or 0.79
    right = inches(section.right_margin) or 0.79
    return (
        f"@page {{ size: {width}in {height}in; "
        f"margin: {top}in {right}in {bottom}in {left}in; }}"
    )


def _docx_ordered_list_starts(source: Path) -> list[int | None] | None:
    word_namespace = DOCX_NAMESPACE
    with zipfile.ZipFile(source) as archive:
        document_xml = ET.fromstring(archive.read("word/document.xml"))
        try:
            numbering_xml = ET.fromstring(archive.read("word/numbering.xml"))
        except KeyError:
            return None

    abstract_formats = {}
    for abstract in numbering_xml.findall(f"{word_namespace}abstractNum"):
        abstract_id = abstract.get(f"{word_namespace}abstractNumId")
        for level in abstract.findall(f"{word_namespace}lvl"):
            index = level.get(f"{word_namespace}ilvl", "0")
            num_format = level.find(f"{word_namespace}numFmt")
            level_text = level.find(f"{word_namespace}lvlText")
            start = level.find(f"{word_namespace}start")
            abstract_formats[(abstract_id, index)] = (
                num_format.get(f"{word_namespace}val") if num_format is not None else None,
                level_text.get(f"{word_namespace}val") if level_text is not None else None,
                int(start.get(f"{word_namespace}val")) if start is not None else 1,
            )

    numbering = {}
    for number in numbering_xml.findall(f"{word_namespace}num"):
        number_id = number.get(f"{word_namespace}numId")
        abstract = number.find(f"{word_namespace}abstractNumId")
        if abstract is None:
            continue
        abstract_id = abstract.get(f"{word_namespace}val")
        override = number.find(
            f"{word_namespace}lvlOverride[@{word_namespace}ilvl='0']/"
            f"{word_namespace}startOverride"
        )
        numbering[number_id] = (
            abstract_id,
            int(override.get(f"{word_namespace}val")) if override is not None else None,
        )

    groups = []
    current_number_id = None
    last_number = {}
    for paragraph in document_xml.findall(f".//{word_namespace}body//{word_namespace}p"):
        number_properties = paragraph.find(
            f"{word_namespace}pPr/{word_namespace}numPr"
        )
        if number_properties is None:
            has_text = any(
                (text.text or "").strip()
                for text in paragraph.iter(f"{word_namespace}t")
            )
            has_break_or_image = any(
                element.tag in {
                    f"{word_namespace}br",
                    f"{word_namespace}drawing",
                    f"{word_namespace}object",
                }
                for element in paragraph.iter()
            )
            if has_text or has_break_or_image:
                current_number_id = None
            continue
        number_node = number_properties.find(f"{word_namespace}numId")
        level_node = number_properties.find(f"{word_namespace}ilvl")
        if number_node is None:
            return None
        number_id = number_node.get(f"{word_namespace}val")
        level_index = level_node.get(f"{word_namespace}val", "0") if level_node is not None else "0"
        number_info = numbering.get(number_id)
        if number_info is None:
            return None
        abstract_id, start_override = number_info
        level_format = abstract_formats.get((abstract_id, level_index))
        if level_format is None:
            return None
        num_format, level_text, default_start = level_format

        if level_index != "0":
            if num_format not in {"bullet", "none"}:
                return None
            continue
        if num_format in {"bullet", "none"}:
            current_number_id = None
            continue
        if number_id != current_number_id:
            initial_number = (
                start_override if start_override is not None else default_start
            )
            start = last_number.get(number_id, initial_number)
            marker = re.fullmatch(r"%1([.)])", level_text or "%1.")
            groups.append(
                start if num_format == "decimal" and marker and marker.group(1) == ")" else None
            )
            current_number_id = number_id
        initial_number = start_override if start_override is not None else default_start
        last_number[number_id] = last_number.get(number_id, initial_number) + 1

    return groups


class _DocxListMarkerFormatter(HTMLParser):
    def __init__(self, list_starts: list[int | None]):
        super().__init__(convert_charrefs=False)
        self.list_starts = iter(list_starts)
        self.list_stack = []
        self.output = []

    def handle_starttag(self, tag, attrs):
        if tag in {"ol", "ul"}:
            start = next(self.list_starts, None) if tag == "ol" else None
            self.list_stack.append([tag, start])
            self.output.append(
                '<ol class="pdf4um-custom-numbering">'
                if tag == "ol" and start is not None
                else self.get_starttag_text()
            )
            return
        if tag == "li" and self.list_stack:
            list_tag, next_number = self.list_stack[-1]
            if list_tag == "ol" and next_number is not None:
                self.output.append(self.get_starttag_text())
                self.output.append(
                    f'<span class="pdf4um-list-marker">{next_number})</span> '
                )
                self.list_stack[-1][1] += 1
                return
        self.output.append(self.get_starttag_text())

    def handle_endtag(self, tag):
        self.output.append(f"</{tag}>")
        if tag in {"ol", "ul"} and self.list_stack and self.list_stack[-1][0] == tag:
            self.list_stack.pop()

    def handle_startendtag(self, tag, attrs):
        self.output.append(self.get_starttag_text())

    def handle_data(self, data):
        self.output.append(data)

    def handle_entityref(self, name):
        self.output.append(f"&{name};")

    def handle_charref(self, name):
        self.output.append(f"&#{name};")

    def handle_comment(self, data):
        self.output.append(f"<!--{data}-->")

    def handle_decl(self, decl):
        self.output.append(f"<!{decl}>")

    def format(self, html):
        self.feed(html)
        self.close()
        return "".join(self.output)


def _docx_to_html(source: Path) -> tuple[str, str]:
    doc = Document(str(source))
    with source.open("rb") as stream:
        document = mammoth.docx.read(stream).value

    paragraphs = mammoth.transforms.get_descendants_of_type(
        document, mammoth.documents.Paragraph
    )
    xml_paragraphs = [
        DocxParagraph(element, doc._body)
        for element in doc._element.body.iter(f"{DOCX_NAMESPACE}p")
    ]
    runs = mammoth.transforms.get_descendants_of_type(
        document, mammoth.documents.Run
    )
    xml_runs = list(doc._element.body.iter(f"{DOCX_NAMESPACE}r"))
    run_colors = []
    for xml_run in xml_runs:
        properties = xml_run.find(f"{DOCX_NAMESPACE}rPr")
        color = properties.find(f"{DOCX_NAMESPACE}color") if properties is not None else None
        value = color.get(f"{DOCX_NAMESPACE}val") if color is not None else None
        run_colors.append(
            f"#{value}" if value and value.lower() != "auto" and re.fullmatch(r"[0-9A-Fa-f]{6}", value) else None
        )
    if len(run_colors) != len(runs):
        run_colors = [None] * len(runs)

    font_root = Path(reportlab.__file__).resolve().parent / "fonts"
    vera_fonts = {
        "normal": font_root / "Vera.ttf",
        "bold": font_root / "VeraBd.ttf",
        "italic": font_root / "VeraIt.ttf",
        "bold_italic": font_root / "VeraBI.ttf",
    }
    has_vera_fonts = all(path.is_file() for path in vera_fonts.values())

    def font_family(name):
        normalized = (name or "").strip().casefold()
        if normalized in {"verdana", "comic sans ms", "calibri", "aptos"} and has_vera_fonts:
            return "Pdf4UmVeraSans"
        if normalized in {"times new roman", "cambria", "georgia"}:
            return "Times-Roman"
        if normalized in {"courier new", "consolas"}:
            return "Courier"
        return "Helvetica"

    def font_css(font, *, include_family=True):
        declarations = []
        if include_family and font.name:
            declarations.append(f'font-family: "{font_family(font.name)}"')
        if font.size:
            declarations.append(f"font-size: {font.size.pt:g}pt")
        if font.bold is not None:
            declarations.append(f"font-weight: {'bold' if font.bold else 'normal'}")
        if font.italic is not None:
            declarations.append(f"font-style: {'italic' if font.italic else 'normal'}")
        color = font.color.rgb
        if color is not None:
            declarations.append(f"color: #{color}")
        return declarations

    paragraph_rules = []
    css_rules = []
    normal_style = doc.styles["Normal"]
    body_declarations = font_css(normal_style.font)
    if body_declarations:
        css_rules.append(f"body {{ {'; '.join(body_declarations)}; }}")
    numbered_paragraphs = [paragraph for paragraph in paragraphs if paragraph.numbering]
    if numbered_paragraphs:
        list_runs = mammoth.transforms.get_descendants_of_type(
            numbered_paragraphs[0], mammoth.documents.Run
        )
        if list_runs:
            list_declarations = [
                f'font-family: "{font_family(list_runs[0].font)}"'
            ] if list_runs[0].font else []
            if list_runs[0].font_size:
                list_declarations.append(f"font-size: {list_runs[0].font_size:g}pt")
            if list_declarations:
                css_rules.append(f"ol, ul {{ {'; '.join(list_declarations)}; }}")
    for index, paragraph in enumerate(paragraphs):
        if paragraph.numbering:
            continue
        marker = f"Pdf4UmParagraph{index}"
        style = xml_paragraphs[index].style if index < len(xml_paragraphs) else None
        style_name = style.name if style else paragraph.style_name or ""
        tag = {
            "Heading 1": "h1",
            "Heading 2": "h2",
            "Heading 3": "h3",
            "Title": "h1",
            "Subtitle": "p",
        }.get(style_name, "p")
        paragraph_rules.append(
            f"p[style-name='{marker}'] => {tag}.pdf4um-paragraph-{index}:fresh"
        )
        declarations = font_css(style.font) if style else []
        if paragraph.alignment:
            alignment = {"both": "justify"}.get(paragraph.alignment, paragraph.alignment)
            declarations.append(f"text-align: {alignment}")
        if declarations:
            css_rules.append(
                f".pdf4um-paragraph-{index} {{ {'; '.join(declarations)}; }}"
            )

    run_rules = []
    for index, run in enumerate(runs):
        marker = f"Pdf4UmRun{index}"
        run_rules.append(f"r[style-name='{marker}'] => span.pdf4um-run-{index}")
        declarations = [f'font-family: "{font_family(run.font)}"'] if run.font else []
        if run.font_size:
            declarations.append(f"font-size: {run.font_size:g}pt")
        if run.is_bold is not None:
            declarations.append(f"font-weight: {'bold' if run.is_bold else 'normal'}")
        if run.is_italic is not None:
            declarations.append(f"font-style: {'italic' if run.is_italic else 'normal'}")
        if run.is_underline is not None or run.is_strikethrough is not None:
            decorations = []
            if run.is_underline:
                decorations.append("underline")
            if run.is_strikethrough:
                decorations.append("line-through")
            declarations.append(
                f"text-decoration: {' '.join(decorations) if decorations else 'none'}"
            )
        if run.is_all_caps:
            declarations.append("text-transform: uppercase")
        if run.is_small_caps:
            declarations.append("font-variant: small-caps")
        if index < len(run_colors) and run_colors[index]:
            declarations.append(f"color: {run_colors[index]}")
        if declarations:
            css_rules.append(f".pdf4um-run-{index} {{ {'; '.join(declarations)}; }}")

    paragraph_index = iter(range(len(paragraphs)))
    run_index = iter(range(len(runs)))

    def apply_paragraph_style(paragraph):
        index = next(paragraph_index)
        if paragraph.numbering:
            return paragraph
        return paragraph.copy(style_name=f"Pdf4UmParagraph{index}")

    transform_paragraph = mammoth.transforms.paragraph(apply_paragraph_style)
    transform_run = mammoth.transforms.run(
        lambda run: run.copy(style_name=f"Pdf4UmRun{next(run_index)}")
    )

    def transform_document(value):
        return transform_run(transform_paragraph(value))

    style_map = "\n".join(paragraph_rules + run_rules)

    def _image_handler(image):
        with image.open() as img:
            encoded = base64.b64encode(img.read()).decode("ascii")
        return {"src": f"data:{image.content_type};base64,{encoded}"}

    with source.open("rb") as stream:
        result = mammoth.convert_to_html(
            stream,
            transform_document=transform_document,
            style_map=style_map,
            convert_image=mammoth.images.img_element(_image_handler),
        )
    list_starts = _docx_ordered_list_starts(source)
    if list_starts and any(start is not None for start in list_starts):
        html_list_count = len(re.findall(r"<ol(?:\s|>)", result.value))
        if html_list_count == len(list_starts):
            result.value = _DocxListMarkerFormatter(list_starts).format(result.value)
            css_rules.append(".pdf4um-custom-numbering { list-style-type: none; }")
        else:
            LOGGER.warning(
                "DOCX ordered-list groups could not be matched; using default numbering."
            )
    if has_vera_fonts:
        font_faces = "\n".join(
            f'@font-face {{ font-family: "Pdf4UmVeraSans"; src: url("{path.as_uri()}");'
            f"{' font-weight: bold;' if 'bold' in name else ''}"
            f"{' font-style: italic;' if 'italic' in name else ''} }}"
            for name, path in vera_fonts.items()
        )
        css_rules.insert(0, font_faces)
    page_css = _docx_page_css(source) + "\n" + "\n".join(css_rules)
    return result.value, page_css


# --- Funzioni specifiche per ODT ---

def _odt_page_css(source: Path) -> str:
    with zipfile.ZipFile(source) as archive:
        for member in ("styles.xml", "content.xml"):
            try:
                root = ET.fromstring(archive.read(member))
            except KeyError:
                continue
            layout = root.find(f".//{ODT_STYLE_NAMESPACE}page-layout/{ODT_STYLE_NAMESPACE}page-layout-properties")
            if layout is None:
                continue

            def to_in(val, default):
                if not val: return default
                factors = {"cm": 0.393701, "mm": 0.0393701, "in": 1.0, "pt": 0.0138889, "pc": 0.166667}
                for unit, factor in sorted(factors.items(), key=lambda x: -len(x[0])):
                    if val.endswith(unit):
                        return float(val[:-len(unit)]) * factor
                return float(val) / 72.0

            w = to_in(layout.get(f"{ODT_FO_NAMESPACE}page-width"), 8.27)
            h = to_in(layout.get(f"{ODT_FO_NAMESPACE}page-height"), 11.69)
            t = to_in(layout.get(f"{ODT_FO_NAMESPACE}margin-top"), 0.79)
            b = to_in(layout.get(f"{ODT_FO_NAMESPACE}margin-bottom"), 0.79)
            l = to_in(layout.get(f"{ODT_FO_NAMESPACE}margin-left"), 0.79)
            r = to_in(layout.get(f"{ODT_FO_NAMESPACE}margin-right"), 0.79)
            return f"@page {{ size: {w}in {h}in; margin: {t}in {r}in {b}in {l}in; }}"
    return "@page { size: A4; margin: 2cm; }"


def _extract_odt_styles(root: ET.Element) -> dict:
    styles = {}
    for style in root.findall(f".//{ODT_STYLE_NAMESPACE}style"):
        if style.get(f"{ODT_STYLE_NAMESPACE}family") == "text":
            name = style.get(f"{ODT_STYLE_NAMESPACE}name")
            props = style.find(f"{ODT_STYLE_NAMESPACE}text-properties")
            if name and props is not None:
                info = {}
                if props.get(f"{ODT_FO_NAMESPACE}font-weight") == "bold":
                    info["bold"] = True
                if props.get(f"{ODT_FO_NAMESPACE}font-style") == "italic":
                    info["italic"] = True
                if props.get(f"{ODT_STYLE_NAMESPACE}text-underline-style", "none") != "none":
                    info["underline"] = True
                styles[name] = info
    return styles


def _odt_to_html(source: Path) -> tuple[str, str]:
    page_css = _odt_page_css(source)
    with zipfile.ZipFile(source) as archive:
        root = ET.fromstring(archive.read("content.xml"))
        styles_root = root
        try:
            styles_root = ET.fromstring(archive.read("styles.xml"))
        except KeyError:
            pass

        text_styles = _extract_odt_styles(styles_root)
        text_styles.update(_extract_odt_styles(root))

        body = root.find(f".//{ODT_OFFICE_NAMESPACE}body/{ODT_OFFICE_NAMESPACE}text")
        if body is None:
            raise ValueError("The ODT body is missing.")

        html = _odt_blocks_to_html(body, archive, text_styles)
    return html, page_css


def _odt_blocks_to_html(element: ET.Element, archive: zipfile.ZipFile, text_styles: dict) -> str:
    html = []
    for child in element:
        if child.tag in {f"{ODT_TEXT_NAMESPACE}p", f"{ODT_TEXT_NAMESPACE}h"}:
            tag = "h2" if child.tag == f"{ODT_TEXT_NAMESPACE}h" else "p"
            inline_html = _odt_inline_to_html(child, archive, text_styles)
            html.append(f"<{tag}>{inline_html}</{tag}>")

        elif child.tag == f"{ODT_TEXT_NAMESPACE}list":
            html.append("<ul>")
            for item in child.findall(f"{ODT_TEXT_NAMESPACE}list-item"):
                html.append("<li>")
                html.append(_odt_blocks_to_html(item, archive, text_styles))
                html.append("</li>")
            html.append("</ul>")

        elif child.tag == f"{ODT_TABLE_NAMESPACE}table":
            html.append("<table>")
            for row in child.findall(f"{ODT_TABLE_NAMESPACE}table-row"):
                html.append("<tr>")
                for cell in row:
                    if cell.tag in {f"{ODT_TABLE_NAMESPACE}table-cell", f"{ODT_TABLE_NAMESPACE}covered-table-cell"}:
                        html.append("<td>")
                        html.append(_odt_blocks_to_html(cell, archive, text_styles))
                        html.append("</td>")
                html.append("</tr>")
            html.append("</table>")
    return "".join(html)


def _odt_inline_to_html(element: ET.Element, archive: zipfile.ZipFile, text_styles: dict) -> str:
    def render(node: ET.Element) -> str:
        if node.tag == f"{ODT_TEXT_NAMESPACE}s":
            count = min(int(node.get(f"{ODT_TEXT_NAMESPACE}c", "1")), 100)
            return "&#160;" * count
        if node.tag == f"{ODT_TEXT_NAMESPACE}tab":
            return "&#160;&#160;&#160;&#160;"
        if node.tag == f"{ODT_TEXT_NAMESPACE}line-break":
            return "<br/>"
        
        if node.tag == f"{ODT_TEXT_NAMESPACE}span":
            style_name = node.get(f"{ODT_TEXT_NAMESPACE}style-name")
            content = "".join([escape(node.text or "")] + [render(c) + escape(c.tail or "") for c in node])
            style = text_styles.get(style_name, {})
            if style.get("bold"): content = f"<b>{content}</b>"
            if style.get("italic"): content = f"<i>{content}</i>"
            if style.get("underline"): content = f"<u>{content}</u>"
            return content

        if node.tag == f"{ODT_DRAW_NAMESPACE}frame":
            image = node.find(f"{ODT_DRAW_NAMESPACE}image")
            if image is not None:
                href = image.get(f"{ODT_XLINK_NAMESPACE}href")
                if href and href in archive.namelist():
                    data = archive.read(href)
                    ext = href.split(".")[-1].lower()
                    mime = "image/jpeg" if ext in ("jpg", "jpeg") else "image/png" if ext == "png" else "image/gif"
                    b64 = base64.b64encode(data).decode("ascii")
                    return f'<img src="data:{mime};base64,{b64}" style="max-width: 100%;" />'
            return ""

        parts = [escape(node.text or "")]
        for child in node:
            parts.append(render(child))
            parts.append(escape(child.tail or ""))
        return "".join(parts)

    return render(element)


# --- HTML to PDF (Comune) ---

def _html_to_pdf(html: str, page_css: str, output: Path) -> None:
    full = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<style>
body {{ font-family: Helvetica, Arial, sans-serif; font-size: 11pt; line-height: 1.35; color: #000; }}
h1 {{ font-size: 18pt; margin: 0 0 8pt 0; }}
h2 {{ font-size: 15pt; margin: 12pt 0 6pt 0; }}
h3 {{ font-size: 13pt; margin: 10pt 0 5pt 0; }}
p  {{ margin: 0 0 6pt 0; }}
table {{ border-collapse: collapse; width: 100%; margin: 6pt 0; }}
td, th {{ border: 1px solid #999; padding: 3pt 5pt; vertical-align: top; }}
th {{ background: #f0f0f0; }}
img {{ max-width: 100%; }}
ul, ol {{ margin: 4pt 0 6pt 18pt; padding: 0; }}
li {{ margin-bottom: 2pt; }}
{page_css}
</style></head>
<body>{html}</body></html>"""
    with output.open("wb") as stream:
        result = pisa.CreatePDF(src=full, dest=stream, encoding="utf-8")
    if result.err:
        raise RuntimeError(f"xhtml2pdf reported {result.err} errors.")


# ---------------------------------------------------------------------------
# ALTRE FUNZIONI (PDF, IMMAGINI, ECC.)
# ---------------------------------------------------------------------------

def _images_to_pdf(images: list[Path], output: Path) -> None:
    page_width, page_height = A4_WIDTH, A4_HEIGHT
    margin = 36
    available_width = page_width - margin * 2
    available_height = page_height - margin * 2
    total_pixels = 0
    pdf = PdfWriter()

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            for image_path in images:
                try:
                    with Image.open(image_path) as source:
                        if source.format not in {"JPEG", "PNG"}:
                            raise ApiProblem(415, "Only JPG and PNG images are supported.")
                        width, height = source.size
                        pixels = width * height
                        total_pixels += pixels
                        if pixels > MAX_IMAGE_PIXELS or total_pixels > MAX_TOTAL_IMAGE_PIXELS:
                            raise ApiProblem(
                                413,
                                "The images exceed the supported total pixel limit.",
                            )
                        source.verify()

                    with Image.open(image_path) as source:
                        image = ImageOps.exif_transpose(source)
                        if image.mode in {"RGBA", "LA"} or (
                            image.mode == "P" and "transparency" in image.info
                        ):
                            rgba = image.convert("RGBA")
                            background = Image.new("RGB", rgba.size, "white")
                            background.paste(rgba, mask=rgba.getchannel("A"))
                            image = background
                        else:
                            image = image.convert("RGB")

                        image_pdf = io.BytesIO()
                        image.save(image_pdf, format="PDF", resolution=72)
                        image_pdf.seek(0)
                        image_page = PdfReader(image_pdf).pages[0]
                        image_width = float(image_page.mediabox.width)
                        image_height = float(image_page.mediabox.height)
                        scale = min(
                            available_width / image_width,
                            available_height / image_height,
                        )
                        draw_width = image_width * scale
                        draw_height = image_height * scale
                        x = (page_width - draw_width) / 2
                        y = (page_height - draw_height) / 2
                        page = pdf.add_blank_page(width=page_width, height=page_height)
                        page.merge_transformed_page(
                            image_page,
                            Transformation().scale(scale).translate(x, y),
                        )
                except ApiProblem:
                    raise
                except (
                    Image.DecompressionBombError,
                    Image.DecompressionBombWarning,
                    UnidentifiedImageError,
                    OSError,
                    ValueError,
                ) as error:
                    raise ApiProblem(422, "One or more images are unreadable.") from error
        with output.open("wb") as stream:
            pdf.write(stream)
    except Exception:
        output.unlink(missing_ok=True)
        raise


def _safe_pdf_filename(supplied_name: str, index: int, used_names: set[str]) -> str:
    leaf = supplied_name.replace("\\", "/").rsplit("/", 1)[-1]
    leaf = "".join(char for char in leaf if ord(char) >= 32 and ord(char) != 127).strip()
    if not leaf.lower().endswith(".pdf"):
        raise ApiProblem(415, "Only PDF files are supported.")
    base = re.sub(r'[<>:"/\\|?*]', "_", leaf[:-4]).strip()
    if not base or base in {".", ".."}:
        base = f"upload-{index}"
    filename = f"{base}.pdf"
    duplicate = 2
    while filename.casefold() in used_names:
        filename = f"{base} ({duplicate}).pdf"
        duplicate += 1
    used_names.add(filename.casefold())
    return filename


def _readable_pdfs(files: list[Path]) -> list[PdfReader]:
    readers = []
    for path in files:
        try:
            reader = PdfReader(path, strict=False)
            if reader.is_encrypted:
                raise PdfReadError("Encrypted PDFs require a password.")
            _ = len(reader.pages)
            readers.append(reader)
        except (OSError, PdfReadError, ValueError) as error:
            raise ApiProblem(422, "One or more PDFs are unreadable or password protected.") from error
    return readers


def _text(name: str, default: str) -> str:
    values = request.form.getlist(name)
    if not values:
        return default
    if len(values) != 1:
        raise ApiProblem(400, f"Invalid field: {name}")
    return values[0]


def _integer(value: str, field: str) -> int:
    try:
        return int(value.strip())
    except ValueError as error:
        raise ApiProblem(400, f"Invalid {field} value.") from error


def _boolean(name: str, default: bool) -> bool:
    value = _text(name, "")
    if not value:
        return default
    normalized = value.strip().lower()
    if normalized in {"true", "on", "1", "yes"}:
        return True
    if normalized in {"false", "off", "0", "no"}:
        return False
    raise ApiProblem(400, f"Invalid {name} value.")


def _safe_prefix(prefix: str) -> str:
    safe = "".join(char for char in prefix if ord(char) >= 32 and ord(char) != 127)
    safe = re.sub(r'[<>:"/\\|?*]', "_", safe)
    return safe[:100]


def _zip_response(files: list[Path], workspace: Path, download_name: str) -> Response:
    if not files or any(not path.is_file() for path in files):
        raise OSError("Expected output files were not created.")
    archive = workspace / download_name
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for path in files:
            output.write(path, arcname=path.name)
    return _file_response(archive, workspace, "application/zip")


def _file_response(path: Path, workspace: Path, mimetype: str) -> Response:
    if not path.is_file():
        raise OSError("Expected output file was not created.")
    response = send_file(
        path,
        mimetype=mimetype,
        as_attachment=True,
        download_name=path.name,
        conditional=False,
    )
    response.call_on_close(lambda: _remove_workspace(workspace))
    return response


def _remove_workspace(workspace: Path) -> None:
    try:
        shutil.rmtree(workspace)
    except FileNotFoundError:
        return
    except OSError:
        LOGGER.exception("Unable to remove a temporary PDF work directory.")


app = create_app()


if __name__ == "__main__":
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8080")),
    )