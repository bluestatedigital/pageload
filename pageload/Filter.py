import os
from itertools import izip
from functools import reduce
from pageload.Colors import AnsiColors

class CountFilter:
    def filter( self, testResult, runList ):
        rVal = list()
        for runIndex in runList:
            requests = self.getRequests(testResult, runIndex - 1)
            rVal.append( FilterResultsDict(testResult, runIndex, self.getValues(requests)) )
        return rVal

    def getValues(self, requests):
        values = {
            'time_to_load': 0,
            'time_to_first_byte': 0,
            'ttl_minus_ttfb': 0,
            'js_files': 0,
            'css_files': 0,
            'image_files': 0,
            'js_size': 0,
            'css_size': 0,
            'image_size': 0
        }
        for index, request in enumerate(requests):
            if index == 0:
                values['time_to_load'] = int(request['Time to Load (ms)'])
                values['time_to_first_byte'] = int(request['Time to First Byte (ms)'])
                values['ttl_minus_ttfb'] = values['time_to_load'] - values['time_to_first_byte']
            if 'javascript' in request['Content Type']:
                values['js_files'] += 1
                values['js_size'] += int(request['Object Size'])
            if 'css' in request['Content Type']:
                values['css_files'] += 1
                values['css_size'] += int(request['Object Size'])
            if 'image/' in request['Content Type']:
                values['image_files'] += 1
                values['image_size'] += int(request['Object Size'])
        return values

    def _average(self, values):
        def _sum(x, y):
            r = dict()
            for key in self.strings.keys():
                r[key] = x[key] + y[key]
            return r
        reduced = reduce(_sum, values)
        for k, v in reduced.items():
            reduced[k] = int(v) / len(values)
        return reduced

class ViewCountFilter(CountFilter):
    def getRequests(self, testResult, runIndex):
        run = testResult.getRuns()[runIndex]
        return self.getView(run).getRequestData()

class FirstViewCountFilter(ViewCountFilter):
    def getView(self, run):
        return run.getFirstView()

class RepeatViewCountFilter(ViewCountFilter):
    def getView(self, run):
        return run.getRepeatView()

class UrlTimeToLoadFilter():
    def filter(self, testResult, runList):
        rVal = list()
        for runIndex in runList:
            run = testResult.getRuns()[runIndex - 1]
            requests = run.getFirstView().getRequestData()
            filtered = list()
            for request in requests:
                filtered.append( '%s\t%s' % (request['Time to Load (ms)'] + ' ms', request['Host'] + request['URL']) )
            rVal.append(FilterResultsList(testResult, runIndex, filtered))
        return rVal

class UrlTimeToFirstByteFilter():
    def filter(self, testResult, runList):
        rVal = list()
        for runIndex in runList:
            run = testResult.getRuns()[runIndex - 1]
            requests = run.getFirstView().getRequestData()
            filtered = list()
            for request in requests:
                filtered.append( '%s\t%s' % (request['Time to First Byte (ms)'] + ' ms', request['Host'] + request['URL']) )
            rVal.append(FilterResultsList(testResult, runIndex, filtered))
        return rVal

class StartAndEndTimeFilter():
    def filter(self, testResult, runList):
        rVal = list()
        for runIndex in runList:
            run = testResult.getRuns()[runIndex - 1]
            requests = run.getFirstView().getRequestData()
            filtered = list()
            for request in requests:
                filtered.append( (request['URL'], request['Start Time (ms)'], request['End Time (ms)']) )
            rVal.append( FilterResultsList(testResult, runIndex, filtered) )
        return rVal

class FilterResultsList:
    def __init__(self, testResult, run, filteredList):
        self.__dict__.update(locals())
    def __str__(self):
        styler = AnsiColors()
        rVal = '[%s] run %d (%s)\n' % (styler.color(self.testResult.getSignature(), 'yellow'), self.run, self.testResult.getDateTime().strftime('%Y/%m/%d %H:%M:%S'))
        rVal += 'Run directory: %s\n' % (styler.color(os.path.join(self.testResult.testDir, 'run/' + str(self.run)), 'red'))
        rVal += '\n'.join([str(x) for x in self.filteredList])
        return rVal

