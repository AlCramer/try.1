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

import pg
from defs import *
from msnode import *
import lexer
from lexer import vcb
import serializer
from parseReduct import ReductXfrm
from parseSr import *
import xfrm
import os
import sys

"""
"buildGraph" in module "Pg" constructs our initial parse graph: a
doubly-linked list of nodes representing individual words. Parsing
then procedes in 2 phases: reduction, and syntax relations. In
reduction, we replace short sequences of nodes with a single node, so
simple phrases like "the girl" and "didn't go" are parsed as units. In
syntax relations, we walk the top-level nodes of the graph and
recognize syntax relations between nodes.

Both phases are implemented using "Xfrms". A transform implements
one or more rules. It walks the graph until it finds one or more
nodes to which a rule applies. It then passes the nodes (and/or rule)
over to its "applyRule" method, which makes some modification to the
graph and returns the node at which the walk is to resume.

After the parse graph is fully defined, we have a full and complete
representation of the parse. But parse graph nodes ill suited to an
API, plus they consume a lot of memory. So the final step is to do a
top down walk of the parse graph, constructing a new and simplified
version of the parse using nodes of type MSNode.
"""

# version info
version = "1.0"
def serializeVersion(mode):
    global version
    if mode == 'r':
        version,vcb.version = serializer.decodeStr().split(' ')
    else:
        serializer.encodeStr("%s %s" % (version,vcb.version))
    
# test/dev option
def setTraceParse(enable):
    xfrm.traceparse = enable

""" Values for "kind" and "form" attributes of MSNode's. """
# kinds top-level nodes
MSND_Punct = "punct"
MSND_Quote = "quote"
MSND_Paren = "paren"
MSND_Assert = "assert"
MSND_Query = "query"
MSND_Imper = "imperative"
MSND_Phr = "phr"
# forms leaf nodes
MSND_X = "X"
MSND_Mod = "mod"
MSND_N = "N"
MSND_ConjWrd = "conj"
# clauses (interior nodes)
MSND_VerbClause = "verbclause"
MSND_QueryClause = "queryclause"
MSND_Action = "action"

# the transforms
xfrms = []
xfrms.append(ReductXfrm('initReduct'))
xfrms.append(ReductXfrm('vReduct'))
xfrms.append(ReductXfrm('detReduct'))
xfrms.append(ReductXfrm('conjReduct'))
xfrms.append(ReductXfrm('actReduct'))
xfrms.append(ScSeqToSrXfrm('leftVdomXfrm'))
xfrms.append(SrXfrm('srXfrm'))
xfrms.append(RoleXfrm('roleXfrm'))
xfrms.append(SvToQXfrm('svToQXfrm'))
xfrms.append(InvertQXfrm('invertQXfrm'))
xfrms.append(VconjXfrm('vconjXfrm'))

def getXfrm(name):
    """ get xfrm given name """
    for x in xfrms:
        if x.name == name:
            return x
    return None

def serialize(mode):
    """ read/write the parser (and vocabulary) """
    serializeVersion(mode)
    vcb.serialize(mode)    
    for x in xfrms:
        x.serialize(mode)

def printme(fp):
    """ print parser rules """
    if fp is None:
        fp = sys.stdout
    for x in xfrms:
        x.printme(fp)

def parseText(src,srclno):
    """
    Main entry point for parsing. Parse source text represented as a
    string. "srclno" is used to generate location info: if "src" is an
    extract from some larger text, srclno should be the line number at
    which the extract starts.
    """
    return parseBlkLst(lexer.getParseBlks(src,srclno),None)

def parseBlkLst(blkLst,parent):
    """ parse a list of blocks """
    nds = []
    for blk in blkLst:
        if blk.sublst != None:
            # A quote or parenthesized text. Get content, and surround
            # wth appropriate container.
            opener = lexer.src[blk.S-1]
            if opener == '"' or opener == '\'':
                kind = MSND_Quote
            else:
                kind = MSND_Paren
            nd = MSNode(kind,'','',parent)
            nds.append(nd)
            nd.subnodes = parseBlkLst(blk.sublst,nd)
        else:
            pg.buildGraph(blk)
            # parse it
            parseGraph()
            # create parse node sequence from the graph and add to "nds"
            nds.extend(getParseNodes(pg.getRootNodes(),'',parent))
    return nds

def parseGraph():
    """ parse the graph """
    if xfrm.traceparse:
        pg.printme(None,"initial graph")
    for x in xfrms:
        try:
            x.doXfrm()
        except ParseErr:
            # if an xfrm throws an exception, we just continue on
            # to the next. The try/except mechanism is needed by the
            # tools that build the parse tables.
            pass
    # reduce sr clauses
    reduceSrClause(pg.getRootNodes());

def reduceSrClause(lst):
    """
    transform an "srClause": sequence of nodes, where all the nodes
    share the same scope and syntax-relation to that scope.
    """
    if len(lst) == 0:
        return
    # recurse thru child clauses
    for e in lst:
        for srClause in e.rel:
            reduceSrClause(srClause)
    # merge sequences of prep's
    prepMask = WP_PREP|WP_QUALPREP|WP_CLPREP
    l1 = [lst[0]]
    for e in lst[1:]:
        last = l1[len(l1)-1]
        if last.checkSc(prepMask) and \
            e.checkSc(prepMask) and \
            e.isLeaf():
            last.wrds.extend(e.wrds)
            last.E = e.E
            pg.removeNode(e)
            continue
        l1.append(e)
    # rewrite l1 to "lst", merging word sequences
    del lst[:]
    i = 0
    while i < len(l1):
        e = l1[i]
        i += 1
        if e.checkSc(WP_PUNCT):
            lst.append(e)
            continue
        # "e" is a word. It starts a phrase (which may consist solely
        # of this word).
        S = e
        if S.checkSc(prepMask):
            # bind this to the word that follows (if there is a word)
            if i<len(l1) and not l1[i].checkSc(WP_PUNCT):
                l1[i].head.extend(S.wrds)
                pg.removeNode(S)
                S = l1[i]
                i += 1
        # "i" is at term that follows S. If S is a leaf, merge any
        # leaves that follow.
        if S.isLeaf():
            while i<len(l1):
                if l1[i].checkSc(WP_PUNCT) or not l1[i].isLeaf():
                    break
                S.wrds.extend(l1[i].wrds)
                pg.removeNode(l1[i])
                i += 1
        # add S to the lst
        lst.append(S)

