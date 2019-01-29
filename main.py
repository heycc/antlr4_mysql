#!/bin/env python
# -*- coding: utf8 -*-

from antlr4 import *
from MySqlLexer import MySqlLexer
from MySqlParser import MySqlParser
from MySqlParserListener import MySqlParserListener
import sys

class CustomListener(MySqlParserListener):
    def enterRoot(self, ctx):
        print "root", ctx.getText()
    def enterSqlStatements(self, ctx):
        print "sqls", ctx.getText()
    def enterSqlStatement(self, ctx):
        print "sql", ctx.getText(), type(ctx)
        for child in ctx.getChildren():
            if isinstance(child, MySqlParser.DmlStatementContext):
                self.handleDml(child)
                #print "dml", child
                #self.printContent(child, 0)
        # print ctx.getChild(0).getText()
    def _enterFromClause(self, ctx):
        print ctx.getText()

    def printContent(self, ctx, i):
        print "print context: %s"%i, type(ctx), ctx.getText()
        if isinstance(ctx, tree.Tree.TerminalNodeImpl):
            return
        for child in ctx.getChildren():
            self.printContent(child, i+1)

    def stringifyContext(self, ctx):
        tmp = list()
        if not isinstance(ctx, tree.Tree.TerminalNodeImpl):
            for child in ctx.getChildren():
                child_str = self.stringifyContext(child)
                if child_str:
                    tmp.append(child_str)
            return " ".join(tmp)
        else:
            return ctx.getText()

    def handleDml(self, ctx):
        #print "dml", type(ctx)
        #if isinstance(ctx, MySqlParser.DmlStatementContext)
        child = ctx.getChild(0)
        if isinstance(child, MySqlParser.SimpleSelectContext):
            self.handleSelect(child)
        elif isinstance(child, MySqlParser.UpdateStatementContext):
            self.handleUpdate(child)
        else:
            print type(child)
    
    def handleSelect(self, ctx):
        print "handle select", ctx.getText()

    def handleUpdate(self, ctx):
        ctx = ctx.getChild(0)
        if isinstance(ctx, MySqlParser.SingleUpdateStatementContext):
            children = list(ctx.getChildren())
            # Keyword: UPDATE
            print children[0].getText()
            # tableName
            print children[1].getText()
            # Keyword: SET
            print children[2].getText()
            # updatedElements
            print children[3].getText()
            if len(children[4:]) > 0:
                for child in children[4:]:
                    print self.stringifyContext(child)
                return

    def parseWhereOrderbyLimit(self, ctxs):
        """
        To be fixed
        """
        where = None
        limit = None
        orderby = None
        if len(ctxs) > 4:
            print "Unexpected clause", ctxs
            return
        if isinstance(ctxs[-1], MySqlParser.LimitClauseContext):
            limit = self.formatTree(ctxs[-1])
            print ctxs[0:-1]
            ctxs = self.formatTree(ctxs[0:-1])
        if isinstance(ctxs[-1], MySqlParser.OrderByClauseContext):
            orderby = self.formatTree(ctxs[-1])
            ctxs = self.formatTree(ctxs[0:-1])
        if len(ctxs) == 2:
            where = self.formatTree(ctxs[-1])
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
    lexer = MySqlLexer(FileStream(sys.argv[1]))
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
