import io
import logging
import os
import re
import secrets
import shutil
import tempfile
import zipfile
import warnings
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape

from flask import Flask, Response, abort, jsonify, request, send_file
from PIL import Image, ImageOps, UnidentifiedImageError
from pypdf import PdfReader, PdfWriter
from pypdf.constants import UserAccessPermissions
from pypdf.errors import PdfReadError
from pypdf import Transformation
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
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
DOCX_NAMESPACE = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
ODT_TEXT_NAMESPACE = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"
ODT_TABLE_NAMESPACE = "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}"
ODT_OFFICE_NAMESPACE = "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}"
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


def _document_to_pdf(source: Path, workspace: Path) -> Path:
    output = workspace / f"{source.stem}.pdf"
    try:
        blocks = _document_blocks(source)
        if not any(_block_has_content(block) for block in blocks):
            raise ValueError("The document has no supported text content.")
        _write_document_pdf(blocks, output)
        reader = PdfReader(output, strict=False)
        if reader.is_encrypted or not reader.pages:
            raise PdfReadError("Converted PDF is encrypted or empty.")
    except ApiProblem:
        raise
    except (OSError, zipfile.BadZipFile, ET.ParseError, PdfReadError, ValueError) as error:
        LOGGER.info("Document conversion failed for %s.", source.suffix)
        raise ApiProblem(422, "The DOCX or ODT document could not be converted.") from error
    return output


def _document_blocks(source: Path) -> list[tuple[str, object]]:
    with zipfile.ZipFile(source) as archive:
        entries = archive.infolist()
        if len(entries) > MAX_DOCUMENT_ARCHIVE_ENTRIES:
            raise ValueError("The document archive contains too many entries.")
        members = {entry.filename: entry for entry in entries}
        document_name = "word/document.xml" if source.suffix.lower() == ".docx" else "content.xml"
        document_info = members.get(document_name)
        if document_info is None or document_info.file_size > MAX_DOCUMENT_XML_BYTES:
            raise ValueError("The document XML is missing or too large.")
        document = _parse_document_xml(archive.read(document_name))
        if source.suffix.lower() == ".docx":
            body = document.find(f".//{DOCX_NAMESPACE}body")
            if body is None:
                raise ValueError("The DOCX body is missing.")
            return _docx_blocks(body)

        body = document.find(f".//{ODT_OFFICE_NAMESPACE}body/{ODT_OFFICE_NAMESPACE}text")
        if body is None:
            raise ValueError("The ODT body is missing.")
        return _odt_blocks(body)


def _parse_document_xml(content: bytes) -> ET.Element:
    if b"<!DOCTYPE" in content.upper() or b"<!ENTITY" in content.upper():
        raise ValueError("Document XML declarations are not supported.")
    return ET.fromstring(content)


def _docx_blocks(body: ET.Element) -> list[tuple[str, object]]:
    blocks = []
    for element in body:
        if element.tag == f"{DOCX_NAMESPACE}p":
            properties = element.find(f"{DOCX_NAMESPACE}pPr")
            style = properties.find(f"{DOCX_NAMESPACE}pStyle") if properties is not None else None
            style_name = style.get(f"{DOCX_NAMESPACE}val", "").lower() if style is not None else ""
            kind = "heading" if style_name.startswith(("heading", "title", "subtitle")) else "paragraph"
            prefix = ""
            if properties is not None and properties.find(f"{DOCX_NAMESPACE}numPr") is not None:
                prefix = "• "
            blocks.append((kind, escape(prefix) + _docx_inline(element)))
        elif element.tag == f"{DOCX_NAMESPACE}tbl":
            rows = []
            for row in element.findall(f"{DOCX_NAMESPACE}tr"):
                cells = []
                for cell in row.findall(f"{DOCX_NAMESPACE}tc"):
                    paragraphs = [
                        _docx_inline(paragraph)
                        for paragraph in cell.findall(f"{DOCX_NAMESPACE}p")
                    ]
                    cells.append("<br/>".join(paragraphs))
                if cells:
                    rows.append(cells)
            if rows:
                blocks.append(("table", rows))
    return blocks


