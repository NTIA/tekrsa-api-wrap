"""
Written for Tektronix RSA API for Linux v1.0.0014
Refer to the RSA API Programming Reference Manual for details
on any functions implemented from this module.
"""

import logging
import tempfile
from ctypes import *
from enum import Enum
from os.path import abspath, join
from time import sleep
from typing import Any, Union

import numpy as np

logger = logging.getLogger(__name__)
# GLOBAL CONSTANTS

_DEVSRCH_MAX_NUM_DEVICES = 20  # Max num. of devices that could be found
_DEVSRCH_SERIAL_MAX_STRLEN = 100  # Char array size allocated for serial number string
_DEVSRCH_TYPE_MAX_STRLEN = 20  # Char array size allocated for device type string
_DEVINFO_MAX_STRLEN = 100  # Char array max size to allocate for DEVICE_Get* functions
_FREQ_REF_USER_SETTING_STRLEN = (
    200  # Max. characters in frequency reference user setting string
)

# ENUMERATION TUPLES

_DEV_EVENT = ("OVERRANGE", "TRIGGER", "1PPS")
_FREQ_REF_SOURCE = ("INTERNAL", "EXTREF", "GNSS", "USER")
_IQS_OUT_DEST = ("CLIENT", "FILE_TIQ", "FILE_SIQ", "FILE_SIQ_SPLIT")
_IQS_OUT_DTYPE = ("SINGLE", "INT32", "INT16", "SINGLE_SCALE_INT32")
_NUMPY_IQS_OUT_DTYPE = (np.float32, np.int32, np.int16, np.float32)
_SPECTRUM_DETECTORS = ("PosPeak", "NegPeak", "AverageVRMS", "Sample")
_SPECTRUM_TRACES = ("Trace1", "Trace2", "Trace3")
_SPECTRUM_VERTICAL_UNITS = ("dBm", "Watt", "Volt", "Amp", "dBmV")
_SPECTRUM_WINDOWS = (
    "Kaiser",
    "Mil6dB",
    "BlackmanHarris",
    "Rectangular",
    "FlatTop",
    "Hann",
)
_TRIGGER_MODE = ("freerun", "triggered")
_TRIGGER_SOURCE = ("External", "IFPowerLevel")
_TRIGGER_TRANSITION = ("LH", "HL", "Either")

# CUSTOM DATA STRUCTURES


class _DeviceInfo(Structure):
    _fields_ = [
        ("nomenclature", c_char * _DEVINFO_MAX_STRLEN),
        ("serialNum", c_char * _DEVINFO_MAX_STRLEN),
        ("apiVersion", c_char * _DEVINFO_MAX_STRLEN),
        ("fwVersion", c_char * _DEVINFO_MAX_STRLEN),
        ("fpgaVersion", c_char * _DEVINFO_MAX_STRLEN),
        ("hwVersion", c_char * _DEVINFO_MAX_STRLEN),
    ]


class _FreqRefUserInfo(Structure):
    _fields_ = [
        ("isvalid", c_bool),
        ("dacValue", c_uint32),
        ("datetime", c_char * _DEVINFO_MAX_STRLEN),
        ("temperature", c_double),
    ]


class _SpectrumLimits(Structure):
    _fields_ = [
        ("maxSpan", c_double),
        ("minSpan", c_double),
        ("maxRBW", c_double),
        ("minRBW", c_double),
        ("maxVBW", c_double),
        ("minVBW", c_double),
        ("maxTraceLength", c_int),  # Incorrectly documented as a double
        ("minTraceLength", c_int),  # Incorrectly documented as a double
    ]


class _SpectrumSettings(Structure):
    _fields_ = [
        ("span", c_double),
        ("rbw", c_double),
        ("enableVBW", c_bool),
        ("vbw", c_double),
        ("traceLength", c_int),  # Must be an odd number
        ("window", c_int),  # Really a SpectrumWindows enum value
        ("verticalUnit", c_int),  # Really a SpectrumVerticalUnits enum value
        ("actualStartFreq", c_double),
        ("actualStopFreq", c_double),
        ("actualFreqStepSize", c_double),
        ("actualRBW", c_double),
        ("actualVBW", c_double),
        ("actualNumIQSamples", c_int),
    ]


class _SpectrumTraceInfo(Structure):
    _fields_ = [
        ("timestamp", c_uint64),
        ("acqDataStatus", c_uint16),
    ]


class _IQBlkAcqInfo(Structure):
    _fields_ = [
        ("sample0Timestamp", c_uint64),
        ("triggerSampleIndex", c_uint64),
        ("triggerTimestamp", c_uint64),
        ("acqStatus", c_uint32),
    ]


class _IQStreamFileInfo(Structure):  # "IQSTRMFILEINFO" in RSA_API.h
    _fields_ = [
        ("numberSamples", c_uint64),
        ("sample0Timestamp", c_uint64),
        ("triggerSampleIndex", c_uint64),
        ("triggerTimestamp", c_uint64),
        ("acqStatus", c_uint32),
        ("filenames", POINTER(c_wchar_p)),
    ]


class _IQStreamIQInfo(Structure):  # "IQSTRMIQINFO" in RSA_API.h
    _fields_ = [
        ("timestamp", c_uint64),
        ("triggerCount", c_int),
        ("triggerIndices", POINTER(c_int)),
        ("scaleFactor", c_double),
        ("acqStatus", c_uint32),
    ]


# ERROR HANDLING


class RSAError(Exception):
    def __init__(self, err_txt=""):
        self.err_txt = err_txt
        err = f"RSA Error: {self.err_txt}"
        super().__init__(err)


