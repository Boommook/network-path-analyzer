import matplotlib.pyplot as plt
from datetime import datetime
from pathlib import Path
import matplotlib.dates as mdates
import statistics

from analysis import load_ping_results

def plot_latency_boxplot(results, os_name):
    # group avg RTT values by destination
    grouped_results = {}

    for row in results:
        if row['operating_system'] != os_name:
            continue

        if row['avg_rtt'] is None:
            continue

        destination = row['destination']
        # append the RTT to the list of RTT data for the destination, if the destination is not in the dictionary, create a new list
        grouped_results.setdefault(destination, []).append(row['avg_rtt'])

    if not grouped_results:
        print(f"No RTT data found for OS: {os_name}")
        return

    # sort destinations so the plot is consistent
    destinations = sorted(grouped_results.keys())

    # collect RTT lists in the same order
    rtt_data = [grouped_results[destination] for destination in destinations]

    print(rtt_data)

    # create the plot
    fig, ax = plt.subplots(figsize=(12, 6))

    ax.boxplot(rtt_data, tick_labels=destinations, showfliers=True)

    ax.set_title(f"RTT Distribution by Destination ({os_name})")
    ax.set_xlabel("Destination")
    ax.set_ylabel("Average Ping RTT (ms)")
    ax.grid(True, axis='y', alpha=0.3)

    plt.xticks(rotation=45, ha='right')

    output_dir = Path(__file__).resolve().parent / 'figures'
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / f"latency_boxplot_{os_name}.png"

    fig.tight_layout()
    fig.savefig(output_file, dpi=150)

    print(f"Saved plot to: {output_file}")

    plt.show()
    plt.close(fig)

# ------------------------------------------------------------
# Function: plot_rtt_boxplot_by_time
#
# Purpose: Plot the distribution of normalized RTT deviations
# by time of da, with separate boxplots for each operating system.
# The RTT deviations are normalized by the baseline RTT for each destination and operating system pair.
#
# Parameters: results - a list of dictionaries with the ping measurements.
#
# Returns: None
# ------------------------------------------------------------
def plot_rtt_boxplot_by_time(results):
    # filter out measurements with no RTT data
    measurements = [
        row for row in results
        if row['avg_rtt'] is not None
    ]

    if not measurements:
        print("No valid RTT data found.")
        return

    # get the operating systems present in the measurements
    # should just be windows and linux
    operating_systems = sorted(set(
        row['operating_system'] for row in measurements
    ))

    # group RTTs by dest and OS
    baseline_rtts = {}
    for row in measurements:
        key = (row['destination'], row['operating_system'])
        baseline_rtts.setdefault(key, []).append(row['avg_rtt'])

    # calculate the baseline mean RTT for each destination and operating system pair
    # these are used to normalize
    baselines = {
        key: statistics.mean(rtts)
        for key, rtts in baseline_rtts.items()
    }

    # create a dict to store RTT deviations for hr of day, separated by OS
    hourly_deviations = {
        os_name: {hour: [] for hour in range(24)}
        for os_name in operating_systems
    }

    # normalize each avg RTT and group by hour of day and OS
    for row in measurements:
        os_name = row['operating_system']
        timestamp = datetime.fromisoformat(row['timestamp'])
        hour = timestamp.hour

        key = (row['destination'], os_name)
        # subtract the corresponding baselin
        # pos means higher than avg latency for that dest/OS pair
        # neg means lower than avg latency for that dest/OS pair
        deviation = row['avg_rtt'] - baselines[key]

        # add the RTT deviation to the list of deviations for the hour and OS
        hourly_deviations[os_name][hour].append(deviation)

    # get the hours with at least one measurement from either OS
    hours_with_data = [
        hour for hour in range(24)
        if any(hourly_deviations[os_name][hour]
               for os_name in operating_systems)
    ]

    if not hours_with_data:
        print("No hourly RTT data available.")
        return

    # create the plot
    plt.figure(figsize=(14, 6))

    colors = ['steelblue', 'darkorange']

    for i, os_name in enumerate(operating_systems):
        positions = []
        data = []

        for j, hour in enumerate(hours_with_data):
            deviations = hourly_deviations[os_name][hour]

            if not deviations:
                continue

            positions.append(
                j + 1 + (i - (len(operating_systems) - 1) / 2) * 0.35
            )
            data.append(deviations)

        if not data:
            continue

        plt.boxplot(
            data,
            positions=positions,
            widths=0.3,
            patch_artist=True,
            manage_ticks=False,
            boxprops=dict(
                facecolor=colors[i % len(colors)],
                alpha=0.6
            ),
            medianprops=dict(color='black', linewidth=2)
        )

        plt.plot(
            [],
            [],
            color=colors[i % len(colors)],
            linewidth=8,
            alpha=0.6,
            label=os_name
        )

    plt.axhline(
        y=0,
        color='gray',
        linestyle='--',
        linewidth=1
    )

    plt.xticks(
        range(1, len(hours_with_data) + 1),
        [f"{hour:02d}:00" for hour in hours_with_data],
        rotation=45
    )

    plt.xlabel("Time of Day")
    plt.ylabel("RTT Deviation from Baseline (ms)")
    plt.title("RTT Deviation by Time of Day and Operating System")
    plt.grid(axis='y', alpha=0.3)
    plt.legend(title="Operating System")
    plt.tight_layout()

    output_dir = Path("figures")
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / "rtt_deviation_by_time_of_day.png"

    plt.savefig(output_file)
    plt.show()

    print(f"Saved graph to {output_file}")

