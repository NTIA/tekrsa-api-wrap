# Written for Tektronix RSA API for Linux v1.0.0014 and Python 3.9+
import tempfile
from ctypes import *
from enum import Enum
from os.path import abspath, join
from time import sleep
from typing import Union, Any

import numpy as np

""" GLOBAL CONSTANTS """

_MAX_NUM_DEVICES = 10  # Max num. of devices that could be found
_MAX_SERIAL_STRLEN = 8  # Bytes allocated for serial number string
_MAX_DEVTYPE_STRLEN = 8  # Bytes allocated for device type string
_FPGA_VERSION_STRLEN = 6  # Bytes allocated for FPGA version number string
_FW_VERSION_STRLEN = 6  # Bytes allocated for FW version number string
_HW_VERSION_STRLEN = 4  # Bytes allocated for HW version number string
_NOMENCLATURE_STRLEN = 8  # Bytes allocated for device nomenclature string
_API_VERSION_STRLEN = 8  # Bytes allocated for API version number string

""" ENUMERATION TUPLES """

_DEV_EVENT = ('OVERRANGE', 'TRIGGER', '1PPS')
_FREQ_REF_SOURCE = ('INTERNAL', 'EXTREF', 'GNSS', 'USER')
_IQS_OUT_DEST = ('CLIENT', 'FILE_TIQ', 'FILE_SIQ', 'FILE_SIQ_SPLIT')
_IQS_OUT_DTYPE = ('SINGLE', 'INT32', 'INT16', 'SINGLE_SCALE_INT32')
_SPECTRUM_DETECTORS = ('PosPeak', 'NegPeak', 'AverageVRMS', 'Sample')
_SPECTRUM_TRACES = ('Trace1', 'Trace2', 'Trace3')
_SPECTRUM_VERTICAL_UNITS = ('dBm', 'Watt', 'Volt', 'Amp', 'dBmV')
_SPECTRUM_WINDOWS = ('Kaiser', 'Mil6dB', 'BlackmanHarris', 'Rectangular', 'FlatTop', 'Hann')
_TRIGGER_MODE = ('freeRun', 'triggered')
_TRIGGER_SOURCE = ('External', 'IFPowerLevel')
_TRIGGER_TRANSITION = ('LH', 'HL', 'Either')

""" CUSTOM DATA STRUCTURES """


class _SpectrumLimits(Structure):
    _fields_ = [('maxSpan', c_double),
                ('minSpan', c_double),
                ('maxRBW', c_double),
                ('minRBW', c_double),
                ('maxVBW', c_double),
                ('minVBW', c_double),
                ('maxTraceLength', c_int),  # Incorrectly documented as a double
                ('minTraceLength', c_int)]  # Incorrectly documented as a double


class _SpectrumSettings(Structure):
    _fields_ = [('span', c_double),
                ('rbw', c_double),
                ('enableVBW', c_bool),
                ('vbw', c_double),
                ('traceLength', c_int),
                ('window', c_int),
                ('verticalUnit', c_int),
                ('actualStartFreq', c_double),
                ('actualStopFreq', c_double),
                ('actualFreqStepSize', c_double),
                ('actualRBW', c_double),
                ('actualVBW', c_double),
                ('actualNumIQSamples', c_int)]


class _SpectrumTraceInfo(Structure):
    _fields_ = [('timestamp', c_int64),
                ('acqDataStatus', c_uint16)]


class _IQBlkAcqInfo(Structure):
    _fields_ = [('sample0Timestamp', c_uint64),
                ('triggerSampleIndex', c_uint64),
                ('triggerTimestamp', c_uint64),
                ('acqStatus', c_uint32)]


class _IQStreamFileInfo(Structure):
    _fields_ = [('numberSamples', c_uint64),
                ('sample0Timestamp', c_uint64),
                ('triggerSampleIndex', c_uint64),
                ('triggerTimestamp', c_uint64),
                ('acqStatus', c_uint32),
                ('filenames', c_wchar_p)]


""" ERROR HANDLING """


class RSAError(Exception):
    def __init__(self, err_txt=""):
        self.err_txt = err_txt
        err = "RSA Error: {}".format(self.err_txt)
        super(RSAError, self).__init__(err)


