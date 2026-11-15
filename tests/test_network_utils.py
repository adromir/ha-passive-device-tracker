"""Tests for network utilities (ARP table parser and ping)."""

import unittest
from custom_components.passive_device_tracker.arp import (
    normalize_mac,
    parse_proc_net_arp,
    parse_ip_neigh,
    parse_windows_arp,
)
from custom_components.passive_device_tracker.ping import _parse_latency


class TestNetworkUtils(unittest.TestCase):
    """Test ARP and Ping parsing utilities."""

    def test_parse_latency(self):
        """Test latency extraction from ping output."""
        linux_output = "64 bytes from 192.168.2.1: icmp_seq=1 ttl=64 time=3.42 ms"
        self.assertEqual(_parse_latency(linux_output), 3.42)

        windows_output = "Antwort von 192.168.2.1: Bytes=32 Zeit=12ms TTL=64"
        self.assertEqual(_parse_latency(windows_output), 12.0)

        windows_fast = "Antwort von 192.168.2.1: Bytes=32 Zeit<1ms TTL=64"
        self.assertEqual(_parse_latency(windows_fast), 1.0)

        empty_output = "Request timed out."
        self.assertIsNone(_parse_latency(empty_output))

    def test_normalize_mac(self):
        """Test MAC normalization."""
        self.assertEqual(normalize_mac("AA:BB:CC:DD:EE:FF"), "aa:bb:cc:dd:ee:ff")
        self.assertEqual(normalize_mac("AA-BB-CC-DD-EE-FF"), "aa:bb:cc:dd:ee:ff")
        self.assertEqual(normalize_mac("aabb.ccdd.eeff"), "aa:bb:cc:dd:ee:ff")
        self.assertEqual(normalize_mac("  aa:bb:cc:dd:ee:ff  "), "aa:bb:cc:dd:ee:ff")
        self.assertIsNone(normalize_mac("invalid-mac"))
        self.assertIsNone(normalize_mac(""))

    def test_parse_proc_net_arp(self):
        """Test parsing /proc/net/arp table."""
        sample_arp = """IP address       HW type     Flags       HW address            Mask     Device
192.168.2.1      0x1         0x2         aa:bb:cc:dd:ee:01     *        eth0
192.168.2.50     0x1         0x2         AA:BB:CC:DD:EE:02     *        eth0
192.168.2.99     0x1         0x0         00:00:00:00:00:00     *        eth0
"""
        mac_to_ip = parse_proc_net_arp(sample_arp)
        self.assertEqual(mac_to_ip.get("aa:bb:cc:dd:ee:01"), "192.168.2.1")
        self.assertEqual(mac_to_ip.get("aa:bb:cc:dd:ee:02"), "192.168.2.50")
        # Incomplete entry (Flags 0x0) should be ignored
        self.assertNotIn("00:00:00:00:00:00", mac_to_ip)

    def test_parse_ip_neigh(self):
        """Test parsing ip neigh output."""
        sample_neigh = """192.168.2.1 dev eth0 lladdr aa:bb:cc:dd:ee:01 REACHABLE
192.168.2.50 dev eth0 lladdr aa:bb:cc:dd:ee:02 STALE
192.168.2.99 dev eth0  FAILED
"""
        mac_to_ip = parse_ip_neigh(sample_neigh)
        self.assertEqual(mac_to_ip.get("aa:bb:cc:dd:ee:01"), "192.168.2.1")
        self.assertEqual(mac_to_ip.get("aa:bb:cc:dd:ee:02"), "192.168.2.50")
        self.assertEqual(len(mac_to_ip), 2)

    def test_parse_windows_arp(self):
        """Test parsing Windows arp -a output."""
        sample_win_arp = """
Interface: 192.168.2.100 --- 0x10
  Internet Address      Physical Address      Type
  192.168.2.1           aa-bb-cc-dd-ee-01     dynamic
  192.168.2.50          aa-bb-cc-dd-ee-02     dynamic
  192.168.2.255         ff-ff-ff-ff-ff-ff     static
"""
        mac_to_ip = parse_windows_arp(sample_win_arp)
        self.assertEqual(mac_to_ip.get("aa:bb:cc:dd:ee:01"), "192.168.2.1")
        self.assertEqual(mac_to_ip.get("aa:bb:cc:dd:ee:02"), "192.168.2.50")


if __name__ == "__main__":
    unittest.main()
