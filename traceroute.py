import platform
import re
import subprocess
import statistics
import ipaddress
import csv
import os

#-----------------------------------------------------------
# Procedure: traceroute_destination
# 
# Purpose: Run the system traceroute command against a destination
# and capture the command output.
#
# Parameters:
# - destination - the hostname to traceroute on
# - max_hops - the maximum number of hops to trace (default: 30)
#              this was decided upon by a few rounds of trial and error to find a reasonable number of hops to not cut off the traceroute
#              and not take too long to run.
# - timeout - the timeout in seconds (default: 120)
#
# Other inputs: the system platform
#
# Returns:
# - The standard output, standard error, and return code
#   produced by the traceroute command, and a status string.
#
# References:
# - https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/tracert (Windows tracert command)
# - https://www.geeksforgeeks.org/linux-unix/traceroute-command-in-linux-with-examples/ (Linux traceroute command)
# Note: Both Linux traceroute and Windows tracert uses ICMP probes
# -----------------------------------------------------------
def traceroute_destination(destination, max_hops=35, timeout=120):
    system = platform.system().lower()
    # the second parameter is the IP version to use (IPv4)
    # the third parameter disables reverse DNS lookups
    if system == 'windows':
        command = ["tracert", "-4", "-d", "-h", str(max_hops), "-w", "1000", destination]
    else:
        command = ["traceroute", "-4", "-I", "-n", "-m", str(max_hops), "-w", "1", destination]
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        print(result.stdout)
        return result.stdout, result.stderr, result.returncode, "completed"
    
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout
        stderr = error.stderr

        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")

        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")

        return stdout, f"Traceroute timed out: {destination}; stderr: {stderr or 'None'}", None, "timeout"
    except OSError as error:
        return None, f"Error: Failed to traceroute {destination}: {error}", None, "error"


# ------------------------------------------------------------
# Procedure: parse_traceroute_output
#
# Purpose: Extract the destination's IP address from the 
# output of the system traceroute command.
#
# Parameters:
# - output - the output of the system traceroute command
#
# Returns: The destination's IP address as a string, or 
# None if the destination's IP address is not found.
# ------------------------------------------------------------
def extract_traceroute_destination_ip(output):
    if not output:
        return None

    patterns = [
        # Windows hostname w bracketed IP. ex. Tracing route to google.com [74.125.21.100]
        r"Tracing route to .+?\[([^\]]+)\]",

        # Windows when tracing a direct IP address. ex. Tracing route to 142.250.190.14
        r"^\s*Tracing route to\s+(\S+)",

        # Linux traceroute header. ex. traceroute to google.com (142.250.190.14)
        r"traceroute to .+?\(([^)]+)\)",
    ]

    for pattern in patterns:
        match = re.search(pattern, output, re.IGNORECASE | re.MULTILINE)
        if match:
            try:
                return str(ipaddress.ip_address(match.group(1)))
            except ValueError:
                continue

    return None


