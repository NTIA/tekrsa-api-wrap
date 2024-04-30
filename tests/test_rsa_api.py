"""
This is a test for the entire API Wrapper.
It requires a compatible RSA device to be connected.
"""

import unittest
from os import environ, mkdir
from os.path import isdir
from time import sleep

import numpy as np

import src.rsa_api as rsa_api


class rsa_api_test(unittest.TestCase):
    """Test for rsa_api_wrap.py"""

    @classmethod
    def setUpClass(cls):
        cls.rsa = rsa_api.RSA(so_dir=environ["SO_DIR"])
        cls.rsa.DEVICE_Connect(0)
        cls.device = cls.rsa.DEVICE_GetNomenclature()
        cls.num = 400
        cls.neg = -400

    @classmethod
    def tearDownClass(cls):
        cls.rsa.DEVICE_Disconnect()

    """ALIGN Command Testing"""

    def test_ALIGN_GetAlignmentNeeded(self):
        self.assertIsInstance(self.rsa.ALIGN_GetAlignmentNeeded(), bool)

    def test_ALIGN_GetWarmupStatus(self):
        self.assertIsInstance(self.rsa.ALIGN_GetWarmupStatus(), bool)

    def test_ALIGN_RunAlignment(self):
        self.assertIsNone(self.rsa.ALIGN_RunAlignment())

    """CONFIG Command Testing"""

    def test_CONFIG_CenterFreq(self):
        cf = 2.4453e9
        self.assertIsNone(self.rsa.CONFIG_SetCenterFreq(cf))
        self.assertEqual(self.rsa.CONFIG_GetCenterFreq(), cf)

        self.assertRaises(TypeError, self.rsa.CONFIG_SetCenterFreq, "abc")
        self.assertRaises(TypeError, self.rsa.CONFIG_SetCenterFreq, False)
        self.assertRaises(ValueError, self.rsa.CONFIG_SetCenterFreq, 400e9)
        self.assertRaises(ValueError, self.rsa.CONFIG_SetCenterFreq, -40e6)

    """
    # The following test requires an external reference to be in use.
    def test_CONFIG_ExternalRef(self):
        self.assertIsNone(CONFIG_SetExternalRefEnable(exRefEn=True))
        self.assertTrue(CONFIG_GetExternalRefEnable())
        extRefFreq = 10e6
        self.assertEqual(CONFIG_GetExternalRefFrequency(), extRefFreq)
        CONFIG_SetExternalRefEnable(exRefEn=False)
        self.assertRaises(rsa_api.RSAError, CONFIG_GetExternalRefFrequency)
    """

    def test_CONFIG_FrequencyReferenceSource(self):
        if self.device in ["RSA306B", "RSA306"]:
            self.assertRaises(
                rsa_api.RSAError, self.rsa.CONFIG_SetFrequencyReferenceSource, "GNSS"
            )
        self.assertRaises(
            rsa_api.RSAError, self.rsa.CONFIG_SetFrequencyReferenceSource, "abc"
        )
        self.assertRaises(TypeError, self.rsa.CONFIG_SetFrequencyReferenceSource, 0)
        self.assertIsNone(self.rsa.CONFIG_SetFrequencyReferenceSource("INTERNAL"))
        self.assertIsInstance(self.rsa.CONFIG_GetFrequencyReferenceSource(), str)

    def test_CONFIG_FreqRefUserSetting(self):
        self.assertIsInstance(self.rsa.CONFIG_GetFreqRefUserSetting(), str)
        self.assertRaises(TypeError, self.rsa.CONFIG_SetFreqRefUserSetting, 0)
        self.assertRaises(
            rsa_api.RSAError,
            self.rsa.CONFIG_SetFreqRefUserSetting,
            "Invalid User Setting",
        )
        self.assertRaises(
            rsa_api.RSAError,
            self.rsa.CONFIG_SetFreqRefUserSetting,
            "incorrect length input",
        )
        self.assertIsNone(self.rsa.CONFIG_SetFreqRefUserSetting(None))
        self.assertIsInstance(
            self.rsa.CONFIG_DecodeFreqRefUserSettingString(
                self.rsa.CONFIG_GetFreqRefUserSetting()
            ),
            dict,
        )

    def test_CONFIG_Preset(self):
        self.assertIsNone(self.rsa.CONFIG_Preset())
        self.assertEqual(self.rsa.CONFIG_GetCenterFreq(), 1.5e9)
        self.assertEqual(self.rsa.CONFIG_GetReferenceLevel(), 0)
        self.assertEqual(self.rsa.IQBLK_GetIQBandwidth(), 40e6)
        self.assertEqual(self.rsa.IQBLK_GetIQRecordLength(), 1024)

    def test_CONFIG_ReferenceLevel(self):
        refLevel = 17
        self.assertIsNone(self.rsa.CONFIG_SetReferenceLevel(refLevel))
        self.assertEqual(self.rsa.CONFIG_GetReferenceLevel(), refLevel)
        self.assertRaises(TypeError, self.rsa.CONFIG_SetReferenceLevel, "abc")
        self.assertRaises(ValueError, self.rsa.CONFIG_SetReferenceLevel, 31)
        self.assertRaises(ValueError, self.rsa.CONFIG_SetReferenceLevel, -131)

    def test_CONFIG_GetMaxCenterFreq(self):
        maxCf = 0
        if self.device in ["RSA306B", "RSA306"]:
            # Unsure if RSA306 (non-B variant) has same max freq.
            maxCf = 6.2e9
        elif self.device in ["RSA503A", "RSA603A"]:
            maxCf = 3.0e9
        elif self.device in ["RSA507A", "RSA607A"]:
            maxCf = 7.5e9
        elif self.device == "RSA513A":
            maxCf = 13.6e9
        elif self.device == "RSA518A":
            maxCf = 18.0e9
        self.assertEqual(self.rsa.CONFIG_GetMaxCenterFreq(), maxCf)

    def test_CONFIG_GetMinCenterFreq(self):
        minCf = 9e3
        self.assertEqual(self.rsa.CONFIG_GetMinCenterFreq(), minCf)

    def test_CONFIG_Attenuation(self):
        # Only run test for RSA 500A/600A devices
        if self.device not in ["RSA306B", "RSA306"]:
            self.assertIsNone(self.rsa.CONFIG_SetAutoAttenuationEnable(True))
            self.assertTrue(self.rsa.CONFIG_GetAutoAttenuationEnable())
            self.assertIsNone(self.rsa.CONFIG_SetAutoAttenuationEnable(False))
            self.assertFalse(self.rsa.CONFIG_GetAutoAttenuationEnable())
            atten_setting = -25
            self.assertIsNone(self.rsa.CONFIG_SetRFAttenuator(atten_setting))
            self.assertEqual(self.rsa.CONFIG_GetRFAttenuator(), atten_setting)

    def test_CONFIG_Preamp(self):
        # Only run test for RSA 500A/600A devices.
        if self.device not in ["RSA306B", "RSA306"]:
            self.assertIsNone(self.rsa.CONFIG_SetRFPreampEnable(False))
            self.rsa.DEVICE_Stop()
            self.rsa.CONFIG_SetAutoAttenuationEnable(True)
            self.rsa.DEVICE_Run()
            self.assertFalse(self.rsa.CONFIG_GetRFPreampEnable())
            self.assertIsNone(self.rsa.CONFIG_SetRFPreampEnable(True))
            self.rsa.DEVICE_Stop()
            self.rsa.DEVICE_Run()
            self.assertTrue(self.rsa.CONFIG_GetRFPreampEnable())

    """DEVICE Command Testing"""

    def test_DEVICE_Connect(self):
        # Stop and disconnect device first
        self.rsa.DEVICE_Stop()
        self.assertIsNone(self.rsa.DEVICE_Disconnect())
        self.assertRaises(TypeError, self.rsa.DEVICE_Connect, "abc")
        self.assertRaises(ValueError, self.rsa.DEVICE_Connect, self.neg)
        self.assertIsNone(self.rsa.DEVICE_Connect(0))

    def test_DEVICE_PrepareForRun(self):
        self.assertIsNone(self.rsa.DEVICE_PrepareForRun())

    def test_DEVICE_Run(self):
        self.assertIsNone(self.rsa.DEVICE_Run())
        self.assertTrue(self.rsa.DEVICE_GetEnable())

    def test_DEVICE_Stop(self):
        self.assertIsNone(self.rsa.DEVICE_Stop())
        self.assertFalse(self.rsa.DEVICE_GetEnable())

    def test_DEVICE_GetEventStatus_no_signal(self):
        eventType = ["OVERRANGE", "TRIGGER", "1PPS"]
        for e in eventType:
            event, timestamp = self.rsa.DEVICE_GetEventStatus(e)
            self.assertFalse(event)
            self.assertEqual(timestamp, 0)
        self.assertRaises(TypeError, self.rsa.DEVICE_GetEventStatus, 0)
        self.assertRaises(rsa_api.RSAError, self.rsa.DEVICE_GetEventStatus, "abc")

    def test_DEVICE_GetEventStatus_trig_event(self):
        self.rsa.DEVICE_Stop()
        # Setup trigger mode
        self.rsa.TRIG_SetTriggerMode("triggered")
        self.rsa.TRIG_SetTriggerSource("IFPowerLevel")
        self.rsa.TRIG_SetTriggerTransition("Either")
        self.rsa.TRIG_SetIFPowerTriggerLevel(0)
        self.rsa.DEVICE_Run()
        self.rsa.TRIG_ForceTrigger()
        sleep(0.5)
        trig, trigTs = self.rsa.DEVICE_GetEventStatus("TRIGGER")
        self.assertTrue(trig)
        self.assertGreater(trigTs, 0)

    """
    # The following test would require an actual overrange event.
    def test_DEVICE_GetEventStatus_overrange(self):
        pass
    """

    def test_DEVICE_GetOverTemperatureStatus(self):
        self.assertIsInstance(self.rsa.DEVICE_GetOverTemperatureStatus(), bool)
        self.assertEqual(self.rsa.DEVICE_GetOverTemperatureStatus(), False)

    def test_DEVICE_GetNomenclature(self):
        self.assertIsInstance(self.rsa.DEVICE_GetNomenclature(), str)

    def test_DEVICE_GetSerialNumber(self):
        sn = self.rsa.DEVICE_GetSerialNumber()
        self.assertIsInstance(sn, str)
        self.assertEqual(len(sn), 7)

    def test_DEVICE_GetAPIVersion(self):
        # This uses the Linux API version number
        self.assertEqual(self.rsa.DEVICE_GetAPIVersion(), "1.0.0014")

    def test_DEVICE_GetFWVersion(self):
        self.assertIsInstance(self.rsa.DEVICE_GetFWVersion(), str)

    def test_DEVICE_GetFPGAVersion(self):
        self.assertIsInstance(self.rsa.DEVICE_GetFPGAVersion(), str)

    def test_DEVICE_GetHWVersion(self):
        self.assertIsInstance(self.rsa.DEVICE_GetHWVersion(), str)

    def test_DEVICE_GetInfo(self):
        info = self.rsa.DEVICE_GetInfo()
        self.assertIsInstance(info, dict)
        self.assertEqual(len(info), 6)
        self.assertEqual(len(info["serialNum"]), 7)
        self.assertEqual(info["apiVersion"], "1.0.0014")
        self.assertIsInstance(info["fwVersion"], str)
        self.assertIsInstance(info["fpgaVersion"], str)
        self.assertIsInstance(info["hwVersion"], str)

    """IQBLK Command Testing"""

    def test_IQBLK_MinMaxIQBandwidth(self):
        maxBw = self.rsa.IQBLK_GetMaxIQBandwidth()
        minBw = self.rsa.IQBLK_GetMinIQBandwidth()
        self.rsa.IQBLK_SetIQBandwidth(maxBw)  # To get maxRl properly
        maxRl = self.rsa.IQBLK_GetMaxIQRecordLength()
        self.assertEqual(maxBw, 40e6)
        self.assertEqual(minBw, 100)
        self.assertEqual(maxRl, 126000000)

    def test_IQBLK_IQBandwidth(self):
        iqBw = 20e6
        self.assertIsNone(self.rsa.IQBLK_SetIQBandwidth(iqBw))
        self.assertEqual(iqBw, self.rsa.IQBLK_GetIQBandwidth())
        self.assertRaises(ValueError, self.rsa.IQBLK_SetIQBandwidth, self.neg)
        self.assertRaises(ValueError, self.rsa.IQBLK_SetIQBandwidth, 100e6)
        self.assertRaises(TypeError, self.rsa.IQBLK_SetIQBandwidth, "abc")

    def test_IQBLK_IQRecordLength(self):
        iqRl = 8192
        self.assertIsNone(self.rsa.IQBLK_SetIQRecordLength(iqRl))
        self.assertEqual(iqRl, self.rsa.IQBLK_GetIQRecordLength())
        self.assertRaises(ValueError, self.rsa.IQBLK_SetIQRecordLength, self.neg)
        self.assertRaises(ValueError, self.rsa.IQBLK_SetIQRecordLength, 200e6)
        self.assertRaises(TypeError, self.rsa.IQBLK_SetIQRecordLength, "abc")

    def test_IQBLK_GetSampleRate(self):
        self.assertIsInstance(self.rsa.IQBLK_GetIQSampleRate(), float)

    # def test_IQBLK_GetIQData(self):
    #     self.rsa.IQBLK_Configure()  # Configure to defaults
    #     iq = self.rsa.IQBLK_Acquire()
    #     self.assertEqual(len(iq), 1024)
    #     self.assertIsInstance(iq, np.ndarray)
    #     self.assertEqual(iq.dtype, np.complex64)

    #     self.assertRaises(ValueError, self.rsa.IQBLK_Acquire, rec_len=self.neg)
    #     self.assertRaises(ValueError, self.rsa.IQBLK_Acquire, rec_len=200000000)
    #     self.assertRaises(TypeError, self.rsa.IQBLK_Acquire, rec_len="abc")

    """IQSTREAM Command Testing"""

    def test_IQSTREAM_MinMaxIQBandwidth(self):
        minBandwidthHz = self.rsa.IQSTREAM_GetMinAcqBandwidth()
        maxBandwidthHz = self.rsa.IQSTREAM_GetMaxAcqBandwidth()
        self.assertEqual(minBandwidthHz, 9765.625)
        self.assertEqual(maxBandwidthHz, 40e6)

    def test_IQSTREAM_AcqBandwidth(self):
        bwHz_req = [
            40e6,
            20e6,
            10e6,
            5e6,
            2.5e6,
            1.25e6,
            625e3,
            312.5e3,
            156.25e3,
            78125,
            39062.5,
            19531.25,
            9765.625,
        ]
        srSps_req = [
            56e6,
            28e6,
            14e6,
            7e6,
            3.5e6,
            1.75e6,
            875e3,
            437.5e3,
            218.75e3,
            109.375e3,
            54687.5,
            27343.75,
            13671.875,
        ]
        baseSize = [
            65536,
            65536,
            65536,
            65536,
            65536,
            32768,
            16384,
            8192,
            4096,
            2048,
            1024,
            512,
            256,
            128,
        ]
        for b, s, r in zip(bwHz_req, srSps_req, baseSize):
            self.assertIsNone(self.rsa.IQSTREAM_SetAcqBandwidth(b))
            bwHz_act, srSps = self.rsa.IQSTREAM_GetAcqParameters()
            self.assertEqual(bwHz_act, b)
            self.assertEqual(srSps, s)
            self.assertIsNone(self.rsa.IQSTREAM_SetIQDataBufferSize(r))
            self.assertEqual(self.rsa.IQSTREAM_GetIQDataBufferSize(), r)

        self.assertRaises(TypeError, self.rsa.IQSTREAM_SetAcqBandwidth, "abc")
        self.assertRaises(TypeError, self.rsa.IQSTREAM_SetAcqBandwidth, [self.num])
        self.assertRaises(ValueError, self.rsa.IQSTREAM_SetAcqBandwidth, 41e6)

    def test_IQSTREAM_SetOutputConfiguration(self):
        dest = ["CLIENT", "FILE_TIQ", "FILE_SIQ", "FILE_SIQ_SPLIT"]
        dtype = ["SINGLE", "INT32", "INT16", "SINGLE_SCALE_INT32"]

        for d in dest:
            for t in dtype:
                if d == "FILE_TIQ" and "SINGLE" in t:
                    self.assertRaises(
                        rsa_api.RSAError, self.rsa.IQSTREAM_SetOutputConfiguration, d, t
                    )
                else:
                    self.assertIsNone(self.rsa.IQSTREAM_SetOutputConfiguration(d, t))

        self.assertRaises(
            TypeError, self.rsa.IQSTREAM_SetOutputConfiguration, self.num, dtype[0]
        )
        self.assertRaises(
            TypeError, self.rsa.IQSTREAM_SetOutputConfiguration, dest[0], self.num
        )
        self.assertRaises(
            rsa_api.RSAError, self.rsa.IQSTREAM_SetOutputConfiguration, "a", "SINGLE"
        )
        self.assertRaises(
            rsa_api.RSAError, self.rsa.IQSTREAM_SetOutputConfiguration, "CLIENT", "a"
        )

    def test_IQSTREAM_SetDiskFilenameBase(self):
        path = "/tmp/rsa_api_unittest"
        if not isdir(path):
            mkdir(path)
        filename = "iqstream_test"
        filenameBase = path + filename
        self.assertIsNone(self.rsa.IQSTREAM_SetDiskFilenameBase(filenameBase))

        self.assertRaises(TypeError, self.rsa.IQSTREAM_SetDiskFilenameBase, self.num)
        self.assertRaises(TypeError, self.rsa.IQSTREAM_SetDiskFilenameBase, b"abc")
        self.assertRaises(TypeError, self.rsa.IQSTREAM_SetDiskFilenameBase, [self.num])

    def test_IQSTREAM_SetDiskFilenameSuffix(self):
        suffixCtl = [0, -1, -2]
        for s in suffixCtl:
            self.assertIsNone(self.rsa.IQSTREAM_SetDiskFilenameSuffix(s))

        self.assertRaises(TypeError, self.rsa.IQSTREAM_SetDiskFilenameSuffix, "abc")
        self.assertRaises(ValueError, self.rsa.IQSTREAM_SetDiskFilenameSuffix, self.neg)

    def test_IQSTREAM_SetDiskFileLength(self):
        length = 100
        self.assertIsNone(self.rsa.IQSTREAM_SetDiskFileLength(length))
        self.assertRaises(TypeError, self.rsa.IQSTREAM_SetDiskFileLength, "abc")
        self.assertRaises(ValueError, self.rsa.IQSTREAM_SetDiskFileLength, self.neg)

    def test_IQSTREAM_Operation(self):
        self.rsa.IQSTREAM_SetAcqBandwidth(5e6)
        self.rsa.IQSTREAM_SetOutputConfiguration("CLIENT", "INT16")
        self.rsa.IQSTREAM_GetAcqParameters()
        self.rsa.DEVICE_Run()

        self.assertIsNone(self.rsa.IQSTREAM_Start())
        self.assertTrue(self.rsa.IQSTREAM_GetEnable())

        self.assertIsNone(self.rsa.IQSTREAM_Stop())
        self.assertFalse(self.rsa.IQSTREAM_GetEnable())

        self.rsa.DEVICE_Stop()

    def test_IQSTREAM_ClearAcqStatus(self):
        self.assertIsNone(self.rsa.IQSTREAM_ClearAcqStatus())

    """TRIG Command Testing"""

    def test_TRIG_TriggerMode(self):
        mode = ["freerun", "triggered"]
        for m in mode:
            self.assertIsNone(self.rsa.TRIG_SetTriggerMode(m))
            self.assertEqual(self.rsa.TRIG_GetTriggerMode(), m)

    def test_TRIG_TriggerSource(self):
        source = ["External", "IFPowerLevel"]
        for s in source:
            self.assertIsNone(self.rsa.TRIG_SetTriggerSource(s))
            self.assertEqual(self.rsa.TRIG_GetTriggerSource(), s)

    def test_TRIG_TriggerTransition(self):
        trans = ["LH", "HL", "Either"]
        for t in trans:
            self.assertIsNone(self.rsa.TRIG_SetTriggerTransition(t))
            self.assertEqual(self.rsa.TRIG_GetTriggerTransition(), t)
        self.assertRaises(TypeError, self.rsa.TRIG_SetTriggerTransition, 0)

    def test_TRIG_IFPowerTriggerLevel(self):
        trigLevel = -10
        self.assertIsNone(self.rsa.TRIG_SetIFPowerTriggerLevel(trigLevel))
        self.assertEqual(self.rsa.TRIG_GetIFPowerTriggerLevel(), trigLevel)
        self.assertRaises(TypeError, self.rsa.TRIG_SetIFPowerTriggerLevel, "trigger")
        self.assertRaises(ValueError, self.rsa.TRIG_SetIFPowerTriggerLevel, 31)
        self.assertRaises(ValueError, self.rsa.TRIG_SetIFPowerTriggerLevel, -131)

    def test_TRIG_TriggerPositionPercent(self):
        self.assertRaises(ValueError, self.rsa.TRIG_SetTriggerPositionPercent, 0.5)
        self.assertRaises(ValueError, self.rsa.TRIG_SetTriggerPositionPercent, 100)
        self.assertRaises(TypeError, self.rsa.TRIG_SetTriggerPositionPercent, "abc")

        pos = 20
        self.assertIsNone(self.rsa.TRIG_SetTriggerPositionPercent(pos))
        self.assertEqual(self.rsa.TRIG_GetTriggerPositionPercent(), pos)

    def test_TRIG_ForceTrigger(self):
        self.assertIsNone(self.rsa.TRIG_ForceTrigger())

    """SPECTRUM Command Testing"""

    def test_SPECTRUM_Enable(self):
        enable = [False, True]
        for e in enable:
            self.assertIsNone(self.rsa.SPECTRUM_SetEnable(e))
            self.assertEqual(self.rsa.SPECTRUM_GetEnable(), e)

    def test_SPECTRUM_Settings(self):
        self.assertIsNone(self.rsa.SPECTRUM_SetDefault())

        span = 20e6
        rbw = 100e3
        enableVBW = True
        vbw = 50e3
        traceLength = 1601
        window = "Hann"
        verticalUnit = "dBm"
        self.assertIsNone(
            self.rsa.SPECTRUM_SetSettings(
                span, rbw, enableVBW, vbw, traceLength, window, verticalUnit
            )
        )
        settings = self.rsa.SPECTRUM_GetSettings()
        self.assertIsInstance(settings, dict)
        self.assertEqual(len(settings), 13)
        self.assertEqual(settings["span"], span)
        self.assertEqual(settings["rbw"], rbw)
        self.assertEqual(settings["enableVBW"], enableVBW)
        self.assertEqual(settings["vbw"], vbw)
        self.assertEqual(settings["window"], window)
        self.assertEqual(settings["traceLength"], traceLength)
        self.assertEqual(settings["verticalUnit"], verticalUnit)

        self.assertRaises(
            TypeError,
            self.rsa.SPECTRUM_SetSettings,
            "span",
            "rbw",
            "enableVBW",
            "vbw",
            "traceLength",
            1,
            0,
        )

    def test_SPECTRUM_TraceType(self):
        trace = "Trace2"
        enable = True
        detector = "AverageVRMS"
        self.assertIsNone(self.rsa.SPECTRUM_SetTraceType(trace, enable, detector))
        o_enable, o_detector = self.rsa.SPECTRUM_GetTraceType(trace)
        self.assertEqual(enable, o_enable)
        self.assertEqual(detector, o_detector)

        self.assertRaises(rsa_api.RSAError, self.rsa.SPECTRUM_SetTraceType, trace="abc")
        self.assertRaises(TypeError, self.rsa.SPECTRUM_SetTraceType, trace=40e5)
        self.assertRaises(
            rsa_api.RSAError, self.rsa.SPECTRUM_SetTraceType, detector="abc"
        )
        self.assertRaises(TypeError, self.rsa.SPECTRUM_SetTraceType, detector=40e5)

    def test_SPECTRUM_GetLimits(self):
        if self.device in ["RSA306B", "RSA306"]:
            maxSpan = 6.2e9
        elif self.device in ["RSA503A", "RSA603A"]:
            maxSpan = 3.0e9
        elif self.device in ["RSA507A", "RSA607A"]:
            maxSpan = 7.5e9
        elif self.device == "RSA513A":
            maxSpan = 13.6e9
        elif self.device == "RSA518A":
            maxSpan = 18.0e9

        limits = self.rsa.SPECTRUM_GetLimits()
        self.assertIsInstance(limits, dict)
        self.assertEqual(len(limits), 8)
        self.assertEqual(limits["maxSpan"], maxSpan)
        self.assertEqual(limits["minSpan"], 1e3)
        self.assertEqual(limits["maxRBW"], 10e6)
        self.assertEqual(limits["minRBW"], 10)
        self.assertEqual(limits["maxVBW"], 10e6)
        self.assertEqual(limits["minVBW"], 1)
        self.assertEqual(limits["maxTraceLength"], 64001)
        self.assertEqual(limits["minTraceLength"], 801)

    # def test_SPECTRUM_Acquire(self):
    #     self.rsa.SPECTRUM_SetEnable(True)
    #     span = 20e6
    #     rbw = 100e3
    #     enableVBW = True
    #     vbw = 50e3
    #     traceLength = 1601
    #     window = "Hann"
    #     verticalUnit = "dBm"
    #     self.rsa.SPECTRUM_SetSettings(
    #         span, rbw, enableVBW, vbw, traceLength, window, verticalUnit
    #     )
    #     spectrum, outTracePoints = self.rsa.SPECTRUM_Acquire(
    #         trace="Trace1", trace_points=traceLength
    #     )
    #     self.assertEqual(len(spectrum), traceLength)
    #     self.assertIsInstance(spectrum, np.ndarray)
    #     self.assertRaises(TypeError, self.rsa.SPECTRUM_Acquire, trace=1)

    #     traceInfo = self.rsa.SPECTRUM_GetTraceInfo()
    #     self.assertIsInstance(traceInfo, dict)
    #     self.assertEqual(len(traceInfo), 2)
