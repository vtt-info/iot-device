import os
import re
import setuptools
from iot_device import version

install_requires = [
    "pyserial>=3.4",
    "termcolor>=1.1.0",
    "pyopenssl>=19.1.0",
]

setuptools.setup(
    name="iot-device",
    version=version.__version__,
    packages=[ 'iot_device'],
    author="Bernhard Boser",
    description="Communication with IoT Device (MicroPython) over serial, internet, ...",
    long_description="none",
    long_description_content_type="text/markdown",
    license="MIT",
    keywords="MicroPython,Repl",
    url="https://github.com/iot49/iot-device",
    classifiers = [
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
    ],
    install_requires=install_requires,
    include_package_data=True,
    entry_points = {
        'console_scripts': [
            'iot49server=iot_device.device_server:main',
        ],
    },
    scripts = [ 'server.sh' ],
    python_requires='>=3.8',
) 
