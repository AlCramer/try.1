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
import vcb
import lexer
import sys

"""
The parse graph ("pg") is the main data structure used in parsing.
After reading in the source text, we break it up into a sequence of
lexemes, each corresponding to a word or punctuation mark. Each lexeme
then becomes a node in the graph. This is a doubly linked list of "Pn"
nodes. Initially the graph is a 1-dimensional structure.

Parsing then becomes a matter of deciding: what short sequences of
words ("the girl", "didn't go") can be combined into a single node, to
form a single parse unit? And then: what are the syntax relations
between these parsemes? These tasks are handled by the module
"parser".
"""
# Nodes for parse graph

class Pn (Nd):
    """
    A "Pn" represents a punctuation mark, word, or short sequence of
    words ("the boy"), linked together in a doubly-linked list to
    represent the source text.
    """
    def __init__(self,tokV,S,E):
        Nd.__init__(self,S,E)
        # subnodes for reductions
        self.sublst = []
        # our scope
        self.scope = None
         # verb qualifiers
        self.vqual = []
        # verbs props
        self.vprops = 0
        # syntax class and relation.
        self.sc = 0
        self.sr = SR_undef
        # text associated with this node
        self.wrds = []
        # verb roots associated with this node
        self.verbs = []
        # preposition, etc. which precede this node
        self.head = []
        # syntax relations, verb->word
        self.rel = []
        # "vnxt" is first verb to our right, and "vprv" is
        # first verb to our left.
        self.vnxt = self.vprv = None
	# preceeding verb domain
	self.vd_left = None
        for i in range(0,SR_nWordToVerb):
            self.rel.append([])
        if tokV != -1:
            self.wrds.append(tokV)
            self.sc = self.computeSynClass(tokV)
            if vcb.isScForVerb(self.sc):
                self.verbs.append(vcb.getDef(tokV))
                self.vprops = self.computeVerbProps(tokV)
        # In general the "extent" of a node is just the node. But if
        # this is the verb in a verb expression, then its extent runs
        # from its left-most scope term to its right-most scope term.
        self.extent = [self,self]

    def computeSynClass(self,tokV):
        """ compute the "sc" value for a node """
        sp = vcb.getSpelling(tokV)
        c = sp[0]
        if c == ',':
            return vcb.getScIx("Comma")
        if not (c.isalnum() or c=="_" or c=='\''):
            return vcb.getScIx("Punct")
        # a vocabulary word
        return vcb.synClass[tokV]

    def computeVerbProps(self,tok):
        """ get verb props (VP_xxx) for a parse node """
        p = 0
        if vcb.checkProp(tok,WP_ROOT):
            p |= VP_Root
        elif vcb.checkProp(tok,WP_VNEG_CONTRACTION):
            p |= VP_Neg
        if  vcb.checkProp(tok,WP_PAST|WP_PARTICIPLE):
            p |= VP_Past
        else:
            p |= VP_Present
        if vcb.checkProp(tok,WP_GERUND):
            p |= VP_Gerund
        if vcb.checkProp(tok,WP_VADJ):
            p |= VP_Adj
        # remaining verb props are based on the root of the verb. This
        # is given by its definition.
        tokDef = vcb.getDef(tok)
        if vcb.checkProp(tokDef,WP_VPQ):
            p |= VP_Prelude
        return p

    def getWrd(self,i):
        """ get wrd "i" """
        return self.wrds[i]
    
    def testWrd(self,sp):
        """
        Does node match a word? If > 1 word, the test
        is performed on the first word.
        """
        if len(self.wrds)>0:
            _def = vcb.getDef(self.getWrd(0))
            spDef = vcb.getSpelling(_def)
            if isinstance(sp,list):
                for _sp in sp:
                    if spDef == _sp:
                        return True
                return False
            return spDef == sp
        return False

    def setVProp(self,v):
        """ set a prop """
        self.vprops |= v

    def checkVProp(self,m):
        """ check verb props """
        return (self.vprops & m) != 0

    def checkWrdProp(self,m):
        """ check word props """
        if len(self.wrds) > 0:
            return vcb.checkProp(self.wrds[0],m)
        return False

    def getVRoot(self):
        """ get root form for verb """
        return 0 if len(self.verbs) == 0 else self.verbs[0]

    def testVRoot(self,spTest):
        """ test verb-root against spelling """
        if len(self.verbs) > 0:
            spRoot = vcb.getSpelling(self.getVRoot())
            if isinstance(spTest,list):
                for sp in spTest:
                    if sp == spRoot:
                        return True
            elif spRoot == spTest:
                return True
        return False

    def testVerbForm(self,form):
        """
        Test form of verb. "form" can be:
        WP_AVGT,WP_EVT,WP_AVE,WP_VPQ
        """
        return len(self.verbs)>0 and \
            vcb.checkProp(self.verbs[0],form)
    
    def isVerb(self):
        """ is this a verb? """
        return vcb.isScForVerb(self.sc)

    def isLeaf(self):
        """ is this a leaf? (no descendents) """
        for lst in self.rel:
            if len(lst) > 0:
                return False
        return True

    def linearize(self,leaves):
        """ append leaves to "leaves" """
        if len(self.sublst) == 0:
            leaves.append(self)
            return
        for e in self.sublst:
            e.linearize(leaves)

    def checkSc(self,m):
        """ check sc props """
        return vcb.scDct.checkProp(self.sc,m)

    def getRel(self,e):
        """ find relation of "e" to this node """
        for i in range(SR_nWordToVerb):
            if e in self.rel[i]:
                return i
        return -1

    def unsetScope(self):
        """
        Unset scope for "e". This erases any existing relations from
        verbs to e.
        """
        if self.scope != None:
            for rset in self.scope.rel:
                if self in rset:
                    rset.remove(self)
                    break
        self.scope = None
        self.sr = SR_undef

    def setScope(self,v,i):
        """
        Set an edge from "v" to "e". "None" is a legal value for "v"
        -- this just unsets any "i" relations to e
        """
        # setting scope to self is illegal
        assert self != v
        # for all our relations, setting v->x erases any existing
        # relations vold->x. If "x" is currently in some relation with
        # "vold", then "vold" is given by "e.scope"
        self.unsetScope()
        if v != None:
            # we order the terms left-to-right by "e.S"
            ix = -1
            rset = v.rel[i]
            for j in range(0,len(rset)):
                if self.S <= rset[j].S:
                    ix = j
                    break
            if ix == -1:
                rset.append(self)
            else:
                rset.insert(ix,self)
            self.scope = v
            self.sr = i

    def resetRel(self,oldRel,newRel):
        """ reset a relation """
        self.rel[newRel] = self.rel[oldRel]
        self.rel[oldRel] = []
        for t in self.rel[newRel]:
            t.sr = newRel
            
    def dumpNdLst(self,label,lst):
        """ return a list of "h" (handles) for a list of nodes """
        l = [str(e.h) for e in lst]
        l = ','.join(l)
        return ' %s:%s' % (label,l)

    def dumpAttr(self):
        tmp = [('%d. [%d.%d]' % (self.h,self.S,self.E))]
        if len(self.wrds) > 0:
            tmp.append('"%s"' % vcb.spellWrds(self.wrds))
        if len(self.head) > 0:
            tmp.append('head: "%s"' % vcb.spellWrds(self.head))
        if self.vprops != 0:
            tmp.append('VP:' + VPtoStr(self.vprops,'|'))
        if self.sc < vcb.getScN():
            tmp.append('sc:' + vcb.getScSpelling(self.sc))
        else:
            tmp.append('sc:' + str(self.sc))
        tmp.append('sr:' + SRids[self.sr])
        if self.scope != None:
            tmp.append("Scp:" + str(self.scope.h))
        return ' '.join(tmp)

    def printme(self,fp,depth):
        """
        print node. depth == -1 means: don't recurse
        """
	if fp is None:
	    fp = sys.stdout
        if depth == -1:
            fp.write(self.dumpAttr())
            for i in range(0,SR_nWordToVerb):
                if len(self.rel[i]) > 0:
                    fp.write(self.dumpNdLst(SRids[i],self.rel[i]))
	    fp.write('\n')
            return
        indent = ''
        for i in range(depth):
            indent += '  '
        print indent + self.dumpAttr()
        for i in range(0,SR_nWordToVerb):
            if len(self.rel[i]) > 0:
                fp.write('%s%s' % (indent + '  ', SRids[i]))
                for e in self.rel[i]:
                    e.printme(fp,depth+1)

