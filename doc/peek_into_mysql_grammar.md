## 编译parser
```shell
alias antlr4='java -Xmx500M -cp "/usr/local/lib/antlr-4.7.1-complete.jar:$CLASSPATH" org.antlr.v4.Tool'
antlr4  -Dlanguage=Python2 MySqlParser.g4
```
## tree walker 遍历解析过程
```python
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
                print "dml", child
                self.printContent(child, 0)
        # print ctx.getChild(0).getText()
    def _enterFromClause(self, ctx):
        print ctx.getText()

    def printContent(self, ctx, i):
        print "print context: %s"%i, type(ctx), ctx.getText()
        if isinstance(ctx, tree.Tree.TerminalNodeImpl):
            return
        for child in ctx.getChildren():
            self.printContent(child, i+1)

def main():
    lexer = MySqlLexer(FileStream(sys.argv[1]))
    stream = CommonTokenStream(lexer)
    parser = MySqlParser(stream)
    tree = parser.root()
    printer = CustomListener()
    walker = ParseTreeWalker()
    walker.walk(printer, tree)

if __name__ == '__main__':
    main()
```

## 分析过程
**大小写问题**

输入sql
```sql
select a from tb_test where name = "abc";
```
解析报错
```bash
[root@localhost antlr]# python main.py test.sql
line 1:16 mismatched input '_' expecting {<EOF>, 'ALTER', 'ANALYZE', 'CALL', 'CHANGE', 'CHECK', 'CREATE', 'DELETE', 'DESC', 'DESCRIBE', 'DROP', 'EXPLAIN', 'GRANT', 'INSERT', 'KILL', 'LOAD', 'LOCK', 'OPTIMIZE', 'PURGE', 'RELEASE', 'RENAME', 'REPLACE', 'REVOKE', 'SELECT', 'SET', 'SHOW', 'UNLOCK', 'UPDATE', 'USE', 'BEGIN', 'BINLOG', 'CACHE', 'CHECKSUM', 'COMMIT', 'DEALLOCATE', 'DO', 'FLUSH', 'HANDLER', 'HELP', 'INSTALL', 'PREPARE', 'REPAIR', 'RESET', 'ROLLBACK', 'SAVEPOINT', 'START', 'STOP', 'TRUNCATE', 'UNINSTALL', 'XA', 'EXECUTE', 'SHUTDOWN', '--', '(', ';'}
root _="abc";
```
这里说明``select``关键字解析就报错。把mysql关键字改成大写
```sql
SELECT a FROM tb_test WHERE name = "abc";
```
依然报错。解析成功的部分也丢掉了值，比如字段名
```bash
[root@localhost antlr]# python main.py test.sql
line 1:9 no viable alternative at input 'SELECT a FROM'
root SELECTFROM_WHERE="abc";<EOF>
sqls SELECTFROM_WHERE="abc";
```
加上反引号
```sql
SELECT `a` FROM `tb_test` WHERE `name` = "abc";
```
解析出来的关键字带上了反引号
```bash
[root@localhost antlr]# python main.py test.sql
root SELECT`a`FROM`tb_test`WHERE`name`="abc";<EOF>
sqls SELECT`a`FROM`tb_test`WHERE`name`="abc";
sql SELECT`a`FROM`tb_test`WHERE`name`="abc" <class 'MySqlParser.SqlStatementContext'>
dml [647 636 616]
......
```

**分析grammar语法**

MySqlParser.g4是正式的语法。找到root入口
```
root
    : sqlStatements? MINUSMINUS? EOF
    ;

sqlStatements
    : (sqlStatement MINUSMINUS? SEMI | emptyStatement)*
    (sqlStatement (MINUSMINUS? SEMI)? | emptyStatement)
    ;

sqlStatement
    : ddlStatement | dmlStatement | transactionStatement
    | replicationStatement | preparedStatement
    | administrationStatement | utilityStatement
    ;
```
root入口表面，可以一次解析多条sql语句，即语法：sqlStatements

