# 1. Tektronix RSA 306B API Wrapper

The file wraps the [Tektronix Python/Ctypes RSA API](https://github.com/tektronix/RSA_API/tree/master/Python), with the goal of masking the Ctypes dependency and streamlining use of the API in a Python development environment. It implements the API functions for the RSA 306B, although many of these functions are identical for other RSA devices. Some API documentation is included in docstrings for quick reference during development, but this is not meant as a substitute for the [RSA API Programming Reference manual](https://www.tek.com/spectrum-analyzer/rsa306-manual/rsa306-rsa306b-and-rsa500a-600a-0) offered by Tektronix. This wrapper was primarily developed for use within the [`scos-tekrsa`](https://github.com/ntia/scos-tekrsa) plugin for NTIA/ITS's [`scos-sensor`](https://github.com/ntia/scos-sensor) platform for networked sensor operation, though it may be useful or extensible for other applications.

This wrapper was developed using v1.0.0014 of the RSA API for Linux.

The `rsa306b_api.py` file requires the `libRSA_API.so` and `libcyusb_shared.so` shared objects from the Tektronix RSA API for Linux, and by default expects to find them in the scos-sensor drivers directory. If you are running without scos-sensor, you will need to specify your drivers directory when instantiating the API wrapper:

```python
from rsa306b_api import *
rsa = RSA306B(so_dir='/path/to/shared_objects/')
rsa.DEVICE_Connect(0) # Example usage
```

Some helper methods have been included, which aim to make some common tasks a bit easier to perform. These are included at the very bottom of the `rsa306b_api.py` file.

Depending on your use case, and especially if you plan to run your program from Windows, it may be worth looking into the [Tektronix Python/Cython RSA API](https://github.com/tektronix/RSA_API/tree/master/Python/Cython%20Version).

## 2. List of API functions NOT implemented

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

## 3. Known Issues

Known issues exist in the underlying Tektronix RSA API for Linux. This wrapper is limited by these known issues in certain ways. The list of issues is reproduced from the Tektronix RSA API for Linux release notes, and are up-to-date as of version 1.0.0014:

- No support for API functions related to GNSS, Audio, Power, Ref Time.
- Using RSA607A, Output Level for Tracking Generator cannot be set.
	- Workaround: None.
- When Connect and Disconnect procedure is repeatedly run for extended time duration (> 2 hours), segmentation fault is observed.
	- Workaround: Disconnect the USB RF Instrument by removing from USB 3.0 port and connect again.
- Spectrum Sweep speed is slow (less than 1GHz/s) for span more than 3GHz.
	- Workaround: None.

## 4. Development

If you need to extend this wrapper to support additional API functions, or other Tektronix RSA devices which use the same API, it should be relatively straightforward to do so.

### Requirements

Requires python>=3.6, numpy, and ctypes.

### Running Tests

A testing file, `rsa306b_api_test.py` is included, which uses unittest to test `rsa306b_api.py`. Running tests requires a connected RSA 306B device. It also requires adding the path to the two shared objects, `libRSA_API.so` and `libcyusb_shared.so`, in the top of the `rsa306b_api_test.py` file, where it is stored as a variable called `TEST_SO_DIR`. There is a placeholder value in place by default, which will need to be replaced with the correct path.

Run the test, with segmentation fault handling, by running:

`python3 -q -X faulthandler rsa306b_api_test.py`

This testing code was been adapted from the [Tektronix Cython RSA API testing code for the 306B](https://github.com/tektronix/RSA_API/blob/master/Python/Cython%20Version/test_rsa306b.py). In addition to adapting this code to work with this API wrapper, various tests were also added which were not present in the original version.

## 5. Contact

For technical questions, contact Anthony Romaniello, aromaniello@ntia.gov