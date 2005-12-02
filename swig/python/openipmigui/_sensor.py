# _sensor.py
#
# openipmi GUI handling for sensors
#
# Author: MontaVista Software, Inc.
#         Corey Minyard <minyard@mvista.com>
#         source@mvista.com
#
# Copyright 2005 MontaVista Software Inc.
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public License
#  as published by the Free Software Foundation; either version 2 of
#  the License, or (at your option) any later version.
#
#
#  THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESS OR IMPLIED
#  WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
#  MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
#  IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
#  INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
#  BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS
#  OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
#  ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
#  TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
#  USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this program; if not, write to the Free
#  Software Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
import wx
import OpenIPMI

class SensorRefreshData:
    def __init__(self, s):
        self.s = s

    def sensor_cb(self, sensor):
        sensor.get_value(self.s)


class SensorInfoGetter:
    def __init__(self, s, func):
        self.s = s;
        self.func = func;

    def DoUpdate(self):
        self.s.sensor_id.to_sensor(self)

    def sensor_cb(self, sensor):
        getattr(sensor, self.func)(self.s)


threshold_strings = [ 'un', 'uc', 'ur', 'ln', 'lc', 'lr' ]
threshold_full_strings = [ 'upper non-critical',
                           'upper critical',
                           'upper non-recoverable',
                           'lower non-critical',
                           'lower critical',
                           'lower non-recoverable' ]

def threshold_str_to_full(s):
    i = threshold_strings.index(s)
    return threshold_full_strings[i]

threshold_event_strings = [ 'unha', 'unhd', 'unla', 'unld',
                            'ucha', 'uchd', 'ucla', 'ucld',
                            'urha', 'urhd', 'urla', 'urld',
                            'lnha', 'lnhd', 'lnla', 'lnld',
                            'lcha', 'lchd', 'lcla', 'lcld',
                            'lrha', 'lrhd', 'lrla', 'lrld' ]

def threshold_event_str_to_full(s):
    rv = threshold_str_to_full(s[0:2])
    if (s[2] == 'h'):
        rv += " going high"
    else:
        rv += " going low"
    if (s[3] == 'a'):
        rv += " assertion"
    else:
        rv += " deassertion"
    return rv


class SensorHysteresisSet(wx.Dialog):
    def __init__(self, s):
        wx.Dialog.__init__(self, None, -1, "Set Hysteresis for " + str(s))
        self.s = s
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        box = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self, -1, "Positive:")
        box.Add(label, 0, wx.ALIGN_LEFT | wx.ALL, 5)
        self.pos = wx.TextCtrl(self, -1, "")
        box.Add(self.pos, 0, wx.ALIGN_LEFT | wx.ALL, 5)
        sizer.Add(box, 0, wx.ALIGN_LEFT | wx.ALL, 2)
        
        box = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self, -1, "Negative:")
        box.Add(label, 0, wx.ALIGN_LEFT | wx.ALL, 5)
        self.neg = wx.TextCtrl(self, -1, "")
        box.Add(self.neg, 0, wx.ALIGN_LEFT | wx.ALL, 5)
        sizer.Add(box, 0, wx.ALIGN_LEFT | wx.ALL, 2)

        box = wx.BoxSizer(wx.HORIZONTAL)
        cancel = wx.Button(self, -1, "Cancel")
        self.Bind(wx.EVT_BUTTON, self.cancel, cancel);
        box.Add(cancel, 0, wx.ALIGN_LEFT | wx.ALL, 5);
        ok = wx.Button(self, -1, "Ok")
        self.Bind(wx.EVT_BUTTON, self.ok, ok);
        box.Add(ok, 0, wx.ALIGN_LEFT | wx.ALL, 5);
        sizer.Add(box, 0, wx.ALIGN_CENTRE | wx.ALL, 2)

        self.SetSizer(sizer)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.CenterOnScreen();
        self.setting = False
        if (s.sensor_id.to_sensor(self) != 0):
            self.Destroy()

    def cancel(self, event):
        self.Close()

    def ok(self, event):
        try:
            self.positive = int(self.pos.GetValue())
        except:
            return
        try:
            self.negative = int(self.neg.GetValue())
        except:
            return
        self.s.sensor_id.to_sensor(self)
        self.Close()

    def OnClose(self, event):
        self.Destroy()

    def sensor_cb(self, sensor):
        if (self.setting):
            sensor.set_hysteresis(self.positive, self.negative)
            sensor.get_hysteresis(self.s)
        else:
            sensor.get_hysteresis(self)
            self.setting = True

    def sensor_get_hysteresis_cb(self, sensor, err, positive, negative):
        if (err != 0):
            self.Destroy()
        else:
            self.pos.SetValue(str(positive))
            self.neg.SetValue(str(negative))
            self.Show(True);


