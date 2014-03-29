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

import re
from defs import *
import vcb

"""
Lexer for the package. We break the source up into "blocks"
(convenient chunks for parsing), then turn sequences of words and
punctuation into sequences of tokens (indices into our vocubulary
dictionary)
"""
# the source we're going to lex
src = None
# mapping, source index-> line number
lnoMap = None
# mapping, source index-> column number
colMap = None
# lexing functions

def isWrdChar(i,E,src):
    """
    is src[i] a word char? Letters a word chars, as are digits and a
    few other chars.
    """
    if i>E:
        return False
    c = src[i]
    if c.isalnum() or c=="_" or c=='\'':
        return True
    if c == '-':
        # is this a hyphen?
        return (i>0) and src[i-1].isalnum() and \
            (i+1 <= E) and src[i+1].isalnum()
    return False

def isDotLetterSeq(i,E,src):
    """
    helper for "lexWrd": is src[i] a period followed by a single
    letter/digit?
    """
    if i+2<=E and src[i] == '.' and src[i+1].isalnum():
        return i+2 >= E or not src[i+2].isalnum()
    return False

def lexWrd(i,E,src):
    """ lex a word, starting at src[i]: return index of last char """
    # lex numbers: "1,200.00". Here we accept periods and commas.
    S = i
    if src[i].isdigit():
        while i+1<E:
            if src[i+1].isdigit():
                i += 1
                continue
            if src[i+1] == '.' or src[i+1] == ',':
                if src[i].isdigit() and \
                    i+2<=E and src[i+2].isdigit():
                    i += 2
                    continue
            break
        while isWrdChar(i+1,E,src):
            i += 1
        return i
    # abbreviations like "B.C.", "U.S.A"
    if isDotLetterSeq(i+1,E,src):
        while isDotLetterSeq(i+1,E,src):
            i += 2
        # include trailing "." if present
        if i+1 <= E and src[i+1] == '.':
            i += 1
        return i
    # default cases: just consume all word chars
    while isWrdChar(i+1,E,src):
        i += 1
    # is this "Mr."? May need to bind a trailing period.
    if i+1<=E and src[i+1]=='.':
        sp = src[S:i+1]
        tok = vcb.lkup(sp.lower(),False)
        if vcb.checkProp(tok,WP_ABBREV):
            i += 1
    return i

def appendContract(S,sp,toks,tokLoc):
    """ append token(s) for word "sp", expanding contractions as needed """
    # is there a rewrite rule for this word?
    key = vcb.lkup(sp.lower(),False)
    if key != 0 :
        test = [key]
        rule = vcb.findRewrite(test,0)
        if rule != None:
            rhs = vcb.getRhsRewrite(rule,sp[0].isupper())
            for e in rhs:
                toks.append(e)
                tokLoc.append(S)
        return
    # split on ticks
    terms = sp.split("'")
    if len(terms) == 2:
        # some canonical cases: exceptions are handled by rewrite
        # rules
        t0 = terms[0]
        t1 = terms[1]
        t0lc = t0.lower()
        t1lc = t1.lower()
        l0 = len(t0)
        if l0 > 2 and t0lc.endswith('n') and t1lc == 't' :
            # "wouldn't"
            toks.append(vcb.getVocab(t0[0:l0-1]))
            toks.append(vcb.getVocab("not"))
            tokLoc.extend((S,S))
            return
        if l0 >= 1 and t1lc == 're' :
            # "we're"
            toks.append(vcb.getVocab(t0))
            toks.append(vcb.getVocab("are"))
            tokLoc.extend((S,S))
            return
        if l0 >= 1 and t1lc == 'll' :
            # "we'll"
            toks.append(vcb.getVocab(t0))
            toks.append(vcb.getVocab("will"))
            tokLoc.extend((S,S))
            return
        if l0 >= 1 and t1lc == 've' :
            # "we've"
            toks.append(vcb.getVocab(t0))
            toks.append(vcb.getVocab("have"))
            tokLoc.extend((S,S))
            return
        # "'s" and "'d" are context dependant and are resolved during
        # the parse
        if t1lc == 's' or t1lc == 'd' :
            toks.append(vcb.getVocab(t0))
            toks.append(vcb.getVocab("'" + t1))
            tokLoc.extend((S,S))
            return
    # default is to accept construct as a single word
    toks.append(vcb.getVocab(sp))
    tokLoc.append(S)

