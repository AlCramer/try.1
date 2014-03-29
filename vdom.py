# Copyright 2011 Al Cramer

from defs import *
from lexer import vcb
import pg

"""
Parse methods for verb domains. A verb domain is a contiguous
sequence of words centered around a verb. To the left are Q
and subject terms. To the right are object terms. There is a
prioriy in binding: subject is strongest, followed by qualification,
followed by is-object-of. At this point in processing Q, sub, and
object relations have been established  and are represented
by SR_isQby, SR_agent, and SR_theme respectively.
"""

# syntax predicates

def isNVexpr(e):
    """
    is "e" a verb expression that can function as a noun
    ("the girl sitting there", "the boy you saw")
    """
    return e != None and e.checkVProp(VP_NVexpr)

def isAgentAction(e):
    """
    is "e" agent-action? sub-gerund returns false.
    A Q expr ("the girl you saw") will return true, since
    "you saw" is agent-action.
    """
    return e != None and e.checkVProp(VP_AgentAction)    

def hasMutableSub(e):
    """
    is "e" a verb whose subject can be reset?
    """
    return e is not None and e.isVerb() and \
       not e.checkVProp(VP_ImmutableSub)
    
def isSubordCl(v):
    """
    Can v function as a subordinate verb clause?
    """
    return v != None and v.checkVProp(VP_SubordCl)

# vdl: verb domain list. It's a list of nodes, linked by vprv and
# vnxt. Structure is 0 or more non-verb nodes (the prelude), 
# followed by a sequence of verb nodes. Each verb node is a
# verb domain.

vdl = None

def vdlJoin(left,right):
    if left is not None:
        left.vnxt = right
    if right is not None:
        right.vprv = left

def vdlRemove(v):
    """ 
    remove "v" from the vdl. A no-op if v is not in the list.
    """
    global vdl
    if v == vdl:
        vdl = v.vnxt
        if vdl is not None:
            vdl.vprv = None
    else:
        left = v.vprv
        right = v.vnxt
        vdlJoin(left,right)

def vdlInsert(v,e):
    """ insert e in the vdl, immediately before v """
    global vdl
    if v == vdl:
        vdlJoin(e,v)
        vdl = e
    else:
        vdlJoin(v.vprv,e)
        vdlJoin(e,v)

def getFirstVerb():
    e = vdl
    while e is not None:
        if e.isVerb():
            return e
        e = e.vnxt
    return None

def printvdl(title=None):
    if title != None:
        print title
    e = vdl
    while e is not None:
        e.printme(None,0)
        e = e.vnxt

def prv(e,offset=1):
    """ get predecessor of e in vdl """
    ex = e
    for cnt in range(offset):
        if ex is None:
            break
        ex = ex.vprv
    return ex

def nxt(e,offset=1):
    """ get successor of e in vdl """
    ex = e
    for cnt in range(offset):
        if ex is None:
            break
        ex = ex.vnxt
    return ex

def addModifies(v,e):
    """ add e to v's modifier's list. """
    if isinstance(e,list):
        for ex in e:
            addModifies(v,ex)
        return
    vdlRemove(e)
    e.setScope(v,SR_modifies)

def addObj(v,e):
    """ add e to v's object list. """
    if isinstance(e,list):
        for ex in e:
            addObj(v,ex)
        return
    vdlRemove(e)
    e.setScope(v,SR_theme)

def _unreduce(v,ixrel):
    """
    undo a previous reduction: ixrel must be SR_agent, SR_isQby, 
    or SR_vconj.  The unbound nodes are reassigned to the object 
    list of the preceeding verb; or to the vdl, if v is the first 
    verb in the vdl
    """
    assert ixrel in [SR_agent, SR_isQby, SR_vconj]
    lst = v.rel[ixrel]
    if len(lst) > 0:
        v.rel[ixrel] = []
        # if this domain has a predecessor domain, its reduced terms
        # are appended to the predeccessor's object list
        if v.vd_left is not None:
            addObj(v.vd_left,lst)
        else:
            # reinsert the nodes in the vdl, immediately in front
            # of v.
            for e in lst:
                e.unsetScope()
                vdlInsert(v,e)
    
def _reduce(v,ixrel,e):
    """
    reduce: ixrel must be SR_agent, SR_isQby, or SR_vconj
    """
    assert ixrel in [SR_agent, SR_isQby, SR_vconj]
    if isinstance(e,list):
        for ex in e:
            _reduce(v,ixrel,ex)
        return
    # undo any previously performed redution. Note that
    # reducing by Subject implicitly undoes any previously created
    # Q relations.
    if ixrel == SR_agent:
        _unreduce(v,SR_isQby)
    _unreduce(v,ixrel)
    e.setScope(v,ixrel)
    vdlRemove(e)

