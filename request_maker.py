import errno
import os
import requests

from bs4 import BeautifulSoup
from selenium import webdriver


class HTTPError(Exception): pass


class RequestMaker(object):
    """
    Makes HTTP requests to the Q guide. Automatically logs in using selenium
    using credentials provided during construction if necessary. Also caches
    data in filesystem to speed up future runs of the program.
    """
    def __init__(self, username, password, data_dir='data'):
        self.cookies = {}
        self.username = username
        self.password = password
        self.data_dir = data_dir
        self.base_url = 'https://webapps.fas.harvard.edu'

    @classmethod
    def copy(cls, requester):
        """
        Copies a RequestMaker, returning a brand new but idententical
        RequestMaker, complete with credentials and cookies. One RequestMaker
        cannot safely be shared accross processes, and so method can be used
        to copy a RequsetMaker for use in another process.
        """
        new_requester = cls(requester.username,
                            requester.password,
                            requester.data_dir)
        new_requester.base_url = requester.base_url
        new_requester.cookies = {k: v for k, v in requester.cookies.items()}
        return new_requester

    def _get_cookies(self):
        """
        Logs in to the Q Guide using selenium, and returns the cookies it
        receives
        """
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
        """
        Returns data from `path`. It first checks to see if the data is cached
        on the filesystem, and if not, it fetches and downloads the data.
        """
        print 'Getting data for {}'.format(path)
        soup = None

        # First try to get cached data
        filepath = os.path.join(self.data_dir, path[1:])
        try:
            with open(filepath) as f:
                soup = BeautifulSoup(f.read().decode('utf8'), 'lxml')
        except IOError:
            # Make sure we have cookies
            if not self.cookies:
                print 'No cookies, getting them now'
                self.cookies = self._get_cookies()

            # Make request
            url = self.base_url + path
            r = requests.get(url, cookies=self.cookies, verify=False)
            if not r.ok:
                raise HTTPError('Request to path {} failed with HTTP status code {}'.format(path, r.status))

            # Make sure cookies were valid
            soup = BeautifulSoup(r.text, 'lxml')
            if soup.title is not None and soup.title.text == 'HarvardKey Login':
                print 'Cookies are invalid: retrieving them then trying again'
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
