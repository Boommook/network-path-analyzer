import csv
import math
import statistics
from pathlib import Path
from datetime import datetime

def traceroute_rtt_by_hop(filename):
    grouped_results = {}

    with open(filename, 'r', newline='') as file:
        reader = csv.DictReader(file)

        for row in reader:
            # ignore runs with no RTT data
            if not row['avg_rtt_ms']:
                continue
            
            try:
                hop_number = int(row['hop_number'])
                avg_rtt = float(row['avg_rtt_ms'])
            except (ValueError, TypeError):
                continue
            
            key = (row['destination'], row['operating_system'], hop_number)
            grouped_results.setdefault(key, []).append(avg_rtt)
    
    return grouped_results


# ------------------------------------------------------------
# Function: traceroute_hop_count_reaching_destination
#
# Purpose: 
# Checks if traceroute reached each destination for each OS and creates a dictionary
# of the minimum hop count that reached the destination for each destination & OS pair.
#
# Parameters: filename - the name of the file to load (results/traceroute_results.csv)
#
# Returns: A dictionary with the minimum hop count that reached the destination for each destination & OS pair.
# ------------------------------------------------------------
def traceroute_hop_count_reaching_destination(filename):
    grouped_runs = {}

    with open(filename, 'r', newline='') as file:
        reader = csv.DictReader(file)

        for row in reader:
            # key individual traceroute runs
            key = (
                row['destination'],
                row['run_id'],
                row['operating_system']
            )

            grouped_runs.setdefault(key, []).append(row)
    
    hop_counts = {}

    for key, rows in grouped_runs.items():
        destination, run_id, os = key

        # only count for traceroute runs that reached their destination
        # so if no rows have the destination_reached flag set to true, skip the run
        if not any(row['destination_reached'].strip().lower() == 'true' for row in rows):
            continue

        # get the intended destination ip
        destination_ip = rows[0]['destination_ip']

        # get the hop numbers where one of the probes hit the destination ip
        reached_hops = [int(row['hop_number']) for row in rows if destination_ip in [row[f'probe_{i}_ip'] for i in range(1, 4)]]

        # skip any runs that didn't reach the destination ip
        if not reached_hops:
            continue

        # then get the minimum hop count that reached the destination
        min_hop_count = min(reached_hops)

        # append the hop count to the list, keyed by destination & OS
        new_key = (destination, os)
        hop_counts.setdefault(new_key, []).append(min_hop_count)
    
    return hop_counts

# ------------------------------------------------------------
# Function: load_ping_results
#
# Purpose: load ping measurements from a file and convert
# them numeric fields into values that can be used for analysis.
#
# Parameters: filename - the name of the file to load (results/ping_results.csv)
#
# Returns: A list of dictionaries with the ping measurements.
# ------------------------------------------------------------
def load_ping_results(filename):
    results = []

    numeric_fields = [
        'packet_loss',
        'min_rtt',
        'max_rtt',
        'avg_rtt',
        'stddev_rtt',
    ]

    with open(filename, 'r', newline='') as file:
        reader = csv.DictReader(file)

        for row in reader:
            # convert numeric values to floats and preserve missing data
            for field in numeric_fields:
                value = row[field]

                # preserve missing data
                if value is None or value == '':
                    row[field] = None
                else:
                    try:
                        number = float(value)
                        row[field] = number if math.isfinite(number) else None
                    # set to None if conversion fails
                    except ValueError:
                        row[field] = None

            results.append(row)

    # ex. results:
    # {
    #   "timestamp": "2026-11-05 21:00:00",
    #   "operating_system": "windows",
    #   "destination": "google.com",
    #   "packet_loss": 0.0,
    #   "min_rtt": 34.0,
    #   "max_rtt": 42.0,
    #   "avg_rtt": 38.5,
    #   "stddev_rtt": 2.8
    # },
    #
    # each row is a ping run for a destination/OS pair
    return results