def applyRewriteRules(toks,tokLoc):
    """ rewrite token sequence, applying rewrite rules """
    _toks = toks
    _tokLoc = tokLoc
    toks = []
    tokLoc = []
    i = 0
    while i<len(_toks):
        rule = vcb.findRewrite(_toks,i)
        if rule != None:
            # For token-location, we have to approximate. All terms in
            # the rewrite are assigned location of first term of lhs,
            # except for last term in the rewrite; that gets location
            # of last term in lhs.
            nLhs = rule[0]
            SfirstTerm = _tokLoc[i]
            SlastTerm = _tokLoc[i+nLhs-1]
            wantUpper = vcb.getSpelling(_toks[i]).isupper()
            terms = vcb.getRhsRewrite(rule,wantUpper)
            for j in range(0,len(terms)):
                S = SlastTerm if j == len(terms) -1 else SfirstTerm
                toks.append(terms[j])
                tokLoc.append(S)
            i += nLhs
        else:
            toks.append(_toks[i])
            tokLoc.append(_tokLoc[i])
            i += 1
    return (toks,tokLoc)

def canbeProperName(i,toks):
    if i>=len(toks):
        return False
    sp = vcb.getSpelling(toks[i])
    if len(sp)>1 and sp[0].isupper() and sp[1].islower():
        # Camel case. If this word is known to our vocabulary, we in
        # general reject it; exception is for words marked as names.
        props = vcb.getProps(toks[i])
        if (props & WP_N) != 0:
            return True
        return props == 0
    return False

def canbeMI(i,toks):
    if i+1>=len(toks):
        return False
    sp = vcb.getSpelling(toks[i])
    spnxt = vcb.getSpelling(toks[i+1])
    return len(sp)==1 and sp[0].isupper() and spnxt=='.'

def rewriteProperNames(toks,tokLoc):
    """ rewrite token sequence, so "John F.Kennedy" becomes a single token """
    _toks = toks
    _tokLoc = tokLoc
    toks = []
    tokLoc = []
    i = 0
    while i<len(_toks):
        if canbeProperName(i,_toks):
            S = i
            E = i
            spSeq = [vcb.getSpelling(_toks[S])]
            while True:
                if canbeProperName(E+1,_toks):
                    spSeq.append(vcb.getSpelling(_toks[E+1]))
                    E += 1
                    continue
                if canbeMI(E+1,_toks):
                    spSeq.append(vcb.getSpelling(_toks[E+1])+'.')
                    E += 2
                    continue
                break
            if E > S:
                spAll = ' '.join(spSeq)
                toks.append(vcb.getVocab(spAll))
                tokLoc.append(_tokLoc[i])
                i = E + 1
                continue
        toks.append(_toks[i])
        tokLoc.append(_tokLoc[i])
        i += 1
    return (toks,tokLoc)

def lex(parseblk):
    """
    tokenize source text in the region spanned by "parseblk". Returns
    (toks,tokLoc). "toks" is a list of tokens (indices into the
    vocabulary's dictionary. "tokLoc[i]" gives the index in the source
    text for the first character of the i_th token.
    """
    S = parseblk.S
    E = parseblk.E
    if (src==None) or (E<S):
        return ([],[])
    toks = []
    tokLoc = []
    _getVocab = vcb.getVocab
    i = S
    while i <= E:
        # Consume white space.
        c = src[i]
        if (c==' ') or (c=='\t') or \
            (c=='\r') or (c=='\n'):
            i += 1
            continue
        # start index for this token
        S = i
        if src[i] == '-':
            # multiple dashes lex as a single token
            while i <= E and src[i] == '-':
                i += 1
            toks.append(_getVocab(src[S:i]))
            tokLoc.append(S)
            continue
        if src[i] == '$' and isWrdChar(i+1,E,src):
            # $ binds to the word that follows: advance i and fall
            # thru to code below.
            i += 1
        if isWrdChar(i,E,src):
            # a word
            ixE = lexWrd(i,E,src)
            sp = src[S:ixE+1]
            if sp.count("'") == 0:
                toks.append(vcb.getVocab(sp))
                tokLoc.append(i)
            else:
                appendContract(i,sp,toks,tokLoc)
            i = ixE + 1
            continue
        # everything else lexes as a single token.
        toks.append(_getVocab(src[i]))
        tokLoc.append(S)
        i += 1
    # rewrite as per the rules defined in "vcb.txt"
    toks,tokLoc = applyRewriteRules(toks,tokLoc)
    # collapse "John F. Kennedy" into a single token
    return rewriteProperNames(toks,tokLoc)

