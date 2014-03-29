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
from pg import Pn
import serializer
import vcb
import sys

"""
A SeqMap defines a set of (sequence->value) mappings. A sequence is an
ordered set of terms, drawn from the integers 0..maxTerm.  A value is a 
zero-based index.

A SeqMap recognizes sequences drawn from an "alphabet" (where the
"letters" are actually int's in the range 0..maxTerm), and is closely
related to a finite state machine. It consists of a matrix of cells.
nRows (number of rows) gives the length of the longest sequence that
can be recognized. nCols (number of columns) is the cardinality of the
alphabet, so it's just maxTerm+1.

Each cell has a transition table. Transitions are always from a cell
in row_i, to a cell in row_i+1. Suppose we recognize 2 sequences:
(1,22) and (1,33). Then all cells in row0 will be empty, except for
cell[0,1]. Its transition table will be the list [22,33]. This means
there are 2 possible transitions from this cell: one to cell[1,22],
the other to cell[1,33]. So there are 2 possible paths thru the
matrix: cell[0,1]->cell[1,22], and cell[0,1]->cell[1,33]. The first
path corresponds to the sequence (1,22), the second to the sequence
(1,33).

Each cell also has a checksum/value table. This is comprised of a list
of checksums ("cksLst"), and a parallel list of indices 
("vixLst"). The checksum list contains the checksums for all
sequences that terminate at the cell. The index list contains the
valueIndex's for all sequences that terminate at the cell. The two
lists are parallel: if the checksum for some sequence is the 3rd
element in the checksum list, then its valueIndex index will be the
3rd element in "vixLst".
"""

def computeCks(seq):
    """ compute checksum """
    sum1 = 0
    sum2 = 0
    i = 0
    while i < len(seq):
        x = seq[i]<<8
        if i+1 < len(seq):
            x |= seq[i+1]
        sum1 = (sum1+x) % 0xffff
        sum2 = (sum2+sum1) % 0xffff
        i += 2
    return (sum2<<16) | sum1

