#!/usr/bin/env python3

from .default_config import default_config
from .version import __version__
import sys
import os

"""Singleton for accssing config.py and default_config.py"""


class Config:

    @staticmethod
    def get(name, default=None):
        """Return setting or default."""
        return Config.config().get(name, default)


    @staticmethod
    def config():
        """Config as a dict."""
        return Config.get_config('config.py')


    @staticmethod
    def __hosts():
        """Hosts as a dict."""
        return Config.get_config('hosts.py').get('hosts', {})


    _config_cache = {}


    @staticmethod
    def get_config(file='config.py'):
        """Load configuration from cache or disk."""
        # check mtime
        iot49_dir = os.path.expanduser(os.getenv('IOT49', '~'))
        config_file = os.path.join(iot49_dir, 'mcu/base', file)
        mtime = os.path.getmtime(config_file)
        # check cache
        config, last_mtime = Config._config_cache.get(file, (None, 0))
        if not config or mtime > last_mtime:
            try:
                config = default_config.copy()
                with open(config_file) as f:
                    exec(f.read(), config)
                del config['__builtins__']
                config['version'] = __version__
                Config._config_cache[file] = (config, mtime)
            except NameError as ne:
                sys.exit("{} while reading {}".format(ne, config_file))
            except OSError as ose:
                sys.exit("{} while reading {}".format(ose, config_file))
            except SyntaxError as se:
                sys.exit("{} in {}".format(se, config_file))
        return config


def main():
    print("\nQueries:")
    queries = [
        ('wifi_ssid', None),
        ('repl_adv_port', None),
        ('none', None),
    ]
    for q in queries:
        print("  {:20}  {}".format(q[0], Config.get(*q)))

    print("\nAll configuration values:")
    for k, v in Config.config().items():
        print("  {:20}  {}".format(k, v))

if __name__ == "__main__":
    main()
