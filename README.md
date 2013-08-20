# Appurify Python Client

The official Python client for the [Appurify](http://www.appurify.com) API.

### Installation

```
pip install appurify­0.1.7.tar.gz
```

This will install any missing dependencies and add two executable scripts to your bin folder:

```
$ appurify­client.py ­h
$ appurify­proxy.py ­h
```

### Running Tests

```
appurify­client.py ­­api­key <api key> ­­api­secret <api secret> ­­app­src <pathto .ipa> 
        ­­test­src <path to .zip or .js> ­­test­type <test­type> ­­app­test­type <test­type> ­
        ­device­type­id <iOS device type> ­­config­src <pathto test conf> 
        ­­result­dir <result directory>
```

### Parameters

- api-key: Used for authentication
- api-secret: Used for authentication
- app-src: The path or URL to the app binary (.ipa or .apk)
- test-src: The path or URL where the test files are located
- test-type: Your test framework name (i.e. calabash, ios_robot, ocunit, uiautomation)
- device-type-id: A comma separated list of numbers representing the device type IDs you wish to use for your test
- result-dir: The directory on your local machine where you want your results to be written


### Contribution

Found a bug or want to add a much needed feature?  Go for it and just send us the Pull Request!
