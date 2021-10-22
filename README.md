
A small Python script that parses the output of kafka-consumer-groups.sh and submits metrics to Datadog

# Requirements

Requires Linux-based operating system with Python 3+ (to run the included Python script) and Java 8+ (to run `kafka-consumer-groups.sh` which is part of the [Kafka distribution](https://kafka.apache.org/downloads), not included in this repo).

# Setting up the config.json file

Copy `example.config.json`into a new file called `config.json` in the same directory. This file would contain all of the configurations needed in order to set up this script. Edit the configurations inside the new `config.json` file. Here the list of configs and their purpose:

## Important fields
- "api_site_url": this is the site of your Datadog account. If your account is in the EU site, then you should use "https://api.datadoghq.eu", otherwise the metrics will not show up in your account. Use "https://api.datadoghq.com" for US sites.
- "dd_api_key": the Datadog API key
- "kafka_consumer_group_sh_path": Full path to the kafka-consumer-groups.sh file. This should be located under the `bin/` directory of the [Kafka distribution](https://kafka.apache.org/downloads) once extracted. For example, it should look something like: `/home/myuser/kafka_2.13-2.7.1/bin`
- "kafka_consumer_group_config_path": Full path to the config file that is use when running kafka-consumer-groups.sh. This config file contains configs such as client SSL connection configs.
- "kafka_consumer_group_bootstrap_server": You can get the bootstrap server address from the service Connection Information panel in your Kafka service in the Aiven web console by copying the "Service URI". It should look something like "my-kafka.aivencloud.com:12345".

For more information on how to setup and run `kafka-consumer-groups.sh`, please refer to https://help.aiven.io/en/articles/2661525-viewing-and-resetting-consumer-group-offsets.

## Other fields
- "host": this is a tag called "host" that will be tagged along with the metric points. So for example, the metrics will be tagged with "host:kafka-prd".
- "aiven_project_name": this is a tag called "aiven-project" that will be tagged along with the metric points. So for example, the metrics will be tagged with "aiven-project:test-project".
- "aiven_service_name": this is a tag called "aiven-service" that will be tagged along with the metric points. So for example, the metrics will be tagged with "aiven-service:test-service".
- "broker_offset_metric_name": this is the name of the metric/series of broker offset metric points. In the metrics explorer, it would appear under the "Graph" dropdown.
- "consumer_offset_metric_name": this is the name of the metric/series of consumer offset metric points.
- "consumer_lag_metric_name": this is the name of the metric/series of consumer lag metric points.
- "max_metrics_per_request": how many metric points are sent in 1 HTTP POST request to Datadog's API


# Running the script

Once `config.json` has been configured, simply run the python script:

`python custom_metrics_sender.py`


# Issues when sending out the request

During testing, I saw that sending 450 metric points in 1 request equated to ~100000 bytes. Datadog's max payload size is 3.2 megabytes (3200000 bytes). So we can send abit over 13k metric "points"*. But let's keep a safer value of 7000 metric points. If we exceed the content length, Datadog API will return something like this:

`{"status":"error","code":413,"errors":["Payload too large"]...`

Also, we may also get a timeout response when sending the metrics:

`Request timeout. Please retry or make a smaller request`

This also means that we may be sending a request with very large payload.

So in both of these cases, consider lowering 'max_metrics_per_request' in config.json further.

Right now, based on some testing, 'max_metrics_per_request' is set to a "sweet spot" of 7000 metrics sent per request.

*point here mean a "tuple" of group, topic, partition, and offset or lag value - in other words, each line from the output of kafka-consumer-groups.sh are unique with regards to (group, topic, partition).


# Limitations

This is a rudimentary script with no tests or data sanitation. It makes the assumption that the output of `kafka-consumer-groups.sh` is in a specific format, so it will fail if `kafka-consumer-groups.sh`'s output ever changes.

An attempt was made to submit the metrics asynchronously using aiohttp and asyncio but Datadog seems to have some kind of rate-limit preventing this, so for now the requests are sent synchronously (one by one) using the `requests` module.


# Links

- https://docs.datadoghq.com/getting_started/site/
- https://docs.datadoghq.com/api/latest/metrics/
- https://github.com/DataDog/integrations-core/tree/00faec2961baf0122c455cecce5abfe5435eaf53/kafka_consumer