# phrase factory. Do not inline this code -- you will break the tools
# that build the parse tables.
pnEnum = 0
def pnFactory(tokV,S,E):
    """ create phrase with given props """
    global pnEnum
    e = Pn(tokV,S,E)
    e.h = pnEnum
    pnEnum += 1
    return e
# first phr in sequence
eS = None
# last phr in sequence
eE = None

def resetSpan(S,E):
    """ reset span of graph, returning restore info """
    global eS,eE
    rinfo = []
    rinfo.append(S.prv)
    rinfo.append(E.nxt)
    rinfo.append(eS)
    rinfo.append(eE)
    eS = S
    eE = E
    eS.prv = None
    eE.nxt = None
    return rinfo

def restoreSpan(rinfo):
    """ restore span of graph, using info from "rinfo" """
    global eS,eE
    eS.prv = rinfo[0]
    eE.nxt = rinfo[1]
    eS = rinfo[2]
    eE = rinfo[3]

def printme(fp=None,title=None):
    """ print the graph """
    if fp is None:
        fp = sys.stdout
    if title != None:
        fp.write(title+'\n')
    e = eS
    while e != None:
        e.printme(fp,-1)
        e = e.nxt

def buildGraph(parseblk):
    """
    build parse graph for source text in the region specified by
    "parseblk"
    """
    global pnEnum, eS, eE, nToks
    # tokenize the text
    (toks,tokLoc) = lexer.lex(parseblk)
    pnEnum = 0
    eS = eE = None
    for i in range(0,len(toks)):
        # The span of a node gives start and end index of the region
        # in the source text spanned by e.
        ixS = tokLoc[i]
        sp = vcb.getSpelling(toks[i])
        e = pnFactory(toks[i], ixS, ixS+len(sp)-1)
        # linked-list bookkeeping
        if eS == None:
            eS = eE = e
        else:
            Pn.connect(eE,e)
            eE = e

