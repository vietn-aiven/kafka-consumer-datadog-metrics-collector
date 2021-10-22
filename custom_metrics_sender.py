import subprocess
import requests
import time
import json
import argparse
import os

parser = argparse.ArgumentParser()
parser.add_argument(
    "--config-path",
    type=str,
    default="config.json",
    help="The path to the config file. Default config.json")


def run_kafka_consumer_group_tool(config):
    script_path = os.path.join(config["kafka_consumer_group_sh_path"], "kafka-consumer-groups.sh")
    print(script_path)
    return subprocess.check_output([
        script_path,
        "--describe",
        "--all-groups",
        "--bootstrap-server",
        config["kafka_consumer_group_bootstrap_server"],
        "--command-config",
        config["kafka_consumer_group_config_path"],
    ])


def parse_kafka_consumer_group_output(config, output):
    """
    Receives the output of the kafka-consumer-group.sh command and creates a list
    of metric points ready to be submitted to Datadog

    Args:
    - config: a dictionary holding configuration stored in config.json
    - output: a string output from run_kafka_consumer_group_tool()

    Returns:
    - metrics: list of metric objects (ready to be received by Datadog - see https://docs.datadoghq.com/api/latest/metrics/)
    """
    metrics = list()
    project_name = config["aiven_project_name"]
    service_name = config["aiven_service_name"]
    now = int(time.time())
    lines = output.split(b"\n")

    for line in lines:
        # Skip empty line
        line = line.strip()
        if line:
            """
            Here is what the tuple positions (columns) denote:
            - 0: group name
            - 1: topic
            - 2: partition
            - 3: current group offset
            - 4: broker offset
            - 5: consumer lag
            - 6: consumer-id # unused
            - 7: host # unused
            - 8: client-id # unused
            """
            line = line.decode("utf-8")
            try:
                # We skip consumer-id, host, and client-id
                group, topic, partition, consumer_offset, broker_offset, consumer_lag, _ = line.split(None, 6)
                # Skip the headers. Also we know this is the beginning of a new group
                # We determine if it's a header if the PARTITION column is "PARTITION" because partitions are integers :)
                if partition == "PARTITION":
                    # Let's continue on to the next line
                    continue
                else:
                    # print (group, topic, partition, consumer_offset, broker_offset, consumer_lag, consumer_id, host, client_id)
                    broker_offset_metric = {
                        "host": config["host"],
                        "metric": config["broker_offset_metric_name"],
                        "points": [
                            [
                                f"{now}",
                                broker_offset
                            ]
                        ],
                        "type": "gauge",
                        "tags": [
                            f"aiven-service:{service_name}",
                            f"aiven-project:{project_name}",
                            f"topic:{topic}",
                            f"partition:{partition}",
                            f"consumer_group:{group}",
                        ]
                    }
                    metrics.append(broker_offset_metric)

                    consumer_offset_metric = {
                        "host": config["host"],
                        "metric": config["consumer_offset_metric_name"],
                        "points": [
                            [
                                f"{now}",
                                consumer_offset
                            ]
                        ],
                        "type": "gauge",
                        "tags": [
                            f"aiven-service:{service_name}",
                            f"aiven-project:{project_name}",
                            f"topic:{topic}",
                            f"partition:{partition}",
                            f"consumer_group:{group}",
                        ]
                    }
                    metrics.append(consumer_offset_metric)

                    consumer_lag_metric = {
                        "host": config["host"],
                        "metric": config["consumer_lag_metric_name"],
                        "points": [
                            [
                                f"{now}",
                                consumer_lag
                            ]
                        ],
                        "type": "gauge",
                        "tags": [
                            f"aiven-service:{service_name}",
                            f"aiven-project:{project_name}",
                            f"topic:{topic}",
                            f"partition:{partition}",
                            f"consumer_group:{group}",
                        ]
                    }
                    metrics.append(consumer_lag_metric)

            except ValueError:
                # TODO: This shouldn't happen because AFAIK topic names and group names/ids do not contain spaces but not 100% sure
                # So might get a "too many values to unpack". Do nothing ATM
                print ("ValueError: There was an error parsing the line as there were probably too many values to unpack (possibly spaces in group name):")
                print (line)

    #print (json.dumps(metrics, indent=4, sort_keys=True))
    print ("Finished processing kafka-consumer-group.sh output")
    print (f"A total of {len(metrics)} metric points to send to Datadog.")

    return metrics


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def send_metrics(config, metrics):
    for count, chunk in enumerate(chunks(metrics, config["max_metrics_per_request"])):
        print (f"Sending request number {count + 1} to Datadog API. Number of metric points to send: {len(chunk)}")
        payload = {
            "series": chunk
        }

        submit_metrics_to_datadog(config, payload)


def submit_metrics_to_datadog(config, payload):
    headers = {
        "Content-Type": "application/json",
        "DD-API-KEY": config["dd_api_key"],
    }
    site = config["api_site_url"]
    req = requests.Request('POST', f"{site}/api/v1/series", headers=headers, json=payload)
    prepared = req.prepare()
    pretty_print_POST(prepared)

    response = requests.post(f"{site}/api/v1/series", headers=headers, json=payload)
    print (response.text)
    if "Payload too large" in response.text:
        print ("\nPayload is too large. Consider lowering 'max_metrics_per_request' in config.json\n")
    if "Request timeout" in response.text:
        print ("\nRequest timed out. Consider lowering 'max_metrics_per_request' in config.json\n")


def pretty_print_POST(req):
    """
    Source: https://stackoverflow.com/a/23816211
    """
    print('{}\n{}\r\n{}\r\n'.format(
        '-----------START-----------',
        req.method + ' ' + req.url,
        '\r\n'.join('{}: {}'.format(k, v) for k, v in req.headers.items()),
    ))


def load_json_config(config_path):
    # Opening JSON file
    with open(config_path) as json_file:
        return json.load(json_file)


if __name__ == "__main__":
    args = parser.parse_args()
    config = load_json_config(args.config_path)

    output = run_kafka_consumer_group_tool(config)
    metrics = parse_kafka_consumer_group_output(config, output)
    send_metrics(config, metrics)
