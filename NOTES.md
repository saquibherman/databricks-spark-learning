# Notes: Introduction to Apache Spark

My own notes from the Databricks Academy course *Introduction to Apache Spark* (ASP 1, v3.0.1, ~3.5 h).

## Lessons

| # | Topic |
|---|-------|
| 01 | Required setup: `intro_spark` schema, `source_files` / `output` volumes, customer CSVs, `flights` table |
| 1.1–1.3 | What Spark is, runtime architecture (driver, workers, executors, DAG), exploring it in the Spark UI |
| 2.1–2.3 | DataFrames, lazy evaluation, reading/writing data, inferred vs explicit schemas |
| 3.1 | Distributed systems fundamentals: shared-nothing, partitioning, the shuffle, MapReduce |
| 4.1–4.3 | Basic ETL with the DataFrame API, flight data ETL demo, lab on `samples.bakehouse.sales_transactions` |

## Setup notes

- Compute: classic **DBR 17.3 LTS** cluster *Intro to Apache Spark (&lt;you&gt;)* (dedicated, needed for `sc`
  and the Spark UI in 1.3); other notebooks also run on serverless (env v4).
- Writes to `labuser_<user>.intro_spark` (shared catalog with the Data_Engineering repos).
- Data: `samples.tpch.customer` (exported to CSV by setup), `samples.bakehouse`, synthetic flights.

## Notes

<!-- Add what you learn as you go through each module -->