先分析select的语法。按关键字依次进入select的语法定义：
```sqlStatements -> sqlStatement -> dmlStatement -> selectStatement -> querySpecification```
简化的select语法为querySpecification，包括相关的子语法如下：
```
querySpecification
    : SELECT selectSpec* selectElements selectIntoExpression?
      fromClause? orderByClause? limitClause?
    | SELECT selectSpec* selectElements
    fromClause? orderByClause? limitClause? selectIntoExpression?
    ;
---------------
fromClause
    : FROM tableSources
      (WHERE whereExpr=expression)?
      (
        GROUP BY
        groupByItem (',' groupByItem)*
        (WITH ROLLUP)?
      )?
      (HAVING havingExpr=expression)?
    ;
---------------
tableSources
    : tableSource (',' tableSource)*
    ;

tableSource
    : tableSourceItem joinPart*                                     #tableSourceBase
    | '(' tableSourceItem joinPart* ')'                             #tableSourceNested
    ;

tableSourceItem
    : tableName
      (PARTITION '(' uidList ')' )? (AS? alias=uid)?
      (indexHint (',' indexHint)* )?                                #atomTableItem
    | (
      selectStatement
      | '(' parenthesisSubquery=selectStatement ')'
      )
      AS? alias=uid                                                 #subqueryTableItem
    | '(' tableSources ')'                                          #tableSourcesItem
    ;
------------------
fullId
    : uid (DOT_ID | '.' uid)?
    ;

tableName
    : fullId
    ;
------------------
uid
    : simpleId
    //| DOUBLE_QUOTE_ID
    | REVERSE_QUOTE_ID
    | CHARSET_REVERSE_QOUTE_STRING
    ;

simpleId
    : ID
    | charsetNameBase
    | transactionLevelBase
    | engineName
    | privilegesBase
    | intervalTypeBase
    | dataTypeBase
    | keywordsCanBeId
    | functionNameBase
    ;
```
ID的语法在MySQLLexer.g4中
```
ID:                                  ID_LITERAL;
// DOUBLE_QUOTE_ID:                  '"' ~'"'+ '"';
REVERSE_QUOTE_ID:                    '`' ~'`'+ '`';
-----------------
fragment ID_LITERAL:                 [A-Z_$0-9]*?[A-Z_$]+?[A-Z_$0-9]*;
```
由上可见，ID语法仅支持大写字母

## grammar解析过程
没有找到打印AST树形结构的办法，只好遍历过程来查看。上文的代码中，enterSqlStatement进入sql解析后，递归printContent打印子节点，可以一窥AST的树形结构
输入sql
```sql
SELECT A FROM TB_TEST WHERE NAME = "abc";
```
得到递归输出
```bash
[root@localhost antlr]# python main.py test.sql
root SELECTAFROMTB_TESTWHERENAME="abc";<EOF>
sqls SELECTAFROMTB_TESTWHERENAME="abc";
sql SELECTAFROMTB_TESTWHERENAME="abc" <class 'MySqlParser.SqlStatementContext'>
dml [647 636 616]
print context: 0 <class 'MySqlParser.DmlStatementContext'> SELECTAFROMTB_TESTWHERENAME="abc"
print context: 1 <class 'MySqlParser.SimpleSelectContext'> SELECTAFROMTB_TESTWHERENAME="abc"
print context: 2 <class 'MySqlParser.QuerySpecificationContext'> SELECTAFROMTB_TESTWHERENAME="abc"
print context: 3 <class 'antlr4.tree.Tree.TerminalNodeImpl'> SELECT
print context: 3 <class 'MySqlParser.SelectElementsContext'> A
print context: 4 <class 'MySqlParser.SelectColumnElementContext'> A
print context: 5 <class 'MySqlParser.FullColumnNameContext'> A
print context: 6 <class 'MySqlParser.UidContext'> A
print context: 7 <class 'MySqlParser.SimpleIdContext'> A
print context: 8 <class 'antlr4.tree.Tree.TerminalNodeImpl'> A
print context: 3 <class 'MySqlParser.FromClauseContext'> FROMTB_TESTWHERENAME="abc"
print context: 4 <class 'antlr4.tree.Tree.TerminalNodeImpl'> FROM
print context: 4 <class 'MySqlParser.TableSourcesContext'> TB_TEST
print context: 5 <class 'MySqlParser.TableSourceBaseContext'> TB_TEST
print context: 6 <class 'MySqlParser.AtomTableItemContext'> TB_TEST
print context: 7 <class 'MySqlParser.TableNameContext'> TB_TEST
print context: 8 <class 'MySqlParser.FullIdContext'> TB_TEST
print context: 9 <class 'MySqlParser.UidContext'> TB_TEST
print context: 10 <class 'MySqlParser.SimpleIdContext'> TB_TEST
print context: 11 <class 'antlr4.tree.Tree.TerminalNodeImpl'> TB_TEST
print context: 4 <class 'antlr4.tree.Tree.TerminalNodeImpl'> WHERE
print context: 4 <class 'MySqlParser.PredicateExpressionContext'> NAME="abc"
print context: 5 <class 'MySqlParser.BinaryComparasionPredicateContext'> NAME="abc"
print context: 6 <class 'MySqlParser.ExpressionAtomPredicateContext'> NAME
print context: 7 <class 'MySqlParser.FullColumnNameExpressionAtomContext'> NAME
print context: 8 <class 'MySqlParser.FullColumnNameContext'> NAME
print context: 9 <class 'MySqlParser.UidContext'> NAME
print context: 10 <class 'MySqlParser.SimpleIdContext'> NAME
print context: 11 <class 'MySqlParser.KeywordsCanBeIdContext'> NAME
print context: 12 <class 'antlr4.tree.Tree.TerminalNodeImpl'> NAME
print context: 6 <class 'MySqlParser.ComparisonOperatorContext'> =
print context: 7 <class 'antlr4.tree.Tree.TerminalNodeImpl'> =
print context: 6 <class 'MySqlParser.ExpressionAtomPredicateContext'> "abc"
print context: 7 <class 'MySqlParser.ConstantExpressionAtomContext'> "abc"
print context: 8 <class 'MySqlParser.ConstantContext'> "abc"
print context: 9 <class 'MySqlParser.StringLiteralContext'> "abc"
print context: 10 <class 'antlr4.tree.Tree.TerminalNodeImpl'> "abc"
```

