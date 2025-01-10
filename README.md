# NTIA/ITS Python Wrapper for Tektronix® RSA API for Linux

![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/NTIA/tekrsa-api-wrap?display_name=tag&sort=semver)
![PyPI - Downloads](https://img.shields.io/pypi/dm/tekrsa-api-wrap)
![GitHub issues](https://img.shields.io/github/issues/NTIA/tekrsa-api-wrap)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

This Python package provides a module which wraps the
[Tektronix Python/Ctypes RSA API](https://github.com/tektronix/RSA_API/tree/master/Python),
with the goal of masking the Ctypes dependency and streamlining use of the API in a
Python development environment. It implements most of the available RSA API functionality
(see below for more information). Basic documentation is included in docstrings for quick
reference during development, but this is not meant as a substitute for the comprehensive
[RSA API Programming Reference manual](https://www.tek.com/spectrum-analyzer/rsa306-manual/rsa306-rsa306b-and-rsa500a-600a-0)
offered by Tektronix. The manual details many peculiarities in API or device behavior
which are not immediately obvious, and yet are important for developing software to
control an RSA device.

This wrapper was developed for applications involving programmatic control of Tektronix
RSA devices from Linux. Depending on your use case, and especially if you plan to run
your program from Microsoft Windows®, it may be worth looking into the
[Tektronix Python/Cython RSA API](https://github.com/tektronix/RSA_API/tree/master/Python/Cython%20Version)
instead of using this wrapper.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Development](#development)
- [License](#license)
- [Contact](#contact)
- [Disclaimer](#disclaimer)

## Installation

Requires `python>=3.9`, `numpy>=1.25`, and the Tektronix RSA API for Linux.

First, download and install the
[RSA API for Linux](https://www.tek.com/spectrum-analyzer/rsa306-software/rsa-application-programming-interface--api-for-64bit-linux--v100014)
from Tektronix. Follow the included installation instructions, then copy the
`libRSA_API.so` and `libcyusb_shared.so` files into your project.

These shared object files are required, and this API wrapper by default expects to find
them in the [SCOS Sensor](https://github.com/NTIA/scos-sensor/) drivers directory
(`/drivers/`). If you are running without SCOS Sensor, you will need to specify your
drivers directory when instantiating the API wrapper. See the [Usage section](#usage)
below for an example of how to do this.

Next download and install this API wrapper using `pip`:

```bash
pip install tekrsa-api-wrap
```

## Usage

Interface with a supported Tektronix RSA device using Python as follows:

```python
import rsa_api

# Directory which contains both libRSA_API.so and libcyusb_shared.so
drivers_path = '/path/to/shared_objects/'

# Initialize an RSA device using the API wrapper
rsa = rsa_api.RSA(so_dir=drivers_path)

# Example usage: connect, print current center frequency, then disconnect
rsa.DEVICE_SearchAndConnect()
print(f"Current Center Frequency (Hz): {rsa.CONFIG_GetCenterFreq()}")
rsa.DEVICE_Disconnect()

# Print docstrings for any implemented API function
help(rsa.IQSTREAM_Acquire) # Requires initialized RSA device
help(rsa_api.RSA.IQSTREAM_Acquire)  # Does not require initalized RSA device
```

### List of API functions NOT implemented

- All functions not supported by the RSA API for Linux (see "Known Issues" below)
- All `DPX`, `PLAYBACK`, `IFSTREAM` and `TRKGEN` functions
- `DEVICE_GetErrorString()`
  - Alternate error handling is implemented.
- `DEVICE_GetNomenclatureW()` and `IQSTREAM_SetDiskFilenameBaseW()`
  - `DEVICE_GetNomenclature()` and `IQSTREAM_SetDiskFilenameBase()` are used instead.
- `IQBLK_GetIQDataCplx()`
  - `IQBLK_GetIQData()` and `IQBLK_GetIQDataDeinterleaved()` are used instead.

### List of API "Helper" functions

A handful of useful functions are included in this wrapper which streamline some common
tasks. These "helper functions" include:

- `IQSTREAM_Acquire()`
- `IQBLK_Acquire()`
- `IQBLK_Configure()`
- `SPECTRUM_Acquire()`
- `IQSTREAMFileInfo_StatusParser()`
- `IQSTREAMIQInfo_StatusParser()`
- `IQSTREAM_Tempfile()`
- `IQSTREAM_Tempfile_NoConfig()`
- `DEVICE_SearchAndConnect()`
- `DEVICE_GetTemperature()`

To read more about these functions, check their docstrings with `help()`.

### Known Issues

Known issues exist in the underlying Tektronix RSA API for Linux, and therefore this
wrapper is limited in certain ways. The list of known issues is provided by Tektronix in
the [Tektronix RSA API for Linux release notes](https://download.tek.com/software/supporting_files/ReleaseNotes_1_0_0014_64bit_066207701.txt)
(up-to-date as of version 1.0.0014).

### TODO: Update this section after resolving

Additionally, a known issue exists with parsing IQ streaming status data structures.
There appears to be a discrepancy between the documented status message encoding scheme
and the implemented encoding scheme. In its current implementation, this API wrapper has
been tested to ensure that ADC overrange events are properly flagged when using
`IQSTREAM_Tempfile`, `IQSTREAM_Tempfile_NoConfig` or `IQSTREAM_Acquire` methods. Buffer
overflow warnings and errors should work, but have not been tested. The USB data
discontinuity status is unable to be parsed. Unknown IQ stream status codes are treated
as errors and handled as configured in `IQSTREAM_StatusParser`.

## Development

### Development Environment

Set up a development environment using a tool like
[Conda](https://docs.conda.io/en/latest/)
or [venv](https://docs.python.org/3/library/venv.html#module-venv).
Then, from the cloned directory, install the development dependencies by running:

```bash
pip install .[dev]
```

This will install the project itself, along with development dependencies for pre-commit
hooks, building distributions, and running tests. Set up pre-commit, which runs
auto-formatting and code-checking automatically when you make a commit, by running:

```bash
pre-commit install
```

The pre-commit tool will auto-format Python code using [Black](https://github.com/psf/black)
and [isort](https://github.com/pycqa/isort). Other pre-commit hooks are also enabled, and
can be found in [`.pre-commit-config.yaml`](.pre-commit-config.yaml).

### Building New Releases

This project uses [Hatchling](https://github.com/pypa/hatch/tree/master/backend) as a
backend. Hatchling makes version control and building new releases easy. The package
version can be updated easily using any of the following commands.

```bash
hatchling version major  # 1.0.0 -> 2.0.0
hatchling version minor  # 1.0.0 -> 1.1.0
hatchling version micro  # 1.0.0 -> 1.0.1
hatchling version "X.X.X"  # 1.0.0 -> X.X.X
```

To build a wheel and source distribution, run:

```bash
hatchling build
```

### Running Tests

A testing file is included in the `tests` directory of this repository. The test uses
`unittest` to test supported API functions. Running a test requires an RSA device to be
connected. The same test is used for any supported RSA device, with some tests being
enabled, disabled, or modified as needed depending on the device's specific supported
API functions. For example, tests of the preamp configuration are not run when testing
with an RSA which does not have a preamp.

From the top-level directory of this repository, run the test by running:

  ```bash
  export SO_DIR=/path/to/drivers
  python -X faulthandler -m unittest
  ```

Replacing `<path-to-shared-objects>` with the path to a directory containing both
`libRSA_API.so` and `libcyusb_shared.so`.

This testing code was been adapted from the
[Tektronix Cython RSA API testing code for the 306B](https://github.com/tektronix/RSA_API/blob/master/Python/Cython%20Version/test_rsa306b.py)
and [for the 500A/600A series devices](https://github.com/tektronix/RSA_API/blob/master/Python/Cython%20Version/test_rsa500-600.py).
In addition to adapting this code to work with this API wrapper, various tests were also
added which were not present in the original versions, and the test was made to be
universal for all supported RSA devices.

## License

See [LICENSE](LICENSE.md)

TEKTRONIX and TEK are registered trademarks of Tektronix, Inc.

Microsoft and Windows are trademarks of the Microsoft group of companies.

## Contact

For technical questions, contact [the ITS Spectrum Monitoring Team](mailto:spectrummonitoring@ntia.gov).

## Disclaimer

Certain commercial equipment, instruments, or materials are identified in this project
were used for the convenience of the developers. In no case does such identification
imply recommendation or endorsement by the National Telecommunications and Information
Administration, nor does it imply that the material or equipment identified is necessarily
the best available for the purpose.
