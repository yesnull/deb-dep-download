import logging
import logging.config
import colorlog
from downloader.package_dep_downloader import PackageDepDownloader

logging.config.fileConfig(fname='logging.conf', disable_existing_loggers=False)
LOGGER = logging.getLogger(__name__)

if __name__=='__main__':
    cpp_trawler = PackageDepDownloader("cpp")
    cpp_trawler.find_all_packages_needed()
    # print(cpp_trawler.package_list)
    for package in cpp_trawler.package_list:
        package_downloaded_successfully = cpp_trawler.download_deb_package(package)
        if not package_downloaded_successfully:
            LOGGER.warning(f"Unable to download package: {package}")