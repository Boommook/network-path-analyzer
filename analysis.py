import csv
import math
import statistics
from pathlib import Path
from datetime import datetime


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

    return results


# ------------------------------------------------------------
# Function: analyze_ping_results
#
# Purpose: turn the list of ping measurements into
# a dictionary of analysis results for each destination with useful statistics.
#
# Parameters: results - a list of dictionaries with the ping measurements.
#
# Returns: A dictionary with the analysis results for each destination.
# ------------------------------------------------------------
def analyze_ping_results(results):
    grouped_results = {}

    for row in results:
        destination = row['destination']
        # append the row to the list of results for the destination
        # if the destination is not in the dictionary, create a new list
        # then append the row to the list
        grouped_results.setdefault(destination, []).append(row)
    
    analysis = {}

    for destination, rows in grouped_results.items():
        # gather all rtts for the destination
        rtts = [row['avg_rtt'] for row in rows if row['avg_rtt'] is not None]

        # gather all packet losses for the destination
        packet_losses = [row['packet_loss'] for row in rows if row['packet_loss'] is not None]

        # compile the analysis for the destination
        analysis[destination] = {
            'measurement_count': len(rows),
            'valid_rtt_count': len(rtts),
            'mean_rtt': statistics.mean(rtts) if rtts else None,
            'median_rtt': statistics.median(rtts) if rtts else None,
            'min_rtt': min(rtts) if rtts else None,
            'max_rtt': max(rtts) if rtts else None,
            'std_dev_rtt': statistics.stdev(rtts) if len(rtts) >= 2 else None,
            'mean_packet_loss': statistics.mean(packet_losses) if packet_losses else None,
            'max_packet_loss': max(packet_losses) if packet_losses else None,
            'min_packet_loss': min(packet_losses) if packet_losses else None,
            'runs_with_packet_loss': sum(loss > 0 for loss in packet_losses),
            'packet_loss_run_percentage': (100 * sum(loss > 0 for loss in packet_losses) / len(packet_losses) if packet_losses else None),
        }
    return analysis


def analyze_ping_by_hour(results):
    grouped_results = {}

    for row in results:
        # extract the hour from the timestamp
        timestamp = datetime.fromisoformat(row['timestamp'])
        hour = timestamp.hour

        # group by destination, OS, and hour
        key = (row['destination'], row['operating_system'], hour)

        # append the row to the list of results for the key
        grouped_results.setdefault(key, []).append(row)

    analysis = {}

    for key, rows in grouped_results.items():
        rtts = [row['avg_rtt'] for row in rows if row['avg_rtt'] is not None]

        packet_losses = [row['packet_loss'] for row in rows if row['packet_loss'] is not None]

        analysis[key] = {
            'measurement_count': len(rows),
            'mean_rtt': statistics.mean(rtts) if rtts else None,
            'median_rtt': statistics.median(rtts) if rtts else None,
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
    
    for destination, data in analysis.items():
        print(f"\nDestination: {destination}")

        for metric, value in data.items():
            # format float values to 3 decimal places
            if isinstance(value, float):
                print(f" {metric}: {value:.3f}")
            else:
                print(f" {metric}: {value}")

    hourly_analysis = analyze_ping_by_hour(results)

    print("\nHourly Analysis:")

    for (destination, os, hour), data in hourly_analysis.items():
        mean_rtt = data['mean_rtt']
        mean_packet_loss = data['mean_packet_loss']

        rtt_formatted = f"{mean_rtt:.3f}" if mean_rtt is not None else "N/A"
        packet_loss_formatted = f"{mean_packet_loss:.2f}%" if mean_packet_loss is not None else "N/A"

        print(f"\nDestination: {destination}, OS: {os}, Hour: {hour:02d}")
        print(f"Runs: {data['measurement_count']}")
        print(f"Mean RTT: {rtt_formatted}")
        print(f"Mean Packet Loss: {packet_loss_formatted}")


if __name__ == "__main__":
    main()