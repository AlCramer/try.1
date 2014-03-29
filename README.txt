This directory contains source code for the Minimal Syntax Parser, plus
associated files. The package name is "msparse". Contents are:

*.py (EXCEPT makevcb.py):
    Source code for the package.

msp.dat:
    Binary initialization file for the package.  You must include it in your
    app. 

lexicon.txt, makevcb.py:
    lexicon.txt is an ascii file containing information about words.
    makevcb.py reads this file and updates the vocabulary contained
    in msp.dat.  You can improve the accuray of the parse
    by editing lexicon.txt, then running makevcb.py to rebuild msp.dat.
    lexicon.txt and makevcb.py should not be included in your app.

qasrc.txt
qaref.xml
    qasrc.txt contains test sentences. qaref.xml contains the expected 
    parse results. These are for qa purposes and should not be included
    in your app.

Notes
-----
You can run msp.py as a main script. To parse text interactively,
type "python msp.py -i". The script will loop, accepting text
you type in and displaying the parse. Other options will parse
the contents of an input file and write the parse to an output 
file. Type "python msp.py -h" to get the usage message for the 
script.

