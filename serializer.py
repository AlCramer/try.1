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

import array
import os

"""
We use two files of serialized data structures. "vcb.dat" initializes
the vocabulary, and "parser.dat" provides the parse rules. We don't
use language specific serialization methods, because the package is
ported to multiple languages, so it's best to create our own binary
format.
"""
# file name
fn = ''
# mode ('r' or 'w')
mode = ''
# array of bytes, written to/read from file
ary = None
# serialization index
ixAry = 0

def getFilepath(_fn):
    """
    Get filepath given filename: the code expects the file to reside
    in the same directory as this file.
    """
    dn = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(dn,_fn)
    
def init(_fn,_mode):
    """ init the serialization: specify file name and mode ('r' or 'w') """
    global fn,mode,ary,ixAry
    fn = _fn
    mode = _mode
    ary = array.array('B')
    ixAry = 0
    if mode == 'r':
        fp = open(getFilepath(fn),"rb")
        ary.fromstring(fp.read())
        fp.close()

def fini():
    """ complete the serialization """
    global mode, ary
    if mode == 'w':
        fp = open(getFilepath(fn),"wb")
        fp.write(ary.tostring())
        fp.close()
    ary = None
# int encodings

def encodeInt(v,nBits=32):
    """ encode an int """
    if nBits==8:
        ary.append(0xff & v)
    elif nBits == 16:
        ary.append(0xff & (v>>8))
        ary.append(0xff & v)
    else:
        ary.append(0xff & (v>>24))
        ary.append(0xff & (v>>16))
        ary.append(0xff & (v>>8))
        ary.append(0xff & v)

def decodeInt(nBits=32):
    """ decode an int """
    global ary,ixAry
    if nBits==8:
        v =  ary[ixAry]
        ixAry += 1
    elif nBits == 16:
        v = (ary[ixAry] << 8) |\
            ary[ixAry+1]
        ixAry += 2
    else:
        v = (ary[ixAry] << 24) |\
            (ary[ixAry+1] << 16) |\
            (ary[ixAry+2] << 8) |\
            ary[ixAry+3]
        ixAry += 4
    return v
# string encodings

def encodeStr(s):
    """ encode a string """
    global ary
    ary.append(len(s))
    for i in range(0,len(s)):
        ary.append(ord(s[i]))

def decodeStr():
    """ decode a string """
    global ary,ixAry
    slen = ary[ixAry]
    ixAry += 1
    s = ary[ixAry : ixAry+slen].tostring()
    ixAry += slen
    return s

def encodeStrLst(lst):
    """ encode a list of str's """
    global ary
    encodeInt(len(lst))
    for s in lst:
        ary.append(len(s))
        for i in range(0,len(s)):
            ary.append(ord(s[i]))

def decodeStrLst():
    """ decode a list of str's """
    global ary,ixAry
    lst = []
    N = decodeInt()
    for j in range(0,N):
        slen = ary[ixAry]
        ixAry += 1
        lst.append(ary[ixAry : ixAry+slen].tostring())
        ixAry += slen
    return lst

# List encodings

def encodeIntLst(lst,nBits):
    """ encode a list of int's """
    encodeInt(len(lst),16)
    for e in lst:
        encodeInt(e,nBits)

def decodeIntLst(nBits):
    """ decode a lits of int's """
    lst = []
    N = decodeInt(16)
    for cnt in range(0,N):
        lst.append(decodeInt(nBits))
    return lst

def encodeLstLst(lst,nBits):
    """ encode a list of int-list's. """
    if lst == None:
        encodeInt(0,16)
        return
    encodeInt(len(lst),16)
    for v in lst:
        lenV = 0 if v is None else len(v)
        encodeInt(lenV,16)
        if v is not None:
            for e in v:
                encodeInt(e,nBits)

def decodeLstLst(nBits):
    """
    decode a list of int-list's. An empty int-list is decoded as
    "None" (not as an empty list).
    """
    lstLst = []
    N = decodeInt(16)
    if N == 0:
        return None
    for i in range(N):
        lenV = decodeInt(16)
        if lenV == 0:
            lstLst.append(None)
            continue
        v = []
        for j in range(lenV):
            v.append(decodeInt(nBits))
        lstLst.append(v)
    return lstLst

if __name__== '__main__':
    i = 123
    intLst = [1,2]
    strLst = ['a','ab']
    lstLst = [[1,2],[3]]
    init('x.dat','w')
    encodeInt(i)
    encodeIntLst(intLst,32)
    encodeStrLst(strLst)
    encodeLstLst(lstLst,16)
    fini()
    init('x.dat','r')
    i2 = decodeInt()
    intLst2 = decodeIntLst(32)
    strLst2 = decodeStrLst()
    lstLst2 = decodeLstLst(16)
    fini()
    assert i == i2
    assert intLst == intLst2
    assert strLst == strLst2
    assert lstLst == lstLst2
