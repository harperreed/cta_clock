import time
import requests
import logging
import sys
try:
    import wink
except ImportError as e:
    import sys
    sys.path.insert(0, "..")
    import wink
from xml.etree import cElementTree as ET
import datetime

from collections import defaultdict

def etree_to_dict(t):
    d = {t.tag: {} if t.attrib else None}
    children = list(t)
    if children:
        dd = defaultdict(list)
        for dc in map(etree_to_dict, children):
            for k, v in dc.iteritems():
                dd[k].append(v)
        d = {t.tag: {k:v[0] if len(v) == 1 else v for k, v in dd.iteritems()}}
    if t.attrib:
        d[t.tag].update(('@' + k, v) for k, v in t.attrib.iteritems())
    if t.text:
        text = t.text.strip()
        if children or t.attrib:
            if text:
              d[t.tag]['#text'] = text
        else:
            d[t.tag] = text
    return d

class WinkManualControl(object):
    """docstring for WinkManualControl"""
    def __init__(self, secret_file_name):
        super(WinkManualControl, self).__init__()



        self.w = wink.init(secret_file_name)

        if "cloud_clock" not in self.w .device_types():
            raise RuntimeError(
                "you do not have a cloud_clock associated with your account!"
            )
        c = self.w.cloud_clock()
        self.__class__ = type(c.__class__.__name__,
                              (self.__class__, c.__class__),
                              {})
        self.__dict__ = c.__dict__

        self.min_value = sys.maxint
        self.max_value = 0
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)

    def scale_value(self, x, in_min, in_max, out_min, out_max):
        try:
            return (x - in_min) * (out_max - out_min) // (in_max - in_min) + out_min
        except ZeroDivisionError:
            return x

    def set_dial_value(self, dial_num, value, label):
        if value < self.min_value:
            self.min_value = value
        if value > self.max_value:
            self.max_value = value

        dial = self.dials()[dial_num]

        # the dial servo will always display a percentage [0..100],
        # we'll set up the dial minimum and maximum to reflect that:
        dial_config = {
            "scale_type": "linear",
            "rotation": "cw",
            "min_value": 0,
            "max_value": 100,
            "min_position": 0,
            "max_position": 360,
            "num_ticks": 12
        }

        # calculate percentage:
        percent = self.scale_value(value, self.min_value, self.max_value, 0, 100)

        # log statement:
        current_time = datetime.datetime.now().time()
        self.logger.debug("percent = %d%%, label = '%s', actual = %d [%d, %d]" % (
            percent, label,
            value, self.min_value, self.max_value))

        # assert manual control (chan. 10) with new config, value, & label:
        dial.update(dict(
            channel_configuration=dict(channel_id="10"),
            dial_configuration=dial_config,
            label=label,
            value=percent,
        ))

    def set_manual_dial(self, dial_num, label, value):

        dial = self.dials()[dial_num]

        # the dial servo will always display a percentage [0..100],
        # we'll set up the dial minimum and maximum to reflect that:
        dial_config = {
            "scale_type": "linear",
            "rotation": "cw",
            "min_value": 0,
            "max_value": 100,
            "min_position": 0,
            "max_position": 360,
            "num_ticks": 12
        }

        # log statement:
        current_time = datetime.datetime.now().time()
        self.logger.debug("label = '%s', actual = %d" % (
            label,
            value))

        # assert manual control (chan. 10) with new config, value, & label:
        dial.update(dict(
            channel_configuration=dict(channel_id="10"),
            dial_configuration=dial_config,
            label=label,
            value=value,
        ))

    def set_clock(self, dial_id, timezone):
        dial = self.dials()[dial_id]
        config = {
            "channel_configuration":{
                "timezone":timezone,
                'channel_id': '1'
            },
        }
        return dial.update(config)

    def set_weather(self, dial_id, lat, lng):
        dial = self.dials()[dial_id]
        config = {
            "channel_configuration": {
                'channel_id': '2',
                'lat_lng': [lat, lng],
                'locale': 'en_US',
                'reading_type': 'weather_conditions',
                'location': '',
                'units': {'temperature': 'f'}

            },


        }
        return dial.update(config)

    def flash(self, dial_id, message):
        dial = self.dials()[dial_id]
        original_config = dial.get_config()
        dial.update({"label":"harper"})
        time.sleep(1)
        dial.update(original_config)





if __name__ == "__main__":


    w = WinkManualControl("./config.cfg")

    url = "http://chicago.transitapi.com/bustime/map/getStopPredictions.jsp?stop=15206&route=66"

    r = requests.get(url)

    e = ET.XML(r.text)
    from pprint import pprint
    bus = etree_to_dict(e)

    try:
        stop =  bus['stop']['pre'][0]
    except:
        stop = bus['stop']['pre']
    value = 0
    if (stop['pt'] == "APPROACHING"):
        value = 0
    else:
        v = stop['pt'].replace(" MIN","")
        value =  720/360 * int(v)



    w.set_manual_dial(0,label=stop['pt'], value=value)
   
