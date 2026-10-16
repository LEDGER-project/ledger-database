# JOSS Paper

This directory contains the code for the [JOSS](https://joss.readthedocs.io/en/latest/submitting.html) paper. Use the code below to compile the paper

```
docker run --rm \     
    --volume $PWD/paper:/data \
    --user $(id -u):$(id -g) \
    --env JOURNAL=joss \
    openjournals/inara
```