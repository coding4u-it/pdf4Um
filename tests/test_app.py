import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import pymupdf as fitz
import app as pdf4um_app
from PIL import Image
from docx.shared import Pt, RGBColor
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app import create_app


def make_pdf(page_count: int = 1) -> bytes:
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=300, height=400)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def make_anonymization_pdf() -> bytes:
    document = fitz.open()
    page = document.new_page(width=400, height=220)
    page.insert_text((40, 60), "Email mario@example.com")
    page.insert_text((40, 100), "CF RSSMRA85T10A562S")
    page.insert_text((40, 140), "P.IVA 12345678901")
    document.set_metadata({"author": "Mario Rossi", "title": "Documento privato"})
    output = io.BytesIO()
    document.save(output)
    document.close()
    return output.getvalue()


def make_text_pdf(text: str) -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=400)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    resources = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {NameObject("/F1"): writer._add_object(font)}
            )
        }
    )
    page[NameObject("/Resources")] = writer._add_object(resources)
    content = DecodedStreamObject()
    content.set_data(f"BT /F1 12 Tf 50 700 Td ({text}) Tj ET".encode())
    page[NameObject("/Contents")] = writer._add_object(content)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def make_image(format_name: str, color: str, size: tuple[int, int] = (120, 80)) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", size, color).save(output, format=format_name)
    return output.getvalue()


def make_docx() -> bytes:
    output = io.BytesIO()
    document = pdf4um_app.Document()
    document.add_heading("Titolo documento", level=1)
    document.add_paragraph("Testo di prova")
    cells = document.add_table(rows=1, cols=2).rows[0].cells
    cells[0].text = "Prima colonna"
    cells[1].text = "Seconda colonna"
    document.save(output)
    return output.getvalue()


