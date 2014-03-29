"""
This module implements regular-expression matching for the parser. The
match method accepts a sequence of terms ("src") and a string
representation of a regexpr ("re"). Each re term matches to zero or
more src terms. If the match is successful, the method returns true
and write the match results to "matchResult".

Qualifiers:
re terms accept the qualifiers "?" , "+", and "*".

"?" means the term is optional. If including this term in the matched
sequence yields a complete match, we include it; if excluding the term
yields a complete match, we exclude it.

"*" means "zero or more", "+" means "one or more". The match is
semi-greedy. In general an re term consumes as many source terms as it
can; but if consuming less allows us to complete the match, then it
yields the minimal number of required terms to its successors.

Variants:
An re term containing bars ("a|b|c") specifies three match variants
("a","b", or "c"). We always accept the first term in the variants
list that yields a match.Note that if a qualifier appears at the end
of a variants list, it applies to the list as a whole. It's illegal to
qualify a term inside a variants list: you can't say "A|B?|C".

Nested re's:
Surrounding one or more terms with square brackets specifies a nested
re. You can also declare an re ("%myName") using "declRe" and then
refer to it in another re.

class ReMatch is abstract: you must implement the "matchTerm" method.
"""
import lexer
import re
# qualifiers for re terms
_isOption = 0x1
_zeroOrMore = 0x2
_oneOrMore = 0x4

class ReMatch:
    def __init__(self):
        self.matchResult = None
        self.reDict = {}

    def matchTerm(self,state,reTerm):
        """
        Match terms in src, against the reTerm. Returns None if
        no-match; otherwise it returns a list of the src terms
        consumed in the match. This method is a stub: derived classes
        should override.
        """
        return None

    def getInitialState(self):
        """
        Get initial state for a match. "State" specifies our current
        location in the source. In the default version, "src" is a
        list of nodes, and "state" is just an index into the list.
        """
        return 0

    def updateState(self,state,consumed):
        """
        Update state: "consumed" contains the source terms just
        consumed in matching a term. Returns the updated state. In the
        default version, "src" is a list of nodes, and "state" is just
        an index into the list.
        """
        return state + len(consumed)

    def match(self,_src,_re):
        """
        match a list of terms in "src" against a regular expression.
        Returns True if the match is complete, and writes the match
        terms to "matchResult". There's one element in matchResult for
        each element in the re. Each element is a list, and contains
        the term(s) that matched the re term.
        """
        self.src = _src
        self.matchResult = []
        reLst = self.reDict.get(_re)
        if reLst is None:
            # compile the re and install in the dictionary
            reLst = self.compileRe(_re)
            self.reDict[_re] = reLst
        return self.matchLst(\
            self.getInitialState(),\
            reLst,self.matchResult)

    def compileReTerm(self,variants,src,i):
        """
        Helper for "compileRe": compile a term and add to variants
        list
        """
        lsrc = len(src)
        c0 = src[i]
        if c0 == '[':
            # nested re
            E = lexer.findCloser(src,i,len(src)-1)
            assert E != -1
            reName = '%' + src[i:E+1]
            self.declRe(reName,src[i+1:E])
            variants.append(reName)
            return E+1
        # id's can start with "%" (that's the name of a nested re). We
        # also allow underscores, ":", and "!".
        if c0=='%' or c0=='_' or c0.isalnum() or c0 == '!' or c0 == ':':
            # grab id chars
            E = i
            while (E+1)<lsrc and \
                (src[E+1].isalnum() or \
                src[E+1] == '_' or \
                src[E+1] == ':' or \
                src[E+1] == '!'):
                E += 1
            variants.append(src[i:E+1])
            return E+1
        if c0 == '.':
            # match any
            variants.append('.')
            return i+1
        # error
        assert False,"Malformed reg.expr"

    def compileRe(self,src):
        """ compile re from source """
        # "reLst" is a list of match-terms. Each term is a pair:
        # [props,variants]. props gives the qualifiers (if any) and
        # variants is a list of variants for the term.
        reLst = []
        # canonicalize space
        src = src.strip()
        reBar = re.compile(r'\s*\|\s*')
        src = reBar.sub('|',src)
        lsrc = len(src)
        i = 0
        while i<lsrc:
            while src[i] == ' ':
                i += 1
                continue
            variants = []
            term = [0,variants]
            reLst.append(term)
            # collect alternatives for this term
            while i<lsrc:
                i = self.compileReTerm(variants,src,i)
                if i>=lsrc:
                    break
                c = src[i]
                i += 1
                if c == '|':
                    # get additional alternatives
                    continue
                # if c is a qualifier, it ends the term
                if c == '*':
                    term[0] = _zeroOrMore
                elif c == '+':
                    term[0] = _oneOrMore
                elif c == '?':
                    term[0] = _isOption
                # this term is complete: advance to next
                break
        return reLst

    def declRe(self,reName,_re):
        """
        declare an re: it can then appears as a term in a larger re.
        Our convention requires that name start with "%".
        """
        assert reName.startswith("%")
        self.reDict[reName] = self.compileRe(_re)

    def matchLst(self,state,reLst,matLst):
        """
        Match terms in src against terms in "reLst". Returns True if
        the match is complete, and writes the match terms to "matLst".
        There's one element in matLst, for each element in the re.
        """
        ixRe = len(matLst)
        if ixRe == len(reLst):
            # the match is complete
            return True
        # Loop thru match terms until we hit a qualified term (or are
        # match complete)
        while True:
            (props,variants) = reLst[ixRe]
            if props != 0:
                break
            terms = self.matchVariants(state,variants)
            if terms is None:
                # match failed
                return False
            matLst.append(terms)
            state = self.updateState(state,terms)
            ixRe += 1
            if ixRe == len(reLst):
                # the match is complete
                return True
        # The match term is qualified, so there are multiple ways
        # source terms can be matched to it. Each way is called a
        # "mode". Find all possible modes.
        modes = []
        termsConsumed = []
        if props & (_zeroOrMore|_isOption):
            modes.append([])
        statex = state
        while True:
            terms = self.matchVariants(statex,variants)
            if terms is None:
                break
            termsConsumed.extend(terms)
            modes.append(termsConsumed[:])
            statex = self.updateState(statex,terms)
            if props & _isOption:
                break
        if len(modes) == 0:
            # There's no way to match this term: match has failed
            return False
        # Find the longest mode that completes the match.
        nMatLst = len(matLst)
        i = len(modes)-1
        while i >= 0:
            # purge matLst of terms added in previous iterations
            matLst[:] = matLst[:nMatLst]
            # accept the match associated with this mode, then try to
            # complete the match.
            matLst.append(modes[i])
            newstate = self.updateState(state,modes[i])
            if self.matchLst(newstate,reLst,matLst):
                return True
            i -= 1
        # match failed
        return False

    def matchVariant(self,state,v):
        """ Match a variant """
        if v.startswith('%'):
            # a nested re
            terms = []
            if not self.matchLst(state,self.reDict[v],terms):
                return None
        else:
            terms = self.matchTerm(state,v)
            if terms is None:
                return None
        leaves = []
        self.getLeaves(leaves,terms)
        return leaves

    def matchVariants(self,state,variants):
        """
        Match terms in src, starting at term specified by "state",
        against the variants. Returns a list of the terms consumed in
        the match: None means no-match. The method searches the
        variants list in left-to-right order, and accepts the first
        successful variant encountered.
        """
        for v in variants:
            terms = self.matchVariant(state,v)
            if terms is not None:
                return terms
        return None

    def getLeaves(self,leaves,tree):
        """ linearize a tree (or list of trees) """
        if isinstance(tree,list):
            for e in tree:
                self.getLeaves(leaves,e)
        else:
            leaves.append(tree)
    # test/dev
    def dumpMatch(self):
        for i in range(len(self.matchResult)):
            tmp = [str(e.h) for e in self.matchResult[i]]
            print '%d. %s' % (i, ','.join(tmp))
