# Corona statistics for Sweden
Data from [Folkhälsomydigheten](https://www.folkhalsomyndigheten.se/smittskydd-beredskap/utbrott/aktuella-utbrott/covid-19/aktuellt-epidemiologiskt-lage/). Runs with Python 3+


## How to run
 - [Scraper](fhm-scraper.py) 
   - **NOTE**: if no Chrome-browser
       1. Download from [source](https://raw.githubusercontent.com/Bugazelle/chromium-all-old-stable-versions/master/chromium.stable.json) or for [Linux](https://www.googleapis.com/download/storage/v1/b/chromium-browser-snapshots/o/Linux_x64%2F722276%2Fchrome-linux.zip?generation=1575588380806233&alt=media) (version <= 80)
       2. Unpack to `driver/` and rename to `chromium` 
```
$ ./fhm-scraper.py
```

</br>

 - [Hax](fhm-hax.py)
   - Much faster alternative (gets data directly from API)
```
$ ./fhm-hax.py
```

</br>

 - [forecast](forecast.py) 
   - Based on exponential growth
   - **Requires** `numpy` and `scipy`)
```
$ ./forecast
```
