# Ascom Gul Signalvej

## Overview

"Gul Signalvej" is a monitoring solution that checks the connection to Systematic's positioning system in relation to Ascom's personal security solution (panic alarms) at AUH (Aarhus University Hospital). The system monitors if positioning data is being updated correctly and within acceptable time frames.

## Problem Statement

The old solution monitored the connection to Systematic's backend by using four specific tags that are physically taped (with gaffa tape) to Ascom hardware. Since these tags don't move, and the check against the backend is based on timestamps being updated within 900 seconds, the solution fails because timestamps are only updated when tags actually move.

The old implementation used:
- Specific MAC addresses via the `MATCH_epc` parameter in the API call
- A check against a tag's timestamp that required physical movement to update

## Solution

The updated algorithm:

1. Changes the API payload to use `MATCH_objectClass` instead of `MATCH_epc` to get data for all alarm tags
2. Processes the large response (1000+ tags) 
3. Checks if any tag has been updated within the specified time threshold (e.g., 900 seconds)
4. Returns success if at least one tag has been updated within the threshold, otherwise returns failure

## Improvements

- No longer dependent on specific, static tags
- More reliable monitoring by checking all available alarm tags
- Returns positional data when successful, including a Google Maps link
- Properly handles timezone information in the API responses
- Better error handling and logging

## Setup and Installation (Offline Environment)

### Step 1: On an online PC

1. Download the source code and put it in a folder
2. Download the Python 3.11.9 installer from [python.org](https://www.python.org/downloads/release/python-3119/) and put it in the folder with the source code
3. Run the following command to download all Python dependencies:
   ```
   py -m pip download -r requirements.txt -d python_packages
   ```

### Step 2: On the offline machine

1. Transfer the Python installer, dependencies, and source code to a folder
2. Install Python 3.11.9
3. Run the following command to install dependencies from the local packages:
   ```
   py -m pip install --no-index --find-links=python_packages -r requirements.txt
   ```
4. Start the test API server (simulates the Systematic Track API):
   ```
   py test-api.py
   ```
5. In a new terminal, start the main API server:
   ```
   py main.py
   ```
6. Navigate to `http://localhost:6060/commands/systematic/900` in a browser to test Gul Signalvej with a 900-second threshold

## Environment Variables

The application requires the following environment variables:

- `HOST`: Identifies the host in log messages
- `TRACK_SERVICES_API_URL`: URL to the Track Services API (defaults to test server at http://localhost:5000/mock if using test-api.py)
- `WATCHDOG_PATH`: Path to the folder where result files are stored (for the `/commands/` endpoint)

## API Endpoints

- `/commands/systematic/<seconds>`: Tests if any tag in the system has been updated within the specified seconds
- `/commands/<command1>/<mac1>/<command2>/<mac2>/<command3>/<mac3>/<command4>/<mac4>`: Legacy endpoint for MAC address specific commands

## Testing

The included `test-api.py` script provides a mock API server that returns test data from `test_payload.xml`. This allows for testing the application without access to the actual Systematic Track API.

When running with the test server:
- The most recent record in the test data is from 2023-01-05, so the check will likely fail with the current date
- To test a successful scenario, you can modify the `recordTime` in `test_payload.xml` to be within your specified threshold of the current time

## Architecture

1. **main.py**: Contains the Flask API server and processing logic
2. **test-api.py**: Mock server for the Systematic Track API
3. **test_payload.xml**: Sample response data for testing
4. **requirements.txt**: Python dependencies

## License

Proprietary. For internal use only.