class SensorThresholdsSet(wx.Dialog):
    def __init__(self, s):
        wx.Dialog.__init__(self, None, -1, "Set Thresholds for " + str(s))
        self.s = s
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.thresholds = { }
        for th in s.settable_thresholds:
            box = wx.BoxSizer(wx.HORIZONTAL)
            label = wx.StaticText(self, -1, threshold_str_to_full(th))
            box.Add(label, 0, wx.ALIGN_LEFT | wx.ALL, 5)
            th_text_box = wx.TextCtrl(self, -1, "")
            self.thresholds[th] = th_text_box
            box.Add(th_text_box, 0, wx.ALIGN_LEFT | wx.ALL, 5)
            sizer.Add(box, 0, wx.ALIGN_LEFT | wx.ALL, 2)
        
        box = wx.BoxSizer(wx.HORIZONTAL)
        cancel = wx.Button(self, -1, "Cancel")
        self.Bind(wx.EVT_BUTTON, self.cancel, cancel);
        box.Add(cancel, 0, wx.ALIGN_LEFT | wx.ALL, 5);
        ok = wx.Button(self, -1, "Ok")
        self.Bind(wx.EVT_BUTTON, self.ok, ok);
        box.Add(ok, 0, wx.ALIGN_LEFT | wx.ALL, 5);
        sizer.Add(box, 0, wx.ALIGN_CENTRE | wx.ALL, 2)

        self.SetSizer(sizer)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.CenterOnScreen();

        if (self.s.threshold_support == OpenIPMI.THRESHOLD_ACCESS_SUPPORT_READABLE):
            self.setting = False
            if (s.sensor_id.to_sensor(self) != 0):
                self.Destroy()
        else:
            # Can't read them, just set.
            self.setting = False
            self.Show()

    def cancel(self, event):
        self.Close()

    def ok(self, event):
        try:
            self.positive = float(self.pos.GetValue())
        except:
            return
        try:
            self.negative = int(self.neg.GetValue())
        except:
            return
        self.s.sensor_id.to_sensor(self)
        self.Close()

    def OnClose(self, event):
        self.Destroy()

    def sensor_cb(self, sensor):
        if (self.setting):
            sensor.set_thresholds(self.positive, self.negative)
            sensor.get_thresholds(self.s)
        else:
            sensor.get_thresholds(self)

    def sensor_get_thresholds_cb(self, sensor, err, th):
        if (err != 0):
            self.Destroy()
            return
        for i in th.split(':'):
            j = i.split(' ')
            self.thresholds[j[0]].SetValue(j[1])
        self.Show()


