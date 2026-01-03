import json
import pathlib
import io
from typing import Any, Optional, Callable
import logging
from helpers import get_english_name

import requests
from PIL import Image
import scripts.utils as utils

logger = logging.getLogger(__name__)
# ==========================================
# Configuration & Constants
# ==========================================

DATA_DIR = pathlib.Path("./data")
CONTENT_DIR = DATA_DIR / "content"
LANG_DIR = DATA_DIR / "languages"
IMG_DIR = DATA_DIR / "img"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# ==========================================
# Data Structures
# ==========================================

class ImageRequest:
    """Simple container for an image download job."""
    def __init__(self, item_id: str, local_filename: str, wiki_filename: str):
        self.item_id = item_id
        self.local_filename = local_filename
        self.wiki_filename = wiki_filename

# ==========================================
# Helper Functions
# ==========================================

def load_json(path: pathlib.Path) -> Any:
    """Safely loads a JSON file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f'Could not find file at {path}')
        return {}

def ensure_dir(path: pathlib.Path):
    """Creates the directory if it doesn't exist."""
    path.mkdir(parents=True, exist_ok=True)

# ==========================================
# Core Downloading Logic
# ==========================================

def download_and_process_batch(
    category_name: str,
    requests_list: list[ImageRequest],
    output_dir: pathlib.Path,
    resize_logic: Optional[Callable[[Image.Image], Image.Image]] = None,
    save_kwargs: Optional[dict[str, Any]] = None,
    english_names: Optional[dict[str, str]] = None
):
    """
    Generic processor that downloads, processes, and saves images.
    """
    if not requests_list:
        logger.info(f"{category_name}: Up to date.")
        return

    ensure_dir(output_dir)
    save_kwargs = save_kwargs or {}

    logger.info(f"Downloading {category_name} ({len(requests_list)} items)...")

    # Process in batches of 50 (Wiki API limit)
    batch_size = 50
    for i in range(0, len(requests_list), batch_size):
        batch = requests_list[i : i + batch_size]

        # 1. Get URLs for the wiki filenames
        wiki_filenames = [req.wiki_filename for req in batch]
        urls: list[bool | str] = utils.obtaintrueurl(wiki_filenames) # pyright: ignore[reportUnknownMemberType, reportAssignmentType]

        # 2. Iterate through results
        for idx, url in enumerate(urls):
            req = batch[idx]
            display_name = english_names.get("M" + req.item_id, req.item_id) if english_names else req.item_id

            if not url or not isinstance(url, str) or not url.startswith("http"): # type: ignore
                logger.warning(f"{display_name}: Could not find URL for '{req.wiki_filename}'")
                continue

            # 3. Download and Process
            try:
                response = requests.get(url, headers=HEADERS, timeout=10)
                response.raise_for_status()

                img_data = io.BytesIO(response.content)
                with Image.open(img_data) as img:

                    # Resize if a logic function is provided
                    if resize_logic:
                        img = resize_logic(img)

                    # Save
                    out_path = output_dir / req.local_filename
                    img.save(out_path, **save_kwargs)
                    logger.info(f"{display_name}: Downloaded.")

            except Exception:
                logger.exception(f"{display_name}: Failed to download.")

# ==========================================
# Face Processing Logic
# ==========================================

def process_faces_only(units: dict[str, dict[str, Any]], english_names: dict[str, str]):
    """
    Gathers and downloads only the base face assets (Face_FC) at original resolution.
    """

    def gather_faces_requests(target_folder: str, suffixes: dict[str, str]) -> list[ImageRequest]:
        """
        Helper to generate download requests for a specific folder and suffix map.
        """
        reqs: list[ImageRequest] = []
        folder_path = IMG_DIR / target_folder

        for u_id, u_data in units.items():
            true_name = get_english_name(u_id, english_names)

            # Enemy logic: Generally only bosses have face crops
            is_enemy = "EID_" in u_id and not u_data.get("boss")
            if is_enemy:
                continue

            # Resplendent check
            is_resplendent = english_names.get(u_id.replace("PID", "MPID_VOICE") + "EX01", False)

            # Create a sanitized filename from the English name (e.g., "Marth Hero-King")
            # This replaces invalid chars like ":" with empty space to prevent file system errors
            safe_filename: str = true_name.replace(":", "").replace("?", "").replace('"', "").replace("/", "")

            # Map Local Filename Suffix -> Wiki Filename Suffix
            final_map: dict[str, str] = {}

            # 1. Standard Faces
            for local_suffix, wiki_fmt in suffixes.items():
                final_map[local_suffix] = wiki_fmt.format(name=true_name)

            # 2. Resplendent Faces
            if is_resplendent:
                final_map["_Resplendent.webp"] = f"{true_name}_Resplendent_Face_FC.webp"

            # Check if file exists, if not, add to download list
            for local_suffix, wiki_name in final_map.items():
                local_file = safe_filename + local_suffix
                if not (folder_path / local_file).is_file():
                    reqs.append(ImageRequest(u_id, local_file, wiki_name))

        return reqs

    # --- Unit Faces (Original Size) ---
    download_and_process_batch(
        "Unit Faces",
        gather_faces_requests("faces", {".webp": "{name}_Face_FC.webp"}),
        IMG_DIR / "faces",
        resize_logic=None, # Keep original size
        save_kwargs={'format': 'WEBP', 'lossless': True, 'quality': 100, 'method': 6},
        english_names=english_names
    )

# ==========================================
# Main Entry Point
# ==========================================

def main():
    logger.info("Initializing Unit Face Downloader...")

    # Load Data
    units = load_json(CONTENT_DIR / "fullunits.json")
    languages = load_json(LANG_DIR / "fulllanguages.json")

    if not units or not languages:
        logger.error("Failed to load required JSON data files. Exiting.")
        return

    english_names = languages.get("USEN", {})

    # Run Processor
    process_faces_only(units, english_names)

    logger.info("Face download tasks completed.")