class RSA:
    def __init__(self, so_dir: str = "/drivers/"):
        """Load the RSA USB Driver"""
        # Param. 'so_dir' is the directory containing libRSA_API.so and
        # libcyusb_shared.so.
        rtld_lazy = 0x0001
        lazy_load = rtld_lazy | RTLD_GLOBAL
        self.rsa = CDLL(join(abspath(so_dir), "libRSA_API.so"), lazy_load)
        self.usb_api = CDLL(join(abspath(so_dir), "libcyusb_shared.so"), lazy_load)

    """ ERROR HANDLING """

    class ReturnStatus(Enum):
        noError = 0

        # Connection
        errorNotConnected = 101
        errorIncompatibleFirmware = 102
        errorBootLoaderNotRunning = 103
        errorTooManyBootLoadersConnected = 104
        errorRebootFailure = 105
        errorGNSSNotInstalled = 106
        errorGNSSNotEnabled = 107

        # POST
        errorPOSTFailureFPGALoad = 201
        errorPOSTFailureHiPower = 202
        errorPOSTFailureI2C = 203
        errorPOSTFailureGPIF = 204
        errorPOSTFailureUsbSpeed = 205
        errorPOSTDiagFailure = 206
        errorPOSTFailure3P3VSense = 207
        errorPOSTLinkFailure = 208

        # General Msmt
        errorBufferAllocFailed = 301
        errorParameter = 302
        errorDataNotReady = 303

        # Spectrum
        errorParameterTraceLength = 1101
        errorMeasurementNotEnabled = 1102
        errorSpanIsLessThanRBW = 1103
        errorFrequencyOutOfRange = 1104

        # IF streaming
        errorStreamADCToDiskFileOpen = 1201
        errorStreamADCToDiskAlreadyStreaming = 1202
        errorStreamADCToDiskBadPath = 1203
        errorStreamADCToDiskThreadFailure = 1204
        errorStreamedFileInvalidHeader = 1205
        errorStreamedFileOpenFailure = 1206
        errorStreamingOperationNotSupported = 1207
        errorStreamingFastForwardTimeInvalid = 1208
        errorStreamingInvalidParameters = 1209
        errorStreamingEOF = 1210
        errorStreamingIfReadTimeout = 1211
        errorStreamingIfNotEnabled = 1212

        # IQ streaming
        errorIQStreamInvalidFileDataType = 1301
        errorIQStreamFileOpenFailed = 1302
        errorIQStreamBandwidthOutOfRange = 1303
        errorIQStreamingNotEnabled = 1304

        # -----------------
        # Internal errors
        # -----------------
        errorTimeout = 3001
        errorTransfer = 3002
        errorFileOpen = 3003
        errorFailed = 3004
        errorCRC = 3005
        errorChangeToFlashMode = 3006
        errorChangeToRunMode = 3007
        errorDSPLError = 3008
        errorLOLockFailure = 3009
        errorExternalReferenceNotEnabled = 3010
        errorLogFailure = 3011
        errorRegisterIO = 3012
        errorFileRead = 3013
        errorConsumerNotActive = 3014

        errorDisconnectedDeviceRemoved = 3101
        errorDisconnectedDeviceNodeChangedAndRemoved = 3102
        errorDisconnectedTimeoutWaitingForADcData = 3103
        errorDisconnectedIOBeginTransfer = 3104
        errorOperationNotSupportedInSimMode = 3015
        errorDisconnectedIOFinishTransfer = 3016

        errorFPGAConfigureFailure = 3201
        errorCalCWNormFailure = 3202
        errorSystemAppDataDirectory = 3203
        errorFileCreateMRU = 3204
        errorDeleteUnsuitableCachePath = 3205
        errorUnableToSetFilePermissions = 3206
        errorCreateCachePath = 3207
        errorCreateCachePathBoost = 3208
        errorCreateCachePathStd = 3209
        errorCreateCachePathGen = 3210
        errorBufferLengthTooSmall = 3211
        errorRemoveCachePath = 3212
        errorGetCachingDirectoryBoost = 3213
        errorGetCachingDirectoryStd = 3214
        errorGetCachingDirectoryGen = 3215
        errorInconsistentFileSystem = 3216

        errorWriteCalConfigHeader = 3301
        errorWriteCalConfigData = 3302
        errorReadCalConfigHeader = 3303
        errorReadCalConfigData = 3304
        errorEraseCalConfig = 3305
        errorCalConfigFileSize = 3306
        errorInvalidCalibConstantFileFormat = 3307
        errorMismatchCalibConstantsSize = 3308
        errorCalConfigInvalid = 3309

        # flash
        errorFlashFileSystemUnexpectedSize = 3401
        errorFlashFileSystemNotMounted = 3402
        errorFlashFileSystemOutOfRange = 3403
        errorFlashFileSystemIndexNotFound = 3404
        errorFlashFileSystemReadErrorCRC = 3405
        errorFlashFileSystemReadFileMissing = 3406
        errorFlashFileSystemCreateCacheIndex = 3407
        errorFlashFileSystemCreateCachedDataFile = 3408
        errorFlashFileSystemUnsupportedFileSize = 3409
        errorFlashFileSystemInsufficentSpace = 3410
        errorFlashFileSystemInconsistentState = 3411
        errorFlashFileSystemTooManyFiles = 3412
        errorFlashFileSystemImportFileNotFound = 3413
        errorFlashFileSystemImportFileReadError = 3414
        errorFlashFileSystemImportFileError = 3415
        errorFlashFileSystemFileNotFoundError = 3416
        errorFlashFileSystemReadBufferTooSmall = 3417
        errorFlashWriteFailure = 3418
        errorFlashReadFailure = 3419
        errorFlashFileSystemBadArgument = 3420
        errorFlashFileSystemCreateFile = 3421
        errorARchiveDirectoryNotFound = 3422
        errorArchiveDirectoryNotWriteable = 3423
        errorArchiveWriteFile = 3424
        errorArchiveGenerateFilename = 3425
        errorArchiveBoost = 3426
        errorArchiveStd = 3427
        errorArchiveGeneric = 3428

        # Aux monitoring
        errorMonitoringNotSupported = 3501
        errorAuxDataNotAvailable = 3502

        # battery
        errorBatteryCommFailure = 3601
        errorBatteryChargerCommFailure = 3602
        errorBatteryNotPresent = 3603

        # EST
        errorESTOutputPathFile = 3701
        errorESTPathNotDirectory = 3702
        errorESTPathDoesntExist = 3703
        errorESTUnableToOpenLog = 3704
        errorESTUnableToOpenLimits = 3705

        # Revision information
        errorRevisionDataNotFound = 3801

        # alignment
        error112MHzAlignmentSignalLevelTooLow = 3901
        error10MHzAlignmentSignalLevelTooLow = 3902
        errorInvalidCalConstant = 3903
        errorNormalizationCacheInvalid = 3904
        errorInvalidAlignmentCache = 3905
        errorLockExtRefAfterAlignment = 3906

        # Triggering
        errorTriggerSystem = 4000

        # VNA
        errorVNAUnsupportedConfiguration = 4100

        # MFC
        errorMFCHWNotPresent = 4200
        errorMFCWriteCalFile = 4201
        errorMFCReadCalFile = 4202
        errorMFCFileFormatError = 4203
        errorMFCFlashCorruptDataError = 4204

        # acq status
        errorADCOverrange = 9000  # must not change the location of these error codes without coordinating with MFG TEST
        errorOscUnlock = 9001

        errorNotSupported = 9901

        errorPlaceholder = 9999
        notImplemented = -1

    def err_check(self, rs):
        """Obtain internal API ErrorStatus and pass to RSAError."""
        if self.ReturnStatus(rs) != self.ReturnStatus.noError:
            raise RSAError(self.ReturnStatus(rs).name)

    # INPUT VALIDATION

    @staticmethod
    def check_range(
        in_var: Union[float, int],
        min_val: Union[float, int],
        max_val: Union[float, int],
        incl: bool = True,
    ) -> Union[float, int]:
        """Check if input is in valid range, inclusive or exclusive"""
        if incl:
            if min_val <= in_var <= max_val:
                return in_var
            else:
                raise ValueError(
                    f"Input must be in range {min_val} to {max_val}, inclusive."
                )
        else:
            if min_val < in_var < max_val:
                return in_var
            else:
                raise ValueError(
                    f"Input must be in range {min_val} to {max_val}, exclusive."
                )

    @staticmethod
    def check_int(value: Any) -> int:
        """Check if input is an integer."""
        if type(value) is int:
            return value
        elif type(value) is float and value.is_integer():
            # Accept floats if they are whole numbers
            return int(value)
        else:
            raise TypeError("Input must be an integer.")

    @staticmethod
    def check_string(value: Any) -> str:
        """Check if input is a string."""
        if type(value) is str:
            return value
        else:
            raise TypeError("Input must be a string.")

    @staticmethod
    def check_num(value: Any) -> Union[float, int]:
        """Check if input is a number (float or int)."""
        if type(value) is int or type(value) is float:
            return value
        else:
            raise TypeError("Input must be a number (float or int).")

    @staticmethod
    def check_bool(value: Any) -> bool:
        """Check if input is a boolean."""
        if type(value) is bool:
            return value
        else:
            raise TypeError("Input must be a boolean.")

    # ALIGNMENT METHODS

    def ALIGN_GetAlignmentNeeded(self) -> bool:
        """
        Determine if an alignment is needed or not.

        Returns
        -------
        bool
            True indicates an alignment is needed, False for not needed.
        """
        needed = c_bool()
        self.err_check(self.rsa.ALIGN_GetAlignmentNeeded(byref(needed)))
        return needed.value

    def ALIGN_GetWarmupStatus(self) -> bool:
        """
        Report device warm-up status.

        Returns
        -------
        bool
            True indicates device warm-up interval reached.
            False indicates warm-up has not been reached
        """
        warmed_up = c_bool()
        self.err_check(self.rsa.ALIGN_GetWarmupStatus(byref(warmed_up)))
        return warmed_up.value

    def ALIGN_RunAlignment(self) -> None:
        """Run the device alignment process."""
        self.err_check(self.rsa.ALIGN_RunAlignment())

    # AUDIO METHODS NOT IMPLEMENTED
    # BROKEN IN RSA API FOR LINUX v1.0.0014

    # CONFIG METHODS

    def CONFIG_GetCenterFreq(self) -> float:
        """Return the current center frequency in Hz."""
        cf = c_double()
        self.err_check(self.rsa.CONFIG_GetCenterFreq(byref(cf)))
        return cf.value

    def CONFIG_GetExternalRefEnable(self) -> bool:
        """
        Return the state of the external reference.

        Returns
        -------
        bool
            True means external reference is enabled, False means disabled.
        """
        ext_ref_en = c_bool()
        self.err_check(self.rsa.CONFIG_GetExternalRefEnable(byref(ext_ref_en)))
        return ext_ref_en.value

    def CONFIG_GetExternalRefFrequency(self) -> float:
        """
        Return the frequency, in Hz, of the external reference.

        Returns
        -------
        float
            The external reference frequency, measured in Hz.

        Raises
        ------
        RSAError
            If there is no external reference input in use.
        """
        src = self.CONFIG_GetFrequencyReferenceSource()
        if src == _FREQ_REF_SOURCE[0]:
            raise RSAError("External frequency reference not in use.")
        else:
            ext_freq = c_double()
            self.err_check(self.rsa.CONFIG_GetExternalRefFrequency(byref(ext_freq)))
            return ext_freq.value

    def CONFIG_GetFrequencyReferenceSource(self) -> str:
        """
        Return a string representing the frequency reference source.

        Returns
        -------
        string
            Name of the frequency reference source. Valid results:
                INTERNAL : Internal frequency reference.
                EXTREF : External (Ref In) frequency reference.
                GNSS : Internal GNSS receiver reference
                USER : Previously set USER setting, or, if none, INTERNAL.
        """
        src = c_int()
        self.err_check(self.rsa.CONFIG_GetFrequencyReferenceSource(byref(src)))
        return _FREQ_REF_SOURCE[src.value]

    def CONFIG_GetMaxCenterFreq(self) -> float:
        """Return the maximum center frequency in Hz."""
        max_cf = c_double()
        self.err_check(self.rsa.CONFIG_GetMaxCenterFreq(byref(max_cf)))
        return max_cf.value

    def CONFIG_GetMinCenterFreq(self) -> float:
        """Return the minimum center frequency in Hz."""
        min_cf = c_double()
        self.err_check(self.rsa.CONFIG_GetMinCenterFreq(byref(min_cf)))
        return min_cf.value

    def CONFIG_GetReferenceLevel(self) -> float:
        """Return the current reference level, measured in dBm."""
        ref_level = c_double()
        self.err_check(self.rsa.CONFIG_GetReferenceLevel(byref(ref_level)))
        return ref_level.value

    def CONFIG_Preset(self) -> None:
        """
        Set the connected device to preset values.
        """
        self.err_check(self.rsa.CONFIG_Preset())
        # For some reason, the record length is not successfully set.
        # Manual override:
        self.err_check(self.rsa.IQBLK_SetIQRecordLength(1024))

    def CONFIG_SetCenterFreq(self, cf: Union[float, int]) -> None:
        """
        Set the center frequency value, in Hz.

        Parameters
        ----------
        cf : float or int
            Value to set center frequency, in Hz.
        """
        cf = RSA.check_num(cf)
        cf = RSA.check_range(
            cf, self.CONFIG_GetMinCenterFreq(), self.CONFIG_GetMaxCenterFreq()
        )
        self.err_check(self.rsa.CONFIG_SetCenterFreq(c_double(cf)))

    def CONFIG_DecodeFreqRefUserSettingString(self, i_usstr: str) -> dict:
        """
        Decode a formatted User setting string into component elements.

        Parameters
        ----------
        i_usstr: A formatted User setting string.

        Returns
        -------
        A dict with keys:
            'isvalid' (bool) : True if the dict contains valid data.
            'dacValue' (int) : Control DAC value
            'datetime' (str) : Datetime string, formatted "YYYY-MM-DDThh:mm:ss"
            'temperature' (float) : Device temperature when user setting data
                was created.
        """
        i_usstr = c_char_p(i_usstr.encode("utf-8"))
        o_fui = _FreqRefUserInfo()
        self.err_check(
            self.rsa.CONFIG_DecodeFreqRefUserSettingString(i_usstr, byref(o_fui))
        )
        try:
            logger.debug(f"FreqRefUserInfo.isvalid {o_fui.isvalid}")
            logger.debug(f"FreqRefUserInfo.dacValue {o_fui.dacValue}")
            logger.debug(f"FreqRefUserInfo.datetime: {o_fui.datetime}")
            logger.debug(f"FreqRefUserInfo.temperature: {o_fui.temperature}")
        except Exception as ex:
            logger.debug(f"unable to print decoded values: {ex}")

        fui = {
            "isvalid": o_fui.isvalid,
            "dacValue": o_fui.dacValue,
            "datetime": o_fui.datetime.decode("utf-8"),
            "temperature": o_fui.temperature,
        }
        return fui

    def CONFIG_SetExternalRefEnable(self, ext_ref_en: bool) -> None:
        """
        Enable or disable the external reference.

        Parameters
        ----------
        ext_ref_en : bool
            True enables the external reference. False disables it.
        """
        ext_ref_en = RSA.check_bool(ext_ref_en)
        self.err_check(self.rsa.CONFIG_SetExternalRefEnable(c_bool(ext_ref_en)))

    def CONFIG_SetFrequencyReferenceSource(self, src: str) -> None:
        """
        Select the device frequency reference source.

        Parameters
        ----------
        src : string
            Frequency reference source selection. Valid settings:
                INTERNAL : Internal frequency reference.
                EXTREF : External (Ref In) frequency reference.
                GNSS : Internal GNSS receiver reference
                USER : Previously set USER setting, or, if none, INTERNAL.

        Raises
        ------
        RSAError
            If the input string does not match one of the valid settings.
        """
        src = RSA.check_string(src)
        if src in _FREQ_REF_SOURCE:
            device_name = self.DEVICE_GetNomenclature()
            if src == "GNSS" and device_name in ["RSA306", "RSA306B"]:
                raise RSAError(f"{device_name} device does not support GNSS reference.")
            else:
                value = c_int(_FREQ_REF_SOURCE.index(src))
                self.err_check(self.rsa.CONFIG_SetFrequencyReferenceSource(value))
        else:
            raise RSAError("Input does not match a valid setting.")

    def CONFIG_GetFreqRefUserSetting(self) -> str:
        """
        Get the Frequency Reference User-source setting value.

        Returns
        --------
        A formatted user setting string containing:
        "$FRU,<devType>,<devSN>,<dacVal>,<dateTime>,<devTemp>*<CS>"
        Where:
            <devType> : device type
            <devSN> : device serial number
            <dacVal> : integer DAC value
            <dateTime> : date and time of creation, format:
                "YYY-MM-DDThh:mm:ss"
            <devTemp> : device temperature (degC) at creation
            <CS> : integer checksum of characters before '*'

        If the User setting is not valid, then the user string result
        returns the string "Invalid User Setting"
        """
        o_usstr = (c_char * _FREQ_REF_USER_SETTING_STRLEN)()
        self.err_check(self.rsa.CONFIG_GetFreqRefUserSetting(byref(o_usstr)))
        return o_usstr.value.decode("utf-8")

    def CONFIG_SetFreqRefUserSetting(self, i_usstr: Union[str, None] = None) -> None:
        """
        Set the Frequency Reference User-source setting value.

        Parameters
        ----------
        i_usstr: The user setting string, which must be formatted as
            by CONFIG_GetFreqRefUserSetting(). If this parameter is
            None (the default behavior), the current frequency reference
            setting is copied to the User setting memory.
        """
        if i_usstr is None:
            self.err_check(self.rsa.CONFIG_SetFreqRefUserSetting(None))
        else:
            RSA.check_string(i_usstr)
            if i_usstr == "Invalid User Setting":
                raise RSAError("User setting is invalid.")
            elif len(i_usstr) > _FREQ_REF_USER_SETTING_STRLEN:
                raise RSAError(
                    f"Frequency reference setting '{i_usstr}' is longer than the maximum"
                    + f"allowed length {_FREQ_REF_USER_SETTING_STRLEN}"
                )
            i_usstr = c_char_p(i_usstr.encode("utf-8"))
            self.err_check(self.rsa.CONFIG_SetFreqRefUserSetting(i_usstr))

    def CONFIG_SetReferenceLevel(self, ref_level: Union[float, int]) -> None:
        """
        Set the reference level

        Parameters
        ----------
        ref_level : float or int
            Reference level, in dBm. Valid range: -130 dBm to 30 dBm.
        """
        ref_level = RSA.check_num(ref_level)
        ref_level = RSA.check_range(ref_level, -130, 30)
        self.err_check(self.rsa.CONFIG_SetReferenceLevel(c_double(ref_level)))

    def CONFIG_GetAutoAttenuationEnable(self) -> bool:
        """
        Return the signal path auto-attenuation enable state.

        Returns
        -------
        bool
            True indicates that auto-attenuation operation is enabled.
            False indicated it is disabled.
        """
        enable = c_bool()
        self.err_check(self.rsa.CONFIG_GetAutoAttenuationEnable(byref(enable)))
        return enable.value

    def CONFIG_SetAutoAttenuationEnable(self, enable: bool) -> None:
        """
        Set the signal path auto-attenuation enable state.

        The device Run state is cycled in order to apply the setting.

        Parameters
        ----------
        enable : bool
            True enables auto-attenuation operation. False disables it.
        """
        enable = RSA.check_bool(enable)
        self.rsa.DEVICE_Stop()
        self.err_check(self.rsa.CONFIG_SetAutoAttenuationEnable(c_bool(enable)))
        self.rsa.DEVICE_Run()

    def CONFIG_GetRFPreampEnable(self) -> bool:
        """
        Return the state of the RF Preamplifier.

        Returns
        -------
        bool
            True indicates the RF Preamplifier is enabled. False indicates
            it is disabled.
        """
        enable = c_bool()
        self.err_check(self.rsa.CONFIG_GetRFPreampEnable(byref(enable)))
        return enable.value

    def CONFIG_SetRFPreampEnable(self, enable: bool) -> None:
        """
        Set the RF Preamplifier enable state.

        The device Run state is cycled in order to apply the setting.

        Parameters
        ----------
        enable : bool
            True enables the RF Preamplifier. False disables it.
        """
        enable = RSA.check_bool(enable)
        self.rsa.DEVICE_Stop()
        self.err_check(self.rsa.CONFIG_SetRFPreampEnable(c_bool(enable)))
        self.rsa.DEVICE_Run()

    def CONFIG_GetRFAttenuator(self) -> float:
        """
        Return the setting of the RF Input Attenuator.

        Returns
        -------
        float
            The RF Input Attenuator setting value, in dB.
        """
        value = c_double()
        self.err_check(self.rsa.CONFIG_GetRFAttenuator(byref(value)))
        return value.value

    def CONFIG_SetRFAttenuator(self, value: Union[float, int]) -> None:
        """
        Set the RF Input Attenuator value manually.

        The device Run state is cycled in order to apply the setting.

        Parameters
        ----------
        value : float
            The desired RF Input Attenuator setting, in dB. Values are
            rounded to the nearest integer, in the range -51 dB to 0 dB.
        """
        value = RSA.check_num(value)
        value = RSA.check_range(value, -51, 0)
        self.rsa.DEVICE_Stop()
        self.err_check(self.rsa.CONFIG_SetRFAttenuator(c_double(value)))
        self.rsa.DEVICE_Run()

    # DEVICE METHODS

    def DEVICE_Connect(self, device_id: int = 0) -> None:
        """
        Connect to a device specified by the device_id parameter.

        Parameters
        ----------
        device_id : int
            The device ID of the target device. Defaults to zero.
        """
        device_id = RSA.check_int(device_id)
        device_id = RSA.check_range(device_id, 0, float("inf"))
        self.err_check(self.rsa.DEVICE_Connect(c_int(device_id)))

    def DEVICE_Disconnect(self) -> None:
        """Stop data acquisition and disconnect from connected device."""
        self.err_check(self.rsa.DEVICE_Disconnect())

    def DEVICE_GetEnable(self) -> bool:
        """
        Query the run state.

        Returns
        -------
        bool
           True indicates the device is in the run state. False indicates
           that it is in the stop state.
        """
        enable = c_bool()
        self.err_check(self.rsa.DEVICE_GetEnable(byref(enable)))
        return enable.value

    def DEVICE_GetFPGAVersion(self) -> str:
        """
        Retrieve the FPGA version number.

        Returns
        -------
        string
            The FPGA version number.
        """
        fpga_version = (c_char * _DEVINFO_MAX_STRLEN)()
        self.err_check(self.rsa.DEVICE_GetFPGAVersion(byref(fpga_version)))
        return fpga_version.value.decode("utf-8")

    def DEVICE_GetFWVersion(self) -> str:
        """
        Retrieve the firmware version number.

        Returns
        -------
        string
            The firmware version number.
        """
        fw_version = (c_char * _DEVINFO_MAX_STRLEN)()
        self.err_check(self.rsa.DEVICE_GetFWVersion(byref(fw_version)))
        return fw_version.value.decode("utf-8")

    def DEVICE_GetHWVersion(self) -> str:
        """
        Retrieve the hardware version number.

        Returns
        -------
        string
            The hardware version number.
        """
        hw_version = (c_char * _DEVINFO_MAX_STRLEN)()
        self.err_check(self.rsa.DEVICE_GetHWVersion(byref(hw_version)))
        return hw_version.value.decode("utf-8")

    def DEVICE_GetNomenclature(self) -> str:
        """
        Retrieve the name of the device.

        Returns
        -------
        string
            Name of the device.
        """
        nomenclature = (c_char * _DEVINFO_MAX_STRLEN)()
        self.err_check(self.rsa.DEVICE_GetNomenclature(byref(nomenclature)))
        return nomenclature.value.decode("utf-8")

    def DEVICE_GetSerialNumber(self) -> str:
        """
        Retrieve the serial number of the device.

        Returns
        -------
        string
            Serial number of the device.
        """
        serial_num = (c_char * _DEVSRCH_SERIAL_MAX_STRLEN)()
        self.err_check(self.rsa.DEVICE_GetSerialNumber(byref(serial_num)))
        return serial_num.value.decode("utf-8")

    def DEVICE_GetAPIVersion(self) -> str:
        """
        Retrieve the API version number.

        Returns
        -------
        string
            The API version number.
        """
        api_version = (c_char * _DEVINFO_MAX_STRLEN)()
        self.err_check(self.rsa.DEVICE_GetAPIVersion(byref(api_version)))
        return api_version.value.decode("utf-8")

    def DEVICE_PrepareForRun(self) -> None:
        """
        Put the system in a known state, ready to stream data.
        """
        self.err_check(self.rsa.DEVICE_PrepareForRun())

    def DEVICE_GetInfo(self) -> dict:
        """
        Retrieve multiple device and information strings.

        Returns
        -------
        dict
            Keys: nomenclature, serialNum, fwVersion, fpgaVersion,
                  hwVersion, apiVersion
        """
        dev_info = _DeviceInfo()
        self.err_check(self.rsa.DEVICE_GetInfo(byref(dev_info)))
        info = {
            "nomenclature": dev_info.nomenclature.decode("utf-8"),
            "serialNum": dev_info.serialNum.decode("utf-8"),
            "apiVersion": dev_info.apiVersion.decode("utf-8"),
            "fwVersion": dev_info.fwVersion.decode("utf-8"),
            "fpgaVersion": dev_info.fpgaVersion.decode("utf-8"),
            "hwVersion": dev_info.hwVersion.decode("utf-8"),
        }
        return info

    def DEVICE_GetOverTemperatureStatus(self) -> bool:
        """
        Query device for over-temperature status.

        Returns
        -------
        bool
            Over-temperature status. True indicates device above nominal
            safe operating range, and may result in reduced accuracy and/
            or damage to the device. False indicates device temperature is
            within the safe operating range.
        """
        over_temp = c_bool()
        self.err_check(self.rsa.DEVICE_GetOverTemperatureStatus(byref(over_temp)))
        return over_temp.value

    def DEVICE_Reset(self, device_id: int = -1) -> None:
        """
        Reboot the specified device.

        Parameters
        ----------
        device_id : int
            The device ID of the target device.

        Raises
        ------
        RSAError
            If multiple devices are found but no device ID is specified.
        """
        device_id = RSA.check_int(device_id)
        self.DEVICE_Disconnect()
        found_devices = self.DEVICE_Search()
        num_found = len(found_devices)
        if num_found == 1:
            device_id = 0
        elif num_found > 1 and device_id == -1:
            raise RSAError("Multiple devices found, but no ID specified.")
        self.err_check(self.rsa.DEVICE_Reset(c_int(device_id)))

    def DEVICE_Run(self) -> None:
        """Start data acquisition."""
        self.err_check(self.rsa.DEVICE_Run())

    def DEVICE_Search(self) -> dict:
        """
        Search for connectable devices.

        Returns
        -------
        dict
            Found devices: {device_id : (deviceSerial, deviceType)}.
                device_id : int
                deviceSerial : string
                deviceType : string

        Raises
        ------
        RSAError
            If no devices are found.
        """
        num_found = c_int()
        dev_ids = (c_int * _DEVSRCH_MAX_NUM_DEVICES)()
        dev_serial = (
            (c_char * _DEVSRCH_MAX_NUM_DEVICES) * _DEVSRCH_SERIAL_MAX_STRLEN
        )()
        dev_type = ((c_char * _DEVSRCH_MAX_NUM_DEVICES) * _DEVSRCH_TYPE_MAX_STRLEN)()

        self.err_check(
            self.rsa.DEVICE_Search(
                byref(num_found), byref(dev_ids), dev_serial, dev_type
            )
        )

        found_devices = {
            ID: (dev_serial[ID].value.decode(), dev_type[ID].value.decode())
            for ID in dev_ids
        }

        # If there are no devices, there is still a dict returned
        # with a device ID, but the other elements are empty.
        if found_devices[0] == ("", ""):
            raise RSAError("Could not find a matching Tektronix RSA device.")
        else:
            return found_devices

    def DEVICE_StartFrameTransfer(self) -> None:
        """
        Start data transfer.
        """
        self.err_check(self.rsa.DEVICE_StartFrameTransfer())

    def DEVICE_Stop(self) -> None:
        """
        Stop data acquisition.
        """
        self.err_check(self.rsa.DEVICE_Stop())

    def DEVICE_GetEventStatus(self, event_id: str) -> tuple[bool, int]:
        """
        Return global device real-time event status.

        Parameters
        ----------
        event_id : string
            Identifier for the event status to query. Valid settings:
                OVERRANGE : Overrange event detection.
                TRIGGER : Trigger event detection.
                1PPS : 1PPS event detection (RSA500A/600A only).

        Returns
        -------
        occurred : bool
            Indicates whether the event has occurred.
        timestamp : int
            Event occurrence timestamp. Only valid if occurred is True.

        Raises
        ------
        RSAError
            If the input string does not match one of the valid settings.
        """
        occurred = c_bool()
        timestamp = c_uint64()
        event_id = RSA.check_string(event_id)
        if event_id in _DEV_EVENT:
            value = c_int(_DEV_EVENT.index(event_id))
        else:
            raise RSAError("Input string does not match one of the valid settings.")
        self.err_check(
            self.rsa.DEVICE_GetEventStatus(value, byref(occurred), byref(timestamp))
        )
        return occurred.value, timestamp.value

    # GNSS METHODS NOT IMPLEMENTED
    # BROKEN IN RSA API FOR LINUX v1.0.0014

    # IQ BLOCK METHODS

    def IQBLK_GetIQAcqInfo(self) -> tuple[int, int, int, int]:
        """
        Return IQ acquisition status info for the most recent IQ block.

        Returns
        -------
        sample0Timestamp : int
            Timestamp of the first sample of the IQ block record.
        triggerSampleIndex : int
            Index to the sample corresponding to the trigger point.
        triggerTimestamp : int
            Timestamp of the trigger sample.
        acqStatus : int
            "Word" with acquisition status bits. See above for details.
        """
        acq_info = _IQBlkAcqInfo()
        self.err_check(self.rsa.IQBLK_GetIQAcqInfo(byref(acq_info)))
        info = (
            acq_info.sample0Timestamp.value,
            acq_info.triggerSampleIndex.value,
            acq_info.triggerTimestamp.value,
            acq_info.acqStatus.value,
        )
        return info

    def IQBLK_AcquireIQData(self) -> None:
        """
        Initiate an IQ block record acquisition.
        """
        self.err_check(self.rsa.IQBLK_AcquireIQData())

    def IQBLK_GetIQBandwidth(self) -> float:
        """
        Query the IQ bandwidth value.

        Returns
        -------
        float
            The IQ bandwidth value.
        """
        iq_bandwidth = c_double()
        self.err_check(self.rsa.IQBLK_GetIQBandwidth(byref(iq_bandwidth)))
        return iq_bandwidth.value

    def IQBLK_GetIQData(self, req_length: int) -> np.ndarray:
        """
        Retrieve an IQ block data record in a single interleaved array.

        Parameters
        ----------
        req_length : int
            Number of IQ sample pairs requested to be returned.
            The maximum value of reqLength is equal to the recordLength
            value set in IQBLK_SetIQRecordLength(). Smaller values allow
            retrieving partial IQ records.

        Returns
        -------
        Numpy array
            I-data and Q-data stored in a single array.
            I-data is stored at even indexes of the returned array,
            and Q-data is stored at the odd indexes.
        """
        req_length = RSA.check_int(req_length)
        req_length = RSA.check_range(req_length, 2, self.IQBLK_GetIQRecordLength())
        out_length = c_int()
        iq_data = (c_float * (req_length * 2))()
        self.err_check(
            self.rsa.IQBLK_GetIQData(
                byref(iq_data), byref(out_length), c_int(req_length)
            )
        )
        return np.ctypeslib.as_array(iq_data)

    def IQBLK_GetIQDataDeinterleaved(
        self, req_length: int
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Retrieve an IQ block data record in separate I and Q array format.

        Parameters
        ----------
        req_length : int
            Number of IQ samples requested to be returned in data arrays.
            The maximum value of reqLength is equal to the recordLength
            value set in IQBLK_SetIQRecordLength(). Smaller values of
            reqLength allow retrieving partial IQ records.

        Returns
        -------
        iData : Numpy array
            Array of I-data.
        qData : Numpy array
            Array of Q-data.
        """
        req_length = RSA.check_int(req_length)
        req_length = RSA.check_range(req_length, 2, self.IQBLK_GetIQRecordLength())
        i_data = (c_float * req_length)()
        q_data = (c_float * req_length)()
        out_length = c_int()
        self.err_check(
            self.rsa.IQBLK_GetIQDataDeinterleaved(
                byref(i_data), byref(q_data), byref(out_length), c_int(req_length)
            )
        )
        return np.ctypeslib.as_array(i_data), np.ctypeslib.as_array(q_data)

    def IQBLK_GetIQRecordLength(self) -> int:
        """
        Query the IQ record length.

        Returns
        -------
        int
            Number of IQ data samples to be generated with each acquisition.
        """
        record_length = c_int()
        self.err_check(self.rsa.IQBLK_GetIQRecordLength(byref(record_length)))
        return record_length.value

    def IQBLK_GetIQSampleRate(self) -> float:
        """
        Query the IQ sample rate value.

        Returns
        -------
        float
            The IQ sampling frequency, in samples/second.
        """
        iq_sr = c_double()
        self.err_check(self.rsa.IQBLK_GetIQSampleRate(byref(iq_sr)))
        return iq_sr.value

    def IQBLK_GetMaxIQBandwidth(self) -> float:
        """
        Query the maximum IQ bandwidth of the connected device.

        Returns
        -------
        float
            The maximum IQ bandwidth, measured in Hz.
        """
        max_bw = c_double()
        self.err_check(self.rsa.IQBLK_GetMaxIQBandwidth(byref(max_bw)))
        return max_bw.value

    def IQBLK_GetMaxIQRecordLength(self) -> int:
        """
        Query the maximum IQ record length.

        Returns
        -------
        int
            The maximum IQ record length, measured in samples.
        """
        max_iq_rec_len = c_int()
        self.err_check(self.rsa.IQBLK_GetMaxIQRecordLength(byref(max_iq_rec_len)))
        return max_iq_rec_len.value

    def IQBLK_GetMinIQBandwidth(self) -> float:
        """
        Query the minimum IQ bandwidth of the connected device.

        Returns
        -------
        float
            The minimum IQ bandwidth, measured in Hz.
        """
        min_bw = c_double()
        self.err_check(self.rsa.IQBLK_GetMinIQBandwidth(byref(min_bw)))
        return min_bw.value

    def IQBLK_SetIQBandwidth(self, iq_bandwidth: Union[float, int]) -> None:
        """
        Set the IQ bandwidth value.

        Parameters
        ----------
        iq_bandwidth : float or int
            IQ bandwidth value measured in Hz
        """
        iq_bandwidth = RSA.check_num(iq_bandwidth)
        iq_bandwidth = RSA.check_range(
            iq_bandwidth, self.IQBLK_GetMinIQBandwidth(), self.IQBLK_GetMaxIQBandwidth()
        )
        self.err_check(self.rsa.IQBLK_SetIQBandwidth(c_double(iq_bandwidth)))

    def IQBLK_SetIQRecordLength(self, record_length: int) -> None:
        """
        Set the number of IQ samples generated by each IQ block acquisition.

        Parameters
        ----------
        record_length : int
            IQ record length, measured in samples. Minimum value of 2.
        """
        record_length = RSA.check_int(record_length)
        record_length = RSA.check_range(
            record_length, 2, self.IQBLK_GetMaxIQRecordLength()
        )
        self.err_check(self.rsa.IQBLK_SetIQRecordLength(c_int(record_length)))

    def IQBLK_WaitForIQDataReady(self, timeout_msec: int) -> bool:
        """
        Wait for the data to be ready to be queried.

        Parameters
        ----------
        timeout_msec : int
            Timeout value measured in ms.

        Returns
        -------
        bool
            True indicates data is ready for acquisition. False indicates
            the data is not ready and the timeout value is exceeded.
        """
        timeout_msec = RSA.check_int(timeout_msec)
        ready = c_bool()
        self.err_check(
            self.rsa.IQBLK_WaitForIQDataReady(c_int(timeout_msec), byref(ready))
        )
        return ready.value

    # IQ STREAM METHODS

    def IQSTREAM_GetMaxAcqBandwidth(self) -> float:
        """
        Query the maximum IQ bandwidth for IQ streaming.

        Returns
        -------
        float
            The maximum IQ bandwidth supported by IQ streaming, in Hz.
        """
        max_bw_hz = c_double()
        self.err_check(self.rsa.IQSTREAM_GetMaxAcqBandwidth(byref(max_bw_hz)))
        return max_bw_hz.value

    def IQSTREAM_GetMinAcqBandwidth(self) -> float:
        """
        Query the minimum IQ bandwidth for IQ streaming.

        Returns
        -------
        float
            The minimum IQ bandwidth supported by IQ streaming, in Hz.
        """
        min_bw_hz = c_double()
        self.err_check(self.rsa.IQSTREAM_GetMinAcqBandwidth(byref(min_bw_hz)))
        return min_bw_hz.value

    def IQSTREAM_ClearAcqStatus(self) -> None:
        """
        Reset the "sticky" status bits of the acqStatus info element during
        an IQ streaming run interval.
        """
        self.err_check(self.rsa.IQSTREAM_ClearAcqStatus())

    def IQSTREAM_GetAcqParameters(self) -> tuple[float, float]:
        """
        Retrieve the processing parameters of IQ streaming output bandwidth
        and sample rate, resulting from the user's requested bandwidth.

        Returns
        -------
        float: bwHz_act
            Actual acquisition bandwidth of IQ streaming output data in Hz.
        float: srSps
            Actual sample rate of IQ streaming output data in Samples/sec.
        """
        bw_hz_act = c_double()
        sr_sps = c_double()
        self.err_check(
            self.rsa.IQSTREAM_GetAcqParameters(byref(bw_hz_act), byref(sr_sps))
        )
        return bw_hz_act.value, sr_sps.value

    def IQSTREAM_GetDiskFileInfo(self) -> _IQStreamFileInfo:
        """
        Retrieve information about the previous file output operation.

        Returns
        -------
        An _IQStreamFileInfo structure which contains:
        numberSamples : int
            Number of IQ sample pairs written to the file.
        sample0Timestamp : int
            Timestamp of the first sample written to file.
        triggerSampleIndex : int
            Sample index where the trigger event occurred. This is only
            valid if triggering has been enabled. Set to 0 otherwise.
        triggerTimestamp : int
            Timestamp of the trigger event. This is only valid if
            triggering has been enabled. Set to 0 otherwise.
        filenames : strings
        acqStatus : int
            Acquisition status flags for the run interval. Individual bits
            are used as indicators as follows:
                Individual Internal Write Block Status (Bits 0-15, starting
                from LSB):
                    Bits 0-15 indicate status for each internal write block,
                        so may not be very useful. Bits 16-31 indicate the
                        entire run status up to the time of query.
                    Bit 0 : 1 = Input overrange.
                    Bit 1 : 1 = USB data stream discontinuity.
                    Bit 2 : 1 = Input buffer > 75% full (IQStream
                        processing heavily loaded).
                    Bit 3 : 1 = Input buffer overflow (IQStream processing
                        overloaded, data loss has occurred).
                    Bit 4 : 1 = Output buffer > 75% full (File output
                        falling behind writing data).
                    Bit 5 : 1 = Output buffer overflow (File output too
                        slow, data loss has occurred).
                    Bit 6 - Bit 15 : Unused, always 0.
                Entire Run Summary Status ("Sticky Bits"):
                    The bits in this range are essentially the same as Bits
                        0-15, except once they are set (to 1) they remain
                        set for the entire run interval. They can be used to
                        determine if any of the status events occurred at
                        any time during the run.
                    Bit 16 : 1 = Input overrange.
                    Bit 17 : 1 = USB data stream discontinuity.
                    Bit 18 : 1 = Input buffer > 75% full (IQStream
                        processing heavily loaded).
                    Bit 19 : 1 = Input buffer overflow (IQStream processing
                        overloaded, data loss has occurred).
                    Bit 20 : 1 = Output buffer > 75% full (File output
                        falling behind writing data).
                    Bit 21 : 1 = Output buffer overflow (File output too
                        slow, data loss has occurred).
                    Bit 22 - Bit 31 : Unused, always 0.
        """
        file_info = _IQStreamFileInfo()
        self.err_check(self.rsa.IQSTREAM_GetDiskFileInfo(byref(file_info)))
        return file_info

    def IQSTREAM_GetDiskFileWriteStatus(self) -> tuple[bool, bool]:
        """
        Allow monitoring the progress of file output.

        Returns
        -------
        bool: isComplete
            Whether the IQ stream file output writing is complete.
        bool: isWriting
            Whether the IQ stream processing has started writing to file.
        """
        is_complete = c_bool()
        is_writing = c_bool()
        self.err_check(
            self.rsa.IQSTREAM_GetDiskFileWriteStatus(
                byref(is_complete), byref(is_writing)
            )
        )
        return is_complete.value, is_writing.value

    def IQSTREAM_GetEnable(self) -> bool:
        """
        Retrieve the current IQ stream processing state.

        Returns
        -------
        bool
            The current IQ stream processing enable status. True if active,
            False if inactive.
        """
        enabled = c_bool()
        self.err_check(self.rsa.IQSTREAM_GetEnable(byref(enabled)))
        return enabled.value

    def IQSTREAM_GetIQData(
        self, dtype: str, buffer_size: int
    ) -> tuple[np.ndarray, int, _IQStreamIQInfo]:
        """
        Retrieve interleaved IQ data generated by IQ Stream processing.

        Parameters
        ----------
        dtype : str
            IQSTREAM data type, must be one of: "SINGLE" "INT32"
            "INT16" or "SINGLE_SCALE_INT32"
        buffer_size : int
            Configured size of the IQSTREAM buffer, as returned
            by IQSTREAM_GetIQDataBufferSize().

        Returns
        -------
        np.ndarray
            Interleaved IQ data retrieved from the buffer.
        int
            Length of the IQ block retrieved, in samples.
        _IQStreamIQInfo
            IQ Stream info structure, containing the acquisition
            status. Note that the timestamp field of this structure
            seems to give wildly incorrect results.

        Raises
        ------
        ValueError
            If `dtype` is not a valid IQSTREAM data type.
        """
        np_dtype = _NUMPY_IQS_OUT_DTYPE[_IQS_OUT_DTYPE.index(dtype)]
        iqdata = np.empty(2 * buffer_size, np_dtype)
        c_iqdata = np.ctypeslib.as_ctypes(iqdata)
        iqlen = c_int32()
        iqinfo = _IQStreamIQInfo()

        self.err_check(
            self.rsa.IQSTREAM_GetIQData(byref(c_iqdata), byref(iqlen), byref(iqinfo))
        )

        del c_iqdata
        return iqdata, iqlen.value, iqinfo

    def IQSTREAM_GetIQDataBufferSize(self) -> int:
        """
        Get the maximum number of IQ sample pairs to be returned by IQSTREAM_GetData().

        Returns
        -------
        int
            Maximum size IQ output data buffer required when using client
            IQ access. Size value is in IQ sample pairs.
        """
        max_size = c_int()
        self.err_check(self.rsa.IQSTREAM_GetIQDataBufferSize(byref(max_size)))
        return max_size.value

    def IQSTREAM_SetAcqBandwidth(self, bw_hz_req: Union[float, int]) -> None:
        """
        Request the acquisition bandwidth of the output IQ stream samples.

        The device Run state is cycled in order to apply the setting.

        Parameters
        ----------
        bw_hz_req : float or int
            Requested acquisition bandwidth of IQ streaming data, in Hz.
        """
        bw_hz_req = RSA.check_num(bw_hz_req)
        bw_hz_req = RSA.check_range(
            bw_hz_req,
            self.IQSTREAM_GetMinAcqBandwidth(),
            self.IQSTREAM_GetMaxAcqBandwidth(),
        )
        self.rsa.DEVICE_Stop()
        self.err_check(self.rsa.IQSTREAM_SetAcqBandwidth(c_double(bw_hz_req)))
        self.rsa.DEVICE_Run()

    def IQSTREAM_SetDiskFileLength(self, msec: int) -> None:
        """
        Set the time length of IQ data written to an output file.

        Parameters
        ----------
        msec : int
            Length of time in milliseconds to record IQ samples to file.
        """
        msec = RSA.check_int(msec)
        msec = RSA.check_range(msec, 0, float("inf"))
        self.err_check(self.rsa.IQSTREAM_SetDiskFileLength(c_int(msec)))

    def IQSTREAM_SetDiskFilenameBase(self, filename_base: str) -> None:
        """
        Set the base filename for file output.

        Parameters
        ----------
        filename_base : string
            Base filename for file output.
        """
        filename_base = RSA.check_string(filename_base)
        self.err_check(self.rsa.IQSTREAM_SetDiskFilenameBaseW(c_wchar_p(filename_base)))

    def IQSTREAM_SetDiskFilenameSuffix(self, suffix_ctl: int) -> None:
        """
        Set the control that determines the appended filename suffix.

        Parameters
        ----------
        suffix_ctl : int
            The filename suffix control value.
        """
        suffix_ctl = RSA.check_int(suffix_ctl)
        suffix_ctl = RSA.check_range(suffix_ctl, -2, float("inf"))
        self.err_check(self.rsa.IQSTREAM_SetDiskFilenameSuffix(c_int(suffix_ctl)))

    def IQSTREAM_SetIQDataBufferSize(self, req_size: int) -> None:
        """
        Set the requested size, in sample pairs, of the returned IQ record.

        The resulting buffer size is determined by the request and by the
        configured IQ Bandwidth. Set the bandwidth before requesting a buffer
        size, then query the buffer size to get the resulting set value.

        Parameters
        ----------
        req_size : int
            Requested size of IQ output data buffer in IQ sample pairs.
            0 resets to default. 1 sets to minimum size, and 1,000,000
            sets to the maximum size.
        """
        req_size = RSA.check_int(req_size)
        self.err_check(self.rsa.IQSTREAM_SetIQDataBufferSize(c_int(req_size)))

    def IQSTREAM_SetOutputConfiguration(self, dest: str, dtype: str) -> None:
        """
        Set the output data destination and IQ data type.

        Parameters
        ----------
        dest : string
            Destination (sink) for IQ sample output. Valid settings:
                CLIENT : Client application
                FILE_TIQ : TIQ format file (.tiq extension)
                FILE_SIQ : SIQ format file with header and data combined in
                    one file (.siq extension)
                FILE_SIQ_SPLIT : SIQ format with header and data in separate
                    files (.siqh and .siqd extensions)
        dtype : string
            Output IQ data type. Valid settings:
                SINGLE : 32-bit single precision floating point (not valid
                    with TIQ file destination)
                INT32 : 32-bit integer
                INT16 : 16-bit integer
                SINGLE_SCALE_INT32 : 32-bit single precision float, with
                    data scaled the same as INT32 data type (not valid with
                    TIQ file destination)

        Raises
        ------
        RSAError
            If inputs are not valid settings, or if single data type is
            selected along with TIQ file format.
        """
        dest = RSA.check_string(dest)
        dtype = RSA.check_string(dtype)
        if dest in _IQS_OUT_DEST and dtype in _IQS_OUT_DTYPE:
            if dest == "FILE_TIQ" and "SINGLE" in dtype:
                raise RSAError(
                    "Invalid selection of TIQ file with"
                    + " single precision data type."
                )
            else:
                val1 = c_int(_IQS_OUT_DEST.index(dest))
                val2 = c_int(_IQS_OUT_DTYPE.index(dtype))
                self.err_check(self.rsa.IQSTREAM_SetOutputConfiguration(val1, val2))
        else:
            raise RSAError("Input data type or destination string invalid.")

    def IQSTREAM_Start(self) -> None:
        """
        Initialize IQ stream processing and initiate data output.
        """
        self.err_check(self.rsa.IQSTREAM_Start())

    def IQSTREAM_Stop(self) -> None:
        """
        Terminate IQ stream processing and disable data output.
        """
        self.err_check(self.rsa.IQSTREAM_Stop())

    def IQSTREAM_WaitForIQDataReady(self, timeout_msec: int) -> bool:
        """
        Block while waiting for IQ Stream data output.

        Parameters
        ----------
        timeout_msec : int
            Timeout interval in milliseconds.

        Returns
        -------
        bool
            Ready status. True if data is ready, False if data not ready.
        """
        timeout_msec = RSA.check_int(timeout_msec)
        timeout_msec = RSA.check_range(timeout_msec, 0, float("inf"))
        ready = c_bool()
        self.err_check(
            self.rsa.IQSTREAM_WaitForIQDataReady(c_int(timeout_msec), byref(ready))
        )
        return ready.value

    # PLAYBACK METHODS NOT IMPLEMENTED

    # POWER METHODS NOT IMPLEMENTED
    # BROKEN IN RSA API FOR LINUX v1.0.0014

    # SPECTRUM METHODS

    def SPECTRUM_AcquireTrace(self) -> None:
        """
        Initiate a spectrum trace acquisition.
        """
        self.err_check(self.rsa.SPECTRUM_AcquireTrace())

    def SPECTRUM_GetEnable(self) -> bool:
        """
        Return the spectrum measurement enable status.

        Returns
        -------
        bool
            True if spectrum measurement enabled, False if disabled.
        """
        enable = c_bool()
        self.err_check(self.rsa.SPECTRUM_GetEnable(byref(enable)))
        return enable.value

    def SPECTRUM_GetLimits(self) -> dict:
        """
        Return the limits of the spectrum settings.

        Returns
        -------
        Dict including the following:
        maxSpan : float
            Maximum span (device dependent).
        minSpan : float
            Minimum span.
        maxRBW : float
            Maximum resolution bandwidth.
        minRBW : float
            Minimum resolution bandwidth.
        maxVBW : float
            Maximum video bandwidth.
        minVBW : float
            Minimum video bandwidth.
        maxTraceLength : int
            Maximum trace length.
        minTraceLength : int
            Minimum trace length.
        """
        limits = _SpectrumLimits()
        self.err_check(self.rsa.SPECTRUM_GetLimits(byref(limits)))
        limits_dict = {
            "maxSpan": limits.maxSpan,
            "minSpan": limits.minSpan,
            "maxRBW": limits.maxRBW,
            "minRBW": limits.minRBW,
            "maxVBW": limits.maxVBW,
            "minVBW": limits.minVBW,
            "maxTraceLength": limits.maxTraceLength,
            "minTraceLength": limits.minTraceLength,
        }
        return limits_dict

    def SPECTRUM_GetSettings(self) -> dict:
        """
        Return the spectrum settings.

        Returns
        -------
        All of the following as a dict, in this order:
        span : float
            Span measured in Hz.
        rbw : float
            Resolution bandwidth measured in Hz.
        enableVBW : bool
            True for video bandwidth enabled, False for disabled.
        vbw : float
            Video bandwidth measured in Hz.
        traceLength : int
            Number of trace points.
        window : string
            Windowing method used for the transform.
        verticalUnit : string
            Vertical units.
        actualStartFreq : float
            Actual start frequency in Hz.
        actualStopFreq : float
            Actual stop frequency in Hz.
        actualFreqStepSize : float
            Actual frequency step size in Hz.
        actualRBW : float
            Actual resolution bandwidth in Hz.
        actualVBW : float
            Not used.
        actualNumIQSamples : int
            Actual number of IQ samples used for transform.
        """
        sets = _SpectrumSettings()
        self.err_check(self.rsa.SPECTRUM_GetSettings(byref(sets)))
        settings_dict = {
            "span": sets.span,
            "rbw": sets.rbw,
            "enableVBW": sets.enableVBW,
            "vbw": sets.vbw,
            "traceLength": sets.traceLength,
            "window": _SPECTRUM_WINDOWS[sets.window],
            "verticalUnit": _SPECTRUM_VERTICAL_UNITS[sets.verticalUnit],
            "actualStartFreq": sets.actualStartFreq,
            "actualStopFreq": sets.actualStopFreq,
            "actualFreqStepSize": sets.actualFreqStepSize,
            "actualRBW": sets.actualRBW,
            "actualVBW": sets.actualVBW,
            "actualNumIQSamples": sets.actualNumIQSamples,
        }
        return settings_dict

    def SPECTRUM_GetTrace(
        self, trace: str, max_trace_points: int
    ) -> tuple[np.ndarray, int]:
        """
        Return the spectrum trace data.

        Parameters
        ----------
        trace : str
            Selected trace. Must be 'Trace1', 'Trace2', or 'Trace3'.
        max_trace_points : int
            Maximum number of trace points to retrieve. The traceData array
            should be at least this size.

        Returns
        -------
        traceData : np.ndarray of floats
            Spectrum trace data, in the unit of verticalunit specified in
            the spectrum settings.
        outTracePoints : int
            Actual number of valid trace points in traceData array.

        Raises
        ------
        RSAError
            If the trace input does not match one of the valid strings.
        """
        trace = RSA.check_string(trace)
        max_trace_points = RSA.check_int(max_trace_points)
        if trace in _SPECTRUM_TRACES:
            trace_val = c_int(_SPECTRUM_TRACES.index(trace))
        else:
            raise RSAError("Invalid trace input.")
        trace_data = (c_float * max_trace_points)()
        out_trace_points = c_int()
        self.err_check(
            self.rsa.SPECTRUM_GetTrace(
                trace_val,
                c_int(max_trace_points),
                byref(trace_data),
                byref(out_trace_points),
            )
        )
        return np.ctypeslib.as_array(trace_data), out_trace_points.value

    def SPECTRUM_GetTraceInfo(self) -> dict:
        """
        Return the spectrum result information.

        Returns
        -------
        Dict including:
        timestamp : int
            Timestamp. See REFTIME_GetTimeFromTimestamp() for converting
            from timestamp to time.
        acqDataStatus : int
            1 for adcOverrange, 2 for refFreqUnlock, and 32 for adcDataLost.
        """
        trace_info = _SpectrumTraceInfo()
        self.err_check(self.rsa.SPECTRUM_GetTraceInfo(byref(trace_info)))
        info_dict = {
            "timestamp": trace_info.timestamp,
            "acqDataStatus": trace_info.acqDataStatus,
        }
        return info_dict

    def SPECTRUM_GetTraceType(self, trace: str) -> tuple[bool, str]:
        """
        Query the trace settings.

        Parameters
        ----------
        trace : str
            Desired trace. Must be 'Trace1', 'Trace2', or 'Trace3'.

        Returns
        -------
        enable : bool
            Trace enable status. True for enabled, False for disabled.
        detector : string
            Detector type. Valid results are:
                PosPeak, NegPeak, AverageVRMS, or Sample.

        Raises
        ------
        RSAError
            If the trace input does not match a valid setting.
        """
        trace = RSA.check_string(trace)
        if trace in _SPECTRUM_TRACES:
            trace_val = c_int(_SPECTRUM_TRACES.index(trace))
        else:
            raise RSAError("Invalid trace input.")
        enable = c_bool()
        detector = c_int()
        self.err_check(
            self.rsa.SPECTRUM_GetTraceType(trace_val, byref(enable), byref(detector))
        )
        return enable.value, _SPECTRUM_DETECTORS[detector.value]

    def SPECTRUM_SetDefault(self) -> None:
        """
        Set the spectrum settings to their default values.
        """
        self.err_check(self.rsa.SPECTRUM_SetDefault())

    def SPECTRUM_SetEnable(self, enable: bool) -> None:
        """
        Set the spectrum enable status.

        Parameters
        ----------
        enable : bool
            True enables the spectrum measurement. False disables it.
        """
        enable = RSA.check_bool(enable)
        self.err_check(self.rsa.SPECTRUM_SetEnable(c_bool(enable)))

    def SPECTRUM_SetSettings(
        self,
        span: Union[float, int],
        rbw: Union[float, int],
        enable_vbw: bool,
        vbw: Union[float, int],
        trace_len: int,
        win: str,
        vert_unit: str,
    ) -> None:
        """
        Set the spectrum settings.

        Parameters
        ----------
        span : float or int
            Span measured in Hz.
        rbw : float or int
            Resolution bandwidth measured in Hz.
        enable_vbw : bool
            True for video bandwidth enabled, False for disabled.
        vbw : float or int
            Video bandwidth measured in Hz.
        trace_len : int
            Number of trace points.
        win : string
            Windowing method used for the transform. Valid settings:
            Kaiser, Mil6dB, BlackmanHarris, Rectangular, FlatTop, or Hann.
        vert_unit : string
            Vertical units. Valid settings: dBm, Watt, Volt, Amp, or dBmV.

        Raises
        ------
        RSAError
            If window or verticalUnit string inputs are not one of the
            allowed settings.
        """
        win = RSA.check_string(win)
        vert_unit = RSA.check_string(vert_unit)
        if win in _SPECTRUM_WINDOWS and vert_unit in _SPECTRUM_VERTICAL_UNITS:
            settings = _SpectrumSettings()
            settings.span = RSA.check_num(span)
            settings.rbw = RSA.check_num(rbw)
            settings.enableVBW = RSA.check_bool(enable_vbw)
            settings.vbw = RSA.check_num(vbw)
            settings.traceLength = RSA.check_int(trace_len)
            settings.window = _SPECTRUM_WINDOWS.index(win)
            settings.verticalUnit = _SPECTRUM_VERTICAL_UNITS.index(vert_unit)
            self.err_check(self.rsa.SPECTRUM_SetSettings(settings))
        else:
            raise RSAError("Window or vertical unit input invalid.")

    def SPECTRUM_SetTraceType(
        self, trace: str = "Trace1", enable: bool = True, detector: str = "AverageVRMS"
    ) -> None:
        """
        Set the trace settings.

        Parameters
        ----------
        trace : str
            One of the spectrum traces. Can be 'Trace1', 'Trace2', or 'Trace3'.
            Set to Trace1 by default.
        enable : bool
            True enables trace output. False disables it. True by default.
        detector : string
            Detector type. Default to AverageVRMS. Valid settings:
                PosPeak, NegPeak, AverageVRMS, or Sample.

        Raises
        ------
        RSAError
            If the trace or detector type input is not one of the valid settings.
        """
        trace = RSA.check_string(trace)
        detector = RSA.check_string(detector)
        if trace in _SPECTRUM_TRACES and detector in _SPECTRUM_DETECTORS:
            trace_val = c_int(_SPECTRUM_TRACES.index(trace))
            det_val = c_int(_SPECTRUM_DETECTORS.index(detector))
            self.err_check(
                self.rsa.SPECTRUM_SetTraceType(trace_val, c_bool(enable), det_val)
            )
        else:
            raise RSAError("Trace or detector type input invalid.")

    def SPECTRUM_WaitForTraceReady(self, timeout_msec: int) -> bool:
        """
        Wait for the spectrum trace data to be ready to be queried.

        Parameters
        ----------
        timeout_msec : int
            Timeout value in msec.

        Returns
        -------
        bool
            True indicates spectrum trace data is ready for acquisition.
            False indicates it is not ready, and timeout value is exceeded.
        """
        timeout_msec = RSA.check_int(timeout_msec)
        ready = c_bool()
        self.err_check(
            self.rsa.SPECTRUM_WaitForTraceReady(c_int(timeout_msec), byref(ready))
        )
        return ready.value

    # TRIGGER METHODS

    def TRIG_ForceTrigger(self) -> None:
        """Force the device to trigger."""
        self.err_check(self.rsa.TRIG_ForceTrigger())

    def TRIG_GetIFPowerTriggerLevel(self) -> float:
        """
        Return the trigger power level.

        Returns
        -------
        float
            Detection power level for the IF power trigger source
        """
        level = c_double()
        self.err_check(self.rsa.TRIG_GetIFPowerTriggerLevel(byref(level)))
        return level.value

    def TRIG_GetTriggerMode(self) -> str:
        """
        Return the trigger mode (either freeRun or triggered).

        Returns
        -------
        string
            Either "freeRun" or "triggered".
        """
        mode = c_int()
        self.err_check(self.rsa.TRIG_GetTriggerMode(byref(mode)))
        return _TRIGGER_MODE[mode.value]

    def TRIG_GetTriggerPositionPercent(self) -> float:
        """
        Return the trigger position percent.

        Returns
        -------
        float
            Trigger position percent value when the method completes.
        """
        trig_pos_percent = c_double()
        self.err_check(self.rsa.TRIG_GetTriggerPositionPercent(byref(trig_pos_percent)))
        return trig_pos_percent.value

    def TRIG_GetTriggerSource(self) -> str:
        """
        Return the trigger source.

        Returns
        -------
        string
            The trigger source type. Valid results:
                External : External source.
                IFPowerLevel : IF power level source.
        """
        source = c_int()
        self.err_check(self.rsa.TRIG_GetTriggerSource(byref(source)))
        return _TRIGGER_SOURCE[source.value]

    def TRIG_GetTriggerTransition(self) -> str:
        """
        Return the current trigger transition mode.

        Returns
        -------
        Name of the trigger transition mode. Valid results:
            LH : Trigger on low-to-high input level change.
            HL : Trigger on high-to-low input level change.
            Either : Trigger on either LH or HL transitions.
        """
        transition = c_int()
        self.err_check(self.rsa.TRIG_GetTriggerTransition(byref(transition)))
        return _TRIGGER_TRANSITION[transition.value]

    def TRIG_SetIFPowerTriggerLevel(self, level: Union[float, int]) -> None:
        """
        Set the IF power detection level.

        Parameters
        ----------
        level : float or int
            The detection power level setting for the IF power trigger
            source.
        """
        level = RSA.check_num(level)
        level = RSA.check_range(level, -130, 30)
        self.err_check(self.rsa.TRIG_SetIFPowerTriggerLevel(c_double(level)))

    def TRIG_SetTriggerMode(self, mode: str) -> None:
        """
        Set the trigger mode.

        Parameters
        ----------
        mode : The trigger mode, case insensitive. Valid settings:
            freeRun : to continually gather data
            Triggered : do not acquire new data unless triggered

        Raises
        ------
        RSAError
            If the input string is not one of the valid settings.
        """
        mode = RSA.check_string(mode)
        if mode.lower() in _TRIGGER_MODE:
            mode_value = _TRIGGER_MODE.index(mode.lower())
            self.err_check(self.rsa.TRIG_SetTriggerMode(c_int(mode_value)))
        else:
            raise RSAError("Invalid trigger mode input string.")

    def TRIG_SetTriggerPositionPercent(
        self, trig_pos_percent: Union[float, int] = 50
    ) -> None:
        """
        Set the trigger position percentage.

        Parameters
        ----------
        trig_pos_percent : float or int
            The trigger position percentage, from 1% to 99%.
        """
        trig_pos_percent = RSA.check_num(trig_pos_percent)
        trig_pos_percent = RSA.check_range(trig_pos_percent, 1, 99)
        self.err_check(
            self.rsa.TRIG_SetTriggerPositionPercent(c_double(trig_pos_percent))
        )

    def TRIG_SetTriggerSource(self, source: str) -> None:
        """
        Set the trigger source.

        Parameters
        ----------
        source : string
            A trigger source type. Valid settings:
                External : External source.
                IFPowerLevel: IF power level source.

        Raises
        ------
        RSAError
            If the input string does not match one of the valid settings.
        """
        source = RSA.check_string(source)
        if source in _TRIGGER_SOURCE:
            source_value = _TRIGGER_SOURCE.index(source)
            self.err_check(self.rsa.TRIG_SetTriggerSource(c_int(source_value)))
        else:
            raise RSAError("Invalid trigger source input string.")

    def TRIG_SetTriggerTransition(self, transition: str) -> None:
        """
        Set the trigger transition detection mode.

        Parameters
        ----------
        transition : string
            A trigger transition mode. Valid settings:
                LH : Trigger on low-to-high input level change.
                HL : Trigger on high-to-low input level change.
                Either : Trigger on either LH or HL transitions.

        Raises
        ------
        RSAError
            If the input string does not match one of the valid settings.
        """
        transition = RSA.check_string(transition)
        if transition in _TRIGGER_TRANSITION:
            trans_value = _TRIGGER_TRANSITION.index(transition)
            self.err_check(self.rsa.TRIG_SetTriggerTransition(c_int(trans_value)))
        else:
            raise RSAError("Invalid trigger transition mode input string.")

    # HELPER METHODS

    def DEVICE_SearchAndConnect(self, verbose: bool = False) -> None:
        """
        Search for and connect to a Tektronix RSA device.

        More than 10 devices cannot be found at once. Connection only
        occurs if exactly one device is found. It may be more convenient to
        simply use DEVICE_Connect(), however this helper method is useful
        if problems occur when searching for or connecting to a device.

        Parameters
        ----------
        verbose : bool
            Whether to print the steps of the process as they happen.

        Raises
        ------
        RSAError
            If no matching device is found, if more than one matching
            device are found, or if connection fails.
        """
        if verbose:
            print("Searching for devices...")

        found_devices = self.DEVICE_Search()
        num_found = len(found_devices)

        # Zero devices found case handled within DEVICE_Search()
        found_dev_str = ""
        if num_found == 1:
            found_dev_str += "The following device was found:"
        elif num_found > 1:
            found_dev_str += "The following devices were found:"
        for k, v in found_devices.items():
            found_dev_str += f"\r\n{str(k)}: {str(v)}"

        if verbose:
            print(f"Device search completed.\n{found_dev_str}\n")

        # Multiple devices found case:
        if num_found > 1:
            raise RSAError(f"Found {num_found} devices, need exactly 1.")
        else:
            if verbose:
                print("Connecting to device...")
            self.DEVICE_Connect()
            if verbose:
                print("Device connected.\n")

    def IQSTREAM_Tempfile_NoConfig(
        self, duration_msec: int, return_status: bool = False
    ) -> Union[np.ndarray, tuple[np.ndarray, str]]:
        """
        Retrieve IQ data from device by first writing to a tempfile.
        Does not perform any device configuration: only captures data.

        Parameters
        ----------
        duration_msec : int
            Duration of time to record IQ data, in milliseconds.
        return_status : bool
            Whether or not to return the IQ capture status message.
            If False, errors will be raised for buffer overflow and
            input overrange events.

        Returns
        -------
        iq_data : np.ndarray of np.complex64 values
            IQ data, with each element in the form (I + j*Q)
        iq_status : str (optional)
            The status string for the IQ capture, as defined in
            the documentation for IQSTREAMFileInfo_StatusParser().
        """
        # Configuration parameters
        dest = _IQS_OUT_DEST[3]  # Split SIQ format
        dtype = _IQS_OUT_DTYPE[0]  # 32-bit single precision floating point
        suffix_ctl = -2  # No file suffix
        filename = "tempIQ"
        sleep_time_sec = 0.05  # Loop sleep time checking if acquisition complete

        # Ensure device is stopped before proceeding
        self.DEVICE_Stop()

        # Create temp directory and collect data
        with tempfile.TemporaryDirectory() as tmp_dir:
            filename_base = tmp_dir + "/" + filename

            # Configure device
            self.IQSTREAM_SetOutputConfiguration(dest, dtype)
            self.IQSTREAM_SetDiskFilenameBase(filename_base)
            self.IQSTREAM_SetDiskFilenameSuffix(suffix_ctl)
            self.IQSTREAM_SetDiskFileLength(duration_msec)
            self.IQSTREAM_ClearAcqStatus()
            self.DEVICE_PrepareForRun()

            # Collect data
            complete = False

            self.DEVICE_Run()
            self.IQSTREAM_Start()
            sleep_time = (duration_msec + 1) / 1000
            logger.debug(f"Started IQ stream. Sleeping for {sleep_time}")
            sleep(sleep_time)
            complete = self.IQSTREAM_GetDiskFileWriteStatus()[0]
            logger.debug(f"File write complete: {complete}")
            while not complete:
                logger.debug(f"Sleeping for {sleep_time_sec}")
                sleep(sleep_time_sec)
                complete = self.IQSTREAM_GetDiskFileWriteStatus()[0]
                logger.debug(f"File write complete: {complete}")
            logger.debug("Stopping stream.")
            self.IQSTREAM_Stop()

            # Check acquisition status
            file_info = self.IQSTREAM_GetDiskFileInfo()
            logger.debug(f"Status: {file_info.acqStatus}")
            logger.debug(f"Filename: {file_info.filenames.contents.value}")
            iq_status = self.IQSTREAMFileInfo_StatusParser(file_info, not return_status)

            self.DEVICE_Stop()

            # Read data back in from file
            with open(filename_base + ".siqd", "rb") as f:
                d = np.frombuffer(f.read(), dtype=np.float32)

        # Deinterleave I and Q
        i = d[0:-1:2]
        q = np.append(d[1:-1:2], d[-1])
        # Re-interleave as numpy complex64)
        iq_data = i + 1j * q
        assert iq_data.dtype == np.complex64

        if return_status:
            return iq_data, iq_status
        else:
            return iq_data

    def IQSTREAM_Tempfile(
        self,
        cf: Union[float, int],
        ref_level: Union[float, int],
        bw: Union[float, int],
        duration_msec: int,
        return_status: bool = False,
    ) -> Union[np.ndarray, tuple[np.ndarray, str]]:
        """
        Retrieve IQ data from device by first writing to a tempfile.
        Tunes device parameters before recording: center frequency,
        reference level, and IQ bandwidth. Does not adjust preamp
        or attenuation settings for RSA500/600 devices.

        Parameters
        ----------
        cf : float or int
            Center frequency value in Hz.
        ref_level : float or int
            Reference level value in dBm.
        bw : float or int
            Requested IQ streaming bandwidth in Hz.
        duration_msec : int
            Duration of time to record IQ data, in milliseconds.
        return_status : bool
            Whether or not to return the IQ capture status integer.
            If False, errors will be raised for buffer overflow and
            input overrange events.

        Returns
        -------
        iq_data : np.ndarray of np.complex64 values
            IQ data, with each element in the form (I + j*Q)
        iq_status : str (optional)
            The status code for the IQ capture, as defined in
            the documentation for IQSTREAMFileInfo_StatusParser().
        """
        logger.warning(
            "IQSTREAM_Tempfile is not recommended! Use IQSTREAM_Tempfile_NoConfig instead."
        )
        # Configure the device: tune frequency and
        self.CONFIG_SetCenterFreq(cf)
        self.CONFIG_SetReferenceLevel(ref_level)
        self.IQSTREAM_SetAcqBandwidth(bw)

        # Retrieve IQ data (and, optionally, status message)
        return self.IQSTREAM_Tempfile_NoConfig(duration_msec, return_status)

    @staticmethod
    def IQSTREAMFileInfo_StatusParser(
        iq_stream_info: _IQStreamFileInfo, exit: bool = True
    ) -> Union[None, str]:
        """
        Parse an _IQStreamFileInfo struct to get the acquisition status.

        Depending on the ``exit`` parameter, this method will either raise an
        error or return a status string. Possible values for the
        returned status string (when ``exit`` is False):

        - No error
        - Input overrange.
        - USB data stream discontinuity.
        - Input buffer > 75% full.
        - Input buffer overflow. IQ Stream processing
          too slow. Data loss has occurred.
        - Output buffer > 75% full.
        - Output buffer overflow. File writing
          too slow. Data loss has occurred.
        - Invalid status code returned. Some always-zero bits are nonzero.

        In the case of multiple status codes being returned, the status
        string will contain all returned status strings, separated by line
        breaks.

        Parameters
        ----------
        iq_stream_info : _IQStreamFileInfo
            The IQ streaming status information structure.
        exit : bool
            If True, raise an exception for any error or warning status in the
                IQ stream. Return None if there is no error or warning.
            If False, return a string indicating the status, without raising
                an exception.

        Returns
        -------
        status: str
            A string containing all returned status messages.

        Raises
        ------
        RSAError
            If errors or warnings have occurred during IQ streaming, and
            ``exit`` is True.
        """
        status = iq_stream_info.acqStatus
        status_str = ""

        # Handle no error case
        if status == 0:
            if exit:
                return
            else:
                status_str += "No error."
        else:
            # Construct status string if status != 0
            if bool(status & 0x10000):  # mask bit 16
                status_str += "Input overrange.\n"
            if bool(status & 0x20000):  # mask bit 17
                status_str += "USB data stream discontinuity.\n"
            if bool(status & 0x40000):  # mask bit 18
                status_str += "Input buffer > 75{} full.\n".format("%")
            if bool(status & 0x80000):  # mask bit 19
                status_str += "Input buffer overflow. IQStream processing too"
                status_str += " slow, data loss has occurred.\n"
            if bool(status & 0x100000):  # mask bit 20
                status_str += "Output buffer > 75{} full.\n".format("%")
            if bool(status & 0x200000):  # mask bit 21
                status_str += "Output buffer overflow. File writing too slow, "
                status_str += "data loss has occurred.\n"
            if bool(status & 0xFFC00000):
                status_str += (
                    "Invalid status code returned. Some always-zero bits are nonzero."
                )
            if exit:
                # Raise error with full string if configured
                raise RSAError(status_str)
        return status_str

    @staticmethod
    def IQSTREAMIQInfo_StatusParser(
        iq_stream_info: _IQStreamIQInfo, exit: bool = True
    ) -> Union[None, str]:
        """
        Parse an _IQStreamIQInfo struct to get the acquisition status.

        Depending on the ``exit`` parameter, this method will either raise an
        error or return a status string. Possible values for the
        returned status string (when ``exit`` is False):

        - No error
        - Input overrange.
        - USB data stream discontinuity.
        - Input buffer > 75% full.
        - Input buffer overflow. IQ Stream processing
          too slow. Data loss has occurred.
        - Output buffer > 75% full.
        - Output buffer overflow. File writing
          too slow. Data loss has occurred.
        - Invalid status code returned. Some always-zero bits are nonzero.

        In the case of multiple status codes being returned, the status
        string will contain all returned status strings, separated by line
        breaks.

        Parameters
        ----------
        iq_stream_info : _IQStreamIQInfo
            The IQ streaming status information structure.
        exit : bool
            If True, raise an exception for any error or warning status in the
                IQ stream. Return None if there is no error or warning.
            If False, return a string indicating the status, without raising
                an exception.

        Returns
        -------
        status: str
            A string containing all returned status messages.

        Raises
        ------
        RSAError
            If errors or warnings have occurred during IQ streaming, and
            ``exit`` is True.
        """
        status = iq_stream_info.acqStatus
        status_str = ""

        # Handle no error case
        if status == 0:
            if exit:
                return
            else:
                status_str += "No error."
        else:
            # Construct status string if status != 0
            if bool(status & 0x10000):  # mask bit 16
                status_str += "Input overrange.\n"
            if bool(status & 0x20000):  # mask bit 17
                status_str += "USB data stream discontinuity.\n"
            if bool(status & 0x40000):  # mask bit 18
                status_str += "Input buffer > 75{} full.\n".format("%")
            if bool(status & 0x80000):  # mask bit 19
                status_str += "Input buffer overflow. IQStream processing too"
                status_str += " slow, data loss has occurred.\n"
            if bool(status & 0x100000):  # mask bit 20
                status_str += "Output buffer > 75{} full.\n".format("%")
            if bool(status & 0x200000):  # mask bit 21
                status_str += "Output buffer overflow. File writing too slow, "
                status_str += "data loss has occurred.\n"
            if bool(status & 0xFFC00000):
                status_str += (
                    "Invalid status code returned. Some always-zero bits are nonzero."
                )
            if exit:
                # Raise error with full string if configured
                raise RSAError(status_str)
        return f"{status_str}, {status=}"

    def SPECTRUM_Acquire(
        self, trace: str = "Trace1", trace_points: int = 801, timeout_msec: int = 50
    ) -> tuple[np.ndarray, int]:
        """
        Acquire spectrum trace.

        Parameters
        ----------
        trace : str
            Desired spectrum trace. Valid settings:
            'Trace1', 'Trace2', or 'Trace3'
        trace_points : int
            Maximum number of trace points to receive.
        timeout_msec : int
            How long to wait for trace data to be ready, in milliseconds.

        Returns
        -------
        traceData : float array
            Spectrum trace data, in the unit of verticalunit specified in
            the spectrum settings.
        outTracePoints : int
            Actual number of valid trace points in traceData array.
        """
        self.DEVICE_Run()
        self.SPECTRUM_AcquireTrace()
        ready = False
        while not ready:
            ready = self.SPECTRUM_WaitForTraceReady(timeout_msec)
            sleep(int(timeout_msec * 1e-3))
        return self.SPECTRUM_GetTrace(trace, trace_points)

    def IQBLK_Configure(
        self,
        cf: Union[float, int] = 1e9,
        ref_level: Union[float, int] = 0,
        iq_bw: Union[float, int] = 40e6,
        record_length: int = 1024,
    ) -> None:
        """
        Configure device for IQ block collection.

        Parameters
        ----------
        cf : float or int
            Desired center frequency in Hz.
        ref_level : float or int
            Desired reference level in dBm.
        iq_bw : float or int
            Desired IQ bandwidth in Hz.
        record_length : int
            Desired IQBLK record length, a number of samples.
        """
        self.CONFIG_SetCenterFreq(cf)
        self.CONFIG_SetReferenceLevel(ref_level)
        self.IQBLK_SetIQBandwidth(iq_bw)
        self.IQBLK_SetIQRecordLength(record_length)

    def IQBLK_Acquire(
        self, rec_len: int = 1024, timeout_ms: int = 50
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Acquire IQBLK data using IQBLK_GetIQDataDeinterleaved.

        Parameters
        ----------
        rec_len : int
            Requested IQBLK record length, a number of samples.
        timeout_ms : int
            How long to wait for IQBLK data to be ready, in milliseconds.

        Returns
        -------
        i_data : np.ndarray
            Deinterleaved I samples.
        q_data : np.ndarray
            Deinterleaved Q samples.
        """
        self.DEVICE_Run()
        self.IQBLK_AcquireIQData()
        ready = False
        while not ready:
            ready = self.IQBLK_WaitForIQDataReady(timeout_ms)
            sleep(int(timeout_ms * 1e-3))
        return self.IQBLK_GetIQDataDeinterleaved(req_length=rec_len)

    def DEVICE_GetTemperature(self, unit: str = "celsius") -> float:
        """
        Get the device temperature.

        Parameters
        ----------
        unit: The unit for the returned temperature value. May
            be any of 'celsius', 'fahrehnheit', 'kelvin', 'kelvins',
            'c', 'f', or 'k' (case-insensitive). Defaults to 'celsius'.

        Returns
        -------
        The device temperature in the specified units.
        """
        # Store previous frequency reference setting
        old_fru = self.CONFIG_GetFreqRefUserSetting()

        # Update frequency reference setting to update temperature value
        self.CONFIG_SetFreqRefUserSetting(None)

        # Retrieve new frequency reference setting
        fru = self.CONFIG_GetFreqRefUserSetting()

        # Restore previous frequency reference setting
        if old_fru != "Invalid User Setting":
            self.CONFIG_SetFreqRefUserSetting(old_fru)

        # Read back in value
        temp_c = self.CONFIG_DecodeFreqRefUserSettingString(fru)["temperature"]

        # Handle unit conversion if needed
        if unit.lower() in ["c", "celsius"]:
            temp = temp_c
        elif unit.lower() in ["f", "fahrenheit"]:
            temp = (temp_c * 9.0 / 5.0) + 32
        elif unit.lower() in ["k", "kelvin", "kelvins"]:
            temp = temp_c + 273.15
        else:
            raise RSAError("Invalid temperature unit selection.")

        return temp

    def IQSTREAM_Acquire(
        self, duration_msec: int, return_status: bool
    ) -> Union[np.ndarray, tuple[np.ndarray, str]]:
        """
        Stream IQ data to a NumPy array.

        Parameters
        ----------
        duration_msec : int
            Duration of time to record IQ data, in milliseconds.
        return_status : bool
            Whether or not to return the IQ capture status message.
            If False, errors will be raised for buffer overflow and
            input overrange events.

        Returns
        -------
        iq_data : np.ndarray of np.complex64 values
            IQ data, with each element in the form (I + j*Q)
        iq_status : str (optional)
            The status string for the IQ capture, as defined in
            the documentation for IQSTREAMIQInfo_StatusParser().
        """
        dest = _IQS_OUT_DEST[0]  # Client
        dtype = _IQS_OUT_DTYPE[0]  # Single
        buffer_size = 1000000  # Maximum

        # Ensure device is stopped before proceeding
        self.DEVICE_Stop()

        # Configure IQ Streaming
        self.IQSTREAM_SetOutputConfiguration(dest, dtype)
        self.IQSTREAM_SetIQDataBufferSize(buffer_size)
        buffer_size = self.IQSTREAM_GetIQDataBufferSize()
        sample_rate_Hz = self.IQSTREAM_GetAcqParameters()[1]
        iq_samples_requested = int(duration_msec * 1e-3 * sample_rate_Hz)
        buffer_time_msec = round(buffer_size / sample_rate_Hz * 1e3) * 2

        self.IQSTREAM_ClearAcqStatus()
        self.DEVICE_PrepareForRun()

        # Initialize data array
        iqdata = np.empty(iq_samples_requested, dtype=np.complex64)
        iq_samples_received = 0

        self.DEVICE_Run()
        self.IQSTREAM_Start()

        while iq_samples_received < iq_samples_requested:
            # Block while RSA buffer fills
            while not self.IQSTREAM_WaitForIQDataReady(buffer_time_msec):
                pass
            # Then retrieve IQ data (interleaved)
            iq_block, iq_block_len, iqinfo = self.IQSTREAM_GetIQData(dtype, buffer_size)

            # Deinterleave and store data
            if iq_samples_received + iq_block_len <= iq_samples_requested:
                iqdata[iq_samples_received : iq_samples_received + iq_block_len] = (
                    iq_block[0 : iq_block_len * 2 : 2]
                    + 1j * iq_block[1 : iq_block_len * 2 : 2]
                )
            else:
                remaining_samples = iq_samples_requested - iq_samples_received
                iqdata[iq_samples_received:iq_samples_requested] = (
                    iq_block[0 : remaining_samples * 2 : 2]
                    + 1j * iq_block[1 : remaining_samples * 2 : 2]
                )
            iq_samples_received += iq_block_len

        self.IQSTREAM_Stop()
        self.DEVICE_Stop()

        assert len(iqdata) == iq_samples_requested

        if return_status:
            iq_status = self.IQSTREAMIQInfo_StatusParser(iqinfo, not return_status)
            return iqdata, iq_status
        else:
            return iqdata
