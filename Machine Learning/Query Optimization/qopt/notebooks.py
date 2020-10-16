"""Support for Jupyter Lab notebooks."""

import os

from copy import deepcopy
from .eval import build_requests
from .optimize import optimize_query, optimize_bm25
from .trec import load_queries_as_tuple_list, load_qrels
from .util import load_json

ROOT_DIR = os.path.abspath('..')
INDEX = 'msmarco-document'
TEMPLATES_FILE = os.path.join(ROOT_DIR, 'config', 'msmarco-document-templates.json')


def mrr(k):
    return deepcopy({
        'mean_reciprocal_rank': {
            'k': k,
            'relevant_rating_threshold': 1,
        }
    })


def evaluate_mrr100_dev(es, template_id, params):
    templates = load_json(TEMPLATES_FILE)
    queries = load_queries_as_tuple_list(os.path.join(ROOT_DIR, 'data', 'msmarco', 'document', 'msmarco-docdev-queries.tsv'))
    qrels = load_qrels(os.path.join(ROOT_DIR, 'data', 'msmarco', 'document', 'msmarco-docdev-qrels.tsv'))
    body = {
        'metric': mrr(100),
        'templates': templates,
        'requests': build_requests(INDEX, template_id, queries, qrels, params),
        'max_concurrent_searches': 30,
    }

    results = es.rank_eval(body=body, index=INDEX, request_timeout=1200,
                           allow_no_indices=False, ignore_unavailable=False)
    print(f"Score: {results['metric_score']:.04f}")
    return results


def verbose_logger(iteration, score, params):
    print(f" - iteration {iteration} scored {score:.04f} with: {params}")


def optimize_query_mrr100(es, template_id, config_space, verbose=True):
    templates = load_json(TEMPLATES_FILE)
    queries = load_queries_as_tuple_list(os.path.join(ROOT_DIR, 'data', 'msmarco-document-sampled-queries.1000.tsv'))
    qrels = load_qrels(os.path.join(ROOT_DIR, 'data', 'msmarco', 'document', 'msmarco-doctrain-qrels.tsv'))
    if verbose:
        print("Optimizing parameters")
        logger = verbose_logger
    else:
        logger = None

    best_score, best_params, final_params, metadata = optimize_query(
        es, INDEX, config_space, mrr(100), templates, template_id, queries, qrels, logger)

    print(f"Best score: {best_score:.04f}")
    print(f"Best params: {best_params}")
    print(f"Final params: {final_params}")
    print()

    return best_score, best_params, final_params, metadata


def optimize_bm25_mrr100(es, template_id, default_params, verbose=True):
    templates = load_json(TEMPLATES_FILE)
    queries = load_queries_as_tuple_list(os.path.join(ROOT_DIR, 'data', 'msmarco-document-sampled-queries.10000.tsv'))
    qrels = load_qrels(os.path.join(ROOT_DIR, 'data', 'msmarco', 'document', 'msmarco-doctrain-qrels.tsv'))
    if verbose:
        print("Optimizing parameters")
        logger = verbose_logger
    else:
        logger = None

    best_score, best_params, final_params, metadata = optimize_bm25(
        es, INDEX, mrr(100), templates, template_id, queries, qrels, default_params, logger)

    print(f"Best score: {best_score:.04f}")
    print(f"Best params: {best_params}")
    print(f"Final params: {final_params}")
    print()

    return best_score, best_params, final_params, metadata
