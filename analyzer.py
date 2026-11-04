import platform
import csv
from datetime import datetime
import os
import socket

from ping import ping_destination, parse_ping_output
from traceroute import traceroute_destination, parse_traceroute_output, extract_traceroute_destination_ip, check_traceroute_destination_reached

# ------------------------------------------------------------
# Procedure: load_destination
#
# Purpose: load destination hostnames from a file and return
# them as a list.
#
# Parameters: filename - the name of the file to load
# Other inputs: the contents of the provided text file
#
# Returns: a list of the file's lines with leading and 
# trailing white spaces stripped.
# ------------------------------------------------------------
def load_destination(filename):
    with open(filename, 'r') as file:
        return [line.strip() for line in file if line.strip()] # only ping non-empty lines
            

# ------------------------------------------------------------
# Procedure: resolve_destination
#
# Purpose: Resolve a destination hostname to an IPv4 address
# so ping and traceroute test the same destination IP address
#
# Parameters:
# - destination - the hostname to resolve
#
# Returns: The IPV4 address of the destination as a string, or
# None if the destination is not found.
# ------------------------------------------------------------
def resolve_destination(destination):
    try:
        addr_info = socket.getaddrinfo(
            destination, 
            None, # port number is not needed for IPv4
            socket.AF_INET, # request IPv4 addr only
            socket.SOCK_STREAM # request adrr info for TCP sockets
        )

        # addr_info[0][4][0] is the IP address
        return addr_info[0][4][0]

    except socket.gaierror as error:
        print(f"Failed to resolve {destination}: {error}")
        return None

