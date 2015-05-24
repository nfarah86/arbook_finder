#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import logging
import os
import queue
import sys
import threading

import requests
from lxml import html

from udemy.config.config import Config
from udemy.notification.notifier import Notifier
from udemy.scrapers import write_arbook_finder

logger = logging.getLogger(__name__)


class ARBookScraper(object):
    NUM_THREADS = {
        'scraping': 3
    }

    def __init__(self, range_min, range_max):
        self.config = Config()
        self.requests = queue.Queue()
        self.range_min = int(range_min)
        self.range_max = int(range_max)
        self.book_list = []
        self.data_path = self.get_file_path()

        # executes fn's
        self.create_requests(self.range_min, self.range_max)
        self.main()

    def create_requests(self, min_num, max_num):
        """
        puts the numbers 1-174000 in a queue
        """
        for i in range(min_num, max_num):
            self.requests.put(i)

    def get_file_path(self):
        """
        sets the file path where the
        tsv file will be located
        """
        yesterday = (datetime.date.today() -
                     datetime.timedelta(1)).strftime("%Y-%m-%d")
        self.data_path = self.config.path.get(
            'source_data', None) + 'arbook/arbook_finder_' + yesterday + '.tsv'
        # "/Users/.." which we will use to store
        # .tsv file
        return self.data_path

    def main(self):
        # we start running threads here: each thread
        # will execute below:
        for i in range(self.NUM_THREADS['scraping']):
            # each thread will execute below:
            r = Scraper(self)
            r.setDaemon(True)
            r.start()
        # wait for everything to execute, before writing to file
        self.requests.join()
        # module is imported; [{book_obj}, {book_obj}], 'file_path'
        write_arbook_finder.write_books(self.book_list, self.data_path)


class Scraper(threading.Thread):

    def __init__(self, parent):
        threading.Thread.__init__(self)
        self.parent = parent

    def get_cookies(self):
        """
        get and set the cookie for session;
        it should only be executed once
        """
        try:
            arbook_url_main_page = 'http://www.arbookfind.com/UserType.aspx'
            print(arbook_url_main_page)
            response = requests.get(arbook_url_main_page, timeout=10)
            cookies = response.cookies
            # we have to manually set a cookie here for
            # script to work
            cookies.set('BFUserType', 'Librarian')
            # cookies is an object {}
            return cookies
        except Exception as e:
            _error_log(e)

    def run(self):
        queue = self.parent.requests
        try:
            while not queue.empty():
                # get a page number
                rid = self.parent.requests.get()
                # get cookies for each thread each time
                got_cookies = self.get_cookies()
                # get the html
                html_content = self.get_html(got_cookies, rid)
                if not html_content:
                    pass
                else:
                    # put the obj after parsing to a list: [{book_obj}, {book_obj}]
                    self.parse_html(html_content)
                    # mark the threads done
                    self.parent.requests.task_done()
        except Exception as e:
            _error_log(e)

    def get_html(self, cookies, rid):
        """
        gets the html directly by sending the cookies
        """
        try:
            arbook_url = 'http://www.arbookfind.com/bookdetail.aspx?q=%d&l=EN&slid=615244298' \
                         % (rid)
            print(arbook_url)
            # checks to see if the cookies are set
            set_cookies_present = _check_cookies(cookies)
            if set_cookies_present:
                response_head = requests.head(arbook_url, timeout=10, cookies=cookies)
                status_number = response_head.status_code
                # checks to see if the status code is 200 vs. ie 304
                result_status_code_present = _check_status_code(int(status_number))
                # if status code == range of 200:
                if result_status_code_present:
                    response_html = requests.get(arbook_url, timeout=10, cookies=cookies)
                    # return '<html><body></body></html>'
                    return response_html.text
                else:
                    return ''
            # if thread didn't set cookie, return ''
            # each thread creates new cookie
            else:
                return ''
        # exception is for connection issues
        except Exception as e:
            _error_log(e)

    def parse_html(self, html_content):
        """
        parses html for ie book title
        and word count ...
        """
        # exception if url is a 302 or 404
        # don't store in data queue, just pass
        try:
            book_information = {}
            dom = html.fromstring(html_content)
            book_information['book_title'] = _grab_title(dom)
            book_information['book_author'] = _grab_author(dom)
            book_information['book_image_link'] = _grab_image_link(dom)
            book_information['book_rating'] = _grab_rating(dom)
            book_information['book_word_count'] = _grab_word_count(dom)
            book_information['interest_level'] = _grab_interest_level(dom)
            print(book_information)
            # [{book_info}, {book_info}]
            self.parent.book_list.append(book_information)
        except Exception as e:
            _error_log(e)


