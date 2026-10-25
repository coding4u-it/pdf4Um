import io
import json
import unittest
import zipfile

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


class PdfWorkbenchTest(unittest.TestCase):
    def setUp(self):
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
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(self.get("/app.js").status_code, 200)
        self.assertEqual(self.get("/styles.css").status_code, 200)

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
