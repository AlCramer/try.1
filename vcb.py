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
import re
import serializer
import os

class WordVariant():
    """
    "softly" is a variant of "soft", "looked" is a variant of "look".
    This data structure records the root and props of the variant
    """
    rootKey = 0
    props = 0

class Dict():
    """
    This class encapsulates 3 mappings: word->index, index->word, and
    index->props. "word" is a the spelling for an entry; "index" is
    the index assigned to an entry; "props" is a bitmask.
    """
    def __init__(self):
        # spelling->index
        self.spToIx = {}
        # index->spelling
        self.spelling = []
        # index->props
        self.props = []

    def getN(self):
        # get number of entries
        return len(self.spelling)

    def lkup(self,sp,createIfMissing):
        """ lookup "sp", returning the index for its entry """
        ix = self.spToIx.get(sp)
        if ix != None:
            return ix
        if not createIfMissing:
            return 0
        ix = len(self.spelling)
        self.spToIx[sp] = ix
        self.spelling.append(sp);
        self.props.append(0);
        return ix

    def serialize(self,mode):
        """ serialize  the dictionary """
        global spToIx,spelling,props
        if mode == 'w':
            serializer.encodeStrLst(self.spelling)
            serializer.encodeIntLst(self.props,32)
        else:
            self.spelling = serializer.decodeStrLst()
            self.spToIx = {}
            for i in range(len(self.spelling)):
                self.spToIx[self.spelling[i]] = i
            self.props = serializer.decodeIntLst(32)

    def getSpelling(self,ix):
        """ get spelling """
        return self.spelling[ix]

    def setProp(self,ix,v):
        """ set prop """
        self.props[ix] |= v

    def checkProp(self,ix,v):
        """ check prop """
        return (ix != 0) and ((self.props[ix] & v) != 0)

"""
This module contains our vocabulary. "dict" is a dictionary, defining
the mappings word->index, index->word, and index->properties.
Additional data structures provide more information about entries.
These are: 1. "_def" -- key of some other entry in the lexicon, which
is the "definition" of this word. Sometimes a word is defined to
itself. 2. "synClass" -- syntax-class for the word. 3. Prep<->Verb
associations -- is a prep associated with a verb? The association may
be an indirect object phrase ("I gave the apple TO the girl"); or it
might be a common modifier clause ("I walked TO the store"). 4.
Rewrite Rules -- rules for replacing one set of words with another
during tokenization.
"""
# Our dictionary
dct = Dict()
def getN():
    return dct.getN();
# definitions for entries.
_def = []
# syntax class for entries.
synClass = []
# rewrite rules A rewrite rule specifies a lhs ("target"), and a rhs
# ("replacement"). Both are sequences, giving indices into the
# dictionary. We apply a rule by recognizing a lhs in the token
# sequence and replacing it with the rhs. A rule is represented as an
# array of int's. The format is: element0: length, lhs element1:
# length, rhs len-lhs int's, giving the lhs dictionary indices len-rhs
# int's, giving the rhs dictionary indices.
rwrules = []
# list of int-lists prep->{verbs}, where prep is an object prep for a
# verb in {verbs}
prepToVerbs = []
# The syntax-class dictionary
scDct = Dict()
# sc singeltons
scSingletons = []
# version info: readin from "lexicon.txt"
version = "?"

def serialize(mode):
    """ serialize  the vocabulary """
    global _def,rwrules,prepToVerbs,scSingletons
    global synClass
    dct.serialize(mode)
    if mode == 'w':
        serializer.encodeIntLst(_def,32)

        for ruleSet in rwrules:
            serializer.encodeLstLst(ruleSet,32)

        serializer.encodeLstLst(prepToVerbs,32)
        serializer.encodeIntLst(synClass,32)
        serializer.encodeStrLst(scSingletons)
    else:
        _def = serializer.decodeIntLst(32)

        rwrules = []
        for i in range(dct.getN()):
            rwrules.append(serializer.decodeLstLst(32))

        prepToVerbs = serializer.decodeLstLst(32)
        synClass = serializer.decodeIntLst(32)
        scSingletons = serializer.decodeStrLst()
    scDct.serialize(mode)

