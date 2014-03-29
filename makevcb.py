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
Initialize vocabulary from "lexicon.txt", an ascii file containing
information about words (lists of verbs, etc.).
"""

import re
from defs import *
import vcb
from vcb import WordVariant
import serializer
import parser
import os


# utility function
def sortLstLst(lstLst):
    """ sort a list of int-lists by length """
    for i in range(0,len(lstLst)-1):
        for j in range(i+1,len(lstLst)):
            I = lstLst[i]
            J = lstLst[j]
            if len(I) < len(J):
                lstLst[i] = J
                lstLst[j] = I

def addRule(terms):
    """ add a rewrite rule """
    # create the rule.
    rule = []
    # First 2 elements reserved for len-lhs and len-rhs
    rule.append(0)
    rule.append(0)
    # len, current side
    nTerms = 0
    for i in range(0,len(terms)):
        if terms[i] == ":":
            # end of lhs
            rule[0] = nTerms
            nTerms = 0
            continue
        rule.append(vcb.define(terms[i],0,0))
        nTerms +=1
    rule[1] = nTerms
    # install the rule in the collection of rules for the first term
    # in the lhs.
    t0 = rule[2]
    if vcb.rwrules[t0] == None:
        vcb.rwrules[t0] = []
    vcb.rwrules[t0].append(rule)

def sortRewriteRules(vcb):
    """ sort the rewrite rules """
    for ruleset in vcb.rwrules:
        if ruleset != None:
            sortLstLst(ruleset)

def addPrepToVerbs(terms):
    """ add a prep->{verb} mapping """
    # get prep
    vPrep = vcb.define(terms[0],WP_PREP,0)
    # collect verbs
    i = 2        # skip ":" after prep
    verbs = []
    while i<len(terms):
        vkey = vcb.lkup(terms[i],False)
        if vkey is 0 or not vcb.checkProp(vkey,WP_ROOT):
            # print 'prepToVerbs: skipped %s,%s' %(terms[0],terms[i])
            pass
        else:
            verbs.append(vcb.define(terms[i],WP_ROOT,0))
        i += 1
    vcb.prepToVerbs[vPrep] = verbs

def define(sp,props):
    """
    create entry for word and set props. If word is already defined,
    just add the props to the existing entry
    """
    key = vcb.lkup(sp,False)
    if key != 0:
        vcb.setProp(key,props)
        return
    key = vcb.define(sp,props,0)
    _def = vcb.getDef(key)
    if _def == key:
        # is this word a variant of some other entry?
        v = WordVariant()
        if vcb.isWordVariant(sp,v):
            vcb.setDef(key,v.rootKey)
            vcb.setProp(key,v.props)

def defineWords(props,root,lst):
    """
    define a group of words: props and root apply to all
    members in list
    """
    for sp in lst.split():
        vcb.define(sp,props,root)
        
def readLexicon():
    """ Get lines from the ASCII file of lexical info """
    # This code assumes the ascii file "lexicon.txt" lives
    # in the same directory as this script.
    dn = os.path.dirname(os.path.realpath(__file__))
    f = open(os.path.join(dn,"lexicon.txt"),'r')
    fstr = f.read()
    f.close()
    fstr = fstr.replace('\r',' ')
    rePlus = re.compile(r'\+[ ]*\n')
    fstr = rePlus.sub(' ',fstr);
    return fstr.split('\n')

def addVerb(terms):
    """
    Add a verb. First word is the root. If verb is irregular,
    remaining terms are:
    3rdPersonPresent past-simple past-perfect gerund. Ex:
    "go goes went gone going".
    """
    rootKey = \
        vcb.define(terms[0], WP_VERB|WP_ROOT|WP_PRESENT,0)
    i = 1
    if i<len(terms) and terms[i] != ':':
        # forms for verbs "goes"
        vcb.define(terms[i], WP_VERB|WP_PRESENT,rootKey)
        i += 1
        # "went"
        vcb.define(terms[i], WP_VERB|WP_PAST,rootKey)
        i += 1
        # "gone"
        vcb.define(terms[i], WP_VERB|WP_PAST,rootKey)
        i += 1
        # "going"
        vcb.define(terms[i], WP_VERB|WP_GERUND,rootKey)
        i += 1
    if i<len(terms):
        # get syntax form
        i += 1
        if terms[i] =="AVE":
            vcb.setProp(rootKey,WP_AVE)
        elif terms[i] == "EVT":
            vcb.setProp(rootKey,WP_EVT)
        elif terms[i] == "AVGT":
            vcb.setProp(rootKey,WP_AVGT)
        elif terms[i] == "VPQ":
            vcb.setProp(rootKey,WP_VPQ)
        else:
            assert False
            
def assignSynclasses():
    """
    assign a syntax class to each word in the vocabulary
    """
    vcb.synClass = [0]
    for i in range(1,vcb.getN()):
        sp = vcb.getSpelling(i)
        scIx = vcb.scDct.lkup(sp,False)
        if scIx == 0:
            scDesc = vcb.getScDesc(i)
            scIx = vcb.scDct.lkup(scDesc,False)
            if scIx == 0:
                print \
                    "Warning: could not assign syntax class to \"%s\"" % \
                    sp
                scIx = vcb.scDct.lkup('X',False)
        vcb.synClass.append(scIx)
    debug = 1
            
def createVcb():
    """ initialize vocabulary from an ASCII file of lexical info """
    # reallocate data structures: the make process will have
    # read in old versions.
    vcb.dct = vcb.Dict()
    vcb._def = []
    vcb.synClass = []
    vcb.rwrules = []
    vcb.prepToVerbs = []
    # By convention an index of "0" means "no entry" on a lookup. Make
    # a dummy entry for 0, so any subsequent entries will have key > 0
    vcb.dct.lkup('_NULL_',True)
    vcb._def.append(0);
    vcb.synClass.append(0)
    vcb.rwrules.append(None)
    vcb.prepToVerbs.append(None)
    # create entries for various forms of "be": be being am are is was
    # were been
    rootKey = vcb.define("be", \
        WP_VERB|WP_ROOT|WP_PRESENT,0)
    vcb.define("being",WP_VERB|WP_GERUND,rootKey)
    # present tense forms. "'s" is a contraction for "is"
    defineWords(WP_VERB|WP_PRESENT,rootKey,\
        "am are is 's")
    # past tense forms
    defineWords(WP_VERB|WP_PAST,rootKey,
        "was were been")
    # create entry for "'d" as a verb adjunct
    vcb.define("'d",WP_VADJ,0)
    # create entries for "and" and "or"
    defineWords(WP_CONJ,0,
        "and or")
    # create entries for verb-phrase-adjuncts
    defineWords(WP_VADJ,0,
        "will shall would should may might ought")
    vcb.define("can",WP_VADJ|WP_PRESENT,0)
    vcb.define("could",WP_VADJ|WP_PAST,0)
    # create entries for words mapping to distinct synclasses
    for sp in vcb.scSingletons:
        vcb.define(sp,0,0)
   
    # read additional lexical info from file.     state = ""
    props = 0
    lines = readLexicon()
    for line in lines:
        line = line.strip()
        if line.startswith("/"):
            continue;
        if line.startswith(">>Version"):
            vcb.version = line[len(">>Version"):].strip()
            continue
        terms = line.split()
        if len(terms) == 0:
            continue;
        w0 = terms[0]
        if w0[0] == ">":
            if w0 == ">>Rewrite":
                state = w0
            elif w0 == ">>Verbs":
                state = w0
            elif w0 == ">>Contractions":
                state = w0
            elif w0 == ">>PrepVerbs":
                state = w0
            else:
                # everything else sets a prop for a word.
                state = "props"
                if w0 == ">>Nouns":
                    props = WP_NOUN
                elif w0 == ">>Conjunctions":
                    props = WP_CONJ
                elif w0 == ">>DetStrong":
                    props = WP_DETS
                elif w0 == ">>DetWeak":
                    props = WP_DETW
                elif w0 == ">>Names":
                    props = WP_N
                elif w0 == ">>Pronouns":
                    props = WP_N|WP_PRONOUN
                elif w0 == ">>Abbrev":
                    props = WP_ABBREV
                elif w0 == ">>Modifiers":
                    props = WP_MOD
                elif w0 == ">>Prepositions":
                    props = WP_PREP
                elif w0 == ">>ClausePreps":
                    props = WP_CLPREP
                elif w0 == ">>QualPreps":
                    props = WP_QUALPREP
                elif w0 == ">>Query":
                    props = WP_QUERY
                else:
                    assert False, \
                        "malformed file: \"" + fn +"\" (unknown control)"
            continue
        if state == "props":
            if len(terms) > 1 and props != WP_ABBREV:
                # create respell rule mapping multiple tokens to a
                # single token, then set the props for the single
                # token
                lhs = ' '.join(terms)
                terms.append(":")
                terms.append(lhs)
                addRule(terms)
                w0 = lhs
            define(w0, props)
        elif state == ">>Verbs":
            addVerb(terms)
        elif state == ">>Contractions" or \
            state == ">>Rewrite":
            # For the contraction case, mark the word as a
            # contraction.
            if state == ">>Contractions":
                rootKey = vcb.define(w0,WP_CONTRACTION,0)
            addRule(terms)
        elif state == ">>PrepVerbs":
            addPrepToVerbs(terms)
    
    # end loop over lines

    # sort rewrite rules
    sortRewriteRules(vcb)

if __name__== '__main__':
    # read "msp.dat"
    serializer.init("msp.dat",'r')
    parser.serialize('r')
    serializer.fini()
    # re-create the vocabulary from the ascii file "lexicon.txt"
    createVcb()
    assignSynclasses()
    # write out "msp.dat"
    serializer.init("msp.dat",'w')
    parser.serialize('w')
    serializer.fini()
    print 'rewrote "msp.dat"'
##    # enable this code to test interactively
##    print 'Testing vocab: enter "q" to quit'
##    vcb.unitTest()
##    vcb.printSynClasses()