class Sensor:
    def __init__(self, e, sensor):
        self.e = e
        self.name = sensor.get_name()
        self.sensor_id = sensor.get_id()
        self.ui = e.ui
        ui = self.ui
        self.updater = SensorRefreshData(self)
        ui.add_sensor(self.e, self)
        self.in_warning = False
        self.in_severe = False
        self.in_critical = False
        self.ui.append_item(self, "Sensor Type",
                            sensor.get_sensor_type_string())
        self.ui.append_item(self, "Event Reading Type",
                            sensor.get_event_reading_type_string())
        m = sensor.get_mc()
        self.ui.append_item(self, "Msg Routing Info",
                            "MC: " + m.get_name()
                            + "  LUN:" + str(sensor.get_lun())
                            + "  Num:" + str(sensor.get_num()))
                            
        self.event_support = sensor.get_event_support()
        es = self.event_support
        self.ui.append_item(self, "Event Support",
                            OpenIPMI.get_event_support_string(es))
        if ((es == OpenIPMI.EVENT_SUPPORT_PER_STATE)
            or (es == OpenIPMI.EVENT_SUPPORT_ENTIRE_SENSOR)):
            self.event_enables = self.ui.append_item(self, "Event Enables",
                                      None,
                                      data = SensorInfoGetter(self,
                                                       "get_event_enables"))

        self.auto_rearm = sensor.get_supports_auto_rearm()

        self.is_threshold = (sensor.get_event_reading_type()
                             == OpenIPMI.EVENT_READING_TYPE_THRESHOLD)
        if (self.is_threshold):
            self.threshold_sensor_units = sensor.get_base_unit_string()
            modifier = sensor.get_modifier_unit_use();
            if (modifier == OpenIPMI.MODIFIER_UNIT_BASE_DIV_MOD):
               self.threshold_sensor_units += "/"
            elif (modifier == OpenIPMI.MODIFIER_UNIT_BASE_MULT_MOD):
               self.threshold_sensor_units += "*"
            modifier = sensor.get_modifier_unit_string()
            if (modifier != "unspecified"):
                self.threshold_sensor_units += modifier
            self.threshold_sensor_units += sensor.get_rate_unit_string()
            if (sensor.get_percentage()):
                self.threshold_sensor_units += '%'

            sval = ""
            fval = [ 0.0 ]
            rv = sensor.get_nominal_reading(fval)
            if (rv == 0):
                sval += "  Nominal:" + str(fval[0])
            rv = sensor.get_sensor_min(fval)
            if (rv == 0):
                sval += "  Min:" + str(fval[0])
            rv = sensor.get_sensor_max(fval)
            if (rv == 0):
                sval += "  Max:" + str(fval[0])
            rv = sensor.get_normal_min(fval)
            if (rv == 0):
                sval += "  NormalMin:" + str(fval[0])
            rv = sensor.get_normal_max(fval)
            if (rv == 0):
                sval += "  NormalMax:" + str(fval[0])
            if (sval != ""):
                sval = sval.strip()
                self.ui.append_item(self, "Ranges", sval);

            self.threshold_support = sensor.get_threshold_access()
            ts = self.threshold_support
            self.ui.append_item(self, "Threshold Support",
                              OpenIPMI.get_threshold_access_support_string(ts))
            sval = ""
            if (ts != OpenIPMI.THRESHOLD_ACCESS_SUPPORT_NONE):
                rval = ""
                wval = ""
                ival = [ 0 ]
                for th in threshold_strings:
                    rv = sensor.threshold_settable(th, ival)
                    if (rv == 0) and (ival[0] == 1):
                        sval += " " + th
                    rv = sensor.threshold_readable(th, ival)
                    if (rv == 0) and (ival[0] == 1):
                        rval += " " + th
                    rv = sensor.threshold_reading_supported(th, ival)
                    if (rv == 0) and (ival[0] == 1):
                        wval += " " + th
                if (wval != ""):
                    wval = wval.strip()
                    self.ui.append_item(self, "Thresholds Reported", wval)

            if ((ts == OpenIPMI.THRESHOLD_ACCESS_SUPPORT_READABLE)
                or (ts == OpenIPMI.THRESHOLD_ACCESS_SUPPORT_SETTABLE)):
                if (sval != ""):
                    sval = sval.strip()
                    self.ui.append_item(self, "Settable Thresholds", sval)
                if (rval != ""):
                    rval = rval.strip()
                    self.ui.append_item(self, "Readable Thresholds", rval)
                        
                self.thresholds = self.ui.append_item(self, "Thresholds",
                                      None,
                                      data = SensorInfoGetter(self,
                                                       "get_thresholds"))
            else:
                sval = ""

            self.settable_thresholds = sval

            self.hysteresis_support = sensor.get_hysteresis_support()
            hs = self.hysteresis_support
            self.ui.append_item(self, "Hysteresis Support",
                                OpenIPMI.get_hysteresis_support_string(hs))
            if ((hs == OpenIPMI.HYSTERESIS_SUPPORT_READABLE)
                or (hs == OpenIPMI.HYSTERESIS_SUPPORT_SETTABLE)):
                self.hysteresis =  self.ui.append_item(self, "Hysteresis",
                                     None,
                                     data = SensorInfoGetter(self,
                                                             "get_hysteresis"))
        else:
            self.hysteresis_support = OpenIPMI.HYSTERESIS_SUPPORT_NONE
            self.threshold_support = OpenIPMI.THRESHOLD_ACCESS_SUPPORT_NONE
                
    def __str__(self):
        return self.name

    def DoUpdate(self):
        self.sensor_id.to_sensor(self.updater)

    def HandleMenu(self, event):
        eitem = event.GetItem();
        menu = wx.Menu();
        doit = False
        if (self.event_support != OpenIPMI.EVENT_SUPPORT_NONE):
            item = menu.Append(-1, "Rearm")
            self.ui.Bind(wx.EVT_MENU, self.Rearm, item)
            doit = True
        if (self.threshold_support == OpenIPMI.THRESHOLD_ACCESS_SUPPORT_SETTABLE):
            item = menu.Append(-1, "Set Thresholds")
            self.ui.Bind(wx.EVT_MENU, self.SetThresholds, item)
            doit = True
        if (self.hysteresis_support == OpenIPMI.HYSTERESIS_SUPPORT_SETTABLE):
            item = menu.Append(-1, "Set Hysteresis")
            self.ui.Bind(wx.EVT_MENU, self.SetHysteresis, item)
            doit = True
        if ((self.event_support == OpenIPMI.EVENT_SUPPORT_PER_STATE)
            or (self.event_support == OpenIPMI.EVENT_SUPPORT_ENTIRE_SENSOR)):
            item = menu.Append(-1, "Set Event Enables")
            self.ui.Bind(wx.EVT_MENU, self.SetEventEnables, item)
            doit = True

        if (doit):
            self.ui.PopupMenu(menu, self.ui.get_item_pos(eitem))
        menu.Destroy()

    def Rearm(self, event):
        pass
    
    def SetThresholds(self, event):
        pass
    
    def SetHysteresis(self, event):
        SensorHysteresisSet(self)
    
    def SetEventEnables(self, event):
        pass
    
    def remove(self):
        self.e.sensors.pop(self.name)
        self.ui.remove_sensor(self)

    def handle_threshold_states(self, states):
        th = states.split()
        while len(th) > 0:
            v = th[0]
            del th[0]

            if (v == "un") or (v == "ln"):
                if (not self.in_warning):
                    self.in_warning = True
                    self.ui.incr_item_warning(self.treeroot)
            else:
                if (self.in_warning):
                    self.in_warning = False
                    self.ui.decr_item_warning(self.treeroot)

            if (v == "uc") or (v == "lc"):
                if (not self.in_severe):
                    self.in_severe = True
                    self.ui.incr_item_severe(self.treeroot)
            else:
                if (self.in_severe):
                    self.in_severe = False
                    self.ui.decr_item_severe(self.treeroot)

            if (v == "ur") or (v == "lr"):
                if (not self.in_critical):
                    self.in_critical = True
                    self.ui.incr_item_critical(self.treeroot)
            else:
                if (self.in_critical):
                    self.in_critical = False
                    self.ui.decr_item_critical(self.treeroot)


    def threshold_reading_cb(self, sensor, err, raw_set, raw, value_set,
                             value, states):
        if (err):
            self.ui.set_item_text(self.treeroot, None)
            return
        v = ""
        if (value_set):
            v += str(value) + self.threshold_sensor_units
        if (raw_set):
            v += " (" + str(raw) + ")"
        v += ": " + states
        self.ui.set_item_text(self.treeroot, v)
        self.handle_threshold_states(states)
        
    def discrete_states_cb(self, sensor, err, states):
        if (err):
            self.ui.set_item_text(self.treeroot, None)
            return
        self.ui.set_item_text(self.treeroot, states)
        
    def sensor_get_event_enable_cb(self, sensor, err, states):
        if (err != 0):
            self.ui.set_item_text(self.event_enables, None)
            return
        self.ui.set_item_text(self.event_enables, states)

    def sensor_get_hysteresis_cb(self, sensor, err, positive, negative):
        if (err != 0):
            self.ui.set_item_text(self.hysteresis, None)
            return
        self.ui.set_item_text(self.hysteresis,
                              "Positive:" + str(positive)
                              + " Negative:" + str(negative))

    def sensor_get_thresholds_cb(self, sensor, err, th):
        if (err != 0):
            self.ui.set_item_text(self.thresholds, None)
            return
        self.ui.set_item_text(self.thresholds, th)