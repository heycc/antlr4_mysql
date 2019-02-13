#!/bin/env python
# -*- coding: utf8 -*-

from antlr4 import *
from MySqlLexer import MySqlLexer
from MySqlParser import MySqlParser
from MySqlParserListener import MySqlParserListener
import sys


class CaseChangingCharInputStream(InputStream):
    def __init__(self, data, upper=True):
        super(CaseChangingCharInputStream, self).__init__(data)
        self.upper = upper

    def LA(self, pos):
        value = super(CaseChangingCharInputStream, self).LA(pos)
        if 0 <= value < 256:
            if pos <= 0: return value
            str_value = chr(value)
            return ord(str_value.upper()) if self.upper else ord(str_value.lower())
        else:
            return value


class CaseChangingCharFileStream(FileStream, CaseChangingCharInputStream):
    def __init__(self, file, upper=True):
        super(CaseChangingCharFileStream, self).__init__(file)
        self.upper = upper


class CustomListener(MySqlParserListener):
    def _enterRoot(self, ctx):
        print "root", ctx.getText()
    def _enterSqlStatements(self, ctx):
        print "sqls", ctx.getText()
    def enterSqlStatement(self, ctx):
        print "sql", ctx.getText()
        for child in ctx.getChildren():
            if isinstance(child, MySqlParser.DmlStatementContext):
                self.handleDml(child)

    def _enterFromClause(self, ctx):
        print ctx.getText()

    def printContent(self, ctx, i):
        print "print context: %s"%i, type(ctx), ctx.getText()
        if isinstance(ctx, tree.Tree.TerminalNodeImpl):
            return
        for child in ctx.getChildren():
            self.printContent(child, i+1)

    def printContextTree(self, ctx, i=0, siblings=None):
        if siblings == None:
            siblings = []
        if isinstance(ctx, tree.Tree.TerminalNodeImpl):
            s = u""
            for j in range(i):
                if j in siblings:
                    s += u"│   "
                else:
                    s += u"    "
            s += u"└── "
            s += ctx.getText().encode('utf8')
            print s
            return
        idx = 0
        child_arr = list(ctx.getChildren())
        for child in child_arr:
            has_siblings = True if idx < len(child_arr)-1 else False
            s = u""
            for j in range(i):
                if j in siblings:
                    s += u"│   "
                else:
                    s += u"    "
            if has_siblings:
                s += u"├── "
            else:
                s += u"└── "
            s += str(type(child)).encode('utf8')
            print s
            sub_siblings = list(siblings)
            if has_siblings:
                sub_siblings.append(i)
                self.printContextTree(child, i+1, sub_siblings)
            else:
                self.printContextTree(child, i+1, sub_siblings)
            idx += 1

    def stringifyContext(self, ctx):
        tmp = list()
        if isinstance(ctx, MySqlParser.FullColumnNameContext):
            return ctx.getText()
        elif not isinstance(ctx, tree.Tree.TerminalNodeImpl):
            for child in ctx.getChildren():
                child_str = self.stringifyContext(child)
                if child_str:
                    tmp.append(child_str)
            return " ".join(tmp)
        else:
            return ctx.getText()

    def handleDml(self, ctx):
        child = ctx.getChild(0)     # DmlStatementContext has one child
        if isinstance(child, MySqlParser.SimpleSelectContext):
            self.handleSelect(child)
        elif isinstance(child, MySqlParser.UpdateStatementContext):
            self.handleUpdate(child)
        else:
            print type(child)
    
    def handleSelect(self, ctx):
        print "handle select", self.stringifyContext(ctx)

    def handleUpdate(self, ctx):
        self.printContextTree(ctx)
        ctx = ctx.getChild(0)
        print "handle update", self.stringifyContext(ctx)
        children = list(ctx.getChildren())
        idx = 0
        for child in children[idx:]:
            idx += 1
            if isinstance(child, MySqlParser.TableNameContext):
                tb_name = child.getText()
                break
            elif isinstance(child, MySqlParser.TableSourcesContext):
                tb_name = self.stringifyContext(child)
                break
            elif isinstance(child, tree.Tree.TerminalNodeImpl):
                continue
        for child in children[idx:]:
            idx += 1
            if isinstance(child, tree.Tree.TerminalNodeImpl):
                continue
            elif isinstance(child, MySqlParser.UpdatedElementsContext):
                update_element = self.stringifyContext(child)
                break

        where, orderby, limit = self.parseWhereOrderbyLimit(children[idx:])
        
        print "-- BACKUP SQL FOR UPDATE --"
        print "SELECT * FROM", tb_name, "WHERE", where, orderby, limit

    def parseWhereOrderbyLimit(self, ctxs):
        """
        """
        where = None
        limit = None
        orderby = None
        if len(ctxs) > 4:
            print "Unexpected where/orderby/limit clause", ctxs
            return
        if isinstance(ctxs[-1], MySqlParser.LimitClauseContext):
            limit = self.stringifyContext(ctxs[-1])
            ctxs = ctxs[0:-1]
        if isinstance(ctxs[-1], MySqlParser.OrderByClauseContext):
            orderby = self.stringifyContext(ctxs[-1])
            ctxs = ctxs[0:-1]
        if len(ctxs) == 2:
            where = self.stringifyContext(ctxs[-1])
        return where, orderby, limit
        
def handleTree(tree):
    print "in handle", type(tree)
    for child in tree.getChildren():
        if isinstance(child, tree.Tree.TerminalNode):
            print "child", child.getText()
        else:
            handleTree(child)


def main():
    #lexer = MySqlLexer(StdinStream())
    fs = CaseChangingCharFileStream(sys.argv[1])
    # print fs.__class__.__mro__
    lexer = MySqlLexer(fs)
    stream = CommonTokenStream(lexer)
    parser = MySqlParser(stream)
    tree = parser.root()
    #print tree.getRuleIndex()
    printer = CustomListener()
    walker = ParseTreeWalker()
    walker.walk(printer, tree)

    #handleTree(tree)

if __name__ == '__main__':
    main()