def lkup(sp,createIfMissing):
    """ lookup "sp", returning the key for its entry """
    global _def,synClass,rwrules,prepToVerbs
    ix = dct.lkup(sp,False)
    if ix != 0:
        return ix
    if not createIfMissing:
        return 0
    ix = dct.lkup(sp,True)
    _def.append(0);
    synClass.append(0)
    rwrules.append(None)
    prepToVerbs.append(None)
    return ix

def define(sp,_props,_def):
    """ define an entry """
    ix = lkup(sp,True)
    setProp(ix,_props)
    if _def != 0:
        # this def overrides any previous def
        setDef(ix,_def)
    else:
        # if this entry has no definition, define to self
        if getDef(ix) == 0:
            setDef(ix,ix)
    return ix

def getSpelling(ix):
    """ get spelling, given ix """
    return dct.getSpelling(ix)

def getDef(ix):
    """ get def for ix """
    return _def[ix]

def setDef(ix,v):
    """ set def for ix """
    _def[ix] = v

def getProps(ix):
    """ get props """
    return dct.props[ix]

def setProp(ix,v):
    """ set prop """
    dct.setProp(ix,v)

def checkProp(ix,v):
    """ check prop """
    return dct.checkProp(ix,v)

def testRewrite(rule,toks,i):
    """
    does rewrite rule apply to tok sequence "toks" starting at element
    "i"?
    """
    nLhs = rule[0]
    if i + nLhs > len(toks):
        return False
    lhs = rule[2 : 2+nLhs]
    pat = toks[i : i+nLhs]
    return lhs == pat

def findRewrite(toks,i):
    """ find rewrite rule that applies to toks[i] """
    rules = rwrules[toks[i]]
    if rules != None:
        for r in rules:
            if testRewrite(r,toks,i):
                return r
    return None

def getRhsRewrite(rule,wantUpper):
    """ get rhs tokens for rewrite rule """
    nLhs = rule[0]
    nRhs = rule[1]
    rhs = rule[2+nLhs : 2+nLhs+nRhs]
    if wantUpper:
        # want upper-case start for rhs[0]
        spx = getSpelling(rhs[0])
        c0 = spx[0].upper()
        spx = c0 + spx[1:]
        rhs[0] = getVocab(spx)
    return rhs

def prepVerbFitness(prep,verb):
    """ is "prep" asociated with "verb" """
    verbs = prepToVerbs[prep]
    if verbs != None and verb in verbs:
        return verbs.index(verb)
    return -1

def isVerbVariant(wrd,v):
    """
    is an unknown word a variant of a known verb? We expect the
    lower-case spelling of the unknown word.
    """
    l = len(wrd)
    # if this the not-contraction for a verb? ("isn't", "didn't")
    if (l >= 5) and wrd.endswith("n't"):
        test = wrd[0 : l-3]
        # some cases are irregular...
        vKey = lkup(test,False)
        if vKey != 0:
            v.props = WP_VNEG_CONTRACTION | getProps(vKey)
            v.props &= ~WP_ROOT
            v.rootKey = getDef(vKey)
            return True
    # "...ing"
    if (l >= 5) and wrd.endswith("ing"):
        root = wrd[0 : l-3]
        # "wanting"
        key = lkup(root,False)
        if checkProp(key,WP_ROOT):
            v.rootKey = key
            v.props |= WP_VERB|WP_GERUND
            return True
        # "hating"
        test = root + "e"
        key = lkup(test,False)
        if checkProp(key,WP_ROOT):
            v.rootKey = key
            v.props |= WP_VERB|WP_GERUND
            return True
        # "shipping"
        lroot =len(root)
        if root[lroot-1] == root[lroot-2]:
            test = root[0:lroot]
            key = lkup(test,False)
            if checkProp(key,WP_ROOT):
                v.rootKey = key
                v.props |= WP_VERB|WP_GERUND
                return True
    # "...ed"
    if (l >= 4) and wrd.endswith("ed"):
        root = wrd[0 : l-2]
        lroot = len(root)
        # "wanted"
        key = lkup(root, False)
        if checkProp(key,WP_ROOT):
            v.rootKey = key
            v.props |= WP_VERB|WP_PARTICIPLE|WP_PAST
            return True
        # "hated"
        key = lkup(root + "e",False)
        if checkProp(key,WP_ROOT):
            v.rootKey = key
            v.props |= WP_VERB|WP_PARTICIPLE|WP_PAST
            return True
        # "shipped"
        if root[lroot-1] == root[lroot-2]:
            test = root[0:lroot]
            key = lkup(test,False)
            if checkProp(key,WP_ROOT):
                v.rootKey = key
                v.props |= WP_VERB|WP_PARTICIPLE|WP_PAST
                return True
    # "...es"
    if (l >= 4) and wrd.endswith("es"):
        # "watches"
        test = wrd[0 : l-2]
        if test == "be":
            # "bees"
            return False
        key = lkup(test,False)
        if checkProp(key,WP_ROOT):
            v.rootKey = key
            v.props |= WP_VERB|WP_PRESENT
            return True
    # "eats"
    if (l >= 3) and wrd.endswith("s"):
        test = wrd[0 : l-1]
        key = lkup(test, False)
        if checkProp(key,WP_ROOT):
            v.rootKey = key
            v.props |= WP_VERB|WP_PRESENT
            return True
    return False

