import requests
import logging
import os
from typing import TypedDict
import subprocess
from pathlib import Path
import sys

logger = logging.getLogger(__name__)

class Resource(TypedDict):
  url: str
  path: str

def run_upstream_script() -> None:
  renew_data_path = Path('scripts/renewdata-assets.py')

  if renew_data_path.is_file():
    logger.info('Renewing data assets...')
    process = subprocess.Popen(
      [sys.executable, "renewdata-assets.py"],
      cwd=os.path.abspath('scripts'),
      stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT,
      text=True,
      bufsize=1,
      universal_newlines=True
    )

    if process.stdout:
      for line in process.stdout:
        logger.info(line.strip())

    process.wait()
  else:
    logger.error('Renew data script does not exist')


def sync_tools_and_data() -> None:
  base_url: str = 'https://raw.githubusercontent.com/Eskuero/fehbuilder/master/'
  renew_data: Resource = {'url': 'scripts/renewdata-assets.py', 'path': 'scripts/renewdata-assets.py'}
  utils: Resource = {'url': 'scripts/utils.py', 'path': 'scripts/utils.py'}
  full_units: Resource = {'url': 'data/content/fullunits.json', 'path': 'data/content/fullunits.json'}
  full_langs: Resource = {'url': 'data/languages/fulllanguages.json', 'path': 'data/languages/fulllanguages.json'}
  full_skills: Resource = {'url': 'data/content/fullskills.json', 'path': 'data/content/fullskills.json'}

  files_to_dl: list[Resource] = [renew_data, utils, full_units, full_langs, full_skills]

  create_folder_structure()

  for file in files_to_dl:
    try:
      with open(file['path'], 'w') as f:
        r = requests.get(base_url + file['url'])
        if r.status_code == 200:
          logger.info(f'Successfully downloaded {file["url"]}')
          f.write(r.text)
          logger.info(f'Successfully wrote {file["path"]}')
    except Exception:
      logger.exception('Failed to create/update {file["path"]}')

def create_folder_structure() -> None:
  dirs_to_create: list[str] = [
    'scripts',
    'data',
    'data/content',
    'data/languages'
  ]

  for dir in dirs_to_create:
    logger.info(f'Ensuring {dir} exists...')
    os.makedirs(dir, exist_ok=True)
