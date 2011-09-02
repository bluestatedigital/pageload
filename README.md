Pageload Performance Monitoring
===============================

Python CLI and library that collects data using the webpagetest.org API and can run analysis on the data.

Requirements
------------

* Python 2.7+
* webpagetest.org API key

Installing
----------

    $ cd /path/to/setup.py
    $ python setup.py install

The executable's path might not be in your PATH.  In the output for the installer, there is a line that says where the executable is located.  It should say something like 'Installing pageload script to /home/sfrazer/bin'.

Usage
-----
To display usage options use the `--help` flag

    $ pageload -h
    usage: pageload [-h] [-L LOGGING] {run,dev,filter,ls,list-filters,rm} ...

    BSD Page Load Performance Monitor

    positional arguments:
      {run,dev,filter,ls,list-filters,rm}
                            Available actions
        run                 Run a series of web page tests.
        ls                  List contents of a directory containing test data.
        rm                  Remove a test.
        filter              Display a subset of the information about the test
                            data.
        list-filters        List currently available filters.
        dev                 Developer land.

    optional arguments:
      -h, --help            show this help message and exit
      -L LOGGING, --logging LOGGING
                            Turn on debugging output

    (c) 2011 Blue State Digital

Configuration & Running Tests
-----------------------------

There are two configuration files: one for specifying which tests to run and one to specify global parameters that are to be passed along to each test.  An example of a test configuration file is

    [
        {
            "url": "http://google.com/",
            "name": "mytest",
            "params": {"runs": 5}
        },
        {
            "url": "http://yahoo.com/",
            "name": "mysecondtest",
            "params": {"runs": 5}
        }
    ]

Each test must contain a url, name, and parameters.  The params section of each test specifies test-specific parameters as described here: https://sites.google.com/a/webpagetest.org/docs/advanced-features/webpagetest-restful-apis.  The name field is the name of the directory where test results will be stored and the URL field specifies the URL to gather page load performance data for.

Some parameters, like the webpagetest.org API key, should be passed in with every request.  This is where the global parameters configuration file comes in.  An example global parameters configuration file looks like:

    {
        "k": "api_key",
        "f": "xml"
    }

These two files together can be specified at the command line with the 'run' command to gather page load metrics.  For example:

    $ pageload run --tests=~/tests.json --global-params=~/global-params.json --directory=.

This command will run all tests in tests.json and store the results in the current directory.  If we use the test configuration above, the current directory will have a 'mytest' and a 'mysecondtest' directory in it when the metrics are finished gathering.

Analyzing Test Runs
-------------------

The core to analyzing test results is to filter them by key pieces of information.  To see what kind of filters are available and what information each provide, use the list-filters command.  Webpagetest collects data for 'first views' and 'repeat views'.  All filters are prefixed by either fv (first view) or rv (repeat view).

Filters can be one of two types: a normal filter or an aggregate filter.  Normal filters just present the data as it is.  For example, fv_url_and_ttfb will simply output each request and the time to first byte for that request.  Aggregate filters will combine data in some way.  fv_count, for example, shows the number of CSS, Javascript, and image requests by scanning all requests and counting based on the content-type header.

Using the list-filters sub-command can show which filters are available:

    $ pageload list-filters
    fv_count - (type: aggregate) Time to load, # of assets and their sizes (first view)
    fv_url_and_ttfb - (type: normal) Time to first byte for each resource (first view)
    rv_count - (type: aggregate) Time to load, # of assets and their sizes (repeat view)
    fv_start_end_time - (type: normal) Start time and end time for each resource (first view)
    fv_url_and_ttl - (type: normal) Time to load for each resource (first view)

The filter sub-command is used to perform one of these filters.  The filter command MUST be run in the same directory that the tests are in.  To find out which tests are visible from the current directory, use the 'ls' subcommand:

    $ pageload ls
    first_test
      [7aaf7151] 2011/08/25 14:16:26

    second_test
      [4f545e21] 2011/08/25 14:07:16
      [ee168e04] 2011/08/31 13:08:20

The important information here is the hash which identifies this test uniquely, and the date/time it was run.  The hash will can be used with the filter command to specify which test(s) to run the filter on:

    $ pageload filter --filter=fv_count 7aaf7151:1
    [7aaf7151a2f470db298537f62bd3158f] run 1 (2011/08/25 14:16:26)
      Run directory: ./first_test/20110825141626/run/1
      Images size (bytes): 281004
      Image files: 34
      Time to Load (ms): 8508
      JS files: 21
      Time to First Byte (ms): 2915
      JS size (bytes): 256938
      TTL - TTFB (ms): 5593
      CSS files: 4
      CSS size (bytes): 14388

Test Hash Format
----------------

Each test consists of one or more run.  Because of this, a test hash AND one or more run must be specified with the filter command.  The general format for specifying test runs is:

    <hash>[:<runs>]

<hash> is the unique identifier of the test run (acquired from the 'pageload ls' command).  the <runs> parameter can specify a comma separated list of run numbers or a ranges of runs.  If no <runs> parameter is specified, ALL runs will be assumed.  Some examples of test run specifications:

    7aaf7151:1     # test 7aaf7151, first run
    7aaf7151:1-5   # first five runs
    7aaf7151:1,4-6 # runs 1,4,5,6

Comparing Tests
---------------

The 'filter' subcommand can accept a --compare parameter for an aggregate filter to list the results for each test run side by side for quick visual comparison:

    $ pageload filter --filter=fv_count 7aaf7151:1,2,3 --compare
                             7aaf7151:1     7aaf7151:2     7aaf7151:3       
    Images size (bytes)      281004         280242         287336         
    Image files              34             29             34             
    Time to Load (ms)        8508           7686           8077           
    JS files                 21             21             9              
    Time to First Byte (ms)  2915           2203           3015           
    JS size (bytes)          256938         356216         234511         
    TTL - TTFB (ms)          5593           5483           5062           
    CSS files                4              4              2              
    CSS size (bytes)         14388          18588          14142

Alternatively, --combine=<mean|median> can be specified to further compare many results.  This is often used to get a summary which will help weed out outliers from a test with many runs.

    $ pageload filter --filter=fv_count 7aaf7151:1-9 --combine=median
    Combined results using the median (9 runs)
    Images size (bytes)      280242
    Image files              34
    Time to Load (ms)        8077
    JS files                 9
    Time to First Byte (ms)  2326
    JS size (bytes)          229398
    TTL - TTFB (ms)          5593
    CSS files                2
    CSS size (bytes)         14142

At an even higher level, you can diff two sets of test runs using the --diff option.  This adds a column at the end that showing the difference:

    $ pageload filter --filter=fv_count 7aaf7151:1-2 4f545e21:1-2 --combine=median --diff
                             7aaf7151:1,2                  4f545e21:1,2                  diff                          
    Images size (bytes)      280623.0                      280172.0                      -451.0               
    Image files              31.5                          34.0                          +2.5                 
    Time to Load (ms)        8097.0                        8764.0                        +667.0               
    JS files                 21.0                          21.0                          +0.0                 
    Time to First Byte (ms)  2559.0                        1906.0                        -653.0               
    JS size (bytes)          306577.0                      290960.5                      -15616.5             
    TTL - TTFB (ms)          5538.0                        6858.0                        +1320.0              
    CSS files                4.0                           4.0                           +0.0                 
    CSS size (bytes)         16488.0                       14375.0                       -2113.0 
