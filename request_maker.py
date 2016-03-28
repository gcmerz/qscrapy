import errno
import logging
import os
import requests

from bs4 import BeautifulSoup
from selenium import webdriver

logger = logging.getLogger(__name__)


class HTTPError(Exception): pass


class RequestMaker(object):
    def __init__(self, username, password, data_dir='data'):
        self.cookies = {}
        self.username = username
        self.password = password
        self.data_dir = data_dir
        self.base_url = 'https://webapps.fas.harvard.edu'

    def _get_cookies(self):
        driver = webdriver.PhantomJS(service_args=['--ignore-ssl-errors=true'])
        driver.get(self.base_url + '/course_evaluation_reports/fas/list')
        driver.find_element_by_css_selector('#HUID').click()
        driver.find_element_by_css_selector('#username').send_keys(self.username)
        driver.find_element_by_css_selector('#password').send_keys(self.password)
        driver.find_element_by_css_selector('#submitLogin').click()
        cookies_raw = driver.get_cookies()
        driver.quit()

        return {c['name']: c['value'] for c in cookies_raw}

    def make_request(self, path):
        print 'Getting data for {}'.format(path)
        soup = None
        filepath = os.path.join(self.data_dir, path[1:])
        try:
            with open(filepath) as f:
                soup = BeautifulSoup(f.read().decode('utf8'), 'lxml')
        except IOError:
            # Make sure we have cookies
            if not self.cookies:
                print 'No cookies, getting them now'
                logger.warning('No cookies, getting them now')
                self.cookies = self._get_cookies()

            # Make request
            url = self.base_url + path
            r = requests.get(url, cookies=self.cookies)
            if not r.ok:
                raise HTTPError('Request to path {} failed with HTTP status code {}'.format(path, r.status))

            # Make sure cookies were valid
            soup = BeautifulSoup(r.text, 'lxml')
            if soup.title is not None and soup.title.text == 'HarvardKey Login':
                print 'Cookies are invalid: retrieving them then trying again'
                logger.warning('Cookies are invalid: retrieving them then trying again')
                self.cookies = self._get_cookies()
                return self.make_request(path)

            # Request went through successfully; cache to file and return
            # response
            if not os.path.exists(os.path.dirname(filepath)):
                try:
                    os.makedirs(os.path.dirname(filepath))
                except OSError as exc:  # Guard against race condition
                    if exc.errno != errno.EEXIST:
                        raise
            with open(filepath, 'w') as f:
                f.write(r.text.encode('utf8'))

        return soup