# unit testing this subclass implements "matchTerm"
class _utMatch(ReMatch):
    def __init__(self):
        ReMatch.__init__(self)

    def matchTerm(self,state,reTerm):
        if state < len(self.src) and self.src[state] == reTerm:
            return [self.src[state]]
        return None

if __name__ == '__main__':
    # Unit test
    utm = _utMatch()
    assert utm.match(['a','b'],"a b")
    assert utm.matchResult == [['a'],['b']]

    assert not utm.match(['a','c'],"a b")

    assert utm.match(['a','b'],"c? a b")
    assert utm.matchResult == [[],['a'],['b']]

    assert utm.match(['a','b'],"a? a b")
    assert utm.matchResult == [[],['a'],['b']]

    assert utm.match(['a','b'],"a c* b")
    assert utm.matchResult == [['a'],[],['b']]

    assert utm.match(['a','b', 'b'],"a b*")
    assert utm.matchResult == [['a'],['b','b']]

    assert utm.match(['a','b'],"a|b c* b")
    assert utm.matchResult == [['a'],[],['b']]

    assert utm.match(['c'],"c* c")
    assert utm.matchResult == [[],['c']]

    assert utm.match(['b','c'],"a|b c* c|b")
    assert utm.matchResult == [['b'],[],['c']]

    assert not utm.match(['b','c'],"a+ c")

    assert utm.match(['b','c'],"b+ c")
    assert utm.matchResult == [['b'],['c']]

    assert utm.match(['b','b','c'],"b+ c")
    assert utm.matchResult == [['b','b'],['c']]

    utm.declRe("%bc","b+ c")
    assert utm.match(['b','b','c'],"%bc")
    assert utm.matchResult == [['b','b'],['c']]

    utm.declRe("%ab","a b")
    utm.declRe("%abc","a b c")
    assert utm.match(['a','b','c','d'],"%abc|%ab d")
    assert utm.matchResult == [['a','b','c'],['d']]
    assert utm.match(['a','b','d'],"%abc|%ab d")
    assert utm.matchResult == [['a','b'],['d']]

    assert utm.match(['a','b','c'],"a [b c]")
    assert utm.matchResult == [['a'],['b','c']]

    print "pass unit test"
