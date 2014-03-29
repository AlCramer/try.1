# Copyright 2011 Al Cramer

from defs import *
from lexer import vcb
import pg
import serializer
from rematch import ReMatch
from xfrm import Xfrm
import sys

class ObjRe(ReMatch):
    """ Regular expression machinary for thematic role analysis """
    def __init__(self):
        ReMatch.__init__(self)
        self.verb = None
        self.src = None
        self.declRe("%qualObjTerm","X Prep X")
        self.declRe("%immedObjTerm","[%qualObjTerm|X]")

    def setSource(self,_verb,_src):
        self.verb = _verb
        self.src = _src

    def matchTerm(self,state,reTerm):
        # "state" is an index into "self.src" (a list of Pn's)
        if state >= len(self.src):
            return None
        term = self.src[state]
        if reTerm == ".":
            # match any
            return [term]
        if reTerm.startswith("_"):
            # a literal
            if reTerm[1:] == vcb.getSpelling(term.wrds[0]):
                return [term]
            return None
        if reTerm == "objTerm":
            # anything except a prep
            if not vcb.checkScProp(term.sc,WP_PREP):
                return [term]
            return None
        if reTerm == "objPronoun":
            # an object pronoun
            return reTerm.testWrd(\
                "me","you","us","him","her","them","it")
        if reTerm == "Prep":
            # any kind of prep
            if vcb.checkScProp(term.sc,WP_PREP):
                return [term]
            return None
        if reTerm == "qualPrep":
            # qualifying prep
            if vcb.checkScProp(term.sc,WP_QUALPREP):
                return [term]
            return None
        if reTerm == "Mod":
            # any kind of Mod
            if vcb.checkScProp(term.sc,WP_MOD):
                return [term]
            return None
        if reTerm == 'objPrep':
            # object prep associated with the verb
            if vcb.prepVerbFitness(\
                term.getWrd(0),self.verb.getVRoot()) != -1:
                return [term]
            return None
        if reTerm == "X":
            # a noun or modifier
            if vcb.getScSpelling(term.sc) == 'X':
                return [term]
            return None
        if reTerm == "V":
	    # a verb
            if term.isVerb():
                return [term]
            return None
        if reTerm == "SubVerb":
	    # a verb with defined subject
            if len(term.rel[SR_agent]) > 0:
                return [term]
            return None
        if reTerm == "vexprTopic":
            # a verb phrase acting as a topic in an "is" predictate:
            # "was the guy you saw angry"
            if len(term.rel[SR_isQby]) > 0:
                return [term]
            if term.checkVProp(VP_Inf|VP_Gerund) and \
                len(term.rel[SR_agent]) == 0:
                return [term]
            return None
        return None

def srToStr(sr):
    return '(0xff)' if sr ==0xff else \
        '(%s)' % (SRids[sr])

def checkVSpec(vspec,m):
    return (vspec & m) != 0

def setRole(e,role,terms):
    """ Assign terms to role for verb "e" """
    e.rel[role] = terms
    for ex in terms:
        ex.sr = role

def testVerbForm(e,form):
    """
    Test form of verb. "form" can be:
    WP_AVGT -- agent-verb-goal-theme WP_EVT -- experiencer-verb-theme
    WP_AVE -- agent-verb-exeriencer
    """
    return vcb.checkProp(e.verbs[0],form)

def resolveRole(e,role):
    """
    resolve a role: "SR_sub" and "SR_obj" are remapped to the value
    (SR_agent, SR_exper, etc.) appopriate for the verb
    """
    if role == SR_sub:
        if testVerbForm(e,WP_EVT):
            return SR_exper
        elif e.testVRoot("be"):
            return SR_topic
        else:
            return SR_agent
    elif role == SR_obj:
        if testVerbForm(e,WP_AVE):
            return SR_exper
        else:
            return SR_theme
    else:
        return role

def matchVerb(v,vspec,subLst):
    """ does verb match the spec associated with a rule? """
    if checkVSpec(vspec,VP_IsQ) and \
        len(v.rel[SR_isQby]) == 0:
        return False
    elif checkVSpec(vspec,VP_NotModified) and \
        len(v.rel[SR_modifies]) != 0:
        return False
    elif checkVSpec(vspec,VP_NoSubject) and \
        len(subLst) != 0:
        return False
    elif checkVSpec(vspec,VP_Passive) and \
        not v.checkVProp(VP_Passive):
        return False
    elif checkVSpec(vspec,VP_Avgt) and \
        not testVerbForm(v,WP_AVGT):
        return False
    elif checkVSpec(vspec,VP_Ave) and \
        not testVerbForm(v,WP_AVE):
        return False
    elif checkVSpec(vspec,VP_Evt) and \
        not testVerbForm(v,WP_EVT):
        return False
    elif checkVSpec(vspec,VP_BeQuery):
        if v.testVRoot("be"):
            if len(subLst) == 0:
                return True
            if len(subLst) == 1:
                return subLst[0].checkWrdProp(WP_QUERY)
        return False
    elif checkVSpec(vspec,VP_VAdjQuery):
        if v.checkVProp(VP_Adj) or \
            v.testVRoot(['be','have','do']):
            if len(subLst) == 0:
                return True
            if len(subLst) == 1:
                return subLst[0].checkWrdProp(WP_QUERY)
        return False
    return True