def isWordVariant(wrd,v):
    """
    is an unknown word a variant of a known word? We expect the
    lower-case spelling of the unknown word.
    """
    # check for verb variants
    isVerbVar = isVerbVariant(wrd,v)
    # check non-verb forms. 
    l = len(wrd)
    # is word an adverb form of a known modifier?
    if (l >= 5) and  wrd.endswith("ly"):
        test = wrd[0 : l-2]
        rootKey = lkup(test,False)
        if checkProp(rootKey,WP_MOD):
            v.props |= WP_MOD
            if v.rootKey == 0:
                v.rootKey = rootKey
            return True
    # a simple plural of a noun (cat->cats) ?
    if (l >= 4) and  wrd.endswith("s"):
        test = wrd[:-1]
        rootKey = lkup(test,False)
        if checkProp(rootKey,WP_NOUN):
            v.props |= WP_NOUN
            if v.rootKey == 0:
                v.rootKey = rootKey
            return True
    return isVerbVar

def getScDesc(i):
    """ get synclass spelling for entry "i" """
    # most tests based on word props, but some require that we look at
    # the spelling
    sp = getSpelling(i)
    if checkProp(i,WP_DETS):
        return "DetS"
    # conjunctions
    if sp == 'and' or sp == 'or':
        return "AndOr"
    if checkProp(i,WP_CONJ):
        return "Conj"
    if checkProp(i,WP_QUERY):
        return "Query"
    if checkProp(i,WP_GERUND):
        return "Ger"
    # collect classes for this entry (there may be > 1)
    l = []
    # determinants
    if checkProp(i,WP_DETW):
        l.append("DetW")
    # preps
    if checkProp(i,WP_CLPREP):
        l.append("ClPrep")
    elif checkProp(i,WP_QUALPREP):
        l.append("QualPrep")
    elif checkProp(i,WP_PREP):
        l.append("Prep")
    # nouns
    if checkProp(i,WP_NOUN):
        l.append("Noun")
    # names
    if checkProp(i,WP_N|WP_PRONOUN):
        l.append("N")
    # mods
    if checkProp(i,WP_MOD):
        l.append("Mod")
    # verb-adjuncts and verbs
    if checkProp(i,WP_VERB_PROPS):
        if checkProp(i,WP_VADJ):
            l.append("VAdj")
        else:
            l.append("V")
    if len(l) == 0:
        l.append("X")
    return '|'.join(l)

def getVocab(sp):
    """ get entry for word "sp", create if needed """
    ix = lkup(sp,False)
    if ix != 0:
        return ix
    ix = lkup(sp,True)
    # need a def for this word. Does the lower case version exist?
    spLc = sp.lower()
    if spLc != sp:
        ixLc = lkup(spLc,False)
        if ixLc != 0:
            # this is our def. Set and transfer props
            setDef(ix,ixLc)
            setProp(ix,getProps(ixLc))
            synClass[ix] = synClass[ixLc]
            return ix
    # is this word a variant of a known word?
    wv = WordVariant()
    if isWordVariant(spLc,wv):
        setDef(ix,wv.rootKey)
        setProp(ix,wv.props)
        synClass[ix] = scDct.lkup(getScDesc(ix),False)
        assert synClass[ix] != 0
        return ix
    # define to self
    setDef(ix,ix)
    synClass[ix] = scDct.lkup("X",False)
    return ix

