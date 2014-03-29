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
from defs import *
from lexer import vcb
import serializer
from seqmap import SeqMap,scToStr,srSeqToStr
from xfrm import *

"""
This code performs phrase reductions. At this point the parse graph
consists of a linked list of parse nodes (class "Pn"), representing
words and punctuation. Each node has a "sc" (syntax class) attribute:
this is our generalization of part-of-speach. In reduction, we replace
short sequences of nodes with a single node, so simple phrases like
"the girl" and "didn't go" are parsed as units.

A reduction rule maps a sequence of "sc" values to a value
[offS,offE,vprops,sc,action]. We walk the graph until we see a node 
sequence whose sc values match the sc sequence of some rule "r". 
We then perform "action" on the nodes. "offS" and "offE" specify
which which of the nodes in the sequence are affected: offS == 1
means "exclude first node", offE == 2 means "exclude the last 2
nodes", etc.

Supported actions are:
reduce -- remove nodes from graph & replace with a new node
setprops -- set props of nodes

"""
# dev/test
traceRules = False

def isVQual(e):
    """ can "e" be a verb-qualifier? """
    return e is not None and \
        e.isVerb() and \
        not e.testVRoot(['be','have','do','will','shall'])

def reduceTerms(S,E,vprops,sc):
    """ reduce a phrase, S..E. """
    # If this is not a verb phrase reduction, just call graph's
    # reduction method
    if not vcb.isScForVerb(sc):
        return pg.reduceTerms(S,E,vprops,sc)
    # get list of verb terms S..E (skip modfiers). Catch negations
    # ("have not seen")
    terms = []
    e = S
    while e is not None:
        # catch negative forms
        if len(e.wrds) > 0:
            sp = vcb.getSpelling(e.wrds[0]).lower()
            if sp == "not" or sp == "never":
                vprops |= VP_Neg
        if e.isVerb():
            terms.append(e)
        if e == E:
            break
        e = e.nxt
    # "vS" and "vE": first/last verb in list
    N = len(terms)
    vS = terms[0]
    vE = terms[N-1]
    # tense is derived from first term. Semantic props are inherited
    # from the last verb.
    vprops |= (vS.vprops & VP_tenseMask)
    vprops |= (vE.vprops & VP_semanticMask)
    # If this is the reduction of an atomic verb phrase, get
    # additional props from vS. Same story for conjuctions ("sing and
    # dancing", "ran and hid")
    if vprops & VP_Atomic:
        mask = VP_Gerund|VP_Root|VP_semanticMask
        vprops |= (vS.vprops & mask)
    # Setting this prop increases the accuracy of the parse in
    # a small number of very common cases.
    if S.prv is not None:
        test = vcb.getSpelling(S.prv.wrds[0]).lower()
        if test in ["i","we","he","she","they"]:
            vprops |= VP_ImmutableSub
    # compute the syntax-class. This is based on "vprops", plus facts
    # about the main verb. Default is "V"
    if vprops & VP_Inf:
        scSp = "Inf"
    elif vprops & VP_Gerund:
        scSp = "Ger"
    elif vprops & VP_Passive:
        scSp = "Pas"
    else:
        scSp = 'be' if vE.testVRoot('be') else 'V'
    sc = vcb.getScIx(scSp)
    # call the graph's reduction method
    R = pg.reduceTerms(S,E,vprops,sc)
    # last term gives the root verbs(s)
    R.verbs = vE.verbs[:]
    # some complex forms ("have gone") are purely syntactic; others
    # ("might go") are considered to represent a qualified form for a
    # verb, and we save the qualifier.
    for i in range(0,len(terms)):
        ex = terms[i]
        if len(ex.vqual) > 0:
            R.vqual.extend(ex.vqual)
        if ex != vE and isVQual(ex):
            R.vqual.append(ex.verbs[0])
    # Reduce "[was beginning][to understand]
    # TODO: comment
    left = R.prv
    if left is not None and \
        left.isVerb() and \
        left.testVerbForm(WP_VPQ):
        vprops = R.vprops & VP_semanticMask
        R = reduceTerms(left,R,vprops,vcb.getScIx('V'))    
    return R

class ReductXfrm(SeqMapXfrm):
    """
    Reduction transform. We make several passes over the graph,
    performing different kind of reductions. Each pass is implemented
    by a ReductXfrm.
    """

    # actions
    actReduce = 0x1
    actSetProp = 0x2
    
    def __init__(self,_name=''):
        SeqMapXfrm.__init__(self,_name)
        self.offS = []
        self.offE = []
        self.props = []
        self.sc = []
        self.act = []
        
    def vToStr(self,i):
            l = []
            if self.offS[i] != 0:
                l.append("offS: %d" % self.offS[i])
            if self.offE[i] != 0:
                l.append("offE: %d:" % self.offE[i])
            if self.props[i] != 0:
                l.append("props: %s" % VPtoStr(self.props[i],'|'))
            if self.sc[i] != 0:
                l.append("sc: %s" % vcb.getScSpelling(self.sc[i]))
            if self.act[i] != 0:
                l.append("act: %d" % self.act[i])
            return ' '.join(l)

    def printme(self,fp):
        fp.write('Xfrm "%s"\n' % self.name)
        self.rules.printme(fp,scToStr)
        for i in range(len(self.offS)):
            fp.write("d. %s\n" % (i, self.vToStr(i)))
    

    def serializeValues(self,mode):
        if mode == 'w':
            serializer.encodeIntLst(self.offS,8)
            serializer.encodeIntLst(self.offE,8)
            serializer.encodeIntLst(self.props,32)
            serializer.encodeIntLst(self.sc,8)
            serializer.encodeIntLst(self.act,8)
        else:
            self.offS = serializer.decodeIntLst(8)
            self.offE = serializer.decodeIntLst(8)
            self.props = serializer.decodeIntLst(32)
            self.sc = serializer.decodeIntLst(8)
            self.act = serializer.decodeIntLst(8)

    def applyRule(self,e,rule):
        seq,vix = rule
        S = seq[0]
        E = seq[len(seq)-1]
        if traceRules:
            l = [vcb.getScSpelling(0xff & e.sc) for e in seq]
            print "%s. reduce [%s] by  [%s]" % \
                (self.name, ' '.join(l), self.vToStr(vix))
        for i in range(0,self.offS[vix]):
            S = S.nxt
        for i in range(0,self.offE[vix]):
            E = E.prv
        if self.act[vix] == ReductXfrm.actReduce:
            R = reduceTerms(S,E,self.props[vix],self.sc[vix])
            return R.nxt
        if self.act[vix] == ReductXfrm.actSetProp:
            ex = S
            while True:
                ex.setVProp(self.props[vix])
                if ex == E:
                    break
                ex = ex.nxt
            return seq[len(seq)-1].nxt
        assert False