def reduceS(v,e):
    _reduce(v,SR_agent,e)

def reduceQ(v,e):
    _reduce(v,SR_isQby,e)

def reduceConjAction(v,e):
    _reduce(v,SR_vconj,e)

def unreduceS(v):
    _unreduce(v,SR_agent)

def unreduceQ(v):
    _unreduce(v,SR_isQby)
    
def findSc(lst,mask):
    """ find index in list: test is on Sc props """
    for i in range(len(lst)):
        if lst[i].checkSc(mask):
            return i
    return -1

def matchSc(lst,pat):
    """ match lst against pat: test is on Sc props """
    for i in range(len(pat)):
        if i >= len(lst) or not lst[i].checkSc(pat[i]):
            return False
    return True
    
def reduceLeftAdj():
    """ reduce left-adjuncts """
    # get first verb
    v0 = getFirstVerb()
    if v0 is None:
        return
    # prep: prep that precedes the verb
    prep = None
    ex = prv(v0)
    if ex is not None and ex.checkSc(WP_PREP|WP_CLPREP):
        prep = ex
    # Cases with explicit prep
    if prep is not None:
        if prep.testWrd("for") or prep.testWrd("then"):
            # reject as left adjunct
            return
        if isNVexpr(v0):
            v1 = nxt(v0)
            if isAgentAction(v1):
                # "On the day you left we saw mermaids"
                unreduceQ(v1)
                addModifies(v1,[prep,v0])
                return
            # Look for prep clause adjuncts not containing verbs:
            # "on monday we saw mermaids",
            # TODO:
            # "by the day after tommorrow we'll be in Paris"
            if len(v0.rel[SR_isQby]) > 0:
                unreduceQ(v0)
                addModifies(v0,[prep,nxt(prep)])
                return
        if isAgentAction(v0):
            v1 = nxt(v0)
            if isAgentAction(v1):
                # "After you left the ship we saw mermaids"
                unreduceQ(v1)
                addModifies(v1,[prep,v0])
                return
        # no other cases with explicit prep are recognized
        return
    # No explicit prep. Look for cases:
    # "The day you left the ship we saw mermaids"
    v1 = nxt(v0)
    if isNVexpr(v0):
        if isNVexpr(v1):
            unreduceQ(v1)
            addModifies(v1,v0)
            return
        if not hasMutableSub(v1):
            # "The day you left we saw mermaids". Test on mutable
            # sub means "The day you left Paris was cold" parses
            # as [The day you left Paris] was cold (mutable sub means
            # subject can be changed to be the Q term).
            addModifies(v1,v0)
            return
    
def reduceSubObj():
    """
    Reduce subject/objects for verb-domains. Returns False
    if the reduction cannot be performed (the case lies outside
    our model).
    """
    # advance to the first verb
    v = getFirstVerb()
    if v is None or nxt(v) is None:
        # no verbs; or only one verb. Nothing to resolve
        return
    # get initial scope: either v, or NVexpr + vnxt
    scope = None
    peek = nxt(v)
    if isNVexpr(v):
        if hasMutableSub(peek):
            # lv + peek -> SV
            reduceS(peek,v)
            scope = peek
        else:
            # an error (case is outside our model)
            raise ParseErr("failed to set initial scope")
    else:
        scope = v
    # advance: we're currently in the object context of "scope"
    v = nxt(scope)
    while v is not None:
        peek = nxt(v)
        if isNVexpr(v):
            if isNVexpr(peek):
                # 2 names in an object context. Both becomes object
                # terms of "scope". Scope then shifts to "peek".
                addObj(scope,v)
                addObj(scope,peek)
                scope = peek
                v = nxt(scope)
                continue
            if hasMutableSub(peek):
                # v + peek ->SV, which is added to scope's object;
                # scope then shifts to peek.
                reduceS(peek,v)
                addObj(scope,peek)
                scope = peek
                v = nxt(scope)
                continue
            if peek is not None:
                # error (case is outside our model)
                raise ParseErr("could not handle 'peek'")
            # Fall thru to code below
        # "v" added to scope's object list; scope then shifts to v.
        # "peek" becomes the new v. 
        addObj(scope,v)
        scope = v;
        v = peek
    return

