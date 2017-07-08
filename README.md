# chrome-url-dumper

Accessing db's stored on machine by chrome browser and dumping urls found 

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

### Prerequisites

```
Python 2.7
```

### Installing

```
pip install requirements.txt
```

Check packages


Windows
```
pip list | Findstr /L "package"
```

Linux
```
pip list | grep "package"
```

## Running the tests

-o oprating system
-k kill chrome proccess ( deeper analysis )
-d deeper analysis
```
./chrome_urls.py -o {string} -k {1/0} -d {1/0}
```

## Authors

* **Tomer Eyzenberg** - *Initial work* - [eLoopWoo](https://github.com/eLoopWoo)