def isOpener(v):
    """ does 'v' open a nested scope? """
    return v=='(' or v=='{' or v=='[' or v=='\'' or v=='"'

def findCloser(_src,i,imax):
    """ find close for nested scope """
    opener = _src[i]
    closer = opener
    i += 1
    if i>imax:
        return -1
    if opener == '{':
        closer = '}'
    elif opener == '[':
        closer = ']'
    elif opener == '(':
        closer = ')'
    while i<=imax:
        if _src[i]==closer:
            return i
        if isOpener(_src[i]):
            E = findCloser(_src,i,imax)
            if E == -1:
                i += 1
            else:
                i = E + 1
            continue
        i += 1
    return -1

def _getParseBlks(_src, i, imax):
    """
    Recursively break a region of "_src" into a sequence of blocks for
    parsing.
    """
    lst = []
    while i <= imax:
        if isOpener(_src[i]):
            E = findCloser(_src,i,imax)
            if E == -1:
                # malformed: skip this character and continue
                i += 1
                continue
            # A quote or parenthesized text.Get content
            content = _getParseBlks(_src,i+1,E-1)
            if len(content) > 0:
                # exclude the quotes or parens from the span for the
                # block
                blk = Nd(i+1,E-1)
                blk.sublst = content
                lst.append(blk)
        else:
            E = i
            while E+1<=imax :
                if isOpener(_src[E+1]):
                    break;
                E += 1
            blk = Nd(i,E)
            lst.append(blk)
        i = E + 1
    return lst

def getParseBlks(sourceText,lno):
    """
    Break source into a sequence of blocks for parsing. "sourceText"
    is a chunk taken from some larger text. "lno" gives the line
    number at which this chunk starts.
    """
    global lnoMap, colMap, src
    # save ref to source and create the line and column mappings.
    src = sourceText
    lnoMap = []
    colMap = []
    col = 1
    for c in src:
        lnoMap.append(lno)
        colMap.append(col)
        col += 1
        if c == '\n':
            lno += 1
            col = 1
    # create the parse blocks. First create a version of the source in
    # which contraction ticks are encoded to '~'. (Some texts use
    # single ticks as quote marks, creating confusion between quote
    # marks and contraction ticks. So we rewrite contraction ticks.)
    _src = src[:]
    _src = re.compile(r"(\w+)'(\w+)").sub(r'\1~\2',_src)
    _src = re.compile(r"''(\w+)").sub(r"'~\1",_src)
    _src = re.compile(r"(\w+)''").sub(r"\1~'",_src)
    # some irregular forms
    _src = _src.replace("'em","~em")
    _src = _src.replace("'tis","~tis")
    _src = _src.replace("'twas","~twas")
    return _getParseBlks(_src,0,len(_src)-1)
# Unit testing lex a list of parse blocks and print result
def _utLexParseBlks(blkLst,depth):
    indent = '';
    for i in range(0,depth):
        indent += '   '
    for b in blkLst:
        print indent + "blkS: " + str(b.S) + " blkE: " + str(b.E)
        if b.sublst != None:
            print indent + "sublst:"
            _utLexParseBlks(b.sublst,depth+1)
            continue
        toks,tokLoc = lex(b)
        for i in range(0,len(toks)):
            S = tokLoc[i]
            l = []
            l.append(indent)
            l.append(vcb.getSpelling(toks[i]))
            l.append("lno:")
            l.append(str(lnoMap[S]))
            l.append("col:")
            l.append(str(colMap[S]))
            print ' '.join(l)
        print ""
# unit test: tokenize some text and print result
if __name__== '__main__':
    dn = os.path.dirname(os.path.realpath(__file__))
    # This test requires "map.dat", which contains the
    # serialized vocabulary.
    fn = os.path.join(dn,"msp.dat")
    serializer.init(fn,mode)
    version = serializer.decodeStr()
    vcb.serialize("r")
    serializer.fini()
    # xt = '"That\'s stupid," said Dr. Who (laughing wildly).' xt =
    # '$12 1,20.0 $1,200.00 Dr. Who said' xt = '$12,000. 16,000.00' xt
    # = "I saw John F. Kennedy at the White House." xt = 'C.I.A B.C.
    # AB A.B.C..' xt = "Hello. John Kennedy died in 1963."
    txt = "I wouldn't"
    _utLexParseBlks(getParseBlks(txt,1),0)
