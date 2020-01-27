import argparse
import json
import os
from typing import NoReturn

from download import create_file
from search_page import create_chrome_driver, get_image_infos, Config, \
    Env, Query, default_env, default_logger, default_config


def save_thumbs(image_infos, dir_path, prefix):
    os.makedirs(dir_path, exist_ok=True)
    for info in image_infos:
        with open(create_file('some.png', dir_path, prefix), 'wb') as out:
            out.write(info.thumb_png)


def parse_args():
    base_scrap_parser = argparse.ArgumentParser(add_help=False)
    base_scrap_parser.add_argument('--min-width', type=int, default=0)
    base_scrap_parser.add_argument('--min-height', type=int, default=0)
    base_scrap_parser.add_argument('--white', action='store_true')
    base_scrap_parser.add_argument('--num-images', type=int, required=True)

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='cmd')

    only_scrap_one_parser = subparsers.add_parser(
        'only-scrap-one',
        help='scrap one query, saving image urls and thumbnails',
        parents=[base_scrap_parser],
    )
    only_scrap_one_parser.add_argument('--text', required=True)
    only_scrap_one_parser.add_argument('--urls-file')
    only_scrap_one_parser.add_argument('--thumbs-dir')
    only_scrap_one_parser.add_argument('--thumbs-prefix', default='')

    only_scrap_many_parser = subparsers.add_parser(
        'only-scrap-many',
        help='scrap many queries taken from a file, saving image thumbnails and a json report',
        parents=[base_scrap_parser],
    )
    only_scrap_many_parser.add_argument('--texts-file', required=True)
    only_scrap_many_parser.add_argument('--report-file')
    only_scrap_many_parser.add_argument('--thumbs-dir')
    only_scrap_many_parser.add_argument('--thumbs-prefix', default='')

    return parser.parse_args()


def main():
    args = parse_args()

    if args.cmd == 'only-scrap-one':
        driver = create_chrome_driver()
        query = Query(args.text, args.min_width, args.min_height, args.white)
        image_infos = get_image_infos(driver, default_env, query, args.num_images, bool(args.thumbs_dir))

        if args.urls_file:
            with open(args.urls_file, 'w') as out:
                out.write('\n'.join(info.url for info in image_infos))

        if args.thumbs_dir:
            save_thumbs(image_infos, args.thumbs_dir, args.thumbs_prefix)

    elif args.cmd == 'only-scrap-many':
        driver = create_chrome_driver()

        text_to_urls = {}
        with open(args.texts_file, 'r') as in_:
            texts = [line.strip() for line in in_ if line.strip()]
        for text in texts:
            query = Query(text, args.min_width, args.min_height, args.white)
            image_infos = get_image_infos(driver, default_env, query, args.num_images, bool(args.thumbs_dir))

            text_to_urls[text] = [info.url for info in image_infos]

            if args.thumbs_dir:
                save_thumbs(image_infos, os.path.join(args.thumbs_dir, text), args.thumbs_prefix)

        if args.report_file:
            with open(args.report_file, 'w') as out:
                json.dump({
                    'min_height': args.min_height,
                    'min_width': args.min_width,
                    'white': args.white,
                    'text_to_urls': text_to_urls
                }, out, indent=2, sort_keys=True, ensure_ascii=False)

    elif args.cmd == 'download-scrapped-one':
        download_scrapped_one()

    elif args.cmd == 'download-scrapped-many':
        download_scrapped_many()

    elif args.cmd == 'scrap-and-download-one':
        scrap_and_download_one()

    elif args.cmd == 'scrap-and-download-many':
        scrap_and_download_many()
