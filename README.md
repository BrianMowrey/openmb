# openmb
git scraping of open manitoba data (since it's unpublished json endpoints for maps)
using https://www.gov.mb.ca/openmb/datamb/

## Process
1. github action scrapes json endpoints and saves pretty printed .json if it has changed (so you get nice revision history)
2. another github action runs on commit to build a sqlite database from .json
3. example jupyter notebook shows how to use data



## TODO:
* pull all possible data
* pandas/datasette examples

