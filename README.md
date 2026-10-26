# Pdf4Um

Pdf4Um is a web workbench for converting JPG/PNG images to PDF, splitting,
merging, renaming, protecting, and extracting text from PDF files. The browser
interface is served by a Python Flask backend, which processes uploads in a
temporary workspace and returns the result as a download. Image conversion
creates one A4 page per image in the selected order. Original files are not
modified. Requests are limited to 100 MiB and operations accept up to 32 files.

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
    ├── venv/                      # Created on the host
    └── src/main/resources/web/    # Browser assets from the GitHub repository
```

The supplied WSGI file resolves `pdf4um/` as the sibling of `httpdocs/`,
uses `pdf4um-web/` when that folder contains the browser assets or otherwise
uses `src/main/resources/web/`, loads its virtualenv site-packages for the
Python version running mod_wsgi, sets `PDF4UM_WEB_DIRECTORY`, and imports the
Flask application. Keep the `/flask.wsgi/` mapping configured in HeliHost and
restart the Python app after uploading files.

Create the virtualenv on HeliHost using the exact Python version selected for
the WSGI application, then install the requirements from the application
directory. For example, if mod_wsgi uses Python 3.14:

```sh
cd /home/in4matika.helioho.st/pdf4um
python3.14 -m venv venv
venv/bin/python -m pip install -r requirements.txt
```

Upload the repository into `pdf4um/` with the `src/main/resources/web/` folder
intact. Alternatively, copy `index.html`, `app.js`, and `styles.css` into
`pdf4um/pdf4um-web/`; that folder takes precedence when present. The logo is
optional and can be uploaded as `logoinfo.png` beside `app.py` or in the
selected web assets folder. Do not upload the local `.venv` from a development
machine; create the virtualenv on the host.

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
