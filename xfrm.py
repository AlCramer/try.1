# Copyright 2012 Al Cramer
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

import pg
import serializer
from seqmap import SeqMap,scToStr

# true-> write trace info to stdout
traceparse = False

class Xfrm():
    """
    An "Xfrm" encapsulates one or more rules that transform the graph.
    "doXfrm" walks the graph, calliing "findRule" on each node, until
    it reaches a node to which a rule applies. It then passes that
    node, plus the rule, to "applyRule". applyRule modifies the graph,
    and returns the node at which the walk is to resume.

    Some child classes may implement "postXfrm", called after the 
    walk.  If the rules take the form of data tables, the class will 
    implement "serialize".
    """
    def __init__(self,_name):
        self.name = _name

    def findRule(self,e):
        return None

    def applyRule(self,e,rule):
        return None

    def doXfrm(self):
        e = pg.eS
        while e != None:
            rule = self.findRule(e)
            if rule is not None:
                e = self.applyRule(e,rule)
            else:
                e = e.nxt
	self.postXfrm()
        if traceparse:
            pg.printme(None,self.name)
            print ''

    # optional: called after the walk
    def postXfrm(self):
        pass

    def serialize(self,mode):
	pass

    def printme(self,fp):
	pass

class SeqMapXfrm(Xfrm):
    """
    This transform uses a sequence map to represent
    a collection of rules. The value index of the sequence map
    is an index into a table of values.
    """
    def __init__(self,_name):
        Xfrm.__init__(self,_name)
	# the sequence map: maps an sc sequence to a index
	# into the value table.
        self.rules = SeqMap()

    def serializeValues(self,mode):
        pass

    def serialize(self,mode):
        if mode == 'w':
            serializer.encodeStr(self.name)
        else:
            self.name = serializer.decodeStr()
        self.rules.serialize(mode)
	self.serializeValues(mode)

    def findRule(self,e):
        matches = self.rules.getMatches(e,True)
        if len(matches) > 0:
            # want the longest match: the last element in the match
            # set.
            return matches[len(matches)-1]
        return None
	

