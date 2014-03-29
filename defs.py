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

"""
This module defineds constants (mostly bitmasks for various kinds of
properties) used throughout the package.
"""

""" Word properties """
# parts-of-speach
WP_CONJ =      0x1
WP_CLPREP =    0x2
WP_QUALPREP =  0x4
WP_PREP =      0x8
WP_N =         0x10
WP_NOUN =      0x20
WP_MOD =       0x40
WP_PRONOUN =   0x80
WP_X =         0x100
# verb properties
WP_VERB =      0x200
WP_ROOT =      0x400
WP_GERUND =    0x800
WP_PARTICIPLE = 0x1000
WP_PRESENT =   0x2000
WP_PAST =      0x4000
WP_VADJ =      0x8000
# "mr","mrs", etc.
WP_ABBREV =    0x10000
# "can't"
WP_CONTRACTION = 0x20000
# negative contraction of a verb: "can't"
WP_VNEG_CONTRACTION = 0x40000
# who/what/why/when/where/how
WP_QUERY =     0x80000
# strong ("a") and weak ("that") determinants
WP_DETS =      0x100000
WP_DETW =      0x200000
# thematic props for verbs agent-verb-goal-theme
WP_AVGT =      0x400000
# agent-verb-experiencer
WP_AVE =       0x800000
# experiencer-verb-them
WP_EVT =       0x1000000
# verb-phrase qualifier: I BEGAN to eat
WP_VPQ =       0x2000000
# punctuation
WP_PUNCT =     0x4000000

WP_VERB_PROPS = \
(WP_ROOT|WP_GERUND|WP_PARTICIPLE|WP_PRESENT|WP_PAST|WP_VADJ)

def WPtoStr(m):
    """ Dump word props """
    s =''
    if (m & WP_CONJ) != 0: s += "CONJ "
    if (m & WP_CLPREP) != 0: s += "CLPREP "
    if (m & WP_QUALPREP) != 0: s += "QUALPREP "
    if (m & WP_PREP) != 0: s += "PREP "
    if (m & WP_N) != 0: s += "N "
    if (m & WP_NOUN) != 0: s += "NOUN "
    if (m & WP_MOD) != 0: s += "MOD "
    if (m & WP_PRONOUN) != 0: s += "PRONOUN "
    if (m & WP_X) != 0: s += "X "
    if (m & WP_VERB) != 0: s += "VERB "
    if (m & WP_ROOT) != 0: s += "ROOT "
    if (m & WP_GERUND) != 0: s += "GERUND "
    if (m & WP_PARTICIPLE) != 0: s += "PARTICIPLE "
    if (m & WP_PRESENT) != 0: s += "PRESENT "
    if (m & WP_PAST) != 0: s += "PAST "
    if (m & WP_VADJ) != 0: s += "VADJ "
    if (m & WP_ABBREV) != 0: s += "ABBREV "
    if (m & WP_CONTRACTION) != 0: s += "CONTRACTION "
    if (m & WP_VNEG_CONTRACTION) != 0: s += "VNEG_CONTRACTION "
    if (m & WP_QUERY) != 0: s += "QUERY "
    if (m & WP_DETS) != 0: s += "DETS "
    if (m & WP_DETW) != 0: s += "DETW "
    if (m & WP_AVGT) != 0: s += "AVGT "
    if (m & WP_AVE) != 0: s += "AVE "
    if (m & WP_EVT) != 0: s += "EVT "
    if (m & WP_VPQ) != 0: s += "VPQ "
    if (m & WP_PUNCT) != 0: s += "PUNCT "
    l = len(s)
    if l > 0:
        s = s[0:l-1]
    return s

""" Verb properties """
VP_Neg = 0x1
VP_Adj = 0x2
VP_Past = 0x4
VP_Present = 0x8
VP_Future = 0x10
VP_Perfect = 0x20
VP_Subjunctive = 0x40
VP_Inf = 0x80
VP_Root = 0x100
VP_Gerund = 0x200
VP_Passive = 0x400
VP_Atomic = 0x800
VP_Prelude = 0x1000
VP_ActName = 0x2000
VP_Avgt = 0x4000
VP_Ave = 0x8000
VP_Evt = 0x10000
VP_IsQ = 0x20000
VP_NotModified = 0x40000
VP_NoSubject = 0x80000
VP_BeQuery = 0x100000
VP_VAdjQuery = 0x200000
VP_SubordCl = 0x400000
VP_NVexpr = 0x800000
VP_AgentAction = 0x1000000
VP_ImmutableSub = 0x2000000

VP_tenseMask = VP_Past|VP_Present|VP_Future|VP_Subjunctive
VP_semanticMask = VP_Neg|VP_Prelude

def VPtoStr(m,delim):
    """ Dump verb props """
    s = []
    if (m & VP_Neg) != 0: s.append("not")
    if (m & VP_Adj) != 0: s.append("adj")
    if (m & VP_Past) != 0: s.append("past")
    if (m & VP_Present) != 0: s.append("present")
    if (m & VP_Future) != 0: s.append("future")
    if (m & VP_Perfect) != 0: s.append("perfect")
    if (m & VP_Subjunctive) != 0: s.append("subj")
    if (m & VP_Inf) != 0: s.append("inf")
    if (m & VP_Root) != 0: s.append("root")
    if (m & VP_Gerund) != 0: s.append("ger")
    if (m & VP_Passive) != 0: s.append("passive")
    if (m & VP_Atomic) != 0: s.append("atomic")
    if (m & VP_Prelude) != 0: s.append("prelude")
    if (m & VP_ActName) != 0: s.append("actname")
    if (m & VP_Avgt) != 0: s.append("avgt")
    if (m & VP_Ave) != 0: s.append("ave")
    if (m & VP_Evt) != 0: s.append("evt")
    if (m & VP_IsQ) != 0: s.append("isQ")
    if (m & VP_NotModified) != 0: s.append("notModified")
    if (m & VP_NoSubject) != 0: s.append("noSubject")
    if (m & VP_BeQuery) != 0: s.append("beQuery")
    if (m & VP_VAdjQuery) != 0: s.append("vadjQuery")
    if (m & VP_SubordCl) != 0: s.append("subordCl")
    if (m & VP_NVexpr) != 0: s.append("nvExpr")
    if (m & VP_AgentAction) != 0: s.append("agentAct")
    if (m & VP_ImmutableSub) != 0: s.append("immutableSub")
    return ' '.join(s)

""" Syntax-relations """
SR_agent = 0
SR_topic = 1
SR_exper = 2
SR_theme = 3
SR_auxTheme = 4
SR_modifies = 5
SR_isQby = 6
SR_head = 7
SR_vconj = 7
SR_vAdj = 8
# This used for a word that is in the scope of a verb, but its
# relation is undefined.
SR_undef = 9
# Total number of relations, word->verb
SR_nWordToVerb = 10
# generic subject/object: computational
SR_sub = 10
SR_obj = 11
# names for roles
SRids = ["agent","topic","exper","theme","auxTheme",\
    "qual","isQby","vconj","vAdj","undef",\
    "sub","obj"]

class Nd:
    """ Generic node """
    def __init__(self,S = -1,E = -1):
        # span attributes
        self.S = S
        self.E = E
        # list structure
        self.prv = self.nxt = None
        self.sublst = None

    def setSp(self,S,E):
        self.S = S
        self.E = E

    @classmethod
    def connect(cls,lhs,rhs):
        if lhs != None:
            lhs.nxt = rhs
        if rhs != None:
            rhs.prv = lhs
            
class ParseErr(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