def doPredicateQueries():
    """
    Handle predicate queries. These are queries of the form:
    "is she pretty", "is that man the one you met yesterday",
    etc.:  form is verb-subject-object, rather than
    subject-verb-object. Thematic role analysis expects to
    see Verb ("Be") followed by a sequence of object terms; it
    will identify the subject term in that sequence. But if one
    or more of these terms are NVexpr, the default object assignments
    mey be incorrect. Our job is to fix these.
    """
    v0 = getFirstVerb()
    if v0 is None or not v0.testVRoot(['be']):
        return
    # In general predicate queries have null subject terms
    # ("is she angry?"), and cases with non-null subjects
    # ("is she angry") are rejected as predicate queries;
    # the exception is "why is she angry", which is treated as
    # pred. query
    sublst = v0.rel[SR_agent]
    if len(sublst) > 0 and \
        not sublst[0].checkWrdProp(WP_QUERY):
        return
    # want the object list of v0
    objlst = v0.rel[SR_theme]
    N = len(objlst)
    e1 = None if N == 0 else objlst[0]
    e2 = None if N < 2 else objlst[1]
    if isNVexpr(e1):
        if e2 is not None:
            if e2.checkVProp(VP_Gerund):
                # "was the guy you saw today leaving?"
                reduceS(e2,e1)
                return
            if isNVexpr(e2):
                # "is the ring I bought the one you liked?"
                # no resolution required: accept as is
                return
        # "was the guy you saw angry"
        objlst = e1.rel[SR_theme]
        i = findSc(objlst,WP_MOD)
        if i != -1:
            for ex in objlst[i:]:
                ex.setScope(v0,SR_theme)

def resolveObjRelations(v):
    # we want verbs with "weak scope": they compete with their
    # parent for object terms
    if v.scope is None or not isNVexpr(v):
        # reject as weak scope
        return v.nxt
    objlst = v.rel[SR_theme]
    owner = v.scope
    prepMask = WP_PREP|WP_CLPREP|WP_QUALPREP
    # look for an explicit prep
    for i in range(len(objlst)):
        e = objlst[i]
        if e.checkSc(prepMask):
            prep = e.getWrd(0)
            vFit = vcb.prepVerbFitness(prep,v.getVRoot())
            ownerFit = vcb.prepVerbFitness(prep,owner.getVRoot())
            if ownerFit != -1 and ownerFit > vFit:
                # this prep, plus terms that follow, are promoted to
                # the owner scope
                terms = objlst[i:]
                for ex in terms:
                    ex.setScope(owner,SR_theme)
                return v.nxt
    # give "v" a minimal object clause
    def check(i,mask):
        return i<len(objlst) and objlst[i].checkSc(mask)
    ix = -1
    if matchSc(objlst,[prepMask,WP_X]):
        ix = 2
    elif matchSc(objlst,[WP_X]):
        ix = 1
    if ix != -1:
        terms = objlst[ix:]
        for ex in terms:
            ex.setScope(owner,SR_theme)
    return v.nxt

def parse():
    """ Main parse method for verb domains. """
    # Create the vdl (verb-domain-list). Structure will be a prelude
    # (non verb nodes), followed by a sequence of verb nodes.
    # Each verb node is actually a verb domain: subject terms
    # are in v.rel[SR_agent], object terms are in v.rel[SR_theme],
    # and qualified terms in v.rel[R_isQby]
    global vdl
    vdl = None
    vdlTail = None
    e = pg.eS
    while e is not None:
        if e.scope is None:
            e.vnxt = e.vprv = None
            if vdl is None:
                vdl = vdlTail = e
            else:
                vdlJoin(vdlTail,e)
                vdlTail = e
            # If this verb domain is immediately preceeded by
            # a verb domain, save a reference as "vd_left". This is
            # an invariant: "vprv" and "vnxt" relations change when we
            # do reductions, but "vd_left" is constant. 
            left = prv(e)
            if left is not None and left.isVerb():
                e.vd_left = left
        e = e.nxt

    # reduce conjoined actions
    e = getFirstVerb()
    while e is not None and \
        nxt(e) is not None:
        objlst = e.rel[SR_theme]
        N = len(objlst)
        if N>0 and objlst[N-1].checkSc(WP_CONJ):
            reduceConjAction(e,nxt(e))
            continue
        e = nxt(e)
    
    # reduce subordinate clauses
    e = getFirstVerb()
    while e is not None and nxt(e) is not None:
        ex = nxt(e)
        while isSubordCl(ex):
            addObj(e,ex)
            ex = nxt(e)
        e = nxt(e)

    # reduce left-adjuncts
    reduceLeftAdj()
    
    # reduce subjects and objects for verb-domains
    reduceSubObj()

    # parse predicate queries: "Is the girl you saw coming".
    # These follow verb-subject-object pattern.
    doPredicateQueries()

    # reassign  object terms as needed.
    pg.walk(resolveObjRelations)
            