def _docx_inline(paragraph: ET.Element) -> str:
    parts = []
    for run in paragraph.iter(f"{DOCX_NAMESPACE}r"):
        properties = run.find(f"{DOCX_NAMESPACE}rPr")
        bold = properties is not None and properties.find(f"{DOCX_NAMESPACE}b") is not None
        italic = properties is not None and properties.find(f"{DOCX_NAMESPACE}i") is not None
        value = []
        for element in run.iter():
            if element.tag == f"{DOCX_NAMESPACE}t" and element.text:
                value.append(escape(element.text))
            elif element.tag == f"{DOCX_NAMESPACE}tab":
                value.append("&#160;&#160;&#160;&#160;")
            elif element.tag == f"{DOCX_NAMESPACE}br":
                value.append("<br/>")
        text = "".join(value)
        if bold:
            text = f"<b>{text}</b>"
        if italic:
            text = f"<i>{text}</i>"
        parts.append(text)
    return "".join(parts)


def _odt_blocks(body: ET.Element, in_list: bool = False) -> list[tuple[str, object]]:
    blocks = []
    for element in body:
        if element.tag in {f"{ODT_TEXT_NAMESPACE}p", f"{ODT_TEXT_NAMESPACE}h"}:
            kind = "heading" if element.tag == f"{ODT_TEXT_NAMESPACE}h" else "paragraph"
            prefix = "• " if in_list and kind == "paragraph" else ""
            blocks.append((kind, escape(prefix) + _odt_inline(element)))
        elif element.tag == f"{ODT_TABLE_NAMESPACE}table":
            rows = []
            for row in element.iter(f"{ODT_TABLE_NAMESPACE}table-row"):
                cells = []
                for cell in row:
                    if cell.tag not in {
                        f"{ODT_TABLE_NAMESPACE}table-cell",
                        f"{ODT_TABLE_NAMESPACE}covered-table-cell",
                    }:
                        continue
                    paragraphs = [
                        _odt_inline(paragraph)
                        for paragraph in cell
                        if paragraph.tag in {
                            f"{ODT_TEXT_NAMESPACE}p",
                            f"{ODT_TEXT_NAMESPACE}h",
                        }
                    ]
                    cells.append("<br/>".join(paragraphs))
                if cells:
                    rows.append(cells)
            if rows:
                blocks.append(("table", rows))
        elif element.tag in {
            f"{ODT_TEXT_NAMESPACE}list",
            f"{ODT_TEXT_NAMESPACE}list-item",
        }:
            blocks.extend(_odt_blocks(element, in_list=True))
    return blocks


def _odt_inline(element: ET.Element) -> str:
    def render(node: ET.Element) -> str:
        if node.tag == f"{ODT_TEXT_NAMESPACE}s":
            count = min(int(node.get(f"{ODT_TEXT_NAMESPACE}c", "1")), 100)
            return "&#160;" * count
        if node.tag == f"{ODT_TEXT_NAMESPACE}tab":
            return "&#160;&#160;&#160;&#160;"
        if node.tag == f"{ODT_TEXT_NAMESPACE}line-break":
            return "<br/>"

        parts = [escape(node.text or "")]
        for child in node:
            parts.append(render(child))
            parts.append(escape(child.tail or ""))
        return "".join(parts)

    return render(element)


def _block_has_content(block: tuple[str, object]) -> bool:
    kind, content = block
    if kind == "table":
        return any(cell.strip() for row in content for cell in row)
    return bool(content.strip())


def _write_document_pdf(blocks: list[tuple[str, object]], output: Path) -> None:
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="DocumentBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        alignment=TA_LEFT,
        spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="DocumentHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        spaceBefore=8,
        spaceAfter=8,
    ))

    content = []
    for kind, value in blocks:
        if kind == "table":
            rows = [
                [Paragraph(cell or " ", styles["DocumentBody"]) for cell in row]
                for row in value
            ]
            table = Table(rows, repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            content.extend((table, Spacer(1, 8)))
        else:
            text = str(value) or " "
            content.append(Paragraph(
                text,
                styles["DocumentHeading" if kind == "heading" else "DocumentBody"],
            ))

    document = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50,
        title=output.stem,
    )
    document.build(content)


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
