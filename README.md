# 1. NTIA/ITS Tektronix RSA API for Linux Python Wrapper

This Python package provides a module which wraps the [Tektronix Python/Ctypes RSA API](https://github.com/tektronix/RSA_API/tree/master/Python), with the goal of masking the Ctypes dependency and streamlining use of the API in a Python development environment. It implements most available RSA API functionality (see below for more information). Much of the API's documentation is included in docstrings for quick reference during development, but this is not meant as a substitute for the [RSA API Programming Reference manual](https://www.tek.com/spectrum-analyzer/rsa306-manual/rsa306-rsa306b-and-rsa500a-600a-0) offered by Tektronix. This wrapper was primarily developed for use within the [`scos-tekrsa`](https://github.com/ntia/scos-tekrsa) plugin for NTIA/ITS's [`scos-sensor`](https://github.com/ntia/scos-sensor) platform for networked sensor operation, but has proven useful for other applications involving programmatic control of Tektronix RSA devices. Depending on your use case, and especially if you plan to run your program from Windows, it may be worth looking into the [Tektronix Python/Cython RSA API](https://github.com/tektronix/RSA_API/tree/master/Python/Cython%20Version) instead of using this wrapper.

Requires python>=3.9, numpy, and the Tektronix RSA API for Linux.

The `rsa306b_api.py` file requires the `libRSA_API.so` and `libcyusb_shared.so` shared objects from the Tektronix RSA API for Linux, and by default expects to find them in the scos-sensor drivers directory. If you are running without scos-sensor, you will need to specify your drivers directory when instantiating the API wrapper:

# Installation

First, download and install the [RSA API for Linux](https://www.tek.com/spectrum-analyzer/rsa306-software/rsa-application-programming-interface--api-for-64bit-linux--v100014) from Tektronix. Follow the included installation instructions, then copy the `libRSA_API.so` and `libcyusb_shared.so` files into your project.

Next, download the most recent [release](https://github.com/NTIA/tekrsa-api-ntia/releases) of this package, and install it using `pip`:

```
pip install tekrsa-api-ntia-0.3.0.tar.gz
```

# Usage

Once you've followed the installation instructions above, you can interface with a supported Tektronix RSA device from Python as follows:

```python
import rsa_api

# Directory which contains both libRSA_API.so and libcyusb_shared.so
drivers_path = '/path/to/shared_objects/'

# Initialize and connect to RSA device using the API wrapper
rsa306b = rsa_api.RSA(so_dir=drivers_path)

# Example usage: connect, print current center frequency, then disconnect
rsa306b.DEVICE_SearchAndConnect()
print(f"Current Center Frequency (Hz): {rsa306b.CONFIG_GetCenterFreq()}")
rsa306b.DEVICE_Disconnect()

# Print docstrings for any implemented API function
help(rsa306b.IQSTREAM_Tempfile)
help(rsa_api.RSA.IQSTREAM_Tempfile)  # Does not require initalized RSA device
```

## List of API functions NOT implemented

- All functions not supported by the RSA API for Linux (see "Known Issues" below)
- All `DPX`, `PLAYBACK`, `IFSTREAM` and `TRKGEN` functions
- `DEVICE_GetErrorString()`
    - Alternate error handling is implemented.
- `DEVICE_GetNomenclatureW()` and `IQSTREAM_SetDiskFilenameBaseW()`
    - `DEVICE_GetNomenclature()` and `IQSTREAM_SetDiskFilenameBase()` are used instead.
- `IQBLK_GetIQDataCplx()`
    - `IQBLK_GetIQData()` and `IQBLK_GetIQDataDeinterleaved()` are used instead.
- `IQSTREAM_GetIQData()`
    - `IQSTREAM_Tempfile()` is used instead.

## List of API "Helper" functions
A handful of useful functions are included in this wrapper which streamline some common tasks. These "helper functions" include:

- `IQBLK_Acquire()`
- `IQBLK_Configure()`
- `SPECTRUM_Acquire()`
- `IQSTREAM_StatusParser()`
- `IQSTREAM_Tempfile()`
- `DEVICE_SearchAndConnect()`

To read more about these functions, check their docstrings with `help()`.

## Known Issues

Known issues exist in the underlying Tektronix RSA API for Linux. This wrapper is limited by these known issues in certain ways. The list of issues is reproduced from the Tektronix RSA API for Linux release notes, and are up-to-date as of version 1.0.0014:

- No support for API functions related to GNSS, Audio, Power, Ref Time.
- Using RSA607A, Output Level for Tracking Generator cannot be set.
	- Workaround: None.
- When Connect and Disconnect procedure is repeatedly run for extended time duration (> 2 hours), segmentation fault is observed.
	- Workaround: Disconnect the USB RF Instrument by removing from USB 3.0 port and connect again.
- Spectrum Sweep speed is slow (less than 1GHz/s) for span more than 3GHz.
	- Workaround: None.

## Running Tests

A testing file is included in the `tests` directory of this repository. The test uses `unittest` to test supported API functions. Running a test requires an RSA device to be connected. The same test is used for any supported RSA device, with some tests being enabled, disabled, or modified as needed depending on the device's specific supported API functions. For example, tests of the preamp configuration are not run when testing with an RSA which does not have a preamp.

From the top level directory of this repository, run the test, with segmentation fault handling, by running:

`python3 -q -X faulthandler tests/rsa_api_test.py <path-to-shared-objects>`

Replacing `<path-to-shared-objects>` with the path to a directory containing both `libRSA_API.so` and `libcyusb_shared.so`.

This testing code was been adapted from the [Tektronix Cython RSA API testing code for the 306B](https://github.com/tektronix/RSA_API/blob/master/Python/Cython%20Version/test_rsa306b.py) and [for the 500A/600A series devices](https://github.com/tektronix/RSA_API/blob/master/Python/Cython%20Version/test_rsa500-600.py). In addition to adapting this code to work with this API wrapper, various tests were also added which were not present in the original versions, and the test was made to be universal for all supported RSA devices.

# Development

## Building the Python Package

From the top level directory in this repository, run:

`python3 -m pip install --upgrade build`
`python3 -m build`

TO 

## Contact

For technical questions, contact Anthony Romaniello, aromaniello@ntia.gov