# ------------------------------------------------------------
# Function: analyze_ping_results
#
# Purpose: turn the list of ping measurements into
# a dictionary of analysis results for each destination and operating system with useful statistics:
# 
# mean_run_rtt, median_run_rtt, and std_dev_run_mean_rtt 
# summarize the average RTT of each ping run. 
# 
# min_rtt and max_rtt are the minimum and maximum individual
# packet RTTs across the collected runs.
#
# Parameters: results - a list of dictionaries with the ping measurements.
#
# Returns: A dictionary with the analysis results for each destination and operating system.
# ------------------------------------------------------------
def analyze_ping_results(results):
    grouped_results = {}

    for row in results:
        destination = row['destination']
        operating_system = row['operating_system']
        # append the row to the list of results for the destination
        # if the destination/OS pair is not in the dictionary, create a new list
        # then append the row to the list
        grouped_results.setdefault((destination, operating_system), []).append(row)
    
    analysis = {}

    for key, rows in grouped_results.items():
        # gather the run-level average RTTs (one avg_rtt per ping run)
        run_mean_rtts = [row['avg_rtt'] for row in rows if row['avg_rtt'] is not None]
        # each run's minimum and maximum individual packet RTTs
        # summary min_rtt and max_rtt are the min and max of these values
        min_rtts = [row['min_rtt'] for row in rows if row['min_rtt'] is not None]
        max_rtts = [row['max_rtt'] for row in rows if row['max_rtt'] is not None]

        # gather all packet losses for the destination/OS pair
        packet_losses = [row['packet_loss'] for row in rows if row['packet_loss'] is not None]

        # compile the analysis for the destination/OS pair
        analysis[key] = {
            'measurement_count': len(rows),
            'valid_run_count': len(run_mean_rtts),
            'mean_run_rtt': statistics.mean(run_mean_rtts) if run_mean_rtts else None,
            'median_run_rtt': statistics.median(run_mean_rtts) if run_mean_rtts else None,
            'min_rtt': min(min_rtts) if min_rtts else None,
            'max_rtt': max(max_rtts) if max_rtts else None,
            'std_dev_run_mean_rtt': statistics.stdev(run_mean_rtts) if len(run_mean_rtts) >= 2 else None,
            'mean_packet_loss': statistics.mean(packet_losses) if packet_losses else None,
            'max_packet_loss': max(packet_losses) if packet_losses else None,
            'min_packet_loss': min(packet_losses) if packet_losses else None,
            'runs_with_packet_loss': sum(loss > 0 for loss in packet_losses),
            'packet_loss_run_percentage': (100 * sum(loss > 0 for loss in packet_losses) / len(packet_losses) if packet_losses else None),
        }
    return analysis


# ------------------------------------------------------------
# Function: analyze_ping_by_hour
#
# Purpose: analyze the ping results by hour using the loaded ping results.
#
# Parameters: results - a list of dictionaries with the individual ping measurements.
#
# Returns: A dictionary with the analysis results (with basic statistics) for each destination and operating system by hour.
# ------------------------------------------------------------
def analyze_ping_by_hour(results):
    grouped_results = {}

    for row in results:
        # extract the hour from the timestamp
        timestamp = datetime.fromisoformat(row['timestamp'])
        hour = timestamp.hour

        destination = row['destination']
        operating_system = row['operating_system']

        # group by destination, OS, and hour
        key = (destination, operating_system, hour)

        # append the row to the list of results for the key
        grouped_results.setdefault(key, []).append(row)

    analysis = {}

    # now iterate over the grouped results and compile the analysis for each (destination, OS, and hour) trio
    for key, rows in grouped_results.items():
        # run-level average RTTs for this destination, OS, and hour
        run_mean_rtts = [row['avg_rtt'] for row in rows if row['avg_rtt'] is not None]

        packet_losses = [row['packet_loss'] for row in rows if row['packet_loss'] is not None]

        analysis[key] = {
            'measurement_count': len(rows),
            'mean_run_rtt': statistics.mean(run_mean_rtts) if run_mean_rtts else None,
            'median_run_rtt': statistics.median(run_mean_rtts) if run_mean_rtts else None,
            'mean_packet_loss': statistics.mean(packet_losses) if packet_losses else None
        }
    return analysis

# ------------------------------------------------------------
# Function: main
#
# Purpose: load the ping results, analyze them, and print the results.
#
# Parameters: None
#
# Other inputs: the filename of the ping results to analyze.
#
# Returns: None
# ------------------------------------------------------------
def main():
    filename = Path(__file__).resolve().parent / 'results' / 'ping_results.csv'

    results = load_ping_results(filename)
    analysis = analyze_ping_results(results)

    # I wanted to clarify the distinction between run-level average RTTs and individual packet RTTs
    # sO I added these labels.
    metric_labels = {
        'mean_run_rtt': 'mean of run-level average RTTs',
        'median_run_rtt': 'median of run-level average RTTs',
        'std_dev_run_mean_rtt': 'std dev of run-level average RTTs',
        'min_rtt': 'minimum individual packet RTT',
        'max_rtt': 'maximum individual packet RTT',
    }

    for destination, data in analysis.items():
        print(f"\nDestination: {destination}")

        for metric, value in data.items():
            label = metric_labels.get(metric, metric)
            # format float values to 3 decimal places
            if isinstance(value, float):
                print(f" {label}: {value:.3f}")
            else:
                print(f" {label}: {value}")

    hourly_analysis = analyze_ping_by_hour(results)

    print("\nHourly Analysis:")

    for (destination, os, hour), data in hourly_analysis.items():
        mean_run_rtt = data['mean_run_rtt']
        mean_packet_loss = data['mean_packet_loss']

        rtt_formatted = f"{mean_run_rtt:.3f}" if mean_run_rtt is not None else "N/A"
        packet_loss_formatted = f"{mean_packet_loss:.2f}%" if mean_packet_loss is not None else "N/A"

        print(f"\nDestination: {destination}, OS: {os}, Hour: {hour:02d}")
        print(f"Runs: {data['measurement_count']}")
        print(f"Mean of Run-Level Average RTTs: {rtt_formatted}")
        print(f"Mean Packet Loss: {packet_loss_formatted}")


if __name__ == "__main__":
    main()