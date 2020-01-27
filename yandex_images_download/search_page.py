import json
import logging
import random
from dataclasses import dataclass
from time import sleep
from typing import Dict, Any, List, Iterable, NoReturn, Tuple, Union, Optional
from urllib.parse import urlencode

from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver as Driver
from selenium.webdriver.remote.webelement import WebElement as Element


"""
    TODO 
    * captcha
    * tools
    * examples
    * logging
    * pypi
    * more browsers?
    * disclaimer
    * merge
    * update pypi
    * test on others
    * go for the stars
"""


@dataclass
class Query:
    text: str
    min_width: int
    min_height: int
    white: bool


@dataclass
class ImageInfo:
    url: str
    thumb_png: bytes


@dataclass
class Config:
    scroll_interval_sec: float
    max_scroll_retries: int
    retry_open_interval_sec: float


default_config = Config(0.5, 6, 2)


@dataclass
class Env:
    config: Config
    logger: logging.Logger


default_logger = logging.getLogger(__name__)
default_env = Env(config=default_config, logger=default_logger)


def create_chrome_driver() -> webdriver.Chrome:
    """ Driver corresponds to an opened browser window """
    return webdriver.Chrome()


def get_image_infos(driver: Driver, env: Env, query: Query, num_images: int, with_thumbs: bool) -> List[ImageInfo]:
    open_search_page(driver, env, query)

    return list(iter_image_infos(driver, env, num_images, with_thumbs))


# - private - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

DEFAULT_SEARCH_PATH = 'https://yandex.ru/images/search'


def open_search_page(driver: Driver, env: Env, query: Query) -> NoReturn:
    path, params = query_to_path_and_params(query)

    while True:
        driver.get(f'{path}?{urlencode(params)}')  # TODO test captcha args

        if shows_captcha(driver):
            report_captcha_and_wait()
            # TODO redirect or wait or get again?

        if shows_valid_page(driver):
            break

        rand_sleep(env.config.scroll_interval_sec)


def query_to_path_and_params(query: Query) -> Tuple[str, Dict[str, Any]]:
    return DEFAULT_SEARCH_PATH, {k: v for k, v in {
        'text': query.text,
        'nomisspell': 1,
        'iw': query.min_width,
        'ih': query.min_height,
        'icolor': 'white' if query.white else None
    }.items() if v}


def iter_image_infos(driver: Driver, env: Env, num_elements: int, with_thumbs: bool) -> Iterable[Element]:
    yielded_ids = set()

    retries = 0
    while len(yielded_ids) < num_elements:
        old_num_yielded = len(yielded_ids)

        for element in find_all(driver, 'serp-item'):
            if element.id not in yielded_ids and len(yielded_ids) < num_elements:
                image_info = element_to_image_info(element, with_thumbs)
                if image_info:
                    yield image_info
                    yielded_ids.add(element.id)

        retries = (retries + 1) if len(yielded_ids) == old_num_yielded else 0
        if retries > env.config.max_scroll_retries:
            return

        rand_sleep(env.config.scroll_interval_sec)
        scroll_down(driver)


def element_to_image_info(element: Element, with_thumbs: bool) -> Optional[ImageInfo]:
    url = json.loads(element.get_attribute('data-bem') or "{}").get('serp-item', {}).get('img_href', None)
    thumb = find(element, 'serp-item__thumb') if with_thumbs else None
    if url and (thumb or not with_thumbs):
        return ImageInfo(url=url, thumb_png=thumb.screenshot_as_png if with_thumbs else None)
    else:
        return None


def shows_captcha(driver: Driver) -> bool:
    return bool(find_all(driver, 'form__captcha'))


def shows_valid_page(driver: Driver) -> bool:
    return bool(find_all(driver, 'serp-item'))


def report_captcha_and_wait() -> NoReturn:
    input('please switch to the browser and manually solve the captcha, then press enter')


def rand_sleep(dur_sec: float) -> NoReturn:
    sleep(dur_sec * (2.0 ** random.uniform(-1, 2)))


def find(driver: Union[Driver, Element], class_name) -> Element:
    return driver.find_element_by_class_name(class_name)


def find_all(driver: Union[Driver, Element], class_name) -> List[Element]:
    return driver.find_elements_by_class_name(class_name)


def scroll_down(driver: Driver) -> NoReturn:
    driver.execute_script("window.scrollTo(0, window.scrollY + window.innerHeight);")
