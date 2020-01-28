import argparse
import inspect
import json
import os
from typing import NoReturn, List, Optional

from download import create_file, download_and_save_images
from search_page import create_chrome_driver, get_image_infos, Config, \
    Env, Query, default_env, default_logger, default_config, ImageInfo


GENERAL_DESCRIPTION = """
Scrap Yandex search images pages and:
* download fullsize images
* download thumbnails
* store urls for later downloading

Tool mode terms:
* scrap-and-download: all on one; scrap and download fullsize images
* only-scrap: just get the search page, save thumbnails and urls
* download-scrapped: use 'only-scrap' output to download fullsize images
* one: a single search query
* many: a list of search queries

"""


def get_args_and_call(func, args):
    func(**{name: getattr(args, name) for name in inspect.getfullargspec(func)[0]})


def save_thumbs(image_infos: List[ImageInfo], dir_path: Optional[str], prefix: str) -> NoReturn:
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)
        for info in image_infos:
            with open(create_file('some.png', dir_path, prefix), 'wb') as out:
                out.write(info.thumb_png)


def read_lines(path: str) -> List[str]:
    with open(path, 'r') as in_:
        return [line.strip() for line in in_ if line.strip()]


def write_lines(path: Optional[str], lines: List[str]) -> NoReturn:
    if path:
        with open(path, 'w') as out:
            out.write('\n'.join(lines))


def save_json(data, path: Optional[str]) -> NoReturn:
    if path:
        with open(path, 'w') as out:
            json.dump(data, out, indent=2, sort_keys=True, ensure_ascii=False)


def only_scrap_one(
    text: str,
    min_width: int,
    min_height: int,
    white: bool,
    num_images: int,
    urls_file: str,
    thumbs_dir: str,
    thumbs_prefix: str
):
    driver = create_chrome_driver()
    image_infos = get_image_infos(
        driver=driver,
        env=default_env,
        query=Query(text, min_width, min_height, white),
        num_images=num_images,
        with_thumbs=bool(thumbs_dir)
    )

    write_lines(urls_file, [info.url for info in image_infos])
    save_thumbs(image_infos, thumbs_dir, thumbs_prefix)


def only_scrap_many(
    texts_file: str,
    min_width: int,
    min_height: int,
    white: bool,
    num_images: int,
    report_file: str,
    thumbs_dir: str,
    thumbs_prefix: str
):
    driver = create_chrome_driver()
    texts = read_lines(texts_file)
    text_to_urls = {}
    for text in texts:
        image_infos = get_image_infos(
            driver=driver,
            env=default_env,
            query=Query(text, min_width, min_height, white),
            num_images=num_images,
            with_thumbs=bool(thumbs_dir)
        )

        text_to_urls[text] = [info.url for info in image_infos]
        save_thumbs(image_infos, os.path.join(thumbs_dir, text) if thumbs_dir else None, thumbs_prefix)

    save_json({
        'min_height': min_height,
        'min_width': min_width,
        'white': white,
        'text_to_urls': text_to_urls
    }, report_file)


def download_scrapped_one(
    urls_file: str,
    images_dir: str,
    images_prefix: str,
    timeout_ms: int,
    num_threads: int,
):
    os.makedirs(images_dir, exist_ok=True)
    download_and_save_images(
        urls=read_lines(urls_file),
        dir_path=images_dir,
        prefix=images_prefix,
        timeout_ms=timeout_ms,
        num_threads=num_threads
    )


def download_scrapped_many(
    report_file: str,
    images_dir: str,
    images_prefix: str,
    timeout_ms: int,
    num_threads: int,
):
    with open(report_file, 'r') as in_:
        report = json.load(in_)

    for text, urls in report['text_to_urls'].items():
        images_subdir = os.path.join(images_dir, text)
        os.makedirs(images_subdir, exist_ok=True)
        download_and_save_images(
            urls=urls,
            dir_path=images_subdir,
            prefix=images_prefix,
            timeout_ms=timeout_ms,
            num_threads=num_threads
        )


def scrap_and_download_one(
    text: str,
    min_width: int,
    min_height: int,
    white: bool,
    num_images: int,
    images_dir: str,
    images_prefix: str,
    timeout_ms: int,
    num_threads: int,
):
    driver = create_chrome_driver()
    image_infos = get_image_infos(
        driver=driver,
        env=default_env,
        query=Query(text, min_width, min_height, white),
        num_images=num_images,
        with_thumbs=False,
    )

    os.makedirs(images_dir, exist_ok=True)
    download_and_save_images(
        urls=[info.url for info in image_infos],
        dir_path=images_dir,
        prefix=images_prefix,
        timeout_ms=timeout_ms,
        num_threads=num_threads
    )


