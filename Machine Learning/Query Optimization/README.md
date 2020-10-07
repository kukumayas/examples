# Query Optimization

Tune query parameters using search templates.

## Get started

Use the `Makefile` for all setup, building, testing, etc.

```bash
# install project dependencies (from requirements.txt)
make init

# cleanup environment
make clean

# run tests
make test

# run Jupyter Lab (notebooks)
make jupyter
```

## Demo

All commands can be used with `--help` to explore the various optional arguments such as number of processes to use (for parallelizable tasks), URL for Elasticsearch, etc.

### Start Elasticsearch

Start an Elasticsearch instance locally or use a Cloud instance. For this demo, we recommend allocating at least 8GB of memory to the Elasticsearch JVM and having at least 16 GB total available on the host.

```bash
ES_JAVA_OPTS="-Xmx8g -Xms8g" ./bin/elasticsearch
```

### Data

We use [MSMARCO](http://www.msmarco.org) as a large-scale, public benchmark. Download the dataset and make it available in `data/msmarco-document`.

Convert corpus into indexable documents (~5 mins):

```bash
bin/convert-msmarco-document-corpus \
  data/msmarco/document/msmarco-docs.tsv \
  data/msmarco-document-index-actions.jsonl
```

Bulk index documents (~30 mins):

```bash
bin/bulk-index \
  --index msmarco-document \
  --config config/msmarco-document-index.json \
  data/msmarco-document-index-actions.jsonl
```

For experimentation and the final optimization process, sample the query training dataset into smaller datasets:

```bash
bin/split-and-sample \
  --input data/msmarco/document/msmarco-doctrain-queries.tsv \
  --output \
    data/msmarco-document-sampled-queries.10.tsv,10 \
    data/msmarco-document-sampled-queries.100.tsv,100 \
    data/msmarco-document-sampled-queries.1000.tsv,1000 \
    data/msmarco-document-sampled-queries.10000.tsv,10000
```

### Run evaluation

Using some baseline/default parameter values, run an evaluation. This uses the `dev` dataset, which contains about 3,200 queries.

```bash
bin/eval \
  --index msmarco-document \
  --metric config/metric-mrr.json \
  --templates config/msmarco-document-templates.json \
  --queries data/msmarco/document/msmarco-docdev-queries.tsv \
  --qrels data/msmarco/document/msmarco-docdev-qrels.tsv \
  --params config/params.baseline.json
```

### Run query optimization

Build a configuration file based on the kind of optimization you want to do. This uses one of the sampled `train` datasets, which contains just 100 queries to experiment quickly with.

```bash
bin/optimize-query \
  --index msmarco-document \
  --metric config/metric-mrr.json \
  --templates config/msmarco-document-templates.json \
  --queries data/msmarco-document-sampled-queries.100.tsv \
  --qrels data/msmarco/document/msmarco-doctrain-qrels.tsv \
  --config config/optimize-query.json
```

See the accompanying Jupyter notebooks for more details and a full example.
