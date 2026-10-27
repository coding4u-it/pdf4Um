# Pdf4Um

Pdf4Um is a web workbench for converting JPG/PNG images and DOCX/ODT documents
to PDF, splitting, merging, renaming, protecting, and extracting text from PDF
files. DOCX documents are rendered in the browser and converted to image-based
PDF pages on the user's device; the source document is not uploaded to the
server. This uses pinned libraries loaded from unpkg and respects page breaks
stored in the DOCX. Each rendered page becomes one PDF page using the document's
page dimensions (including standard A4 pages); rendering may still differ from
Microsoft Word. ODT conversion uses ReportLab on the server and preserves text, headings,
paragraphs, lists, and basic tables; page layout and advanced formatting may
differ from the source. Neither conversion requires LibreOffice. The browser
interface is served by a Python Flask backend, which processes server-side
uploads in a temporary workspace and returns the result as a download. Image
conversion creates one A4 page per image in the selected order. Original files
are not modified. Requests are limited to 100 MiB and operations accept up to
32 files.

## Run locally

Requires Python 3.10 or later.

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:8080`. The development server defaults to loopback;
set `HOST` and `PORT` if you need to change the local bind address or port.

Run the Python backend tests with:

```sh
python -m unittest discover -s tests
```

## Deploy on HeliHost

To keep the main website publisher from removing Pdf4Um directories, keep the
application outside `httpdocs` and leave only the WSGI entry point there:

```text
/home/in4matika.helioho.st/
├── httpdocs/
│   ├── index.html                 # Main website
│   └── flask.wsgi                 # Copy from deploy/helihost/flask.wsgi
└── pdf4um/
    ├── app.py
    ├── requirements.txt
    ├── venv/                      # Python packages prepared locally and uploaded
    └── src/main/resources/web/    # Browser assets from the GitHub repository
```

The supplied WSGI file resolves `pdf4um/` as the sibling of `httpdocs/`,
uses `pdf4um-web/` when that folder contains the browser assets or otherwise
uses `src/main/resources/web/`, loads its virtualenv site-packages for the
Python version running mod_wsgi, sets `PDF4UM_WEB_DIRECTORY`, and imports the
Flask application. Keep the `/flask.wsgi/` mapping configured in HeliHost and
restart the Python app after uploading files.

If you do not have shell access on the host, prepare the packages locally on
Ubuntu using the same Python version as mod_wsgi (Python 3.14 in this example).
From the repository root:

```sh
python3.14 -m venv venv
venv/bin/python -m pip install -r requirements.txt
venv/bin/python -c "import reportlab; print('ReportLab', reportlab.Version)"
mkdir -p pdf4um-web
cp src/main/resources/web/{index.html,app.js,styles.css} pdf4um-web/
zip -r -FS pdf4um-deploy.zip \
  app.py requirements.txt \
  venv/lib/python3.14/site-packages \
  pdf4um-web \
  src/main/resources/web
```

Upload `pdf4um-deploy.zip` to the `pdf4um/` directory and extract it there,
overwriting the existing files. The archive must contain
`venv/lib/python3.14/site-packages/reportlab/`; the `reportlab` import error
means this package was missing from the previously uploaded archive. Copy
`deploy/helihost/flask.wsgi` to `httpdocs/flask.wsgi` and restart the Python app.

The archive contains only the virtualenv's `site-packages`, because the WSGI
entry point imports packages from that directory and does not invoke
`venv/bin/python`. It includes the current browser assets in both supported
locations. The WSGI entry point prefers `pdf4um-web/` when present, so updating
only `src/main/resources/web/` leaves an older copy visible. Do not upload
`.venv` from a development machine. The logo is optional and can be uploaded as
`logoinfo.png` beside `app.py` or in the selected web assets folder.

When the Flask application is mounted under a URL prefix such as
`/flask.wsgi/`, open that URL with its trailing slash. The frontend uses
relative asset and API URLs so they remain under the Flask mount instead of
being sent to the main website's root.

The app's `app` object is the production WSGI entry point. `python app.py` is
intended for local development, not as a production server. Before public use,
confirm the hosting upload limit and Python package installation support with
HeliHost. Uploaded PDFs are sent to the server for processing, so use HTTPS
and only publish the service on a plan with suitable resource limits.

## Legacy Java application

The original Java desktop application and Maven files remain in the repository.
They are separate from the Flask website backend; Java is not required to run
the Flask app.