class SeqMap:
    """ A set of mappings, sequence->value. """
    def __init__(self):
        self.nRows = self.nCols = 0
        # These tables define the attributes of cells. They're all
        # indexed by "cellIx", where cellIx is the index (address) for
        # some cell. If the cell is at (rowIx,colIx), then its index
        # is rowIx*nCols + colIx. "trsTbl[cellIx]": a transition
        # table. Transitions are always to a cell in the next row, so
        # it suffices to specify the column-index (colIx) for the
        # destination cells. "trsTbl[cellIx]" is a list of column
        # indices for allowed transitions from a cell.
        self.trsTbl = []
        # "cksLstTbl[cellIx]": a list of checksums for sequences
        # ending at the cell.
        self.cksLstTbl = []
        # "vixLstTbl[cellIx]": a list of value-indices. It parallels
        # the checksum list: if some sequence ends at this cell, and
        # its checksum matches the 3rd element in "cksLst", then the
        # value-index for the sequence is the 3rd element in this
        # list.
        self.vixLstTbl = []

    def setDimensions(self,maxSeqLen,maxTerm):
        """
        set dimensions. maxSeqLen is the longest sequence we can
        recognize. maxTerm is the max value in a sequence.
        """
        self.nCols = maxTerm+1
        self.nRows = maxSeqLen
        order = self.nCols*self.nRows
        self.trsTbl = [None]*order
        self.cksLstTbl = [None]*order
        self.vixLstTbl = [None]*order

    def serialize(self,mode):
        """ serialize a sequence map """
        if mode == 'w':
            serializer.encodeInt(self.nRows)
            if self.nRows == 0:
                return
            serializer.encodeInt(self.nCols)
            serializer.encodeLstLst(self.trsTbl,8)
            serializer.encodeLstLst(self.cksLstTbl,32)
            serializer.encodeLstLst(self.vixLstTbl,16)
        else:
            self.nRows = serializer.decodeInt()
            if self.nRows == 0:
                return
            self.nCols = serializer.decodeInt()
            self.trsTbl = serializer.decodeLstLst(8)
            self.cksLstTbl = serializer.decodeLstLst(32)
            self.vixLstTbl = serializer.decodeLstLst(16)

    def validatePath(self,seq,createTransitions):
        """
        walk the path described by "seq". If "createPath", we create
        transitions as needed to perform the walk. Otherwise the walk
        terminates when it requires an undefined transition. If the
        walk reaches the end of the sequence, we return the index of
        the last cell reached; otherwise we return -1.
        """
        rowIx = 0
        colIx = seq[0]
        if len(seq) == 1:
            # no transitions required
            return colIx
        # do the walk.
        while True:
            # address of current cell
            curCellIx = rowIx*self.nCols + colIx
            # transitions from current cell
            trs = self.trsTbl[curCellIx]
            if trs is None:
                if not createTransitions:
                    # failed.
                    return -1
                # Create a transition set
                trs = self.trsTbl[curCellIx] = []
            # can we transit?
            dstColIx = seq[rowIx+1]
            if not dstColIx in trs:
                if not createTransitions:
                    # failed.
                    return -1
                # add the transition
                trs.append(dstColIx)
            # reset rowIx and colIx to the next cell
            rowIx += 1
            colIx = dstColIx
            if rowIx == len(seq)-1:
                # we reached the end of the walk
                return rowIx*self.nCols + colIx

    def getSeqValAtCell(self,seq,cellIx):
        """
        We've walked the matrix, as per the sequence, and reached a
        cell. This method returns the value associated with the
        sequence, at that cell.
        """
        if cellIx == -1:
            return None
        # compute checksum.
        cks = computeCks(seq)
        # Find index of "cks" in the checksum list for this cell
        cksLst = self.cksLstTbl[cellIx]
        if cksLst is not None:
            for i in range(len(cksLst)):
                if cks == cksLst[i]:
                    return self.vixLstTbl[cellIx][i]
        return None

    def get(self,seq):
        """ get value associated with sequence """
        if len(seq) == 0:
            return None
        # "validatePath" walks the matrix as per the sequence, and
        # returns the index of the final cell reached.
        return self.getSeqValAtCell(seq,\
                                    self.validatePath(seq,False))

    def defineEntry(self,seq,valueIx):
        """
        Associate an index into the value table with a sequence. If
        the (last cell, checksum) pair for the sequence already has a
        value-index, this is taken to be hash-collision; the new
        assignment is rejected and the method returns False. To
        contruct a sequence map, you should gather all the sequences
        into a comprehensive collection
        """
        if len(seq) == 0:
            return False
        assert isinstance(valueIx,int)
        cellIx = self.validatePath(seq,True)
        # compute checksum.
        cks = computeCks(seq)
        # "cell" is the last cell reached in the path. If "cks" is
        # already in its checksum list, the attempt to define fails
        # and we return False
        cksLst = self.cksLstTbl[cellIx]
        vixLst = self.vixLstTbl[cellIx]
        if cksLst is None:
            cksLst = self.cksLstTbl[cellIx] = []
            vixLst = self.vixLstTbl[cellIx] = []
        ix = -1
        for i in range(len(cksLst)):
            if cks == cksLst[i]:
                # failed!
                return False
        # we can define the entry
        cksLst.append(cks)
        vixLst.append(valueIx)
        return True

    def getMatches(self,e,leftToRight):
        """
        "e" is a node in a doubly linked list. Each node has an "sc"
        attribute, drawn from the same enumeration set as our
        sequences. We're interested in node-sequences whose "sc"
        values match the sequences known to the SeqMap. This method
        finds all such sequences that start at "e". It returns a list
        of [node-sequence,value] pairs. If "leftToRight", we start at
        "e" and procede left-to-right; otherwise we start at e and
        move right-to-left.
        """
        if self.nRows == 0 or e is None:
            return []
        # our result: a list of [node-sequence,value] pairs
        matches = []
        # sequence of sc values
        seq = []
        # sequence of nodes
        ndSeq = []
        # "rowIx" and "colIx" gives our current positions in the
        # matrix
        colIx = e.sc
        rowIx = 0
        while True:
            # update sequences
            seq.append(e.sc)
            ndSeq.append(e)
            # get value (if any) for this sequence at this cell
            cellIx = rowIx*self.nCols + colIx
            v = self.getSeqValAtCell(seq,cellIx)
            if v is not None:
                # append [ndSeq,v] to the results
                matches.append([ndSeq[:],v])
            # Can we walk farther? Reset "e" to the next node in the
            # walk.
            e = e.nxt if leftToRight else e.prv
            if e is not None:
                # get transitions out of current cell
                trs = self.trsTbl[cellIx]
                if trs is not None and e.sc in trs:
                    # we can continue
                    rowIx += 1
                    colIx = e.sc
                    continue
            # cannot walk farther
            break
        return matches

    def printme(self,fp,termToStr):
        """ print the map """
        if fp is None:
            fp = sys.stdout
        fp.write('seqMap. nRows: %s nCols: %d\n' %
            (self.nRows, self.nCols))
        for rowIx in range(self.nRows):
            for colIx in range(self.nCols):
                cellIx = rowIx*self.nCols + colIx
                trsLst = self.trsTbl[cellIx]
                cksLst = self.cksLstTbl[cellIx]
                vixLst = self.vixLstTbl[cellIx]
                cellDefined = False
                if trsLst is not None and len(trsLst)>0:
                    cellDefined = True
                if cksLst is not None and len(cksLst)>0:
                    cellDefined = True
                if not cellDefined:
                    continue
                if termToStr is None:
                    fp.write('[%d,%d] sc:%s ' %
                        (rowIx,colIx,str(colIx)))
                else:
                    fp.write('[%d,%d] sc:%s ' %
                        (rowIx,colIx,termToStr(colIx)))
                fp.write('trs:%s\n' % str(trsLst))
                if cksLst is not None:
                    for i in range(len(cksLst)):
                        cks = cksLst[i]
                        vix = vixLst[i]
                        fp.write('  cks: %d. %d\n' % (cks,vix))

def scToStr(v):
    """ get string representation for sc value """
    return vcb.getScSpelling(v)

def srSeqToStr(seq):
    """ get string representation for sr sequence """
    l = []
    for t in seq:
        scopeOffset = 0xf & (t>>4)
        sr = 0xf & t
        srSp = SRids[sr]
        l.append('%s:%s' % (srSp,scopeOffset))
    return ' '.join(l)
