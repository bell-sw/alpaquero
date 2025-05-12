# Alpaquero

An installer for Alpaquita-like Linux distributions.

## Usage

The installer supports cross-libc installations, i.e. it's possible
to install a musl Linux instance running on a glibc Linux instance.
So the code expects that APK key files are shipped with the package.

For that to work put the keys to the `alpaquero/keys` directory.
Then build the package using the provided `setup.py` and install it as usual.
For example:

```
# Before doing this, make sure that the Python wheel package is installed
python setup.py bdist_wheel
pip install dist/<the generated wheel file>
```

By default, the installer is configured to work with Alpaquita. For installation
of other Alpaquita-like Linux distributions you may need to update
the `alpaquero/app/distro.py` file.

The installer operates in 2 modes:
 * interactive mode with a text-based UI (default mode)
 * batch (non-interactive) mode (when `-n` is passed)

The former performs an installation based on the user's answers
in the UI, the latter - in accordance with a provided `.yaml` file.

Please consult `AUTOMATING_INSTALLATION.md` for the syntax of the `.yaml` file.

The interactive mode also generates a `setup.yaml` file with a description
of the current installation.

Passing `-h` will display the list of all supported command line arguments.

## Development environment setup
The code is Python 3, the minimum supported Python version is 3.9.

All necessary dependencies are listed in the provided `requirements.txt`:
```
python -m venv venv
. venv/bin/activate
pip install -r requirements.txt
alpaquero [args] # or python -m alpaquero [args]
```

The tests are written using `pytest` and can be run with:
```
pip install pytest
pytest tests/*
```

## Acknowledgements

The code implements parts of the MVC ideas and uses many of Urwid widgets
from the [Ubuntu Subiquity installer](https://github.com/canonical/subiquity/blob/main/DESIGN.md).