class FilterResultsDict:
    strings = {
        'time_to_load': 'Time to Load (ms)',
        'time_to_first_byte': 'Time to First Byte (ms)',
        'ttl_minus_ttfb': 'TTL - TTFB (ms)',
        'js_files': 'JS files',
        'css_files': 'CSS files',
        'image_files': 'Image files',
        'js_size': 'JS size (bytes)',
        'css_size': 'CSS size (bytes)',
        'image_size': 'Images size (bytes)'
    }

    def __init__(self, testResult, run, dictionary):
        self.__dict__.update(locals())
    def __str__(self):
        styler = AnsiColors()
        rVal = '[%s] run %d (%s)\n' % (styler.color(self.testResult.getSignature(), 'yellow'), self.run, self.testResult.getDateTime().strftime('%Y/%m/%d %H:%M:%S'))
        rVal += 'Run directory: %s\n' % (styler.color(os.path.join(self.testResult.testDir, 'run/' + str(self.run)), 'red'))
        for k, v in self.dictionary.items():
            rVal += '  %s: %s\n' % (self.strings[k], v)
        return rVal

    def asJson(self):
        rVal = "{\n";
        for k, v in self.dictionary.items():
            rVal += "\t  '%s': %d,\n" % (k, v)
        return rVal + "\n}"


class FilterResultsDictComparator:
    def __init__(self, filteredResultsDicts):
        self.__dict__.update(locals())
    def __str__(self):
        styler = AnsiColors()
        columnWidth = 15
        keys = self.filteredResultsDicts[0].dictionary.keys()
        longestKey = max(map(lambda x: len(x), keys))
        testHashes = list(map(lambda x: '%s:%d' % (x.testResult.getSignature()[:8], x.run), self.filteredResultsDicts))
        rVal = '%s  %s\n' % (''.ljust(longestKey), styler.color(''.join([x.ljust(columnWidth) for x in testHashes]), 'yellow') )
        for key in keys:
            values = list(map(lambda x: x.dictionary[key], self.filteredResultsDicts))
            rVal += '%s  %s\n' % (key.ljust(longestKey), ''.join([str(x).ljust(columnWidth) for x in values]))
        return rVal

class FilterResultsDictCombinor:
    def __init__(self, filteredResultsDicts, method):
        self.__dict__.update(locals())
        self._compute()

    def getTestRunSignatures(self):
        tests = list(map(lambda x: (x.testResult.getSignature()[:8], x.run), self.filteredResultsDicts))
        testRunMap = dict()
        for hash, run in tests:
            if hash not in testRunMap:
                testRunMap[hash] = list()
            testRunMap[hash].append(run)
        return ' '.join(['%s:%s' % (hash, ','.join([str(x) for x in runs])) for hash, runs in testRunMap.items()])

    def _compute(self):
        self.combined = dict()
        func = self._median if self.method == 'median' else self._mean
        for key in self.filteredResultsDicts[0].dictionary.keys():
            values = list(map(lambda x: x.dictionary[key], self.filteredResultsDicts))
            combined = func(values)
            self.combined[key] = combined

    def _median(self, numericValues):
      theValues = sorted(numericValues)
      if len(theValues) % 2 == 1:
        return theValues[(len(theValues)+1)/2-1]
      else:
        lower = theValues[len(theValues)/2-1]
        upper = theValues[len(theValues)/2]
        return (float(lower + upper)) / 2
            
    def _mean(self, numericValues):
        summed = reduce(lambda x, y: x + y, numericValues)
        mean = summed / len(numericValues)
        return mean

    def __str__(self):
        styler = AnsiColors()
        keys = self.filteredResultsDicts[0].dictionary.keys()
        longestKey = max(map(lambda x: len(x), keys))
        rVal = '%s using the %s (%d runs)\n' % (styler.color('Combined results', 'green'), self.method, len(self.filteredResultsDicts))
        for k, v in self.combined.items():
            rVal += '%s  %s\n' % (k.ljust(longestKey), v)
        return rVal

