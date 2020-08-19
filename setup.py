import os
import re
import setuptools

NAME             = "iot-device"
AUTHOR           = "Bernhard Boser"
AUTHOR_EMAIL     = "boser@berkeley.edu"
DESCRIPTION      = "Communication with IoT Device (MicroPython) over serial, internet, ..."
LICENSE          = "MIT"
KEYWORDS         = "MicroPython programming"
URL              = "https://github.com/iot49/" + NAME
README           = "index.ipynb"
CLASSIFIERS      = [
  "Development Status :: 4 - Beta",
  "Programming Language :: Python :: 3",
  
]
INSTALL_REQUIRES = [
  "pyserial",
  
]
ENTRY_POINTS = {
  "console_scripts" : [
    "iot-device",
    
  ]
}
SCRIPTS = [
  
]

HERE = os.path.dirname(__file__)

def read(file):
  with open(os.path.join(HERE, file), "r") as fh:
    return fh.read()

VERSION = re.search(
  r'__version__ = [\'"]([^\'"]*)[\'"]',
  read(NAME.replace("-", "_") + "/__init__.py")
).group(1)

LONG_DESCRIPTION = read(README)

if __name__ == "__main__":
  setuptools.setup(
    name=NAME,
    version=VERSION,
    packages=setuptools.find_packages(),
    author=AUTHOR,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    license=LICENSE,
    keywords=KEYWORDS,
    url=URL,
    classifiers=CLASSIFIERS,
    install_requires=INSTALL_REQUIRES,
    entry_points=ENTRY_POINTS,
    scripts=SCRIPTS,
    include_package_data=True    
  )
