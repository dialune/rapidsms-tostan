#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8

import unittest
from rapidsms.utils import *

import pytz
from datetime import datetime, timedelta

class TestUtils(unittest.TestCase):
    
    def setUp(self):
        pass

    def testEmptyStr(self):
        empty_ascii = [
            '',' ','\n','\r','\t',
            ' \n\r\t '
            ]
        
        empty_unicode = [unicode(s) for s in empty_ascii]
    
        self.assertTrue(empty_str(None))
        for s in empty_ascii+empty_unicode:
            self.assertTrue(empty_str(s))

        not_empty = [ '%sa%s' % (s,s) for s in empty_ascii ]
        not_empty_unicode = [ unicode(s) for s in not_empty]
        for s in not_empty+not_empty_unicode:
            self.assertFalse(empty_str(s))

    def testToNaiveUTC(self):
        pacific_10am = \
            pytz.timezone('US/Pacific').\
            localize(datetime(2009, 7, 16, 10, 0, 0, 0))

        naive_utc = to_naive_utc_dt(pacific_10am)
        self.assertTrue(naive_utc.tzinfo is None)
        
        if pacific_10am.dst() == timedelta(0):
            # no daylight savings, UTC is 8 hrs ahead
            self.assertTrue(naive_utc==datetime(2009,7,16,18,0,0,0))
        else:
            # currently is DST, so UTC is 7 hours ahead
            self.assertTrue(naive_utc==datetime(2009,7,16,17,0,0,0))
        
        # now test that a naive time passed in stays naive
        utc_now = datetime.utcnow()
        out_now = to_naive_utc_dt(utc_now)
        self.assertTrue(out_now.tzinfo is None)
        self.assertTrue(utc_now==out_now)

    def testToAwareUTC(self):
        # test an aware inbound
        pacific_10am = pytz.timezone('US/Pacific').\
            localize(datetime(2009, 7, 16, 10, 0, 0, 0))
        
        utc_aware = to_aware_utc_dt(pacific_10am)
        self.assertTrue(utc_aware.tzinfo==pytz.utc)
        self.assertTrue(utc_aware == pacific_10am)
        if pacific_10am.dst() == timedelta(0):
            # no daylight savings, UTC is 8 hrs ahead
            self.assertTrue(utc_aware.hour==pacific_10am.hour+8)
        else:
            # currently is DST, so UTC is 7 hours ahead         
            self.assertTrue(utc_aware.hour==pacific_10am.hour+7)
                              
        # test a naive inbound
        utc_naive=datetime.utcnow()
        utc_aware=to_aware_utc_dt(utc_naive)
        self.assertTrue(utc_aware.tzinfo==pytz.utc)
        for attr in [
            'year',
            'month',
            'day',
            'hour',
            'minute',
            'second',
            'microsecond']:
            self.assertTrue(getattr(utc_naive, attr)==
                            getattr(utc_aware, attr))


    def testTimeDeltaAs(self):
        two_ten_ten=timedelta(hours=2, minutes=10, seconds=10)
        self.assertTrue(timedelta_as_seconds(two_ten_ten)==\
                            2*60*60+10*60+10)
        
        # do that again with microsends to prove the rounding
        # that is, the micros are dropped
        two_ten_ten_five=timedelta(hours=2, 
                                   minutes=10, 
                                   seconds=10,
                                   microseconds=5)
        self.assertTrue(timedelta_as_seconds(two_ten_ten_five)==\
                            2*60*60+10*60+10)

        # test minute rounding now--should return
        # a float with partial minutes, but ignoring
        # microseconds
        self.assertTrue(timedelta_as_minutes(two_ten_ten_five)==\
                            2*60+10+10/60)

if __name__ == '__main__':
    unittest.main()
