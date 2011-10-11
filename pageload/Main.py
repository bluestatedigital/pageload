import argparse, sys, json, os, logging
from datetime import datetime
from functools import reduce
from pageload.PageLoadTestResults import Factory as PageLoadTestResultsFactory
from pageload.PageLoadTest import Factory as PageLoadTestFactory
from pageload.PageLoadTestDirectory import Factory as PageLoadTestDirectoryFactory
from pageload.Colors import AnsiColors
from pageload.Filter import Factory as FilterFactory
from pageload.Filter import FilterResultsDictComparator, FilterResultsDict, FilterResultsDictCombinor, FilterResultsDictComparatorDiff, FilterResultsDictCombinorDiff

def getLogger(level):
    logMap = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'error': logging.ERROR,
        'warning': logging.WARNING,
        'critical': logging.CRITICAL
    }

    try:
        llevel = logMap[level.lower()]
    except KeyError:
        llevel = logging.WARNING

    logger = logging.getLogger('pageload')
    logger.setLevel(llevel)
    ch = logging.StreamHandler()
    ch.setLevel(llevel)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger

def findResult(testHash, directories):
    for directory in directories:
        testResult = directory.getTestResultByHash(testHash)
        if testResult:
            return (directory, testResult)
    return None

def parseTestHash(testHash, directories):
    try:
        (hashPart, runPart) = testHash.split(':')
    except ValueError:
        (hashPart, runPart) = (testHash, '*')

    try:
        (directory, testResult) = findResult(hashPart, directories)
    except TypeError:
        raise Exception('Invalid hash: %s' % (hashPart))

    def parseNum(num):
        if num == '*':
            return list(range(1, len(testResult.getRuns())+1))
        y = num.split('-')
        if len(y) == 2:
            return list(range( int(y[0]), int(y[1])+1 ))
        return [int(num)]

    runRange = list(map(parseNum, runPart.split(',')))
    runRange = set([item for sublist in runRange for item in sublist])
    return (testResult, directory, runRange)

