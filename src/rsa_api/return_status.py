from enum import Enum


class ReturnStatus(Enum):
    noError = 0  # Most API functions return this value when successful

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
    errorFlashFileSystemUnexpectedSize = (3401,)
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
    errorMonitoringNotSupported = (3501,)
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

    # Triggering
    errorTriggerSystem = 4000

    # VNA
    errorVNAUnsupportedConfiguration = 4100

    # MFC
    errorMFCHWNotPresent = 4200
    errorMFCWriteCalFile = 4201
    errorMFCReadCalFile = 4203
    errorMFCFileFormatError = 4204
    errorMFCFlashCorruptDataError = 4205

    # acq status
    errorADCOverrange = 9000
    errorOscUnlock = 9001

    errorNotSupported = 9901

    errorPlaceholder = 9999
    notImplemented = -1
