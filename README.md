# Q Guide Scraper

A Python script to scrape Harvard's course ratings website

## Setup

The q guide scraper uses Selenium + PhantomJS to interact with Harvard's login site, so install PhantomJS with

```
npm install -g phantomjs
```

Next install the python requirements with

```
pip install -r requirements.txt
```

Finally, give the scraper your Harvard login credentials. Create a credentials file with

```
cp sample_credentials.txt credentials.txt
```

then put your own Harvard PIN and password into `credentials.txt`.

## Running

To run the scraper, run

```
python scrapers.py
```

This will create two directories: `data/` and `output/`. The scraper caches webpages it downloads to the `data/` directory to speed up future runs. For each course that the scraper finds, it generates a JSON file `<course_id>.json`, stored in the directory `output/<n>/`, where `n` is the `n`th time the scraper has been run. The schema for the JSON file is defined in `models.py`