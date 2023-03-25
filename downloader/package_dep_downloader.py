import requests
from bs4 import BeautifulSoup
import os
import hashlib
import logging
import logging.config
import colorlog
import shutil
from tenacity import (
    after_log,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
    wait_random,
)
from config.config_constants import (
    BASE_URL,
    DISTRO_NAME,
    ARCH_NAME,
    PACKAGE_DIRECTORY,
    WAIT_FIXED_TIME,
    APT_LIST_FILE
)

logging.config.fileConfig(fname='logging.conf', disable_existing_loggers=False)
LOGGER = logging.getLogger(__name__)

retry_options = {
    "wait": wait_fixed(WAIT_FIXED_TIME) + wait_random(0, 1),
    "stop": stop_after_attempt(10),
    "retry": retry_if_exception_type(requests.HTTPError),
    "before_sleep": before_sleep_log(LOGGER, logging.WARNING),
    "after": after_log(LOGGER, logging.WARNING),
}

class PackageDepDownloader:

    def __init__(self, top_level_package):
        self.apt_list = self.generate_installed_list()
        self.package = top_level_package
        self.package_list = set()
        deb_pkg_path = os.path.join(os.getcwd(), PACKAGE_DIRECTORY, self.package)
        self.deb_pkg_path = str(deb_pkg_path)
        if os.path.exists(deb_pkg_path) and os.path.isdir(deb_pkg_path):
            shutil.rmtree(deb_pkg_path)
        os.makedirs(deb_pkg_path, 0o777)

    def generate_installed_list(self):
        if APT_LIST_FILE:
            file_content = open(APT_LIST_FILE, "r").readlines()
            # TODO
        return []

    @retry(**retry_options)
    def _make_request(self, href, stream=None):
        """ makes a request w/ retrying support

        Args:
            href (str): _description_
            stream (str, optional): _description_. Defaults to None.

        Returns:
            (Response): response object
        """
        response = requests.get(href, stream=stream)

        if response.status_code != 200:
            response.raise_for_status()

        LOGGER.info(f"Returning response successfully for {href}!")
        return response
    #####
    ###
    #
    ###
    ##### ----- Begin package discovery
    def find_all_packages_needed(self, package_name=None):
        """ Recursive function to create list of all packages required by initial package sent in
            Filtered by whether or not package currently exists based on "apt list" set

        Args:
            package_name (str): name of package

        Returns:
            (list): list of packages (ordered by level, lowest level first)
        """

        if package_name in self.package_list:
            return

        if package_name != None:
            self.package_list.add(package_name)
        else:
            self.package_list.add(self.package) # first package
            package_name = self.package


        dependencies = self.find_required_packages(package_name)

        for dependency in dependencies:
            self.find_all_packages_needed(dependency)


    def find_required_packages(self, package_name):
        """ Finds package dependencies given a package

        Args:
            package_name (str): package to find deps for

        Returns:
            required_packages (list): deps for package, for example: ['cpp', 'gcc-11']
        """
        required_packages = []

        # retrieve page
        package_page_url = f"{BASE_URL}/{DISTRO_NAME}/{ARCH_NAME}/{package_name}"
        webpage_response = self._make_request(package_page_url)

        # soupify
        soup = BeautifulSoup(webpage_response.text, "html.parser")

        # get dependencies
        dependents = soup.findAll("ul", class_="uldep")

        for dependent in dependents:
            # packages = dependent.findAll("dt") # includes version info
            packages = dependent.findAll("a")
            if packages:
                for pack in packages:
                    package = pack.get_text().strip()
    
                    if self.apt_list or package not in self.apt_list:
        
                        required_packages.append(package)
                    # required_packages = [''.join(pack.get_text().strip().split()) for pack in packages] # includes version info

        return required_packages
    ##### ----- End package discovery
    ###
    #
    ###
    ##### ----- Begin package downloading
    # TODO
    def download(self, href):
        """ downloads a file

        Args:
            href (_type_): _description_
        """
        try:
            response = self._make_request(href)
        except Exception as exception:
            LOGGER.warning(exception)
            return False

        filename = href.split('/')[-1]
        with open(f"{self.deb_pkg_path}/{filename}", "wb") as f:
            f.write(response.content)
        return True

    def verify_hash(self, href, expected_hash):
        """ Verifies SHA256 hash of deb file

        Args:
            href (str): url where file is hosted
            expected_hash (str): expected SHA256 hash

        Returns:
            (bool): True if hash matches, False otherwise
        """
        response = self._make_request(href, True)
        hash_object = hashlib.sha256()

        for chunk in response.iter_content(chunk_size=4096):  # 4 bytes
            hash_object.update(chunk)

        if hash_object.hexdigest() == expected_hash:
            LOGGER.info("Hashes match! Proceeding to download.")
            return True
        else:
            LOGGER.warning("Hashes do not match :( Proceeding to next download URL.")
            return False

    # TODO
    def download_deb_package(self, package_name):
        """ Finds download url for given package, verifies hash, and downloads package

        Args:
            package_name (str): package name

        Returns:
            (bool): True/False if download was successful
        """
        expected_hash = None
        unverified_download = False

        # retrieve page
        download_page_url = f"{BASE_URL}/{DISTRO_NAME}/{ARCH_NAME}/{package_name}/download"
        webpage_response = self._make_request(download_page_url)

        # soupify
        soup = BeautifulSoup(webpage_response.text, "html.parser")

        # find expected md5 hash
        metadata_table = soup.find("table", id="pdownloadmeta")
        for row in metadata_table.find_all('tr'):
            header = row.find('th').text.strip()
            if header == 'SHA256 checksum':
                expected_hash = row.find('td').text.strip()

        if not expected_hash:
            LOGGER.warning(f"WARNING: could not find a hash for {package_name}... proceed at your own risk.")
            unverified_download = True
        
        # lets only look at 'a' tags since they have 'href' within them
        a_items = soup.findAll('a')
        for item in a_items:
            try:
                # get url
                href = item.get('href')

                # only pay attention to deb download links
                if href.startswith('http') and href.endswith('.deb'):
                    if expected_hash:
                        verified = self.verify_hash(href, expected_hash)
                    if verified or unverified_download:
                        downloaded = self.download(href)
                        if downloaded:
                            return True
                        else:
                            LOGGER.warning(f".deb file at {href} was NOT downloaded. Checking next .deb")
                    else:
                        LOGGER.warning(f".deb file at {href} was NOT verified. Checking next .deb")
                    
            except Exception as e:
                print(f"Problem iterating through download URLS: {e}")
                continue
        return False
    ##### ----- End package downloading


# cpp_trawler = PackageDepDownloader("cpp")
# cpp_trawler.find_all_packages_needed()
# # print(cpp_trawler.package_list)
# for package in cpp_trawler.package_list:
#     package_downloaded_successfully = cpp_trawler.download_deb_package(package)
#     if not package_downloaded_successfully:
#         LOGGER.warning(f"Unable to download package: {package}")
# # trawler.download_deb_package("libstdc++6")
# # download_deb_package(package_name, distro_name, arch_name)