SELECT A AS "a" FROM TB_TEST WHERE NAME = "abc";
UPDATE /* comment */ TB_TEST SET A='a', B='b' WHERE ID=123 AND A='z' ORDER BY A, B LIMIT 1, 1;
-- SELECT `table_name` FROM `information_schema`.`TABLES` WHERE `table_schema` = DATABASE();