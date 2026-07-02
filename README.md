# Satellite Imagery Web Application

A production-ready **Satellite Imagery Explorer** built with Python, Streamlit, and Google Earth Engine. Search any location, visualize Sentinel-2 and Landsat imagery, compute spectral indices (NDVI, NDWI, SAVI, EVI), draw regions of interest, compare before/after scenes, generate time-lapses, and export PNG, JPEG, or GeoTIFF files.

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-red.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Features

- **Google Earth Engine** authentication with graceful error handling
- **Interactive full-screen map** with Satellite, Terrain, and OpenStreetMap basemaps
- **Location search** — cities, addresses, countries, or coordinates
- **Sentinel-2 & Landsat** imagery with date range and cloud filters
- **Visualizations** — True Color, False Color, NDVI, NDWI, SAVI, EVI
- **Drawing tools** — point, polygon, rectangle with area calculation and GeoJSON export
- **Time series** — before/after comparison slider and GIF time-lapse
- **Downloads** — PNG, JPEG, GeoTIFF
- **Statistics** — mean/max/min NDVI, vegetation %, water %
- **Modern UI** — sidebar controls, dark/light mode, loading indicators

## Quick Start

### Prerequisites

- Python 3.12 or newer
- A [Google Earth Engine](https://signup.earthengine.google.com/) account
- A Google Cloud project with Earth Engine API enabled

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/satellite-imagery-app.git
cd satellite-imagery-app

# Create virtual environment
python -m venv venv

# Activate (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Activate (Linux/macOS)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Earth Engine Authentication

```bash
# Authenticate (opens browser)
earthengine authenticate

# Set your Google Cloud project ID
# Windows PowerShell:
$env:EE_PROJECT = "your-gcp-project-id"

# Linux/macOS:
export EE_PROJECT="your-gcp-project-id"
```

### Run the Application

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

## Project Structure

```
satellite-imagery-app/
├── app.py                      # Streamlit entry point
├── requirements.txt
├── LICENSE
├── README.md
├── .streamlit/
│   ├── config.toml             # Streamlit theme & server config
│   └── secrets.toml.example    # Cloud deployment secrets template
├── assets/                     # Static assets
├── docs/
│   ├── installation.md
│   ├── user_guide.md
│   ├── developer_guide.md
│   └── api.md
├── exports/                    # Downloaded files (auto-created)
├── src/
│   └── satellite_app/
│       ├── config/             # Settings and constants
│       ├── services/           # EE auth, imagery, geocoding
│       ├── processing/         # Indices and composites
│       ├── map/                # Folium map and drawing tools
│       ├── downloads/          # Export service
│       ├── ui/                 # Streamlit UI components
│       └── utils/              # Helpers and logging
└── tests/                      # Unit tests
```

## Deployment (Streamlit Community Cloud)

1. Push this repository to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) and create a new app
3. Set **Main file path** to `app.py`
4. Add secrets (Settings → Secrets) using `.streamlit/secrets.toml.example` as a template:

```toml
EE_PROJECT = "your-gcp-project-id"
EE_SERVICE_ACCOUNT = "your-sa@project.iam.gserviceaccount.com"
EE_PRIVATE_KEY_DATA = '''{"type": "service_account", ...}'''
```

5. Deploy — the app uses `requirements.txt` automatically

See [docs/installation.md](docs/installation.md) for detailed deployment steps.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `EE_PROJECT` | Google Cloud project ID |
| `EE_SERVICE_ACCOUNT` | Service account email (cloud deployment) |
| `EE_PRIVATE_KEY_PATH` | Path to service account JSON key file |
| `EE_PRIVATE_KEY_DATA` | Service account JSON as string (Streamlit secrets) |
| `LOG_LEVEL` | Logging level (default: `INFO`) |
| `EXPORTS_DIR` | Directory for exported files (default: `./exports`) |

## Running Tests

```bash
pip install pytest
pytest
```

## Documentation

- [Installation Guide](docs/installation.md)
- [User Guide](docs/user_guide.md)
- [Developer Guide](docs/developer_guide.md)
- [API Documentation](docs/api.md)

## License

MIT License — see [LICENSE](LICENSE).

## Acknowledgments

- [Google Earth Engine](https://earthengine.google.com/)
- [Streamlit](https://streamlit.io/)
- [geemap](https://geemap.org/)
- [OpenStreetMap Nominatim](https://nominatim.org/)
