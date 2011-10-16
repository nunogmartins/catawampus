#!/usr/bin/python
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409

"""Implementation of tr-181 Device.Ethernet hierarchy of objects.

Handles the Device.Ethernet portion of TR-181, as described
in http://www.broadband-forum.org/cwmp/tr-181-2-2-0.html
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import pynetlinux
import string
import subprocess
import tr.core
import tr.tr181_v2_2

BASEETHERNET = tr.tr181_v2_2.Device_v2_2.Device.Ethernet

e_states = dict()

class NetdevStatsLinux26(object):
  # Fields in /proc/net/dev
  _RX_BYTES = 0
  _RX_PKTS = 1
  _RX_ERRS = 2
  _RX_DROP = 3
  _RX_FIFO = 4
  _RX_FRAME = 5
  _RX_COMPRESSED = 6
  _RX_MCAST = 7
  _TX_BYTES = 8
  _TX_PKTS = 9
  _TX_DROP = 10
  _TX_FIFO = 11
  _TX_COLLISIONS = 12
  _TX_CARRIER = 13
  _TX_COMPRESSED = 14

  def __init__(self, proc_net_dev='/proc/net/dev'):
    self._proc_net_dev = proc_net_dev

  def get_stats(self, ifname, ethstat):
    ifstats = self._ReadProcNetDev(ifname, self._proc_net_dev)
    ethstat.BroadcastPacketsReceived = None
    ethstat.BroadcastPacketsSent = None
    ethstat.BytesReceived = ifstats[self._RX_BYTES]
    ethstat.BytesSent = ifstats[self._TX_BYTES]
    ethstat.DiscardPacketsReceived = ifstats[self._RX_DROP]
    ethstat.DiscardPacketsSent = ifstats[self._TX_DROP]

    err = int(ifstats[self._RX_ERRS]) + int(ifstats[self._RX_FRAME])
    ethstat.ErrorsReceived = str(err)

    ethstat.ErrorsSent = ifstats[self._TX_FIFO]
    ethstat.MulticastPacketsReceived = ifstats[self._RX_MCAST]
    ethstat.MulticastPacketsSent = None
    ethstat.PacketsReceived = ifstats[self._RX_PKTS]
    ethstat.PacketsSent = ifstats[self._TX_PKTS]

    rx = int(ifstats[self._RX_PKTS]) - int(ifstats[self._RX_MCAST])
    ethstat.UnicastPacketsReceived = str(rx)

    # Linux doesn't break out transmit uni/multi/broadcast, but we don't
    # want to return None for all of them. So we return all transmitted
    # packets as unicast, though some were surely multicast or broadcast.
    ethstat.UnicastPacketsSent = ifstats[self._TX_PKTS]
    ethstat.UnknownProtoPacketsReceived = None

  def _ReadProcNetDev(self, ifname, proc_net_dev):
    f = open(proc_net_dev)
    devices = dict()
    for line in f:
      fields = line.split(':')
      if (len(fields) == 2) and (fields[0].strip() == ifname):
        return fields[1].split()


class EthernetInterfaceStatsLinux26(BASEETHERNET.Interface.Stats):
  def __init__(self, ifname, devstat=NetdevStatsLinux26()):
    BASEETHERNET.Interface.Stats.__init__(self)
    devstat.get_stats(ifname, self)


class EthernetInterfaceLinux26(BASEETHERNET.Interface):
  def __init__(self, ifname, ifstats=None, pynet=None):
    BASEETHERNET.Interface.__init__(self)
    if pynet is None:
      pynet = pynetlinux.ifconfig.Interface(ifname)
    if ifstats is None:
      ifstats = EthernetInterfaceStatsLinux26(ifname)
    state = e_states[ifname]
    self.Alias = ifname
    self.DuplexMode = "Auto"
    self.Enable = True
    self.LastChange = 0  # TODO(dgentry) figure out date format
    self.LowerLayers = None  # Ethernet.Interface is L1, nothing below it.
    self.MACAddress = pynet.get_mac()
    self.MaxBitRate = -1
    self.Name = ifname
    self.Stats = ifstats
    self.Status = self._GetStatus(pynet)
    self.Upstream = state.upstream
    pynet = None

  def _GetStatus(self, pynet):
    if not pynet.is_up():
      return "Down"
    (speed, duplex, auto, link_up) = pynet.get_link_info()
    if link_up:
      return "Up"
    else:
      return "Dormant"


class EthernetState(object):
  def __init__(self, ifname, upstream):
    self.ifname = ifname
    self.upstream = upstream


class Ethernet(BASEETHERNET):
  def __init__(self):
    BASEETHERNET.__init__(self)
    self.InterfaceList = []
    self.LinkList = []
    self.VLANTerminationList = []

  def add_interface(self, ifname, upstream, interface):
    state = EthernetState(ifname, upstream)
    e_states[ifname] = state
    self.InterfaceList.append(interface)

  @property
  def InterfaceNumberOfEntries(self):
    return len(self.InterfaceList)

  def add_link(self, link):
    self.LinkList.append(link)

  @property
  def LinkNumberOfEntries(self):
    return len(self.LinkList)

  def add_vlan(self, vlan):
    self.VLANTerminationList.append(vlan)

  @property
  def VLANTerminationNumberOfEntries(self):
    return len(self.VLANTerminationList)


def main():
  pass

if __name__ == '__main__':
  main()