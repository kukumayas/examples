# Query Optimization

In the following example code and notebooks we present a principled, data-driven approach to tuning queries based on a search relevance metric. We use the [Rank Evaluation API](https://www.elastic.co/guide/en/elasticsearch/reference/7.10/search-rank-eval.html) and [search templates](https://www.elastic.co/guide/en/elasticsearch/reference/7.10/search-template.html) to build a black-box optimization function and parameter space over which to optimize. This relies on the [skopt](https://scikit-optimize.github.io/) library for Bayesian optimization, which is one of the techniques used. All examples use the [MS MARCO](https://msmarco.org/) Document ranking datasets and metric, however all scripts and notebooks can easily be run with your own data and metric of choice. See the [Rank Evaluation API](https://www.elastic.co/guide/en/elasticsearch/reference/7.10/search-rank-eval.html) for a description of [supported metrics](https://www.elastic.co/guide/en/elasticsearch/reference/7.10/search-rank-eval.html#_available_evaluation_metrics).

In the context of the MS MARCO Document ranking task, we believe this provides a stronger baseline for comparison with neural ranking approaches. It can also be tuned for recall to provide a strong "retriever" component of a Q&A pipeline. What is often not talked about on leaderboards is also the latency of queries. You may achieve a higher relevance score (MRR@100) with neural ranking approaches but at what cost to real performance? This technique allows us to get the most relevance out of a query while maintaining high scalability and low latency search queries.   

For a high-level overview of the motivation, prerequisite knowledge and summary, please see the accompanying blog post (pending publishing).

## Results

Based on a series of evaluations with various analyzers, query types, and optimization, we’ve achieved the following results on the MS MARCO Document "Full Ranking" task as measured by MRR@100 on the "development" dataset. All experiments with full details and explanations can be found in the referenced Jupyter notebook. The best scores from each notebook are highlighted.

| Reference notebook | Experiment | MRR@100 |
|---|---|---|
| [0 - Analyzers](notebooks/0%20-%20Analyzers.ipynb) | Default analyzers, combined per-field `match`es | 0.2403 |
| [0 - Analyzers](notebooks/0%20-%20Analyzers.ipynb) | Custom analyzers, combined per-field `match`es | 0.2505 |
| [0 - Analyzers](notebooks/0%20-%20Analyzers.ipynb) | Default analyzers, `multi_match` `cross_fields` (default params) | 0.2477 |
| [0 - Analyzers](notebooks/0%20-%20Analyzers.ipynb) | Default analyzers, `multi_match` `cross_fields` (default params) | 0.2680 |
| [0 - Analyzers](notebooks/0%20-%20Analyzers.ipynb) | Default analyzers, `multi_match` `best_fields` (default params) | 0.2717 |
| [0 - Analyzers](notebooks/0%20-%20Analyzers.ipynb) | Default analyzers, `multi_match` `best_fields` (default params) | **0.2873** |
| [1 - Query tuning](notebooks/1%20-%20Query%20tuning.ipynb) | `multi_match` `cross_fields` baseline: default params | 0.2673 |
| [1 - Query tuning](notebooks/1%20-%20Query%20tuning.ipynb) | `multi_match` `cross_fields` tuned (step-wise): `tie_breaker`, `minimum_should_match` | 0.2829 |
| [1 - Query tuning](notebooks/1%20-%20Query%20tuning.ipynb) | `multi_match` `cross_fields` tuned (step-wise): all params | **0.3011** |
| [1 - Query tuning](notebooks/1%20-%20Query%20tuning.ipynb) | `multi_match` `cross_fields` tuned (all-in-one v1): all params | 0.2945 |
| [1 - Query tuning](notebooks/1%20-%20Query%20tuning.ipynb) | `multi_match` `cross_fields` tuned (all-in-one v2, refined parameter space): all params | 0.2990 |
| [1 - Query tuning](notebooks/1%20-%20Query%20tuning.ipynb) | `multi_match` `cross_fields` tuned (all-in-one v3, random): all params | 0.2980 |
| [2 - Query tuning - best_fields](notebooks/1%20-%20Query%20tuning%20best_fields.ipynb) | `multi_match` `best_fields` baseline: default params | 0.2873 |
| [2 - Query tuning - best_fields](notebooks/1%20-%20Query%20tuning%20best_fields.ipynb) | `multi_match` `best_fields` tuned (all-in-one): all params | **0.3078** |

## Setup

### Prerequisites

To run the simulation, you will first need:

 - Elasticsearch 7.10+ **
   - Cloud [Elasticsearch Service](https://www.elastic.co/elasticsearch/service) (free trials available)
   - [Local installations](https://www.elastic.co/start)
 - `make`
 - Python 3.7+ (try [pyenv](https://github.com/pyenv/pyenv) to manage multiple Python versions)
 - `virtualenv` (installed with `pip install virtualenv`)

** Instructions and code have been tested on versions: 7.8.0, 7.9.3, 7.10.0. There is a slight relevance improvement in 7.9.3 over 7.8.x so we would recommend 7.9.3 at a minimum, but prefer always the latest release.

### Project and environment

Use the `Makefile` for all setup, building, testing, etc. Common commands (and targets) are:

 - `make init`: install project dependencies (from requirements.txt)
 - `make clean`: cleanup environment
 - `make test`: run tests
 - `make jupyter`: run Jupyter Lab (notebooks)

Most operations are performed using scripts in the `bin` directory. Use `-h` or `--help` on the commands to explore their functionality and arguments such as number of processes to use (for parallelizable tasks), URL for Elasticsearch, etc.

Start off by running just `make init` to setup the project.

Start an Elasticsearch instance locally or use a [Cloud](https://cloud.elastic.co) instance. For this demo, we recommend allocating at least 8GB of memory to the Elasticsearch JVM and having at least 16 GB total available on the host.

```bash
ES_JAVA_OPTS="-Xmx8g -Xms8g" ./bin/elasticsearch
```

### Data

We use [MSMARCO](https://msmarco.org) as a large-scale, public benchmark. Download the dataset and make it available in `data/msmarco-document`.

Convert the corpus into indexable documents (~5 mins):

```bash
time bin/convert-msmarco-document-corpus \
  data/msmarco/document/msmarco-docs.tsv \
  data/msmarco-document-index-actions.jsonl
```

Bulk index documents into two indices (with different analyzers) (~30 mins):

```bash
time bin/bulk-index \
  --index msmarco-document.defaults \
  --config config/msmarco-document-index.defaults.json \
  data/msmarco-document-index-actions.jsonl
```

```bash
time bin/bulk-index \
  --index msmarco-document \
  --config config/msmarco-document-index.custom.json \
  data/msmarco-document-index-actions.jsonl
```

For debugging, experimentation and the final optimization process, sample the query training dataset into smaller datasets:

```bash
bin/split-and-sample \
  --input data/msmarco/document/msmarco-doctrain-queries.tsv \
  --output \
    data/msmarco-document-sampled-queries.10.tsv,10 \
    data/msmarco-document-sampled-queries.100.tsv,100 \
    data/msmarco-document-sampled-queries.1000.tsv,1000 \
    data/msmarco-document-sampled-queries.10000.tsv,10000
```

At this point, you can choose to either carry on running things from the command line or you can jump to the notebooks and walk through a more detailed set of examples. We recommend the notebooks first, then come back and use the command line scripts when you have larger scale experimentation or evaluation that you'd like to perform.

## Notebooks

The notebooks are structued as teaching walkthroughs and contain a lot of detail on the process. We recommend going through the notebooks in the following order:

- `0 - Analyzers`
- `1 - Query tuning`
- `2 - Query tuning - best_fields`
- `Appendix A - BM25 tuning`

To start the Jupyter Labs (notebooks) server, use `make jupyter`.

## Command line scripts

All of the code that powers the notebooks is also available through command line scripts. These scripts can be more convenient to run on a server in a `screen` session, for example, if your jobs take hours to run.

### Run evaluation

Using some baseline/default parameter values, run an evaluation. This uses the `dev` dataset, which contains about 3,200 queries.

```bash
time bin/eval \
  --index msmarco-document \
  --metric config/metric-mrr-100.json \
  --templates config/msmarco-document-templates.json \
  --template-id cross_fields \
  --queries data/msmarco/document/msmarco-docdev-queries.tsv \
  --qrels data/msmarco/document/msmarco-docdev-qrels.tsv \
  --params config/params.cross_fields.baseline.json
```

### Run query optimization

Build a configuration file based on the kind of optimization you want to do. This uses one of the sampled `train` datasets, which contains 10,000 queries. (Note that in the notebooks, we typically only use 1,000 queries for training.) This will save the output of the final parameters to a JSON config file that can be used by evaluation.

```bash
time bin/optimize-query \
  --index msmarco-document \
  --metric config/metric-mrr-100.json \
  --templates config/msmarco-document-templates.json \
  --template-id cross_fields \
  --queries data/msmarco-document-sampled-queries.10000.tsv \
  --qrels data/msmarco/document/msmarco-doctrain-qrels.tsv \
  --config config/optimize-query.cross_fields.json \ 
  --output data/params.cross_fields.optimal.json
```

Run the evaluation again to compare results on the same `dev` dataset, but this time with the optimal parameters.

```bash
time bin/eval \
  --index msmarco-document \
  --metric config/metric-mrr-100.json \
  --templates config/msmarco-document-templates.json \
  --template-id cross_fields \
  --queries data/msmarco/document/msmarco-docdev-queries.tsv \
  --qrels data/msmarco/document/msmarco-docdev-qrels.tsv \
  --params data/params.cross_fields.optimal.json
```

See the accompanying Jupyter notebooks for more details and examples.

### Run TREC evaluation

Download the official TREC evaluation tool. The current version as of publish date is `9.0.7`.

```bash
wget https://trec.nist.gov/trec_eval/trec_eval-9.0.7.tar.gz
tar -xzvf trec_eval-9.0.7.tar.gz
cd trec_eval-9.0.7
make
cd ..
```

Run the evaluation on the provided top 100 results from the `dev` set, and validate the output.

```bash
trec_eval-9.0.7/trec_eval -c -mmap -M 100 \
    data/msmarco/document/msmarco-docdev-qrels.tsv \
    data/msmarco/document/msmarco-docdev-top100
```

```
map                   	all	0.2219
```

Run our query and generate a TREC compatible result file. Make sure to choose the right template and a matching parameter configuration file.

```bash
time bin/bulk-search \
  --index msmarco-document \
  --name cross_fields \
  --templates config/msmarco-document-templates.json \
  --template-id cross_fields \
  --queries data/msmarco/document/msmarco-docdev-queries.tsv \
  --params config/params.cross_fields.optimal.json \
  --size 100 \
  --output data/msmarco-docdev-cross_fields-top100.tsv
```

And now evalute on the new results.

```bash
trec_eval-9.0.7/trec_eval -c -mmap -M 100 \
    data/msmarco/document/msmarco-docdev-qrels.tsv \
    data/msmarco-docdev-cross_fields-top100.tsv
```