# ------------------------------------------------------------
# Procedure: save_ping_results
#
# Purpose: Save the collected ping results (from parse_ping_output)
# to a specified CSV file.
#
# Parameters:
# - results - a list of dictionaries containing the ping results
# - filename - the name of the CSV file to save the results to
#
# Returns: None
# ------------------------------------------------------------
def save_ping_results(results, filename):
    fieldnames = ['run_id', 'timestamp', 'operating_system', 'destination', 'destination_ip', 'command_status', 'packet_loss', 'min_rtt', 'avg_rtt', 'max_rtt', 'stddev_rtt']
    
    # check if the file exists and is not emptyw
    write_header = not os.path.exists(filename) or os.path.getsize(filename) == 0

    with open(filename, 'a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        
        if write_header:
            writer.writeheader()

        writer.writerows(results)

# ------------------------------------------------------------
# Procedure: save_traceroute_results
#
# Purpose: Save the collected traceroute results (from parse_traceroute_output)
# to a specified CSV file.
#
# Parameters:
# - results - a list of dictionaries containing the traceroute results
# - filename - the name of the CSV file to save the results to
#
# Returns: None
# ------------------------------------------------------------
def save_traceroute_results(results, filename):
    fieldnames = ['run_id', 'timestamp', 'operating_system', 'destination', 'destination_ip', 'destination_reached', 'command_status', 'hop_number', 'probe_1_ip', 'probe_1_rtt_ms', 'probe_2_ip', 'probe_2_rtt_ms', 'probe_3_ip', 'probe_3_rtt_ms', 'avg_rtt_ms', 'status']
    
    # check if the file exists and is not empty
    write_header = not os.path.exists(filename) or os.path.getsize(filename) == 0

    with open(filename, 'a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        
        if write_header:
            writer.writeheader()

        writer.writerows(results)

#-----------------------------------------------------------
# Procedure: record_error
#
# Purpose: Save the collected error results to a specified CSV file
#
# Parameters:
# - errors - a list of dictionaries containing the error results
# - filename - the name of the CSV file to save the results to
#
# Returns: None
# ------------------------------------------------------------
def record_error(errors, filename):
    fieldnames = ['run_id', 'timestamp', 'destination', 'stage', 'error_type', 'error_message']
    
    write_header = not os.path.exists(filename) or os.path.getsize(filename) == 0

    with open(filename, 'a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        
        if write_header:
            writer.writeheader()
        writer.writerows(errors)

# ------------------------------------------------------------
# Procedure: append_error
#
# Purpose: Form a dictionary of error details and append it to the list of errors
#
# Parameters:
# - errors - a list of dictionaries containing the error results
# - run_id - the run ID
# - destination - the destination hostname
# - stage - the stage of the error (ping or traceroute)
# - error_type - the type of the error (timeout or error)
# - error_message - the message of the error
#
# Returns: None
# ------------------------------------------------------------
def append_error(errors, run_id, destination, stage, error_type, error_message):
    errors.append({
        'run_id': run_id,
        'timestamp': datetime.now().isoformat(timespec='seconds'),
        'destination': destination,
        'stage': stage,
        'error_type': error_type,
        'error_message': error_message
    })

# ------------------------------------------------------------
# Procedure: main
#
# Purpose: Run the ping and traceroute functions for each
# destination in the destinations.txt file and save the results
# to the results directory and record any errors.
#
# Parameters: None
#
# Other inputs: the contents of the destinations.txt file
#
# Returns: None
#
# Other outputs:
# - results/ping_results.csv: a CSV file containing the ping results
# - results/traceroute_results.csv: a CSV file containing the traceroute results
# - results/errors.csv: a CSV file containing the error results
# ------------------------------------------------------------
def main():
    destinations = load_destination("destinations.txt")

    ping_results = []
    traceroute_results = []
    errors = []

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    operating_system = platform.system().lower()

    for destination in destinations:
        # add a separator between destinations
        print("=" * 50)
        print(f"Testing: {destination}")

        # ============================================================
        # Resolve destination
        # ============================================================
        resolved_ip = resolve_destination(destination)
        if resolved_ip is None:
            print(f"Skipping {destination} because it could not be resolved")
            append_error(errors, run_id, destination, 'dns', 'resolution_failed', "No IPv4 address resolved for destination")
            continue
        print(f"Resolved destination {destination} to {resolved_ip}")

        # ============================================================
        # Ping test
        # ============================================================
        print(f"Running ping for {destination}...", flush=True)
        ping_timestamp = datetime.now().isoformat(timespec='seconds')

        ping_output, ping_error, return_code, ping_status = ping_destination(resolved_ip, timeout=25)
        
        if ping_status != "completed":
            append_error(errors, run_id, destination, 'ping', ping_status, ping_error)

        elif return_code != 0:
            append_error(errors, run_id, destination, 'ping', 'nonzero_exit_code', f"Exit code: {return_code}; stderr: {ping_error}")

        metrics = parse_ping_output(ping_output)

        if metrics is None:
            # if no metrics are found, set them to None, rather than thowing an error and stopping the program
            metrics = {
                "packet_loss": None,
                "min_rtt": None,
                "avg_rtt": None,
                "max_rtt": None,
                "stddev_rtt": None
            }

        if ping_status == "completed" and metrics["packet_loss"] is None:
            append_error(errors, run_id, destination, 'ping', 'parse_failed', f"No packet loss data found: {ping_output}")
        
        # packet loss
        if metrics['packet_loss'] is not None:
            packet_loss = f"{metrics['packet_loss']}%"
        else:
            packet_loss = "N/A"

        # minimum RTT
        if metrics['min_rtt'] is not None:
            min_rtt = f"{metrics['min_rtt']}ms"
        else:
            min_rtt = "N/A"

        # average RTT
        if metrics['avg_rtt'] is not None:
            avg_rtt = f"{metrics['avg_rtt']}ms"
        else:
            avg_rtt = "N/A"

        # maximum RTT
        if metrics['max_rtt'] is not None:
            max_rtt = f"{metrics['max_rtt']}ms"
        else:
            max_rtt = "N/A"

        # standard deviation of RTT
        if metrics['stddev_rtt'] is not None:
            stddev_rtt = f"{metrics['stddev_rtt']:.3f}ms"
        else:
            stddev_rtt = "N/A"

        print(f"Packet Loss: {packet_loss}")
        print(f"Minimum RTT: {min_rtt}")
        print(f"Average RTT: {avg_rtt}")
        print(f"Maximum RTT: {max_rtt}")
        print(f"RTT Standard Deviation: {stddev_rtt}")

        # append the ping results to the list, but do not include units
        ping_results.append({
            "run_id": run_id,
            "timestamp": ping_timestamp,
            "operating_system": operating_system,
            "destination": destination,
            "destination_ip": resolved_ip,
            "command_status": ping_status,
            "packet_loss": metrics['packet_loss'],
            "min_rtt": metrics['min_rtt'],
            "avg_rtt": metrics['avg_rtt'],
            "max_rtt": metrics['max_rtt'],
            "stddev_rtt": metrics['stddev_rtt']
        })
        # ============================================================
        # End of Ping test
        # ============================================================

        # ============================================================
        # Traceroute test
        # ============================================================
        print(f"Running traceroute for {destination}...", flush=True)
        tracert_timestamp = datetime.now().isoformat(timespec='seconds')
        traceroute_output, traceroute_error, return_code, traceroute_status = traceroute_destination(resolved_ip, max_hops=35)

        if traceroute_status != "completed":
            append_error(errors, run_id, destination, 'traceroute', traceroute_status, traceroute_error)

        elif return_code != 0:
            append_error(errors, run_id, destination, 'traceroute', 'nonzero_exit_code', f"Exit code: {return_code}; stderr: {traceroute_error}")

        hops = parse_traceroute_output(traceroute_output)

        # check if the destination IP address is reached using the helper functions
        traced_ip = extract_traceroute_destination_ip(traceroute_output)
            
        if traced_ip is None:
            append_error(errors, run_id, destination, 'traceroute', 'header_parse_failed', "Could not verify the traceroute destination IP address")

        elif traced_ip != resolved_ip:
            append_error(errors, run_id, destination, 'traceroute', 'destination_mismatch', f"Traceroute destination IP address mismatch: {traced_ip} != {resolved_ip}")
            print(f"WARNING: Traceroute destination IP address mismatch: {traced_ip} != {resolved_ip}")

        # if the destination IP address is resolved, check if it is reached by the traceroute
        if traced_ip == resolved_ip:
            destination_reached = check_traceroute_destination_reached(hops, resolved_ip)
        else:
            destination_reached = None

        if not hops:
            append_error(errors, run_id, destination, 'traceroute', 'no_hops_recorded', "No hops recorded")

        for hop in hops:
            hop['run_id'] = run_id
            hop['timestamp'] = tracert_timestamp
            hop['operating_system'] = operating_system
            hop['destination'] = destination
            hop['destination_ip'] = resolved_ip
            hop['destination_reached'] = destination_reached
            hop['command_status'] = traceroute_status
            traceroute_results.append(hop)

        print(f"\nTotal hops recorded: {len(hops)}")

        # ============================================================
        # End of Traceroute test
        # ============================================================

    os.makedirs('results', exist_ok=True) # create results directory if it doesn't exist
    save_ping_results(ping_results, 'results/ping_results.csv')
    save_traceroute_results(traceroute_results, 'results/traceroute_results.csv')
    record_error(errors, 'results/errors.csv')
    print(f"Results saved to 'results/ping_results.csv' and 'results/traceroute_results.csv'")
    print(f"Errors recorded to 'results/errors.csv'")
    print(f"Total errors: {len(errors)}")

if __name__ == "__main__":
    main()