# ------------------------------------------------------------
# Prcoedure: parse_traceroute_output
#
# Purpose: Parse the output of the system traceroute command to 
# extract each hop's IP address(es) and RTT measurements.
# 
# Parameters:
# - output - the output of the system traceroute command
#
# Other inputs: the system platform
#
# Returns:
# - A list of dictionaries containing the hop number, IP address(es), RTT measurements, and status for each hop
#
# Notes:
# - Windows and Linux use diff formats. Windows prints the 3 RTT measurements
#   before the router address. Linux prints the router address before the 3 RTT measurements.
# - Linux can report multiple IP addresses at the same hop
#     ex. 10  96.34.2.64  14.900 ms 96.34.2.156  17.102 ms  16.404 ms
# - Some hops don't respond. ex. Linux hop 5: 5  * * 173.40.137.10 36.050 ms
# ------------------------------------------------------------
def parse_traceroute_output(output):
    if not output:
        return []
    
    system_name = platform.system().lower()
    hops = []

    # [rpcess traceroute output one line at a time
    for line in output.splitlines():
        # each hop line starts with its hop number (regardless of platform)
        hop_match = re.match(r"^\s*(\d+)\s+(.+)$", line)
        # if the line doesn't match the expected format, skip it
        if not hop_match:
            continue

        hop_number = int(hop_match.group(1))
        hop_output = hop_match.group(2)

        probed_ips = []
        probe_rtts = []

        elements = hop_output.split()

        if system_name == 'windows':
            # ex. 1    10 ms     2 ms     2 ms  2600:6c65:20f0:a40::1
            ip_addr = None
            
            if not elements:
                continue
            last_element = elements[-1] # last element is the IP address

            try:
                ip_addr = str(ipaddress.ip_address(last_element))
            except ValueError:
                pass

            # then extract the RTT measurements and timeouts
            probe_matches = re.findall(r"<\s*1\s*ms|\d+(?:\.\d+)?\s*ms|\*", hop_output, re.IGNORECASE)

            for probe in probe_matches[:3]:
                if probe == '*': # timeout
                    probed_ips.append(None)
                    probe_rtts.append(None)
                else:
                    rtt = re.search(r"[\d.]+", probe)

                    probed_ips.append(ip_addr)
                    probe_rtts.append(float(rtt.group(0)))
        else:
            # ex.  1  172.20.144.1  5.430 ms  5.089 ms  4.965 ms
            # here we need to handle multiple IP addresses at the same hop so
            # iterate through the elements until we find the next IP address or run out of elements

            # track the last valid IP address because some systems report multiple IP addresses at the same hop
            curr_ip = None
            index = 0

            while index < len(elements) and len(probed_ips) < 3: # at most 3 RTT measurements per hop
                element = elements[index]

                if element == '*': # timeout
                    probed_ips.append(None)
                    probe_rtts.append(None)
                
                else: # valid RTT measurement
                    # try to check if the element is a valid IP address
                    try:
                        curr_ip = str(ipaddress.ip_address(element))
                    except ValueError: # not a valid IP address
                        if (index + 1 < len(elements) and elements[index + 1] == 'ms'):
                            # if the next element is 'ms', then the current element is an RTT measurement
                            try:
                                rtt = float(element)
                                probed_ips.append(curr_ip)
                                probe_rtts.append(rtt)
                                index += 1 # skip the next element because it is 'ms'

                            except ValueError:
                                pass
                
                index += 1 # move to the next element

        # if no RTT measurements were found, skip this hop
        if not probe_rtts:
            continue    
        # otherwise...
        # if less than 3 RTT measurements were found, add None values to the list
        while len(probed_ips) < 3:
            probed_ips.append(None)
            probe_rtts.append(None)
        
        # calculate the average RTT
        # first filter out any None values
        valid_rtts = [rtt for rtt in probe_rtts if rtt is not None]
        avg_rtt = statistics.mean(valid_rtts) if valid_rtts else None

        if len(valid_rtts) == 3:
            status = "success"
        elif len(valid_rtts) > 0:
            status = "partial"
        else:
            status = "timeout"

        hops.append({
            "hop_number": hop_number,
            "probe_1_ip": probed_ips[0],
            "probe_1_rtt_ms": probe_rtts[0],
            "probe_2_ip": probed_ips[1],
            "probe_2_rtt_ms": probe_rtts[1],
            "probe_3_ip": probed_ips[2],
            "probe_3_rtt_ms": probe_rtts[2],
            "avg_rtt_ms": avg_rtt,
            "status": status
        })
        

    return hops

# ------------------------------------------------------------
# Procedure: load_and_group_traceroute_results
#
# Purpose: Load the traceroute results from a CSV file 
# and group them by run ID and destination
#
# Parameters:
# - filename - the name of the CSV file to load the results from
#
# Returns: A dictionary mapping (run ID, destination, destination IP) 
# to a list of traceroute results (hop records)
# ------------------------------------------------------------
def load_and_group_traceroute_results(filename):
    runs = {}

    with open(filename, 'r') as file:
        reader = csv.DictReader(file)

        for row in reader:
            # create a key for the dictionary based on the run ID, destination, and destination IP
            key = (
                row['run_id'],
                row['destination'],
                row['destination_ip']
            )

            # if the key isn't in the dictionary yet, add it
            if key not in runs:
                runs[key] = []

            # append the row to the list for the key
            runs[key].append(row)
        
    for hop in runs.values():
        # sort the hops by hop number
        hop.sort(key=lambda hop: int(hop['hop_number']))

    return runs


# ------------------------------------------------------------
# Procedure: check_traceroute_destination_reached
#
# Purpose: Check if the destination IP address is reached in the traceroute output.
#
# Parameters:
# - hops - a list of dictionaries containing the traceroute results
#           as returned by parse_traceroute_output
# - destination_ip - the destination IP address to check,
#                    as returned by extract_traceroute_destination_ip
#
# Returns: True if the destination IP address is reached, False otherwise.
# ------------------------------------------------------------
def check_traceroute_destination_reached(hops, destination_ip):
    if destination_ip is None:
        return None

    for hop in hops:
        for i in range(1, 4):
            if hop[f'probe_{i}_ip'] == destination_ip:
                print(f"Destination IP address reached at hop {hop['hop_number']}")
                return True
    print(f"Destination IP address not reached")
    return False
