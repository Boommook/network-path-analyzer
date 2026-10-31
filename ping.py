import re
import statistics
import platform
import subprocess
import os

# ------------------------------------------------------------
# Procedure: ping_destination
#
# Purpose: Run the system ping command against a destination
# and capture the command output.
# 
# Parameters: 
# - destination - the hostname or IP address to ping
# - ping_count - the number of pings to send (default: 4)
# - timeout - the timeout in seconds (default: 15)
#
# Other inputs: the system platform
#
# Returns: The standard output, standard error, and return code
# produced by the ping command, and a status string.
#
# References:
# - https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/ping (Windows ping command)
# - https://www.geeksforgeeks.org/linux-unix/ping-command-in-linux-with-examples/ (Linux ping command)
# ------------------------------------------------------------
def ping_destination(destination, ping_count=4, timeout=25):
    system = platform.system().lower()

    # the second parameter is the IP version to use (IPv4) (matches traceroute_destination)
    if system == 'windows':
        command = ["ping", "-4", "-n", str(ping_count), destination]
    else:
        command = ["ping", "-4", "-c", str(ping_count), destination]

    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        return result.stdout, result.stderr, result.returncode, "completed"

    # handle a timeout error (currently a problem for wpi.edu)
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout
        stderr = error.stderr

        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")

        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")

        return stdout, f"Ping timed out: {destination}; stderr: {stderr or ''}", None, "timeout"
    except OSError as error:
        return None, f"Error: Failed to ping {destination}: {error}", None, "error"

# ------------------------------------------------------------
# Example ping output (Windows):
# PS C:\Users\boomm> ping -n 4 google.com

# Pinging google.com [2607:f8b0:4002:c06::64] with 32 bytes of data:
# Reply from 2607:f8b0:4002:c06::64: time=41ms
# Reply from 2607:f8b0:4002:c06::64: time=37ms
# Reply from 2607:f8b0:4002:c06::64: time=40ms
# Reply from 2607:f8b0:4002:c06::64: time=52ms
#
# Ping statistics for 2607:f8b0:4002:c06::64:
#     Packets: Sent = 4, Received = 4, Lost = 0 (0% loss),
# Approximate round trip times in milli-seconds:
#     Minimum = 37ms, Maximum = 52ms, Average = 42ms
# 
# ------------------------------------------------------------
#
# Example ping output (Linux):
# Craptop:~# ping -c 4 google.com
# PING google.com (64.233.176.113): 56 data bytes
# 64 bytes from 64.233.176.113: seq=0 ttl=96 time=43.729 ms
# 64 bytes from 64.233.176.113: seq=1 ttl=96 time=39.819 ms
# 64 bytes from 64.233.176.113: seq=2 ttl=96 time=38.478 ms
# 64 bytes from 64.233.176.113: seq=3 ttl=96 time=37.660 ms
#
# --- google.com ping statistics ---
# 4 packets transmitted, 4 packets received, 0% packet loss
# round-trip min/avg/max = 37.660/39.921/43.729 ms
# ------------------------------------------------------------

# ------------------------------------------------------------
# Procedure: parse_ping_output
#
# Purpose: Parse the output of the system ping command to
# extract the packet loss and RTT statistics. Calculate the
# standard deviation of RTT manually using statistics.
#
# Parameters:
# - output - the output of the system ping command
#
# Other inputs: the system platform
#
# Returns: a dictionary containining packet loss, minimum RTT,
# average RTT, maximum RTT, and standard deviation of RTT (if available)
# 
# References: 
# - https://docs.python.org/3/library/re.html (regular expressions for parsing)
# - https://www.geeksforgeeks.org/python/re-search-in-python/ (re.search() for searching)
# - https://www.geeksforgeeks.org/python/re-matchobject-group-function-in-python-regex/ (match.group() for extracting values)
# - https://www.geeksforgeeks.org/python/re-findall-in-python/ (re.findall() for finding all matches)
# - https://www.w3schools.com/python/module_statistics.asp (statistics module. subpages for stddev calcs can be found here)
# ------------------------------------------------------------
def parse_ping_output(output):
    if output is None:
        return None

    system_name = platform.system().lower()

    packet_loss = None
    min_rtt = None
    max_rtt = None
    avg_rtt = None
    stddev_rtt = None

    if system_name == 'windows':
        # https://www.geeksforgeeks.org/python/re-search-in-python/
        # re.search() is used to search the string for a match, and returns a match object if there isn't one
        # ex. (0% loss)
        loss_match = re.search(r"\((\d+)% loss\)", output)
        # ex. Average = 42ms
        rtt_match = re.search(r"Minimum = (\d+)ms, Maximum = (\d+)ms, Average = (\d+)ms", output)

        # https://www.geeksforgeeks.org/python/re-matchobject-group-function-in-python-regex/
        # now extract the desired values from the match objects
        if loss_match:
            packet_loss = float(loss_match.group(1)) # group(1) is the first captured group
        
        if rtt_match:
            min_rtt = float(rtt_match.group(1))
            max_rtt = float(rtt_match.group(2))
            avg_rtt = float(rtt_match.group(3))
    
    else:
        # ex. 0% packet loss
        loss_match = re.search(r"(\d+(?:\.\d+)?)% packet loss", output)
        
        # some systems return min/avg/max others return min/avg/max/stddev
        # for the sake of consistency, we will only use the min/avg/max values
        # and manually calculate the standard deviation of RTT using the statistics module

        # ex. = 37.660/39.921/43.729 ms
        rtt_match = re.search(r"= ([\d.]+)/([\d.]+)/([\d.]+)(?:/[\d.]+)?\s*ms", output)

        if loss_match:
            packet_loss = float(loss_match.group(1))
        
        if rtt_match:
            min_rtt = float(rtt_match.group(1))
            avg_rtt = float(rtt_match.group(2))
            max_rtt = float(rtt_match.group(3))
    
    # extract the standard deviation of RTT manually using statistics
    if system_name == 'windows':
        # ex. from mit.edu: Reply from 2600:1402:b800:d84::255e: time=38ms
        # also handles cases where time < 1ms (which gets approximated as 1ms)
        rtt_vals = re.findall(r"time[<=]([\d.]+)\s*ms", output, re.IGNORECASE)
    else:
        # ex. from mit.edu: 64 bytes from a23-49-179-66.deploy.static.akamaitechnologies.com (23.49.179.66): icmp_seq=1 ttl=48 time=24.1 ms
        rtt_vals = re.findall(r"time=([\d.]+)\s*ms", output, re.IGNORECASE)
    
    # calculate the sampled standard deviation
    if len(rtt_vals) >= 2 : # at least 2 RTT values are needed to calculate the standard deviation
        rtt_vals = [float(rtt) for rtt in rtt_vals]
        stddev_rtt = statistics.stdev(rtt_vals)

    return {
        "packet_loss": packet_loss,
        "min_rtt": min_rtt,
        "avg_rtt": avg_rtt,
        "max_rtt": max_rtt,
        "stddev_rtt": stddev_rtt
    }