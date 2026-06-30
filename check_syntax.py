import ast, sys
try:
    ast.parse(open(sys.argv[1]).read())
    print('SYNTAX OK')
except SyntaxError as e:
    print(f'SYNTAX ERROR: {e}')
