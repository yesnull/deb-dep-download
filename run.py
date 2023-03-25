import logging
import logging.config
import colorlog
from downloader.package_dep_downloader import PackageDepDownloader
import sys

logging.config.fileConfig(fname='logging.conf', disable_existing_loggers=False)
LOGGER = logging.getLogger(__name__)

if __name__=='__main__':
    args = sys.argv
    args_length = len(sys.argv)
    
    if args_length < 2:
        LOGGER.error(f"Missing arguments! supply each package as an argument Example: python run.py cpp gcc")
        exit()
    
    packages = args[1:]
    
    for package in packages:
        
        package_trawler = PackageDepDownloader(package)  # instantiate class

        # package_trawler.find_all_packages_needed()  # find all packages needed

        # for pack in package_trawler.package_list:
        #     package_downloaded_successfully = package_trawler.download_deb_package(pack)  # download the package
        #     if not package_downloaded_successfully:
        #         LOGGER.warning(f"Unable to download package: {pack}")