# Pdf4Um

Pdf4Um is a web workbench for splitting, merging, renaming, protecting, and
extracting text from PDF files. The browser interface is served by a Python
Flask backend, which processes uploads in a temporary workspace and returns
the result as a download. Original files are not modified. Requests are limited
to 100 MiB and multi-file operations accept up to 32 PDFs.

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

Use the Python/Flask application option in the hosting control panel if it is
available for your account. Upload the project files (including `app.py`,
`requirements.txt`, `tests/`, and `src/main/resources/web/`) to the configured
application root, install the packages from `requirements.txt`, and configure
the WSGI entry point as `app:app` if the panel asks for a module and variable.
Follow HeliHost's current instructions for selecting the Python version,
application root, and startup/restart action; those settings are account- and
panel-specific. Do not expose the project directory as a browsable document
root: the Flask app serves only the workbench assets and API routes.

The app's `app` object is the production WSGI entry point. `python app.py` is
intended for local development, not as a production server. Before public use,
confirm the hosting upload limit and Python package installation support with
HeliHost. Uploaded PDFs are sent to the server for processing, so use HTTPS
and only publish the service on a plan with suitable resource limits.

## Legacy Java application

The original Java desktop application and Maven files remain in the repository.
They are separate from the Flask website backend; Java is not required to run
the Flask app.