class FilterResultsDictCombinorDiff:
    def __init__(self, filterResultsDictCombinorLeft, filterResultsDictCombinorRight):
        self.__dict__.update(locals())
        self.filteredResultsDicts = [filterResultsDictCombinorLeft, filterResultsDictCombinorRight]

    def diff2str(self, diff, styler):
      if diff < 0:
        return styler.color(str(diff), 'red')
      else:
        return styler.color('+' + str(diff), 'green')

    def __str__(self):
        styler = AnsiColors()
        columnWidth = 30
        keys = self.filteredResultsDicts[0].combined.keys()
        longestKey = max(map(lambda x: len(x), keys))
        testHashes = list(map(lambda x: x.getTestRunSignatures(), self.filteredResultsDicts))
        rVal = '%s  %s%s\n' % (''.ljust(longestKey), styler.color(''.join([x.ljust(columnWidth) for x in testHashes]), 'yellow'), styler.color('diff'.ljust(columnWidth), 'yellow') )
        for key in keys:
            values = list(map(lambda x: x.combined[key], self.filteredResultsDicts))
            diff = self.filterResultsDictCombinorRight.combined[key] - self.filterResultsDictCombinorLeft.combined[key]
            rVal += '%s  %s%s\n' % (key.ljust(longestKey), ''.join([str(x).ljust(columnWidth) for x in values]), self.diff2str(diff, styler).ljust(columnWidth))
        return rVal

class FilterResultsDictComparatorDiff:
    def __init__(self, filteredTestResultLeft, filteredTestResultRight):
        self.__dict__.update(locals())
        self.filteredResultsDicts = [filteredTestResultLeft, filteredTestResultRight]
    def diff2str(self, diff, styler):
      if diff < 0:
        return styler.color(str(diff), 'red')
      else:
        return styler.color('+' + str(diff), 'green')
    def __str__(self):
        styler = AnsiColors()
        columnWidth = 15
        keys = self.filteredResultsDicts[0].dictionary.keys()
        longestKey = max(map(lambda x: len(x), keys))
        testHashes = list(map(lambda x: '%s:%d' % (x.testResult.getSignature()[:8], x.run), self.filteredResultsDicts))
        rVal = '%s  %s%s\n' % (''.ljust(longestKey), styler.color(''.join([x.ljust(columnWidth) for x in testHashes]), 'yellow'), styler.color('diff'.ljust(columnWidth), 'yellow') )
        for key in keys:
            values = list(map(lambda x: x.dictionary[key], self.filteredResultsDicts))
            diff = self.filteredTestResultRight.dictionary[key] - self.filteredTestResultLeft.dictionary[key]
            rVal += '%s  %s%s\n' % (key.ljust(longestKey), ''.join([str(x).ljust(columnWidth) for x in values]), self.diff2str(diff, styler).ljust(columnWidth))
        return rVal

class Factory:
    filterMap = {
        'fv_count': {
            'class': FirstViewCountFilter,
            'type': 'aggregate',
            'description': "Time to load, # of assets and their sizes (first view)"
        },
        'rv_count': {
            'class': RepeatViewCountFilter,
            'type': 'aggregate',
            'description': "Time to load, # of assets and their sizes (repeat view)"
        },
        'fv_url_and_ttl': {
            'class': UrlTimeToLoadFilter,
            'type': 'normal',
            'description': "Time to load for each resource (first view)"
        },
        'fv_url_and_ttfb': {
            'class': UrlTimeToFirstByteFilter,
            'type': 'normal',
            'description': "Time to first byte for each resource (first view)"
        },
        'fv_start_end_time': {
            'class': StartAndEndTimeFilter,
            'type': 'normal',
            'description': "Start time and end time for each resource (first view)"
        }
    }

    def create(self, name):
        return self.filterMap[name]['class']()