"""
TODO: rework Rules for assigning roles. A rule is the triplet
(vSpec,objSpec,srInfo). "vSpec" and "objSpec" give the conditions
which must be must for the rule to apply. "vSpec" concerns the verb,
and is a collection of verb props (VP_xxx). "ObjSpec" concerns the
object list, and is a string representation of a reg. expr.

"srInfo" gives the syntax-relations established by the rule. This is a
list of SR_xxx values. srInfo[0] describes the verb. srInfo[1]
descrbes the subject terms. Remaining terms describe the object terms:
there's one value for each match-term in the reg.expr. "objSpec".
"""
class RoleXfrm(Xfrm):
    def __init__(self,_name=''):
        Xfrm.__init__(self,_name)
        # reg.expr match engine for object clauses
        self.objRe = ObjRe()
        # Rule data... list of int's
        self.vSpec = None
        # list of Strings, each a reg.expr.
        self.objSpec = None
        # list of syntax relations for rules.
        self.srInfo = None

    def serialize(self,mode):
        if mode == 'w':
            serializer.encodeIntLst(self.vSpec,32)
            serializer.encodeStrLst(self.objSpec)
            serializer.encodeLstLst(self.srInfo,8)
        else:
            self.vSpec = serializer.decodeIntLst(32)
            self.objSpec = serializer.decodeStrLst()
            self.srInfo = serializer.decodeLstLst(8)

    def printRule(self,fp,rix):
        if fp is None:
            fp = sys.stdout
        spSrInfo = [srToStr(sr) for sr in self.srInfo[rix]]
        fp.write('vSpec: %s srV: %s\n' % \
            (VPtoStr(self.vSpec[rix],':'), spSrInfo[0]))
        fp.write('objSpec: %s\n' % self.objSpec[rix])
        fp.write('srObj: %s\n' % ' '.join(spSrInfo[2:]))
        if self.srInfo[rix][1] != 0xff:
            fp.write('srSub: %s\n' % spSrInfo[1])
        fp.write('\n')

    def printme(self,fp):
        for rix in range(len(self.vSpec)):
            self.printRule(fp,rix)

    def findRule(self,e):
        if e.isVerb():
            subLst = e.rel[SR_agent]
            objLst = e.rel[SR_theme]
            self.objRe.setSource(e,objLst)
            for i in range(len(self.vSpec)):
                if matchVerb(e,self.vSpec[i],subLst) and \
                    self.objRe.match(objLst,self.objSpec[i]):
                    return i
        return None

    def applyRule(self,e,rule):
        # "rule" is an index rintRule(rule)
        _srinfo = self.srInfo[rule]
        vspec = self.vSpec[rule]
        srV = _srinfo[0]
        srSub = _srinfo[1]
        # Prior processing has recognized grammatical relations:
        # subject terms have been placed on the "agent" list, object
        # terms on the "theme" list. Save these lists, then clear
        # them.
        subLst = e.rel[SR_agent]
        e.rel[SR_agent] = []
        objLst = e.rel[SR_theme]
        e.rel[SR_theme] = []
        for ex in subLst:
            ex.sr = SR_undef
        for ex in objLst:
            ex.sr = SR_undef
        # apply the rule
        if srV == SR_vAdj:
            # "did she leave": e is a verb-adjunct to objLst[0], which
            # is subject-verb
            vMain = objLst[0]
            vMain.unsetScope()
            e.setScope(vMain,SR_vAdj)
            # transfer attributes from adjunct to main verb
            vMain.vprops = e.vprops & VP_tenseMask
            if not e.testVRoot(\
                ['be','have','do','will','shall']):
                vMain.vqual.append(e.getWrd(0))
        else:
            for i in range(len(_srinfo)-2):
                role = resolveRole(e,_srinfo[i+2])
                if role != 0xff and \
                    len(self.objRe.matchResult[i]) > 0:
                    setRole(e,role,self.objRe.matchResult[i])
    
            role = resolveRole(e,srSub)
            if role != 0xff:
                setRole(e,role,subLst)
        if checkVSpec(vspec,VP_BeQuery) or srV == SR_vAdj:
            # "why is she angry", "why did he leave": the main verb
            # becomes a qualifier for "why"
            if len(subLst) == 1 and subLst[0].checkWrdProp(WP_QUERY):
                vMain = objLst[0] if srV == SR_vAdj else e
                vMain.unsetScope()
                subLst[0].setScope(vMain,SR_isQby)
        return e.nxt
