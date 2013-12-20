# Appurify Python Client

The official Python client for the [Appurify](http://www.appurify.com) API.

### Installation

```
pip install appurify-0.2.7.tar.gz
```

This will install any missing dependencies and add two executable scripts to your bin folder:

```
$ appurify-client.py -h
$ appurify-tunnel.py -h
```

### Running Tests

```
appurify-client.py --api-key $API_KEY --api-secret $API_SECRET \
--app-src $APP-SRC --app-test-type $TEST_TYPE --test-src $TEST_SRC --test-type $TEST_TYPE \
--device-type-id $DEVICE_TYPE_IDS --result-dir $RESULT_DIR
```

### Parameters

- `API-KEY`: Used for authentication
- `API-SECRET`: Used for authentication
- `APP-SRC`: The path or URL to the app binary (.ipa or .apk)
- `TEST_SRC`: The path or URL where the test files are located
- `TEST_TYPE`: Your test framework name (i.e. calabash, ios_robot, ocunit, uiautomation)
- `DEVICE_TYPE_IDS`: A comma separated list of numbers representing the device type IDs you wish to use for your test
- `RESULT_DIR`: The directory on your local machine where you want your results to be written.

### Jenkins Integration
In Jenkins create a new Execute Shell build step and upload your app using the Python wrapper as pictured below.

![Jenkins Integration](https://raw.github.com/appurify/appurify-python/master/jenkins.png)

### Contribution

Found a bug or want to add a much needed feature?  Go for it and just send us the Pull Request!

## Release Notes

### 0.2.8 
- Added ```--version``` flag to print version and exit

### 0.2.6
- Users will receive a warning when attempting to upload a web test without specifying the url parameter.
- Support for both ```--timeout``` parameter to specify the desired timeout at runtime, or using the os environment variable ```APPURIFY_API_TIMEOUT```. Specify desired timeout in seconds. 

### 0.2.2

- Added ```ios_sencharobot``` test type 

### 0.2.1

- ```network_headers``` test type no longer requires app source
- Fixed an issue where test results were not properly downloaded despite setting the ```result-dir``` parameter.
- Test source is now optional for ```kif``` test type
- Improved test status information when polling a running test
- Configuration values are now printed when running a test
- Fixed a bug where ``name``` parameter was not respected for web apps