class RSA:

    def __init__(self, so_dir: str = '/drivers/'):
        """ Load the RSA USB Driver """
        # Param. 'so_dir' is the directory containing libRSA_API.so and
        # libcyusb_shared.so.
        rtld_lazy = 0x0001
        lazy_load = rtld_lazy | RTLD_GLOBAL
        self.rsa = CDLL(join(abspath(so_dir), 'libRSA_API.so'), lazy_load)
        self.usb_api = CDLL(join(abspath(so_dir), 'libcyusb_shared.so'), lazy_load)

    """ ERROR HANDLING """

    class ReturnStatus(Enum):
        noError = 0

        # Connection
        errorNotConnected = 101
        errorIncompatibleFirmware = 102
        errorBootLoaderNotRunning = 103
        errorTooManyBootLoadersConnected = 104
        errorRebootFailure = 105

        # POST
        errorPOSTFailureFPGALoad = 201
        errorPOSTFailureHiPower = 202
        errorPOSTFailureI2C = 203
        errorPOSTFailureGPIF = 204
        errorPOSTFailureUsbSpeed = 205
        errorPOSTDiagFailure = 206

        # General Msmt
        errorBufferAllocFailed = 301
        errorParameter = 302
        errorDataNotReady = 304

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

        # IQ streaming
        errorIQStreamInvalidFileDataType = 1301
        errorIQStreamFileOpenFailed = 1302
        errorIQStreamBandwidthOutOfRange = 1303

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

        errorDisconnectedDeviceRemoved = 3101
        errorDisconnectedDeviceNodeChangedAndRemoved = 3102
        errorDisconnectedTimeoutWaitingForADcData = 3103
        errorDisconnectedIOBeginTransfer = 3104
        errorOperationNotSupportedInSimMode = 3015

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
        errorFlashFileSystemUnexpectedSize = 3401,
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

        # Aux monitoring
        errorMonitoringNotSupported = 3501,
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

    """ INPUT VALIDATION """

    @staticmethod
    def check_range(in_var: Union[float, int], min_val: Union[float, int],
                    max_val: Union[float, int], incl: bool = True) -> Union[float, int]:
        """Check if input is in valid range, inclusive or exclusive"""
        if incl:
            if min_val <= in_var <= max_val:
                return in_var
            else:
                raise ValueError(f"Input must be in range {min_val} to {max_val}, inclusive.")
        else:
            if min_val < in_var < max_val:
                return in_var
            else:
                raise ValueError(f"Input must be in range {min_val} to {max_val}, exclusive.")

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

    """ ALIGNMENT METHODS """

    def ALIGN_GetAlignmentNeeded(self) -> bool:
        """
        Determine if an alignment is needed or not.

        This is based on the difference between the current temperature
        and the temperature from the last alignment.

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

        Devices start in the "warm-up" state after initial power up until
        the internal temperature stabilizes. The warm-up interval is
        different for different devices.

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

    """ AUDIO METHODS NOT IMPLEMENTED """
    """ BROKEN IN RSA API FOR LINUX v1.0.0014 """

    """ CONFIG METHODS """

    def CONFIG_GetCenterFreq(self) -> float:
        """Return the current center frequency in Hz."""
        cf = c_double()
        self.err_check(self.rsa.CONFIG_GetCenterFreq(byref(cf)))
        return cf.value

    def CONFIG_GetExternalRefEnable(self) -> bool:
        """
        Return the state of the external reference.

        This method is less useful than CONFIG_GetFrequencyReferenceSource(),
        because it only indicates if the external reference is chosen or
        not. The CONFIG_GetFrequencyReferenceSource() method indicates all
        available sources, and should often be used in place of this one.

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

        The external reference input must be enabled for this method to
        return useful results.

        Returns
        -------
        float
            The external reference frequency, measured in Hz.

        Raises
        ------
        RSAError
            If there is no external reference input in use.
        """
        global _FREQ_REF_SOURCE
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

        Note: The RSA306 and RSA306B support only INTERNAL and EXTREF
        sources.

        Returns
        -------
        string
            Name of the frequency reference source. Valid results:
                INTERNAL : Internal frequency reference.
                EXTREF : External (Ref In) frequency reference.
                GNSS : Internal GNSS receiver reference
                USER : Previously set USER setting, or, if none, INTERNAL.
        """
        global _FREQ_REF_SOURCE
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

        This method sets the trigger mode to Free Run, the center frequency
        to 1.5 GHz, the span to 40 MHz, the IQ record length to 1024
        samples, and the reference level to 0 dBm.
        """
        self.err_check(self.rsa.CONFIG_Preset())
        # For some reason, the record length is not successfully set.
        # Manual override:
        self.err_check(self.rsa.IQBLK_SetIQRecordLength(1024))

    def CONFIG_SetCenterFreq(self, cf: Union[float, int]) -> None:
        """
        Set the center frequency value, in Hz.

        When using the tracking generator, be sure to set the tracking
        generator output level before setting the center frequency.

        Parameters
        ----------
        cf : float or int
            Value to set center frequency, in Hz.
        """
        cf = RSA.check_num(cf)
        cf = RSA.check_range(cf, self.CONFIG_GetMinCenterFreq(), self.CONFIG_GetMaxCenterFreq())
        self.err_check(self.rsa.CONFIG_SetCenterFreq(c_double(cf)))

    def CONFIG_SetExternalRefEnable(self, ext_ref_en: bool) -> None:
        """
        Enable or disable the external reference.

        When the external reference is enabled, an external reference
        signal must be connected to the "Ref In" port. The signal must have
        a frequency of 10 MHz with a +10 dBm maximum amplitude. This signal
        is used by the local oscillators to mix with the input signal.

        When the external reference is disabled, an internal reference
        source is used.

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

        Note: RSA306B and RSA306 support only INTERNAL and EXTREF sources.

        The INTERNAL source is always a valid selection, and is never
        switched out of automatically.

        The EXTREF source uses the signal input to the Ref In connector as
        frequency reference for the internal oscillators. If EXTREF is
        selected without a valid signal connected to Ref In, the source
        automatically switches to USER if available, or to INTERNAL
        otherwise. If lock fails, an error status indicating the failure is
        returned.

        The GNSS source uses the internal GNSS receiver to adjust the
        internal reference oscillator. If GNSS source is selected, the GNSS
        receiver must be enabled. If the GNSS receiver is not enabled, the
        source selection remains GNSS, but no frequency correction is done.
        GNSS disciplining only occurs when the GNSS receiver has navigation
        lock. When the receiver is unlocked, the adjustment setting is
        retained unchanged until receiver lock is achieved or the source is
        switched to another selection

        If USER source is selected, the previously set USER setting is
        used. If the USER setting has not been set, the source switches
        automatically to INTERNAL.

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
        global _FREQ_REF_SOURCE
        src = RSA.check_string(src)
        if src in _FREQ_REF_SOURCE:
            if src == 'GNSS':
                raise RSAError("RSA 306B does not support GNSS reference.")
            else:
                value = c_int(_FREQ_REF_SOURCE.index(src))
                self.err_check(self.rsa.CONFIG_SetFrequencyReferenceSource(value))
        else:
            raise RSAError("Input does not match a valid setting.")

    def CONFIG_SetReferenceLevel(self, ref_level: Union[float, int]) -> None:
        """
        Set the reference level

        The reference level controls the signal path gain and attenuation
        settings. The value should be set to the maximum expected signal
        power level in dBm. Setting the value too low may result in over-
        driving the signal path and ADC, while setting it too high results
        in excess noise in the signal.

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

        Note: This command is for RSA500A Series and RSA600A Series
        instruments only.

        This method returns the enable state value set by the last
        call to CONFIG_SetAutoAttenuationEnable(), regardless of
        whether is has been applied to the hardware yet.

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

        Note: This command is for RSA500A Series and RSA600A Series
        instruments only.

        The device Run state must be re-applied to apply the new
        state value to the hardware. At device connect time, the
        auto-attenuation state is initialized to enabled (True).

        Parameters
        ----------
        enable : bool
            True enables auto-attenuation operation. False disables it.
        """
        enable = RSA.check_bool(enable)
        self.err_check(self.rsa.CONFIG_SetAutoAttenuationEnable(c_bool(enable)))

    def CONFIG_GetRFPreampEnable(self) -> bool:
        """
        Return the state of the RF Preamplifier.

        Note: This command is for RSA500A Series and RSA600A Series
        instruments only.

        This function returns the RF Preamplifier enable state value
        set by the last call to CONFIG_SetRFPreampEnable(), regardless
        of whether it has been applied to the hardware yet.

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

        Note: This command is for RSA500A Series and RSA600A Series
        instruments only.

        The device Run state must be re-applied to cause a new state
        value to be applied to the hardware.

        Parameters
        ----------
        enable : bool
            True enables the RF Preamplifier. False disables it.
        """
        enable = RSA.check_bool(enable)
        self.err_check(self.rsa.CONFIG_SetRFPreampEnable(c_bool(enable)))

    def CONFIG_GetRFAttenuator(self) -> float:
        """
        Return the setting of the RF Input Attenuator.

        Note: This command is for RSA500A Series and RSA600A Series
        instruments only.

        If auto-attenuation is enabled, the returned value is the
        current RF attenuator hardware configuration. If it is disabled,
        the returned value is the last value set by CONFIG_SetRFAttenuator(),
        regardless of whether it has been applied to the hardware.

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

        Note: This command is for RSA500A Series and RSA600A Series
        instruments only.

        The attenuator can be set in 1 dB steps, over the range -51 dB
        to 0 dB. Input values outside the range are converted to the
        closest legal value. Input values with fractional parts are
        rounded to the nearest integer value, giving 1 dB steps.

        The device auto-attenuation state must be disabled for this
        control to have effect. Setting the attenuator value with this
        function does not change the auto-attenuation state.

        The device Run state must be re-applied to cause a new setting
        value to be applied to the hardware.

        Improper manual attenuator settings may cause signal path
        saturation. It is recommended to use auto-attenuation mode to
        set the initial RF Attenuator level when making significant
        attenuator or preamp setting changes, then query the attenuator
        settings to determine reasonable values for manual control.

        Parameters
        ----------
        value : float
            The desired RF Input Attenuator setting, in dB. Values are
            rounded to the nearest integer, in the range -51 dB to 0 dB.
        """
        value = RSA.check_num(value)
        value = RSA.check_range(value, -51, 0)
        self.err_check(self.rsa.CONFIG_SetRFAttenuator(c_double(value)))

    """ DEVICE METHODS """

    def DEVICE_Connect(self, device_id: int = 0) -> None:
        """
        Connect to a device specified by the device_id parameter.

        If a single device is attached, no parameter needs to be given. If
        multiple devices are attached, a device ID value must be given to
        identify which device is the target for connection.

        The device ID value can be found using the search() method.

        Parameters
        ----------
        device_id : int
            The device ID of the target device. Defaults to zero.
        """
        device_id = RSA.check_int(device_id)
        device_id = RSA.check_range(device_id, 0, float('inf'))
        self.err_check(self.rsa.DEVICE_Connect(c_int(device_id)))

    def DEVICE_Disconnect(self) -> None:
        """Stop data acquisition and disconnect from connected device."""
        self.err_check(self.rsa.DEVICE_Disconnect())

    def DEVICE_GetEnable(self) -> bool:
        """
        Query the run state.

        The device only produces data results when in the run state, when
        signal samples flow from the device to the host API.

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

        The FPGA version has the form "Vmajor.minor" - for example, "V3.4"
        indicates a major version of 3, and a minor version of 4. The
        maximum total string length supported is 6 characters.

        Returns
        -------
        string
            The FPGA version number, formatted as described above.
        """
        global _FPGA_VERSION_STRLEN
        fpga_version = (c_char * _FPGA_VERSION_STRLEN)()
        self.err_check(self.rsa.DEVICE_GetFPGAVersion(byref(fpga_version)))
        return fpga_version.value.decode('utf-8')

    def DEVICE_GetFWVersion(self) -> str:
        """
        Retrieve the firmware version number.

        The firmware version number has the form: "Vmajor.minor". For
        example: "V3.4", for major version 3, minor version 4. The
        maximum total string length supported is 6 characters.

        Returns
        -------
        string
            The firmware version number, formatted as described above.
        """
        global _FW_VERSION_STRLEN
        fw_version = (c_char * _FW_VERSION_STRLEN)()
        self.err_check(self.rsa.DEVICE_GetFWVersion(byref(fw_version)))
        return fw_version.value.decode('utf-8')

    def DEVICE_GetHWVersion(self) -> str:
        """
        Retrieve the hardware version number.

        The firmware version number has the form: "VversionNumber". For
        example: "V3". The maximum string length supported is 4 characters.

        Returns
        -------
        string
            The hardware version number, formatted as described above.
        """
        global _HW_VERSION_STRLEN
        hw_version = (c_char * _HW_VERSION_STRLEN)()
        self.err_check(self.rsa.DEVICE_GetHWVersion(byref(hw_version)))
        return hw_version.value.decode('utf-8')

    def DEVICE_GetNomenclature(self) -> str:
        """
        Retrieve the name of the device.

        The nomenclature has the form "RSA306B", for example. The maximum
        string length supported is 8 characters.

        Returns
        -------
        string
            Name of the device.
        """
        global _NOMENCLATURE_STRLEN
        nomenclature = (c_char * _NOMENCLATURE_STRLEN)()
        self.err_check(self.rsa.DEVICE_GetNomenclature(byref(nomenclature)))
        return nomenclature.value.decode('utf-8')

    def DEVICE_GetSerialNumber(self) -> str:
        """
        Retrieve the serial number of the device.

        The serial number has the form "B012345", for example. The maximum
        string length supported is 8 characters.

        Returns
        -------
        string
            Serial number of the device.
        """
        global _MAX_SERIAL_STRLEN
        serial_num = (c_char * _MAX_SERIAL_STRLEN)()
        self.err_check(self.rsa.DEVICE_GetSerialNumber(byref(serial_num)))
        return serial_num.value.decode('utf-8')

    def DEVICE_GetAPIVersion(self) -> str:
        """
        Retrieve the API version number.

        The API version number has the form: "major.minor.revision", for
        example: "3.4.0145", for major version 3, minor version 4, and
        revision 0145. The maximum string length supported is 8 characters.

        Returns
        -------
        string
            The API version number, formatted as described above.
        """
        global _API_VERSION_STRLEN
        api_version = (c_char * _API_VERSION_STRLEN)()
        self.err_check(self.rsa.DEVICE_GetAPIVersion(byref(api_version)))
        return api_version.value.decode('utf-8')

    def DEVICE_PrepareForRun(self) -> None:
        """
        Put the system in a known state, ready to stream data.

        This method does not actually initiate data transfer. During file
        playback mode, this is useful to allow other parts of your
        application to prepare to receive data before starting the
        transfer. See DEVICE_StartFrameTransfer(). This is in comparison to
        the DEVICE_Run() method, which immediately starts data streaming
        without waiting for a "go" signal.
        """
        self.err_check(self.rsa.DEVICE_PrepareForRun())

    def DEVICE_GetInfo(self) -> dict:
        """
        Retrieve multiple device and information strings.

        Obtained information includes: device nomenclature, serial number,
        firmware versionn, FPGA version, hardware version, and API version.

        Returns
        -------
        dict
            All of the above listed information as strings.
            Keys: nomenclature, serialNum, fwVersion, fpgaVersion,
                  hwVersion, apiVersion
        """
        nomenclature = self.DEVICE_GetNomenclature()
        serial_num = self.DEVICE_GetSerialNumber()
        fw_version = self.DEVICE_GetFWVersion()
        fpga_version = self.DEVICE_GetFPGAVersion()
        hw_version = self.DEVICE_GetHWVersion()
        api_version = self.DEVICE_GetAPIVersion()
        info = {
            "nomenclature": nomenclature,
            "serialNum": serial_num,
            "fwVersion": fw_version,
            "fpgaVersion": fpga_version,
            "hwVersion": hw_version,
            "apiVersion": api_version
        }
        return info

    def DEVICE_GetOverTemperatureStatus(self) -> bool:
        """
        Query device for over-temperature status.

        This method allows clients to monitor the device's internal
        temperature status when operating in high-temperature environments.
        If the over-temperature condition is detected, the device should be
        powered down or moved to a lower temperature area.

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

        If a single device is attached, no parameter needs to be given. If
        multiple devices are attached, a device ID value must be given to
        identify which device to reboot.

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

        Returns a dict with an entry containing the device ID number,
        serial number, and device type information for each device found.
        An example of this would be: {0 : ('B012345', 'RSA306B')}, when a
        single RSA306B is found, with serial number 'B012345'.

        Valid deviceType strings are "RSA306", "RSA306B", "RSA503A",
        "RSA507A", "RSA603A", and "RSA607A".

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
        global _MAX_NUM_DEVICES, _MAX_SERIAL_STRLEN, _MAX_DEVTYPE_STRLEN
        num_found = c_int()
        dev_ids = (c_int * _MAX_NUM_DEVICES)()
        dev_serial = ((c_char * _MAX_NUM_DEVICES) * _MAX_SERIAL_STRLEN)()
        dev_type = ((c_char * _MAX_NUM_DEVICES) * _MAX_DEVTYPE_STRLEN)()

        self.err_check(
            self.rsa.DEVICE_Search(byref(num_found), byref(dev_ids), dev_serial, dev_type))

        found_devices = {ID: (dev_serial[ID].value.decode(), dev_type[ID].value.decode())
                         for ID in dev_ids}

        # If there are no devices, there is still a dict returned
        # with a device ID, but the other elements are empty.
        if found_devices[0] == ('', ''):
            raise RSAError("Could not find a matching Tektronix RSA device.")
        else:
            return found_devices

    def DEVICE_StartFrameTransfer(self) -> None:
        """
        Start data transfer.

        This is typically used as the trigger to start data streaming after
        a call to DEVICE_PrepareForRun(). If the system is in the stopped
        state, this call places it back into the run state with no changes
        to any internal data or settings, and data streaming will begin
        assuming there are no errors.
        """
        self.err_check(self.rsa.DEVICE_StartFrameTransfer())

    def DEVICE_Stop(self) -> None:
        """
        Stop data acquisition.

        This method must be called when changes are made to values that
        affect the signal.
        """
        self.err_check(self.rsa.DEVICE_Stop())

    def DEVICE_GetEventStatus(self, event_id: str) -> tuple[bool, int]:
        """
        Return global device real-time event status.

        The device should be in the Run state when this method is called.
        Event information is only updated in the Run state, not in the Stop
        state.

        Overrange event detection requires no additional configuration to
        activate. The event indicates that the ADC input signal exceeded
        the allowable range, and signal clipping has likely occurred. The
        reported timestamp value is the most recent USB transfer frame in
        which a signal overrange was detected.

        Trigger event detection requires the appropriate HW trigger
        settings to be configured. These include trigger mode, source,
        transition, and IF power level (if IF power trigger is selected).
        The event indicates that the trigger condition has occurred. The
        reported timestamp value is of the most recent sample instant when
        a trigger event was detected. The forceTrigger() method can be used
        to simulate a trigger event.

        1PPS event detection (RSA500AA/600A only) requires the GNSS receiver
        to be enabled and have navigation lock. The even indicates that the
        1PPS event has occurred. The reported timestamp value is of the
        most recent sample instant when the GNSS Rx 1PPS pulse rising edge
        was detected.

        Querying an event causes the information for that event to be
        cleared after its state is returned. Subsequent queries will
        report "no event" until a new one occurs. All events are cleared
        when the device state transitions from Stop to Run.

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
        global _DEV_EVENT
        occurred = c_bool()
        timestamp = c_uint64()
        event_id = RSA.check_string(event_id)
        if event_id in _DEV_EVENT:
            value = c_int(_DEV_EVENT.index(event_id))
        else:
            raise RSAError("Input string does not match one of the valid settings.")
        self.err_check(self.rsa.DEVICE_GetEventStatus(value, byref(occurred),
                                                      byref(timestamp)))
        return occurred.value, timestamp.value

    """ GNSS METHODS NOT IMPLEMENTED """
    """ BROKEN IN RSA API FOR LINUX v1.0.0014 """

    """ IQ BLOCK METHODS """

    def IQBLK_GetIQAcqInfo(self) -> tuple[int, int, int, int]:
        """
        Return IQ acquisition status info for the most recent IQ block.

        IQBLK_GetIQAcqInfo() may be called after an IQ block record is
        retrieved with IQBLK_GetIQData(), IQBLK_GetIQDataInterleaved(), or
        IQBLK_GetIQDataComplex(). The returned information applies to the
        IQ record returned by the "GetData" methods.

        The acquisition status bits returned by this method are:
            Bit 0 : INPUT_OVERRANGE
                ADC input overrange during acquisition.
            Bit 1 : FREQREF_UNLOCKED
                Frequency reference unlocked during acquisition.
            Bit 2 : ACQ_SYS_ERROR
                Internal oscillator unlocked or power failure during
                acquisition.
            Bit 3 : DATA_XFER_ERROR
                USB frame transfer error detected during acquisition.

        A status bit value of 1 indicates that event occurred during the
        signal acquisition. A value of 0 indicates no occurrence.

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
        info = (acq_info.sample0Timestamp.value, acq_info.triggerSampleIndex.value,
                acq_info.triggerTimestamp.value, acq_info.acqStatus.value)
        return info

    def IQBLK_AcquireIQData(self) -> None:
        """
        Initiate an IQ block record acquisition.

        Calling this method initiates an IQ block record data acquisition.
        This method places the device in the Run state if it is not
        already in that state.

        Before calling this method, all device acquisition parameters must
        be set to valid states. These include Center Frequency, Reference
        Level, any desired Trigger conditions, and the IQBLK Bandwidth and
        Record Length settings.
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
        req_length = RSA.check_range(req_length, 2, self.IQBLK_GetMaxIQRecordLength())
        out_length = c_int()
        iq_data = (c_float * (req_length * 2))()
        self.err_check(
            self.rsa.IQBLK_GetIQData(byref(iq_data), byref(out_length), c_int(req_length)))
        return np.ctypeslib.as_array(iq_data)

    def IQBLK_GetIQDataDeinterleaved(self, req_length: int) -> tuple[np.ndarray, np.ndarray]:
        """
        Retrieve an IQ block data record in separate I and Q array format.

        When complete, the iData array is filled with I-data and the qData
        array is filled with Q-data. The Q-data is not imaginary.

        For example, with reqLength = N:
            iData: [I_0, I_1, ..., I_N]
            qData: [Q_0, Q_1, ..., Q_N]
            Actual IQ Data: [I_0 + i*Q_0, I_1 + i*Q_1, ..., I_N + i*Q_N]

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
        req_length = RSA.check_range(req_length, 2, self.IQBLK_GetMaxIQRecordLength())
        i_data = (c_float * req_length)()
        q_data = (c_float * req_length)()
        out_length = c_int()
        self.err_check(self.rsa.IQBLK_GetIQDataDeinterleaved(byref(i_data), byref(q_data),
                                                             byref(out_length), c_int(req_length)))
        return np.ctypeslib.as_array(i_data), np.ctypeslib.as_array(q_data)

    def IQBLK_GetIQRecordLength(self) -> int:
        """
        Query the IQ record length.

        The IQ record length is the number of IQ data samples to be
        generated with each acquisition.

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

        The IQ sample rate value depends on the IQ bandwidth value. Set the
        IQ bandwidth value before querying the sample rate.

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

        The maximum IQ record length is the maximum number of samples which
        can be generated in one IQ block record. The maximum IQ record
        length varies as a function of the IQ bandwidth - set the bandwidth
        before querying the maximum record length. You should not request
        more than the maximum number of IQ samples when setting the record
        length. The maximum record length is the maximum number of IQ sample
        pairs that can be generated at the requested IQ bandwidth and
        corresponding IQ sample rate from 2 seconds of acquired signal data.

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

        The IQ bandwidth must be set before acquiring data. The input value
        must be within a valid range, and the IQ sample rate is determined
        by the IQ bandwidth.

        Parameters
        ----------
        iq_bandwidth : float or int
            IQ bandwidth value measured in Hz
        """
        iq_bandwidth = RSA.check_num(iq_bandwidth)
        iq_bandwidth = RSA.check_range(iq_bandwidth, self.IQBLK_GetMinIQBandwidth(),
                                       self.IQBLK_GetMaxIQBandwidth())
        self.err_check(self.rsa.IQBLK_SetIQBandwidth(c_double(iq_bandwidth)))

    def IQBLK_SetIQRecordLength(self, record_length: int) -> None:
        """
        Set the number of IQ samples generated by each IQ block acquisition.

        A check is performed to ensure that the desired value is within the
        allowed range. For best results in FFT analysis, choose a multiple
        of 2. The maximum allowed value is determined by the IQ bandwidth;
        set that first.

        Parameters
        ----------
        record_length : int
            IQ record length, measured in samples. Minimum value of 2.
        """
        record_length = RSA.check_int(record_length)
        record_length = RSA.check_range(record_length, 2, self.IQBLK_GetMaxIQRecordLength())
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
        self.err_check(self.rsa.IQBLK_WaitForIQDataReady(c_int(timeout_msec), byref(ready)))
        return ready.value

    """ IQ STREAM METHODS """

    def IQSTREAM_GetMaxAcqBandwidth(self) -> float:
        """
        Query the maximum IQ bandwidth for IQ streaming.

        The IQ streaming bandwidth should be set to a value no larger than
        the value returned by this method.

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

        The IQ streaming bandwidth should be set to a value no smaller than
        the value returned by this method.

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

        This is effective for both client and file destination runs.
        """
        self.err_check(self.rsa.IQSTREAM_ClearAcqStatus())

    def IQSTREAM_GetAcqParameters(self) -> tuple[float, float]:
        """
        Retrieve the processing parameters of IQ streaming output bandwidth
        and sample rate, resulting from the user's requested bandwidth.

        Call this method after calling IQSTREAM_SetAcqBandwidth() to set
        the requested bandwidth. See IQSTREAM_SetAcqBandwidth() docstring
        for details of how requested bandwidth is used to select output
        bandwidth and sample rate settings.

        Returns
        -------
        float: bwHz_act
            Actual acquisition bandwidth of IQ streaming output data in Hz.
        float: srSps
            Actual sample rate of IQ streaming output data in Samples/sec.
        """
        bw_hz_act = c_double()
        sr_sps = c_double()
        self.err_check(self.rsa.IQSTREAM_GetAcqParameters(byref(bw_hz_act), byref(sr_sps)))
        return bw_hz_act.value, sr_sps.value

    def IQSTREAM_GetDiskFileInfo(self) -> _IQStreamFileInfo:
        """
        Retrieve information about the previous file output operation.

        This information is intended to be queried after the file output
        operation has completed. It can be queried during file writing as
        an ongoing status, but some of the results may not be valid at that
        time.

        Note: This method does not return the filenames parameter as shown
        in the official API documentation.

        IQSTREAM_ClearAcqStatus() can be called to clear the "sticky" bits
        during the run if it is desired to reset them.

        Note: If acqStatus indicators show "Output buffer overflow", it is
        likely that the disk is too slow to keep up with writing the data
        generated by IQ stream processing. Use a faster disk (SSD is
        recommended), or a smaller acquisition bandwidth which generates
        data at a lower rate.

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

        The returned values indicate when the file output has started and
        completed. These become valid after IQSTREAM_Start() is called,
        with any file output destination selected.

        For untriggered configuration, isComplete is all that needs to be
        monitored. When it switches from false -> true, file output has
        completed. Note that if "infinite" file length is selected, then
        isComplete only changes to true when the run is stopped by running
        IQSTREAM_Stop().

        If triggering is used, isWriting can be used to determine when a
        trigger has been received. The client application can monitor this
        value, and if a maximum wait period has elapsed while it is still
        false, the output operation can be aborted. isWriting behaves the
        same for both finite and infinite file length settings.

        The [isComplete, isWriting] sequence is as follows (assumes a finite
        file length setting):
            Untriggered operation:
                IQSTREAM_Start()
                    => File output in progress: [False, True]
                    => File output complete: [True, True]
            Triggered operation:
                IQSTREAM_Start()
                    => Waiting for trigger, file writing not started:
                        [False, False]
                    => Trigger event detected, file writing in progress:
                        [False, True]
                    => File output complete: [True, True]

        Returns
        -------
        bool: isComplete
            Whether the IQ stream file output writing is complete.
        bool: isWriting
            Whether the IQ stream processing has started writing to file.
        """
        is_complete = c_bool()
        is_writing = c_bool()
        self.err_check(self.rsa.IQSTREAM_GetDiskFileWriteStatus(byref(is_complete),
                                                                byref(is_writing)))
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

    def IQSTREAM_GetIQDataBufferSize(self) -> int:
        """
        Get the maximum number of IQ sample pairs to be returned by IQSTREAM_GetData().

        Refer to the RSA API Reference Manual for additional details.

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

        The requested bandwidth should only be changed when the instrument
        is in the global stopped state. The new BW setting does not take
        effect until the global system state is cycled from stopped to
        running.

        The range of requested bandwidth values can be queried using
        IQSTREAM_GetMaxAcqBandwidth() and IQSTREAM_GetMinAcqBandwidth().

        The following table shows the mapping of requested bandwidth to
        output sample rate for all allowed bandwidth settings.

        Requested BW                      Output Sample Rate
        ----------------------------------------------------
        20.0 MHz < BW <= 40.0 MHz         56.000 MSa/s
        10.0 MHz < BW <= 20.0 MHz         28.000 MSa/s
        5.0 MHz < BW <= 10.0 MHz          14.000 MSa/s
        2.50 MHz < BW <= 5.0 MHz          7.000 MSa/s
        1.25 MHz < BW <= 2.50 MHz         3.500 MSa/s
        625.0 kHz < BW <= 1.25 MHz        1.750 MSa/s
        312.50 kHz < BW <= 625.0 kHz      875.000 kSa/s
        156.250 kHz < BW <= 312.50 kHz    437.500 kSa/s
        78125.0 Hz < BW <= 156.250 kHz    218.750 kSa/s
        39062.5 Hz < BW <= 78125.0 Hz     109.375 kSa/s
        19531.25 Hz < BW <= 39062.5 Hz    54687.5 Sa/s
        9765.625 Hz < BW <= 19531.25 Hz   24373.75 Sa/s
        BW <= 9765.625 Hz                 13671.875 Sa/s

        Parameters
        ----------
        bw_hz_req : float or int
            Requested acquisition bandwidth of IQ streaming data, in Hz.
        """
        bw_hz_req = RSA.check_num(bw_hz_req)
        bw_hz_req = RSA.check_range(bw_hz_req, self.IQSTREAM_GetMinAcqBandwidth(),
                                    self.IQSTREAM_GetMaxAcqBandwidth())
        self.err_check(self.rsa.IQSTREAM_SetAcqBandwidth(c_double(bw_hz_req)))

    def IQSTREAM_SetDiskFileLength(self, msec: int) -> None:
        """
        Set the time length of IQ data written to an output file.

        See IQSTREAM_GetDiskFileWriteStatus to find out how to monitor file
        output status to determine when it is active and completed.

        Msec Value    File Store Behavior
        ----------------------------------------------------------------
        0             No time limit on file output. File storage is
                      terminated when IQSTREAM_Stop() is called.
        > 0           File output ends after this number of milliseconds
                      of samples stored. File storage can be terminated
                      early by calling IQSTREAM_Stop().

        Parameters
        ----------
        msec : int
            Length of time in milliseconds to record IQ samples to file.
        """
        msec = RSA.check_int(msec)
        msec = RSA.check_range(msec, 0, float('inf'))
        self.err_check(self.rsa.IQSTREAM_SetDiskFileLength(c_int(msec)))

    def IQSTREAM_SetDiskFilenameBase(self, filename_base: str) -> None:
        """
        Set the base filename for file output.

        Input can include the drive/path, as well as the common base
        filename portion of the file. It should not include a file
        extension, as the file writing operation will automatically append
        the appropriate one for the selected file format.

        The complete output filename has the format:
        <filenameBase><suffix><.ext>, where <filenameBase is set by this
        method, <suffix> is set by IQSTREAM_SetDiskFilenameSuffix(), and
        <.ext> is set by IQSTREAM_SetOutputConfiguration(). If separate data
        and header files are generated, the same path/filename is used for
        both, with different extensions to indicate the contents.

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

        suffix_ctl Value    Suffix Generated
        -------------------------------------------------------------------
        -2                 None. Base filename is used without suffix. Note
                           that the output filename will not change automa-
                           tically from one run to the next, so each output
                           file will overwrite the previous one unless the
                           filename is explicitly changed by calling the
                           Set method again.
        -1                 String formed from file creation time. Format:
                           "-YYYY.MM.DD.hh.mm.ss.msec". Note this time is
                           not directly linked to the data timestamps, so
                           it should not be used as a high-accuracy time-
                           stamp of the file data!
        >= 0               5 digit auto-incrementing index, initial value =
                           suffixCtl. Format: "-nnnnn". Note index auto-
                           increments by 1 each time IQSTREAM_Start() is
                           invoked with file data destination setting.

        Parameters
        ----------
        suffix_ctl : int
            The filename suffix control value.
        """
        suffix_ctl = RSA.check_int(suffix_ctl)
        suffix_ctl = RSA.check_range(suffix_ctl, -2, float('inf'))
        self.err_check(self.rsa.IQSTREAM_SetDiskFilenameSuffix(c_int(suffix_ctl)))

    def IQSTREAM_SetIQDataBufferSize(self, req_size: int) -> None:
        """
        Set the requested size, in sample pairs, of the returned IQ record.

        Refer to the RSA API Reference Manual for additional details.

        Parameters
        ----------
        req_size : int
            Requested size of IQ output data buffer in IQ sample pairs.
            0 resets to default.
        """
        req_size = RSA.check_int(req_size)
        self.err_check(self.rsa.IQSTREAM_SetIQDataBufferSize(c_int(req_size)))

    def IQSTREAM_SetOutputConfiguration(self, dest: str, dtype: str) -> None:
        """
        Set the output data destination and IQ data type.

        The destination can be the client application, or files of different
        formats. The IQ data type can be chosen independently of the file
        format. IQ data values are stored in interleaved I/Q/I/Q order
        regardless of the destination or data type.

        Note: TIQ format files only allow INT32 or INT16 data types.

        Note: Midas 2.0 format files (.cdif, .det extensions) are not
        implemented.

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
        global _IQS_OUT_DEST, _IQS_OUT_DTYPE
        dest = RSA.check_string(dest)
        dtype = RSA.check_string(dtype)
        if dest in _IQS_OUT_DEST and dtype in _IQS_OUT_DTYPE:
            if dest == "FILE_TIQ" and "SINGLE" in dtype:
                raise RSAError("Invalid selection of TIQ file with"
                               + " single precision data type.")
            else:
                val1 = c_int(_IQS_OUT_DEST.index(dest))
                val2 = c_int(_IQS_OUT_DTYPE.index(dtype))
                self.err_check(self.rsa.IQSTREAM_SetOutputConfiguration(val1, val2))
        else:
            raise RSAError("Input data type or destination string invalid.")

    def IQSTREAM_Start(self) -> None:
        """
        Initialize IQ stream processing and initiate data output.

        If the data destination is file, the output file is created, and if
        triggering is not enabled, data starts to be written to the file
        immediately. If triggering is enabled, data will not start to be
        written to the file until a trigger event is detected.
        TRIG_ForceTrigger() can be used to generate a trigger even if the
        specified one does not occur.

        If the data destination is the client application, data will become
        available soon after this method is called. Even if triggering is
        enabled, the data will begin flowing to the client without need for
        a trigger event. The client must begin retrieving data as soon
        after IQSTREAM_Start() as possible.
        """
        self.err_check(self.rsa.IQSTREAM_Start())

    def IQSTREAM_Stop(self) -> None:
        """
        Terminate IQ stream processing and disable data output.

        If the data destination is file, file writing is stopped and the
        output file is closed.
        """
        self.err_check(self.rsa.IQSTREAM_Stop())

    def IQSTREAM_WaitForIQDataReady(self, timeout_msec: int) -> bool:
        """
        Block while waiting for IQ Stream data output.

        This method blocks while waiting for the IQ Streaming processing to
        produce the next block of IQ data. If data becomes available during
        the timeout interval, the method returns True immediately. If the
        timeout interval expires without data being ready, the method
        returns False. A timeoutMsec value of 0 checks for data ready, and
        returns immediately without waiting.

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
        timeout_msec = RSA.check_range(timeout_msec, 0, float('inf'))
        ready = c_bool()
        self.err_check(self.rsa.IQSTREAM_WaitForIQDataReady(c_int(timeout_msec), byref(ready)))
        return ready.value

    """ PLAYBACK METHODS NOT IMPLEMENTED """

    """ POWER METHODS NOT IMPLEMENTED """
    """ BROKEN IN RSA API FOR LINUX v1.0.0014 """

    """ SPECTRUM METHODS """

    def SPECTRUM_AcquireTrace(self) -> None:
        """
        Initiate a spectrum trace acquisition.

        Before calling this method, all acquisition parameters must be set
        to valid states. These include center frequency, reference level,
        any desired trigger conditions, and the spectrum configuration
        settings.
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
        limits_dict = {'maxSpan': limits.maxSpan,
                       'minSpan': limits.minSpan, 'maxRBW': limits.maxRBW,
                       'minRBW': limits.minRBW, 'maxVBW': limits.maxVBW,
                       'minVBW': limits.minVBW, 'maxTraceLength': limits.maxTraceLength,
                       'minTraceLength': limits.minTraceLength
                       }
        return limits_dict

    def SPECTRUM_GetSettings(self) -> dict:
        """
        Return the spectrum settings.

        In addition to user settings, this method also returns some
        internal setting values.

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
        global _SPECTRUM_WINDOWS, _SPECTRUM_VERTICAL_UNITS
        sets = _SpectrumSettings()
        self.err_check(self.rsa.SPECTRUM_GetSettings(byref(sets)))
        settings_dict = {'span': sets.span,
                         'rbw': sets.rbw,
                         'enableVBW': sets.enableVBW,
                         'vbw': sets.vbw,
                         'traceLength': sets.traceLength,
                         'window': _SPECTRUM_WINDOWS[sets.window],
                         'verticalUnit': _SPECTRUM_VERTICAL_UNITS[sets.verticalUnit],
                         'actualStartFreq': sets.actualStartFreq,
                         'actualStopFreq': sets.actualStopFreq,
                         'actualFreqStepSize': sets.actualFreqStepSize,
                         'actualRBW': sets.actualRBW,
                         'actualVBW': sets.actualVBW,
                         'actualNumIQSamples': sets.actualNumIQSamples}
        return settings_dict

    def SPECTRUM_GetTrace(self, trace: str, max_trace_points: int) -> tuple[np.ndarray, int]:
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
        global _SPECTRUM_TRACES
        trace = RSA.check_string(trace)
        max_trace_points = RSA.check_int(max_trace_points)
        if trace in _SPECTRUM_TRACES:
            trace_val = c_int(_SPECTRUM_TRACES.index(trace))
        else:
            raise RSAError("Invalid trace input.")
        trace_data = (c_float * max_trace_points)()
        out_trace_points = c_int()
        self.err_check(self.rsa.SPECTRUM_GetTrace(trace_val, c_int(max_trace_points),
                                                  byref(trace_data), byref(out_trace_points)))
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
        info_dict = {'timestamp': trace_info.timestamp,
                     'acqDataStatus': trace_info.acqDataStatus}
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
        global _SPECTRUM_TRACES, _SPECTRUM_DETECTORS
        trace = RSA.check_string(trace)
        if trace in _SPECTRUM_TRACES:
            trace_val = c_int(_SPECTRUM_TRACES.index(trace))
        else:
            raise RSAError("Invalid trace input.")
        enable = c_bool()
        detector = c_int()
        self.err_check(self.rsa.SPECTRUM_GetTraceType(trace_val, byref(enable), byref(detector)))
        return enable.value, _SPECTRUM_DETECTORS[detector.value]

    def SPECTRUM_SetDefault(self) -> None:
        """
        Set the spectrum settings to their default values.

        This does not change the spectrum enable status. The following are
        the default settings:
            Span : 40 MHz
            RBW : 300 kHz
            Enable VBW : False
            VBW : 300 kHz
            Trace Length : 801
            Window : Kaiser
            Vertical Unit : dBm
            Trace 0 : Enable, +Peak
            Trace 1 : Disable, -Peak
            Trace 2 : Disable, Average
        """
        self.err_check(self.rsa.SPECTRUM_SetDefault())

    def SPECTRUM_SetEnable(self, enable: bool) -> None:
        """
        Set the spectrum enable status.

        When the spectrum measurement is enabled, the IQ acquisition is
        disabled.

        Parameters
        ----------
        enable : bool
            True enables the spectrum measurement. False disables it.
        """
        enable = RSA.check_bool(enable)
        self.err_check(self.rsa.SPECTRUM_SetEnable(c_bool(enable)))

    def SPECTRUM_SetSettings(self, span: Union[float, int], rbw: Union[float, int],
                             enable_vbw: bool, vbw: Union[float, int], trace_len: int,
                             win: str, vert_unit: str) -> None:
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
        global _SPECTRUM_WINDOWS, _SPECTRUM_VERTICAL_UNITS
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

    def SPECTRUM_SetTraceType(self, trace: str = 'Trace1', enable: bool = True,
                              detector: str = 'AverageVRMS') -> None:
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
        global _SPECTRUM_TRACES, _SPECTRUM_DETECTORS
        trace = RSA.check_string(trace)
        detector = RSA.check_string(detector)
        if trace in _SPECTRUM_TRACES and detector in _SPECTRUM_DETECTORS:
            trace_val = c_int(_SPECTRUM_TRACES.index(trace))
            det_val = c_int(_SPECTRUM_DETECTORS.index(detector))
            self.err_check(self.rsa.SPECTRUM_SetTraceType(trace_val, c_bool(enable), det_val))
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
        self.err_check(self.rsa.SPECTRUM_WaitForTraceReady(c_int(timeout_msec), byref(ready)))
        return ready.value

    """ TRIGGER METHODS """

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

        When the mode is set to freeRun, the signal is continually updated.

        When the mode is set to Triggered, the data is only updated when a trigger occurs.

        Returns
        -------
        string
            Either "freeRun" or "Triggered".
        """
        global _TRIGGER_MODE
        mode = c_int()
        self.err_check(self.rsa.TRIG_GetTriggerMode(byref(mode)))
        return _TRIGGER_MODE[mode.value]

    def TRIG_GetTriggerPositionPercent(self) -> float:
        """
        Return the trigger position percent.

        Note: The trigger position setting only affects IQ Block and
        Spectrum acquisitions.

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

        When set to external, acquisition triggering looks at the external
        trigger input for a trigger signal. When set to IF power level, the
        power of the signal itself causes a trigger to occur.

        Returns
        -------
        string
            The trigger source type. Valid results:
                External : External source.
                IFPowerLevel : IF power level source.
        """
        global _TRIGGER_SOURCE
        source = c_int()
        self.err_check(self.rsa.TRIG_GetTriggerSource(byref(source)))
        return _TRIGGER_SOURCE[source.value]

    def TRIG_GetTriggerTransition(self) -> str:
        """
        Return the current trigger transition mode.

        Returns
        -------
        string
            Name of the trigger transition mode. Valid results:
                LH : Trigger on low-to-high input level change.
                HL : Trigger on high-to-low input level change.
                Either : Trigger on either LH or HL transitions.
        """
        global _TRIGGER_TRANSITION
        transition = c_int()
        self.err_check(self.rsa.TRIG_GetTriggerTransition(byref(transition)))
        return _TRIGGER_TRANSITION[transition.value]

    def TRIG_SetIFPowerTriggerLevel(self, level: Union[float, int]) -> None:
        """
        Set the IF power detection level.

        When set to the IF power level trigger source, a trigger occurs
        when the signal power level crosses this detection level.

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
        mode : string
            The trigger mode. Valid settings:
                freeRun : to continually gather data
                Triggered : do not acquire new data unless triggered

        Raises
        ------
        RSAError
            If the input string is not one of the valid settings.
        """
        global _TRIGGER_MODE
        mode = RSA.check_string(mode)
        if mode in _TRIGGER_MODE:
            mode_value = _TRIGGER_MODE.index(mode)
            self.err_check(self.rsa.TRIG_SetTriggerMode(c_int(mode_value)))
        else:
            raise RSAError("Invalid trigger mode input string.")

    def TRIG_SetTriggerPositionPercent(self, trig_pos_percent: Union[float, int] = 50) -> None:
        """
        Set the trigger position percentage.

        This value determines how much data to store before and after a
        trigger event. The stored data is used to update the signal's image
        when a trigger occurs. The trigger position setting only affects IQ
        Block and Spectrum acquisitions.

        Default setting is 50%.

        Parameters
        ----------
        trig_pos_percent : float or int
            The trigger position percentage, from 1% to 99%.
        """
        trig_pos_percent = RSA.check_num(trig_pos_percent)
        trig_pos_percent = RSA.check_range(trig_pos_percent, 1, 99)
        self.err_check(self.rsa.TRIG_SetTriggerPositionPercent(c_double(trig_pos_percent)))

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
        global _TRIGGER_SOURCE
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
        global _TRIGGER_TRANSITION
        transition = RSA.check_string(transition)
        if transition in _TRIGGER_TRANSITION:
            trans_value = _TRIGGER_TRANSITION.index(transition)
            self.err_check(self.rsa.TRIG_SetTriggerTransition(c_int(trans_value)))
        else:
            raise RSAError("Invalid trigger transition mode input string.")

    """ HELPER METHODS """

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
        found_dev_str = ''
        if num_found == 1:
            found_dev_str += "The following device was found:"
        elif num_found > 1:
            found_dev_str += "The following devices were found:"
        for (k, v) in found_devices.items():
            found_dev_str += f'\r\n{str(k)}: {str(v)}'

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

    def IQSTREAM_Tempfile(self, cf: Union[float, int], ref_level: Union[float, int],
                          bw: Union[float, int], duration_msec: int) -> np.ndarray:
        """
        Retrieve IQ data from device by first writing to a tempfile.

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

        Returns
        -------
        np.ndarray of np.complex64 values
            IQ data, with each element in the form (I + j*Q)
        """
        # Configuration parameters
        global _IQS_OUT_DEST, _IQS_OUT_DTYPE
        dest = _IQS_OUT_DEST[3]  # Split SIQ format
        dtype = _IQS_OUT_DTYPE[0]  # 32-bit single precision floating point
        suffix_ctl = -2  # No file suffix
        filename = 'tempIQ'
        sleep_time_sec = 0.1  # Loop sleep time checking if acquisition complete

        # Ensure device is stopped before proceeding
        self.DEVICE_Stop()

        # Create temp directory and configure/collect data
        with tempfile.TemporaryDirectory() as tmp_dir:
            filename_base = tmp_dir + '/' + filename

            # Configure device
            self.CONFIG_SetCenterFreq(cf)
            self.CONFIG_SetReferenceLevel(ref_level)
            self.IQSTREAM_SetAcqBandwidth(bw)
            self.IQSTREAM_SetOutputConfiguration(dest, dtype)
            self.IQSTREAM_SetDiskFilenameBase(filename_base)
            self.IQSTREAM_SetDiskFilenameSuffix(suffix_ctl)
            self.IQSTREAM_SetDiskFileLength(duration_msec)
            self.IQSTREAM_ClearAcqStatus()

            # Collect data
            complete = False

            self.DEVICE_Run()
            self.IQSTREAM_Start()
            while not complete:
                sleep(sleep_time_sec)
                complete = self.IQSTREAM_GetDiskFileWriteStatus()[0]
            self.IQSTREAM_Stop()

            # Check acquisition status
            file_info = self.IQSTREAM_GetDiskFileInfo()
            self.IQSTREAM_StatusParser(file_info)

            self.DEVICE_Stop()

            # Read data back in from file
            with open(filename_base + '.siqd', 'rb') as f:
                # If SIQ file, skip the header
                if f.name[-1] == 'q':
                    # This case currently is never used
                    # but would be needed if code is later modified
                    f.seek(1024)
                # read in data as float32 ("SINGLE" SIQ)
                d = np.frombuffer(f.read(), dtype=np.float32)

        # Deinterleave I and Q
        i = d[0:-1:2]
        q = np.append(d[1:-1:2], d[-1])
        # Re-interleave as numpy complex64)
        iq_data = i + 1j * q
        assert iq_data.dtype == np.complex64
        return iq_data

    @staticmethod
    def IQSTREAM_StatusParser(iq_stream_info: _IQStreamFileInfo) -> None:
        """
        Parse _IQStreamFileInfo structure.

        Parameters
        ----------
        iq_stream_info : _IQStreamFileInfo
            The IQ streaming status information structure.

        Raises
        ------
        RSAError
            If errors have occurred during IQ streaming.
        """
        status = iq_stream_info.acqStatus
        if status == 0:
            pass
        elif bool(status & 0x10000):  # mask bit 16
            raise RSAError('Input overrange.')
        elif bool(status & 0x40000):  # mask bit 18
            raise RSAError('Input buffer > 75{} full.'.format('%'))
        elif bool(status & 0x80000):  # mask bit 19
            raise RSAError('Input buffer overflow. IQStream processing too'
                           + ' slow, data loss has occurred.')
        elif bool(status & 0x100000):  # mask bit 20
            raise RSAError('Output buffer > 75{} full.'.format('%'))
        elif bool(status & 0x200000):  # mask bit 21
            raise RSAError('Output buffer overflow. File writing too slow, '
                           + 'data loss has occurred.')

    def SPECTRUM_Acquire(self, trace: str = 'Trace1', trace_points: int = 801,
                         timeout_msec: int = 10) -> tuple[np.ndarray, int]:
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
        while not self.SPECTRUM_WaitForTraceReady(timeout_msec):
            pass
        return self.SPECTRUM_GetTrace(trace, trace_points)

    def IQBLK_Configure(self, cf: Union[float, int] = 1e9, ref_level: Union[float, int] = 0,
                        iq_bw: Union[float, int] = 40e6, record_length: int = 1024) -> None:
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

    def IQBLK_Acquire(self, rec_len: int = 1024, timeout_ms: int = 10) -> tuple[np.ndarray, np.ndarray]:
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
        while not self.IQBLK_WaitForIQDataReady(timeout_ms):
            pass
        return self.IQBLK_GetIQDataDeinterleaved(req_length=rec_len)
