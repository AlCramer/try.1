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
import lexer
from lexer import vcb
import serializer
from seqmap import SeqMap,scToStr,srSeqToStr
from parseRoles import RoleXfrm
from xfrm import *
import vdom
import os
import sys

"""
This module defines transforms the establish syntax relations.
"""

class ScSeqToSrXfrm(SeqMapXfrm):
    """
    This transform using the mapping (scSeq->srSeq) to set 
    syntax relations between nodes.
    """
    def __init__(self,_name=''):
        SeqMapXfrm.__init__(self,_name)
        self.srSeq = []
        
    def vToStr(self,i):
        return "srSeq: %s" % srSeqToStr(self.srSeq[i])
    
    def printme(self,fp):
        fp.write('Xfrm "%s"\n' % self.name)
        self.rules.printme(fp,scToStr,srSeqToStr)
        for i in range(len(self.srSeq)):
            fp.write("d. %s\n" % (i, self.vToStr(i)))

    def serializeValues(self,mode):
        if mode == 'w':
            serializer.encodeLstLst(self.srSeq,8)
        else:
            self.srSeq = serializer.decodeLstLst(8)

    def applyRule(self,e,rule):
        ndSeq,vix = rule
        srSeq = self.srSeq[vix]
        # For each ndSeq[i], the corresponding element srSeq[i] gives
        # syntax-relation and scope, encoded into an 8-bit value.
        for i in range(0,len(ndSeq)):
            e = ndSeq[i]
            # low 4 bits give the syntax-relation value;
	    # hi 4 bits gives offset to the verb
	    offset = 0xf & (srSeq[i] >> 4)
	    assert i+offset < len(ndSeq)
	    if offset != 0:
		e.setScope(ndSeq[i+offset],0xf & srSeq[i])
        # resume walk at the successor to the last node covered by
        # the rule. 
        return ndSeq[len(ndSeq)-1].nxt
    
class SrXfrm(Xfrm):
    """
    Establish syntax relations. Thematic roles are set
    later by "RoleXfrm".
    """
    def __init__(self,_name=''):
        Xfrm.__init__(self,_name)
        
    def canExtendComplex(self,e):
        """
        helper for findRule: can e extend a verb complex?
        """
        if e is None or e.checkSc(WP_PUNCT):
            return False
        # In general a conjunction ends the entangled region;
        # but not if joins an action ("and see what was there")
        if e.checkSc(WP_CONJ):
            nxt = e.nxt
            if nxt is not None and nxt.isVerb() and \
                len(nxt.rel[SR_agent]) == 0 and \
                len(nxt.rel[SR_isQby]) == 0:
                return True
            else:
                return False
        return True

    def findRule(self,e):
        if e.checkSc(WP_PUNCT|WP_CONJ):
            return None
        sawVerb = False
        ex = e
        while ex is not None:
            if ex.isVerb():
                sawVerb = True
            if not self.canExtendComplex(ex.nxt):
                break
            ex = ex.nxt
        if sawVerb:
            return [e,ex]
        return None
    
    def applyRule(self,e,rule):
        # rule is [S,E] defining a sub-region of the graph.
        # This is a verb complex: a sequence of one or more
        # verb domains, preceeded by a set of prelude nodes.
        S,E = rule
        savePg = pg.resetSpan(S,E)
        # Q and sub relations have been set.
        # Any remaining non-verb, un-scoped terms are assigned an
        # object relation to the closest preceeding verb
        scope = None
        ex = S
        while True:
            if ex.isVerb():
                scope = ex
            elif ex.scope is None and \
                scope is not None:
                ex.setScope(scope,SR_theme)
            if ex == E:
                break
            ex = ex.nxt
        vdom.parse()
        pg.restoreSpan(savePg)
	return E.nxt

class SvToQXfrm(Xfrm):
    """
    Context dependent transform of subject-verb to qualified
    expression.
    """

    def inSubRole(self,e):
        """ Can "e" be in a subject role? """
        return e.sr == SR_agent or \
             e.sr == SR_exper or \
             e.sr == SR_topic

    def findRule(self,e):
        """ Returns verb node to be transformed """
        if e.checkVProp(VP_Gerund):
            if self.inSubRole(e):
                # "the girl sitting there" in subject role
                return e
            elif e.sr == SR_theme or e.sr == SR_auxTheme:
                if len(e.scope.rel[SR_theme]) > 0 and \
                    len(e.scope.rel[SR_auxTheme]) > 0:
                    # We're an object term in AGVT context: "I gave
                    # the guy sitting there an apple".
                    return e
        elif vcb.checkScProp(e.sc, WP_QUERY) and \
            self.inSubRole(e) and \
            len(e.scope.rel[SR_isQby]) == 0:
            # "who ate the cake".
            return e.scope
        return None

    def applyRule(self,e,rule):
        # "rule" is verb node to be transformed
        v = rule
        if len(v.rel[SR_agent]) > 0:
            v.resetRel(SR_agent,SR_isQby)
        elif len(v.rel[SR_exper]) > 0:
            v.resetRel(SR_exper,SR_isQby)
        elif len(v.rel[SR_topic]) > 0:
            v.resetRel(SR_topic,SR_isQby)
        return v.nxt

    def postXfrm(self):
        pg.validateRel()

class InvertQXfrm(Xfrm):
    """
    Invert Q expressions. Given "the girl you saw", [the girl] gets
    the (sr,scope) attributes of the verb, and the verb becomes a
    modifier of [the girl].
    """

    def findRule(self,e):
        """ Returns node to be transformed into a qualified node """
        if e.sr == SR_isQby:
            return e
        return None

    def applyRule(self,e,rule):
        # rule is the node to be qualified
        q = rule
        v = q.scope
        q.scope = v.scope
        q.sr = v.sr
        v.sr = SR_modifies
        v.scope = q
        return q.nxt

    def postXfrm(self):
        pg.validateRel()
        # the domain of verb expressions has now been defined: set the
        # spans accordingly.
        pg.validateSpan()
    
class VconjXfrm(Xfrm):
    """ Verb conjunction transform """
    
    def findRule(self,e):
        """ Returns node to be transformed """
        if e.sr == SR_vconj:
            return e
        return None

    def applyRule(self,e,rule):
        # rule is the node to be transformed
        peer = e.scope
        scope = peer.scope
        # e is given same scope, syntax role, and relations as
        # its peer.
        e.scope = scope
        e.sr = peer.sr
        e.rel[SR_agent].extend(peer.rel[SR_agent])
        e.rel[SR_exper].extend(peer.rel[SR_exper])
        if scope is not None:
            relIx = scope.getRel(peer);
            if relIx != -1:
                scope.rel[relIx].append(e)
        # the conjunction preceeding e is made the head of "e"
        conj = e.prv
        e.head.extend(conj.wrds)
        pg.removeNode(conj)
        conj.scope = scope     
        return e.nxt