def getMSNodeKind(e,form):
    """ get the "kind" attribute for a parse node """
    if e.checkSc(WP_PUNCT):
        return MSND_Punct
    if form == MSND_QueryClause or \
        form == MSND_Query:
        return MSND_Query
    if e.isVerb():
        sub = []
        sub.extend(e.rel[SR_agent])
        sub.extend(e.rel[SR_topic])
        sub.extend(e.rel[SR_exper])
        if len(sub) > 0:
            # something is in a subject role.
            if sub[0].checkSc(WP_QUERY):
                return MSND_Query
            if len(e.rel[SR_vAdj]) > 0 and \
                e.rel[SR_vAdj][0].testVRoot("let"):
                return MSND_Imper
            if not e.checkVProp(VP_Gerund):
                return MSND_Assert
        elif e.checkVProp(VP_Root):
            return MSND_Imper
        elif e.checkVProp(VP_Passive) and \
            len(e.rel[SR_theme]) > 0:
            return MSND_Assert
    # default is "MSND_Phr"
    return MSND_Phr

def getMSNodeForm(e):
    """ get the "form" attribute for a parse node """
    if e.checkSc(WP_PUNCT):
        return ""
    if e.isVerb():
        # "sub": set of terms in subject clause
        sub = []
        sub.extend(e.rel[SR_agent])
        sub.extend(e.rel[SR_topic])
        sub.extend(e.rel[SR_exper])
        if len(sub) == 0:
            if e.checkVProp(VP_Gerund|VP_Inf|VP_Root):
                return MSND_Action
        elif len(e.rel[SR_vAdj]) > 0:
            # "did he go": in general a query. But "where can you go"
            # translates as a verb clause.
            if e.sr == SR_modifies:
                return MSND_VerbClause
            return MSND_QueryClause
        elif e.E < sub[0].S and not e.checkVProp(VP_Passive):
            # "is she here", "did he?", "have you the time?"
            return MSND_QueryClause
        # default is "verb-clause"
        return MSND_VerbClause
    if len(e.wrds) == 1:
        # a word. Default is "X", but look for useful cases.
        wrd = e.getWrd(0)
        if vcb.checkProp(wrd,WP_QUERY):
            return MSND_Query
        if vcb.checkProp(wrd,WP_N):
            return MSND_N
        if vcb.checkProp(wrd,WP_CONJ):
            return MSND_ConjWrd
        if vcb.checkProp(wrd,WP_MOD):
            return MSND_Mod
        # use default
        return MSND_X
    # a phrase. possessive? ("John's cat")
    possContract = vcb.lkup("'s",False)
    if possContract in e.wrds:
        return MSND_N
    # compound modifier? ("very happy", "sad and miserable")
    isMod = True
    for wrd in e.wrds:
        if not vcb.checkProp(wrd,WP_MOD|WP_CONJ):
            isMod = False
            break
    if isMod:
        return MSND_Mod
    # remaining tests based on first word
    wrd = e.getWrd(0)
    if vcb.checkProp(wrd,WP_QUERY):
        return MSND_Query
    if vcb.checkProp(wrd,WP_DETS|WP_DETW):
        return MSND_N
    # default
    return MSND_Phr

def getParseNodes(lst,relToParent,parent):
    """
    This method accepts a list of graph nodes, and returns a
    corresponding list of parse nodes.
    """
    nds = []
    for e in lst:
        # create a parse node and add to "nds".
        form = getMSNodeForm(e)
        kind = getMSNodeKind(e,form) if relToParent == '' else relToParent
        text = lexer.src[e.S:e.E+1] if e.isVerb() \
            else vcb.spellWrds(e.wrds)
        nd = MSNode(kind,form,text,parent)
        nds.append(nd)
        for i in range(SR_nWordToVerb):
            if i == SR_isQby or \
                i==SR_vconj or i==SR_undef or i==SR_vAdj:
                # these are computational: skip
                continue
            nd.subnodes.extend(getParseNodes(e.rel[i],SRids[i],nd))
        if len(e.head)>0:
            nd.head = vcb.spellWrds(e.head)
        if len(e.verbs)>0:
            nd.vroots = vcb.spellWrds(e.verbs)
        if len(e.vqual)>0:
            nd.vqual = vcb.spellWrds(e.vqual)
        if e.vprops != 0:
            if form != MSND_Action:
                mask = VP_tenseMask | VP_Neg | VP_Perfect
                nd.vprops = VPtoStr(e.vprops & mask,' ')
        locS = e.S
        locE = e.E
        nd.lineS = lexer.lnoMap[locS]
        nd.colS = lexer.colMap[locS]
        nd.lineE = lexer.lnoMap[locE]
        nd.colE = lexer.colMap[locE]
    return nds
