import requests
import tempfile
from multiprocessing.pool import ThreadPool
from typing import NoReturn, List, Optional
from urllib.parse import urlparse


def download_image(url: str, timeout_ms: int) -> Optional[bytes]:
    try:
        response = requests.get(url, timeout=(timeout_ms * 0.001, timeout_ms * 0.001))
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException:
        return None


def save_image(data: bytes, path: str):
    with open(path, 'wb') as out:
        out.write(data)


def download_and_save_image(url: str, dir_path: str, prefix: str, timeout_ms: int) -> NoReturn:
    data = download_image(url, timeout_ms)
    if not data:
        return

    save_image(data, create_file(url, dir_path, prefix))


def download_images(urls: List[str], num_threads: int) -> List[bytes]:
    with ThreadPool(num_threads) as pool:
        return list(pool.map(download_image, urls))


def download_and_save_images(urls: List[str], dir_path: str, prefix: str,
                             timeout_ms: int, num_threads: int) -> NoReturn:
    def do(url: str):
        return download_and_save_image(url, dir_path, prefix, timeout_ms)

    with ThreadPool(num_threads) as pool:
        list(pool.map(do, urls))


def create_file(url: str, dir_path: str, prefix: str) -> str:
    tokens = urlparse(url).path.split('/')[-1].split('.')
    suffix = ('.' + tokens[-1]) if len(tokens) > 1 else ''
    return tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=dir_path, text=False)[1]