def removeNode(e):
    """ remove a node from the graph """
    global eS, eE
    if e == eS and e == eE:
        eS = eE = None
    elif e == eS:
        eS = e.nxt
    elif e == eE:
        eE = e.prv
    Pn.connect(e.prv,e.nxt)

def reduceTerms(S,E,vprops,sc):
    """
    replace nodes S..E with a single node, "R". S..E become the
    sublist of R. R's "wrds" attribute is the concatenation of the
    words for S..E. if R is a verb expression, its "verbs" attribute
    is derived likewise from S..E
    """
    global eS, eE
    R = pnFactory(-1,S.S,E.E)
    R.vprops = vprops
    R.sc = sc
    # words for the reduction is the concatenation of the words for
    # eS..eE
    e = S
    while True:
        R.sublst.append(e)
        R.wrds.extend(e.wrds)
        R.verbs.extend(e.verbs)
        if e == E:
            break
        e = e.nxt
    if not vcb.isScForVerb(sc):
        # kill the verbs
        R.verbs = []
    # insert R into the region S..E
    left = S.prv
    right = E.nxt
    Pn.connect(left,R)
    Pn.connect(R,right)
    if R.prv == None:
        eS = R
    if R.nxt == None:
        eE = R
    return R

def getRootNodes():
    """
    Walk the graph and get all "root" nodes: these are nodes with null
    scope.
    """
    global eS
    rootNds = []
    e = eS
    while e != None:
        if e.scope == None:
            rootNds.append(e)
        e = e.nxt
    return rootNds

def validateRel():
    """
    Clear the "rel" attributes of nodes, then recompute using scope
    and sr attributes.
    """
    # clear any currently defined relations
    e = eS
    while e != None:
        for lst in e.rel:
            del lst[:]
        e = e.nxt
    # rebuild using scope and sr attributes
    e = eS
    while e != None:
        if e.scope is not None and e.sr < SR_nWordToVerb:
            e.scope.rel[e.sr].append(e)
        e = e.nxt

def validateSpan():
    """
    Validate the "span" attribute of nodes: if "e" is in the scope of
    "ex", increase ex's span as needed to include e.
    """
    e = eS
    while e != None:
        ex = e.scope
        # Walk up the scope tree.
        while ex is not None:
            if ex.isVerb():
                if e.S < ex.S:
                    ex.S = e.S
                if e.E > ex.E:
                    ex.E = e.E
            ex = ex.scope
        e = e.nxt

def walk(func):
    """
    Walk the graph, calling "func" on each node. func returns
    the next node in the walk
    """
    e = eS
    while e != None:
        e = func(e)