def spellWrds(wrds):
    """ spell out a sequence of dictionary indices """
    if len(wrds)==0:
        return ''
    buf = getSpelling(wrds[0])
    i = 1
    while i < len(wrds):
        sp = getSpelling(wrds[i])
        i += 1
        clast = buf[len(buf)-1]
        if clast.isalnum() and sp[0].isalnum():
            buf += ' '
        buf += sp
    reWantSp1 = re.compile(r'([\.\?\!\;\:\-\)]+)(\w+)')
    buf = reWantSp1.sub(r'\1 \2',buf)
    reWantSp2 = re.compile(r'(\w+)([\$])')
    buf = reWantSp2.sub(r'\1 \2',buf)
    return buf

def getScN():
    """ get number of syn-classes """
    return scDct.getN()

def getScSpelling(i):
    """ get spelling for syntax class """
    return scDct.getSpelling(i)

def getScIx(scSp):
    """ get index for sc, given its spelling """
    return scDct.lkup(scSp,False)

def scSeqToStr(seq):
    """ get string representation for sc sequence """
    return ' '.join([getScSpelling(i) for i in seq])
# TODO: remove these 2
def isScForVerb(i):
    """ is "sc" a synclass for a verb? """
    return scDct.checkProp(i,WP_VERB)

def checkScProp(scIx, m):
    """ check props (WP_xxx) for sc's """
    return scDct.checkProp(scIx,m)

def printRewriteRule(r):
    """ print a rewrite rule """
    nLhs = r[0]
    nRhs = r[1]
    # lhs
    offset = 2
    for j in range(0,nLhs):
        print getSpelling(r[offset]),' ',
        offset += 1
    print ' : ',
    for j in range(0,nRhs):
        print getSpelling(r[offset]),' ',
        offset += 1
    print ""

def printRewriteRules(self):
    """ print the rewrite rules """
    print "lexicon rewrite rules:"
    for ruleSet in rwrules:
        if ruleSet != None:
            for r in ruleSet:
                printRewriteRule(r)

def printPrepsForVerbs(self):
    """ print prep->{verb} mapping. """
    print "Preps-for-verbs:"
    for i in range(getN()):
        verbs = prepToVerbs[i]
        if verbs != None:
            print getSpelling(i),':',
            for v in verbs:
                print ' ', getSpelling(v),
            print ""

def printEntries(maxEntries):
    """ print first "maxEntries" entries """
    print "N: ",getN()
    if maxEntries > getN():
        maxEntries = getN()
    for i in range(0,maxEntries):
        print str(i) , "." , getSpelling(i) , " ",
        print "def: " , getDef(i) , " ",
        print "props: " , WPtoStr(getProps(i))
    printRewriteRules()
    printPrepsForVerbs()

def printWrdInfo(sp):
    """ print info about a word """
##    i = lkup(sp,False)
##    if i == 0:
##        print "no entry"
##        return
    i = getVocab(sp)
    print "ix:" , str(i) ,
    print "def:" , getDef(i) ,
    print "spDef:" , getSpelling(getDef(i)) ,
    print "props:" , WPtoStr(getProps(i))
    scIx = synClass[i]
    print "sc:" , getScSpelling(scIx),
    scProps = scDct.props[scIx]
    print "scProps:", WPtoStr(scProps),
    if rwrules[i] != None:
        print "rewrite rules:"
        for r in rwrules[i]:
            printRewriteRule(r)
    verbs = prepToVerbs[i]
    if verbs != None:
        print "prep->{verbs}"
        for v in verbs:
            print getSpelling(v), " ",
        print ""
    print ""

def printSynClasses():
    """ print syn-classes, plus first 12 entries assigned to that class """
    cases = []
    for i in range(0,getScN()):
        cases.append([])
    for i in range(getN()):
        sc = synClass[i]
        myCases = cases[sc]
        if len(myCases) < 12:
            myCases.append(getSpelling(i))
    for i in range(getScN()):
        print str(i), getScSpelling(i)
        myCases = cases[i]
        if len(myCases) < 6:
            print ' '.join(myCases)
        else:
            print ' '.join(myCases[0:6])
            print ' '.join(myCases[6:])

def unitTest():
    """
    read vocab, then loop on user input, printing info about
    words.
    """
    serialize("r")
    while True:
        wrd = raw_input("Enter word: ")
        if wrd == 'q' or wrd == "quit":
            return
        printWrdInfo(wrd)
        print ''

if __name__== '__main__':
    unitTest()
    
