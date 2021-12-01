import unittest
from os.path import isdir
from os import mkdir
import rsa_api
from time import sleep
import numpy as np

"""
This is a test for the entire API Wrapper for the Tektronix RSA306B.
It requires a compatible RSA device to be connected.

The location for libcyusb_shared.so and libRSA_API.so must also be
specified in TEST_SO_DIR below before use. By default this is set to
the scos-sensor drivers directory.
"""

TEST_SO_DIR = './drivers/'

class rsa_api_test(unittest.TestCase):
    """Test for rsa306b_api.py"""

    """ALIGN Command Testing"""

    def test_ALIGN_GetAlignmentNeeded(self):
        self.assertIsInstance(rsa.ALIGN_GetAlignmentNeeded(), bool)
    
    def test_ALIGN_GetWarmupStatus(self):
        self.assertIsInstance(rsa.ALIGN_GetWarmupStatus(), bool)
    
    def test_ALIGN_RunAlignment(self):
        self.assertIsNone(rsa.ALIGN_RunAlignment())

    """CONFIG Command Testing"""
    
    def test_CONFIG_CenterFreq(self):
        cf = 2.4453e9
        self.assertIsNone(rsa.CONFIG_SetCenterFreq(cf))
        self.assertEqual(rsa.CONFIG_GetCenterFreq(), cf)
        
        self.assertRaises(TypeError, rsa.CONFIG_SetCenterFreq, 'abc')
        self.assertRaises(TypeError, rsa.CONFIG_SetCenterFreq, False)
        self.assertRaises(ValueError, rsa.CONFIG_SetCenterFreq, 400e9)
        self.assertRaises(ValueError, rsa.CONFIG_SetCenterFreq, -40e6)

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
        self.assertRaises(rsa_api.RSAError, rsa.CONFIG_SetFrequencyReferenceSource, 'GNSS')
        self.assertRaises(rsa_api.RSAError, rsa.CONFIG_SetFrequencyReferenceSource, 'abc')
        self.assertRaises(TypeError, rsa.CONFIG_SetFrequencyReferenceSource, 0)
        self.assertIsNone(rsa.CONFIG_SetFrequencyReferenceSource('INTERNAL'))
        self.assertIsInstance(rsa.CONFIG_GetFrequencyReferenceSource(), str)


    def test_CONFIG_Preset(self):
        self.assertIsNone(rsa.CONFIG_Preset())
        self.assertEqual(rsa.CONFIG_GetCenterFreq(), 1.5e9)
        self.assertEqual(rsa.CONFIG_GetReferenceLevel(), 0)
        self.assertEqual(rsa.IQBLK_GetIQBandwidth(), 40e6)
        self.assertEqual(rsa.IQBLK_GetIQRecordLength(), 1024)
    
    def test_CONFIG_ReferenceLevel(self):
        refLevel = 17
        self.assertIsNone(rsa.CONFIG_SetReferenceLevel(refLevel))
        self.assertEqual(rsa.CONFIG_GetReferenceLevel(), refLevel)
        self.assertRaises(TypeError, rsa.CONFIG_SetReferenceLevel, 'abc')
        self.assertRaises(ValueError, rsa.CONFIG_SetReferenceLevel, 31)
        self.assertRaises(ValueError, rsa.CONFIG_SetReferenceLevel, -131)
    
    def test_CONFIG_GetMaxCenterFreq(self):
        maxCf = 6.2e9
        self.assertEqual(rsa.CONFIG_GetMaxCenterFreq(), maxCf)
    
    def test_CONFIG_GetMinCenterFreq(self):
        minCf = 9e3
        self.assertEqual(rsa.CONFIG_GetMinCenterFreq(), minCf)

    """DEVICE Command Testing"""

    def test_DEVICE_Connect(self):
        # Stop and disconnect device first
        rsa.DEVICE_Stop()
        self.assertIsNone(rsa.DEVICE_Disconnect())
        self.assertRaises(TypeError, rsa.DEVICE_Connect, 'abc')
        self.assertRaises(ValueError, rsa.DEVICE_Connect, neg)
        self.assertIsNone(rsa.DEVICE_Connect(0))

    def test_DEVICE_PrepareForRun(self):
        self.assertIsNone(rsa.DEVICE_PrepareForRun())
    
    def test_DEVICE_Run(self):
        self.assertIsNone(rsa.DEVICE_Run())
        self.assertTrue(rsa.DEVICE_GetEnable())
    
    def test_DEVICE_Stop(self):
        self.assertIsNone(rsa.DEVICE_Stop())
        self.assertFalse(rsa.DEVICE_GetEnable())
    
    def test_DEVICE_GetEventStatus_no_signal(self):
        eventType = ['OVERRANGE', 'TRIGGER', '1PPS']
        for e in eventType:
            event, timestamp = rsa.DEVICE_GetEventStatus(e)
            self.assertFalse(event)
            self.assertEqual(timestamp, 0)
        self.assertRaises(TypeError, rsa.DEVICE_GetEventStatus, 0)
        self.assertRaises(rsa_api.RSAError, rsa.DEVICE_GetEventStatus, 'abc')
    
    def test_DEVICE_GetEventStatus_trig_event(self):
        rsa.DEVICE_Run()
        rsa.TRIG_ForceTrigger()
        sleep(0.05)
        trig, trigTs = rsa.DEVICE_GetEventStatus('TRIGGER')
        self.assertTrue(trig)
        self.assertGreater(trigTs, 0)
    
    """
    # The following test woudl require an actual overrange event.
    def test_DEVICE_GetEventStatus_overrange(self):
        pass
    """

    def test_DEVICE_GetOverTemperatureStatus(self):
        self.assertIsInstance(rsa.DEVICE_GetOverTemperatureStatus(), bool)
        self.assertEqual(rsa.DEVICE_GetOverTemperatureStatus(), False)

    def test_DEVICE_GetNomenclature_rsa306b(self):
        self.assertEqual(rsa.DEVICE_GetNomenclature(), 'RSA306B')

    def test_DEVICE_GetSerialNumber(self):
        sn = rsa.DEVICE_GetSerialNumber()
        self.assertIsInstance(sn, str)
        self.assertEqual(len(sn), 7)

    def test_DEVICE_GetAPIVersion(self):
        # This uses the Linux API version number
        self.assertEqual(rsa.DEVICE_GetAPIVersion(), '1.0.0014')

    def test_DEVICE_GetFWVersion(self):
        self.assertEqual(rsa.DEVICE_GetFWVersion(), 'V1.7')

    def test_DEVICE_GetFPGAVersion(self):
        self.assertEqual(rsa.DEVICE_GetFPGAVersion(), 'V2.1')

    def test_DEVICE_GetHWVersion(self):
        self.assertEqual(rsa.DEVICE_GetHWVersion(), 'V7')

    def test_DEVICE_GetInfo(self):
        info = rsa.DEVICE_GetInfo()
        self.assertIsInstance(info, dict)
        self.assertEqual(len(info), 6)
        self.assertEqual(len(info['serialNum']), 7)
        self.assertEqual(info['apiVersion'], '1.0.0014')
        self.assertEqual(info['fwVersion'], 'V1.7')
        self.assertEqual(info['fpgaVersion'], 'V2.1')
        self.assertEqual(info['hwVersion'], 'V7')

    """IQBLK Command Testing"""
    
    def test_IQBLK_MinMaxIQBandwidth(self):
        maxBw = rsa.IQBLK_GetMaxIQBandwidth()
        minBw = rsa.IQBLK_GetMinIQBandwidth()
        rsa.IQBLK_SetIQBandwidth(maxBw) # To get maxRl properly
        maxRl = rsa.IQBLK_GetMaxIQRecordLength()
        self.assertEqual(maxBw, 40e6)
        self.assertEqual(minBw, 100)
        self.assertEqual(maxRl, 126000000)
    
    def test_IQBLK_IQBandwidth(self):
        iqBw = 20e6
        self.assertIsNone(rsa.IQBLK_SetIQBandwidth(iqBw))
        self.assertEqual(iqBw, rsa.IQBLK_GetIQBandwidth())
        self.assertRaises(ValueError, rsa.IQBLK_SetIQBandwidth, neg)
        self.assertRaises(ValueError, rsa.IQBLK_SetIQBandwidth, 100e6)
        self.assertRaises(TypeError, rsa.IQBLK_SetIQBandwidth, 'abc')
    
    def test_IQBLK_IQRecordLength(self):
        iqRl = 8192
        self.assertIsNone(rsa.IQBLK_SetIQRecordLength(iqRl))
        self.assertEqual(iqRl, rsa.IQBLK_GetIQRecordLength())
        self.assertRaises(ValueError, rsa.IQBLK_SetIQRecordLength, neg)
        self.assertRaises(ValueError, rsa.IQBLK_SetIQRecordLength, 200e6)
        self.assertRaises(TypeError, rsa.IQBLK_SetIQRecordLength, 'abc')

    def test_IQBLK_GetSampleRate(self):
        self.assertIsInstance(rsa.IQBLK_GetIQSampleRate(), float)
    
    def test_IQBLK_GetIQData(self):
        rl = 1000
        rsa.IQBLK_Configure() # Configure to defaults
        i, q = rsa.IQBLK_Acquire(rl, 10)
        self.assertEqual(len(i), rl)
        self.assertEqual(len(q), rl)
        
        self.assertRaises(ValueError, rsa.IQBLK_Acquire, rec_len=neg)
        self.assertRaises(ValueError, rsa.IQBLK_Acquire, rec_len=200000000)
        self.assertRaises(TypeError, rsa.IQBLK_Acquire, rec_len='abc')

    """IQSTREAM Command Testing"""
    
    def test_IQSTREAM_MinMaxIQBandwidth(self):
        minBandwidthHz = rsa.IQSTREAM_GetMinAcqBandwidth()
        maxBandwidthHz = rsa.IQSTREAM_GetMaxAcqBandwidth()
        self.assertEqual(minBandwidthHz, 9765.625)
        self.assertEqual(maxBandwidthHz, 40e6)
    
    def test_IQSTREAM_AcqBandwidth(self):
        bwHz_req = [40e6, 20e6, 10e6, 5e6, 2.5e6, 1.25e6, 625e3, 312.5e3,
                    156.25e3, 78125, 39062.5, 19531.25, 9765.625]
        srSps_req = [56e6, 28e6, 14e6, 7e6, 3.5e6, 1.75e6, 875e3,
                     437.5e3, 218.75e3, 109.375e3, 54687.5, 27343.75,
                     13671.875]
        baseSize = [65536, 65536, 65536, 65536, 65536, 32768, 16384, 8192,
                    4096, 2048, 1024, 512, 256, 128]
        for b, s, r in zip(bwHz_req, srSps_req, baseSize):
            self.assertIsNone(rsa.IQSTREAM_SetAcqBandwidth(b))
            bwHz_act, srSps = rsa.IQSTREAM_GetAcqParameters()
            self.assertEqual(bwHz_act, b)
            self.assertEqual(srSps, s)
            self.assertIsNone(rsa.IQSTREAM_SetIQDataBufferSize(r))
            self.assertEqual(rsa.IQSTREAM_GetIQDataBufferSize(), r)
        
        self.assertRaises(TypeError, rsa.IQSTREAM_SetAcqBandwidth, 'abc')
        self.assertRaises(TypeError, rsa.IQSTREAM_SetAcqBandwidth, [num])
        self.assertRaises(ValueError, rsa.IQSTREAM_SetAcqBandwidth, 41e6)
    
    def test_IQSTREAM_SetOutputConfiguration(self):
        dest = ['CLIENT', 'FILE_TIQ', 'FILE_SIQ', 'FILE_SIQ_SPLIT']
        dtype = ['SINGLE', 'INT32', 'INT16', 'SINGLE_SCALE_INT32']
        
        for d in dest:
            for t in dtype:
                if d == 'FILE_TIQ' and 'SINGLE' in t:
                    self.assertRaises(rsa_api.RSAError,
                                      rsa.IQSTREAM_SetOutputConfiguration, d, t)
                else:
                    self.assertIsNone(rsa.IQSTREAM_SetOutputConfiguration(d, t))
        
        self.assertRaises(TypeError, rsa.IQSTREAM_SetOutputConfiguration,
                          num, dtype[0])
        self.assertRaises(TypeError, rsa.IQSTREAM_SetOutputConfiguration,
                          dest[0], num)
        self.assertRaises(rsa_api.RSAError, rsa.IQSTREAM_SetOutputConfiguration, 'a', 'SINGLE')
        self.assertRaises(rsa_api.RSAError, rsa.IQSTREAM_SetOutputConfiguration, 'CLIENT', 'a')

    def test_IQSTREAM_SetDiskFilenameBase(self):
        path = '/tmp/rsa_api_unittest'
        if not isdir(path):
            mkdir(path)
        filename = 'iqstream_test'
        filenameBase = path + filename
        self.assertIsNone(rsa.IQSTREAM_SetDiskFilenameBase(filenameBase))
        
        self.assertRaises(TypeError, rsa.IQSTREAM_SetDiskFilenameBase, num)
        self.assertRaises(TypeError, rsa.IQSTREAM_SetDiskFilenameBase, b'abc')
        self.assertRaises(TypeError, rsa.IQSTREAM_SetDiskFilenameBase, [num])
    
    def test_IQSTREAM_SetDiskFilenameSuffix(self):
        suffixCtl = [0, -1, -2]
        for s in suffixCtl:
            self.assertIsNone(rsa.IQSTREAM_SetDiskFilenameSuffix(s))
        
        self.assertRaises(TypeError, rsa.IQSTREAM_SetDiskFilenameSuffix, 'abc')
        self.assertRaises(ValueError, rsa.IQSTREAM_SetDiskFilenameSuffix, neg)
    
    def test_IQSTREAM_SetDiskFileLength(self):
        length = 100
        self.assertIsNone(rsa.IQSTREAM_SetDiskFileLength(length))
        self.assertRaises(TypeError, rsa.IQSTREAM_SetDiskFileLength, 'abc')
        self.assertRaises(ValueError, rsa.IQSTREAM_SetDiskFileLength, neg)
    
    def test_IQSTREAM_Operation(self):
        rsa.IQSTREAM_SetAcqBandwidth(5e6)
        rsa.IQSTREAM_SetOutputConfiguration('CLIENT', 'INT16')
        rsa.IQSTREAM_GetAcqParameters()
        rsa.DEVICE_Run()
        
        self.assertIsNone(rsa.IQSTREAM_Start())
        self.assertTrue(rsa.IQSTREAM_GetEnable())
        
        self.assertIsNone(rsa.IQSTREAM_Stop())
        self.assertFalse(rsa.IQSTREAM_GetEnable())
        
        rsa.DEVICE_Stop()
    
    def test_IQSTREAM_ClearAcqStatus(self):
        self.assertIsNone(rsa.IQSTREAM_ClearAcqStatus())

    """TRIG Command Testing"""
    
    def test_TRIG_TriggerMode(self):
        mode = ["freeRun", "triggered"]
        for m in mode:
            self.assertIsNone(rsa.TRIG_SetTriggerMode(m))
            self.assertEqual(rsa.TRIG_GetTriggerMode(), m)
    
    def test_TRIG_TriggerSource(self):
        source = ["External", "IFPowerLevel"]
        for s in source:
            self.assertIsNone(rsa.TRIG_SetTriggerSource(s))
            self.assertEqual(rsa.TRIG_GetTriggerSource(), s)
    
    def test_TRIG_TriggerTransition(self):
        trans = ["LH", "HL", "Either"]
        for t in trans:
            self.assertIsNone(rsa.TRIG_SetTriggerTransition(t))
            self.assertEqual(rsa.TRIG_GetTriggerTransition(), t)
        self.assertRaises(TypeError, rsa.TRIG_SetTriggerTransition, 0)
    
    def test_TRIG_IFPowerTriggerLevel(self):
        trigLevel = -10
        self.assertIsNone(rsa.TRIG_SetIFPowerTriggerLevel(trigLevel))
        self.assertEqual(rsa.TRIG_GetIFPowerTriggerLevel(), trigLevel)
        self.assertRaises(TypeError, rsa.TRIG_SetIFPowerTriggerLevel, 'trigger')
        self.assertRaises(ValueError, rsa.TRIG_SetIFPowerTriggerLevel, 31)
        self.assertRaises(ValueError, rsa.TRIG_SetIFPowerTriggerLevel, -131)
    
    def test_TRIG_TriggerPositionPercent(self):
        self.assertRaises(ValueError, rsa.TRIG_SetTriggerPositionPercent, 0.5)
        self.assertRaises(ValueError, rsa.TRIG_SetTriggerPositionPercent, 100)
        self.assertRaises(TypeError, rsa.TRIG_SetTriggerPositionPercent, 'abc')
        
        pos = 20
        self.assertIsNone(rsa.TRIG_SetTriggerPositionPercent(pos))
        self.assertEqual(rsa.TRIG_GetTriggerPositionPercent(), pos)
    
    def test_TRIG_ForceTrigger(self):
        self.assertIsNone(rsa.TRIG_ForceTrigger())
    
    """SPECTRUM Command Testing"""
    
    def test_SPECTRUM_Enable(self):
        enable = [False, True]
        for e in enable:
            self.assertIsNone(rsa.SPECTRUM_SetEnable(e))
            self.assertEqual(rsa.SPECTRUM_GetEnable(), e)
    
    def test_SPECTRUM_Settings(self):
        self.assertIsNone(rsa.SPECTRUM_SetDefault())
        
        span = 20e6
        rbw = 100e3
        enableVBW = True
        vbw = 50e3
        traceLength = 1601
        window = 'Hann'
        verticalUnit = 'dBm'
        self.assertIsNone(rsa.SPECTRUM_SetSettings(span, rbw, enableVBW, vbw,
                                                   traceLength, window,
                                                   verticalUnit))
        settings = rsa.SPECTRUM_GetSettings()
        self.assertIsInstance(settings, dict)
        self.assertEqual(len(settings), 13)
        self.assertEqual(settings['span'], span)
        self.assertEqual(settings['rbw'], rbw)
        self.assertEqual(settings['enableVBW'], enableVBW)
        self.assertEqual(settings['vbw'], vbw)
        self.assertEqual(settings['window'], window)
        self.assertEqual(settings['traceLength'], traceLength)
        self.assertEqual(settings['verticalUnit'], verticalUnit)
        
        self.assertRaises(TypeError, rsa.SPECTRUM_SetSettings, 'span', 'rbw',
                          'enableVBW', 'vbw', 'traceLength',
                          1, 0)
    
    def test_SPECTRUM_TraceType(self):
        trace = 'Trace2'
        enable = True
        detector = 'AverageVRMS'
        self.assertIsNone(rsa.SPECTRUM_SetTraceType(trace, enable, detector))
        o_enable, o_detector = rsa.SPECTRUM_GetTraceType(trace)
        self.assertEqual(enable, o_enable)
        self.assertEqual(detector, o_detector)
        
        self.assertRaises(rsa_api.RSAError, rsa.SPECTRUM_SetTraceType, trace='abc')
        self.assertRaises(TypeError, rsa.SPECTRUM_SetTraceType, trace=40e5)
        self.assertRaises(rsa_api.RSAError, rsa.SPECTRUM_SetTraceType,
                          detector='abc')
        self.assertRaises(TypeError, rsa.SPECTRUM_SetTraceType, detector=40e5)
    
    def test_SPECTRUM_GetLimits(self):
        limits = rsa.SPECTRUM_GetLimits()
        self.assertIsInstance(limits, dict)
        self.assertEqual(len(limits), 8)
        self.assertEqual(limits['maxSpan'], 6.2e9)
        self.assertEqual(limits['minSpan'], 1e3)
        self.assertEqual(limits['maxRBW'], 10e6)
        self.assertEqual(limits['minRBW'], 10)
        self.assertEqual(limits['maxVBW'], 10e6)
        self.assertEqual(limits['minVBW'], 1)
        self.assertEqual(limits['maxTraceLength'], 64001)
        self.assertEqual(limits['minTraceLength'], 801)
    
    def test_SPECTRUM_Acquire(self):
        rsa.SPECTRUM_SetEnable(True)
        span = 20e6
        rbw = 100e3
        enableVBW = True
        vbw = 50e3
        traceLength = 1601
        window = 'Hann'
        verticalUnit = 'dBm'
        rsa.SPECTRUM_SetSettings(span, rbw, enableVBW, vbw, traceLength, window,
                                verticalUnit)
        spectrum, outTracePoints = rsa.SPECTRUM_Acquire(trace='Trace1',
                                       trace_points=traceLength)
        self.assertEqual(len(spectrum), traceLength)
        self.assertIsInstance(spectrum, np.ndarray)
        self.assertRaises(TypeError, rsa.SPECTRUM_Acquire, trace=1)
        
        traceInfo = rsa.SPECTRUM_GetTraceInfo()
        self.assertIsInstance(traceInfo, dict)
        self.assertEqual(len(traceInfo), 2)

if __name__ == '__main__':
    """There must be a connected RSA 306B in order to test."""
    rsa = rsa_api.RSA(so_dir=TEST_SO_DIR)
    rsa.DEVICE_Connect(0)
    if rsa.DEVICE_GetNomenclature() != 'RSA306B':
        raise Exception('Incorrect RSA model, please connect RSA306B')
    
    # Some values used in testing
    num = 400
    neg = -400
    unittest.main()
    
    # Test cleanup
    rsa.DEVICE_Stop()
    rsa.DEVICE_Disconnect()
