# chrome-url-dumper

[![Awesome](https://cdn.rawgit.com/sindresorhus/awesome/d7305f38d29fed78fa85652e3a63e154dd8e8829/media/badge.svg)](https://github.com/cugu/awesome-forensics)

Accessing db's stored on machine by chrome browser and dumping urls found 

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See Running the tests for notes on how to deploy the project on a live system.

### Prerequisites

```
Python 2.7
```

### Installing

```
pip install -r requirements.txt
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

-k kill chrome proccess ( deeper analysis )
-d deeper analysis

Windows
```
python main.py -k {1/0} -d {1/0}
```

Linux
```
./main.py -k {1/0} -d {1/0}
```

## Authors

* **Tomer Eyzenberg** - *Initial work* - [eLoopWoo](https://github.com/eLoopWoo)