class PdfWorkbenchTest(unittest.TestCase):
    def setUp(self):
        web_directory = Path(__file__).parents[1] / "src" / "main" / "resources" / "web"
        self.web_directory_patcher = patch.object(pdf4um_app, "WEB_DIRECTORY", web_directory)
        self.web_directory_patcher.start()
        self.addCleanup(self.web_directory_patcher.stop)
        self.client = create_app().test_client()
        self.pdf = make_pdf()

    @staticmethod
    def upload(name: str, content: bytes):
        return (io.BytesIO(content), name)

    def post(self, path: str, data: dict):
        response = self.client.post(
            path, data=data, content_type="multipart/form-data", buffered=True
        )
        self.addCleanup(response.close)
        return response

    def get(self, path: str):
        response = self.client.get(path, buffered=True)
        self.addCleanup(response.close)
        return response

    def zip_names(self, response):
        with zipfile.ZipFile(io.BytesIO(response.data)) as archive:
            return archive.namelist()

    def test_serves_workbench_and_security_headers(self):
        response = self.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"PDF", response.data)
        self.assertIn(b'href="/" aria-label="Torna alla home di In4matika"', response.data)
        self.assertIn(
            b'src="logoinfo.png" alt="In4matika"',
            response.data,
        )
        self.assertIn(b'class="home-link" href="/">Home</a>', response.data)
        self.assertNotIn(b"Chi Siamo", response.data)
        self.assertNotIn(b"Servizi", response.data)
        self.assertNotIn(b"Contattaci", response.data)
        self.assertIn(b'value="images-to-pdf"', response.data)
        self.assertIn(b'value="anonymize"', response.data)
        self.assertIn(b'name="anonymize-category" value="nomi" checked', response.data)
        self.assertIn(b"Converti immagini in PDF", response.data)
        self.assertIn(b'value="docx-to-pdf"', response.data)
        self.assertIn(b'value="pdf-to-docx"', response.data)
        self.assertNotIn(b"ODT", response.data)
        self.assertNotIn(b"ODT in PDF", response.data)
        self.assertNotIn(b"documents-to-pdf", response.data)
        self.assertIn(b"Converti PDF in DOCX", response.data)
        self.assertIn(b"Converti DOCX in PDF", response.data)
        self.assertIn(b"Il documento viene elaborato sul server", response.data)
        self.assertNotIn(b"docx-preview@", response.data)
        self.assertNotIn(b"html2canvas@", response.data)
        self.assertNotIn(b"jspdf@", response.data)
        self.assertIn(b'href="styles.css"', response.data)
        self.assertIn(b'src="app.js"', response.data)
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        javascript = self.get("/app.js")
        self.assertEqual(javascript.status_code, 200)
        self.assertIn(b'fetch("api/"', javascript.data)
        self.assertEqual(self.get("/styles.css").status_code, 200)

    def test_serves_uploaded_logo_from_web_assets_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            logo = Path(directory) / "logoinfo.png"
            logo.write_bytes(b"\x89PNG\r\n\x1a\n")
            with patch.object(pdf4um_app, "WEB_DIRECTORY", Path(directory)):
                response = self.get("/logoinfo.png")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.mimetype, "image/png")
            self.assertEqual(response.data, b"\x89PNG\r\n\x1a\n")

    def test_serves_flat_named_assets_without_overwriting_site_homepage(self):
        with tempfile.TemporaryDirectory() as directory:
            app_directory = Path(directory)
            (app_directory / "index.html").write_text("Main website")
            (app_directory / "pdf4um-index.html").write_text("PDF workbench")
            (app_directory / "pdf4um-app.js").write_text("workbench script")
            (app_directory / "pdf4um-styles.css").write_text("workbench styles")
            (app_directory / "pdf4um-logoinfo.png").write_bytes(b"\x89PNG\r\n\x1a\n")
            with (
                patch.object(pdf4um_app, "APP_DIRECTORY", app_directory),
                patch.object(pdf4um_app, "WEB_DIRECTORY", app_directory / "removed-folder"),
            ):
                page = self.get("/")
                javascript = self.get("/app.js")
                stylesheet = self.get("/styles.css")
                logo = self.get("/logoinfo.png")

            self.assertEqual(page.data, b"PDF workbench")
            self.assertEqual(javascript.data, b"workbench script")
            self.assertEqual(stylesheet.data, b"workbench styles")
            self.assertEqual(logo.data, b"\x89PNG\r\n\x1a\n")

    def test_serves_logo_uploaded_directly_beside_app(self):
        with tempfile.TemporaryDirectory() as directory:
            app_directory = Path(directory)
            (app_directory / "logoinfo.png").write_bytes(b"\x89PNG\r\n\x1a\n")
            with (
                patch.object(pdf4um_app, "APP_DIRECTORY", app_directory),
                patch.object(pdf4um_app, "WEB_DIRECTORY", app_directory / "removed-folder"),
            ):
                response = self.get("/logoinfo.png")

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.mimetype, "image/png")
            self.assertEqual(response.data, b"\x89PNG\r\n\x1a\n")

    def test_prefers_deployed_web_assets_to_legacy_source_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            app_directory = Path(directory)
            deployed_assets = app_directory / "pdf4um-web"
            legacy_assets = app_directory / "src" / "main" / "resources" / "web"
            for assets in (deployed_assets, legacy_assets):
                assets.mkdir(parents=True)
                for filename in ("index.html", "app.js", "styles.css"):
                    (assets / filename).touch()

            resolved = pdf4um_app._resolve_web_directory(app_directory, None)

            self.assertEqual(resolved, deployed_assets)

    def test_workbench_routes_work_when_mounted_under_wsgi_prefix(self):
        environ = {"SCRIPT_NAME": "/flask.wsgi"}
        page = self.client.get("/", environ_overrides=environ, buffered=True)
        self.addCleanup(page.close)
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'href="styles.css"', page.data)

        stylesheet = self.client.get("/styles.css", environ_overrides=environ, buffered=True)
        self.addCleanup(stylesheet.close)
        self.assertEqual(stylesheet.status_code, 200)

    def test_split_and_merge_preserve_page_counts_and_order(self):
        split = self.post(
            "/api/split",
            {"file": self.upload("Report.pdf", make_pdf(3)), "pagesPerPart": "2"},
        )
        self.assertEqual(split.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(split.data)) as archive:
            self.assertEqual(archive.namelist(), ["Report_0001.pdf", "Report_0002.pdf"])
            self.assertEqual(len(PdfReader(io.BytesIO(archive.read("Report_0001.pdf"))).pages), 2)
            self.assertEqual(len(PdfReader(io.BytesIO(archive.read("Report_0002.pdf"))).pages), 1)

        merged = self.post(
            "/api/merge",
            {
                "files": [
                    self.upload("First.pdf", self.pdf),
                    self.upload("Second.pdf", make_pdf(2)),
                ]
            },
        )
        self.assertEqual(merged.status_code, 200)
        self.assertIn("First_merged.pdf", merged.headers["Content-Disposition"])
        self.assertEqual(len(PdfReader(io.BytesIO(merged.data)).pages), 3)

    def test_converts_multiple_jpg_and_png_images_to_a4_pdf_in_order(self):
        response = self.post(
            "/api/images-to-pdf",
            {
                "images": [
                    self.upload("first.jpg", make_image("JPEG", "red")),
                    self.upload("second.png", make_image("PNG", "blue")),
                ]
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/pdf")
        self.assertIn("immagini.pdf", response.headers["Content-Disposition"])
        reader = PdfReader(io.BytesIO(response.data))
        self.assertEqual(len(reader.pages), 2)
        for index, page in enumerate(reader.pages):
            self.assertAlmostEqual(float(page.mediabox.width), 595.27, places=1)
            self.assertAlmostEqual(float(page.mediabox.height), 841.89, places=1)
            self.assertTrue(page.images)
            pixel = page.images[0].image.convert("RGB").getpixel((0, 0))
            if index == 0:
                self.assertGreater(pixel[0], pixel[2])
            else:
                self.assertGreater(pixel[2], pixel[0])

    def test_image_conversion_rejects_unsupported_and_unreadable_files(self):
        unsupported = self.post(
            "/api/images-to-pdf",
            {"images": self.upload("animation.gif", b"not an image")},
        )
        self.assertEqual(unsupported.status_code, 415)

        unreadable = self.post(
            "/api/images-to-pdf",
            {"images": self.upload("broken.png", b"not a PNG")},
        )
        self.assertEqual(unreadable.status_code, 422)

    def test_converts_docx_to_pdf(self):
        response = self.post(
            "/api/docx-to-pdf",
            {"file": self.upload("Report.docx", make_docx())},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/pdf")
        self.assertIn("Report.pdf", response.headers["Content-Disposition"])
        reader = PdfReader(io.BytesIO(response.data))
        self.assertGreaterEqual(len(reader.pages), 1)
        extracted_text = "\n".join(page.extract_text() or "" for page in reader.pages)
        self.assertIn("Titolo documento", extracted_text)
        self.assertIn("Testo di prova", extracted_text)
        self.assertIn("Prima colonna", extracted_text)
        self.assertIn("Seconda colonna", extracted_text)

    def test_docx_conversion_preserves_run_font_sizes_and_emphasis(self):
        document = pdf4um_app.Document()
        title = document.add_paragraph()
        title_run = title.add_run("Titolo personalizzato")
        title_run.font.size = Pt(28)
        title_run.bold = True
        title_run.font.name = "Arial"
        title_run.font.color.rgb = RGBColor(0x12, 0x34, 0x56)
        body = document.add_paragraph()
        body_run = body.add_run("Testo personalizzato")
        body_run.font.size = Pt(9)
        body_run.italic = True

        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            source = workspace / "styles.docx"
            document.save(source)
            html, css = pdf4um_app._docx_to_html(source)
            output = pdf4um_app._docx_to_pdf(source, workspace)

            page = PdfReader(output).pages[0]
            styled_runs = {}

            def record_run(text, _cm, _tm, font, font_size):
                if text.strip():
                    styled_runs[text.strip()] = (font_size, str(font.get("/BaseFont")))

            page.extract_text(visitor_text=record_run)

        self.assertIn('font-family: "Helvetica"', css)
        self.assertIn("font-size: 28pt", css)
        self.assertIn("color: #123456", css)
        self.assertAlmostEqual(styled_runs["Titolo personalizzato"][0], 28)
        self.assertIn("Bold", styled_runs["Titolo personalizzato"][1])
        self.assertAlmostEqual(styled_runs["Testo personalizzato"][0], 9)
        self.assertIn("Oblique", styled_runs["Testo personalizzato"][1])

    def test_docx_conversion_preserves_heading_style(self):
        document = pdf4um_app.Document()
        heading = document.add_heading("Heading style preserved", level=1)
        heading.style.font.size = Pt(26)

        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            source = workspace / "heading.docx"
            document.save(source)
            html, css = pdf4um_app._docx_to_html(source)
            output = pdf4um_app._docx_to_pdf(source, workspace)

            text_runs = []
            PdfReader(output).pages[0].extract_text(
                visitor_text=lambda text, _cm, _tm, _font, size:
                    text_runs.append((text, size)) if text.strip() else None
            )

        self.assertIn('<h1 class="pdf4um-paragraph-0"', html)
        self.assertIn("font-size: 26pt", css)
        self.assertTrue(any("Heading style preserved" in text and size == 26 for text, size in text_runs))

    def test_docx_conversion_preserves_parenthesized_list_markers(self):
        html = pdf4um_app._DocxListMarkerFormatter([1]).format(
            "<ol><li>Primo elemento</li><li>Secondo elemento</li></ol>"
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "numbering.pdf"
            pdf4um_app._html_to_pdf(
                html,
                ".pdf4um-custom-numbering { list-style-type: none; }",
                output,
            )
            text = PdfReader(output).pages[0].extract_text()

        self.assertIn("1) Primo elemento", text)
        self.assertIn("2) Secondo elemento", text)

    def test_pdf_to_docx_extracts_text_and_preserves_page_breaks(self):
        source = fitz.open()
        first_page = source.new_page()
        first_page.insert_text((50, 80), "Titolo da PDF", fontname="hebo", fontsize=18)
        first_page.insert_text((50, 110), "Testo modificabile", fontsize=12)
        second_page = source.new_page()
        second_page.insert_text((50, 80), "Seconda pagina", fontsize=12)
        pdf_bytes = source.tobytes()
        source.close()

        response = self.post(
            "/api/pdf-to-docx",
            {"file": self.upload("Report.pdf", pdf_bytes)},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.mimetype,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        self.assertIn("Report.docx", response.headers["Content-Disposition"])
        converted = pdf4um_app.Document(io.BytesIO(response.data))
        self.assertEqual(
            [paragraph.text for paragraph in converted.paragraphs if paragraph.text],
            ["Titolo da PDF", "Testo modificabile", "Seconda pagina"],
        )
        self.assertTrue(converted.paragraphs[0].runs[0].bold)
        self.assertTrue(any(
            br.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}type") == "page"
            for br in converted._element.body.iter(
                "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}br"
            )
        ))

    def test_pdf_to_docx_rejects_invalid_and_scanned_pdfs(self):
        invalid = self.post(
            "/api/pdf-to-docx",
            {"file": self.upload("invalid.pdf", b"not a PDF")},
        )
        self.assertEqual(invalid.status_code, 422)

        no_text = self.post(
            "/api/pdf-to-docx",
            {"file": self.upload("scan.pdf", self.pdf)},
        )
        self.assertEqual(no_text.status_code, 422)
        self.assertIn("no extractable text", no_text.json["error"])

    def test_docx_conversion_rejects_unsupported_and_invalid_files(self):
        unsupported = self.post(
            "/api/docx-to-pdf",
            {"file": self.upload("report.odt", b"not supported")},
        )
        self.assertEqual(unsupported.status_code, 415)

        removed_odt_api = self.post(
            "/api/documents-to-pdf",
            {"file": self.upload("report.odt", b"not supported")},
        )
        self.assertEqual(removed_odt_api.status_code, 404)

        invalid = self.post(
            "/api/docx-to-pdf",
            {"file": self.upload("report.docx", b"not a DOCX archive")},
        )
        self.assertEqual(invalid.status_code, 422)

    def test_rename_sequential_and_random(self):
        sequential = self.post(
            "/api/rename",
            {
                "files": [self.upload("First.pdf", self.pdf), self.upload("Second.pdf", self.pdf)],
                "mode": "sequential",
                "prefix": "Chapter-",
                "startingNumber": "4",
            },
        )
        self.assertEqual(sequential.status_code, 200)
        self.assertEqual(self.zip_names(sequential), ["Chapter-4.pdf", "Chapter-5.pdf"])

        random_result = self.post(
            "/api/rename",
            {
                "files": self.upload("First.pdf", self.pdf),
                "mode": "random",
                "codeLength": "8",
                "useSymbols": "false",
            },
        )
        self.assertEqual(random_result.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(random_result.data)) as archive:
            self.assertIn("esporta.csv", archive.namelist())
            self.assertRegex(archive.read("esporta.csv").decode(), r"(?s)\.pdf;\d{8}\n")

    def test_encryption_and_text_download(self):
        encrypted = self.post(
            "/api/encrypt",
            {
                "files": self.upload("Report.pdf", self.pdf),
                "password": "test-password",
                "allowOpen": "false",
            },
        )
        self.assertEqual(encrypted.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(encrypted.data)) as archive:
            reader = PdfReader(io.BytesIO(archive.read("Report_cript.pdf")))
            self.assertTrue(reader.is_encrypted)
            self.assertTrue(reader.decrypt("test-password"))

        extracted = self.post(
            "/api/extract-text",
            {"file": self.upload("Notes.pdf", make_text_pdf("EXTRACTED TEXT"))},
        )
        self.assertEqual(extracted.status_code, 200)
        self.assertEqual(extracted.mimetype, "text/plain")
        self.assertIn("Notes_text.txt", extracted.headers["Content-Disposition"])
        self.assertIn(b"EXTRACTED TEXT", extracted.data)

    def test_anonymization_preview_and_irreversible_redaction(self):
        source = make_anonymization_pdf()
        preview = self.post(
            "/api/anonymize-preview",
            {
                "file": self.upload("Private.pdf", source),
                "categories": json.dumps(["email", "codice-fiscale", "partita-iva"]),
                "terms": "Mario",
            },
        )
        self.assertEqual(preview.status_code, 200)
        result = json.loads(preview.data)
        self.assertEqual(len(result["pages"]), 1)
        self.assertTrue(result["pages"][0]["image"])
        self.assertTrue(result["hasExtractableText"])
        categories = {suggestion["category"] for suggestion in result["suggestions"]}
        self.assertTrue({"email", "codice-fiscale", "partita-iva", "testo"}.issubset(categories))
        email = next(item for item in result["suggestions"] if item["category"] == "email")

        anonymized = self.post(
            "/api/anonymize",
            {
                "file": self.upload("Private.pdf", source),
                "areas": json.dumps([{
                    key: email[key] for key in ("page", "x0", "y0", "x1", "y1")
                }]),
            },
        )
        self.assertEqual(anonymized.status_code, 200)
        self.assertEqual(anonymized.mimetype, "application/pdf")
        document = fitz.open(stream=anonymized.data, filetype="pdf")
        self.addCleanup(document.close)
        text = document[0].get_text()
        self.assertNotIn("mario@example.com", text)
        self.assertIn("RSSMRA85T10A562S", text)
        self.assertEqual(document.metadata["author"], "")
        self.assertEqual(document.metadata["title"], "")
        self.assertEqual(document.embfile_count(), 0)

        metadata_only = self.post(
            "/api/anonymize",
            {
                "file": self.upload("Private.pdf", source),
                "areas": "[]",
            },
        )
        self.assertEqual(metadata_only.status_code, 200)
        metadata_document = fitz.open(stream=metadata_only.data, filetype="pdf")
        self.addCleanup(metadata_document.close)
        self.assertEqual(metadata_document.metadata["author"], "")
        self.assertIn("mario@example.com", metadata_document[0].get_text())

    def test_anonymization_preview_identifies_scanned_pdf_without_text(self):
        image = Image.new("RGB", (240, 120), "white")
        image_bytes = io.BytesIO()
        image.save(image_bytes, format="PNG")
        document = fitz.open()
        page = document.new_page(width=400, height=220)
        page.insert_image(page.rect, stream=image_bytes.getvalue())
        source = io.BytesIO()
        document.save(source)
        document.close()

        response = self.post(
            "/api/anonymize-preview",
            {
                "file": self.upload("Scanned.pdf", source.getvalue()),
                "categories": json.dumps(["email", "telefono"]),
                "terms": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        result = json.loads(response.data)
        self.assertFalse(result["hasExtractableText"])
        self.assertEqual(result["suggestions"], [])
        self.assertTrue(result["pages"][0]["image"])

    def test_anonymization_phone_matching_avoids_dates_and_finds_names(self):
        source_document = fitz.open()
        page = source_document.new_page(width=500, height=400)
        page.insert_text((30, 40), "Telefono 333 123 4567")
        page.insert_text((30, 80), "Ufficio 02 1234 5678")
        page.insert_text((30, 120), "D.Lgs. 33/2013")
        page.insert_text((30, 160), "Decreto 2023 2024 2025")
        page.insert_text((30, 200), "Data 01.02.2023")
        page.insert_text((30, 240), "Data 12/03/2024")
        page.insert_text((30, 280), "MARIO ROSSI")
        page.insert_text((30, 320), "Maria Chiara Bianchi")
        source = io.BytesIO()
        source_document.save(source)
        source_document.close()

        response = self.post(
            "/api/anonymize-preview",
            {
                "file": self.upload("Names-and-numbers.pdf", source.getvalue()),
                "categories": json.dumps(["telefono", "nomi"]),
                "terms": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        suggestions = json.loads(response.data)["suggestions"]
        phones = {item["text"] for item in suggestions if item["category"] == "telefono"}
        names = {item["text"] for item in suggestions if item["category"] == "nomi"}
        self.assertEqual(phones, {"333 123 4567", "02 1234 5678"})
        self.assertEqual(names, {"MARIO ROSSI", "Maria Chiara Bianchi"})

    def test_anonymization_rejects_invalid_categories_and_redaction_areas(self):
        invalid_categories = self.post(
            "/api/anonymize-preview",
            {
                "file": self.upload("Private.pdf", make_anonymization_pdf()),
                "categories": json.dumps(["unknown"]),
                "terms": "",
            },
        )
        self.assertEqual(invalid_categories.status_code, 400)

        invalid_area = self.post(
            "/api/anonymize",
            {
                "file": self.upload("Private.pdf", make_anonymization_pdf()),
                "areas": json.dumps([{
                    "page": 2, "x0": 0.1, "y0": 0.1, "x1": 0.3, "y1": 0.3,
                }]),
            },
        )
        self.assertEqual(invalid_area.status_code, 400)

    def test_anonymization_redacts_manual_areas_on_rotated_pages(self):
        source_document = fitz.open()
        page = source_document.new_page(width=400, height=220)
        page.insert_text((40, 80), "REMOVE-ME")
        page.set_rotation(90)
        source_stream = io.BytesIO()
        source_document.save(source_stream)
        source_document.close()
        source = source_stream.getvalue()

        preview = self.post(
            "/api/anonymize-preview",
            {
                "file": self.upload("Rotated.pdf", source),
                "categories": "[]",
                "terms": "REMOVE-ME",
            },
        )
        self.assertEqual(preview.status_code, 200)
        area = json.loads(preview.data)["suggestions"][0]
        anonymized = self.post(
            "/api/anonymize",
            {
                "file": self.upload("Rotated.pdf", source),
                "areas": json.dumps([{
                    key: area[key] for key in ("page", "x0", "y0", "x1", "y1")
                }]),
            },
        )
        self.assertEqual(anonymized.status_code, 200)
        output_document = fitz.open(stream=anonymized.data, filetype="pdf")
        self.addCleanup(output_document.close)
        self.assertNotIn("REMOVE-ME", output_document[0].get_text())

    def test_rejects_invalid_uploads_and_unknown_routes_as_json(self):
        too_few = self.post(
            "/api/merge",
            {"files": self.upload("Report.pdf", self.pdf)},
        )
        self.assertEqual(too_few.status_code, 400)
        self.assertIn("error", json.loads(too_few.data))

        unsupported = self.post(
            "/api/split",
            {"file": self.upload("image.png", b"not a PDF")},
        )
        self.assertEqual(unsupported.status_code, 415)

        unreadable = self.post(
            "/api/extract-text",
            {"file": self.upload("broken.pdf", b"not a PDF")},
        )
        self.assertEqual(unreadable.status_code, 422)

        unknown = self.get("/api/unknown")
        self.assertEqual(unknown.status_code, 404)
        self.assertEqual(unknown.mimetype, "application/json")


if __name__ == "__main__":
    unittest.main()
