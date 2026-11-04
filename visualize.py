import matplotlib.pyplot as plt
from datetime import datetime
from pathlib import Path

from analysis import load_ping_results


# ------------------------------------------------------------
# Function: plot_rtt_single_destination
#
# Purpose: Plot a scatter graph of average ping RTT over time
# for a given destination with separate lines for each OS.
#
# Parameters: results - a list of dictionaries with the ping measurements.
#             destination - the destination to plot the RTT over time for.
#
# Returns: None
#
# Other outputs: a scatter graph of the average ping RTT over time for the destination.
# ------------------------------------------------------------
def plot_rtt_single_destination(results, destination):
    # filter results for the destination
    measurements = [row for row in results if row['destination'] == destination and row['avg_rtt'] is not None]

    if not measurements:
        print(f"No RTT data found for destination: {destination}")
        return

    # separate measurements by OS
    grouped_os_measurements = {}

    for row in measurements:
        os_name = row['operating_system']
        grouped_os_measurements.setdefault(os_name, []).append(row)

    # create a figure and axis for the plot
    fig, ax = plt.subplots(figsize=(12, 6))

    # plot a separate scatter for each OS
    for os_name, rows in sorted(grouped_os_measurements.items()):
        # sort the rows by timestamp
        rows.sort(key=lambda x: x['timestamp'])

        # extract timestamps
        timestamps = [datetime.fromisoformat(row['timestamp']) for row in rows]

        # extract RTTs
        rtts = [row['avg_rtt'] for row in rows]

        ax.scatter(timestamps, rtts, label=os_name, s=35, alpha=0.8)
    
    ax.set_title(f"Average Ping RTT Over Time for {destination}")
    ax.set_xlabel("Timestamp")
    ax.set_ylabel("Average Ping RTT (ms)")
    ax.legend()
    ax.grid(True, alpha = 0.5)

    output_dir = Path(__file__).resolve().parent / 'figures'
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / f"rtt_over_time_{destination}.png"
    fig.savefig(output_file, dpi=150)

    print(f"Saved plot to: {output_file}")

    plt.show()
    plt.close(fig)


def plot_rtt_all_destinations(results, destinations, os_name):
    fig, ax = plt.subplots(figsize=(12, 6))

    for destination in destinations:
        measurements = [
            row for row in results 
            if row['destination'] == destination 
            and row['operating_system'] == os_name 
            and row['avg_rtt'] is not None]

        if not measurements:
            print(f"No RTT data found for destination: {destination} and OS: {os_name}")
            continue
        
        # sort the measurements by timestamp
        measurements.sort(key=lambda x: x['timestamp'])
        
        timestamps = [datetime.fromisoformat(row['timestamp']) for row in measurements]

        rtts = [row['avg_rtt'] for row in measurements]

        ax.scatter(timestamps, rtts, label=destination, s=35, alpha=0.8)

    ax.set_title(f"Average Ping RTT Over Time for {os_name}")

    ax.set_xlabel("Timestamp")
    ax.set_ylabel("Average Ping RTT (ms)")

    ax.legend()
    ax.grid(True, alpha = 0.5)

    output_dir = Path(__file__).resolve().parent / 'figures'
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / f"rtt_over_time_all_destinations_{os_name}.png"
    fig.savefig(output_file, dpi=150)

    print(f"Saved plot to: {output_file}")

    plt.show()
    plt.close(fig)

def main():
    filename = Path(__file__).resolve().parent / 'results' / 'ping_results.csv'

    results = load_ping_results(filename)

    plot_rtt_single_destination(results, 'google.com')

    destinations = [
        'google.com',
        'cloudflare.com',
        '8.8.8.8',
        '1.1.1.1',
        '9.9.9.9'
    ]

    plot_rtt_all_destinations(results, destinations, 'windows')
    plot_rtt_all_destinations(results, destinations, 'linux')

if __name__ == "__main__":
    main()