# used in package_dep_downloader.py
BASE_URL = "https://packages.ubuntu.com"
DISTRO_NAME = "jammy"
ARCH_NAME = "amd64"
PACKAGE_DIRECTORY = "deb_packages" # folder (created for you) where packages will be downloaded
WAIT_FIXED_TIME = 5
APT_LIST_FILE = None # optional if you want to not download pkg you already have # TODO