def Cli():

    ver = sys.version_info

    if ver.major < 2 or (ver.major == 3 and ver.minor < 2) or (ver.major == 2 and ver.minor < 7):
        print("Python 2.7+ required. %d.%d.%d installed" %(ver.major, ver.minor, ver.micro))
        sys.exit(-1)

    parser = argparse.ArgumentParser(
        description = 'BSD Page Load Performance Monitor',
        epilog = '(c) 2011 Blue State Digital')

    parser.add_argument('-L', '--logging',
        default='info',
        help='Turn on debugging output')

    subparsers = parser.add_subparsers(help='Available actions', dest='sub_command')

    commands = {}
    commands['run'] = subparsers.add_parser('run', help='Run a series of web page tests.')
    commands['ls'] = subparsers.add_parser('ls', help='List contents of a directory containing test data.')
    commands['rm'] = subparsers.add_parser('rm', help='Remove a test.')
    commands['filter'] = subparsers.add_parser('filter', help='Display a subset of the information about the test data.')
    commands['list-filters'] = subparsers.add_parser('list-filters', help='List currently available filters.')
    commands['dev'] = subparsers.add_parser('dev', help='Developer land.')

    commands['run'].add_argument('-t', '--tests',
        required=True,
        help = 'Location of the test specification file')

    commands['run'].add_argument('-g', '--global-params',
        help = 'Location JSON document with parameters that are to be attached to every request (e.g. API key)')

    commands['run'].add_argument('-d', '--results-dir',
        required = True,
        default = './pageload_tests',
        help = 'Directory to save test results to')

    commands['ls'].add_argument('dir',
        metavar='DIRECTORY',
        nargs='?',
        default = '.',
        help = 'Directory to be listed.')

    commands['dev'].add_argument('dir',
        metavar='DIRECTORY',
        default = '.',
        nargs='?',
        help = 'Directory to be listed.')

    commands['filter'].add_argument('test',
        metavar='TEST',
        nargs='+',
        help = 'Test to filter, by hash value.')

    commands['filter'].add_argument('-f', '--filter',
        required = True,
        help = 'Filter function to run.')

    commands['filter'].add_argument('-c', '--compare',
        action='store_true',
        help = 'For an aggregate filter, compare results side-by-side instead of listing them one after the other.')

    commands['filter'].add_argument('-o', '--output-format',
        action='store',
        default = 'text',
        help = 'How to format the output, ie (json, text)')

    commands['filter'].add_argument('-d', '--diff',
        action='store_true',
        help = 'When used with --compare or --combine, the difference between the results is displayed.')

    commands['filter'].add_argument('-b', '--combine',
        help = 'For an aggregate filter, combines results using either mean or median.')

    commands['rm'].add_argument('test',
        metavar='TEST',
        nargs='+',
        help = 'Tests to remove, by hash value.')

    commands['rm'].add_argument('dir',
        metavar='DIRECTORY',
        nargs='?',
        default = '.',
        help = 'Directory of tests.')

    cli = parser.parse_args()
    logger = getLogger(cli.logging)

    logger.debug( 'CLI: %s' % (cli) )

    if cli.sub_command == 'filter':

        if cli.compare and cli.combine:
            logger.error('--compare and --combine are mutually exclusive')
            sys.exit(-1)

        directoryFactory = PageLoadTestDirectoryFactory( PageLoadTestResultsFactory() )
        directories = directoryFactory.discover('.')
        filterFactory = FilterFactory()
        filteredTestResultsLists = list()

        for testHash in cli.test:
            (testResult, directory, runList) = parseTestHash( testHash, directories )
            if testResult is None:
                logger.error('Test hash %s doesn\'t point to a valid test result' % (testHash))
                sys.exit(-1)

            f = filterFactory.create(cli.filter)
            result = f.filter( testResult, runList )
            filteredTestResultsLists.append(result)


        filteredTestResults = [item for sublist in filteredTestResultsLists for item in sublist]
        if cli.output_format == "json":
            for result in filteredTestResults:
                print(result.asJson())
                sys.exit(0)


        if cli.compare:
            if not isinstance(filteredTestResults[0], FilterResultsDict):
                logger.error('--compare is only allowed with aggregate filters (try pageload list-filters)')
                sys.exit(-1)

            if cli.diff:
                if len(filteredTestResults) != 2:
                    logger.error('Specifying --diff requires exactly two test hashes.  (e.g. pageload filter <hash1> <hash2> --compare --diff)')
                    sys.exit(-1)

                diffComparator = FilterResultsDictComparatorDiff( filteredTestResults[0], filteredTestResults[1] )
                print(diffComparator)
            else:
                comparator = FilterResultsDictComparator( filteredTestResults )
                print(comparator)

        elif cli.combine:
            if not isinstance(filteredTestResults[0], FilterResultsDict):
                logger.error('--combine is only allowed with aggregate filters (try pageload list-filters)')
                sys.exit(-1)

            if cli.combine not in ['median', 'mean']:
                logger.error("--combine must specify either 'mean' or 'median'")
                sys.exit(-1)

            if cli.diff:
                if len(filteredTestResultsLists) != 2:
                    logger.error('Specifying --diff requires exactly two test hash sets.  (e.g. pageload filter <hash1>:4-7 <hash2>:1-3 --compare --diff)')
                    sys.exit(-1)

                combinor0 = FilterResultsDictCombinor( filteredTestResultsLists[0], cli.combine )
                combinor1 = FilterResultsDictCombinor( filteredTestResultsLists[1], cli.combine )
                combinor = FilterResultsDictCombinorDiff(combinor0, combinor1)
                print(combinor)
            else:
                combinor = FilterResultsDictCombinor( filteredTestResults, cli.combine )
                print(combinor)

        else:
            for result in filteredTestResults:
                print(result)

    if cli.sub_command == 'list-filters':
        for filterName, filterAttributes in FilterFactory.filterMap.items():
            print('%s - (type: %s) %s' % (filterName, filterAttributes['type'], filterAttributes['description']))

    if cli.sub_command == 'rm':
        if not os.path.isdir( cli.dir ):
            logger.error('%s is not a directory' % (cli.dir))
            sys.exit(-1)

        directoryFactory = PageLoadTestDirectoryFactory( PageLoadTestResultsFactory() )
        directories = directoryFactory.discover( cli.dir )

        styler = AnsiColors()
        for testHash in cli.test:
            (directory, testResult, runList) = parseTestHash( testHash, directories )
            if testResult is None:
                logger.warning('Test hash %s doesn\'t point to a valid test result' % (testHash))
                continue
            testResult.remove()
            directory.writeManifest()
            print( '%s Removed' % (styler.color(testResult.getSignature(), 'yellow')) )
                        
    if cli.sub_command == 'ls':
        if not os.path.isdir( cli.dir ):
            logger.error('%s is not a directory' % (cli.dir))
            sys.exit(-1)

        directoryFactory = PageLoadTestDirectoryFactory( PageLoadTestResultsFactory() )
        directories = directoryFactory.discover( cli.dir )

        styler = AnsiColors()
        for directory in directories:
            print(directory.getName())
            for result in directory.getTestResults():
                print( '  [%s] %s' % (styler.color(result.getSignature()[:8], 'yellow'), result.getDateTime().strftime('%Y/%m/%d %H:%M:%S')) )
            sys.stdout.write('\n')

    if cli.sub_command == 'dev':
        directoryFactory = PageLoadTestDirectoryFactory( PageLoadTestResultsFactory() )
        directories = directoryFactory.discover('.')

#        try:
        x = parseTestHash(cli.dir, directories)
        print(x)
#        except Exception as e:
#            print(e)
#            sys.exit(-1)

    if cli.sub_command == 'run':
        if not os.access(cli.results_dir, os.W_OK):
            logger.error('Test results directory is not writable.')
            sys.exit(-1)

        if os.path.isfile( cli.tests ):
            try:
                tests = json.loads( open(cli.tests).read() )
            except Exception as e:
                logger.error('Unable to load tests file: %s' % (e))
                sys.exit(-1)
        else:
            logger.error('argument to --tests is not a file')
            sys.exit(-1)

        globalParams = None
        if cli.global_params:
            if os.path.isfile( cli.global_params ):
                try:
                    globalParams = json.loads( open(cli.global_params).read() )
                except Exception as e:
                    logger.warning('Unable to load global parameters file: %s' % (e))
            else:
                logger.warning('Argument to --global-params is not a file')

        for requestParams in tests:
            if globalParams:
                requestParams['params'] = dict(globalParams.items() + requestParams['params'].items())
            requestParams['params']['url'] = requestParams['url']
            testFactory = PageLoadTestFactory()
            directoryFactory = PageLoadTestDirectoryFactory( PageLoadTestResultsFactory() )
            testDirectory = directoryFactory.load( os.path.join(cli.results_dir, requestParams['name']) )
            pageload = testFactory.create(testDirectory, requestParams['url'], requestParams['params'])
            results = pageload.run()
            if results is None:
                logger.warning('Could not acquire test results')
