# Copyright 2011 Al Cramer
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from defs import *
import parser
import vcb
import serializer
import re
import sys
import os
import cProfile

"""
Main script for the msparse package. To parse source text represented
as a string, use "parseString". To parse the entire contents of a file,
use "parseFile". To parse and process the contents of a very large
file use "processFile".
"""

# read the serialized vocabulary and grammar rules in "msp.dat".
# This code expects the file to reside in the same directory
# as this file.
try:
    serializer.init('msp.dat','r')
    parser.serialize('r')
    serializer.fini()
except:
    print "could not read initialization file \"msp.dat\""
    print "Exception: %s\n" % sys.exc_info()[0]
    sys.exit(1)

def parseString(text):
    """
    Parse input string. Returns list of parse nodes. 
    """
    return parser.parseText(text.replace('\r',''),0)

def parseFile(fn):
    """
    Parse input file. Returns list of parse nodes. 
    """
    return __readAndParseFile(fn)

def processFile(fn,delegate=None,maxlines=-1):
    """
    Read and parse the file "fn" in sections, passing the parse
    of each section over to a delegate for processing. "maxlines"
    determines the size of the sections: if a given section
    exceeds "maxlines", we continue reading and parsing until
    we hit a blank or indented line, then declare the section
    complete and parse it. The object here is to support the
    processing of very large files, without blowing the host
    memory resources.
    """
    __readAndParseFile(fn,delegate,maxlines)


def __readAndParseFile(fn,delegate=None,maxlines=-1):
    """
    Read and parse a file. If "delegate" is None, we
    return a list of parse nodes giving the parse of the
    file. If delegate is defined, we read and
    parse the file in sections, passing the parse of each
    section over to the delegate for processing. 
    This function is private to this module. It implements the
    public functions "parseFile" and "processFile"
    """
    fp = open(fn,'r')
    li = fp.readline();
    lno = 1
    if len(li) == 0:
        return []
    # The parse is a list of parse nodes
    nds = []
    # we parse in sections. This is line number of the
    # current section.
    sectionlno = 1
    while len(li) != 0:
        # read a chunk of source. A chunk is ended by an empty
        # or indented line, or by eof. Track number of blank lines
        # preceeding the section and indentation for first line in
        # the section.
        src = []
        srclno = lno
        nblanks = 0
        srcindent = 0
        # This loop builds the chunk
        while True:
            if len(li) == 0:
                # empty line terminates a chunk
                break
            li = li.replace('\r','')
            # compute the indent of this line
            indent = 0
            for c in li:
                if c == ' ':
                    ident += 1
                elif c == '\t':
                    ident += 4
                else:
                    break
            if len(li.strip()) == 0:
                if len(src) > 0:
                    # blank line terminates the current section
                    break
                else:
                    nblanks += 1
                    li = fp.readline();
                    lno += 1
                    continue
            elif indent > srcindent:
                if len(src) > 0:
                    # indented line terminates the current section
                    break
            # build src
            if len(src) == 0:
                srcindent = indent
            src.append(li)
            li = fp.readline();
            lno += 1
        # parse the source: we get a list of parse nodes.
        # srcnds = parser.parseText(''.join(src),srclno,nblanks)
        srcnds = parser.parseText(''.join(src),srclno+nblanks)
        if len(srcnds) > 0 and nblanks >0:
            srcnds[0].blank = nblanks
        nds.extend(srcnds)
        if delegate is not None and \
            lno - sectionlno > maxlines:
            # process the nodes, then start a new section
            delegate(nds)
            sectionlno = lno
            nds = []
    fp.close()
    return nds

def toXml(nds,loc):
    """
    Convert a list of parse nodes into XML. "loc" is a boolean:
    True means include location attributes in the xml,
    """
    xml = ["<?xml version=\"1.0\" standalone=\"yes\"?>\n"]
    xml.append("<msp>\n")
    for nd in nds:
        xml.append(nd.toXml(loc))
        xml.append('\n')
    xml.append("</msp>\n");
    return ''.join(xml)
    
def mspTest():
    """
    Test harness for msparse package. 
    """
    # option: do we show location info in the xml?
    showloc = False
    # usage msg.
    usage = \
    """
Usage:
python msp.py options* [-i] [-f inFile outFile]

"-i" means loop interactively, displaying the parse
for text entered by the user.

"-f" means parse contents of the file "inFile", writing
the results to "outFile" as XML.

options:
    -loc: include source locations attributes in xml nodes
    -trace: trace the parse (dev/test)

    """
    # process args
    # Undocumented args are:
    # -printrules : print parse rules
    # -process inFile outFile : dev test for process file
    action = ''
    fnIn = None
    fnOut = None
    if len(sys.argv) == 1:
        print usage
        sys.exit(1)
    i =1
    while i<len(sys.argv):  
        a = sys.argv[i]
        if a == '-h' or a == '-help' or a == '-0':
            print usage
            sys.exit(1)
        if a == '-printrules':
            parser.printme(None)
            sys.exit(1)
        if a == '-loc':
            showloc = True
        elif a == '-trace':
            parser.setTraceParse(True)
        elif a == '-f' or a == '-process':
            action = a
            i += 1
            if i+1 >= len(sys.argv):
                print 'Error: expected file names'
                print usage
                sys.exit(1)
            fnIn = sys.argv[i]
            i += 1
            fnOut = sys.argv[i]
        elif a == '-i':
            action = a
        else:
            print 'unknown option: ' + a
            print usage
            sys.exit(1)
	i += 1
    if action == '':
        print usage
        sys.exit(1)
    if action == '-f' or action == '-process':
        fp = open(fnOut,'w')
        if action == '-f':
            fp.write(toXml(parseFile(fnIn),showloc))
        else:
            def processParse(nds):
                for nd in nds:
                    if nd.getSubnode("exper") != None:
                        fp.write(nd.text + '\n')
                        fp.write(nd.summary() + '\n')
            processFile(fnIn,processParse,2)
        print 'Created %s' % fnOut
        sys.exit(1)
    # Interactive mode
    print 'Enter text ("q" to quit):'
    while True:
        src = raw_input()
        if src == 'q' or src == 'quit':
            break
        print toXml(parseString(src),showloc)

if __name__== '__main__':
    mspTest()
