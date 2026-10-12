# Workflows

This directory contains different [snakemake](https://snakemake.readthedocs.io/en/stable/) workflows. Each directory is a different workflow. Instead of one main workflow, we decided to split the logic up into a workflow processing datasets and another one for poplulating the database. 

## Visualize the workflow as a DAG

The following command can be run in either workflow directory to visualize the workflow as a [DAG](https://en.wikipedia.org/wiki/Directed_acyclic_graph)

```sh
 snakemake --dag | dot -Tsvg > ./dag.svg
```