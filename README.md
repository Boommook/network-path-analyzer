# Network Path Analyzer

A Python-based network measurement tool developed for WPI's CS513 Computer Networks course. The analyzer uses ping and traceroute to collect network performance metrics and routing info across multiple destinations, supporting both Windows and Linux.

## Features

- Collects packet loss, min/avg/max RTT, and RTT standard deviation using ping
- Records traceroute hops, router IP addresses, and per-probe RTT measurements
- Detects whether destinations are successfully reached

## Project Structure

network-path-analyzer/
├── analyzer.py # Main program and CSV output
├── ping.py # Ping execution and parsing
├── traceroute.py # Traceroute execution and parsing
├── destinations.txt # Hostnames/IP addresses to test
└── results/ # Generated measurement CSV files

## Requirements

Python 3 (standard library only)
Windows: ping and tracert (built in)
Linux: ping and traceroute

## Usage

Add one destination per line to tbe destinations.txt file

Run the analyzer:
Windows: `python analyzer.py`
Linux/WSL: `python3 analyzer.py`

## Output

The program generates three files in the results/ directory:

- ping_results.csv — Packet loss and RTT statistics.
- traceroute_results.csv — Per-hop IP addresses, probe RTTs, and response statuses.
- errors.csv — DNS, execution, timeout, and parsing errors.