def _check_cookies(cookies):
    """
    checks the cookies values
    to see 'Librarian' is there
    """
    if 'Librarian' in cookies.values():
        return True
    else:
        return False


def _check_status_code(status_code):
    """
    checks to see if the status code is 200
    vs. anything else
    """
    if 200 <= status_code < 300:
        return True
    else:
        return False


def _grab_title(dom):
    """
    grabs the title of book and returns it
    as a string
    """
    book_title = dom.get_element_by_id('ctl00_ContentPlaceHolder1_ucBookDetail_lblBookTitle')
    print(book_title.text)
    return book_title.text


def _grab_author(dom):
    """
    grabs the author of book and returns it
    as a string
    """
    book_author = dom.get_element_by_id('ctl00_ContentPlaceHolder1_ucBookDetail_lblAuthor')
    return book_author.text


def _grab_image_link(dom):
    """
    grabs the jpg image from book
    as a string
    """
    # these fields may or may not be there.
    # instead of writing the error, just put not applicable
    # and add to list {{book_obj}]
    try:
        book_image_link = dom.xpath(
            '//*[@id="ctl00_ContentPlaceHolder1_ucBookDetail_imgBookCover"]/@src')
        return book_image_link[0]
    except IndexError:
        return "Not Applicable"


def _grab_rating(dom):
    """
    grabs the rating for the book
    """
    # these fields may or may not be there.
    # instead of writing the error, just put not applicable
    # and add to list {{book_obj}]
    try:
        book_rating = dom.xpath(
            '//*[@id="ctl00_ContentPlaceHolder1_ucBookDetail_lblRanking"]/img/@alt')
        # ie 3.5
        return float(book_rating[0])
    except IndexError:
        return "Not Applicable"


def _grab_word_count(dom):
    """
    grabs word count for book
    """
    book_word_count = dom.get_element_by_id(
        'ctl00_ContentPlaceHolder1_ucBookDetail_lblWordCount')
    # ie 5665
    return int(book_word_count.text)


def _grab_interest_level(dom):
    """
    grabs interest level for book
    """
    interest_level = dom.get_element_by_id(
        'ctl00_ContentPlaceHolder1_ucBookDetail_lblInterestLevel')
    return interest_level.text


def _error_log(e):
    """
    creates and error log with specified file path
    """
    config = Config()
    # file path for where error log will be stored
    logging_error_path = config.path.get(
        'source_data', None) + 'arbook/arbook_book_info.log'
    # fh = file handler
    fh = logging.FileHandler(logging_error_path)
    # verbose writing to error log
    fh.setLevel(logging.DEBUG)
    # when error is there, it writes time, day, and which link caused the error and where
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    # add file handler to logger
    logger.addHandler(fh)
    # write error
    logger.exception(e)


def _error_notifier():
    """
    sends an email with the contents of
    gwt_backlinks_scraper.log
    once program is finished running
    """
    config = Config()
    if os.path.exists(config.path.get('source_data', None) + "arbook/arbook_book_info.log"):
        # file path where I want to store the files with our config
        logging_error_path = config.path.get('source_data', None) + "arbook/arbook_book_info.log"

        # open and read error log
        read_error_log = open(logging_error_path, 'r')
        file_content = read_error_log.read()

        # send an email with contents of error log
        error_content = "<h3>arbook_finder_scraper</h3><pre>Error</pre>" \
                        "<h3>Stacktrace</h3><pre>{stack}</pre>"\
            .format(stack=file_content)
        notifier = Notifier(email=None)
        notifier.send(subject='Error while running arbook_finder_scraper',
                      contents=error_content)
        # if log exist, remove it
        os.remove(logging_error_path)

if __name__ == "__main__":
    range_min_entry = sys.argv[1]
    range_max_entry = sys.argv[2]
    arb_scrape = ARBookScraper(range_min_entry, range_max_entry)
    _error_notifier()