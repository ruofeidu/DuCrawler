# -*- coding: utf-8 -*-
from __future__ import print_function
import re
try:
    from urllib.parse import urlparse
except ImportError:
     from urlparse import urlparse
from bs4 import BeautifulSoup
from selenium import webdriver
import configparser
import requests
import os
import time
import cv2

__author__ = "Ruofei Du"


browser = webdriver.PhantomJS()
re_images = re.compile('mediaurl=(.*?)&amp;')


class Paras:
    section = "DuCrawler"
    save_folder = "Results"
    keywords_file = "%s.txt" % save_folder
    suffix = ""
    remove_color_images = False
    max_counter = 1000
    file_min_size = 1000
    timeout = 0.5
    valid_using_opencv = False
    min_average_illuminance = 100
    min_rgb_difference = 30
    header = {}
    scroll_times = 5
    scroll_pause_time = 0.5



def get_soup(url, header):
    return BeautifulSoup(requests.get(url, headers=header).content, 'html.parser')


def abs_sum(c):
    return abs(c[0] - c[1]) + abs(c[0] - c[2]) + abs(c[1] - c[2])


def search_bing(key, depth=50):
    image_list, url_dict, url_list = [], {}, []

    root_dir = Paras.save_folder
    prefix = "bing"
    if not os.path.exists(root_dir):
        os.mkdir(root_dir)
    dir = os.path.join(root_dir, key)
    if not os.path.exists(dir):
        os.mkdir(dir)
    file_name = os.path.join(dir, "_log.txt")
    log = open(file_name, "a+")

    file_name = os.path.join(dir, "_urls.txt")
    try:
        with open(file_name, "r") as f:
            url_list = f.readlines()
        for l in url_list:
            url_dict[l.strip()] = True
    except Exception as e:
        print("Init URL files, ", e)
    link_file = open(file_name, "a+")

    for page_id in range(depth):
        query = key + Paras.suffix
        query = query + " " + str(page_id) if page_id > 0 else query
        query = '+'.join(query.split())
        url = "https://www.bing.com/images/search?q=" + query + "&FORM=HDRSC2"
        print(url)
        browser.get(url)
        browser.implicitly_wait(1)

        # Get scroll height
        last_height = browser.execute_script("return document.body.scrollHeight")

        for i in range(Paras.scroll_times):
            # Scroll down to bottom
            browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            # Wait to load page
            time.sleep(Paras.scroll_pause_time)
            # Calculate new scroll height and compare with last scroll height
            new_height = browser.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        html = browser.page_source
        matches = re_images.findall(html)
        for image_url in matches:
            p = image_url.rfind(".")
            if p >= len(image_url) - 5:
                ext = image_url[p+1:]
            else:
                continue
            image_url = urllib.parse.unquote(image_url)
            image_list.append((image_url, ext))

        counter = 0
        for (link, ext) in image_list:
            if link in url_dict:
                continue
            print(image_url)
            url_dict[link] = True
            link_file.write("%s\n" % link)
            link_file.flush()
            try:
                req = requests.get(link, headers=Paras.header, timeout=Paras.timeout)
                if req.status_code == 200:
                    counter = len([s for s in os.listdir(dir) if prefix in s]) + 1
                    file_name = os.path.join(dir, prefix + str(counter) + "." + ext)
                    with open(file_name, "wb") as f:
                        f.write(req.content)
            except Exception as e:
                log.write("# Could not download: %s\n" % link)
            else:
                try:
                    if Paras.valid_using_opencv and ext != "gif":
                        img = cv2.imread(file_name)
                        if img is None:
                            raise Exception("The link is invalid.")
                        if Paras.remove_color_images:
                            average_color = [img[:, :, i].mean() for i in range(img.shape[-1])]
                            if average_color[0] < Paras.min_average_illuminance:
                                raise Exception("The average color is too dark.")
                            if abs_sum(average_color) > Paras.min_rgb_difference:
                                raise Exception("It's a color image.")
                    else:
                        stat = os.stat(file_name)
                        if stat.st_size < Paras.file_min_size:
                            raise Exception("File size too small.")
                except Exception as e:
                    try:
                        os.remove(file_name)
                    except Exception:
                        pass
                    log.write("# %s\t%s\n" % (e, link))
                else:
                    if counter % 10 == 0:
                        print(counter)
                    log.write("%d\t%s\n" % (counter, link))
            log.flush()
        if counter > Paras.max_counter:
            break
    log.close()
    link_file.close()
    pass


def test_average_color():
    img = cv2.imread("Google\\Tropical Flower Coloring Pages\\image14.jpg")
    average_color = [img[:, :, i].mean() for i in range(img.shape[-1])]
    print(average_color)
    print(img.shape)


if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read("config.ini")
    Paras.keywords_file = config.get(Paras.section, "keywords_file").strip()
    Paras.suffix = config.get(Paras.section, "suffix").strip()
    if Paras.suffix:
        Paras.suffix = " " + Paras.suffix
    Paras.save_folder = config.get(Paras.section, "save_folder").strip()
    Paras.remove_color_images = config.getboolean(Paras.section, "remove_color_images")
    Paras.max_counter = config.getint(Paras.section, "max_results")
    Paras.timeout = config.getfloat(Paras.section, "time_out")
    Paras.file_min_size = config.getint(Paras.section, "file_min_size")
    Paras.valid_using_opencv = config.getboolean(Paras.section, "valid_using_opencv")
    Paras.header['User-Agent'] = config.get(Paras.section, "header").strip()
    Paras.min_average_illuminance = config.get(Paras.section, "min_average_illuminance")
    Paras.min_rgb_difference = config.get(Paras.section, "min_rgb_difference")
    Paras.scroll_times = config.getint(Paras.scroll_times, "scroll_times")
    Paras.scroll_pause_time = config.getfloat(Paras.scroll_pause_time, "scroll_pause_time")
    Paras.init_pause_time = config.getfloat(Paras.init_pause_time, "init_pause_time")

    print(Paras.keywords_file, Paras.suffix, Paras.save_folder)

    with open(Paras.keywords_file, "r") as f:
        keywords = f.readlines()
    for k in keywords:
        if k[0] == '#' or len(k.strip()) == 0:
            continue
        t = time.time()
        search_bing(k.strip())
        print(time.time() - t)
        break
