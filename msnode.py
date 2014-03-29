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

class MSNode:
    """
    Parse node for msparse package. Code using the package should
    import this module.
    """
    def __init__(self,kind,form,text,parent):
        # What kind of node is this? If the node has a parent,
        # "self.kind" specifies the relation to its parent -- either a
        # thematic role, or a qualifier. For a top-level node, it
        # gives meta-syntaxtic info about the node -- that it's a
        # quote, or punctuation, etc. See UserGuide for details.
        self.kind = kind
        # syntax form: a noun, modifier, verb expression, etc.
        self.form = form
        # source text for this node
        self.text = text
        # tree structure
        self.parent = parent
        self.subnodes = []
        # depth of this node in the parse tree
        self.depth = 0
        e = parent
        while e is not None:
            self.depth += 1
            e = e.parent
        # prepositions, etc. that immediately precede the phrase
        # represented by this node.
        self.head = ''
        # These attributes are defined for verb expressions. root form
        # of the verb(s).
        self.vroots = ''
        # qualifiers in a complex verb phrase ("couldn't go").
        self.vqual = ''
        # properties -- tense, negation, etc.
        self.vprops = ''
        # These attributes are defined only if you enable the "loc"
        # option. They give info about the location in the source of
        # the text associated with this node.
        self.lineS = -1
        self.colS = -1
        self.lineE = -1
        self.colE = -1
        self.blank = -1

    def getSubnode(self,kind):
        """ Get child node of specified kind """
        for nd in self.subnodes:
            if nd.kind == kind:
                return nd
        return None

    def toXml(self,loc):
        """
        Return a string containing an XML representation of the parse
        tree rooted at this node. "loc" means: include location
        information in nodes. This allows you to map a parse node back
        to the location in the source text from which it came. If you
        don't need this information, specify "false" to reduce visual
        clutter.
        """
        # compute indentation
        indent = '  '
        for cnt in range(self.depth):
            indent += '  '
        sb = [indent + '<' + self.kind]
        # xml-style attributes
        if len(self.form) > 0:
            sb.append(' form="%s"' % self.form)
        if len(self.vroots) > 0:
            sb.append(' vroots="%s"' % self.vroots)
        if len(self.vqual) > 0:
            sb.append(' vqual="%s"' % self.vqual)
        if len(self.vprops) > 0:
            sb.append(' vprops="%s"' % self.vprops)
        if len(self.head) > 0:
            sb.append(' head="%s"' % self.head)
        if loc:
            v = '%d %d %d %d' % \
                (self.lineS,self.colS,self.lineE,self.colE)
            sb.append(' loc="%s"' % v)
            if self.blank != -1:
                sb.append(' blank="%d"' % self.blank)
        sb.append('>')
        if self.text=='':
            sb.append('\n')
        # compute the closer
        closer = "</" + self.kind + ">\n"
        if len(self.subnodes) == 0:
            if len(self.text) > 0:
                sb.append(" " + self.text + " ")
                sb.append(closer)
            return ''.join(sb)
        # text
        if len(self.text) > 0:
            sb.append('\n%s  %s\n' % (indent,self.text))
        # subnodes
        for subnd in self.subnodes:
            sb.append(subnd.toXml(loc))
        # closer
        sb.append(indent + closer)
        return ''.join(sb)

    def summary(self):
        """
        Return a summary of the parse rooted at the node. This is a
        dev/test/debug method: to get all the info discovered in the
        parse, use to the "toXml" method.
        """
        # compute indentation
        indent = ''
        for cnt in range(self.depth):
            indent += '  '
        # show kind
        sb = [indent + self.kind + '. ']
        # for verb expressions, show the roots; otherwise show the
        # text.
        if len(self.vroots) > 0:
            if len(self.vprops) > 0:
                sb.append('[' + self.vprops + '] ')
            if len(self.vqual) > 0:
                sb.append('[' + self.vqual + '] ')
            if len(self.head) > 0:
                sb.append('(' + self.head + ') ')
            sb.append(' %s\n' % self.vroots)
        else:
            if len(self.head) > 0:
                sb.append('(' + self.head + ') ')
            sb.append(' %s\n' % self.text)
        # recurse thru subnodes
        for subnd in self.subnodes:
            sb.append(subnd.summary())
        return ''.join(sb)