def scrap_and_download_many(
    texts_file: str,
    min_width: int,
    min_height: int,
    white: bool,
    num_images: int,
    images_dir: str,
    images_prefix: str,
    timeout_ms: int,
    num_threads: int,
):
    driver = create_chrome_driver()

    for text in read_lines(texts_file):
        images_subdir = os.path.join(images_dir, text)
        os.makedirs(images_subdir, exist_ok=True)
        download_and_save_images(
            urls=[info.url for info in get_image_infos(
                driver=driver,
                env=default_env,
                query=Query(text, min_width, min_height, white),
                num_images=num_images,
                with_thumbs=False,
            )],
            dir_path=images_subdir,
            prefix=images_prefix,
            timeout_ms=timeout_ms,
            num_threads=num_threads
        )


def parse_args():
    base_scrap_parser = argparse.ArgumentParser(add_help=False)
    base_scrap_parser.add_argument('--min-width', type=int, default=0)
    base_scrap_parser.add_argument('--min-height', type=int, default=0)
    base_scrap_parser.add_argument('--white', action='store_true')
    base_scrap_parser.add_argument('--num-images', type=int, required=True)

    base_only_scrap_parser = argparse.ArgumentParser(add_help=False)
    base_only_scrap_parser.add_argument('--thumbs-dir')
    base_only_scrap_parser.add_argument('--thumbs-prefix', default='')

    base_download_parser = argparse.ArgumentParser(add_help=False)
    base_download_parser.add_argument('--images-dir', required=True)
    base_download_parser.add_argument('--images-prefix', default='')
    base_download_parser.add_argument('--timeout-ms', type=int, default=1000)
    base_download_parser.add_argument('--num-threads', type=int, default=50)

    parser = argparse.ArgumentParser(description=GENERAL_DESCRIPTION)
    subparsers = parser.add_subparsers(dest='cmd')

    only_scrap_one_parser = subparsers.add_parser(
        'only-scrap-one',
        help='scrap one query, saving image urls and thumbnails',
        parents=[base_scrap_parser, base_only_scrap_parser],
    )
    only_scrap_one_parser.add_argument('--text', required=True)
    only_scrap_one_parser.add_argument('--urls-file', help='one per line')

    only_scrap_many_parser = subparsers.add_parser(
        'only-scrap-many',
        help='scrap many queries taken from a file, saving image thumbnails and a json report',
        parents=[base_scrap_parser, base_only_scrap_parser],
    )
    only_scrap_many_parser.add_argument('--texts-file', required=True, help='one per line')
    only_scrap_many_parser.add_argument('--report-file')

    download_scrapped_one_parser = subparsers.add_parser(
        'download-scrapped-one',
        help='pass a urls list (e.g. produced by only-scrap-one) to download the images',
        parents=[base_download_parser],
    )
    download_scrapped_one_parser.add_argument('--urls-file', help='one per line', required=True)

    download_scrapped_many_parser = subparsers.add_parser(
        'download-scrapped-many',
        help='pass a report produced by only-scrap-many to download the images',
        parents=[base_download_parser],
    )
    download_scrapped_many_parser.add_argument('--report-file', required=True)

    scrap_and_download_one_parser = subparsers.add_parser(
        'scrap-and-download-one',
        help='scrap a single search query saving the fullsize images',
        parents=[base_scrap_parser, base_download_parser]
    )
    scrap_and_download_one_parser.add_argument('--text', required=True)

    scrap_and_download_many_parser = subparsers.add_parser(
        'scrap-and-download-many',
        help='scrap many queries taken from a file, saving the fullsize images',
        parents=[base_scrap_parser, base_download_parser]
    )
    scrap_and_download_many_parser.add_argument('--texts-file', required=True, help='one per line')

    return parser.parse_args()


def main():
    args = parse_args()

    get_args_and_call({
        'only-scrap-one': only_scrap_one,
        'only-scrap-many': only_scrap_many,
        'download-scrapped-one': download_scrapped_one,
        'download-scrapped-many': download_scrapped_many,
        'scrap-and-download-one': scrap_and_download_one,
        'scrap-and-download-many': scrap_and_download_many,
    }[args.cmd], args)