# ------------------------------------------------------------
# Function: get_plot_times
#
# Purpose: Get the timestamps from the measurements and optionally
# convert them to time of day only.
#
# Parameters: rows - a list of dictionaries with the ping measurements
#             time_only - a boolean indicating if only the time should be returned
#
# Returns: A list of datetime objects
# ------------------------------------------------------------
def get_plot_times(rows, time_only):
    # extract timestamps
    timestamps = [datetime.fromisoformat(row['timestamp']) for row in rows]

    if time_only:
        # use same reference date for all timestamps
        # this way all the measurements overlap on the same day
        ref_date = datetime(2000,1,1).date()

        return [
            # combine the reference date with the time of the timestamp
            datetime.combine(ref_date, timestamp.time()) for timestamp in timestamps
        ]
    # return the timestamps as is
    return timestamps

# ------------------------------------------------------------
# Function: plot_rtt_single_destination
#
# Purpose: Plot a scatter graph of average ping RTT over time
# for a given destination with separate lines for each OS.
#
# Parameters: results - a list of dictionaries with the ping measurements.
#             destination - the destination to plot the RTT over time for.
#             time_only - a boolean indicating if only the time should be plotted
#
# Returns: None
#
# Other outputs: a scatter graph of the average ping RTT over time for the destination.
# ------------------------------------------------------------
def plot_rtt_single_destination(results, destination, time_only=False):
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
        timestamps = get_plot_times(rows, time_only)

        # extract RTTs
        rtts = [row['avg_rtt'] for row in rows]

        ax.scatter(timestamps, rtts, label=os_name, s=35, alpha=0.8)

    # configure the title and x-axis based on the time_only parameter
    if time_only:
        ax.set_title(f"Average Ping RTT Over Time of Day for {destination}")
        ax.set_xlabel("Time of Day")

        # format the x-axis as a 24-hr clock
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.set_xlim(datetime(2000,1,1), datetime(2000,1,2))
    else:
        ax.set_title(f"Average Ping RTT Over Time for {destination}")
        ax.set_xlabel("Timestamp")

    ax.set_ylabel("Average Ping RTT (ms)")
    ax.legend()
    ax.grid(True, alpha = 0.5)

    output_dir = Path(__file__).resolve().parent / 'figures'
    output_dir.mkdir(exist_ok=True)

    time_mode = "time_of_day" if time_only else "timestamp"
    output_file = output_dir / f"rtt_over_time_{destination}_{time_mode}.png"
    fig.savefig(output_file, dpi=150)

    print(f"Saved plot to: {output_file}")

    plt.show()
    plt.close(fig)


def plot_rtt_all_destinations(results, destinations, os_name, time_only=False):
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
        
        timestamps = get_plot_times(measurements, time_only)

        rtts = [row['avg_rtt'] for row in measurements]

        ax.scatter(timestamps, rtts, label=destination, s=35, alpha=0.8)

    if time_only:
        ax.set_title(f"Average Ping RTT Over Time of Day for {os_name}")
        ax.set_xlabel("Time of Day")

        # format the x-axis as a 24-hr clock
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.set_xlim(datetime(2000,1,1), datetime(2000,1,2))
    else:
        ax.set_title(f"Average Ping RTT Over Time for {os_name}")
        ax.set_xlabel("Timestamp")

    ax.set_xlabel("Timestamp")
    ax.set_ylabel("Average Ping RTT (ms)")

    ax.legend()
    ax.grid(True, alpha = 0.5)

    output_dir = Path(__file__).resolve().parent / 'figures'
    output_dir.mkdir(exist_ok=True)

    time_mode = "time_of_day" if time_only else "timestamp"
    output_file = output_dir / f"rtt_over_time_all_destinations_{os_name}_{time_mode}.png"
    fig.savefig(output_file, dpi=150)

    print(f"Saved plot to: {output_file}")

    plt.show()
    plt.close(fig)

def main():
    filename = Path(__file__).resolve().parent / 'results' / 'ping_results.csv'

    results = load_ping_results(filename)

    #plot_latency_boxplot(results, 'windows')
    #plot_latency_boxplot(results, 'linux')
    # get the unique destinations from the results
    destinations = sorted(set([row['destination'] for row in results]))
    #plot_rtt_all_destinations(results, destinations, 'windows', time_only=True)
    #plot_rtt_all_destinations(results, destinations, 'linux', time_only=True)
    plot_rtt_boxplot_by_time(results)

if __name__ == "__main__":
    main()