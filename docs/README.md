This wiki guide will walk you through the various steps, technical decision and methodologies taken to setup this app, in terms of how data was prepared from the given inputs and how can users interpret the analysis they do on the frontend application.

### Github Setup
This [repo](../) is the main branch which hosts the following components:
* FastAPI
* Docker Setup
* Links to Data
* PreProcessing Scripts

### Continuous Integration (CI)

The current strategy to merge changes in the main branch is by creating separate `feature` branches, for eg: `feature/0001`. On each commit, there is a CI `unittests` ([YAML File](../.github/workflows/run-unit-tests.yml)) that is triggered and can be tracked under Github Actions

Following was the order to setup this application: 
`Raw Data > PreProcessing > Data Outputs > FastAPI App > Dockerised Deployment`

If you'd like to just use the App and understand how it is built and works, or even deploy it locally with the processed data, [read this](../README.md)

If you'd like to prepare the data from scratch, [read this](../preprocess/README.md)

***

### Conceptual Explanations

1. [Data PreProcessing Workflow](./preprocessing.md) explains the data preparation steps in [preprocess/](https://github.com/purijs/terrain-mapper/blob/main/preprocess/), _aimed for Developers_
2. [User Analytics: App Interaction](./analytics.md) explains how user can infer the analysis made in the UI, _aimed at Business Users_

### Possible Improvements/Challenges Encountered

* Interpolation at scale using grid system causes artifacts at edges of grids
* Initially, DuckDb as a spatial DB was also explored however due to lack of spatial operations support it was dropped
* Data normalisation/ingestion needs to be sophisticated. Not all data sources might provide data in `xyz` format
* Data Pipelines can be automated. If there's an updated DTM file, it should trigger a chain of actions, all the way to create final products
* Data should be usable for querying by internal team members for analytics without affect the Product's performance. 
* Distributed workloads can be tested with Apache Sedona
* Data pipelines should be separated from feature pipeline. One should be able to promote feature across different environments like `DEV/QA/PRD` without depending on Data Changes, for example, if a raster does not exist in `PRD` environment, it should not stop release of features
* Segregate data by `environments`. Developers would want to test with certain subsets of Data before releasing features to `PRD`
