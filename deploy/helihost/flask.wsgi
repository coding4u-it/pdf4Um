import os
import site
import sys
from pathlib import Path


HTTPDOCS = Path(__file__).resolve().parent
PROJECT_ROOT = (HTTPDOCS.parent / "pdf4um").resolve()
VIRTUAL_ENV = PROJECT_ROOT / "venv"
WEB_DIRECTORIES = (
    PROJECT_ROOT / "pdf4um-web",
    PROJECT_ROOT / "src" / "main" / "resources" / "web",
)

app_module = PROJECT_ROOT / "app.py"
if not app_module.is_file():
    raise RuntimeError(f"Pdf4Um app.py was not found at {app_module}")

required_assets = ("index.html", "app.js", "styles.css")
WEB_DIRECTORY = next(
    (
        directory
        for directory in WEB_DIRECTORIES
        if all((directory / name).is_file() for name in required_assets)
    ),
    None,
)
if WEB_DIRECTORY is None:
    searched_directories = ", ".join(str(directory) for directory in WEB_DIRECTORIES)
    raise RuntimeError(
        "Pdf4Um web assets were not found. Expected index.html, app.js, and "
        f"styles.css in one of: {searched_directories}"
    )

site_packages = VIRTUAL_ENV / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
if not site_packages.is_dir():
    raise RuntimeError(
        f"Python packages were not found at {site_packages}. "
        "Create this virtualenv with the same Python version used by mod_wsgi "
        "and install requirements.txt into it."
    )

sys.path.insert(0, str(PROJECT_ROOT))
site.addsitedir(str(site_packages))
os.environ["PDF4UM_WEB_DIRECTORY"] = str(WEB_DIRECTORY)

from app import app as application
